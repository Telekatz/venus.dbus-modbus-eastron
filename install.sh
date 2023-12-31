#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
MODBUS_CLIEN_DIR=/opt/victronenergy/dbus-modbus-client
GUI_DIR=/opt/victronenergy/gui/qml

# set permissions for script files
chmod a+x $SCRIPT_DIR/restart.sh
chmod 744 $SCRIPT_DIR/restart.sh

chmod a+x $SCRIPT_DIR/uninstall.sh
chmod 744 $SCRIPT_DIR/uninstall.sh

# add install-script to rc.local to be ready for firmware update
filename=/data/rc.local
if [ ! -f $filename ]
then
    touch $filename
    chmod 755 $filename
    echo "#!/bin/bash" >> $filename
    echo >> $filename
fi
grep -qxF "$SCRIPT_DIR/install.sh" $filename || echo "$SCRIPT_DIR/install.sh" >> $filename

# Backup GUI
if ! [ -e $GUI_DIR/PageAcInSetup._qml ]
then
    cp $GUI_DIR/PageAcInSetup.qml $GUI_DIR/PageAcInSetup._qml 
fi

# Patch GUI
patch=$SCRIPT_DIR/PageAcInSetup_patch.qml
file=$GUI_DIR/PageAcInSetup.qml
if [ "$(cat $patch)" != "$(sed -n '/\/\* Eastron settings \*\//,/\/\* Eastron settings end \*\//p' $file )" ]; then
    sed -i '/\/\* Eastron settings \*\//,/\/\* Eastron settings end \*\//d'  $file
    line_number=$(grep -n "\/\* EM24 settings \*\/" $file | cut -d ":" -f 1)
    if ! [ -z "$line_number" ]; then
      line_number=$((line_number - 1))r
      echo "patching file $file"
      sed -i "$line_number $patch" $file
      svc -t /service/gui
    else
      echo "Error patching file $file" 
    fi
fi

# Backup modbus-client
if ! [ -e $MODBUS_CLIEN_DIR/dbus-modbus-client._py ]
then
    cp $MODBUS_CLIEN_DIR/dbus-modbus-client.py $MODBUS_CLIEN_DIR/dbus-modbus-client._py 
fi

# Patch modbus-client
ln -s -f $SCRIPT_DIR/Eastron.py $MODBUS_CLIEN_DIR/Eastron.py
file=$MODBUS_CLIEN_DIR/dbus-modbus-client.py
if ! grep -q "import Eastron" $file; then
  line_number=$(grep -n "import carlo_gavazzi" $file | cut -d ":" -f 1)
  if ! [ -z "$line_number" ]; then
      echo "patching file $file"
      sed -i "$line_number i import Eastron" $file
      $SCRIPT_DIR/restart.sh
    else
      echo "Error patching file $file" 
    fi
fi





