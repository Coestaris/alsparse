#!/usr/bin/env python3

#
# @file dump.py
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import sys
from typing import List, Optional

sys.path.append(".")

from alsparse.alsparse import parse_file, MidiTrack, MasterTrack, ReturnTrack, \
    GroupTrack, AudioTrack, Project, Track, Color, Automation, ProjectTime
import os
import argparse
import logging
import sys

__description__ = ""
__version__ = "0.1.0"


def setup_logging(args):
    class Fore:
        GREEN = "\x1b[32m"
        CYAN = "\x1b[36m"
        RED = "\x1b[31m"
        YELLOW = "\x1b[33m"
        RESET = "\x1b[39m"

    def get_format_string(colored: bool, details: bool) -> str:
        green = Fore.GREEN if colored else ""
        cyan = Fore.CYAN if colored else ""
        reset = Fore.RESET if colored else ""

        if details:
            return f"{green}%(asctime)s{reset} - {cyan}%(name)s:%(funcName)s:%(lineno)d{reset} - %(levelname)s - %(message)s"
        else:
            return f"{green}%(asctime)s{reset} - {cyan}%(name)s{reset} - %(levelname)s - %(message)s"

    # Set up logging
    if not args.colorless:
        logging.addLevelName(logging.CRITICAL, f"{Fore.RED}{logging.getLevelName(logging.CRITICAL)}{Fore.RESET}")
        logging.addLevelName(logging.ERROR, f"{Fore.RED}{logging.getLevelName(logging.ERROR)}{Fore.RESET}")
        logging.addLevelName(logging.WARNING, f"{Fore.YELLOW}{logging.getLevelName(logging.WARNING)}{Fore.RESET}")
        logging.addLevelName(logging.INFO, f"{Fore.GREEN}{logging.getLevelName(logging.INFO)}{Fore.RESET}")
        logging.addLevelName(logging.DEBUG, f"{Fore.CYAN}{logging.getLevelName(logging.DEBUG)}{Fore.RESET}")

    logging.getLogger().setLevel(logging.getLevelName(args.log.upper()))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(get_format_string(not args.colorless, args.log == "debug")))
    logging.getLogger().addHandler(handler)


def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog=os.path.basename(__file__))
    parser.description = __description__
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("-l", "--log", type=str, default="info", choices=["debug", "info", "warning", "error", "critical"],
                        help="Log level. Note: 'debug' log level may print sensitive information,\n"
                             "produce a lot of output and program may run slower/incorectly")
    parser.add_argument("-c", "--colorless", action="store_true", help="Disable colored output")
    parser.add_argument("input", help="Input file")
    parser.add_argument("-r", "--renderer", type=str, default="dot", choices=["png", "ffmpeg" ], help="Renderer to use")
    parser.add_argument("-w", "--width", type=int, default=1920, help="Width of the output image")
    parser.add_argument("-hh", "--height", type=int, default=1080, help="Height of the output image")
    parser.add_argument("-f", "--fps", type=float, default=30, help="FPS of the output video")
    parser.add_argument("--render-system-tracks", action="store_true", default=False, help="Render system tracks (master, return, group)")
    parser.add_argument("--render-automations", action="store_true", default=False, help="Render automations")
    parser.add_argument("--render-disabled-clips", action="store_true", default=False, help="Render disabled clips")
    return parser.parse_known_args()

class RenderInfo:
    def __init__(self, width: int, height: int, fps: float,
                 render_system_tracks: bool, render_automations: bool,
                 render_disabled_clips: bool):
        self.width = width
        self.height = height
        self.fps = fps
        self.render_system_tracks = render_system_tracks
        self.render_automations = render_automations
        self.render_disabled_clips = render_disabled_clips

    def get_width(self) -> int: return self.width
    def get_height(self) -> int: return self.height
    def get_fps(self) -> float: return self.fps
    def get_render_system_tracks(self) -> bool: return self.render_system_tracks
    def get_render_automations(self) -> bool: return self.render_automations
    def get_render_disabled_clips(self) -> bool: return self.render_disabled_clips


class SlicedTrack:
    def __init__(self, name: str, color: Color, track: Track):
        self.name = name
        self.color = color
        self.parent = track

    def get_name(self) -> str: return self.name
    def get_color(self) -> Color: return self.color
    def get_parent(self) -> Track: return self.parent

class SlicedAutomation:
    def __init__(self, name: str, color: Color, automation: Automation, value: float):
        self.name = name
        self.color = color
        self.parent = automation
        self.value = value

    def get_name(self) -> str: return self.name
    def get_color(self) -> Color: return self.color
    def get_value(self) -> float: return self.value
    def get_parent(self) -> Automation: return self.parent


class TimeMachine:
    def __have_track(self, track: Track, at: ProjectTime) -> Optional[SlicedTrack]:
        for clip in track.get_clips():
            if not self.render_info.get_render_disabled_clips() and clip.get_disabled():
                continue

            if clip.get_start() <= at <= clip.get_end():
                return SlicedTrack(track.get_name(), track.get_color(), track)

        return None

    def __build_cache(self):
        tracks = self.project.get_tracks()
        if not self.render_info.render_system_tracks:
            tracks = [track for track in tracks if
                      not isinstance(track, (MasterTrack, ReturnTrack, GroupTrack))]

        slices = int(self.project.get_duration() / self.time_slice)

        logging.info("Building cache for %d slices (slice duration: %f), tracks: %d",
                     slices, self.time_slice, len(tracks))

        self.actual_tracks = len(tracks)
        self.cache = []
        for track in tracks:
            arr = [None] * slices
            for i in range(slices):
                arr[i] = self.__have_track(track, i * self.time_slice)

            self.cache.append(arr)

        # Convert NxM array to MxN array
        self.cache = list(map(list, zip(*self.cache)))
        pass

    def __init__(self, project: Project, render_info: RenderInfo, time_slice: float = 1 / 1000):
        self.project = project
        self.render_info = render_info
        self.time_slice = time_slice

        self.__build_cache()

    def get_actual_tracks(self) -> int:
        return self.actual_tracks

    def get_slice(self, at: ProjectTime) -> List[Optional[SlicedTrack]]:
        at_slice = int(at / self.time_slice)
        if at_slice >= len(self.cache):
            return [None] * self.actual_tracks

        return self.cache[int(at / self.time_slice)]


class PixelBuffer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.buffer = [[0] * width for _ in range(height)]

    def __color_to_rgb(self, color: Color) -> int:
        return (color.r << 16) | (color.g << 8) | color.b

    def set_pixel(self, x: int, y: int, color: Color):
        self.buffer[y][x] = self.__color_to_rgb(color)

    def save(self, path: str):
        # Save buffer to file using PIL
        import PIL.Image
        img = PIL.Image.new("RGB", (self.width, self.height))
        for y in range(self.height):
            for x in range(self.width):
                img.putpixel((x, y), self.buffer[y][x])

        img.save(path)

    def get_width(self) -> int: return self.width
    def get_height(self) -> int: return self.height

def main():
    args, other = parse_args()
    setup_logging(args)

    input_file = os.path.abspath(os.path.expanduser(args.input))
    logging.info("Input file '%s'", input_file)
    logging.info("Selected renderer '%s'", args.renderer)
    logging.info("Output resolution: %dx%d", args.width, args.height)
    if args.render_system_tracks:
        logging.info("Rendering all tracks")
    if args.render_automations:
        logging.info("Rendering automations")

    project = parse_file(input_file)
    if not project:
        logging.error("Failed to parse file '%s'", input_file)
        return 1

    logging.info("Parsed file \"%s\"", input_file)
    logging.info("Project: \"%s\" (Daw: %s, %s)", project.get_name(), project.get_daw(), project.get_daw_version())
    logging.info("Duration: %f", project.get_duration())

    render_info = RenderInfo(args.width, args.height, args.fps,
                             args.render_system_tracks, args.render_automations,
                             args.render_disabled_clips)
    machine = TimeMachine(project, render_info)

    buffer = PixelBuffer(args.width, args.height)

    actual_tracks = machine.get_actual_tracks()
    logging.info("Actual tracks: %d", actual_tracks)

    TRACK_HEIGHT = args.height / actual_tracks
    SLICE_WIDTH = project.get_duration() / args.width

    for j in range(0, args.width, 1):
        slice = machine.get_slice(j * SLICE_WIDTH)
        for i in range(actual_tracks):
            if slice[i]:
                for y in range(int(TRACK_HEIGHT)):
                    buffer.set_pixel(j, int(i * TRACK_HEIGHT + y), Color(255, 255, 255, 255))

    buffer.save("output.png")

    return 0


if __name__ == '__main__':
    exit(main())
