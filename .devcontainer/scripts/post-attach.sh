#!/bin/bash

poetry install
# poetry export -f requirements.txt -o requirements.txt --without-hashes
poetry run flet run src/poetry_template/main.py -w
