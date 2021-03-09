#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid
from model import MtmsModel
from model.connection import ConnectionStatus
from ..widgets import ConnectButton, ServerUrlEdit

logger = logging.getLogger(__name__)


class ServerConnectPanel(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel):
        self.model = model

        # Server URL
        self.server_url_edt = ServerUrlEdit(model=self.model, enabled=True)

        def on_connection_status_changed(caller, value, old_value):
            logger.debug(f"on_connection_status_changed called in \"{self}\" with caller=\"{caller}\", value=\"{value}\", old_value=\"{old_value}\".")

            if value == ConnectionStatus.DISCONNECTED:
                self.server_url_edt.enabled = True
            else:
                self.server_url_edt.enabled = False

        self.model.connection.on_connection_status_changed = on_connection_status_changed

        # Connect button
        self.connect_btn = ConnectButton(
            model=self.model)

        self.main_widget = urwid.Pile([
            self.server_url_edt,
            self.connect_btn,
        ])
        urwid.WidgetWrap.__init__(self, self.main_widget)
