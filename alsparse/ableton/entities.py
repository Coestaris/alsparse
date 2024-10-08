#!/usr/bin/env python3

#
# @file entities
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

from alsparse.alsparse import Project, Track, ProjectTime, ProjectStart, Color, \
    AudioClip, MidiClip, Clip, Automation, Entity, MidiTrack, AudioTrack, \
    ReturnTrack, GroupTrack, MasterTrack
from typing import List, Tuple, Optional, Union
from abc import ABC
import logging

logger = logging.getLogger(__name__)

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
                 start: ProjectTime, end: ProjectTime, disabled: bool = False):
        super().__init__(name, color, parent)
        self.start = start
        self.end = end
        self.disabled = disabled

    def get_disabled(self) -> bool:
        return self.disabled

    def get_start(self) -> ProjectTime:
        return self.start

    def get_end(self) -> ProjectTime:
        return self.end

class AbletonAudioClip(AbletonClip, AudioClip):
    def __init__(self, name: str, color: Color, parent: Optional[Track],
                 start: ProjectTime, end: ProjectTime, disabled,
                 analyzed_data: List[float]):
        super().__init__(name, color, parent, start, end, disabled)
        self.analyzed_data = analyzed_data

    def get_analyzed_data(self) -> List[float]:
        return self.analyzed_data


class AbletonMidiClip(AbletonClip, MidiClip):
    def __init__(self,  name: str, color: Color, parent: Optional[Track],
                    start: ProjectTime, end: ProjectTime, disabled):
        super().__init__(name, color, parent, start, end, disabled)
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

    def get_value_at(self, time: ProjectTime) -> Union[bool, float]:
        if not self.events:
            return 0

        # Do linear interpolation
        for i in range(len(self.events) - 1):
            if self.events[i][0] <= time <= self.events[i + 1][0]:
                t1, v1 = self.events[i]
                t2, v2 = self.events[i + 1]

                return v1 + (v2 - v1) * (time - t1) / (t2 - t1)

        return self.events[-1][1]



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

    def get_duration(self) -> ProjectTime:
        if not self.clips:
            return 0

        return max((clip.get_end() for clip in self.clips))

class AbletonMidiTrack(AbletonTrack, MidiTrack): pass
class AbletonAudioTrack(AbletonTrack, AudioTrack): pass
class AbletonGroupTrack(AbletonTrack, GroupTrack): pass
class AbletonReturnTrack(AbletonTrack, ReturnTrack): pass
class AbletonMasterTrack(AbletonTrack, MasterTrack): pass


class AbletonProject(AbletonEntity, Project):
    TIME_SLICE = 1 / 1000

    def __calculate_duration(self):
        if not self.tracks:
            return 0

        return max([track.get_duration() for track in self.tracks])

    def __build_tempo_cache(self):
        master_track = next((track for track in self.tracks if isinstance(track, AbletonMasterTrack)), None)
        if not master_track:
            logger.warning("Master track not found")
            return

        tempo_automation = next((automation for automation in master_track.get_automations() if automation.get_target() == "Tempo"), None)
        if not tempo_automation:
            logger.warning("Tempo automation not found")
            return

        self.__base_tempo = tempo_automation.get_value_at(0)
        self.__tempo_cache = [tempo_automation.get_value_at(i) for i in range(int(self.get_duration() / AbletonProject.TIME_SLICE))]

    def __init__(self, major_version: int, minorA: int, minorB: int, minorC: int, metadata: dict, hash: str):
        super().__init__("Project", Color(0, 0, 0, 0), None)

        self.major_version = major_version
        self.minorA = minorA
        self.minorB = minorB
        self.minorC = minorC
        self.metadata = metadata

        self.tracks = []
        self.hash = hash

        self.__duration = 0
        self.__tempo_cache = []
        self.__base_tempo = 0

    def get_hash(self) -> str:
        return self.hash

    def set_tracks(self, tracks: List[Track]):
        self.tracks = tracks
        self.__duration = self.__calculate_duration()
        self.__build_tempo_cache()

    def get_duration(self) -> ProjectTime:
        return self.__duration

    def get_tempo(self, at: ProjectTime = ProjectStart) -> ProjectTime:
        if at == ProjectStart:
            return self.__base_tempo

        return self.__tempo_cache[int(at / AbletonProject.TIME_SLICE)]

    def get_tracks(self) -> List[Track]:
        return self.tracks

    def get_daw(self) -> str:
        return "Ableton Live"

    def get_daw_version(self) -> str:
        return f"{self.minorA}.{self.minorB}.{self.minorC}"

    def __str__(self):
        return f"AbletonProject(major_version={self.major_version}, minor_version={self.minorA}.{self.minorB}.{self.minorC}, metadata={self.metadata})"