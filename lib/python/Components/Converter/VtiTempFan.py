from Components.Converter.Converter import Converter
from Components.Element import cached
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
		if os.path.exists("/proc/stb/sensors/temp0/value"):
			f = open("/proc/stb/sensors/temp0/value", "r")
			tempinfo = str(f.readline().strip())
			f.close()
		elif os.path.exists("/proc/stb/fp/temp_sensor"):
			f = open("/proc/stb/fp/temp_sensor", "r")
			tempinfo = str(f.readline().strip())
			f.close()
		elif os.path.exists("/proc/stb/sensors/temp/value"):
			f = open("/proc/stb/sensors/temp/value", "r")
			tempinfo = str(f.readline().strip())
			f.close()
		elif os.path.exists('/proc/stb/fp/temp_sensor_avs'):
			f = open('/proc/stb/fp/temp_sensor_avs', 'r')
			tempinfo = f.read()
			f.close()
		elif os.path.exists('/sys/devices/virtual/thermal/thermal_zone0/temp'):
			try:
				f = open('/sys/devices/virtual/thermal/thermal_zone0/temp', 'r')
				tempinfo = f.read()
				tempinfo = tempinfo[:-4]
				f.close()
			except:
				tempinfo = ""
		elif os.path.exists('/proc/hisi/msp/pm_cpu'):
			try:
				tempinfo = search('temperature = (\d+) degree', open("/proc/hisi/msp/pm_cpu").read()).group(1)
			except:
				tempinfo = ""

		if tempinfo and int(tempinfo) > 0:
			mark = str("\xc2\xb0")
			tempinfo = _("Temp:") + tempinfo.replace('\n', '').replace(' ','') + mark + "C"
		return tempinfo

	def fanfile(self):
		fan = ""
		if os.path.exists("/proc/stb/fp/fan_speed"):
			f = open("/proc/stb/fp/fan_speed", "rb")
			fan = str(f.readline().strip())
			f.close()
		return fan

	def getCamName(self):
		camnameinfo = ""
		if os.path.exists("/etc/CurrentBhCamName"):
			try:
				for line in open("/etc/CurrentBhCamName"):
					line = line.lower()
					if "wicardd" in line:
						camnameinfo = "Wicardd"
					elif "incubus" in line:
						camnameinfo = "Incubus"
					elif "gbox" in line:
						camnameinfo = "Gbox"
					elif "mbox" in line:
						camnameinfo = "Mbox"
					elif "cccam" in line:
						camnameinfo = "CCcam"
					elif "oscam" in line:
						camnameinfo = "OScam"
					elif "camd3" in line:
						camnameinfo = "Camd3"
					elif "mgcamd" in line:
						camnameinfo = "Mgcamd"
					elif "gcam" in line:
						camnameinfo = "GCam"
					elif "ncam" in line:
						camnameinfo = "NCam"
					elif "common" in line:
						camnameinfo = "CI"
					elif "interface" in line:
						camnameinfo = "CI"
					if camnameinfo:
						return camnameinfo
			except:
				pass
		elif os.path.exists("/etc/init.d/softcam"):
			try:
				for line in open("/etc/init.d/softcam"):
					line = line.lower()
					if "wicardd" in line:
						camnameinfo = "Wicardd"
					elif "incubus" in line:
						camnameinfo = "Incubus"
					elif "gbox" in line:
						camnameinfo = "Gbox"
					elif "mbox" in line:
						camnameinfo = "Mbox"
					elif "cccam" in line:
						camnameinfo = "CCcam"
					elif "oscam" in line:
						camnameinfo = "OScam"
					elif "camd3" in line:
						camnameinfo = "Camd3"
					elif "mgcamd" in line:
						camnameinfo = "Mgcamd"
					elif "gcam" in line:
						camnameinfo = "GCam"
					elif "ncam" in line:
						camnameinfo = "NCam"
					elif "common" in line:
						camnameinfo = "CI"
					elif "interface" in line:
						camnameinfo = "CI"
					if camnameinfo:
						return camnameinfo
			except:
				pass
		return camnameinfo

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)
