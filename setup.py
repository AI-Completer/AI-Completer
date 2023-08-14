#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pathlib
import sys

from setuptools import Extension, setup

if sys.version_info < (3, 11):
    raise RuntimeError("Requires Python 3.11+")

HERE = pathlib.Path(__file__).parent
IS_GIT_REPO = (HERE / ".git").exists()

if IS_GIT_REPO and not (HERE / "README.md").exists():
    print("Install submodules when building from git clone", file=sys.stderr)
    print("Hint:", file=sys.stderr)
    print("  git submodule update --init", file=sys.stderr)
    sys.exit(2)

extensions = []

# The configuration is in setup.cfg.
setup()
