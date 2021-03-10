#!/bin/env python3
# -*- coding: utf-8 -*-
import urwid
import logging

# Global reusable components
div = urwid.Divider()
hr = urwid.Divider('-')


def get_logger_filename():
    try:
        return [h for h in logging.getLoggerClass().root.handlers if isinstance(h, logging.FileHandler)][0].baseFilename
    except IndexError:
        return None
