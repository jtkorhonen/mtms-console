#!/bin/bash

set -e

PYTHONPATH=src pipenv run python -m mtms_cli
