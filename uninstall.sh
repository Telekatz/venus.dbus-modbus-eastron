#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
MODBUS_CLIEN_DIR=/opt/victronenergy/dbus-modbus-client

# Restore modbus-client
if test -f "$MODBUS_CLIEN_DIR/dbus-modbus-client._py"; then
  cp $MODBUS_CLIEN_DIR/dbus-modbus-client._py $MODBUS_CLIEN_DIR/dbus-modbus-client.py
  rm $MODBUS_CLIEN_DIR/dbus-modbus-client._py
fi

# Remove Eastron Device
if test -f "$MODBUS_CLIEN_DIR/Eastron.py"; then
  rm $MODBUS_CLIEN_DIR/Eastron.py
fi 

# Remove install-script
grep -v "$SCRIPT_DIR/install.sh" /data/rc.local >> /data/temp.local
mv /data/temp.local /data/rc.local
chmod 755 /data/rc.local

# Clean the GUI
sed -i '/\/\* Eastron settings \*\//,/\/\* Eastron settings end \*\//d'  /opt/victronenergy/gui/qml/PageAcInSetup.qml
svc -t /service/gui

$SCRIPT_DIR/restart.sh
