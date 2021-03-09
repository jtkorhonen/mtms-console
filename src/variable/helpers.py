#!/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import logging
import datetime


def get_logger():
    """Sets up a logger instance.
    """
    logger = logging.getLogger(__name__)

    return logger
