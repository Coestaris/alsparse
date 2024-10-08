#!/usr/bin/env python3

#
# @file dump.py
# @date 03-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import sys
sys.path.append(".")

from alsparse.alsparse import parse_file, MidiTrack, MasterTrack, ReturnTrack, \
    GroupTrack, AudioTrack
import os
import argparse
import logging
import sys

__description__ = "Simple CLI tool to dump information from Ableton project files"
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
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args)

    input_file = os.path.abspath(os.path.expanduser(args.input))
    logging.info("Input file '%s'", input_file)

    project = parse_file(input_file)
    if not project:
        logging.error("Failed to parse file '%s'", input_file)
        return 1

    def get_track_type(track):
        if isinstance(track, MidiTrack):
            return "Midi Track"
        elif isinstance(track, AudioTrack):
            return "Audio Track"
        elif isinstance(track, GroupTrack):
            return "Group Track"
        elif isinstance(track, ReturnTrack):
            return "Return Track"
        elif isinstance(track, MasterTrack):
            return "Master Track"
        else:
            return "Unknown Track"

    logging.info("Parsed file \"%s\"", input_file)
    logging.info("Project: \"%s\" (Daw: %s, %s)", project.get_name(), project.get_daw(), project.get_daw_version())
    for track in project.get_tracks():
        logging.info("  %s: \"%s\"", get_track_type(track), track.get_name())
        for clip in track.get_clips():
            logging.info("    Clip: \"%s\". Start: %.2f, End: %.2f",  clip.get_name(), clip.get_start(), clip.get_end())
        for automation in track.get_automations():
            logging.info("    Automation: \"%s\". Events %d", automation.get_target(), len(automation.get_events()))
            for event in automation.get_events():
                logging.debug("      Event: %s, %s", event.time, event.value)

    return 0


if __name__ == '__main__':
    exit(main())
