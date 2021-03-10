#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import urwid
import asyncio
import logging
from model import MtmsModel
from .helpers import div, get_logger_filename
from .panels import ControlPanel, StatusPanel, LogPanel

logger = logging.getLogger(__name__)


class MtmsUi(urwid.WidgetWrap):
    VERSION = "0.0.1"

    def __init__(self, model: MtmsModel):
        self.model = model

        # Title
        self.title_txt = urwid.Text(f"mTMS Console UI, Version {self.VERSION}.")
        self.subtitle_txt = urwid.Text("(c) 2021 Aalto University and Juuso Korhonen (MIT License)")

        # Exit button
        self.exit_btn = urwid.Button("Exit")

        # Control
        self.control_widget = ControlPanel(model=self.model)

        # Status
        self.status_widget = StatusPanel(model=self.model)

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
        self.log_widget = LogPanel(model=self.model, logfile=get_logger_filename())

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
