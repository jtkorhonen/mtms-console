#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from .mtms_model import MtmsModel

logger = logging.getLogger(__name__)


def create_mtms_model():
    mtms_model = MtmsModel()
    return mtms_model
