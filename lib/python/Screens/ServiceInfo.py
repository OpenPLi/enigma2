from Components.MenuList import MenuList
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from ServiceReference import ServiceReference
from enigma import eListboxPythonMultiContent, gFont, iServiceInformation, eServiceCenter, eDVBFrontendParametersSatellite, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Tools.Transponder import ConvertToHumanReadable
from skin import applySkinFactor, fonts, parameters


TYPE_TEXT = 0
TYPE_VALUE_HEX = 1
TYPE_VALUE_DEC = 2
TYPE_VALUE_HEX_DEC = 3
TYPE_SLIDER = 4
TYPE_VALUE_ORBIT_DEC = 5
TYPE_VALUE_FREQ = 6
TYPE_VALUE_FREQ_FLOAT = 7
TYPE_VALUE_BITRATE = 8


def to_unsigned(x):
	return x & 0xFFFFFFFF


def ServiceInfoListEntry(a, b="", valueType=TYPE_TEXT, param=4, altColor=False):
	print("b:", b)
	if not isinstance(b, str):
		if valueType == TYPE_VALUE_HEX:
			b = ("%0" + str(param) + "X") % to_unsigned(b)
		elif valueType == TYPE_VALUE_FREQ:
			b = "%s MHz" % (b / 1000)
		elif valueType == TYPE_VALUE_FREQ_FLOAT:
			b = "%.3f MHz" % (b / 1000.0)
		elif valueType == TYPE_VALUE_BITRATE:
			b = "%s KSymbols/s" % (b / 1000)
		elif valueType == TYPE_VALUE_HEX_DEC:
			b = ("%0" + str(param) + "X (%d)") % (to_unsigned(b), b)
		elif valueType == TYPE_VALUE_ORBIT_DEC:
			direction = 'E'
			if b > 1800:
				b = 3600 - b
				direction = 'W'
			b = ("%d.%d%s") % (b // 10, b % 10, direction)
		else:
			b = str(b)
	xa, ya, wa, ha = parameters.get("ServiceInfoLeft", applySkinFactor(0, 0, 300, 25))
	xb, yb, wb, hb = parameters.get("ServiceInfoRight", applySkinFactor(300, 0, 600, 25))
	color = parameters.get("ServiceInfoAltColor", (0x00FFBF00))  # alternative foreground color
	res = [True]
	if b:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, xa, ya, wa, ha, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, a))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, xb, yb, wb, hb, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, b))
	else:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, xa, ya, wa + wb, ha, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, a, color if altColor else None))  # spread horizontally
	return res


class ServiceInfoList(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, content=eListboxPythonMultiContent)
		font = fonts.get("ServiceInfo", applySkinFactor("Regular", 21, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])


TYPE_SERVICE_INFO = 1
TYPE_TRANSPONDER_INFO = 2


class ServiceInfo(Screen):
	def __init__(self, session, serviceref=None):
		Screen.__init__(self, session)

		self["infolist"] = ServiceInfoList([])
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"red": self.close,
			"green": self.ShowECMInformation,
			"yellow": self.ShowServiceInformation,
			"blue": self.ShowTransponderInformation,
			"up": self["infolist"].pageUp,
			"down": self["infolist"].pageDown,
			"left": self["infolist"].pageUp,
			"right": self["infolist"].pageDown
		}, -1)

		self.setTitle(_("Service info"))
		self["key_red"] = self["red"] = Label(_("Exit"))

		self.transponder_info = self.info = self.service = self.feinfo = self.IPTV = None
		self.show_all = True
		self.play_service = session.nav.getCurrentlyPlayingServiceReference()
		if serviceref and not (self.play_service and self.play_service == serviceref):
			self.type = TYPE_TRANSPONDER_INFO
			self.skinName = "ServiceInfoSimple"
			self.transponder_info = eServiceCenter.getInstance().info(serviceref).getInfoObject(serviceref, iServiceInformation.sTransponderData)
			# info is a iStaticServiceInformation, not a iServiceInformation
		else:
			self.type = TYPE_SERVICE_INFO
			self.service = session.nav.getCurrentService()
			if self.service:
				self.transponder_info = None
				self.info = self.service.info()
				self.feinfo = self.service.frontendInfo()
				if self.feinfo and not self.feinfo.getAll(True):
					self.feinfo = None
					serviceref = self.play_service
					self.transponder_info = serviceref and eServiceCenter.getInstance().info(serviceref).getInfoObject(serviceref, iServiceInformation.sTransponderData)
			if self.play_service:
				refstr = self.play_service.toString()
				reftype = self.play_service.type
				if "%3a//" in refstr and reftype not in (1, 257, 4098, 4114):
					self.IPTV = True
			self.audio = self.service and self.service.audioTracks()
			self.number_of_tracks = self.audio and self.audio.getNumberOfTracks() or 0
			self.sub_list = self.getSubtitleList()
			if not self.IPTV:
				self["key_green"] = self["green"] = Label(_("ECM Info"))
			if not self.IPTV or self.number_of_tracks > 1 or self.sub_list:
				self["key_yellow"] = self["yellow"] = Label(_("Service & PIDs"))
			if self.feinfo or self.transponder_info:
				self["key_blue"] = self["blue"] = Label(_("Tuner setting values"))
			else:
				self.skinName = "ServiceInfoSimple"

		self.onShown.append(self.ShowServiceInformation)

	def ShowServiceInformation(self):
		if self.type == TYPE_SERVICE_INFO:
			self["Title"].text = _("Service info - service & PIDs")
			if self.feinfo or self.transponder_info:
				self["key_blue"].text = self["blue"].text = _("Tuner setting values")
			if self.session.nav.getCurrentlyPlayingServiceOrGroup():
				name = ServiceReference(self.play_service).getServiceName()
				refstr = self.play_service.toString()
			else:
				name = _("N/A")
				refstr = _("N/A")
			resolution = "-"
			if self.info:
				from Components.Converter.PliExtraInfo import codec_data
				videocodec = codec_data.get(self.info.getInfo(iServiceInformation.sVideoType), "N/A")
				width = self.info.getInfo(iServiceInformation.sVideoWidth)
				height = self.info.getInfo(iServiceInformation.sVideoHeight)
				if width > 0 and height > 0:
					fps = (self.info.getInfo(iServiceInformation.sFrameRate) + 500) // 1000
					if fps in (0, -1):
						try:
							fps = (int(open("/proc/stb/vmpeg/0/framerate", "r").read()) + 500) // 1000
						except (ValueError, IOError):
							pass
					resolution = "%s - %dx%d - %s" % (videocodec, width, height, fps)
					resolution += (" i", " p", "")[self.info.getInfo(iServiceInformation.sProgressive)]
					aspect = self.getServiceInfoValue(iServiceInformation.sAspect)
					resolution += " - [%s]" % (aspect in (1, 2, 5, 6, 9, 0xA, 0xD, 0xE) and "4:3" or "16:9")
				gamma = ("SDR", "HDR", "HDR10", "HLG", "")[self.info.getInfo(iServiceInformation.sGamma)]
				if gamma:
					resolution += " - %s" % gamma
			self.toggle_pid_button()
			track_list = self.get_track_list()
			fillList = [
				(_("Service name"), name, TYPE_TEXT),
				(_("Videocodec, size & format"), resolution, TYPE_TEXT),
				(_("Service reference"), ":".join(refstr.split(":")[:9]) if ":/" in refstr or "%3a//" in refstr else refstr, TYPE_TEXT)
			]
			if self.IPTV:  # IPTV 4097 5001, no PIDs shown
				fillList.append((_("URL"), refstr.split(":")[10].replace("%3a", ":"), TYPE_TEXT))
				fillList.extend(track_list)
			else:
				if ":/" in refstr:  # mp4 videos, dvb-s-t recording
					fillList.append((_("Filename"), refstr.split(":")[10], TYPE_TEXT))
				else:  # fallback, movistartv, live dvb-s-t
					fillList.append((_("Provider"), self.getServiceInfoValue(iServiceInformation.sProvider), TYPE_TEXT))
					if "%3a//" in refstr:  # live dvb-s-t
						fillList.append((_("URL"), refstr.split(":")[10].replace("%3a", ":"), TYPE_TEXT))
				fillList.extend([
					(_("Namespace & Orbital pos."), self.namespace(self.getServiceInfoValue(iServiceInformation.sNamespace)), TYPE_TEXT),
					(_("TSID"), self.getServiceInfoValue(iServiceInformation.sTSID), TYPE_VALUE_HEX_DEC, 4),
					(_("ONID"), self.getServiceInfoValue(iServiceInformation.sONID), TYPE_VALUE_HEX_DEC, 4),
					(_("Service ID"), self.getServiceInfoValue(iServiceInformation.sSID), TYPE_VALUE_HEX_DEC, 4),
					(_("Video PID"), self.getServiceInfoValue(iServiceInformation.sVideoPID), TYPE_VALUE_HEX_DEC, 4)
				])
				fillList.extend(track_list)
				fillList.extend([
					(_("PCR PID"), self.getServiceInfoValue(iServiceInformation.sPCRPID), TYPE_VALUE_HEX_DEC, 4),
					(_("PMT PID"), self.getServiceInfoValue(iServiceInformation.sPMTPID), TYPE_VALUE_HEX_DEC, 4),
					(_("TXT PID"), self.getServiceInfoValue(iServiceInformation.sTXTPID), TYPE_VALUE_HEX_DEC, 4)
				])
				if self.show_all is True:
					fillList.extend(self.sub_list)

			self.fillList(fillList)
		elif self.transponder_info:
			self.fillList(self.getFEData(self.transponder_info))

	def namespace(self, nmspc):
		if isinstance(nmspc, str) or nmspc == 0:
			return None
		namespace = "%08X" % (to_unsigned(nmspc))
		if namespace[:4] == "EEEE":
			return "%s - DVB-T" % (namespace)
		elif namespace[:4] == "FFFF":
			return "%s - DVB-C" % (namespace)
		else:
			EW = "E"
			posi = int(namespace[:4], 16)
			if posi > 1800:
				posi = 3600 - posi
				EW = "W"
		return "%s - %s\xb0 %s" % (namespace, (float(posi) / 10.0), EW)

	def get_track_list(self):
		if self.number_of_tracks:
			from Components.Converter.ServiceInfo import StdAudioDesc

			def create_list(i):
				audio_desc = StdAudioDesc(self.audio.getTrackInfo(i).getDescription())
				audio_pid = self.audio.getTrackInfo(i).getPID()
				audio_lang = self.audio.getTrackInfo(i).getLanguage() or _("Not defined")
				if self.IPTV:
					return (_("Codec & lang%s") % ((" %s") % (i + 1) if self.number_of_tracks > 1 and self.show_all else ""), "%s - %s" % (audio_desc, audio_lang), TYPE_TEXT)
				else:
					return (_("Audio PID%s, codec & lang") % ((" %s") % (i + 1) if self.number_of_tracks > 1 and self.show_all else ""), "%04X (%d) - %s - %s" % (to_unsigned(audio_pid), audio_pid, audio_desc, audio_lang), TYPE_TEXT)

			if not self.show_all:
				return [create_list(self.audio.getCurrentTrack())]
			else:
				track_list = []
				for i in range(self.number_of_tracks):
					track_list.append(create_list(i))
				return track_list
		return [(_("Audio PID"), None if self.IPTV else "N/A", TYPE_TEXT)]

	def toggle_pid_button(self):
		if self.number_of_tracks > 1 or self.sub_list:
			if self.show_all is True:
				self.show_all = False
				self["key_yellow"].text = self["yellow"].text = _("Extended info") if self.IPTV else _("Extended PID info")
				self["Title"].text = _("Service info - service & Basic PID Info")
			else:
				self.show_all = True
				self["key_yellow"].text = self["yellow"].text = _("Basic info") if self.IPTV else _("Basic PID info")
				self["Title"].text = _("Service info - service & Extended PID Info")
		else:
			self.show_all = False

	def getSubtitleList(self):
		subtitle = self.service and self.service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()
		subList = []
		if subtitlelist:
			for x in subtitlelist:
				subNumber = str(x[1])
				subPID = x[1]
				subLang = ""
				subLang = x[4]

				if x[0] == 0:  # DVB PID
					subNumber = "%04X" % (x[1])
					subList += [(_("DVB Subtitles PID & lang"), "%04X (%d) - %s" % (to_unsigned(subPID), subPID, subLang), TYPE_TEXT)]

				elif x[0] == 1:  # Teletext
					subNumber = "%x%02x" % (x[3] and x[3] or 8, x[2])
					subList += [(_("TXT Subtitles page & lang"), "%s - %s" % (subNumber, subLang), TYPE_TEXT)]

				elif x[0] == 2:  # File
					types = (_("unknown"), _("embedded"), _("SSA file"), _("ASS file"),
							_("SRT file"), _("VOB file"), _("PGS file"))
					try:
						description = types[x[2]]
					except (IndexError, TypeError) as er:
						print("[ServiceInfo] Error in getSubtitleList:", er)
						description = _("unknown") + ": %s" % x[2]
					subNumber = str(int(subNumber) + 1)
					subList += [(_("Other Subtitles & lang"), "%s - %s - %s" % (subNumber, description, subLang), TYPE_TEXT)]
		return subList

	def ShowTransponderInformation(self):
		if self.type == TYPE_SERVICE_INFO and not self.IPTV:
			self.show_all = True
			self["key_yellow"].text = self["yellow"].text = _("Service & PIDs")
			frontendData = self.feinfo and self.feinfo.getAll(True)
			if frontendData:
				if self["key_blue"].text == _("Tuner setting values"):
					self["Title"].text = _("Service info - tuner setting values")
					self["key_blue"].text = self["blue"].text = _("Tuner live values")
				else:
					self["Title"].text = _("Service info - tuner live values")
					self["key_blue"].text = self["blue"].text = _("Tuner setting values")
					frontendData = self.feinfo.getAll(False)
				self.fillList(self.getFEData(frontendData))
			elif self.transponder_info:
				self["Title"].text = _("Service info - tuner setting values")
				self["key_blue"].text = self["blue"].text = _("Tuner setting values")
				self.fillList(self.getFEData(self.transponder_info))

	def getFEData(self, frontendDataOrg):
		if frontendDataOrg and len(frontendDataOrg):
			frontendData = ConvertToHumanReadable(frontendDataOrg)
			if self.transponder_info:
				tuner = (_("Type"), frontendData["tuner_type"], TYPE_TEXT)
			else:
				tuner = (_("NIM & Type"), chr(ord('A') + frontendData["tuner_number"]) + " - " + frontendData["tuner_type"], TYPE_TEXT)
			if frontendDataOrg["tuner_type"] == "DVB-S":

				def issy(x):
					return 0 if x == -1 else x

				def t2mi(x):
					return None if x == -1 else str(x)

				return (tuner,
					(_("System & Modulation"), frontendData["system"] + " " + frontendData["modulation"], TYPE_TEXT),
					(_("Orbital position"), frontendData["orbital_position"], TYPE_VALUE_DEC),
					(_("Frequency & Polarization"), _("%s MHz") % (frontendData.get("frequency", 0) / 1000) + " - " + frontendData["polarization"], TYPE_TEXT),
					(_("Symbol rate & FEC"), _("%s KSymb/s") % (frontendData.get("symbol_rate", 0) / 1000) + " - " + frontendData["fec_inner"], TYPE_TEXT),
					(_("Inversion, Pilot & Roll-off"), frontendData["inversion"] + " - " + str(frontendData.get("pilot", None)) + " - " + str(frontendData.get("rolloff", None)), TYPE_TEXT),
					(_("Input Stream ID"), issy(frontendData.get("is_id", 0)), TYPE_VALUE_DEC),
					(_("PLS Mode"), frontendData.get("pls_mode", None), TYPE_TEXT),
					(_("PLS Code"), frontendData.get("pls_code", 0), TYPE_VALUE_DEC),
					(_("T2MI PLP ID"), t2mi(frontendData.get("t2mi_plp_id", -1)), TYPE_TEXT),
					(_("T2MI PID"), None if frontendData.get("t2mi_plp_id", -1) == -1 else str(frontendData.get("t2mi_pid", eDVBFrontendParametersSatellite.T2MI_Default_Pid)), TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "DVB-C":
				return (tuner,
					(_("Modulation"), frontendData["modulation"], TYPE_TEXT),
					(_("Frequency"), frontendData.get("frequency", 0), TYPE_VALUE_FREQ_FLOAT),
					(_("Symbol rate & FEC"), _("%s KSymb/s") % (frontendData.get("symbol_rate", 0) / 1000) + " - " + frontendData["fec_inner"], TYPE_TEXT),
					(_("Inversion"), frontendData["inversion"], TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "DVB-T":
				return (tuner,
					(_("Frequency & Channel"), _("%.3f MHz") % ((frontendData.get("frequency", 0) / 1000) / 1000.0) + " - " + frontendData["channel"], TYPE_TEXT),
					(_("Inversion & Bandwidth"), frontendData["inversion"] + " - " + str(frontendData["bandwidth"]), TYPE_TEXT),
					(_("Code R. LP-HP & Guard Int."), frontendData["code_rate_lp"] + " - " + frontendData["code_rate_hp"] + " - " + frontendData["guard_interval"], TYPE_TEXT),
					(_("Constellation & FFT mode"), frontendData["constellation"] + " - " + frontendData["transmission_mode"], TYPE_TEXT),
					(_("Hierarchy info"), frontendData["hierarchy_information"], TYPE_TEXT))
			elif frontendDataOrg["tuner_type"] == "ATSC":
				return (tuner,
					(_("System & Modulation"), frontendData["system"] + " " + frontendData["modulation"], TYPE_TEXT),
					(_("Frequency"), frontendData.get("frequency", 0) / 1000, TYPE_VALUE_FREQ_FLOAT),
					(_("Inversion"), frontendData["inversion"], TYPE_TEXT))
		return []

	def fillList(self, Labels):
		tlist = []
		for item in Labels:
			if item[1]:
				value = item[1]
				if len(item) < 4:
					tlist.append(ServiceInfoListEntry(item[0] + ":", value, item[2]))
				else:
					tlist.append(ServiceInfoListEntry(item[0] + ":", value, item[2], item[3]))
		self["infolist"].setList(tlist)

	def getServiceInfoValue(self, what):
		if self.info:
			v = self.info.getInfo(what)
			if v == -2:
				v = self.info.getInfoString(what)
			elif v == -1:
				v = _("N/A")
			return v
		return ""

	def ShowECMInformation(self):
		if self.info and not self.IPTV:
			self.show_all = True
			from Components.Converter.PliExtraInfo import caid_data
			self["Title"].text = _("Service info - ECM Info")
			self["key_yellow"].text = self["yellow"].text = _("Service & PIDs")
			tlist = []
			for caid in sorted(set(self.info.getInfoObject(iServiceInformation.sCAIDPIDs)), key=lambda x: (x[0], x[1])):
				CaIdDescription = _("Undefined")
				extra_info = ""
				provid = ""
				for caid_entry in caid_data:
					if int(caid_entry[0], 16) <= caid[0] <= int(caid_entry[1], 16):
						CaIdDescription = caid_entry[2]
						break
				if caid[2]:
					if CaIdDescription == "Seca":
						provid = ",".join([caid[2][i:i + 4] for i in range(0, len(caid[2]), 30)])
					if CaIdDescription == "Nagra":
						provid = caid[2][-4:]
					if CaIdDescription == "Via":
						provid = caid[2][-6:]
					if provid:
						extra_info = "provid=%s" % provid
					else:
						extra_info = "extra data=%s" % caid[2]
				from Tools.GetEcmInfo import GetEcmInfo
				ecmdata = GetEcmInfo().getEcmData()
				formatstring = "ECMPid %04X (%d) %04X-%s %s"
				altColor = False
				if caid[0] == int(ecmdata[1], 16) and (caid[1] == int(ecmdata[3], 16) or str(int(ecmdata[2], 16)) in provid):
					formatstring = "%s (%s)" % (formatstring, _("active"))
					altColor = True
				tlist.append(ServiceInfoListEntry(formatstring % (caid[1], caid[1], caid[0], CaIdDescription, extra_info), altColor=altColor))
			if not tlist:
				tlist.append(ServiceInfoListEntry(_("No ECMPids available (FTA Service)")))
			self["infolist"].setList(tlist)
