#!/bin/bash

set -e

export PYTHONPATH=src 

if [[ $PIPENV_ACTIVE -eq 1 ]]; then
    echo "Already in pipenv shell..."
    python -m mtms_cli
else
    echo "Launching with pipenv..."
    pipenv run python -m mtms_cli
fi
