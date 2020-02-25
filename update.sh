#!/usr/bin/env bash

pipenv pip freeze > requirements.txt
python setup.py sdist bdist_wheel
twine upload dist/*
#rm -rf dist/
