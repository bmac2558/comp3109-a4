#!/bin/sh

ANTLR_DIR=antlr-3.1.3
ANTLR_PY=${ANTLR_DIR}/runtime/Python

make

PYTHONPATH=${ANTLR_PY}:. python2 run.py ${1}
