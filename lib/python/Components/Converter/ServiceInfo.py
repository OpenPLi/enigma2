from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Screens.InfoBarGenerics import hasActiveSubservicesForCurrentChannel
from Components.Element import cached


WIDESCREEN = [3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10]


def StdAudioDesc(description):
	if not description:
		return ""

	REPLACEMENTS = (
		("A_", ""),
		("AC-3", "AC3"),
		("(ATSC A/52)", ""),
		("(ATSC A/52B)", ""),
		("MPEG-1 Layer 2 (MP2)", "MP2"),
		(" Layer 2 (MP2)", ""),
		(" Layer 3 (MP3)", "MP3"),
		("-1", ""),
		("-2", ""),
		("2-", ""),
		("MPEG-4 AAC", "AAC"),
		("-4 AAC", "AAC"),
		("4-AAC", "HE-AAC"),
		("audio", ""),
		("/L3", ""),
		("/mpeg", "AAC"),
		("/x-", ""),
		("raw", "Dolby TrueHD"),
		("E-AC3", "AC3+"),
		("EAC3", "AC3+"),
		("IPCM", "AC3"),
		("LPCM", "AC3+"),
		("AAC_PLUS", "AAC+"),
		("AAC_LATM", "AAC"),
		("WMA/PRO", "WMA Pro"),
		("MPEG", "MPEG1 Layer II"),
		("MPEG1 Layer II AAC", "AAC"),
		("MPEG1 Layer IIAAC", "AAC"),
		("MPEG1 Layer IIMP3", "MP3"),
	)

	for orig, repl in REPLACEMENTS:
		description = description.replace(orig, repl)
	return description

def getVideoHeight(info):
	return info.getInfo(iServiceInformation.sVideoHeight)


class ServiceInfo(Converter):
	HAS_TELETEXT = 0
	IS_MULTICHANNEL = 1
	IS_CRYPTED = 2
	IS_WIDESCREEN = 3
	SUBSERVICES_AVAILABLE = 4
	XRES = 5
	YRES = 6
	APID = 7
	VPID = 8
	PCRPID = 9
	PMTPID = 10
	TXTPID = 11
	TSID = 12
	ONID = 13
	SID = 14
	FRAMERATE = 15
	TRANSFERBPS = 16
	HAS_HBBTV = 17
	AUDIOTRACKS_AVAILABLE = 18
	SUBTITLES_AVAILABLE = 19
	EDITMODE = 20
	IS_STREAM = 21
	IS_SD = 22
	IS_HD = 23
	IS_SD_AND_WIDESCREEN = 24
	IS_SD_AND_NOT_WIDESCREEN = 25
	IS_4K = 26
	IS_STEREO = 27
	IS_NOT_WIDESCREEN = 28
	IS_1080 = 29
	IS_720 = 30
	IS_SDR = 31
	IS_HDR = 32
	IS_HDR10 = 33
	IS_HLG = 34
	IS_VIDEO_MPEG2 = 35
	IS_VIDEO_AVC = 36
	IS_VIDEO_HEVC = 37

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type, self.interesting_events = {
				"HasTelext": (self.HAS_TELETEXT, (iPlayableService.evUpdatedInfo,)),
				"IsMultichannel": (self.IS_MULTICHANNEL, (iPlayableService.evUpdatedInfo,)),
				"IsStereo": (self.IS_STEREO, (iPlayableService.evUpdatedInfo,)),
				"IsCrypted": (self.IS_CRYPTED, (iPlayableService.evUpdatedInfo,)),
				"IsWidescreen": (self.IS_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
				"IsNotWidescreen": (self.IS_NOT_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
				"SubservicesAvailable": (self.SUBSERVICES_AVAILABLE, (iPlayableService.evStart,)),
				"VideoWidth": (self.XRES, (iPlayableService.evVideoSizeChanged,)),
				"VideoHeight": (self.YRES, (iPlayableService.evVideoSizeChanged,)),
				"AudioPid": (self.APID, (iPlayableService.evUpdatedInfo,)),
				"VideoPid": (self.VPID, (iPlayableService.evUpdatedInfo,)),
				"PcrPid": (self.PCRPID, (iPlayableService.evUpdatedInfo,)),
				"PmtPid": (self.PMTPID, (iPlayableService.evUpdatedInfo,)),
				"TxtPid": (self.TXTPID, (iPlayableService.evUpdatedInfo,)),
				"TsId": (self.TSID, (iPlayableService.evUpdatedInfo,)),
				"OnId": (self.ONID, (iPlayableService.evUpdatedInfo,)),
				"Sid": (self.SID, (iPlayableService.evUpdatedInfo,)),
				"Framerate": (self.FRAMERATE, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
				"TransferBPS": (self.TRANSFERBPS, (iPlayableService.evUpdatedInfo)),
				"HasHBBTV": (self.HAS_HBBTV, (iPlayableService.evUpdatedInfo, iPlayableService.evHBBTVInfo, iPlayableService.evStart)),
				"AudioTracksAvailable": (self.AUDIOTRACKS_AVAILABLE, (iPlayableService.evUpdatedInfo, iPlayableService.evStart)),
				"SubtitlesAvailable": (self.SUBTITLES_AVAILABLE, (iPlayableService.evUpdatedInfo, iPlayableService.evStart)),
				"Editmode": (self.EDITMODE, (iPlayableService.evUpdatedInfo, iPlayableService.evStart)),
				"IsStream": (self.IS_STREAM, (iPlayableService.evUpdatedInfo, iPlayableService.evStart)),
				"IsSD": (self.IS_SD, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo, iPlayableService.evStart)),
				"IsHD": (self.IS_HD, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo, iPlayableService.evStart)),
				"IsSDAndWidescreen": (self.IS_SD_AND_WIDESCREEN, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
				"IsSDAndNotWidescreen": (self.IS_SD_AND_NOT_WIDESCREEN, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
				"Is4K": (self.IS_4K, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
				"Is1080": (self.IS_1080, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
				"Is720": (self.IS_720, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
				"IsSDR": (self.IS_SDR, (iPlayableService.evVideoGammaChanged, iPlayableService.evUpdatedInfo)),
				"IsHDR": (self.IS_HDR, (iPlayableService.evVideoGammaChanged, iPlayableService.evUpdatedInfo)),
				"IsHDR10": (self.IS_HDR10, (iPlayableService.evVideoGammaChanged, iPlayableService.evUpdatedInfo)),
				"IsHLG": (self.IS_HLG, (iPlayableService.evVideoGammaChanged, iPlayableService.evUpdatedInfo)),
				"IsVideoMPEG2": (self.IS_VIDEO_MPEG2, (iPlayableService.evUpdatedInfo,)),
				"IsVideoAVC": (self.IS_VIDEO_AVC, (iPlayableService.evUpdatedInfo,)),
				"IsVideoHEVC": (self.IS_VIDEO_HEVC, (iPlayableService.evUpdatedInfo,)),
			}[type]
		if self.type in (self.IS_SD, self.IS_HD, self.IS_SD_AND_WIDESCREEN, self.IS_SD_AND_NOT_WIDESCREEN, self.IS_4K, self.IS_1080, self.IS_720):
			self.videoHeight = 0
			if self.type in (self.IS_SD_AND_WIDESCREEN, self.IS_SD_AND_NOT_WIDESCREEN):
				self.aspect = 0

	def isVideoService(self, info):
		serviceInfo = info.getInfoString(iServiceInformation.sServiceref).split(':')
		return len(serviceInfo) < 3 or serviceInfo[2] != '2'

	def getServiceInfoString(self, info, what, convert=lambda x: "%d" % x):
		v = info.getInfo(what)
		if v == -1:
			return _("N/A")
		if v == -2:
			return info.getInfoString(what)
		return convert(v)

	@cached
	def getBoolean(self):
		service = self.source.service
		info = service and service.info()
		if info:
			if self.type == self.HAS_TELETEXT:
				tpid = info.getInfo(iServiceInformation.sTXTPID)
				return tpid != -1
			elif self.type in (self.IS_MULTICHANNEL, self.IS_STEREO):
				# FIXME. but currently iAudioTrackInfo doesn't provide more information.
				audio = service.audioTracks()
				if audio:
					n = audio.getNumberOfTracks()
					idx = 0
					while idx < n:
						i = audio.getTrackInfo(idx)
						description = StdAudioDesc(i.getDescription())
						if description and description.split()[0] in ("AC4", "AAC+", "AC3", "AC3+", "Dolby", "DTS", "DTS-HD", "HE-AAC", "WMA"):
							if self.type == self.IS_MULTICHANNEL:
								return True
							elif self.type == self.IS_STEREO:
								return False
						idx += 1
					if self.type == self.IS_MULTICHANNEL:
						return False
					elif self.type == self.IS_STEREO:
						return True
				return False
			elif self.type == self.IS_CRYPTED:
				return info.getInfo(iServiceInformation.sIsCrypted) == 1
			elif self.type == self.SUBSERVICES_AVAILABLE:
				return hasActiveSubservicesForCurrentChannel(service)
			elif self.type == self.HAS_HBBTV:
				return info.getInfoString(iServiceInformation.sHBBTVUrl) != ""
			elif self.type == self.AUDIOTRACKS_AVAILABLE:
				audio = service.audioTracks()
				return bool(audio and audio.getNumberOfTracks() > 1)
			elif self.type == self.SUBTITLES_AVAILABLE:
				subtitle = service and service.subtitle()
				return bool(subtitle and subtitle.getSubtitleList())
			elif self.type == self.EDITMODE:
				return bool(hasattr(self.source, "editmode") and self.source.editmode)
			elif self.type == self.IS_STREAM:
				return service.streamed() is not None
			elif self.isVideoService(info):
				if self.type == self.IS_SDR:
					return info.getInfo(iServiceInformation.sGamma) == 0
				elif self.type == self.IS_HDR:
					return info.getInfo(iServiceInformation.sGamma) == 1
				elif self.type == self.IS_HDR10:
					return info.getInfo(iServiceInformation.sGamma) == 2
				elif self.type == self.IS_HLG:
					return info.getInfo(iServiceInformation.sGamma) == 3
				elif self.type == self.IS_WIDESCREEN:
					return info.getInfo(iServiceInformation.sAspect) in WIDESCREEN
				elif self.type == self.IS_NOT_WIDESCREEN:
					return info.getInfo(iServiceInformation.sAspect) not in WIDESCREEN
				elif self.type == self.IS_VIDEO_MPEG2:
					return info.getInfo(iServiceInformation.sVideoType) == 0
				elif self.type == self.IS_VIDEO_AVC:
					return info.getInfo(iServiceInformation.sVideoType) == 1
				elif self.type == self.IS_VIDEO_HEVC:
					return info.getInfo(iServiceInformation.sVideoType) == 7
				else:
					videoHeight = info.getInfo(iServiceInformation.sVideoHeight)
					self.videoHeight = videoHeight if videoHeight > 0 else self.videoHeight
					if self.type == self.IS_SD:
						return self.videoHeight and self.videoHeight < 720
					elif self.type == self.IS_HD:
						return self.videoHeight >= 720 and self.videoHeight < 1500
					elif self.type == self.IS_4K:
						return self.videoHeight >= 1500
					elif self.type == self.IS_1080:
						return self.videoHeight > 1000 and self.videoHeight <= 1080
					elif self.type == self.IS_720:
						return self.videoHeight == 720
					else:
						aspect = info.getInfo(iServiceInformation.sAspect)
						self.aspect = aspect if aspect > -1 else self.aspect
						if self.type == self.IS_SD_AND_WIDESCREEN:
							return self.videoHeight and self.aspect and self.videoHeight < 720 and self.aspect in WIDESCREEN
						if self.type == self.IS_SD_AND_NOT_WIDESCREEN:
							return self.videoHeight and self.aspect and self.videoHeight < 720 and self.aspect not in WIDESCREEN
		return False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if info:
			if self.type == self.APID:
				return self.getServiceInfoString(info, iServiceInformation.sAudioPID)
			elif self.type == self.PCRPID:
				return self.getServiceInfoString(info, iServiceInformation.sPCRPID)
			elif self.type == self.PMTPID:
				return self.getServiceInfoString(info, iServiceInformation.sPMTPID)
			elif self.type == self.TXTPID:
				return self.getServiceInfoString(info, iServiceInformation.sTXTPID)
			elif self.type == self.TSID:
				return self.getServiceInfoString(info, iServiceInformation.sTSID)
			elif self.type == self.ONID:
				return self.getServiceInfoString(info, iServiceInformation.sONID)
			elif self.type == self.SID:
				return self.getServiceInfoString(info, iServiceInformation.sSID)
			elif self.type == self.TRANSFERBPS:
				return self.getServiceInfoString(info, iServiceInformation.sTransferBPS, lambda x: _("%d kB/s") % (x / 1024))
			elif self.type == self.HAS_HBBTV:
				return info.getInfoString(iServiceInformation.sHBBTVUrl)
			elif self.isVideoService(info):
				if self.type == self.XRES:
					return self.getServiceInfoString(info, iServiceInformation.sVideoWidth)
				elif self.type == self.YRES:
					return self.getServiceInfoString(info, iServiceInformation.sVideoHeight)
				elif self.type == self.FRAMERATE:
					return self.getServiceInfoString(info, iServiceInformation.sFrameRate, lambda x: _("%d fps") % ((x + 500) / 1000))
				elif self.type == self.VPID:
					return self.getServiceInfoString(info, iServiceInformation.sVideoPID)
		return ""

	text = property(getText)

	@cached
	def getValue(self):
		service = self.source.service
		info = service and service.info()
		if info and self.isVideoService(info):
			if self.type == self.XRES:
				return info.getInfo(iServiceInformation.sVideoWidth)
			if self.type == self.YRES:
				return info.getInfo(iServiceInformation.sVideoHeight)
			if self.type == self.FRAMERATE:
				return info.getInfo(iServiceInformation.sFrameRate)
		return -1

	value = property(getValue)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
