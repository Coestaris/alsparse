#!/usr/bin/env python3
from typing import List

#
# @file entities
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
# @copyright Ajax Systems
#

from alsparse import Project, Track, ProjectTime, ProjectStart, Color, \
    AudioClip, MidiClip, Clip


class AbletonAudioClip(AudioClip):
    def get_name(self) -> str:
        raise NotImplementedError

    def get_color(self) -> Color:
        raise NotImplementedError

    def get_start(self) -> ProjectTime:
        raise NotImplementedError

    def get_end(self) -> ProjectTime:
        raise NotImplementedError

    def get_analyzed_data(self) -> List[float]:
        raise NotImplementedError
    
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
    def get_name(self) -> str:
        raise NotImplementedError

    def get_color(self) -> Color:
        raise NotImplementedError

    def is_freezed(self) -> bool:
        raise NotImplementedError

    def get_clips(self) -> List[Clip]:
        raise NotImplementedError
    
class AbletonProject(Project):
    def __init__(self, major_version: int, minor_version: int, metadata: dict):
        self.major_version = major_version
        self.minor_version = minor_version
        self.metadata = {}

    def get_duration(self) -> ProjectTime:
        raise NotImplementedError

    def get_tempo(self, at: ProjectTime = ProjectStart) -> ProjectTime:
        raise NotImplementedError

    def get_tracks(self) -> List[Track]:
        raise NotImplementedError

    def __str__(self):
        return f"AbletonProject(major_version={self.major_version}, minor_version={self.minor_version}, metadata={self.metadata}, tracks={self.get_tracks()}, duration={self.get_duration()}))"