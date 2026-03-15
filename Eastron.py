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
    offset = None

    def set_raw_value(self, val):
        if self.offset is not None:
            val += self.offset
        return self.update(type(self.scale)(val / self.scale))

nr_phases = [ 0, 1, 3, 3 ]

phase_configs = [
    'undefined',
    '1p2w',
    '3p3w',
    '3p4w',
]

_kwh = lambda v: (str(round(v, 3)) + ' kWh')
_kwh2 = lambda p, v: (str(round(v, 3)) + ' kWh')
_a = lambda v: (str(round(v, 1)) + 'A')
_w = lambda v: (str(round(v, 1)) + 'W')
_v = lambda v: (str(round(v, 1)) + 'V')
_hz = lambda v: (str(round(v, 1)) + 'Hz')

MAXREFRESHRATE = 10

class ModbusDeviceEastron():
    vendor_name = 'Eastron'

    def init_device_settings(self, dbus):
        super().init_device_settings(dbus)
        
        self.interval_item = self.settings.addSetting(
            self.settings_path + '/RefreshRate', 1, 1, MAXREFRESHRATE,
            callback=self.refresh_setting_changed)
        
        self.age_limit_fast = 1 / self.interval_item.get_value()

    def device_init_late(self):
        super().device_init_late()
        self.dbus.add_path('/RefreshRate', self.interval_item.get_value(),
            writeable=True,
            onchangecallback=self.interval_changed)
        self.dbus.add_path('/RefreshTime', int(1000 / self.interval_item.get_value()),
            writeable=False)
        
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
        
        self.update_energy()

        return latency

    def get_ident(self):
        return 'ea_%s' % self.info['/Serial']

    def dbus_write_register(self, reg, path, val):
        super().dbus_write_register(reg, path, val)
        self.sched_reinit()

    def interval_changed(self, path, val):
        if not 1 <= val <= MAXREFRESHRATE:
            return False
        self.interval_item.set_value(val)
        if self.age_limit_fast != 1/val:
            self.sched_reinit()
        return True
    
    def refresh_setting_changed(self, service, path, value):
        if self.age_limit_fast != 1 / value['Value']:
            self.sched_reinit()
        return


class Eastron_1phase(ModbusDeviceEastron,  device.CustomName, device.EnergyMeter):
    phase = 0

    def phase_regs(self, n):
        return [
            Reg_f32b(0x0000, '/Ac/L%d/Voltage' % n,        1, _v),
            Reg_f32b(0x0006, '/Ac/L%d/Current' % n,        1, _a),
            Reg_f32b(0x000c, '/Ac/L%d/Power' % n,          1, _w),
            Reg_f32b(0x001e, '/Ac/L%d/PowerFactor' % n,    1, None),
            Reg_f32b(0x0048, '/Ac/L%d/Energy/Forward' % n, 1, _kwh),
            Reg_f32b(0x004a, '/Ac/L%d/Energy/Reverse' % n, 1, _kwh),
        ]

    def device_init(self):
        self.info_regs = [
            Reg_u32b(0xfc00, '/Serial'),
            Reg_u16 (0xfc02, '/HardwareVersion'),
            Reg_u16 (0xfc03, '/FirmwareVersion'),
        ]

        self.read_info()

        regs = [
            Reg_f32b(0x000c, '/Ac/Power',          1, _w),
            Reg_f32b(0x0006, '/Ac/Current',        1, _a),
            Reg_f32b(0x0046, '/Ac/Frequency',      1, _hz),
            Reg_f32b(0x0048, '/Ac/Energy/Forward', 1, _kwh),
            Reg_f32b(0x004a, '/Ac/Energy/Reverse', 1, _kwh),
        ]

        regs += self.phase_regs(self.phase+1)

        self.data_regs = regs
   
    def device_init_late(self):
        super().device_init_late()
        self.dbus.add_path('/Phase', self.phase_item.get_value(),
            writeable=True,
            onchangecallback=self.phase_changed)
        self.dbus.add_path('/Ac/Phase', self.phase_item.get_value() + 1,
            writeable=False)
        if self.phase != self.phase_item.get_value():
            self.phase = self.phase_item.get_value()
            self.reinit()

    def init_device_settings(self, dbus):
        super().init_device_settings(dbus)
        self.phase_item = self.settings.addSetting(
            self.settings_path + '/Phase', 0, 0, 2,
            callback=self.phase_setting_changed)
        
    def phase_setting_changed(self, service, path, value):
        if self.phase != value['Value']:
            self.phase = value['Value']
            self.sched_reinit()
        return
    
    def phase_changed(self, path, val):
        if not 0 <= val <= 2:
            return False
        self.phase_item.set_value(val)
        if self.phase != val:
            self.phase = val
            self.sched_reinit()
        return True
    
    def update_energy(self):
        pass


class Eastron_3phase(ModbusDeviceEastron,  device.CustomName, device.EnergyMeter):
    deviceEnergyForward = None
    deviceEnergyReverse = None

    def phase_regs(self, n):
        s = 2 * (n - 1)
        return [
            Reg_f32b(0x0000 + s, '/Ac/L%d/Voltage' % n,        1, _v),
            Reg_f32b(0x0006 + s, '/Ac/L%d/Current' % n,        1, _a),
            Reg_f32b(0x000c + s, '/Ac/L%d/Power' % n,          1, _w),
            Reg_f32b(0x001e + s, '/Ac/L%d/PowerFactor' % n,    1, None),
            Reg_f32b(0x015a + s, '/Ac/L%d/Energy/Forward' % n, 1, _kwh),
            Reg_f32b(0x0160 + s, '/Ac/L%d/Energy/Reverse' % n, 1, _kwh),
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
            Reg_f32b(0x0034, '/Ac/Power',             1, _w, onchange=self.power_balance),
            Reg_f32b(0x0030, '/Ac/Current',           1, _a),
            Reg_f32b(0x0046, '/Ac/Frequency',         1, _hz),
            Reg_f32b(0x0048, '/Ac/Energy/ForwardSum', 1, _kwh, onchange=self.deviceEnergyForward_changed),
            Reg_f32b(0x004a, '/Ac/Energy/ReverseSum', 1, _kwh, onchange=self.deviceEnergyReverse_changed),
        ]

        for n in range(1, phases + 1):
            regs += self.phase_regs(n)

        self.data_regs = regs
        self.nr_phases = phases
        self.last_time = time.time()
        self.energy_time = time.time() - 4
        self.balancing_time = time.time()
        self.last_power = 0

    def device_init_late(self):
        super().device_init_late()
        self.dbus.add_path('/Ac/Energy/ForwardBalancing', self.forwardBalancing_item.get_value(), writeable=True, gettextcallback=_kwh2)
        self.dbus.add_path('/Ac/Energy/ReverseBalancing', self.reverseBalancing_item.get_value(), writeable=True, gettextcallback=_kwh2)
        self.dbus.add_path('/Ac/Energy/Forward', None, writeable=True, gettextcallback=_kwh2)
        self.dbus.add_path('/Ac/Energy/Reverse', None, writeable=True, gettextcallback=_kwh2)
        self.dbus.add_path('/Ac/L1/PowerOffset', 0, writeable=True, onchangecallback=self.offset_changed)
        self.dbus.add_path('/Ac/L2/PowerOffset', 0, writeable=True, onchangecallback=self.offset_changed)
        self.dbus.add_path('/Ac/L3/PowerOffset', 0, writeable=True, onchangecallback=self.offset_changed)
        self.dbus.add_path('/DebugTXT', '', writeable=True)
        self.dbus.add_path('/EnergyCounter', self.energyCounter_item.get_value(), writeable=True, onchangecallback=self.energyCounter_changed)
        self.last_time = time.time()

    def init_device_settings(self, dbus):
        super().init_device_settings(dbus)
        self.energyCounter_item = self.settings.addSetting(self.settings_path + '/EnergyCounter', 0, 0, 2)
        self.forwardBalancing_item = self.settings.addSetting(self.settings_path + '/ForwardBalancing', 0.0, 0, 0)
        self.reverseBalancing_item = self.settings.addSetting(self.settings_path + '/ReverseBalancing', 0.0, 0, 0)

    def power_balance(self, reg):
        deltaT =  time.time() - self.last_time
        if (self.last_power > 0):
            self.dbus['/Ac/Energy/ForwardBalancing'] = float(self.dbus['/Ac/Energy/ForwardBalancing']) + (self.last_power * deltaT) / 3600000
        else:
            self.dbus['/Ac/Energy/ReverseBalancing'] = float(self.dbus['/Ac/Energy/ReverseBalancing']) + (abs(self.last_power) * deltaT) / 3600000
        self.last_time = time.time()
        self.last_power = float(copy(reg)) if reg.isvalid() else 0

    def deviceEnergyForward_changed(self, reg):
       self.deviceEnergyForward = float(copy(reg)) if reg.isvalid() else 0

    def deviceEnergyReverse_changed(self, reg):
       self.deviceEnergyReverse = float(copy(reg)) if reg.isvalid() else 0

    def update_energy(self):
        if time.time() - self.energy_time >= 5:
            if self.dbus['/EnergyCounter'] == 1:
                self.dbus['/Ac/Energy/Forward'] = self.dbus['/Ac/Energy/ForwardBalancing']
                self.dbus['/Ac/Energy/Reverse'] = self.dbus['/Ac/Energy/ReverseBalancing']
            elif self.dbus['/EnergyCounter'] == 2:
                if self.deviceEnergyForward is not None and  self.deviceEnergyReverse is not None:
                    forward_result = round(self.deviceEnergyForward - self.deviceEnergyReverse, 5)
                    self.dbus['/Ac/Energy/Forward'] = forward_result
                    self.dbus['/Ac/Energy/Reverse'] = -forward_result
            else:
                self.dbus['/Ac/Energy/Forward'] = self.deviceEnergyForward
                self.dbus['/Ac/Energy/Reverse'] = self.deviceEnergyReverse
            self.energy_time = time.time()

        if time.time() - self.balancing_time >= 300:
            self.forwardBalancing_item.set_value(self.dbus['/Ac/Energy/ForwardBalancing'])
            self.reverseBalancing_item.set_value(self.dbus['/Ac/Energy/ReverseBalancing'])
            self.balancing_time = time.time()

    def energyCounter_changed(self, path, val):
        if not 0 <= val <= 2:
            return False
        self.energyCounter_item.set_value(val)
        return True

    def offset_changed(self, path, val):
        offset1 = val if path == '/Ac/L1/PowerOffset' else self.dbus['/Ac/L1/PowerOffset']
        offset2 = val if path == '/Ac/L2/PowerOffset' else self.dbus['/Ac/L2/PowerOffset']
        offset3 = val if path == '/Ac/L3/PowerOffset' else self.dbus['/Ac/L3/PowerOffset']
        
        for r in self.data_regs:
            for s in r:
                if path == s.name + 'Offset':
                    s.offset = val
                if s.name == '/Ac/Power':
                    s.offset = offset1 + offset2 + offset3

        return True

class Eastron_SDM72DM(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'SDM72D-M'
    min_timeout = 0.5

class Eastron_SDM72DM2(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'SDM72D-M-2'
    min_timeout = 0.5

class Eastron_SDM120M(Eastron_1phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'SDM120-M'
    min_timeout = 0.5

class Eastron_SDM230M(Eastron_1phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'SDM230-Modbus'
    min_timeout = 0.5

class Eastron_SDM630M(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'SDM630-Modbus'
    min_timeout = 0.5

class Eastron_SDM630MCT(Eastron_3phase):
    productid = 0xb023 # id assigned by Victron Support
    productname = 'SDM630-MCT'
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
    136: {
        'model':    'SDM630MCT-40ma',
        'handler':  Eastron_SDM630MCT,
    },
}


probe.add_handler(probe.ModelRegister(Reg_u16(0xfc02), models,
                                      methods=['rtu','tcp'],
                                      rates=[9600, 19200, 38400],
                                      units=[1,2]))
