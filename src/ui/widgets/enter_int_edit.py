#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid

logger = logging.getLogger(__name__)


class EnterIntEdit(urwid.IntEdit):
    signals = ["change", "postchange", "enter"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keypress(self, size, key):
        key = super().keypress(size, key)

        if key and key == 'enter':
            self._emit('enter', self.value())
            return None

        return key
