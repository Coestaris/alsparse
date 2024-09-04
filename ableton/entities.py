#!/usr/bin/env python3
from typing import List, Tuple

#
# @file entities
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
# @copyright Ajax Systems
#

from alsparse import Project, Track, ProjectTime, ProjectStart, Color, \
    AudioClip, MidiClip, Clip


class AbletonAudioClip(AudioClip):
    def __init__(self, name: str, color: Color, start: ProjectTime, end: ProjectTime, analyzed_data: List[float]):
        self.name = name
        self.color = color
        self.start = start
        self.end = end
        self.analyzed_data = analyzed_data

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
    
class AbletonMidiClip(MidiClip):
    def get_name(self) -> str:
        raise NotImplementedError

    def get_color(self) -> Color:
        raise NotImplementedError

    def get_start(self) -> ProjectTime:
        raise NotImplementedError

    def get_end(self) -> ProjectTime:
        raise NotImplementedError

    def get_notes(self) -> List[MidiClip.Note]:
        raise NotImplementedError
    
class AbletonTrack(Track):
    def __init__(self, name: str, color: Color, clips: List[Clip], freezed: bool):
        self.name = name
        self.color = color
        self.clips = clips
        self.freezed = freezed

    def get_name(self) -> str:
        return self.name

    def get_color(self) -> Color:
        return self.color

    def is_freezed(self) -> bool:
        return self.freezed

    def get_clips(self) -> List[Clip]:
        return self.clips
    
class AbletonProject(Project):
    def __init__(self, major_version: int, minorA: int, minorB: int,
                 minorC: int, metadata: dict, tracks: List[AbletonTrack]):
        self.major_version = major_version
        self.minorA = minorA
        self.minorB = minorB
        self.minorC = minorC
        self.metadata = metadata
        self.tracks = tracks

    def get_duration(self) -> ProjectTime:
        raise NotImplementedError

    def get_tempo(self, at: ProjectTime = ProjectStart) -> ProjectTime:
        raise NotImplementedError

    def get_tracks(self) -> List[Track]:
        return self.tracks

    def get_major_version(self) -> int:
        return self.major_version

    def get_minor_version(self) -> Tuple[int, int, int]:
        return self.minorA, self.minorB, self.minorC

    def get_metadata(self) -> dict:
        return self.metadata

    def __str__(self):
        return f"AbletonProject(major_version={self.major_version}, minor_version={self.minorA}.{self.minorB}.{self.minorC}, metadata={self.metadata})"