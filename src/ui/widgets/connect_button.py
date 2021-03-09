#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid
import asyncio
from urllib.parse import urlparse
from model import MtmsModel
from model.connection import ConnectionStatus

logger = logging.getLogger(__name__)


class ConnectButton(urwid.WidgetWrap):
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
                url = ConnectButton.format_url(url)
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
