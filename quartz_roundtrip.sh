#!/bin/sh

set -e

design="$1"
if [ -z "$design" ] || [ ! -f "$(dirname "$0")/examples/${design}_comb.json" ]; then
  echo "usage: $0 <design>  (design from examples file)" >&2
  exit 2
fi

if [ -z "$QUARTZ_DIR" ]; then
  echo "please set \$QUARTZ_DIR to point to your local quartz installation" >&2
  exit 2
fi
cd "$(dirname "$0")"
FF_SPLIT_DIR=$PWD

./json_to_quartz.py "examples/${design}_comb.json" -o "$QUARTZ_DIR/test/${design}_comb.v"
cd $QUARTZ_DIR
dune test
cd "$FF_SPLIT_DIR/examples"
cp -f "$QUARTZ_DIR/_build/default/test/run/${design}_comb.sv" "./quartz_${design}_comb.sv"
