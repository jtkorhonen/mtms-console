#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import collections
import urwid
import asyncio
import io
import datetime
from model import MtmsModel


logger = logging.getLogger(__name__)


class LogQueue(collections.deque):
    def put_nowait(self, item):
        self.append(item)

    def get_nowait(self):
        return self.pop()


class ExitableListBox(urwid.ListBox):
    def keypress(self, size, key):
        key = super().keypress(size, key)

        if key and key in ('>',):
            self.set_focus(len(self.body) - 1)
            key = None
        elif key and key in ('<',):
            self.set_focus(0)
            key = None

        return key


class LogPanel(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel, logfile: str = None, update_delay: float = 1.0):
        self.model = model
        self.logfile = str(logfile)
        self.update_delay = float(update_delay)

        # Log window
        now = datetime.datetime.now().replace(microsecond=0).isoformat(sep=' ')
        log_txt = urwid.Text(f"{now} : System started.")

        self.list_walker = urwid.SimpleFocusListWalker([log_txt])
        self.list_box = ExitableListBox(self.list_walker)

        # Connect a streamhalder to the logging
        self.queue = LogQueue(maxlen=100)
        self.queue_handler = logging.handlers.QueueHandler(self.queue)
        formatter = logging.Formatter('%(asctime)s : %(message)s')
        self.queue_handler.setFormatter(formatter)
        self.queue_handler.setLevel(logging.INFO)
        root_handler = logging.getLogger()
        root_handler.addHandler(self.queue_handler)

        def update_log_and_queue(loop, delay):
            for item in self.queue:
                self.list_walker.insert(0, urwid.Text(str(item.message)))
                self.list_walker.set_focus(0)
            self.queue.clear()

            loop.call_later(delay, update_log_and_queue, loop, self.update_delay)

        loop = asyncio.get_event_loop()
        loop.call_soon(update_log_and_queue, loop, self.update_delay)

        self.main_widget = urwid.LineBox(self.list_box)

        urwid.WidgetWrap.__init__(self, self.main_widget)

    def update_widget(self):
        logger.debug(f"update_widget in \"{self}\" called.")
