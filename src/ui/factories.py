#!/bin/env python3
# -*- coding: utf-8 -*-
from .mtms_ui import MtmsUi
from model import MtmsModel


def create_mtms_ui(model: MtmsModel):
    mtms_ui = MtmsUi(model=model)
    return mtms_ui
