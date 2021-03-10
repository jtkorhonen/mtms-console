#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid

logger = logging.getLogger(__name__)


class EnabledEdit(urwid.WidgetWrap):
    signals = ["change", "postchange", "enter"]

    def __init__(self, caption: str, text: str, enabled: bool = True):
        self._caption = str(caption)
        self._text = str(text)
        self._enabled = bool(enabled)

        self.field_edt = urwid.Edit(caption=self._caption, edit_text=self._text, multiline=False)
        self.field_txt = urwid.Text(f"{self._caption}{self._text}")

        self.main_widget = urwid.WidgetPlaceholder(self.field_edt if self._enabled else self.field_txt)
        urwid.WidgetWrap.__init__(self, self.main_widget)

    @property
    def caption(self) -> str:
        return self._caption

    @caption.setter
    def caption(self, caption: str):
        self._caption = str(caption)
        self.field_edt.set_caption(self._caption)
        self.field_txt.set_text(f"{self._caption}{self._text}")

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, text: str) -> None:
        self._text = str(text)
        self.field_edt.set_edit_text(self._text)
        self.field_txt.set_text(f"{self._caption}{self._text}")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = bool(value)
        self.main_widget.original_widget = self.field_edt if self._enabled else self.field_txt

    def enable(self, enable: bool = True):
        self.enabled = enable

    def keypress(self, size, key):
        key = super().keypress(size, key)

        if key and key in ('enter', 'down', 'up'):
            old_value = self._text
            new_value = self.field_edt.edit_text
            self._emit('enter', new_value, old_value)
            self.text = new_value
        elif key and key in ('esc',):
            old_value = self._text
            self.text = old_value

        return key
