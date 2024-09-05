#!/usr/bin/env python3

#
# @file entities
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

from alsparse import Project, Track, ProjectTime, ProjectStart, Color, \
    AudioClip, MidiClip, Clip, Automation, Entity, MidiTrack, AudioTrack, \
    ReturnTrack, GroupTrack, MasterTrack
from typing import List, Tuple, Optional
from abc import ABC


class AbletonEntity(Entity, ABC):
    def __init__(self, name: str, color: Color, parent: Optional[Entity]):
        self.name = name
        self.color = color
        self.parent = parent

    def get_name(self) -> str:
        return self.name

    def get_color(self) -> Color:
        return self.color

    def get_parent(self) -> Optional[Entity]:
        return self.parent

class AbletonClip(AbletonEntity, Clip):
    def __init__(self, name: str, color: Color, parent: Track,
                 start: ProjectTime, end: ProjectTime):
        super().__init__(name, color, parent)
        self.start = start
        self.end = end

    def get_start(self) -> ProjectTime:
        return self.start

    def get_end(self) -> ProjectTime:
        return self.end

class AbletonAudioClip(AbletonClip, AudioClip):
    def __init__(self, name: str, color: Color, parent: Optional[Track],
                 start: ProjectTime, end: ProjectTime,
                 analyzed_data: List[float]):
        super().__init__(name, color, parent, start, end)
        self.analyzed_data = analyzed_data

    def get_analyzed_data(self) -> List[float]:
        return self.analyzed_data


class AbletonMidiClip(AbletonClip, MidiClip):
    def __init__(self,  name: str, color: Color, parent: Optional[Track],
                    start: ProjectTime, end: ProjectTime):
        super().__init__(name, color, parent, start, end)
        self.notes = []

    def set_notes(self, notes: List[MidiClip.Note]):
        self.notes = notes

    def get_notes(self) -> List[MidiClip.Note]:
        return self.notes

class AbletonAutomation(AbletonEntity, Automation):
    def __init__(self, name: str, color: Color, parent: Optional[Track], target: str, events: List[Tuple[ProjectTime, float]]):
        super().__init__(name, color, parent)
        self.target = target
        self.events = events

    def get_target(self) -> str:
        return self.target

    def get_events(self) -> List[Automation.Event]:
        return [Automation.Event(time, value) for time, value in self.events]


class AbletonTrack(AbletonEntity, Track):
    def __init__(self, name: str, color: Color, parent: Optional[Project]):
        super().__init__(name, color, parent)
        self.clips = []
        self.automations = []

    def set_clips(self, clips: List[Clip]):
        self.clips = clips

    def set_automations(self, automations: List[AbletonAutomation]):
        self.automations = automations

    def is_freezed(self) -> bool:
        return False

    def get_clips(self) -> List[Clip]:
        return self.clips

    def get_automations(self) -> List[AbletonAutomation]:
        return self.automations

class AbletonMidiTrack(AbletonTrack, MidiTrack): pass
class AbletonAudioTrack(AbletonTrack, AudioTrack): pass
class AbletonGroupTrack(AbletonTrack, GroupTrack): pass
class AbletonReturnTrack(AbletonTrack, ReturnTrack): pass
class AbletonMasterTrack(AbletonTrack, MasterTrack): pass


class AbletonProject(AbletonEntity, Project):
    def __init__(self, major_version: int, minorA: int, minorB: int, minorC: int, metadata: dict):
        super().__init__("Project", Color(0, 0, 0, 0), None)

        self.major_version = major_version
        self.minorA = minorA
        self.minorB = minorB
        self.minorC = minorC
        self.metadata = metadata

        self.tracks = []

    def set_tracks(self, tracks: List[Track]):
        self.tracks = tracks

    def get_duration(self) -> ProjectTime:
        raise NotImplementedError

    def get_tempo(self, at: ProjectTime = ProjectStart) -> ProjectTime:
        raise NotImplementedError

    def get_tracks(self) -> List[Track]:
        return self.tracks

    def get_daw(self) -> str:
        return "Ableton Live"

    def get_daw_version(self) -> str:
        return f"{self.minorA}.{self.minorB}.{self.minorC}"

    def __str__(self):
        return f"AbletonProject(major_version={self.major_version}, minor_version={self.minorA}.{self.minorB}.{self.minorC}, metadata={self.metadata})"