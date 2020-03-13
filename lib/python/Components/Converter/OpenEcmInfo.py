from Poll import Poll
from Components.Converter.Converter import Converter
from enigma import eTimer, iPlayableService, iServiceInformation
from Components.Element import cached

try:
	from bitratecalc import eBitrateCalculator
	ISBITRATE = True
except ImportError:
	ISBITRATE = False

class OpenEcmInfo(Poll, Converter, object):
	bitrate = 0
	vbitrate = 1
	abitrate = 2
	videoBitrate = None
	audioBitrate = None
	videoBitrate_conn = None
	audioBitrate_conn = None
	video = audio = 0
	
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type
		self.poll_interval = 1000
		self.poll_enabled = True
		if type == "bitrate":
			self.type = self.bitrate
		elif type == "vbitrate":
			self.type = self.vbitrate
		elif type == "abitrate":
			self.type = self.abitrate
		self.clearData()
		self.initTimer = eTimer()
		try:
			self.initTimer.callback.append(self.initBitrateCalc)
		except:
			self.initTimer_conn = self.initTimer.timeout.connect(self.initBitrateCalc)

		
	def clearData(self):
		self.videoBitrate = None
		self.audioBitrate = None
		self.video = self.audio = 0

	def initBitrateCalc(self):
		service = self.source.service
		vpid = apid = dvbnamespace = tsid = onid = -1
		if service:
			serviceInfo = service.info()
			vpid = serviceInfo.getInfo(iServiceInformation.sVideoPID)
			apid = serviceInfo.getInfo(iServiceInformation.sAudioPID)
			tsid = serviceInfo.getInfo(iServiceInformation.sTSID)
			onid = serviceInfo.getInfo(iServiceInformation.sONID)
			dvbnamespace = serviceInfo.getInfo(iServiceInformation.sNamespace)

		if vpid > 0 and ISBITRATE and (self.type == self.vbitrate or self.type == self.bitrate):
			try:
				self.videoBitrate = eBitrateCalculator(vpid, dvbnamespace, tsid, onid, 1000, 1024*1024) 
				self.videoBitrate.callback.append(self.getVideoBitrateData)
			except:
				self.videoBitrate = eBitrateCalculator(vpid, dvbnamespace, tsid, onid, 1000, 1024*1024)
				self.videoBitrate_conn = self.videoBitrate.timeout.connect(self.getVideoBitrateData)

		if apid > 0 and ISBITRATE and (self.type == self.bitrate or self.type == self.abitrate):
			try:
				self.audioBitrate = eBitrateCalculator(apid, dvbnamespace, tsid, onid, 1000, 64*1024)
				self.audioBitrate.callback.append(self.getAudioBitrateData)
			except:
				self.audioBitrate = eBitrateCalculator(apid, dvbnamespace, tsid, onid, 1000, 64*1024)
				self.audioBitrate_conn  = self.audioBitrate.timeout.connect(self.getAudioBitrateData)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""

		if service.streamed() is not None:
			return ""
			
		if self.type == self.bitrate:
			return _("Video:") + str(self.video) + "  " + _("Audio:") + str(self.audio)

		elif self.type == self.vbitrate:
			return _("Video:") + str(self.video)

		elif self.type == self.abitrate:
			return _("Audio:") + str(self.audio)

	text = property(getText)
	
	def getVideoBitrateData(self, value, status):
		if status:
			self.video = value
		else:
			self.videoBitrate = None
			self.video = 0
		Converter.changed(self, (self.CHANGED_POLL,))

	def getAudioBitrateData(self, value, status):
		if status:
			self.audio = value
		else:
			self.audioBitrate = None
			self.audio = 0
		Converter.changed(self, (self.CHANGED_POLL,))

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC:
			if what[1] == iPlayableService.evStart:
				self.initTimer.stop
				self.initTimer.start(1000, True)
			elif what[1] == iPlayableService.evEnd:
				self.clearData()
				Converter.changed(self, what)
		elif what[0] == self.CHANGED_POLL:
			self.downstream_elements.changed(what)
