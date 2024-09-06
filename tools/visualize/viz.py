#!/usr/bin/env python3
import pickle
import shutil
import subprocess
#
# @file dump.py
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import sys
import tempfile
from abc import abstractmethod
import random
from typing import List, Optional

from PIL import ImageDraw
from fontTools.feaLib.variableScalar import Location

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
    parser.add_argument("--link-audio", type=str, help="Link audio file", default=None)
    parser.add_argument("-w", "--width", type=int, default=1920, help="Width of the output image")
    parser.add_argument("-hh", "--height", type=int, default=1080, help="Height of the output image")
    parser.add_argument("-f", "--fps", type=float, default=30, help="FPS of the output video")
    parser.add_argument("--use-cached-time-machine", action="store_true", default=False, help="Use cached time machine")
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

    def __filter_tracks(self):
        self.tracks = self.project.get_tracks()
        if not self.render_info.render_system_tracks:
            self.tracks = [track for track in self.tracks if
                      not isinstance(track, (MasterTrack, ReturnTrack, GroupTrack))]

        self.slices = int(self.project.get_duration() / self.time_slice)

        logging.info("Building cache for %d slices (slice duration: %f), tracks: %d",
                     self.slices, self.time_slice, len(self.tracks))

        self.actual_tracks = len(self.tracks)

    def _build_cache(self):
        self.cache = []
        for track in self.tracks:
            arr = [None] * self.slices
            for i in range(self.slices):
                arr[i] = self.__have_track(track, i * self.time_slice)

            self.cache.append(arr)

        # Convert NxM array to MxN array
        self.cache = list(map(list, zip(*self.cache)))
        pass

    def __init__(self, project: Project, render_info: RenderInfo, time_slice: float = 1 / 2000, cache=None):
        self.project = project
        self.render_info = render_info
        self.time_slice = time_slice

        self.__filter_tracks()

        if cache is None:
            self._build_cache()
        else:
            self.cache = cache

    def get_actual_tracks(self) -> int:
        return self.actual_tracks

    def get_slice(self, at: ProjectTime) -> List[Optional[SlicedTrack]]:
        at_slice = int(at / self.time_slice)
        if at_slice >= len(self.cache) or at_slice < 0:
            return [None] * self.actual_tracks

        return self.cache[int(at / self.time_slice)]

class FileCachedTimeMachine(TimeMachine):
    def __get_location(self, hash: str) -> str:
        import tempfile
        return os.path.join(tempfile.gettempdir(), f"alsparse_{hash}.cache")

    def __init__(self, project: Project, render_info: RenderInfo, time_slice: float = 1 / 1000):
        super().__init__(project, render_info, time_slice, [])

        hash = project.get_hash()
        location = self.__get_location(hash)

        if os.path.exists(location):
            logging.info("Loading cache from '%s'", location)
            with open(location, "rb") as f:
                self.cache = pickle.load(f)
        else:
            self._build_cache()
            logging.info("Saving cache to '%s'", location)
            with open(location, "wb") as f:
                pickle.dump(self.cache, f)


class PixelBuffer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.fb = bytearray(width * height * 3)

    def blit(self, x: int, y: int, rgb: int):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        offset = (y * self.width + x) * 3
        self.fb[offset] = (rgb >> 16) & 0xFF
        self.fb[offset + 1] = (rgb >> 8) & 0xFF
        self.fb[offset + 2] = rgb & 0xFF

    def get_raw(self) -> bytes:
        header = bytearray(f"P6\n{self.width} {self.height}\n255\n", "utf-8")
        return header + self.fb

    def save(self, path: str, frame_index: int = 0):
        with open(path, "wb") as f:
            f.write(self.get_raw())

    def get_width(self) -> int: return self.width
    def get_height(self) -> int: return self.height

class Gradient:
    def __init__(self, start: Color, end: Color, variation: float = 0.2):
        self.start = start
        self.end = end
        self.variation = variation

    def get_variation(self) -> float: return self.variation

    # Value is in range [0, 1]
    def get_value_at(self, value: float) -> Color:
        if value < 0:
            value = 0
        if value > 1:
            value = 1

        r = self.start.r + (self.end.r - self.start.r) * value
        g = self.start.g + (self.end.g - self.start.g) * value
        b = self.start.b + (self.end.b - self.start.b) * value
        a = self.start.a + (self.end.a - self.start.a) * value

        return Color(r, g, b, a)

class VisualConfig:
    def __init__(self, track_height: int, track_gap: int, centerize: bool,
                 x_window: float, track_colors: Optional[Gradient] = None,
                 border_colors: Optional[Gradient] = None):
        self.track_height = track_height
        self.track_gap = track_gap
        self.centerize = centerize
        self.x_window = x_window

        if track_colors is None:
            self.track_colors = Gradient(Color.DEFAULT, Color.DEFAULT)
        else:
            self.track_colors = track_colors

        if border_colors is None:
            self.border_colors = Gradient(Color.DEFAULT, Color.DEFAULT)
        else:
            self.border_colors = border_colors

    def get_track_height(self) -> int: return self.track_height
    def get_track_gap(self) -> int: return self.track_gap
    def get_centerize(self) -> bool: return self.centerize
    def get_x_window(self) -> float: return self.x_window
    def get_track_colors(self) -> Gradient: return self.track_colors
    def get_border_colors(self) -> Gradient: return self.border_colors

class FrameTask:
    def __init__(self,
                 machine: TimeMachine, render_info: RenderInfo, visual_config: VisualConfig,
                 tempo: float, x_offset: float, y_offset: float, index: int):
        self.machine = machine
        self.render_info = render_info
        self.visual_config = visual_config

        self.tempo = tempo
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.index = index

    def run(self, pipe):
        random.seed(0)

        buffer = PixelBuffer(self.render_info.width, self.render_info.height)

        track_colors = []
        track_variantion = self.visual_config.get_track_colors().get_variation()
        for i in range(self.machine.get_actual_tracks()):
            val = i / self.machine.get_actual_tracks()
            val += random.uniform(- track_variantion, track_variantion)
            track_colors.append(self.visual_config.get_track_colors().get_value_at(val).to_rgb888())

        border_colors = []
        border_variantion = self.visual_config.get_border_colors().get_variation()
        for i in range(self.machine.get_actual_tracks()):
            val = i / self.machine.get_actual_tracks()
            val += random.uniform(- border_variantion, border_variantion)
            border_colors.append(self.visual_config.get_border_colors().get_value_at(val).to_rgb888())

        height = int(self.visual_config.get_track_height())

        slice = None
        for j in range(0, self.render_info.width, 1):
            prev_slice = slice

            # Display only X_WINDOW of samples stretched to the whole width
            slice = self.machine.get_slice(self.x_offset + j / self.render_info.width * self.visual_config.get_x_window())
            for i in range(self.machine.get_actual_tracks()):
                color = None

                if slice[i]:
                    if prev_slice and not prev_slice[i]:
                        color = border_colors[i]
                    else:
                        color = track_colors[i]
                else:
                    if prev_slice and prev_slice[i]:
                        color = border_colors[i]

                if color:
                    base_color = color
                    for y in range(int(height)):
                        if y == 0 or y == height - 1:
                            color = border_colors[i]
                        else:
                            color = base_color

                        buffer.blit(
                            j,
                            int(i * height + y + i * self.visual_config.get_track_gap() + self.y_offset),
                            color)

        raw = buffer.get_raw()
        pipe.write(raw)


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

    if args.use_cached_time_machine:
        machine = FileCachedTimeMachine(project, render_info)
    else:
        machine = TimeMachine(project, render_info)

    actual_tracks = machine.get_actual_tracks()
    logging.info("Actual tracks: %d", actual_tracks)

    visual_config = VisualConfig(
        15, 1, True, 4,
        Gradient(Color(227, 218, 100, 255), Color(100, 214, 227, 255), 0.3),
        Gradient(Color(227 - 50, 218 - 50, 100 - 50, 255), Color(100 - 50, 214 - 50, 227 - 50, 255), 0.3)
    )

    START_X = 0
    END_X = float(project.get_duration())
    END_X = float(project.get_duration())

    y_offset = 0
    if visual_config.get_centerize():
        y_offset = (args.height - actual_tracks * visual_config.get_track_height() -
                    (actual_tracks - 1) * visual_config.get_track_gap()) // 2

    # Generate tasks
    index = 0
    tasks = []
    x_offset = START_X
    while x_offset < END_X:
        tempo = project.get_tempo(x_offset)
        tasks.append(FrameTask(machine, render_info, visual_config, tempo, x_offset, y_offset, index))
        index += 1
        # Video frame step is 1 / fps
        # Project step is 1 / get_tempo(x_offset)
        x_offset += (tempo / args.fps) / 60

    # Setup ffmpeg
    ffmpeg_args = ["ffmpeg", "-r", str(args.fps), "-thread_queue_size", "4096" ]
    # Set input format to rgb888
    # ffmpeg_args += [ "-s", f"{args.width}x{args.height}", "-i", f"{outdir}/%d.ppm" ]
    # Read from pipe
    ffmpeg_args += [ "-f", "image2pipe", "-s", f"{args.width}x{args.height}", "-i", "pipe:0" ]
    # Link audio if provided
    if args.link_audio:
        ffmpeg_args.extend([ "-i", args.link_audio, "-c:a", "aac", "-b:a", "192k" ])
    # Set output format to mp4
    ffmpeg_args += [ "-vcodec", "libx264", "-crf", "25", "-pix_fmt", "yuv420p", "-y", "output.mp4"]

    logging.info("Running ffmpeg: %s", " ".join(ffmpeg_args))
    ffmpeg = subprocess.Popen(ffmpeg_args, stdin=subprocess.PIPE)

    logging.info("Rendering %d frames", len(tasks))
    for task in tasks:
        task.run(ffmpeg.stdin)

    ffmpeg.stdin.close()
    ffmpeg.wait()

    return 0


if __name__ == '__main__':
    exit(main())
