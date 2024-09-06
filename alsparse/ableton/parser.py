#!/usr/bin/env python3
import hashlib

#
# @file parser
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

from alsparse.alsparse import Parser, Color
from alsparse.ableton.entities import AbletonProject, AbletonTrack, AbletonAudioClip, \
    AbletonMidiClip, AbletonAutomation, AbletonGroupTrack, AbletonMidiTrack, \
    AbletonAudioTrack, AbletonReturnTrack, AbletonMasterTrack
import logging
import xml.etree.ElementTree as ET
import gzip
from typing import List, Optional, Tuple
import re
from copy import deepcopy

logger = logging.getLogger(__name__)


class AbletonParser(Parser):
    MINOR_REGEX = re.compile(r'(\d+)\.(\d+)_(\d+)')

    # Some shortcuts to make some common paths more readable
    AUTOMATION_SHORTCUTS = {
        '${track_type}.DeviceChain.Mixer.Volume': 'Volume',
        '${track_type}.DeviceChain.Mixer.On': 'On',
        '${track_type}.DeviceChain.Mixer.Pan': 'Pan',
        '${track_type}.DeviceChain.Mixer.Sends.TrackSendHolder.Send': 'Send',
        '${track_type}.DeviceChain.Mixer.SplitStereoPanL': 'SplitStereoPanL',
        '${track_type}.DeviceChain.Mixer.SplitStereoPanR': 'SplitStereoPanR',
        '${track_type}.DeviceChain.DeviceChain.Devices': 'Plugins',

        'MainTrack.DeviceChain.Mixer.Tempo': 'Tempo',
        'MainTrack.DeviceChain.Mixer.TimeSignature': 'TimeSignature',
    }

    # Expand shortcuts with track types
    for track_type in [ 'AudioTrack', 'MidiTrack', 'GroupTrack', 'ReturnTrack', 'MainTrack' ]:
        for shortcut, target in deepcopy(AUTOMATION_SHORTCUTS).items():
            AUTOMATION_SHORTCUTS[shortcut.replace('${track_type}', track_type)] = target

    @staticmethod
    def is_xml(content: bytes) -> bool:
        """ Check if content is XML-like """
        return content.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')

    @staticmethod
    def is_gzip(content: bytes) -> bool:
        """ Check if content is GZIP-compressed. GZIP magic number is 1f 8b """
        return content.startswith(b'\x1f\x8b')

    @staticmethod
    def __parse_and_verify_version(tree: ET.Element) -> Optional[
        Tuple[int, int, int, int, dict]]:
        """
        Parse and verify an Ableton version from an XML tree.

        Content of the tree looks like this:
          'MinorVersion' = {str} '10.0_377'
          'MajorVersion' = {str} '5'
          'Creator' = {str} 'Ableton Live 10.1.7'
          'Revision' = {str} 'f7eb4c8e0a49802359f4e078b341fdfb9d547a77'
          'SchemaChangeCount' = {str} '3'
        """

        major = int(tree.attrib['MajorVersion'])

        match = AbletonParser.MINOR_REGEX.match(tree.attrib['MinorVersion'])
        minorA, minorB, minorC = map(int, match.groups())

        # Put other keys from XML to metadata
        metadata = {}
        for key, value in tree.attrib.items():
            if key not in ['MajorVersion', 'MinorVersion']:
                metadata[key] = value

        return major, minorA, minorB, minorC, metadata

    @staticmethod
    def __resolve_automation_target(id, track: ET.Element) -> Optional[str]:
        """
        Resolve automation target by ID.
        Various parameters can define automation target, like volume, pan, etc,
        and they can be in different places in the XML tree (since we don't
        have a schema).

        Example:
            <ModulationTarget Id="16178">.

        Function tries to find the target recursively walking through the tree.
        """
        def walk(path, node):
            if node.tag == 'AutomationTarget':
                if int(node.attrib['Id']) == id:
                    return path

            for child in node:
                result = walk(path + [node.tag], child)
                if result:
                    return result

            return None

        path = walk([], track)
        if not path:
            logger.error("Failed to resolve automation target with ID %d", id)
            return None

        path = '.'.join(path)

        for shortcut, target in AbletonParser.AUTOMATION_SHORTCUTS.items():
            path = path.replace(shortcut, target)

        return path

    @staticmethod
    def __get_track_automation_envelopes(parent, track: ET.Element) -> List[AbletonAutomation]:
        """
        Parses automation envelopes for a given track.

        Example of the XML structure:
            <AudioTrack ...> / <MidiTrack ...> and so on
                <AutomationEnvelopes>
                    <Envelopes>
        """
        envelopes = track.find('AutomationEnvelopes').find('Envelopes')
        logger.debug("Found %d automation envelopes", len(envelopes))

        automations = []
        for envelope in envelopes:
            # Example of the XML structure of the envelope:
            # <AutomationEnvelope Id="1">
            #   <EnvelopeTarget>
            #       <PointeeId Value="8638" />
            #   <Automation>
            #       <Events>
            #           <FloatEvent Id="1" Time="0" Value="1" />

            target = AbletonParser.__resolve_automation_target(
                int(envelope.find('EnvelopeTarget').find('PointeeId').attrib['Value']),
                track)

            events = envelope.find('Automation').find('Events')
            points = []

            for event in events:
                time = float(event.attrib['Time'])
                val = event.attrib['Value']
                if val == 'true' or val == 'false':
                    value = 1 if val == 'true' else 0
                else:
                    value = float(val)
                points += [ (time, value) ]

            automations += [ AbletonAutomation("unknown", Color.DEFAULT, parent, target, points) ]

        return automations

    @staticmethod
    def __get_track_color(track: ET.Element) -> Color:
        """ Gets color from element and transforms it to the Color object """
        color = int(track.find('Color').attrib['Value'])
        return Color.DEFAULT

    @staticmethod
    def __get_track_name(track: ET.Element) -> str:
        """ Gets track name from the element (since they have similar structure) """
        return track.find('Name').find('EffectiveName').attrib['Value']

    @staticmethod
    def __parse_audio_track(parent, tree: ET.Element) -> AbletonAudioTrack:
        """
        Parses content of the AudioTrack element.

        AudioTrack is a track that contains audio clips.
        XML structure of the AudioTrack element:
        <AudioTrack ...>
            <DeviceChain>
                <MainSequencer>
                    <Sample>
                        <ArrangerAutomation>
                            <Events>
                                <AudioClip ...>
        """

        track_name = AbletonParser.__get_track_name(tree)
        track_color = AbletonParser.__get_track_color(tree)

        track = AbletonAudioTrack(track_name, track_color, parent)
        clips = []
        for clip in tree.find('DeviceChain').find('MainSequencer').find('Sample').find('ArrangerAutomation').find('Events').findall('AudioClip'):
            start = float(clip.find('CurrentStart').attrib['Value'])
            end = float(clip.find('CurrentEnd').attrib['Value'])
            name = clip.find('Name').attrib['Value']
            color = AbletonParser.__get_track_color(clip)
            disabled = clip.find('Disabled').attrib['Value'] == 'true'
            clips += [ AbletonAudioClip(name, color, track, start, end, disabled, [])]
        track.set_clips(clips)

        automations = AbletonParser.__get_track_automation_envelopes(track, tree)
        track.set_automations(automations)
        return track

    @staticmethod
    def __parse_midi_track(parent, tree: ET.Element) -> AbletonTrack:
        """
        Parses content of the MidiTrack element.

        MidiTrack is a track that contains midi clips.
        XML structure of the MidiTrack element:
            <MidiTrack ...>
                <DeviceChain>
                    <MainSequencer>
                        <ClipTimeable>
                            <ArrangerAutomation>
                                <Events>
        """

        track_name = AbletonParser.__get_track_name(tree)
        track_color = AbletonParser.__get_track_color(tree)

        track = AbletonMidiTrack(track_name, track_color, parent)
        clips = []
        for clip in tree.find('DeviceChain').find('MainSequencer').find('ClipTimeable').find('ArrangerAutomation').find('Events').findall('MidiClip'):
            start = float(clip.find('CurrentStart').attrib['Value'])
            end = float(clip.find('CurrentEnd').attrib['Value'])
            name = clip.find('Name').attrib['Value']
            color = AbletonParser.__get_track_color(clip)
            disabled = clip.find('Disabled').attrib['Value'] == 'true'
            clips += [ AbletonMidiClip(name, color, track, start, end, disabled) ]

            # TODO: Parse notes

        track.set_clips(clips)

        automations = AbletonParser.__get_track_automation_envelopes(track, tree)
        track.set_automations(automations)
        return track


    @staticmethod
    def __parse_simple_track(cls, parent, tree: ET.Element) -> AbletonTrack:
        """
        Parses simple tracks (Return, Group, Master).
        They don't have clips, but they can have automation envelopes.
        """

        track_name = AbletonParser.__get_track_name(tree)
        track_color = AbletonParser.__get_track_color(tree)

        track = cls(track_name, track_color, parent)

        automations = AbletonParser.__get_track_automation_envelopes(track, tree)
        track.set_automations(automations)
        return track


    @staticmethod
    def __parse_tracks(parent, tree: ET.Element) -> List[AbletonTrack]:
        """
        Parses all tracks from the XML tree (except the main/master track).
        Tracks can be of different types: Audio, Group, Return, Midi.
        They have different XML structure, but they all have common elements.
        Example of the XML structure:
            <Ableton ...>
                <LiveSet>
                    <Tracks>
                        <AudioTrack ...>
                        <GroupTrack ...>
                        <ReturnTrack ...>
                        <MidiTrack ...>
                <MainTrack ...>
        """

        # We need to keep order of the tracks, so we can't use a dictionary
        xml_tracks = tree.find('LiveSet').find('Tracks').findall('*')
        tracks = []
        for track in xml_tracks:
            if track.tag == 'AudioTrack':
                tracks += [ AbletonParser.__parse_audio_track(parent, track) ]
            elif track.tag == 'MidiTrack':
                tracks += [ AbletonParser.__parse_midi_track(parent, track) ]
            elif track.tag == 'GroupTrack':
                tracks += [ AbletonParser.__parse_simple_track(AbletonGroupTrack, parent, track) ]
            elif track.tag == 'ReturnTrack':
                tracks += [ AbletonParser.__parse_simple_track(AbletonReturnTrack, parent, track) ]
            else:
                logging.warning("Unknown track type: %s", track.tag)

        master_track = tree.find('LiveSet').find('MainTrack')
        if not master_track:
            master_track = tree.find('LiveSet').find('MasterTrack')
        if not master_track:
            logging.warning("Main track not found")
        else:
            tracks += [ AbletonParser.__parse_simple_track(AbletonMasterTrack, parent, master_track) ]

        return tracks

    def parse(self, content: bytes) -> Optional[AbletonProject]:
        logger.info("Parsing Ableton project")

        if AbletonParser.is_gzip(content):
            logger.info("Detected GZIP compression. Trying to decompress")

            try:
                content = gzip.decompress(content)
            except Exception as e:
                logger.error(f"Failed to decompress: {e}")
                return None

        if not AbletonParser.is_xml(content):
            logger.error("Invalid content: %s", content[:16])
            return None

        # Parse XML content here
        try:
            tree = ET.fromstring(content)
        except Exception as e:
            logger.error(f"Failed to parse XML: {e}")
            return None

        # Get version and metadata
        data = self.__parse_and_verify_version(tree)
        if not data:
            return None
        major, minorA, minorB, minorC, metadata = data
        logger.debug("Parsed version: Major=%d, Minor=%d.%d.%d", major, minorA, minorB, minorC)

        # MD5 hash of the content
        hash = hashlib.md5(content).hexdigest()

        # Process tracks
        project = AbletonProject(major, minorA, minorB, minorC, metadata, hash)
        tracks = self.__parse_tracks(project, tree)
        if not tracks:
            return None
        project.set_tracks(tracks)

        return project

    @staticmethod
    def get_supported_mime_types() -> List[str]:
        return ['application/x-ableton-live-project']

    @staticmethod
    def get_supported_extensions() -> List[str]:
        return ['als']

    @staticmethod
    def probe_content(content: bytes) -> bool:
        return AbletonParser.is_xml(content) or AbletonParser.is_gzip(content)