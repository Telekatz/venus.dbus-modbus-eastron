# dbus-modbus-eastron
Integrate Eastron grid meters into Victron Energies Venus OS

## Purpose
With the scripts in this repo it should be easy possible to install, uninstall, restart a service that connects Eastron grid meters to the VenusOS and GX devices from Victron. 

## Installation
### Get the code
Just grab a copy of the main branch and copy them to a folder under `/data/` e.g. `/dbus-modbus-eastron`.
After that call the install.sh script.

The following script should do everything for you:
```
wget https://github.com/telekatz/venus.dbus-modbus-eastron/archive/refs/heads/main.zip
unzip main.zip "venus.dbus-modbus-eastron-main/*" -d /data
mv /data/venus.dbus-modbus-eastron-main /data/dbus-modbus-eastron
chmod a+x /data/dbus-modbus-eastron/install.sh
/data/dbus-modbus-eastron/install.sh
rm main.zip
```

Before installing a new version, uninstall the installed version:
```
/data/dbus-modbus-eastron/uninstall.sh
```
### Settings
The following settings are available in the device settings menu inside Venus OS:

| Config value | Explanation |
| ------------- | ------------- |
| Role | Valid values Grid meter, PV inverter, Generator or AC load: mode of operation for the energy meter. |
| Position | Only for PV inverter. Valid values AC input 1, AC input 2 or AC output: Position where the device is connected. |
| Phase | Only for single phase grid meters. Valid values L1, L2 or L3: represents the phase where the device is connected. |

## Used documentation
- https://github.com/victronenergy/venus/wiki Victron Energies Venus OS
- https://github.com/victronenergy/venus/wiki/dbus DBus paths for Victron namespace
- https://github.com/victronenergy/venus/wiki/dbus-api DBus API from Victron
- https://www.eastroneurope.com/ Eastron Europe



