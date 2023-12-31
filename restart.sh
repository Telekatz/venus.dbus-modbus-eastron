#!/bin/bash

FILE=/opt/victronenergy/dbus-modbus-client/__pycache__/Eastron.cpython-38.pyc
if test -f "$FILE"; then
   rm $FILE
fi

kill $(pgrep -f "dbus-modbus-client.py")
