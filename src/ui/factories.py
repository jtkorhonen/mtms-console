#!/bin/env python3
# -*- coding: utf-8 -*-
from .mtms_ui import MtmsUi
from model import MtmsModel


def create_mtms_ui(model: MtmsModel, version: str):
    mtms_ui = MtmsUi(model=model, version=version)
    return mtms_ui
