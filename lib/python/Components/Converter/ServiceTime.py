from Components.Converter.Converter import Converter
from Components.Element import cached, ElementError
from enigma import iServiceInformation
from os import lstat, path


class ServiceTime(Converter):
	STARTTIME = 0
	ENDTIME = 1
	DURATION = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "EndTime":
			self.type = self.ENDTIME
		elif type == "StartTime":
			self.type = self.STARTTIME
		elif type == "Duration":
			self.type = self.DURATION
		else:
			raise ElementError("'%s' is not <StartTime|EndTime|Duration> for ServiceTime converter" % type)

	@cached
	def getTime(self):
		service = self.source.service
		info = self.source.info

		if not info or not service:
			return None

		if self.type == self.STARTTIME:
			time = info.getInfo(service, iServiceInformation.sTimeCreate)
			if time == -1:
				service_path = service.getPath()
				if path.isdir(service_path):
					return lstat(service_path).st_mtime
			return time
		elif self.type == self.ENDTIME:
			begin = info.getInfo(service, iServiceInformation.sTimeCreate)
			len = info.getLength(service)
			return begin + len
		elif self.type == self.DURATION:
			return info.getLength(service)

	time = property(getTime)
