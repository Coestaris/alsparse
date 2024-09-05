#!/usr/bin/env python3

#
# @file renderer
# @date 05-09-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

class Renderer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def render(self):
        raise NotImplementedError