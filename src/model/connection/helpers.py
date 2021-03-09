#!/bin/env python3
# -*- coding: utf-8 -*-
from urllib.parse import urlparse


def validate_url(url):
    if not isinstance(url, str):
        return None

    parse_result = urlparse(url)
    if not all([parse_result.netloc, parse_result.scheme]):
        return None
    return f"{parse_result.scheme}://{parse_result.netloc}{parse_result.path}"
