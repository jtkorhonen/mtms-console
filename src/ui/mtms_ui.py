#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import datetime
import urwid
import asyncio
import logging
from urllib.parse import urlparse
from model import MtmsModel
from model.connection import ConnectionStatus
from .helpers import div, hr

logger = logging.getLogger(__name__)


class IntEditWithEnter(urwid.IntEdit):
    signals = ["change", "postchange", "enter"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keypress(self, size, key):
        key = super().keypress(size, key)

        if key and key == 'enter':
            self._emit('enter', self.value())
            return None

        return key


class MtmsCliConnectButton(urwid.WidgetWrap):
    BUTTON_TEXT = {
        ConnectionStatus.UNDEFINED: '<<<error>>>',
        ConnectionStatus.CONNECTED: 'Disconnect',
        ConnectionStatus.DISCONNECTED: 'Connect',
        ConnectionStatus.CONNECTING: 'Connecting...',
        ConnectionStatus.DISCONNECTING: 'Disconnecting...',
        ConnectionStatus.CANCELLING: 'Cancelling...',
    }

    def __init__(self, model: MtmsModel):
        self.model = model

        self.connect_button = urwid.Button(self.BUTTON_TEXT[self.model.connection.connection_status])
        self.main_widget = self.connect_button

        def on_connection_status_changed(caller, value, old_value):
            logger.debug(f"on_connection_status_changed called in \"{self}\" with caller=\"{caller}\", "
                         f"value=\"{value}\", old_value=\"{old_value}\".")
            self.connect_button.set_label(self.BUTTON_TEXT[value])

        self.model.connection.on_connection_status_changed = on_connection_status_changed

        async def on_connect_btn_pressed(button):
            logger.debug(f"on_connect_btn_pressed called in \"{self}\" with button=\"{button}\".")

            if self.model.connection.connection_status == ConnectionStatus.DISCONNECTED:
                logger.info("Connecting to server...")

                # Grab URL from component
                url = self.model.server_url.value

                # Store url to server connection
                url = MtmsCliConnectButton.format_url(url)
                model.connection.url = url
                model.server_url.value = model.connection.url

                if model.connection.url is None:
                    logger.error(f"Invalid URL=\"{url}\". Cannot connect.")
                    return

                # Initiate connection
                try:
                    result = await model.connection.connect()
                    if result:
                        logger.info("Connection successful.")
                    else:
                        logger.info("Connection failed.")
                except ConnectionError as e:
                    logger.error(f"Connection to server failed with error=\"{e}\".")

            elif self.model.connection.connection_status == ConnectionStatus.CONNECTED:
                logger.info("Disconnecting from server...")

                try:
                    await model.connection.disconnect()

                except ConnectionError:
                    logger.error("Disconnection request has already been started.")

            elif self.model.connection.connection_status in (ConnectionStatus.CONNECTING, ConnectionStatus.DISCONNECTING):
                logger.info("Terminating connect/disconnect process...")

                self.model.connection.cancel()

        urwid.connect_signal(self.main_widget, 'click', lambda b: asyncio.create_task(on_connect_btn_pressed(b)))

        urwid.WidgetWrap.__init__(self, self.main_widget)

    @staticmethod
    def format_url(url, default_scheme='https'):
        if not isinstance(url, str):
            return None

        if ("://" not in url):
            url = f"{default_scheme}://{url}"

        parse_result = urlparse(url)
        if not all([parse_result.netloc, parse_result.scheme]):
            return None
        return f"{parse_result.scheme}://{parse_result.netloc}{parse_result.path}"


class MtmsCliServerURLField(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel, enabled: bool = True, label: str = "Server URL : "):
        self.model = model
        self._enabled = bool(enabled)
        self._label = str(label)

        self.server_url_edt = urwid.Edit(self._label, str(self.model.server_url), multiline=False)
        self.server_url_txt = urwid.Text(f"{self._label}{self.model.server_url}")

        def on_server_url_changed(caller, value, old_value):
            logger.debug(f"on_server_url_changed called with in \"{self}\" caller=\"{caller}\", value=\"{value}\", old_value=\"{old_value}\".")

            if value == old_value:
                return
            self.server_url_edt.set_edit_text(value)
            self.server_url_txt.set_text(f"{self._label}{value}")

        self.model.server_url.on_value_changed = on_server_url_changed

        self.main_widget = urwid.WidgetPlaceholder(self.server_url_edt if self._enabled else self.server_url_txt)
        urwid.WidgetWrap.__init__(self, self.main_widget)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = bool(value)
        self.main_widget.original_widget = self.server_url_edt if self._enabled else self.server_url_txt

    def enable(self, enable: bool = True):
        self.enabled = enable

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        self._label = str(value)

        self.server_url_edt.set_label(self._label)
        self.server_url_txt.set_text(f"{self._label}{self.model.server_url}")


class MtmsCliServerConnectWidget(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel):
        self.model = model

        # Server URL
        self.server_url_field = MtmsCliServerURLField(model=self.model, enabled=True)

        def on_connection_status_changed(caller, value, old_value):
            logger.debug(f"on_connection_status_changed called in \"{self}\" with caller=\"{caller}\", value=\"{value}\", old_value=\"{old_value}\".")

            if value == ConnectionStatus.DISCONNECTED:
                self.server_url_field.enabled = True
            else:
                self.server_url_field.enabled = False

        self.model.connection.on_connection_status_changed = on_connection_status_changed

        # Connect button
        self.connect_btn = MtmsCliConnectButton(
            model=self.model)

        self.main_widget = urwid.Pile([
            self.server_url_field,
            self.connect_btn,
        ])
        urwid.WidgetWrap.__init__(self, self.main_widget)


class MtmsCliControlPanel(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel):
        self.model = model

        # Control
        self.control_txt = urwid.Text("Instrument control")

        # Server URL
        self.server_connect_widget = MtmsCliServerConnectWidget(self.model)

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


class MtmsCliConnectedWidget(urwid.WidgetWrap):
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


class MtmsCliStatusPanel(urwid.WidgetWrap):

    def __init__(self, model: MtmsModel):
        self.model = model

        # Status
        self.status_txt = urwid.Text("Instrument status")
        self.connected_widget = MtmsCliConnectedWidget(model=self.model)

        self.main_widget = urwid.Pile([
            self.status_txt,
            hr,
            self.connected_widget
        ])

        urwid.WidgetWrap.__init__(self, self.main_widget)


class MtmsCliLogWindow(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel):
        self.model = model

        # Log window
        now = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.log_txt = urwid.Text(f"Log started at {now}.")

        self.main_widget = urwid.LineBox(urwid.Filler(self.log_txt, valign='bottom', top=1))

        urwid.WidgetWrap.__init__(self, self.main_widget)


class MtmsUi(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel, version: str):
        self.model = model
        self.version = version

        # Title
        self.title_txt = urwid.Text(f"mTMS CLI version {version}.")
        self.subtitle_txt = urwid.Text("(c) 2021 Aalto University and Juuso Korhonen (MIT License)")

        # Exit button
        self.exit_btn = urwid.Button("Exit")

        # Control
        self.control_widget = MtmsCliControlPanel(model=self.model)

        # Status
        self.status_widget = MtmsCliStatusPanel(model=self.model)

        # Put status on control side-by-side
        self.system_widget = urwid.Columns([
            self.control_widget,
            self.status_widget,
        ], dividechars=3, min_width=50)

        # Main content arrangement
        self.content = urwid.Pile([
            self.system_widget,
            div,
            self.exit_btn
        ])

        self.header_widget = urwid.Filler(urwid.GridFlow([self.title_txt, self.subtitle_txt], 50, 3, 1, 'left'))
        self.content_widget = urwid.LineBox(urwid.Filler(self.content, valign='top', bottom=1))
        self.log_widget = MtmsCliLogWindow(model=self.model)

        self.main_ui = urwid.Pile([
            (1, self.header_widget),
            self.content_widget,
            (10, self.log_widget)
        ], focus_item=1)

        self.main_widget = urwid.WidgetPlaceholder(self.main_ui)

        # Connect signals
        urwid.connect_signal(self.exit_btn, 'click', lambda b: asyncio.create_task(self.on_exit_clicked(b)))

        urwid.WidgetWrap.__init__(self, self.main_widget)

    def freeze_ui(self):
        # Freeze UI so nothing can be clicked
        exit_screen = urwid.Filler(urwid.Text("Exiting... Please wait (Ctrl-C exits immediately).", align='center'), valign='middle')
        self.main_widget.original_widget = exit_screen

    async def on_exit_clicked(self, button):
        logger.info("Exit button clicked.")
        self.freeze_ui()

        await self.model.connection.disconnect()

        raise urwid.ExitMainLoop()
