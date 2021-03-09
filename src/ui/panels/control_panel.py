#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid
from model import MtmsModel
from model.connection import ConnectionStatus
from ..panels import ServerConnectPanel
from ..helpers import hr, div

logger = logging.getLogger(__name__)


class ControlPanel(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel):
        self.model = model

        # Control
        self.control_txt = urwid.Text("Instrument control")

        # Server URL
        self.server_connect_widget = ServerConnectPanel(self.model)

        # Control panel
        self.empty_panel = urwid.Text("No connection")
        self.control_panel = urwid.Pile([
            urwid.Text("Connected"),
        ])
        self.control_panel_placeholder = urwid.WidgetPlaceholder(self.empty_panel)

        def on_connection_status_changed(caller, value, old_value):
            logger.debug(f"on_connection_status_changed called in \"{self}\" with caller=\"{caller}\", value=\"{value}\", old_value=\"{old_value}\".")

            if value == ConnectionStatus.CONNECTED:
                self.control_panel_placeholder.original_widget = self.control_panel
            else:
                self.control_panel_placeholder.original_widget = self.empty_panel

        self.model.connection.on_connection_status_changed = on_connection_status_changed

        self.main_widget = urwid.Pile([
            self.control_txt,
            hr,
            self.server_connect_widget,
            div,
            self.control_panel_placeholder,
        ])
        urwid.WidgetWrap.__init__(self, self.main_widget)
