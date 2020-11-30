from Components.ActionMap import ActionMap, HelpableActionMap, NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.SystemInfo import SystemInfo
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo
from Components.PluginComponent import plugins
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from ServiceReference import ServiceReference
from enigma import eServiceReference
from Components.Pixmap import Pixmap
from Components.Label import Label
import os

class hotkey:
	functions = None
	hotkeys = [(_("Red") + " " + _("long"), "red_long", ""),
		(_("Green") + " " + _("long"), "green_long", ""),
		(_("Yellow") + " " + _("long"), "yellow_long", "Plugins/Extensions/GraphMultiEPG/1"),
		(_("Blue") + " " + _("long"), "blue_long", "SoftcamSetup"),
		("F1/LAN", "f1", ""),
		("F1" + " " + _("long"), "f1_long", ""),
		("F2", "f2", ""),
		("F2" + " " + _("long"), "f2_long", ""),
		("F3", "f3", ""),
		("F3" + " " + _("long"), "f3_long", ""),
		(_("Red"), "red", ""),
		(_("Green"), "green", ""),
		(_("Yellow"), "yellow", ""),
		(_("Blue"), "blue", ""),
		("Rec", "rec", ""),
		("Rec" + " " + _("long"), "rec_long", "Infobar/instantRecord"),
		("Radio", "radio", ""),
		("Radio" + " " + _("long"), "radio_long", ""),
		("TV", "showTv", ""),
		("TV" + " " + _("long"), "showTv_long", SystemInfo["LcdLiveTV"] and "Infobar/ToggleLCDLiveTV" or ""),
		("TV2", "toggleTvRadio", ""),
		("TV2" + " " + _("long"), "toggleTvRadio_long", SystemInfo["LcdLiveTV"] and "Infobar/ToggleLCDLiveTV" or ""),
		("Teletext", "text", ""),
		("Help", "displayHelp", ""),
		("Help" + " " + _("long"), "displayHelp_long", ""),
		("Subtitle", "subtitle", ""),
		("Subtitle"+ " " + _("long"), "subtitle_long", ""),
		("Menu", "mainMenu", ""),
		("Info (EPG)", "info", "Infobar/openEventView"),
		("Info (EPG)" + " " + _("long"), "info_long", "Infobar/showEventInfoPlugins"),
		("List/Fav/PVR", "list", ""),
		("List/Fav/PVR" + " " + _("long"), "list_long", "Plugins/Extensions/Kodi/1"),
		("Back/Recall", "back", ""),
		("Back/Recall" + " " + _("long"), "back_long", ""),
		("End", "end", ""),
		("Epg/Guide", "epg", "Plugins/Extensions/GraphMultiEPG/1"),
		("Epg/Guide" + " " + _("long"), "epg_long", "Infobar/showEventInfoPlugins"),
		("Left", "cross_left", ""),
		("Right", "cross_right", ""),
		("Up", "cross_up", ""),
		("Down", "cross_down", ""),
		("Ok", "ok", ""),
		("Channel up", "channelup", ""),
		("Channel down", "channeldown", ""),
		("Page up", "pageUp", ""),
		("Page up"  + " " + _("long"), "pageUp_long", ""),
		("Page down", "pageDown", ""),
		("Page down" + " " + _("long"), "pageDown_long", ""),
		("Next", "next", ""),
		("Previous", "previous", ""),
		("Audio", "audio", ""),
		("Play", "play", ""),
		("Playpause", "playpause", ""),
		("Stop", "stop", ""),
		("Pause", "pause", ""),
		("Rewind", "rewind", ""),
		("Fastforward", "fastforward", ""),
		("Skip back", "skip_back", ""),
		("Skip forward", "skip_forward", ""),
		("Activate PiP", "activatePiP", ""),
		("Timer", "timer", ""),
		("Timer" + " " + _("long"), "timer_long", ""),
		("Playlist", "playlist", ""),
		("Timeshift", "timeshift", ""),
		("Search", "search", ""),
		("Search" + " " + _("long"), "search_long", ""),
		("Slow", "slow", ""),
		("Mark/Portal/Playlist", "mark", ""),
		("Mark/Portal/Playlist" + " " + _("long"), "mark_long", ""),
		("Sleep", "sleep", ""),
		("Sleep" + " " + _("long"), "sleep_long", ""),
		("Context", "contextmenu", ""),
		("Context" + " " + _("long"), "contextmenu_long", ""),
		("Video Mode", "vmode", ""),
		("Video Mode" + " " + _("long"), "vmode_long", ""),
		("Home", "home", ""),
		("Power", "power", "Module/Screens.Standby/Standby"),
		("Power" + " " + _("long"), "power_long", "Menu/shutdown"),
		("HDMIin", "HDMIin", "Infobar/HDMIIn"),
		("HDMIin" + " " + _("long"), "HDMIin_long", ""),
		("Media", "media", ""),
		("Media" + " " + _("long"), "media_long", ""),
		("Favorites", "favorites", "Infobar/openFavouritesList"),
		("Favorites" + " " + _("long"), "favorites_long", ""),
		("Mouse", "mouse", ""),
		("Mouse" + " " + _("long"), "mouse_long", ""),
		("Sat", "sat", ""),
		("Sat" + " " + _("long"), "sat_long", ""),
		("Homepage", "homepage", ""),
		("Homepage" + " " + _("long"), "homepage_long", ""),
		("EjectCD", "ejectcd", ""),
		("EjectCD" + " " + _("long"), "ejectcd_long", ""),
		("VOD", "vod", ""),
		("VOD" + " " + _("long"), "vod_long", ""),
		("WWW Portal", "www", ""),
		("WWW Portal" + " " + _("long"), "www_long", "")]

def getHotkeyFunctions():
	hotkey.functions = []
	twinPlugins = []
	twinPaths = {}
	pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path and 'selectedevent' not in plugin.__call__.func_code.co_varnames:
			if plugin.path[24:] in twinPaths:
				twinPaths[plugin.path[24:]] += 1
			else:
				twinPaths[plugin.path[24:]] = 1
			hotkey.functions.append((plugin.name, plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) , "EPG"))
			twinPlugins.append(plugin.name)
	pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU])
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path:
			if plugin.path[24:] in twinPaths:
				twinPaths[plugin.path[24:]] += 1
			else:
				twinPaths[plugin.path[24:]] = 1
			hotkey.functions.append((plugin.name, plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) , "Plugins"))
			twinPlugins.append(plugin.name)
	hotkey.functions.append((_("Main menu"), "Infobar/mainMenu", "InfoBar"))
	hotkey.functions.append((_("Show help"), "Infobar/showHelp", "InfoBar"))
	hotkey.functions.append((_("Show extension selection"), "Infobar/showExtensionSelection", "InfoBar"))
	hotkey.functions.append((_("Zap down"), "Infobar/zapDown", "InfoBar"))
	hotkey.functions.append((_("Zap up"), "Infobar/zapUp", "InfoBar"))
	hotkey.functions.append((_("Volume up"), "Infobar/volumeUp", "InfoBar"))
	hotkey.functions.append((_("Volume down"), "Infobar/volumeDown", "InfoBar"))
	hotkey.functions.append((_("Switch channel up"), "Infobar/switchChannelUp", "InfoBar"))
	hotkey.functions.append((_("Switch channel down"), "Infobar/switchChannelDown", "InfoBar"))
	hotkey.functions.append((_("Show service list"), "Infobar/openServiceList", "InfoBar"))
	hotkey.functions.append((_("Show movies"), "Infobar/showMovies", "InfoBar"))
	hotkey.functions.append((_("Show servicelist or movies"), "Infobar/showServiceListOrMovies", "InfoBar"))
	hotkey.functions.append((_("Show favourites list"), "Infobar/openFavouritesList", "InfoBar"))
	hotkey.functions.append((_("Show satellites list"), "Infobar/openSatellitesList", "InfoBar"))
	hotkey.functions.append((_("History back"), "Infobar/historyBack", "InfoBar"))
	hotkey.functions.append((_("History next"), "Infobar/historyNext", "InfoBar"))
	hotkey.functions.append((_("Recall to previous service"), "Infobar/servicelist/recallPrevService", "InfoBar"))
	hotkey.functions.append((_("Show eventinfo plugins"), "Infobar/showEventInfoPlugins", "EPG"))
	hotkey.functions.append((_("Show event details"), "Infobar/openEventView", "EPG"))
	hotkey.functions.append((_("Show single service EPG"), "Infobar/openSingleServiceEPG", "EPG"))
	hotkey.functions.append((_("Show multi channel EPG"), "Infobar/openMultiServiceEPG", "EPG"))
	hotkey.functions.append((_("Show Audioselection"), "Infobar/audioSelection", "InfoBar"))
	hotkey.functions.append((_("Switch to radio mode"), "Infobar/showRadio", "InfoBar"))
	hotkey.functions.append((_("Switch to TV mode"), "Infobar/showTv", "InfoBar"))
	hotkey.functions.append((_("Toggle TV/RADIO mode"), "Infobar/toggleTvRadio", "InfoBar"))
	hotkey.functions.append((_("Instant record"), "Infobar/instantRecord", "InfoBar"))
	hotkey.functions.append((_("Start instant recording"), "Infobar/startInstantRecording", "InfoBar"))
	hotkey.functions.append((_("Activate timeshift End"), "Infobar/activateTimeshiftEnd", "InfoBar"))
	hotkey.functions.append((_("Activate timeshift end and pause"), "Infobar/activateTimeshiftEndAndPause", "InfoBar"))
	hotkey.functions.append((_("Start timeshift"), "Infobar/startTimeshift", "InfoBar"))
	hotkey.functions.append((_("Stop timeshift"), "Infobar/stopTimeshift", "InfoBar"))
	hotkey.functions.append((_("Start teletext"), "Infobar/startTeletext", "InfoBar"))
	hotkey.functions.append((_("Show subservice selection"), "Infobar/subserviceSelection", "InfoBar"))
	hotkey.functions.append((_("Show subtitle selection"), "Infobar/subtitleSelection", "InfoBar"))
	hotkey.functions.append((_("Show InfoBar"), "Infobar/showFirstInfoBar", "InfoBar"))
	hotkey.functions.append((_("Show second InfoBar"), "Infobar/showSecondInfoBar", "InfoBar"))
	hotkey.functions.append((_("Toggle infoBar"), "Infobar/toggleShow", "InfoBar"))
	hotkey.functions.append((_("Toggle videomode"), "Infobar/ToggleVideoMode", "InfoBar"))
	hotkey.functions.append((_("Toggle subtitles show/hide"), "Infobar/toggleSubtitleShown", "InfoBar"))
	if SystemInfo["PIPAvailable"]:
		hotkey.functions.append((_("Show PiP"), "Infobar/showPiP", "InfoBar"))
		hotkey.functions.append((_("Swap PiP"), "Infobar/swapPiP", "InfoBar"))
		hotkey.functions.append((_("Move PiP"), "Infobar/movePiP", "InfoBar"))
		hotkey.functions.append((_("Toggle PiPzap"), "Infobar/togglePipzap", "InfoBar"))
	hotkey.functions.append((_("Activate HbbTV (Redbutton)"), "Infobar/activateRedButton", "InfoBar"))
	hotkey.functions.append((_("Toggle HDMI In"), "Infobar/HDMIIn", "InfoBar"))
	if SystemInfo["LcdLiveTV"]:
		hotkey.functions.append((_("Toggle LCD LiveTV"), "Infobar/ToggleLCDLiveTV", "InfoBar"))
	hotkey.functions.append((_("Toggle dashed flickering line for this service"), "Infobar/ToggleHideVBI", "InfoBar"))
	hotkey.functions.append((_("Do nothing"), "Void", "InfoBar"))
	if SystemInfo["HasHDMI-CEC"]:
		hotkey.functions.append((_("HDMI-CEC Source Active"), "Infobar/SourceActiveHdmiCec", "InfoBar"))
		hotkey.functions.append((_("HDMI-CEC Source Inactive"), "Infobar/SourceInactiveHdmiCec", "InfoBar"))
	if SystemInfo["HasSoftcamInstalled"]:
		hotkey.functions.append((_("Softcam Setup"), "SoftcamSetup", "Setup"))
	hotkey.functions.append((_("HotKey Setup"), "Module/Screens.Hotkey/HotkeySetup", "Setup"))
	hotkey.functions.append((_("Software update"), "Module/Screens.SoftwareUpdate/UpdatePlugin", "Setup"))
	hotkey.functions.append((_("Latest Commits"), "Module/Screens.About/CommitInfo", "Setup"))
	hotkey.functions.append((_("CI (Common Interface) Setup"), "Module/Screens.Ci/CiSelection", "Setup"))
	hotkey.functions.append((_("Tuner Configuration"), "Module/Screens.Satconfig/NimSelection", "Scanning"))
	hotkey.functions.append((_("Manual Scan"), "Module/Screens.ScanSetup/ScanSetup", "Scanning"))
	hotkey.functions.append((_("Automatic Scan"), "Module/Screens.ScanSetup/ScanSimple", "Scanning"))
	for plugin in plugins.getPluginsForMenu("scan"):
		hotkey.functions.append((plugin[0], "MenuPlugin/scan/" + plugin[2], "Scanning"))
	hotkey.functions.append((_("Network"), "Module/Screens.NetworkSetup/NetworkAdapterSelection", "Setup"))
	hotkey.functions.append((_("Plugin Browser"), "Module/Screens.PluginBrowser/PluginBrowser", "Setup"))
	hotkey.functions.append((_("Sleeptimer edit"), "Module/Screens.SleepTimerEdit/SleepTimerEdit", "Setup"))
	hotkey.functions.append((_("Channel Info"), "Module/Screens.ServiceInfo/ServiceInfo", "Setup"))
	hotkey.functions.append((_("Timer"), "Module/Screens.TimerEdit/TimerEditList", "Setup"))
	for plugin in plugins.getPluginsForMenu("system"):
		if plugin[2]:
			hotkey.functions.append((plugin[0], "MenuPlugin/system/" + plugin[2], "Setup"))
	for plugin in plugins.getPluginsForMenu("video"):
		if plugin[2]:
			hotkey.functions.append((plugin[0], "MenuPlugin/video/" + plugin[2], "Setup"))
	for plugin in plugins.getPluginsForMenu("gui"):
		if plugin[2]:
			hotkey.functions.append((plugin[0], "MenuPlugin/gui/" + plugin[2], "Setup"))
	hotkey.functions.append((_("PowerMenu"), "Menu/shutdown", "Power"))
	hotkey.functions.append((_("Standby"), "Module/Screens.Standby/Standby", "Power"))
	hotkey.functions.append((_("Restart"), "Module/Screens.Standby/TryQuitMainloop/2", "Power"))
	hotkey.functions.append((_("Restart enigma"), "Module/Screens.Standby/TryQuitMainloop/3", "Power"))
	hotkey.functions.append((_("Deep standby"), "Module/Screens.Standby/TryQuitMainloop/1", "Power"))
	hotkey.functions.append((_("Usage Setup"), "Setup/usage", "Setup"))
	hotkey.functions.append((_("User interface"), "Setup/userinterface", "Setup"))
	hotkey.functions.append((_("Recording Setup"), "Setup/recording", "Setup"))
	hotkey.functions.append((_("Harddisk Setup"), "Setup/harddisk", "Setup"))
	hotkey.functions.append((_("Subtitles Settings"), "Setup/subtitlesetup", "Setup"))
	hotkey.functions.append((_("Language"), "Module/Screens.LanguageSelection/LanguageSelection", "Setup"))
	hotkey.functions.append((_("Memory Info"), "Module/Screens.About/MemoryInfo", "Setup"))
	if SystemInfo["canMultiBoot"]:
		hotkey.functions.append((_("Multiboot image selector"), "Module/Screens.FlashImage/MultibootSelection", "Setup"))
	if os.path.isdir("/etc/ppanels"):
		for x in [x for x in os.listdir("/etc/ppanels") if x.endswith(".xml")]:
			x = x[:-4]
			hotkey.functions.append((_("PPanel") + " " + x, "PPanel/" + x, "PPanels"))
	if os.path.isdir("/usr/script"):
		for x in [x for x in os.listdir("/usr/script") if x.endswith(".sh")]:
			x = x[:-3]
			hotkey.functions.append((_("Shellscript") + " " + x, "Shellscript/" + x, "Shellscripts"))

config.misc.hotkey = ConfigSubsection()
config.misc.hotkey.additional_keys = ConfigYesNo(default=False)
for x in hotkey.hotkeys:
	exec "config.misc.hotkey.%s = ConfigText(default='%s')" % x[1:]

class HotkeySetup(Screen):
	ALLOW_SUSPEND = False
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.setTitle(_("Hotkey Setup"))
		self["key_red"] = StaticText(_("Exit"))
		self["description"] = Label()
		self.list = []
		for x in hotkey.hotkeys:
			self.list.append(ChoiceEntryComponent('',(x[0], x[1])))
		self["list"] = ChoiceList(list=self.list)
		self["choosen"] = ChoiceList(list=[])
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": self.close,
			"red": self.close,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, -1)
		self["NumberActions"] = NumberActionMap(["NumberActions"],
		{
			"0": self.keyNumberGlobal
		})
		self["HotkeyButtonActions"] = hotkeyActionMap(["HotkeyActions"], dict((x[1], self.hotkeyGlobal) for x in hotkey.hotkeys))
		self.onLayoutFinish.append(self.__layoutFinished)
		self.onExecBegin.append(self.getFunctions)

	def __layoutFinished(self):
		self["choosen"].selectionEnabled(0)

	def hotkeyGlobal(self, key):
		index = 0
		for x in self.list:
			if key == x[0][1]:
				self["list"].moveToIndex(index)
				break
			index += 1
		self.getFunctions()

	def keyOk(self):
		self.session.openWithCallback(self.HotkeySetupSelectCallback, HotkeySetupSelect, self["list"].l.getCurrentSelection())

	def HotkeySetupSelectCallback(self, answer):
		if answer:
			self.close(True)

	def keyLeft(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)
		self.getFunctions()

	def keyRight(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)
		self.getFunctions()

	def keyUp(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.getFunctions()

	def keyDown(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.getFunctions()

	def setDefaultHotkey(self, answer):
		if answer:
			for x in hotkey.hotkeys:
				current_config = eval("config.misc.hotkey." + x[1])
				current_config.value = str(x[2])
				current_config.save()
			self.getFunctions()

	def keyNumberGlobal(self, number):
		self.session.openWithCallback(self.setDefaultHotkey, MessageBox, _("Set all hotkey to default?"), MessageBox.TYPE_YESNO)

	def getFunctions(self):
		key = self["list"].l.getCurrentSelection()[0][1]
		if key:
			selected = []
			for x in eval("config.misc.hotkey." + key + ".value.split(',')"):
				if x.startswith("ZapPanic"):
					selected.append(ChoiceEntryComponent('',((_("Panic to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
				elif x.startswith("Zap"):
					selected.append(ChoiceEntryComponent('',((_("Zap to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
				else:
					function = list(function for function in hotkey.functions if function[1] == x )
					if function:
						selected.append(ChoiceEntryComponent('',((function[0][0]), function[0][1])))
			self["choosen"].setList(selected)
		self["description"].setText(_("Press or select button and then press 'OK' for attach next function or edit attached.") if len(selected) else _("Press or select button and then press 'OK' for attach function."))

class HotkeySetupSelect(Screen):
	def __init__(self, session, key, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.key = key
		getHotkeyFunctions()
		self.setTitle(_("Hotkey Setup") + " " + key[0][0])
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText("")
		self["h_prev"] = Pixmap()
		self["h_next"] = Pixmap()
		self["description"] = Label()

		self.mode = "list"
		self.config = eval("config.misc.hotkey." + key[0][1])
		self.expanded = []
		self.selected = []
		for x in self.config.value.split(','):
			if x.startswith("ZapPanic"):
				self.selected.append(ChoiceEntryComponent('',((_("Panic to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
			elif x.startswith("Zap"):
				self.selected.append(ChoiceEntryComponent('',((_("Zap to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
			else:
				function = list(function for function in hotkey.functions if function[1] == x )
				if function:
					self.selected.append(ChoiceEntryComponent('',((function[0][0]), function[0][1])))
		text = _("Press 'OK' for attach next function or 'CH+/-' for edit attached.") if len(self.selected) else _("Press 'OK' for attach function.")
		self.prevselected = self.selected[:]
		if self.prevselected:
			self["key_yellow"].setText(_("Edit selection"))
		self["choosen"] = ChoiceList(list=self.selected, selection=0)
		self["list"] = ChoiceList(list=self.getFunctionList(), selection=0)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"yellow": self.toggleMode,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"pageUp": self.toggleMode,
			"pageDown": self.toggleMode,
			"moveUp": self.moveUp,
			"moveDown": self.moveDown,
			"menu": boundFunction(self.close, True),
		}, -1)
		self.description(text)
		self.showPrevNext()
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self["choosen"].selectionEnabled(0)

	def getFunctionList(self):
		functionslist = []
		catagories = {}
		for function in hotkey.functions:
			if function[2] not in catagories:
				catagories[function[2]] = []
			catagories[function[2]].append(function)
		for catagorie in sorted(list(catagories)):
			if catagorie in self.expanded:
				functionslist.append(ChoiceEntryComponent('expanded',((catagorie), "Expander")))
				for function in catagories[catagorie]:
					functionslist.append(ChoiceEntryComponent('verticalline',((function[0]), function[1])))
				if catagorie == "InfoBar":
					functionslist.append(ChoiceEntryComponent('verticalline',((_("Zap to")), "Zap")))
					functionslist.append(ChoiceEntryComponent('verticalline',((_("Panic to")), "ZapPanic")))
			else:
				functionslist.append(ChoiceEntryComponent('expandable',((catagorie), "Expander")))
		return functionslist

	def description(self, msg=""):
		self["description"].setText(msg)

	def toggleMode(self):
		if self.mode == "list" and self.selected:
			self.mode = "choosen"
			self["choosen"].selectionEnabled(1)
			self["list"].selectionEnabled(0)
			self["key_yellow"].setText(_("Select function"))
			if len(self.selected) > 1:
				self.showPrevNext(True)
			self.description(_("Press 'OK' for remove item or < > for change order or 'CH+/-' for toggle to list of features.") if len(self.selected) > 1 else _("Press 'OK' for remove item or 'CH+/-' for toggle to list of features."))
		elif self.mode == "choosen":
			self.mode = "list"
			self["choosen"].selectionEnabled(0)
			self["list"].selectionEnabled(1)
			self.toggleText()

	def toggleText(self):
		if self.selected:
			self["key_yellow"].setText(_("Edit selection"))
			if self.mode == "list":
				self.description(_("Press 'OK' for attach next function or 'CH+/-' for edit attached."))
		else:
			self["key_yellow"].setText("")
		self.showPrevNext()

	def showPrevNext(self, show=False):
		if show:
			self["h_prev"].show()
			self["h_next"].show()
		else:
			self["h_prev"].hide()
			self["h_next"].hide()

	def keyOk(self):
		if self.mode == "list":
			currentSelected = self["list"].l.getCurrentSelection()
			if currentSelected[0][1] == "Expander":
				if currentSelected[0][0] in self.expanded:
					self.expanded.remove(currentSelected[0][0])
				else:
					self.expanded.append(currentSelected[0][0])
				self["list"].setList(self.getFunctionList())
			else:
				if currentSelected[:2] in self.selected:
					self.selected.remove(currentSelected[:2])
				else:
					if currentSelected[0][1].startswith("ZapPanic"):
						from Screens.ChannelSelection import SimpleChannelSelection
						self.session.openWithCallback(self.zaptoCallback, SimpleChannelSelection, _("Hotkey Panic") + " " + self.key[0][0], currentBouquet=True)
					elif currentSelected[0][1].startswith("Zap"):
						from Screens.ChannelSelection import SimpleChannelSelection
						self.session.openWithCallback(self.zaptoCallback, SimpleChannelSelection, _("Hotkey zap") + " " + self.key[0][0], currentBouquet=True)
					else:
						self.selected.append(currentSelected[:2])
			self.toggleText()
		elif self.selected:
			self.selected.remove(self["choosen"].l.getCurrentSelection())
			if not self.selected:
				self.toggleMode()
				self.toggleText()
		if not len(self.selected):
			self.description(_("Press 'OK' for attach function."))
			self.showPrevNext()
		elif len(self.selected) < 2:
			self.description(_("Press 'OK' for attach next function or 'CH+/-' for edit attached.") if self.mode == "list" else _("Press 'OK' for remove item or 'CH+/-' for toggle to list of features."))
			self.showPrevNext()
		self["choosen"].setList(self.selected)

	def zaptoCallback(self, *args):
		if args:
			currentSelected = self["list"].l.getCurrentSelection()[:]
			currentSelected[1]=currentSelected[1][:-1] + (currentSelected[0][0] + " " + ServiceReference(args[0]).getServiceName(),)
			self.selected.append([(currentSelected[0][0], currentSelected[0][1] + "/" + args[0].toString()), currentSelected[1]])

	def keyLeft(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.pageUp)

	def keyRight(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.pageDown)

	def keyUp(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.moveUp)

	def keyDown(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.moveDown)

	def moveUp(self):
		self.moveChoosen(self.keyUp)

	def moveDown(self):
		self.moveChoosen(self.keyDown)

	def moveChoosen(self, direction):
		if self.mode == "choosen":
			currentIndex = self["choosen"].getSelectionIndex()
			swapIndex = (currentIndex + (direction == self.keyDown and 1 or -1)) % len(self["choosen"].list)
			self["choosen"].list[currentIndex], self["choosen"].list[swapIndex] = self["choosen"].list[swapIndex], self["choosen"].list[currentIndex]
			self["choosen"].setList(self["choosen"].list)
			direction()
		else:
			return 0

	def save(self):
		configValue = []
		for x in self.selected:
			configValue.append(x[0][1])
		self.config.value = ",".join(configValue)
		self.config.save()
		self.close(False)

	def cancel(self):
		if self.selected != self.prevselected:
			self.session.openWithCallback(self.cancelCallback, MessageBox, _("are you sure to cancel all changes"), default=False)
		else:
			self.close(None)

	def cancelCallback(self, answer):
		answer and self.close(None)

class hotkeyActionMap(ActionMap):
	def action(self, contexts, action):
		if action in tuple(x[1] for x in hotkey.hotkeys) and action in self.actions:
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)

class helpableHotkeyActionMap(HelpableActionMap):
	def action(self, contexts, action):
		if action in tuple(x[1] for x in hotkey.hotkeys) and action in self.actions:
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)

class InfoBarHotkey():
	def __init__(self):
		if not hotkey.functions:
			getHotkeyFunctions()
		self["HotkeyButtonActions"] = helpableHotkeyActionMap(self, "HotkeyActions",
			dict((x[1],(self.hotkeyGlobal, boundFunction(self.getHelpText, x[1]))) for x in hotkey.hotkeys), -10)

	def getKeyFunctions(self, key):
		if key in ("play", "playpause", "Stop", "stop", "pause", "rewind", "next", "previous", "fastforward", "skip_back", "skip_forward") and (self.__class__.__name__ == "MoviePlayer" or hasattr(self, "timeshiftActivated") and self.timeshiftActivated()):
			return False
		selection = eval("config.misc.hotkey." + key + ".value.split(',')")
		selected = []
		for x in selection:
			if x.startswith("ZapPanic"):
				selected.append(((_("Panic to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x))
			elif x.startswith("Zap"):
				selected.append(((_("Zap to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x))
			else:
				function = list(function for function in hotkey.functions if function[1] == x )
				if function:
					selected.append(function[0])
		return selected

	def getHelpText(self, key):
		selected = self.getKeyFunctions(key)
		if not selected:
			return
		if len(selected) == 1:
			return selected[0][0]
		else:
			return _("Hotkey") + " " + tuple(x[0] for x in hotkey.hotkeys if x[1] == key)[0]

	def hotkeyGlobal(self, key):
		selected = self.getKeyFunctions(key)
		if not selected:
			return 0
		elif len(selected) == 1:
			return self.execHotkey(selected[0])
		else:
			key = tuple(x[0] for x in hotkey.hotkeys if x[1] == key)[0]
			self.session.openWithCallback(self.execHotkey, ChoiceBox, _("Hotkey") + " " + key, selected)

	def execHotkey(self, selected):
		if selected:
			selected = selected[1].split("/")
			if selected[0] == "Plugins":
				twinPlugins = []
				twinPaths = {}
				pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
				pluginlist.sort(key=lambda p: p.name)
				for plugin in pluginlist:
					if plugin.name not in twinPlugins and plugin.path and 'selectedevent' not in plugin.__call__.func_code.co_varnames:
						if plugin.path[24:] in twinPaths:
							twinPaths[plugin.path[24:]] += 1
						else:
							twinPaths[plugin.path[24:]] = 1
						if plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) == "/".join(selected):
							self.runPlugin(plugin)
							return
						twinPlugins.append(plugin.name)
				pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU])
				pluginlist.sort(key=lambda p: p.name)
				for plugin in pluginlist:
					if plugin.name not in twinPlugins and plugin.path:
						if plugin.path[24:] in twinPaths:
							twinPaths[plugin.path[24:]] += 1
						else:
							twinPaths[plugin.path[24:]] = 1
						if plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) == "/".join(selected):
							self.runPlugin(plugin)
							return
						twinPlugins.append(plugin.name)
			elif selected[0] == "MenuPlugin":
				for plugin in plugins.getPluginsForMenu(selected[1]):
					if plugin[2] == selected[2]:
						self.runPlugin(plugin[1])
						return
			elif selected[0] == "Infobar":
				if hasattr(self, selected[1]):
					exec "self." + ".".join(selected[1:]) + "()"
				else:
					return 0
			elif selected[0] == "Module":
				try:
					exec "from %s import %s" % (selected[1], selected[2])
					exec "self.session.open(%s)" %  ",".join(selected[2:])
				except Exception as e:
					print "[Hotkey] error during executing module %s, screen %s, %s" % (selected[1], selected[2], e)					
					import traceback
					traceback.print_exc()
			elif selected[0] == "SoftcamSetup" and SystemInfo["HasSoftcamInstalled"]:
				from Screens.SoftcamSetup import SoftcamSetup
				self.session.open(SoftcamSetup)
			elif selected[0] == "Setup":
				from Screens.Setup import Setup
				exec "self.session.open(Setup, \"%s\")" % selected[1]
			elif selected[0].startswith("Zap"):
				if selected[0] == "ZapPanic":
					self.servicelist.history = []
					self.pipShown() and self.showPiP()
				self.servicelist.servicelist.setCurrent(eServiceReference("/".join(selected[1:])))
				self.servicelist.zap(enable_pipzap = True)
				if hasattr(self, "lastservice"):
					self.lastservice = eServiceReference("/".join(selected[1:]))
					self.close()
				else:
					self.show()
				from Screens.MovieSelection import defaultMoviePath
				moviepath = defaultMoviePath()
				if moviepath:
					config.movielist.last_videodir.value = moviepath
			elif selected[0] == "PPanel":
				ppanelFileName = '/etc/ppanels/' + selected[1] + ".xml"
				if os.path.isfile(ppanelFileName) and os.path.isdir(resolveFilename(SCOPE_PLUGINS, 'Extensions/PPanel')):
					from Plugins.Extensions.PPanel.ppanel import PPanel
					self.session.open(PPanel, name=selected[1] + ' PPanel', node=None, filename=ppanelFileName, deletenode=None)
			elif selected[0] == "Shellscript":
				command = '/usr/script/' + selected[1] + ".sh"
				if os.path.isfile(command):
					if ".hidden." in command:
						from enigma import eConsoleAppContainer
						eConsoleAppContainer().execute(command)
					else:
						from Screens.Console import Console
						self.session.open(Console, selected[1] + " shellscript", command, closeOnSuccess=selected[1].startswith('!'), showStartStopText=False)
			elif selected[0] == "Menu":
				from Screens.Menu import MainMenu, mdom
				root = mdom.getroot()
				for x in root.findall("menu"):
					y = x.find("id")
					if y is not None:
						id = y.get("val")
						if id and id == selected[1]:
							menu_screen = self.session.open(MainMenu, x)
							break

	def showServiceListOrMovies(self):
		if hasattr(self, "openServiceList"):
			self.openServiceList()
		elif hasattr(self, "showMovies"):
			self.showMovies()

	def ToggleLCDLiveTV(self):
		config.lcd.showTv.value = not config.lcd.showTv.value

	def SourceActiveHdmiCec(self):
		self.setHdmiCec("sourceactive")

	def SourceInactiveHdmiCec(self):
		self.setHdmiCec("sourceinactive")

	def setHdmiCec(self, cmd):
		if config.hdmicec.enabled.value:
			import Components.HdmiCec
			Components.HdmiCec.hdmi_cec.sendMessage(0, cmd)
