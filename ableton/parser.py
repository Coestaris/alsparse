#!/usr/bin/env python3

#
# @file parser
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
# @copyright Ajax Systems
#

from alsparse import Parser
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
    def __parse_and_verify_version(tree: ET.Element) -> Optional[Tuple[int, int, dict]]:
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
            minor = int(MINOR_REGEX.match(tree.attrib['MinorVersion']).group(1))
        except Exception as e:
            logger.error(f"Failed to parse MinorVersion of the project: {e}")
            return None

        # Put other keys from XML to metadata
        metadata = {}
        EXCEPT_KEYS = ['MajorVersion', 'MinorVersion']
        for key, value in tree.attrib.items():
            if key not in EXCEPT_KEYS:
                metadata[key] = value

        return major, minor, metadata

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
        minor, major, metadata = data
        logger.debug("Parsed version: %d.%d", major, minor)
        project = AbletonProject(major, minor, metadata)
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