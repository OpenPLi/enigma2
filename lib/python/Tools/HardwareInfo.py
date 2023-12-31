from Tools.Directories import SCOPE_SKIN, resolveFilename
from Components.SystemInfo import BoxInfo

hw_info = None


class HardwareInfo:
	device_name = _("unavailable")
	device_brandname = None
	device_version = ""
	device_revision = ""
	device_hdmi = False

	def __init__(self):
		global hw_info
		if hw_info:
			return
		hw_info = self

		print("[HardwareInfo] Scanning hardware info")
		# Version
		try:
			self.device_version = open("/proc/stb/info/version").read().strip()
		except:
			pass

		# Revision
		try:
			self.device_revision = open("/proc/stb/info/board_revision").read().strip()
		except:
			pass

		# Name ... bit odd, but history prevails
		try:
			self.device_name = open("/proc/stb/info/model").read().strip()
		except:
			pass

		# Brandname ... bit odd, but history prevails
		self.device_brandname = BoxInfo.getItem("displaybrand")

		# standard values
		self.device_model = self.machine_name = BoxInfo.getItem("machine")
		self.device_hw = BoxInfo.getItem("displaymodel")

		if self.device_revision:
			self.device_string = "%s (%s-%s)" % (self.device_hw, self.device_revision, self.device_version)
		elif self.device_version:
			self.device_string = "%s (%s)" % (self.device_hw, self.device_version)
		else:
			self.device_string = self.device_hw

		self.device_hdmi = BoxInfo.getItem('hdmi')

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
