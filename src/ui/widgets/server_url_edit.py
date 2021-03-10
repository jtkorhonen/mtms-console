#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid
from variable import ValidationError
from model import MtmsModel
from .enabled_edit import EnabledEdit

logger = logging.getLogger(__name__)


class ServerUrlEdit(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel, enabled: bool = True, caption: str = "Server URL : "):
        self.model = model
        self.server_url_edt = EnabledEdit(caption=caption, text=self.model.server_url, enabled=enabled)

        def on_server_url_changed(caller, value, old_value):
            logger.debug(f"on_server_url_changed called with in \"{self}\" caller=\"{caller}\", value=\"{value}\", old_value=\"{old_value}\".")

            if value == old_value:
                return
            self.server_url_edt.text = value

        self.model.server_url.on_value_changed = on_server_url_changed

        def on_value_changed(caller, value, old_value):
            if value == old_value:
                return
            logger.debug(f"on_value_changed called with in \"{self}\" btn=\"{caller}\", value=\"{value}\".")
            old_value = self.model.server_url.value
            try:
                self.model.server_url.value = value
            except ValidationError:
                logger.error(f"Validation of url=\"{value}\" failed. Falling back to \"{old_value}\".")
                self.server_url_edt.text = old_value

        urwid.connect_signal(self.server_url_edt, 'enter', on_value_changed)

        self.main_widget = self.server_url_edt
        urwid.WidgetWrap.__init__(self, self.main_widget)

    @property
    def enabled(self) -> bool:
        return self.server_url_edt.enabled

    @enabled.setter
    def enabled(self, value: bool):
        self.server_url_edt.enabled = value

    def enable(self, enable: bool = True):
        self.enabled = enable

    @property
    def caption(self) -> str:
        return self.server_url_edt.caption

    @caption.setter
    def caption(self, value):
        self.server_url_edt.caption = value
