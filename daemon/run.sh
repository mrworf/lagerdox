#!/bin/bash

DATABASE=lagerdoxdbg
USERNAME=lager
PASSWORD=dox

ARGS=$1

if [ "$1" = "live" ]; then
  DATABASE=lagerdox
  ARGS=$2
fi

echo "===[ Using ${DATABASE} ]==="
./server.py --database ${DATABASE} --dbuser ${USERNAME} --dbpass ${PASSWORD} $ARGS
