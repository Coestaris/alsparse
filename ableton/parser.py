#!/usr/bin/env python3

#
# @file parser
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
# @copyright Ajax Systems
#

from alsparse import Parser, Color
from ableton.entities import AbletonProject, AbletonTrack, AbletonAudioClip, \
    AbletonMidiClip
import logging
import xml.etree.ElementTree as ET
import gzip
from typing import List, overload, Optional, Tuple
import re

logger = logging.getLogger(__name__)

def is_xml(content: bytes) -> bool:
    return content.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')

def is_gzip(content: bytes) -> bool:
    return content.startswith(b'\x1f\x8b')

class AbletonParser(Parser):
    @staticmethod
    def __parse_and_verify_version(tree: ET.Element) -> Optional[Tuple[int, int, int, int, dict]]:
        # 'MinorVersion' = {str} '10.0_377'
        # 'MajorVersion' = {str} '5'
        # 'Creator' = {str} 'Ableton Live 10.1.7'
        # 'Revision' = {str} 'f7eb4c8e0a49802359f4e078b341fdfb9d547a77'
        # 'SchemaChangeCount' = {str} '3'
        try:
            major = int(tree.attrib['MajorVersion'])
        except Exception as e:
            logger.error(f"Failed to parse MajorVersion of the project: {e}")
            return None

        MINOR_REGEX = re.compile(r'(\d+)\.(\d+)_(\d+)')
        try:
            minorA, minorB, minorC = MINOR_REGEX.match(tree.attrib['MinorVersion']).groups()
            minorA, minorB, minorC = int(minorA), int(minorB), int(minorC)
        except Exception as e:
            logger.error(f"Failed to parse MinorVersion of the project: {e}")
            return None

        # Put other keys from XML to metadata
        metadata = {}
        EXCEPT_KEYS = ['MajorVersion', 'MinorVersion']
        for key, value in tree.attrib.items():
            if key not in EXCEPT_KEYS:
                metadata[key] = value

        return major, minorA, minorB, minorC, metadata

    @staticmethod
    def __parse_color(index: int) -> Color:
        return Color(0, 0, 0, 0)


    def __parse_audio_track(self, track: ET.Element) -> AbletonTrack:
        # We're interest only in AudioClips
        # Hierarchical structure:
        # <AudioTrack ...>
        #    <DeviceChain>
        #        <MainSequencer>
        #            <Sample>
        #                <ArrangerAutomation>
        #                    <Events>

        track_name = track.find('Name').find('EffectiveName').attrib['Value']
        track_color = self.__parse_color(int(track.find('Color').attrib['Value']))

        events = track.find('DeviceChain').find('MainSequencer').find('Sample').find('ArrangerAutomation').find('Events')
        audio_clips = events.findall('AudioClip')
        logger.debug("Found %d audio clips in track '%s'", len(audio_clips), track_name)

        clips = []
        for clip in audio_clips:
            start = float(clip.find('CurrentStart').attrib['Value'])
            end = float(clip.find('CurrentEnd').attrib['Value'])
            name = clip.find('Name').attrib['Value']
            color = self.__parse_color(int(clip.find('Color').attrib['Value']))
            clips += [ AbletonAudioClip(name, color, start, end, []) ]

        return AbletonTrack(track_name, track_color, clips, False)

    def __parse_midi_track(self, clip: ET.Element) -> AbletonTrack:
        pass

    def __parse_tracks(self, tree: ET.Element) -> List[AbletonTrack]:
        # Hierarchical structure:
        # <Ableton ...>
        #    <LiveSet>
        #        <Tracks>
        tracks = tree.find('LiveSet').find('Tracks')

        audio_tracks = tracks.findall('AudioTrack')
        return_tracks = tracks.findall('ReturnTrack')
        midi_tracks = tracks.findall('MidiTrack')

        tracks = []
        logger.debug("Found %d audio tracks, %d return tracks, %d midi tracks", len(audio_tracks), len(return_tracks), len(midi_tracks))
        for track in audio_tracks:
            tracks += [ self.__parse_audio_track(track) ]
        # for track in return_tracks:
        #   tracks += [ self.__parse_return_track(track) ]
        for track in midi_tracks:
            tracks += [ self.__parse_midi_track(track) ]

        return tracks

    def parse(self, content: bytes) -> Optional[AbletonProject]:
        logger.info("Parsing Ableton project")

        if is_gzip(content):
            logger.info("Detected GZIP compression. Trying to decompress")

            try:
                content = gzip.decompress(content)
            except Exception as e:
                logger.error(f"Failed to decompress: {e}")
                return None

        if not is_xml(content):
            logger.error("Invalid content: %s", content[:16])
            return None

        # Parse XML content here
        try:
            tree = ET.fromstring(content)
        except Exception as e:
            logger.error(f"Failed to parse XML: {e}")
            return None

        data = self.__parse_and_verify_version(tree)
        if not data:
            return None
        major, minorA, minorB, minorC, metadata = data
        logger.debug("Parsed version: Major=%d, Minor=%d.%d.%d", major, minorA, minorB, minorC)

        tracks = self.__parse_tracks(tree)
        if not tracks:
            return None

        project = AbletonProject(major, minorA, minorB, minorC, metadata, tracks)
        return project

    @staticmethod
    def get_supported_mime_types() -> List[str]:
        return ['application/x-ableton-live-project']

    @staticmethod
    def get_supported_extensions() -> List[str]:
        return ['als']

    @staticmethod
    def probe_content(content: bytes) -> bool:
        return is_xml(content) or is_gzip(content)