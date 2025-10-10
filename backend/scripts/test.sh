#! /usr/bin/env bash
set -e
set -x

python app/tests_pre_start.py

coverage run -m pytest tests/
coverage report
coverage html --title "${@-coverage}"
