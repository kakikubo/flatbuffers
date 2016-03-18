#! /usr/bin/env python
# -*- coding: utf-8 -*-

from logging import info, debug, warning, error

class Base():
    def __init__(self):
        self.table = None

    def error(self, message):
        error(self.table + message)
