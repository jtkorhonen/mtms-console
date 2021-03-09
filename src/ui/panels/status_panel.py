#!/bin/env python3
# -*- coding: utf-8 -*-
import logging
import urwid
from model import MtmsModel
from ..widgets import ConnectedText
from ..helpers import hr

logger = logging.getLogger(__name__)


class StatusPanel(urwid.WidgetWrap):

    def __init__(self, model: MtmsModel):
        self.model = model

        # Status
        self.status_txt = urwid.Text("Instrument status")
        self.connected_widget = ConnectedText(model=self.model)

        self.main_widget = urwid.Pile([
            self.status_txt,
            hr,
            self.connected_widget
        ])

        urwid.WidgetWrap.__init__(self, self.main_widget)
