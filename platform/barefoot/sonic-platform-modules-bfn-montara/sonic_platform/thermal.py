try:
    import subprocess
    from collections import namedtuple
    from bfn_extensions.platform_sensors import platform_sensors_get
    from sonic_platform_base.thermal_base import ThermalBase
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

'''
data argument is in "sensors -A -u" format, example:
coretemp-isa-0000
Package id 0:
  temp1_input: 37.000
  temp1_max: 82.000
  temp1_crit: 104.000
  temp1_crit_alarm: 0.000
Core 0:
  temp2_input: 37.000
  ...
'''

Threshold = namedtuple('Threshold', ['crit', 'max', 'min', 'alarm'], defaults=[0.1]*4)

def _sensors_chip_parsed(data: str):
    def kv(line):
        k, v, *_ = [t.strip(': ') for t in line.split(':') if t] + ['']
        return k, v

    chip, *data = data.strip().split('\n')
    chip = chip.strip(': ')

    sensors = []
    for line in data:
        if not line.startswith(' '):
            sensor_label = line.strip(': ')
            sensors.append((sensor_label, {}))
            continue

        if len(sensors) == 0:
            raise RuntimeError(f'invalid data to parse: {data}')

        attr, value = kv(line)
        sensor_label, sensor_data = sensors[-1]
        sensor_data.update({attr: value})

    return chip, dict(sensors)

'''
Example of returned dict:
{
    'coretemp-isa-0000': {
        'Core 1': { "temp1_input": 40, ...  },
        'Core 2': { ... }
    }
}
'''
def _sensors_get() -> dict:
    data = platform_sensors_get(['-A', '-u']) or ''
    data += subprocess.check_output("/usr/bin/sensors -A -u",
                shell=True, text=True)
    data = data.split('\n\n')
    data = [_sensors_chip_parsed(chip_data) for chip_data in data if chip_data]
    data = dict(data)
    return data

def _value_get(d: dict, key_prefix, key_suffix=''):
    for k, v in d.items():
        if k.startswith(key_prefix) and k.endswith(key_suffix):
            return v
    return None

# Thermal -> ThermalBase -> DeviceBase
class Thermal(ThermalBase):
    _thresholds = {
            "com_e_driver-i2c-4-33:memory-temp": Threshold(85.0, 80.75, 0.2, 0.1),
            "com_e_driver-i2c-4-33:cpu-temp":    Threshold(99.9, 99.75, 0.2, 0.1),
            "psu_driver-i2c-7-5a:psu1-temp1":    Threshold(50.0, 47.5, 0.2, 0.1),
            "psu_driver-i2c-7-5a:psu1-temp2":    Threshold(90.0, 85.5, 0.2, 0.1),
            "psu_driver-i2c-7-5a:psu1-temp3":    Threshold(50.0, 47.5, 0.2, 0.1),
            "tmp75-i2c-3-48:chip-temp":          Threshold(90.0, 85.5, 0.2, 0.1),
            "tmp75-i2c-3-49:exhaust2-temp":      Threshold(80.0, 76.0, 0.2, 0.1),
            "tmp75-i2c-3-4a:exhaust-temp":       Threshold(60.0, 57.0, 0.2, 0.1),
            "tmp75-i2c-3-4b:intake-temp":        Threshold(60.0, 57.0, 0.2, 0.1),
            "tmp75-i2c-3-4c:tofino-temp":        Threshold(99.9, 99.75, 0.2, 0.1),
            "tmp75-i2c-3-4d:intake2-temp":       Threshold(60.0, 57.0, 0.2, 0.1),
            "coretemp-isa-0000:package-id-0":    Threshold(80.0, 76.0, 0.2, 0.1),
            "coretemp-isa-0000:core-0":          Threshold(99.9, 82.0, 0.2, 0.1),
            "coretemp-isa-0000:core-1":          Threshold(99.9, 82.0, 0.2, 0.1),
            "coretemp-isa-0000:core-2":          Threshold(99.9, 82.0, 0.2, 0.1),
            "coretemp-isa-0000:core-3":          Threshold(99.9, 82.0, 0.2, 0.1),
            # add from Montara"
            "psu_driver-i2c-7-59:psu2-temp1":    Threshold(50.0, 47.5, 0.2, 0.1),
            "psu_driver-i2c-7-59:psu2-temp2":    Threshold(90.0, 85.5, 0.2, 0.1),
            "tmp75-i2c-8-48:outlet-right-temp":  Threshold(60.0, 57.0, 0.2, 0.1),
            "tmp75-i2c-8-49:outlet-left-temp":   Threshold(60.0, 57.0, 0.2, 0.1)
    }

    def __init__(self, chip, label, index = 0):
        self.__chip = chip
        self.__label = label
        self.__name = f"{chip}:{label}".lower().replace(' ', '-')
        self.__collect_temp = []
        self.__index = index

    def __get(self, attr_prefix, attr_suffix):
        sensor_data = _sensors_get().get(self.__chip, {}).get(self.__label, {})
        value = _value_get(sensor_data, attr_prefix, attr_suffix)
        if value is not None:
            return value
        elif attr_prefix == 'temp':
            if attr_suffix == 'crit':
                return self._thresholds[self.__name].crit
            elif attr_suffix == 'max':
                return self._thresholds[self.__name].max
            elif attr_suffix == 'min':
                return self._thresholds[self.__name].min
            elif attr_suffix == 'alarm':
                return self._thresholds[self.__name].alarm
            else:
                return 1.0
        else:
            return 0.1

    # ThermalBase interface methods:
    def get_temperature(self) -> float:
        temp = self.__get('temp', 'input')
        self.__collect_temp.append(float(temp))
        self.__collect_temp.sort()
        if len(self.__collect_temp) == 3:
            del self.__collect_temp[1]
        return float(temp)

    def get_high_threshold(self) -> float:
        return float(self.__get('temp', 'max'))

    def get_high_critical_threshold(self) -> float:
        return float(self.__get('temp', 'crit'))

    def get_low_critical_threshold(self) -> float:
        return float(self.__get('temp', 'alarm'))

    def get_model(self):
        return f"{self.__label}".lower()

    # DeviceBase interface methods:
    def get_name(self):
        return self.__name

    def get_presence(self):
        return True

    def get_status(self):
        return True

    def is_replaceable(self):
        return False

    def get_low_threshold(self) -> float:
        return float(self.__get('temp', 'min'))

    def get_serial(self):
        return 'N/A'

    def get_minimum_recorded(self) -> float:
        temp = self.__collect_temp[0] if len(self.__collect_temp) > 0 else 36.6
        temp = temp if temp <= 100.0 else 100.0
        temp = temp if temp > 0.0 else 0.1
        return float(temp)

    def get_maximum_recorded(self) -> float:
        temp = self.__collect_temp[-1] if len(self.__collect_temp) > 0 else 36.6
        temp = temp if temp <= 100.0 else 100.0
        temp = temp if temp > 0.0 else 0.1
        return float(temp)

    def get_position_in_parent(self):
        return self.__index

    def set_high_threshold(self, temperature):
        return False

    def set_low_threshold(self, temperature):
        return False

def thermal_list_get():
    l = []
    index = 0
    for chip, chip_data in _sensors_get().items():
        for sensor, sensor_data in chip_data.items():
            # add only temperature sensors
            if _value_get(sensor_data, "temp") is not None:
                l.append(Thermal(chip, sensor, index))
                index += 1
    return l
