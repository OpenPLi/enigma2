from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, BT_ALIGN_CENTER, iPlayableService, iRecordableService, eServiceReference, iServiceInformation, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_HALIGN_CENTER, eTimer, getDesktop, eSize

from skin import parseScale, applySkinFactor, parseColor, parseFont

from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Converter.ServiceInfo import getVideoHeight
from Components.Converter.VAudioInfo import StdAudioDesc
from Components.Converter.PliExtraInfo import createCurrentCaidLabel
from Components.Label import Label

from Components.config import config

from Screens.InfoBarGenerics import hasActiveSubservicesForCurrentChannel

from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap

import NavigationInstance


class ServiceInfoBar(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.nav = NavigationInstance.instance
		self.nav.record_event.append(self.gotRecordEvent)
		self.elements = []
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(36)
		self.l.setItemWidth(36)
		self.spacing = applySkinFactor(10)
		self.orientations = {"orHorizontal": eListbox.orHorizontal, "orVertical": eListbox.orVertical}
		self.orientation = eListbox.orHorizontal
		self.alignment = "left"
		self.pixmaps = {}
		self.pixmapsDisabled = {}
		self.separatorLineColor = 0xC0C0C0
		self.foreColor = 0xFFFFFF
		self.separatorLineThickness = 0
		self.autoresizeMode = "auto" # possible values: auto, fixed, condensed 
		self.font = gFont("Regular", 18)
		self.__event_tracker = None
		self.current_crypto = "---"
		self.refreshCryptoInfo = eTimer()
		self.refreshCryptoInfo.callback.append(self.checkCrypto_update)
		self.refreshAddon = eTimer()
		self.refreshAddon.callback.append(self.updateAddon)
		self.textRenderer = Label("")
		self.prevElement = None
		self.lastElement = None
		self.permanentIcons = []
		self.records_running = 0
		
		

	def onContainerShown(self):
		self.textRenderer.GUIcreate(self.relatedScreen.instance)
		self.l.setItemHeight(self.instance.size().height())
		self.l.setItemWidth(self.instance.size().width())
		self.updateAddon()
		if not self.__event_tracker:
			self.__event_tracker = ServiceEventTracker(screen=self.relatedScreen,
				eventmap={
					iPlayableService.evStart: self.updateAddon,
					iPlayableService.evEnd: self.updateAddon,
					iPlayableService.evUpdatedInfo: self.updateAddon,
					iPlayableService.evVideoSizeChanged: self.updateAddon,
					iPlayableService.evHBBTVInfo: self.updateAddon
				}
			)
			
	def destroy(self):
		self.nav.record_event.remove(self.gotRecordEvent)
		self.refreshCryptoInfo.stop()
		self.refreshAddon.stop()
		self.refreshCryptoInfo.callback.remove(self.checkCrypto_update)
		self.refreshAddon.callback.remove(self.updateAddon)
		GUIAddon.destroy(self)

	GUI_WIDGET = eListbox
	
	def gotRecordEvent(self, service, event):
		prev_records = self.records_running
		if event in (iRecordableService.evEnd, iRecordableService.evStart, None):
			recs = self.nav.getRecordings()
			self.records_running = len(recs)
			if self.records_running != prev_records:
				self.updateAddon()
	
	def scheduleAddonUpdate(self):
		self.refreshAddon.stop()
		self.refreshAddon.start(1000)
	
	def checkCrypto_update(self):
		if NavigationInstance.instance is not None:
			service = NavigationInstance.instance.getCurrentService()
			info = service and service.info()
			if info:
				new_crypto = createCurrentCaidLabel(info)
				if new_crypto != self.current_crypto:
					self.current_crypto = new_crypto
					self.updateAddon()

	def updateAddon(self):
		self.refreshAddon.stop()
		l_list = []
		l_list.append((self.elements,))
		self.l.setList(l_list)

	def detectVisible(self, key):
		if self.nav is not None:
			service = self.nav.getCurrentService()
			info = service and service.info()
			isRef = isinstance(service, eServiceReference)
			#self.current_info = info
			if not info:
				return None
			video_height = None
			video_aspect = None
			video_height = getVideoHeight(info)
			if key == "videoRes":
				if video_height >= 720 and video_height < 1500:
					return "IS_HD"
				elif video_height >= 1500:
					return "IS_4K"
				else:
					return "IS_SD"
			elif key == "txt":
				tpid = info.getInfo(iServiceInformation.sTXTPID)
				if tpid > 0:
					return key
			elif key == "dolby" and not isRef:
				audio = service.audioTracks()
				if audio:
					n = audio.getNumberOfTracks()
					idx = 0
					while idx < n:
						i = audio.getTrackInfo(idx)
						description = StdAudioDesc(i.getDescription())
						if description and description.split()[0] in ("AC4", "AAC+", "AC3", "AC3+", "Dolby", "DTS", "DTS-HD", "HE-AAC", "IPCM", "LPCM", "WMA Pro"):
							return key
						idx += 1
			elif key == "crypt" and not isRef:
				if info.getInfo(iServiceInformation.sIsCrypted) == 1:
					return key
			elif key == "audiotrack" and not isRef:
				audio = service.audioTracks()
				if bool(audio) and audio.getNumberOfTracks() > 1:
					return key
			elif key == "subtitletrack" and not isRef:
				subtitle = service and service.subtitle()
				subtitlelist = subtitle and subtitle.getSubtitleList()
				if subtitlelist and len(subtitlelist) > 0:
					return key
			elif key == "hbbtv" and not isRef:
				if info.getInfoString(iServiceInformation.sHBBTVUrl) != "":
					return key
			elif key == "subservices" and not isRef:
				sRef = info.getInfoString(iServiceInformation.sServiceref)
				url = "http://%s:%s/" % (config.misc.softcam_streamrelay_url.getHTML(), config.misc.softcam_streamrelay_port.value)
				splittedRef = sRef.split(url.replace(":", "%3a"))
				if len(splittedRef) > 1:
					sRef = splittedRef[1].split(":")[0].replace("%3a", ":")
				if hasActiveSubservicesForCurrentChannel(sRef):
					return key
			elif key == "stream" and not isRef:
				if service.streamed() is not None:
					return key
			elif key == "currentCrypto" and not isRef:
				self.current_crypto = createCurrentCaidLabel(info)
				self.refreshCryptoInfo.start(1000)
				return key
			elif key == "record":
				self.gotRecordEvent(None, None)
				if self.records_running > 0:
					return key
		return None

	def buildEntry(self, sequence):
		xPos = self.instance.size().width() if self.alignment == "right" else 0
		yPos = 0

		res = [None]

		for x in sequence:
			enabledKey = self.detectVisible(x) if x != "separator" else "separator"
			pic = None
			if enabledKey:
				if enabledKey in self.pixmaps:
					pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[enabledKey]))
			elif self.autoresizeMode in ["auto", "fixed"] or x in self.permanentIcons:
				if x == "videoRes":
					enabledKey = "IS_SD"
					if enabledKey in self.pixmaps:
						pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[enabledKey]))
				if x in self.pixmapsDisabled:
					pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmapsDisabled[x]))

			if enabledKey or self.autoresizeMode in ["auto", "fixed"] or x in self.permanentIcons:
				if enabledKey != "separator" and enabledKey != "currentCrypto":
					if pic:
						pixd_size = pic.size()
						pixd_width = pixd_size.width()
						pixd_height = pixd_size.height()
						pic_x_pos = (xPos - pixd_width) if self.alignment == "right" else xPos
						pic_y_pos = yPos + (self.instance.size().height() - pixd_height) // 2
						res.append(MultiContentEntryPixmapAlphaBlend(
							pos=(pic_x_pos, pic_y_pos),
							size=(pixd_width, pixd_height),
							png=pic,
							backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
						if self.alignment == "right":
							xPos -= pixd_width + self.spacing
						else:
							xPos += pixd_width + self.spacing
				else:
					if enabledKey == "separator":
						if self.lastElement != "separator":
							res.append(MultiContentEntryText(
								pos=(xPos-self.separatorLineThickness, yPos), size=(self.separatorLineThickness, self.instance.size().height()),
								font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
								text="",
								color=self.separatorLineColor, color_sel=self.separatorLineColor,
								backcolor=self.separatorLineColor, backcolor_sel=self.separatorLineColor))
							if self.alignment == "right":
								xPos -= self.separatorLineThickness + self.spacing
							else:
								xPos += self.separatorLineThickness + self.spacing
					else:
						textWidth = self._calcTextWidth(self.current_crypto, font=self.font, size=eSize(self.getDesktopWith() // 3, 0))
						res.append(MultiContentEntryText(
								pos=(xPos-textWidth, yPos-2), size=(textWidth, self.instance.size().height()),
								font=0, flags=RT_HALIGN_CENTER | RT_VALIGN_TOP,
								text=self.current_crypto,
								color=self.foreColor, color_sel=self.foreColor,
								backcolor=None, backcolor_sel=None))
						if self.alignment == "right":
							xPos -= textWidth + self.spacing
						else:
							xPos += textWidth + self.spacing
							
			if enabledKey:
				self.prevElement = self.lastElement
				self.lastElement = enabledKey
		
		if self.lastElement == "separator" and self.prevElement != "currentCrypto":
			res.pop()

		return res
		
	def getDesktopWith(self):
		return getDesktop(0).size().width()
		
	def _calcTextWidth(self, text, font=None, size=None):
		if size:
			self.textRenderer.instance.resize(size)
		if font:
			self.textRenderer.instance.setFont(font)
		self.textRenderer.text = text
		return self.textRenderer.instance.calculateSize().width()

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "pixmaps":
				self.pixmaps = dict(item.split(':') for item in value.split(','))
			if attrib == "pixmapsDisabled":
				self.pixmapsDisabled = dict(item.split(':') for item in value.split(','))
			elif attrib == "spacing":
				self.spacing = parseScale(value)
			elif attrib == "alignment":
				self.alignment = value
			elif attrib == "orientation":
				self.orientation = self.orientations.get(value, self.orientations["orHorizontal"])
				if self.orientation == eListbox.orHorizontal:
					self.instance.setOrientation(eListbox.orVertical)
					self.l.setOrientation(eListbox.orVertical)
				else:
					self.instance.setOrientation(eListbox.orHorizontal)
					self.l.setOrientation(eListbox.orHorizontal)
			elif attrib == "elements":
				self.elements = value.split(",")
			elif attrib == "separatorLineColor":
				self.foreColor = parseColor(value).argb()
			elif attrib == "separatorLineThickness":
				self.separatorLineThickness = parseScale(value)
			elif attrib == "autoresizeMode":
				self.autoresizeMode = value
			elif attrib == "font":
				self.font = parseFont(value, ((1, 1), (1, 1)))
			elif attrib == "foregroundColor":
				self.foreColor = parseColor(value).argb()
			elif attrib == "permanent":
				self.permanentIcons = value.split(",")
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		self.l.setFont(0, self.font)
		return GUIAddon.applySkin(self, desktop, parent)
