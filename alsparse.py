#!/usr/bin/env python3
import os
#
# @file alsparse
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

from abc import abstractmethod, ABC
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

ProjectTime = float
ProjectStart = 0

class Color:
    def __init__(self, r: int, g: int, b: int, a: int = 255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

class Entity:
    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_color(self) -> Color:
        raise NotImplementedError

    @abstractmethod
    def get_parent(self) -> Optional["Entity"]:
        return None

class Clip(Entity):
    @abstractmethod
    # Relative to the start of the project
    def get_start(self) -> ProjectTime:
        raise NotImplementedError

    @abstractmethod
    # Relative to the start of the project
    def get_end(self) -> ProjectTime:
        raise NotImplementedError

class AudioClip(Clip):
    @abstractmethod
    # List of float values in range [0, 1]
    # Where 0 is silence and 1 is maximum volume
    def get_analyzed_data(self) -> List[float]:
        raise NotImplementedError

class MidiClip(Clip):
    class Note:
        # Pitch is a MIDI note number (A0 - 21, C4 - 60, C8 - 108, etc)
        # Start is relative to the clip start
        # End is relative to the clip start
        def __init__(self, pitch: int, start: ProjectTime, end: ProjectTime):
            self.pitch = pitch
            self.start = start
            self.end = end

    @abstractmethod
    def get_notes(self) -> List[Note]:
        raise NotImplementedError

class Automation(Entity):
    class Event:
        # Value is in range [0, 1]
        def __init__(self, time: ProjectTime, value: float):
            self.time = time
            self.value = value

    @abstractmethod
    def get_target(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_events(self) -> List[Event]:
        raise NotImplementedError

class Track(Entity):
    @abstractmethod
    def is_freezed(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_clips(self) -> List[Clip]:
        raise NotImplementedError

    @abstractmethod
    def get_automations(self) -> List[Automation]:
        raise NotImplementedError

class MidiTrack(Track, ABC): pass
class AudioTrack(Track, ABC): pass
class GroupTrack(Track, ABC): pass
class ReturnTrack(Track, ABC): pass
class MasterTrack(Track, ABC): pass

class Project(Entity):
    @abstractmethod
    def get_daw(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_daw_version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_duration(self) -> ProjectTime:
        raise NotImplementedError

    @abstractmethod
    def get_tempo(self, at: ProjectTime = ProjectStart) -> ProjectTime:
        raise NotImplementedError

    @abstractmethod
    def get_tracks(self) -> List[Track]:
        raise NotImplementedError

class Parser:
    @abstractmethod
    def parse(self, content: bytes) -> Optional[Project]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_supported_mime_types() -> List[str]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_supported_extensions() -> List[str]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def probe_content(content: bytes) -> bool:
        raise NotImplementedError



from ableton.parser import AbletonParser

IMPLEMENTATIONS = [AbletonParser]

def parse_content(content: bytes, mime_type: Optional[str] = None, extension: Optional[str] = None) -> Optional[Project]:
    # TODO: Implement mime type detection
    raise NotImplementedError

def parse_file(path: str) -> Optional[Project]:
    if not os.path.exists(path):
        logger.error("File '%s' does not exist", path)
        return None

    extension = os.path.splitext(path)[1][1:]
    logger.debug("Trying to detect file using extension of '%s'", extension)

    content = None
    parser = None
    for implementation in IMPLEMENTATIONS:
        extensions = implementation.get_supported_extensions()
        logger.debug("%s: %s", implementation.__name__, extensions)
        if extension in extensions:
            logger.debug("Detected file using extension of '%s'. Parser: %s", path, implementation.__name__)
            parser = implementation()

    if not parser:
        logger.error("Could not detect file using extension of '%s'. Trying to probe content", path)
        with open(path, "rb") as f:
            content = f.read()
        for implementation in IMPLEMENTATIONS:
            logger.debug("Probing content using %s", implementation.__name__)
            if implementation.probe_content(content):
                logger.debug("Detected file using content of '%s'. Parser: %s", path, implementation.__name__)
                parser = implementation()

    if not parser:
        logger.error("Could not detect file using content of '%s'", path)
        return None

    if not content:
        with open(path, "rb") as f:
            content = f.read()

    if not parser.probe_content(content):
        logger.error("Content of '%s' does not match the detected parser", path)
        return None

    return parser.parse(content)

