#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid
from model import MtmsModel
from model.connection import ConnectionStatus

logger = logging.getLogger(__name__)


class ConnectedText(urwid.WidgetWrap):
    CONNECTION_TEXT = {
        ConnectionStatus.CONNECTED: "yes",
        ConnectionStatus.DISCONNECTED: "no",
        ConnectionStatus.CONNECTING: "no (connecting...)",
        ConnectionStatus.DISCONNECTING: "yes (disconnecting...)",
        ConnectionStatus.CANCELLING: "unknown",
        ConnectionStatus.UNDEFINED: "<<<error>>>",
    }

    def __init__(self, model: MtmsModel, connection_text="Connected : {status}"):
        self.model = model
        self.connection_text = connection_text

        self.connected_txt = urwid.Text(self.connection_text.format(status=self.CONNECTION_TEXT[self.model.connection.connection_status]))

        def on_connection_status_changed(caller, value, old_value):
            logger.debug(f"on_connection_status_changed called in \"{self}\" with caller=\"{caller}\", value=\"{value}\", old_value=\"{old_value}\".")
            self.connected_txt.set_text(self.connection_text.format(status=self.CONNECTION_TEXT[self.model.connection.connection_status]))

        self.model.connection.on_connection_status_changed = on_connection_status_changed

        self.main_widget = self.connected_txt
        urwid.WidgetWrap.__init__(self, self.main_widget)
