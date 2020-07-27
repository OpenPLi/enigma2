from Tools.Directories import SCOPE_SKIN, resolveFilename
from os.path import isfile

hw_info = None

class HardwareInfo:
	device_name = _("unavailable")
	device_model = None
	device_version = ""
	device_revision = ""
	device_hdmi = False

	def __init__(self):
		global hw_info
		if hw_info:
			return
		hw_info = self

		print "[HardwareInfo] Scanning hardware info"
		# Version
		if isfile("/proc/stb/info/version"):
			with open("/proc/stb/info/version") as fp:
				self.device_version = fp.read().strip()

		# Revision
		if isfile("/proc/stb/info/board_revision"):
			with open("/proc/stb/info/board_revision") as fp:
				self.device_revision = fp.read().strip()

		# Name ... bit odd, but history prevails
		if isfile("/proc/stb/info/model"):
			with open("/proc/stb/info/model") as fp:
				self.device_name = fp.read().strip()

		# Model
		fp = open((resolveFilename(SCOPE_SKIN, 'hw_info/hw_info.cfg')), 'r')
		for line in fp:
			if not line.startswith('#') and not line.isspace():
				l = line.strip().replace('\t', ' ')
				if ' ' in l:
					infoFname, prefix = l.split()
				else:
					infoFname = l
					prefix = ""

				if isfile("/proc/stb/info/" + infoFname):
					fd = open("/proc/stb/info/" + infoFname)
					self.device_model = prefix + fd.read().strip()
					fd.close()
					break
		fp.close()

		# standard values
		self.device_model = self.device_model or self.device_name
		self.machine_name = self.device_model

		# custom overrides for specific receivers
		if self.device_model.startswith(("et9", "et4", "et5", "et6", "et7")):
			self.machine_name = "%sx00" % self.device_model[:3]
		elif self.device_model == "et11000":
			self.machine_name = "et1x000"
		elif self.device_model.startswith("H9 "):
			self.device_name = self.device_model
			self.device_model = self.device_name.replace(" ", "").lower()
			self.machine_name = "h9combo"
		elif self.device_model.startswith("H9"):
			self.device_name = self.device_model
			self.device_model = self.device_name.lower()
			self.machine_name = "h9"

		if self.device_revision:
			self.device_string = "%s (%s-%s)" % (self.device_model, self.device_revision, self.device_version)
		elif self.device_version:
			self.device_string = "%s (%s)" % (self.device_model, self.device_version)
		else:
			self.device_string = self.device_model

		# only some early DMM boxes do not have HDMI hardware
		self.device_hdmi =  self.device_model not in ("dm800", "dm8000")

		print "Detected: " + self.get_device_string()

	def get_device_name(self):
		return hw_info.device_name

	def get_device_model(self):
		return hw_info.device_model

	def get_device_version(self):
		return hw_info.device_version

	def get_device_revision(self):
		return hw_info.device_revision

	def get_device_string(self):
		return hw_info.device_string

	def get_machine_name(self):
		return hw_info.machine_name

	def has_hdmi(self):
		return hw_info.device_hdmi
