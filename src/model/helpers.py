#!/bin/env python3
# -*- coding: utf-8 -*-
from urllib.parse import urlparse


class ValidationError(Exception):
    pass


def validate_url(url, default_scheme='https'):
    if not isinstance(url, str):
        return None

    if ("://" not in url):
        url = f"{default_scheme}://{url}"

    parse_result = urlparse(url)
    if not all([parse_result.netloc, parse_result.scheme]):
        raise ValidationError(f"Malformed url=\"{url}\".")
    return f"{parse_result.scheme}://{parse_result.netloc}{parse_result.path}"
