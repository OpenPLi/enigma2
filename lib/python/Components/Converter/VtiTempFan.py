from Components.Converter.Converter import Converter
from Components.Element import cached
from Poll import Poll
from os.path import exists, isfile
from Components.About import about

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
		temperature = 0
		if exists("/proc/stb/sensors/temp0/value"):
			f = open("/proc/stb/sensors/temp0/value", "r")
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif exists("/proc/stb/fp/temp_sensor"):
			f = open("/proc/stb/fp/temp_sensor", "r")
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif exists("/proc/stb/sensors/temp/value"):
			f = open("/proc/stb/sensors/temp/value", "r")
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif exists('/proc/stb/fp/temp_sensor_avs'):
			f = open('/proc/stb/fp/temp_sensor_avs', 'r')
			tempinfo = str(f.readline().strip())
			f.close()
			if tempinfo and int(tempinfo) > 0:
				tempinfo = _("Temp:") + tempinfo + mark + "C"
				return tempinfo

		elif exists('/proc/hisi/msp/pm_cpu'):
			with open("/proc/hisi/msp/pm_cpu") as fp:
				tempinfo = search('temperature = (\d+) degree', fp.read()).group(1)
				tempinfo = str(tempinfo.strip())
				if tempinfo and int(tempinfo) > 0:
					tempinfo = _("Temp:") + tempinfo + mark + "C"
					return tempinfo

		elif isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
			with open("/sys/devices/virtual/thermal/thermal_zone0/temp") as fp:
				temperature = int(fp.read().strip())/1000
				if temperature > 0:
					tempinfo = _("Temp:") + str(temperature) + mark + "C"
					return tempinfo

		return tempinfo

	def fanfile(self):
		fan = None
		if exists("/proc/stb/fp/fan_speed"):
			f = open("/proc/stb/fp/fan_speed", "rb")
			fan = str(f.readline().strip())
			f.close()
			if fan:
				return _("Fan:") + fan
		return _("Flash: %s MB") % about.getFlashMemory()

	def getCamName(self):
		if exists("/etc/CurrentBhCamName"):
			with open("/etc/CurrentBhCamName") as fp:
				for line in fp:
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
		elif exists("/etc/init.d/softcam"):
			with open("/etc/init.d/softcam") as fp:
				for line in fp:
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
		return ""

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)
