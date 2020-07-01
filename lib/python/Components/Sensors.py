from Components.FanControl import fancontrol

class Sensors:
	# (type, name, unit, directory)
	TYPE_TEMPERATURE = 0
	# (type, name, unit, fanid)
	TYPE_FAN_RPM = 1

	def __init__(self):
		# (type, name, unit, sensor_specific_dict/list)
		self.sensors_list = []
		self.addSensors()

	def getSensorsCount(self, type = None):
		if type is None:
			return len(self.sensors_list)
		count = 0
		for sensor in self.sensors_list:
			if sensor[0] == type:
				count += 1
		return count

	# returns a list of sensorids of type "type"
	def getSensorsList(self, type = None):
		if type is None:
			return range(len(self.sensors_list))
		list = []
		for sensorid in range(len(self.sensors_list)):
			if self.sensors_list[sensorid][0] == type:
				list.append(sensorid)
		return list


	def getSensorType(self, sensorid):
		return self.sensors_list[sensorid][0]

	def getSensorName(self, sensorid):
		return self.sensors_list[sensorid][1]

	def getSensorValue(self, sensorid):
		value = -1
		sensor = self.sensors_list[sensorid]
		if sensor[0] == self.TYPE_TEMPERATURE:
			with open("%s/value" % sensor[3], "r") as fp:
				value = int(fp.readline().strip())
		elif sensor[0] == self.TYPE_FAN_RPM:
			value = fancontrol.getFanSpeed(sensor[3])
		return value

	def getSensorUnit(self, sensorid):
		return self.sensors_list[sensorid][2]

	def addSensors(self):
		import os
		if os.path.exists("/proc/stb/sensors"):
			for dirname in os.listdir("/proc/stb/sensors"):
				if dirname.find("temp", 0, 4) == 0:
					with open("/proc/stb/sensors/%s/name" % dirname, "r") as fp:
						name = fp.readline().strip()
					with open("/proc/stb/sensors/%s/unit" % dirname, "r") as fp:
						unit = fp.readline().strip()
					self.sensors_list.append((self.TYPE_TEMPERATURE, name, unit, "/proc/stb/sensors/%s" % dirname))
		for fanid in range(fancontrol.getFanCount()):
			if fancontrol.hasRPMSensor(fanid):
				self.sensors_list.append((self.TYPE_FAN_RPM, _("Fan %d") % (fanid + 1), "rpm", fanid))

sensors = Sensors()
