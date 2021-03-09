#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from signal import signal, SIGINT
import sys
import os
import time
import datetime
import logging
from typing import Callable, Any, TypeVar, Generic, Optional
from enum import Enum, auto
from urllib.parse import urlparse
import asyncio
import urwid
import urwid.curses_display


VERSION = "0.0.1"

# Global reusable components
div = urwid.Divider()
hr = urwid.Divider('-')


def logger_setup():
    """Sets up a logger instance.

    Notes
    -----
    Exposes a global `logger` instance.
    """
    global logger

    logpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs")
    if not os.path.exists(logpath):
        print(
            f"Error. Log directory ({logpath}) does not exist. Please create manually first.")
        sys.exit(1)

    logfile = f"{os.path.basename(__file__)}.log.{datetime.datetime.now().replace(microsecond=0).isoformat()}"
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger_fh = logging.FileHandler(os.path.join(logpath, logfile))
    logger_fh.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger_fh.setFormatter(logger_formatter)
    logger.addHandler(logger_fh)

    current_logfile = f"{os.path.basename(__file__)}.log.latest"
    if os.path.exists(os.path.join(logpath, current_logfile)):
        os.remove(os.path.join(logpath, current_logfile))
    os.symlink(os.path.join(logpath, logfile),
               os.path.join(logpath, current_logfile))


def exit_handler(signal_received, frame):
    logger.info("SIGINT or Ctrl+C detected. Exiting.")
    raise urwid.ExitMainLoop()

### Exceptions and Custom Classes ##############################################


class ValidationError(Exception):
    pass


class State(Enum):
    UNINITIALIZED = 0
    RED = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4


class ConnectionStatus(Enum):
    UNDEFINED = -1
    DISCONNECTED = 0
    CONNECTED = 1
    DISCONNECTING = 2
    CONNECTING = 3
    CANCELLING = 4

### Variable and Sub-Classes ###################################################


class Variable():
    """A typed variable that updates automatically.

    Raises
    ------
    ValidationError if validation of `value` returns False.

    Notes
    -----
    Relies on global `logger` instance for logging. Make sure it exists before
    instantiating.
    """

    def __init__(self,
                 value: Any,
                 on_value_changed: Callable[[Variable, Any, Any], None] = None,
                 formatter: Callable[[Variable, Any], Any] = None,
                 validator: Callable[[Variable, Any], bool] = None,
                 ) -> None:
        self._on_value_changed = set()
        if on_value_changed:
            self._on_value_changed.add(on_value_changed)
        self.formatter = formatter
        self.validator = validator

        if self.validator and not self.validator(self, value):
            raise ValidationError(f"validation failed for value \"{value}\".")

        self._value = value
        self._type = type(value)

    def _on_value_changed_setter(self, value: Callable[[Variable, Any, Any], None]):
        self._on_value_changed.add(value)

    on_value_changed = property(None, _on_value_changed_setter)

    def _get_value(self) -> Any:
        return self._value

    def _set_value(self, new_value: Any) -> None:
        if self._type is None:
            raise RuntimeWarning(
                "Setting None value can result in errors later on.")
            self._type = type(new_value)  # Deferred setting of the type
        if new_value is not None:   # It is ok to set variable to None
            assert type(new_value) == self._type

        if self.validator and not self.validator(self, new_value):
            raise ValidationError(f"validation failed for value \"{new_value}\".")

        old_value = self._value
        self._value = new_value

        logger.debug(f"Variable \"{self}\" changed from {old_value} to {new_value}.")

        for callback in self._on_value_changed:
            callback(self, self._value, old_value)

    value = property(_get_value, _set_value)

    def __repr__(self):
        if self.formatter:
            try:
                return self.formatter(self, self._value)
            except TypeError:
                return "<Unformattable value>"
        return str(self._value)


class StateVariable(Variable):
    """A typed variable with a state attached to it."""

    def __init__(self,
                 value: Any,
                 state: State = None,
                 on_state_change: Callable[[StateVariable, Any, Any], None] = None,
                 **kwargs):

        super().__init__(value, **kwargs)
        self._state = state or State.UNINITIALIZED

        self.on_state_change = on_state_change

    def _get_state(self):
        return self._state

    def _set_state(self, new_state):
        assert type(new_state) == State
        old_state = self._state
        self._state = new_state

        logger.debug(f"Variable state changed from \"{old_state}\" to \"{new_state}\".")

        if self.on_state_change:
            self.on_state_change(self, self._state, old_state)

    state = property(_get_state, _set_state)


class AutomaticStateVariable(StateVariable):
    """A typed state variable with automatic state control."""

    def __init__(self,
                 value: Any,
                 green_to_yellow: float = None,
                 yellow_to_red: float = None,
                 **kwargs):
        super().__init__(value, **kwargs)

        if green_to_yellow is not None:
            self._green_to_yellow = float(green_to_yellow)
            logger.debug(f"green-to-yellow timeout in \"{self}\" set to {self._green_to_yellow} s.")
        else:
            self._green_to_yellow = None
        self._green_to_yellow_handle = None

        if yellow_to_red is not None:
            self._yellow_to_red = float(yellow_to_red)
            logger.debug(f"yellow-to-red timeout in \"{self}\" set to {self._yellow_to_red} s.")
        else:
            self._yellow_to_red = None
        self._yellow_to_red_handle = None

    @property
    def green_to_yellow(self):
        return self._green_to_yellow

    @green_to_yellow.setter
    def green_to_yellow(self, new_value):
        if new_value is None:
            self._green_to_yellow = None
        else:
            self._green_to_yellow = float(new_value)
            logger.debug(f"green-to-yellow timeout in \"{self}\" set to {self._green_to_yellow} s.")

    @property
    def yellow_to_red(self):
        return self._yellow_to_red

    @yellow_to_red.setter
    def yellow_to_red(self, new_value):
        if new_value is None:
            self._yellow_to_red = None
        else:
            self._yellow_to_red = float(new_value)
            logger.debug(f"yellow-to-red timeout in \"{self}\" set to {self._yellow_to_red} s.")

    def _set_state(self, new_state: State) -> None:
        super()._set_state(new_state)

        # Cancel existing callbacks
        if (self._green_to_yellow_handle and
                not self._green_to_yellow_handle.cancelled()):
            self._green_to_yellow_handle.cancel()

        if (self._yellow_to_red_handle and
                not self._yellow_to_red_handle.cancelled()):
            self._yellow_to_red_handle.cancel()

        if new_state == State.GREEN and self.green_to_yellow:
            loop = asyncio.get_running_loop()

            self._green_to_yellow_handle = loop.call_later(
                self.green_to_yellow,
                lambda self: self._set_state(State.YELLOW), self)

        if new_state == State.YELLOW and self.yellow_to_red:
            loop = asyncio.get_running_loop()

            self._yellow_to_red_handle = loop.call_later(
                self.yellow_to_red,
                lambda self: self._set_state(State.RED), self)

    state = property(StateVariable._get_state, _set_state)

    def _set_value(self, new_value: Any) -> None:
        super()._set_value(new_value)
        self.state = State.GREEN

    value = property(Variable._get_value, _set_value)


def validate_url(url, default_scheme='https'):
    if not isinstance(url, str):
        return None

    if ("://" not in url):
        url = f"{default_scheme}://{url}"

    parse_result = urlparse(url)
    if not all([parse_result.netloc, parse_result.scheme]):
        return None
    return f"{parse_result.scheme}://{parse_result.netloc}{parse_result.path}"

#### Model #####################################################################


class ServerConnection():
    """Bogus server connection model.
    """

    def __init__(self,
                 url: Optional[str] = None,
                 on_connection_status_changed: Callable[[ServerConnection, ConnectionStatus, ConnectionStatus], None] = None
                 ):
        if url:
            self._url = ServerConnection.validate_url(url)
        else:
            self._url = None

        self._on_connection_status_changed = set()
        if on_connection_status_changed:
            self._on_connection_status_changed.add(on_connection_status_changed)

        #self._connected = False
        self._connection_status = ConnectionStatus.DISCONNECTED
        self._connect_task = None
        self._disconnect_task = None

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = ServerConnection.validate_url(value)

    def _on_connection_status_changed_setter(self, value):
        self._on_connection_status_changed.add(value)

    on_connection_status_changed = property(None, _on_connection_status_changed_setter)

    @property
    def connection_status(self):
        return self._connection_status

    @connection_status.setter
    def connection_status(self, value: ConnectionStatus):
        old_value = self._connection_status
        self._connection_status = value

        for callback in self._on_connection_status_changed:
            callback(self, value, old_value)

    @property
    def connected(self):
        return self.connection_status in (ConnectionStatus.CONNECTED, ConnectionStatus.DISCONNECTING)

    @property
    def connecting(self):
        return self.connection_status == ConnectionStatus.CONNECTING
        # return self._connect_task is not None

    async def connect(self) -> bool:
        logger.info(f"Connecting to server \"{self.url}\"...")
        self.connection_status = ConnectionStatus.CONNECTING

        if self.url is None:
            self.connection_status = ConnectionStatus.DISCONNECTED
            logger.error("Could not initiate connection. URL is not set.")
            raise ConnectionError("Could not initiate connection. URL is not set.")

        if self._connect_task is not None:
            logger.error("Could not initiate another connection. Connection process is already started.")
            raise ConnectionError("Please disconnect or cancel the current connection attempt first.")

        async def connect_coro():
            # Bogus connection method
            await asyncio.sleep(5)
            return True

        self._connect_task = asyncio.create_task(connect_coro())
        await self._connect_task

        try:
            if self._connect_task.result():
                logger.info("Connection success.")
                self.connection_status = ConnectionStatus.CONNECTED
                self._connect_task = None
                return True
            else:
                logger.error("Connection failed.")
                self.connection_status = ConnectionStatus.DISCONNECTED
                self._connect_task = None
                return False
        except asyncio.CancelledError:
            logger.info("Connection cancelled during the process.")
            self.connection_status = ConnectionStatus.DISCONNECTED
            self._connect_task = None
            return False

    async def disconnect(self) -> None:
        if not self.connected:
            return

        self.connection_status = ConnectionStatus.DISCONNECTING

        if self._disconnect_task is not None:
            raise ConnectionError("Disconnect is already started.")

        async def disconnect_coro():
            if self._connect_task is not None:
                self._connect_task.cancel()
                await asyncio.sleep(2)
                self._connect_task = None

            await asyncio.sleep(1)

        self._disconnect_task = asyncio.create_task(disconnect_coro())
        await self._disconnect_task

        self.connection_status = ConnectionStatus.DISCONNECTED
        self._disconnect_task = None

    def cancel(self) -> None:
        self.connection_status = ConnectionStatus.CANCELLING
        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None
            self.connection_status = ConnectionStatus.DISCONNECTED

        if self._disconnect_task is not None:
            self._disconnect_task.cancel()
            self._disconnect_task = None
            self.connection_status = ConnectionStatus.CONNECTED

    @staticmethod
    def validate_url(url):
        if not isinstance(url, str):
            return None

        parse_result = urlparse(url)
        if not all([parse_result.netloc, parse_result.scheme]):
            raise ValidationError(f"validation of url=\"{url}\" failed.")
        return f"{parse_result.scheme}://{parse_result.netloc}{parse_result.path}"


class MtmsModel():
    def __init__(self):
        self.server_url = Variable(
            "localhost:5000",
            validator=lambda _, url: (validate_url(url) is not None))

        self.connection = ServerConnection()

### UI Components ##############################################################


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
                try:
                    url = MtmsCliConnectButton.format_url(url)
                    model.connection.url = url
                    model.server_url.value = model.connection.url
                except ValidationError as e:
                    logger.error(f"Invalid URL=\"{url}\". Cannot connect. Error=\"{e}\".")
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


class MtmsCli(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel):
        self.model = model

        # Title
        self.title_txt = urwid.Text(f"mTMS CLI version {VERSION}.")
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


### Run function ###############################################################

def run_ui():
    # Set up exit with Ctrl-Q
    async def exit_on_q(key):
        if key in ('ctrl q', ):
            logger.info("Received exit signal.")

            try:
                mtms_cli.freeze_ui()
                await mtms_model.connection.disconnect()
            except (NameError, AttributeError):
                pass

            raise urwid.ExitMainLoop()

    # Create model
    mtms_model = MtmsModel()

    # Create CLI
    mtms_cli = MtmsCli(model=mtms_model)

    # Start loop
    asyncio_loop = asyncio.get_event_loop()
    event_loop = urwid.AsyncioEventLoop(loop=asyncio_loop)
    loop = urwid.MainLoop(mtms_cli,
                          event_loop=event_loop,
                          screen=urwid.raw_display.Screen(),
                          unhandled_input=lambda key: asyncio.create_task(exit_on_q(key)))
    loop.run()


if __name__ == "__main__":
    logger_setup()   # Side effect: exposes `logger`
    logger.info("Starting main program.")
    signal(SIGINT, exit_handler)   # Attach an exit listener
    run_ui()
