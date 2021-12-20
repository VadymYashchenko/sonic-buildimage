#!/usr/bin/env python

try:
    import sys
    from threading import Timer
    from sonic_platform_base.chassis_base import ChassisBase
    from sonic_platform.sfp import Sfp, sfp_list_get
    from sonic_platform.psu import psu_list_get
    from sonic_platform.fan_drawer import fan_drawer_list_get
    from sonic_platform.thermal import thermal_list_get
    from eeprom import Eeprom
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

class ThermalManager():
    def __init__(self, polling_time = 30.0):
        self.__polling_thermal_time = polling_time
        self.__thermals = None
        self.start()

    def start(self):
        self.work()
        self.__timer = Timer(self.__polling_thermal_time, self.start)
        self.__timer.start()

    def work(self):
        self.__thermals = thermal_list_get()
        for term in self.__thermals:
            self.check(term)

    def check(self, sensor):
        temperature = sensor.get_temperature()
        if temperature is not None:
            temp_high = sensor.get_high_threshold()
            temp_low = sensor.get_low_threshold()
            if temp_high > -999.0:
                if temperature > temp_high:
                    print('Sensor ', sensor.get_name(), ' temperature more then', temp_high, '!!!')
            else:
                print('Sensor ', sensor.get_name(), ' has no high temperature threshold')

            if temp_low > -999.0:
                if temperature < temp_low:
                    print('Sensor ', sensor.get_name(), ' temperature less then', temp_low, '!!!')
            else:
                print('Sensor ', sensor.get_name(), ' has no low temperature threshold')
            
    def stop(self):
        self.__timer.cancel()

    def __del__(self):
        self.stop()

class Chassis(ChassisBase):
    """
    Platform-specific Chassis class
    """
    def __init__(self):
        ChassisBase.__init__(self)

        self.__eeprom = None
        self.__fan_drawers = None
        self.__fan_list = None
        self.__thermals = None
        self.__psu_list = None
        self.__sfp_list = None
        self.__thermal_mngr = None
        self.__polling_thermal_time = 30

    @property
    def _eeprom(self):
        if self.__eeprom is None:
            self.__eeprom = Eeprom()
        return self.__eeprom

    @_eeprom.setter
    def _eeprom(self, value):
        pass

    @property
    def _fan_drawer_list(self):
        if self.__fan_drawers is None:
            self.__fan_drawers = fan_drawer_list_get()
        return self.__fan_drawers

    @_fan_drawer_list.setter
    def _fan_drawer_list(self, value):
        pass

    @property
    def _fan_list(self):
        if self.__fan_list is None:
            self.__fan_list = []
            for fan_drawer in self._fan_drawer_list:
                self.__fan_list.extend(fan_drawer._fan_list)
        return self.__fan_list

    @_fan_list.setter
    def _fan_list(self, value):
        pass

    @property
    def _thermal_list(self):
        if self.__thermals is None:
            self.__thermals = thermal_list_get()
        return self.__thermals

    @_thermal_list.setter
    def _thermal_list(self, value):
        pass

    @property
    def _psu_list(self):
        if self.__psu_list is None:
            self.__psu_list = psu_list_get()
        return self.__psu_list

    @_psu_list.setter
    def _psu_list(self, value):
        pass

    @property
    def _sfp_list(self):
        if self.__sfp_list is None:
            self.__sfp_list = sfp_list_get()
        return self.__sfp_list

    @_sfp_list.setter
    def _sfp_list(self, value):
        pass

    @property
    def _thermal_mngr(self):
        if self.__thermal_mngr is None:
            self.__thermal_mngr = ThermalManager(self.__polling_thermal_time)
        return self.__thermal_mngr

    @_thermal_mngr.setter
    def _thermal_mngr(self, value):
        self.__thermal_mngr = ThermalManager(value)

    def get_name(self):
        """
        Retrieves the name of the chassis
        Returns:
            string: The name of the chassis
        """
        return self._eeprom.modelstr()

    def get_presence(self):
        """
        Retrieves the presence of the chassis
        Returns:
            bool: True if chassis is present, False if not
        """
        return True

    def get_model(self):
        """
        Retrieves the model number (or part number) of the chassis
        Returns:
            string: Model/part number of chassis
        """
        return self._eeprom.part_number_str()

    def get_serial(self):
        """
        Retrieves the serial number of the chassis (Service tag)
        Returns:
            string: Serial number of chassis
        """
        return self._eeprom.serial_number_str()

    def get_revision(self):
        """
        Retrieves the revision number of the chassis (Service tag)
        Returns:
            string: Revision number of chassis
        """
        return self._eeprom.revision_str()

    def get_sfp(self, index):
        """
        Retrieves sfp represented by (1-based) index <index>

        Args:
            index: An integer, the index (1-based) of the sfp to retrieve.
                   The index should be the sequence of a physical port in a chassis,
                   starting from 1.
                   For example, 0 for Ethernet0, 1 for Ethernet4 and so on.

        Returns:
            An object dervied from SfpBase representing the specified sfp
        """
        sfp = None

        try:
            sfp = self._sfp_list[index-1]
        except IndexError:
            sys.stderr.write("SFP index {} out of range (1-{})\n".format(
                             index, len(self._sfp_list)-1))
        return sfp

    def get_status(self):
        """
        Retrieves the operational status of the chassis
        Returns:
            bool: A boolean value, True if chassis is operating properly
            False if not
        """
        return True

    def get_base_mac(self):
        """
        Retrieves the base MAC address for the chassis

        Returns:
            A string containing the MAC address in the format
            'XX:XX:XX:XX:XX:XX'
        """
        return self._eeprom.base_mac_addr()

    def get_system_eeprom_info(self):
        """
        Retrieves the full content of system EEPROM information for the chassis

        Returns:
            A dictionary where keys are the type code defined in
            OCP ONIE TlvInfo EEPROM format and values are their corresponding
            values.
        """
        return self._eeprom.system_eeprom_info()

    def get_change_event(self, timeout=0):
        ready, event_sfp = Sfp.get_transceiver_change_event(timeout)
        return ready, { 'sfp': event_sfp } if ready else {}

    def get_reboot_cause(self):
        """
        Retrieves the cause of the previous reboot

        Returns:
            A tuple (string, string) where the first element is a string
            containing the cause of the previous reboot. This string must be
            one of the predefined strings in this class. If the first string
            is "REBOOT_CAUSE_HARDWARE_OTHER", the second string can be used
            to pass a description of the reboot cause.
        """
        return self.REBOOT_CAUSE_NON_HARDWARE, ''

    def get_position_in_parent(self):
        """
        Retrieves 1-based relative physical position in parent device. If the agent cannot determine the parent-relative position
        for some reason, or if the associated value of entPhysicalContainedIn is '0', then the value '-1' is returned
        Returns:
            integer: The 1-based relative physical position in parent device or -1 if cannot determine the position
        """
        return -1

    def is_replaceable(self):
        """
        Indicate whether this device is replaceable.
        Returns:
            bool: True if it is replaceable.
        """
        return False

    def initizalize_system_led(self):
        self.system_led = ""
        return True

    def set_status_led(self, color):
        """
        Sets the state of the system LED

        Args:
            color: A string representing the color with which to set the
                   system LED

        Returns:
            bool: True if system LED state is set successfully, False if not
        """
        self.system_led = color
        return True

    def get_status_led(self):
        """
        Gets the state of the system LED

        Returns:
            A string, one of the valid LED color strings which could be vendor
            specified.
        """
        return self.system_led

    def get_thermal_manager(self):
        return self._thermal_mngr

    def __del__(self):
        self.__thermal_mngr.stop()
