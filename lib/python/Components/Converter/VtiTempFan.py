from Components.Converter.Converter import Converter
from Components.Sensors import sensors
from Components.Element import cached
from enigma import getBoxType
from Poll import Poll
import os

class VtiTempFan(Poll, Converter, object):
	TEMPINFO = 0
	FANINFO = 1
	ALL = 2
	CAMNAME = 3

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		self.type = type
		self.poll_interval = 5000
		self.poll_enabled = True
		if type == "TempInfo":
			self.type = self.TEMPINFO
		elif type == "FanInfo":
			self.type = self.FANINFO
		elif type == "AllInfo":
			self.type = self.ALL
		elif type == "CamName":
			self.type = self.CAMNAME

	@cached
	def getText(self):
		textvalue = ""
		if self.type == self.TEMPINFO:
			textvalue = self.tempfile()
		elif self.type == self.FANINFO:
			textvalue = self.fanfile()
		elif self.type == self.ALL:
			textvalue = self.tempfile() + "  " + self.fanfile()
		elif self.type == self.CAMNAME:
			textvalue = self.getCamName()
		return textvalue

	text = property(getText)

	def tempfile(self):
		tempinfo = ""
		mark = str("\xc2\xb0")
		sensor_info = None
	 	if getBoxType() not in ('dm7020hd',):
			try:
				sensor_info = sensors.getSensorsList(sensors.TYPE_TEMPERATURE)
				if sensor_info and len(sensor_info) > 0:			
					tempinfo = str(sensors.getSensorValue(sensor_info[0]))
					tempinfo = _("Temp:") + tempinfo + mark + "C"
					return tempinfo
			except:
				pass

		elif os.path.exists("/proc/stb/sensors/temp0/value"):
			f = open("/proc/stb/sensors/temp0/value", "r")
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif os.path.exists("/proc/stb/fp/temp_sensor"):
			f = open("/proc/stb/fp/temp_sensor", "r")
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif os.path.exists("/proc/stb/sensors/temp/value"):
			f = open("/proc/stb/sensors/temp/value", "r")
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif os.path.exists('/proc/stb/fp/temp_sensor_avs'):
			f = open('/proc/stb/fp/temp_sensor_avs', 'r')
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif os.path.exists('/sys/devices/virtual/thermal/thermal_zone0/temp'):
			f = open('/sys/devices/virtual/thermal/thermal_zone0/temp', 'r')
			tempinfo = f.read()
			tempinfo = tempinfo[:-4]
			tempinfo = str(tempinfo.strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif os.path.exists('/proc/hisi/msp/pm_cpu'):
			try:
				tempinfo = search('temperature = (\d+) degree', open("/proc/hisi/msp/pm_cpu").read()).group(1)
			except:
				pass
			tempinfo = str(tempinfo.strip())
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		return tempinfo

	def fanfile(self):
		fan = None
		flash_info = None
		if os.path.exists("/proc/stb/fp/fan_speed"):
			f = open("/proc/stb/fp/fan_speed", "rb")
			fan = str(f.readline().strip())
			f.close()
			if fan is not None:
				return _("Fan:") + fan

		try:
			flash_info = os.statvfs("/")
			if flash_info is not None:			
				free_flash = int((flash_info.f_frsize) * (flash_info.f_bavail) / 1024 / 1024)
				return _("Flash: %s MB") % free_flash
		except:
			pass

		return ""

	def getCamName(self):
		if os.path.exists("/etc/CurrentBhCamName"):
			try:
				for line in open("/etc/CurrentBhCamName"):
					line = line.lower()
					if "wicardd" in line:
						return "Wicardd"
					elif "incubus" in line:
						return "Incubus"
					elif "gbox" in line:
						return "Gbox"
					elif "mbox" in line:
						return "Mbox"
					elif "cccam" in line:
						return "CCcam"
					elif "oscam" in line:
						return "OScam"
					elif "camd3" in line:
						if "mgcamd" not in line:
							return "Camd3"
					elif "mgcamd" in line:
						return "Mgcamd"
					elif "gcam" in line:
						if "mgcamd" not in line:
							return "GCam"
					elif "ncam" in line:
						return "NCam"
					elif "common" in line:
						return "CI"
					elif "interface" in line:
						return "CI"
			except:
				pass
		elif os.path.exists("/etc/init.d/softcam"):
			try:
				for line in open("/etc/init.d/softcam"):
					line = line.lower()
					if "wicardd" in line:
						return "Wicardd"
					elif "incubus" in line:
						return "Incubus"
					elif "gbox" in line:
						return "Gbox"
					elif "mbox" in line:
						return "Mbox"
					elif "cccam" in line:
						return "CCcam"
					elif "oscam" in line:
						return "OScam"
					elif "camd3" in line:
						if "mgcamd" not in line:
							return "Camd3"
					elif "mgcamd" in line:
						return "Mgcamd"
					elif "gcam" in line:
						if "mgcamd" not in line:
							return "GCam"
					elif "ncam" in line:
						return "NCam"
					elif "common" in line:
						return "CI"
					elif "interface" in line:
						return "CI"
			except:
				pass
		return ""

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)
