#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid
import datetime
from model import MtmsModel


logger = logging.getLogger(__name__)


class LogPanel(urwid.WidgetWrap):
    def __init__(self, model: MtmsModel):
        self.model = model

        # Log window
        now = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.log_txt = urwid.Text(f"Log started at {now}.")

        self.main_widget = urwid.LineBox(urwid.Filler(self.log_txt, valign='bottom', top=1))

        urwid.WidgetWrap.__init__(self, self.main_widget)
