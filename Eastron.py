from copy import copy
import logging
import time
import device
import probe
from register import *
import time
from settingsdevice import SettingsDevice

log = logging.getLogger()

class Reg_f32b(Reg_num):
    coding = ('>f', '>2H')
    count = 2
    rtype = float

nr_phases = [ 0, 1, 3, 3 ]

phase_configs = [
    'undefined',
    '1p2w',
    '3p3w',
    '3p4w',
]

MAXREFRESHRATE = 10

class ModbusDeviceEastron():

    def read_data_regs(self, regs, d):
        now = time.time()

        if all(now - r.time < r.max_age for r in regs):
            return

        start = regs[0].base
        count = regs[-1].base + regs[-1].count - start

        rr = self.modbus.read_input_registers(start, count, unit=self.unit)

        latency = time.time() - now

        if rr.isError():
            log.error('Error reading registers %#04x-%#04x: %s',
                      start, start + count - 1, rr)
            raise Exception(rr)

        for reg in regs:
            base = reg.base - start
            end = base + reg.count

            if now - reg.time > reg.max_age:
                if reg.decode(rr.registers[base:end]):
                    d[reg.name] = copy(reg) if reg.isvalid() else None
                reg.time = now

        return latency

    def get_ident(self):
        return 'ea_%s' % self.info['/Serial']

    def dbus_write_register(self, reg, path, val):
        super().dbus_write_register(reg, path, val)
        self.sched_reinit()


class Eastron_1phase(ModbusDeviceEastron,  device.CustomName, device.EnergyMeter):
    phase = 0

    def phase_regs(self, n):
        return [
            Reg_f32b(0x0000, '/Ac/L%d/Voltage' % n,        1, '%.1f V'),
            Reg_f32b(0x0006, '/Ac/L%d/Current' % n,        1, '%.1f A'),
            Reg_f32b(0x000c, '/Ac/L%d/Power' % n,          1, '%.1f W'),
            Reg_f32b(0x0048, '/Ac/L%d/Energy/Forward' % n, 1, '%.1f kWh'),
            Reg_f32b(0x004a, '/Ac/L%d/Energy/Reverse' % n, 1, '%.1f kWh'),
        ]

    def device_init(self):
        self.info_regs = [
            Reg_u32b(0xfc00, '/Serial'),
            Reg_u16 (0xfc02, '/HardwareVersion'),
            Reg_u16 (0xfc03, '/FirmwareVersion'),
        ]

        self.read_info()

        regs = [
            Reg_f32b(0x000c, '/Ac/Power',          1, '%.1f W'),
            Reg_f32b(0x0006, '/Ac/Current',        1, '%.1f A'),
            Reg_f32b(0x0046, '/Ac/Frequency',      1, '%.1f Hz'),
            Reg_f32b(0x0048, '/Ac/Energy/Forward', 1, '%.1f kWh'),
            Reg_f32b(0x004a, '/Ac/Energy/Reverse', 1, '%.1f kWh'),
        ]

        regs += self.phase_regs(self.phase+1)

        self.data_regs = regs
        self.nr_phases = self.phase+1
    
    def init_device_settings(self, dbus):
        super().init_device_settings(dbus)
        
        self.phase_item = self.settings.addSetting(
                self.settings_path + '/Phase', 0, 0, 2,
                callback=self.phase_setting_changed)
        
        self.interval_item = self.settings.addSetting(
                self.settings_path + '/RefreshRate', 1, 1, MAXREFRESHRATE,
                callback=self.refresh_setting_changed)
        
        self.age_limit_fast = 1 / self.interval_item.get_value()

    def phase_setting_changed(self, service, path, value):
        if self.phase != value['Value']:
            self.phase = value['Value']
            self.sched_reinit()
        return

    def refresh_setting_changed(self, service, path, value):
        if self.age_limit_fast != 1 / value['Value']:
            self.sched_reinit()
        return
    
    def device_init_late(self):
        super().device_init_late()
        self.dbus.add_path('/Phase', self.phase_item.get_value(),
                    writeable=True,
                    onchangecallback=self.phase_changed)
        self.dbus.add_path('/RefreshRate', self.interval_item.get_value(),
                    writeable=True,
                    onchangecallback=self.interval_changed)
        if self.phase != self.phase_item.get_value():
            self.phase = self.phase_item.get_value()
            self.reinit()

    def phase_changed(self, path, val):
        if not 0 <= val <= 2:
            return False
        self.phase_item.set_value(val)
        if self.phase != val:
            self.phase = val
            self.sched_reinit()
        return True
    
    def interval_changed(self, path, val):
        if not 1 <= val <= MAXREFRESHRATE:
            return False
        self.interval_item.set_value(val)
        if self.age_limit_fast != 1/val:
            self.sched_reinit()
        return True
        

    
    
# Register list for the SDM72 V2 see https://github.com/reaper7/SDM_Energy_Meter/blob/master/SDM.h#L104

class Eastron_3phase(ModbusDeviceEastron,  device.CustomName, device.EnergyMeter):
    last_time = 0
    last_power = 0


    def phase_regs(self, n):
        s = 2 * (n - 1)
        return [
            Reg_f32b(0x0000 + s, '/Ac/L%d/Voltage' % n,        1, '%.1f V'),
            Reg_f32b(0x0006 + s, '/Ac/L%d/Current' % n,        1, '%.1f A'),
            Reg_f32b(0x000c + s, '/Ac/L%d/Power' % n,          1, '%.1f W'),
            Reg_f32b(0x015a + s, '/Ac/L%d/Energy/Forward' % n, 1, '%.1f kWh'),
            Reg_f32b(0x0160 + s, '/Ac/L%d/Energy/Reverse' % n, 1, '%.1f kWh'),
        ]

    def device_init(self):
        self.info_regs = [
            Reg_u32b(0xfc00, '/Serial'),
            Reg_u16 (0xfc02, '/HardwareVersion'),
            Reg_u16 (0xfc03, '/FirmwareVersion'),
            Reg_f32b(0x000a, '/PhaseConfig', text=phase_configs, write=(0, 3)),
        ]

        self.read_info()

        phases = nr_phases[int(self.info['/PhaseConfig'])]

        regs = [
            Reg_f32b(0x0034, '/Ac/Power',          1, '%.1f W', onchange=self.power_balance),
            Reg_f32b(0x0030, '/Ac/Current',        1, '%.1f A'),
            Reg_f32b(0x0046, '/Ac/Frequency',      1, '%.1f Hz'),
            Reg_f32b(0x018C, '/Ac/Energy/Forward', 1, '%.1f kWh'),     # export minus import
            Reg_f32b(0x018C, '/Ac/Energy/Reverse', -1, '%.1f kWh'),    # export minus import (negative)
            Reg_f32b(0x018C, '/Ac/L1/Energy/Forward', 3, '%.1f kWh'),  # export minus import
            Reg_f32b(0x018C, '/Ac/L1/Energy/Reverse', -3, '%.1f kWh'), # export minus import (negative)
            Reg_f32b(0x018C, '/Ac/L2/Energy/Forward', 3, '%.1f kWh'),  # export minus import
            Reg_f32b(0x018C, '/Ac/L2/Energy/Reverse', -3, '%.1f kWh'), # export minus import (negative)
            Reg_f32b(0x018C, '/Ac/L3/Energy/Forward', 3, '%.1f kWh'),  # export minus import
            Reg_f32b(0x018C, '/Ac/L3/Energy/Reverse', -3, '%.1f kWh'), # export minus import (negative)
            #Reg_f32b(0x0048, '/Ac/Energy/Forward', 1, '%.1f kWh'),    
            #Reg_f32b(0x004a, '/Ac/Energy/Reverse', 1, '%.1f kWh'),
            # Commented out because of wrong phase salding statistics in 1-phase systems, see https://community.victronenergy.com/questions/121094/historical-data-in-vrm-portal-statistics-are-incor.html
        ]

        for n in range(1, phases + 1):
            regs += self.phase_regs(n)

        self.data_regs = regs
        self.nr_phases = phases
        self.last_time = time.time()
        self.last_power = 0

    def init_device_settings(self, dbus):
        super().init_device_settings(dbus)
        
        self.interval_item = self.settings.addSetting(
                self.settings_path + '/RefreshRate', 1, 1, MAXREFRESHRATE,
                callback=self.refresh_setting_changed)
        
        self.age_limit_fast = 1 / self.interval_item.get_value()

    def refresh_setting_changed(self, service, path, value):
        if self.age_limit_fast != 1 / value['Value']:
            self.sched_reinit()
        return
    
    def power_balance(self, reg):
        deltaT =  time.time() - self.last_time
        if (self.last_power > 0):
            self.dbus['/Ac/Energy/ForwardBalancing'] = float(self.dbus['/Ac/Energy/ForwardBalancing']) + (self.last_power * deltaT)/3600000
        else:
            self.dbus['/Ac/Energy/ReverseBalancing'] = float(self.dbus['/Ac/Energy/ReverseBalancing']) + (abs(self.last_power) * deltaT)/3600000
        self.last_time = time.time()
        self.last_power = float(copy(reg)) if reg.isvalid() else 0

    def device_init_late(self):
        super().device_init_late()
        self.dbus.add_path('/Ac/Energy/ForwardBalancing', 0, writeable=True)
        self.dbus.add_path('/Ac/Energy/ReverseBalancing', 0, writeable=True)
        self.last_time = time.time()
        self.dbus.add_path('/RefreshRate', self.interval_item.get_value(),
                    writeable=True,
                    onchangecallback=self.interval_changed)

    def interval_changed(self, path, val):
        if not 1 <= val <= MAXREFRESHRATE:
            return False
        self.interval_item.set_value(val)
        if self.age_limit_fast != 1/val:
            self.sched_reinit()
        return True


class Eastron_SDM72DM(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'Eastron SDM72D-M'
    min_timeout = 0.5

class Eastron_SDM72DM2(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'Eastron SDM72D-M-2'
    min_timeout = 0.5

class Eastron_SDM120M(Eastron_1phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'Eastron SDM120-M'
    min_timeout = 0.5

class Eastron_SDM230M(Eastron_1phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'Eastron SDM230-Modbus'
    min_timeout = 0.5

class Eastron_SDM630M(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'Eastron SDM630-Modbus'
    min_timeout = 0.5

class Eastron_SDM630MCT(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'Eastron SDM630-MCT'
    min_timeout = 0.5


models = {
    132: {
        'model':    'SDM72DM',
        'handler':  Eastron_SDM72DM,
    },
    137: {
        'model':    'SDM72DM2',
        'handler':  Eastron_SDM72DM2,
    },
    32: {
        'model':    'SDM120M',
        'handler':  Eastron_SDM120M,
    },
    43: {
        'model':    'SDM230Modbus',
        'handler':  Eastron_SDM230M,
    },
    112: {
        'model':    'SDM630Modbus',
        'handler':  Eastron_SDM630M,
    },
    121: {
        'model':    'SDM630MCT',
        'handler':  Eastron_SDM630MCT,
    },
}


probe.add_handler(probe.ModelRegister(Reg_u16(0xfc02), models,
                                      methods=['rtu','tcp'],
                                      rates=[9600, 19200, 38400],
                                      units=[1,2]))
