try:
    from threading import Timer
    import json
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")
    
class ThermalManager():
    JSON_FIELD_POLICIES = 'policies'
    def __init__(self, polling_time = 30.0):
        self.__polling_thermal_time = polling_time
        self.__thermals = None
        self.__timer = None
        self.__chassis = None
        self.__running = False
        
    def start(self):
        if self.__running == True:
            self.work()
            self.__timer = Timer(self.__polling_thermal_time, self.start)
            self.__timer.start()

    def work(self):
        if self.__chassis is not None:
            self.__thermals = self.__chassis._thermal_list
            for term in self.__thermals:
                self.check(term)

    def check(self, sensor):
        temperature = sensor.get_temperature()
        if temperature is not None:
            temp_high = sensor.get_high_threshold()
            temp_low = sensor.get_low_threshold()
            if temperature > temp_high:
                print('Sensor ', sensor.get_name(), ' temperature more then', temp_high, '!!!')
            if temperature < temp_low:
                print('Sensor ', sensor.get_name(), ' temperature less then', temp_low, '!!!')
            
    def stop(self):
        if self.__timer is not None:
            self.__running = False
            self.__timer.cancel()

    def __del__(self):
        self.stop()

    # for compatibility with old version
    def run_policy(self, chassis_def):
        self.__chassis = chassis_def

    def get_interval(self):
        return self.__polling_thermal_time

    def initialize(self):
        pass

    def load(self, policy_file_name):
        with open(policy_file_name, 'r') as policy_file:
            json_obj = json.load(policy_file)
            if self.JSON_FIELD_POLICIES in json_obj:
                json_policies = json_obj[self.JSON_FIELD_POLICIES]
                count = 0
                for json_policy in json_policies:
                    count += 1
                if count == 0:
                    raise Exception('Policies are not exists')
            else:
                raise Exception('Policies are not exists')



    def init_thermal_algorithm(self, chassis_def):
        self.__chassis = chassis_def
        self.__running = True
        self.start()

    def deinitialize(self):
        self.stop()