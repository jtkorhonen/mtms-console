#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from .helpers import validate_url, ValidationError
from variable import Variable
from .connection import ServerConnection

logger = logging.getLogger(__name__)


class MtmsModel():
    def __init__(self, server_url: str = "localhost"):
        self.server_url = Variable(
            server_url,
            validator=lambda _, url: (validate_url(url) is not None))

        self.connection = ServerConnection()
        logger.debug(f"Initialized MtmsModel \"{self}\".")
