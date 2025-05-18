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

### Update GUI-V2
GUI-V2 Source: https://github.com/Telekatz/gui-v2

The following script installs the latest version of GUI-V2:
```
/data/dbus-modbus-eastron/installGuiV2.sh
```
After installing a new version of GUI-V2, you should restart Venus OS to update the GUI in the VRM portal.
A backup of the original GUI-V2 is available at https://venus/gui-v2-backup/.

### Settings
The following settings are available in the device settings menu inside Venus OS:

| Config value | Explanation |
| ------------- | ------------- |
| Role | Valid values Grid meter, PV inverter, Generator or AC load: mode of operation for the energy meter. |
| Position | Only for PV inverter. Valid values AC input 1, AC input 2 or AC output: Position where the device is connected. |
| Phase | Only for single phase grid meters. Valid values L1, L2 or L3: represents the phase where the device is connected. |
| Refresh Rate | Update rate of power measurement. |
| Energy Counter Source | Method of calculating total imported and exported energy:<br>**Device Value:** Raw values from the energy meter. <br>**Balancing:** Balancing calculation of imported and exported energy.<br>**Import - Export:** Difference between imported and exported energy. |


## Used documentation
- https://github.com/victronenergy/venus/wiki Victron Energies Venus OS
- https://github.com/victronenergy/venus/wiki/dbus DBus paths for Victron namespace
- https://github.com/victronenergy/venus/wiki/dbus-api DBus API from Victron
- https://www.eastroneurope.com/ Eastron Europe



