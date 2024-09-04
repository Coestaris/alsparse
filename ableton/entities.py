#!/usr/bin/env python3

#
# @file entities
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
# @copyright Ajax Systems
#

from alsparse import Project, Track, ProjectTime, ProjectStart, Color, \
    AudioClip, MidiClip, Clip, Automation, Entity
from typing import List, Tuple, Optional
from abc import ABC


class AbletonAudioClip(AudioClip):
    def __init__(self, name: str, color: Color, start: ProjectTime, end: ProjectTime, analyzed_data: List[float], parent: Track):
        self.name = name
        self.color = color
        self.start = start
        self.end = end
        self.analyzed_data = analyzed_data
        self.parent = parent

    def get_name(self) -> str:
        return self.name

    def get_color(self) -> Color:
        return self.color

    def get_start(self) -> ProjectTime:
        return self.start

    def get_end(self) -> ProjectTime:
        return self.end

    def get_analyzed_data(self) -> List[float]:
        return self.analyzed_data

    def get_parent(self) -> Optional[Track]:
        return self.parent

class AbletonMidiClip(MidiClip):
    def __init__(self, name: str, color: Color, start: ProjectTime, end: ProjectTime, parent: Track):
        self.name = name
        self.color = color
        self.start = start
        self.end = end
        self.parent = parent

    def set_notes(self, notes: List[MidiClip.Note]):
        self.notes

    def get_parent(self) -> Optional[Track]:
        return self.parent

    def get_name(self) -> str:
        return self.name

    def get_color(self) -> Color:
        return self.color

    def get_start(self) -> ProjectTime:
        return self.start

    def get_end(self) -> ProjectTime:
        return self.end

    def get_notes(self) -> List[MidiClip.Note]:
        return self.notes

class AbletonAutomation(Automation):
    def __init__(self, name: str, target: str, color: Color, events: List[Tuple[ProjectTime, float]], parent: Entity):
        self.name = name
        self.color = color
        self.events = events
        self.target = target
        self.parent = parent

    def get_parent(self) -> Optional[Entity]:
        pass

    def get_name(self) -> str:
        return self.name

    def get_color(self) -> Color:
        return self.color

    def get_target(self) -> str:
        return self.target

    def get_events(self) -> List[Automation.Event]:
        return [Automation.Event(time, value) for time, value in self.events]

class AbletonTrack(Track):
    def __init__(self, name: str, color: Color, freezed: bool, parent: Project):
        self.name = name
        self.color = color
        self.freezed = freezed
        self.parent = parent

        self.clips = []
        self.automations = []

    def set_clips(self, clips: List[Clip]):
        self.clips = clips

    def set_automations(self, automations: List[AbletonAutomation]):
        self.automations = automations

    def get_name(self) -> str:
        return self.name

    def get_color(self) -> Color:
        return self.color

    def is_freezed(self) -> bool:
        return self.freezed

    def get_clips(self) -> List[Clip]:
        return self.clips

    def get_automations(self) -> List[AbletonAutomation]:
        return self.automations

    def get_parent(self) -> Optional[Project]:
        return self.parent


class AbletonProject(Project):
    def __init__(self, name: str, major_version: int, minorA: int, minorB: int,
                 minorC: int, metadata: dict):
        self.name = name
        self.major_version = major_version
        self.minorA = minorA
        self.minorB = minorB
        self.minorC = minorC
        self.metadata = metadata

        self.tracks = []
        self.automations = []

    def set_tracks(self, tracks: List[Track]):
        self.tracks = tracks

    def set_automations(self, automations: List[Automation]):
        self.automations = automations

    def get_name(self) -> str:
        return self.name

    def get_color(self) -> Color:
        return Color.BLACK

    def get_parent(self) -> Optional[Entity]:
        return None

    def get_automations(self) -> List[AbletonAutomation]:
        return self.automations

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