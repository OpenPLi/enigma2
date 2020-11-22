from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry
from Components.Sources.StaticText import StaticText

class HdmiCECSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-300,c-250" size="600,540" title="HDMI-CEC setup">
		<widget name="config" position="25,25" size="550,300" scrollbarMode="showOnDemand"/>
		<widget source="current_address" render="Label" position="25,335" size="550,25" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<widget source="fixed_address" render="Label" position="25,360" size="550,25" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<widget source="description" render="Label" position="25,390" size="550,92" zPosition="10" font="Regular;20" halign="left" />
		<ePixmap pixmap="buttons/red.png" position="20,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/green.png" position="160,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/yellow.png" position="300,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/blue.png" position="440,e-45" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="20,e-55" zPosition="1" size="140,50" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="160,e-55" zPosition="1" size="140,50" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="300,e-55" zPosition="1" size="140,50" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget source="key_blue" render="Label" position="440,e-55" zPosition="1" size="140,50" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
	</screen>"""

	def __init__(self, session):
		self.skin = HdmiCECSetupScreen.skin
		Screen.__init__(self, session)

		self.setTitle(_("HDMI-CEC setup"))

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Set fixed"))
		self["key_blue"] = StaticText(_("Clear fixed"))
		self["current_address"] = StaticText()
		self["fixed_address"] = StaticText()
		self["description"] = StaticText("")

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"yellow": self.setFixedAddress,
			"blue": self.clearFixedAddress,
			"menu": self.closeRecursive,
		}, -2)

		self.list = []
		self.logpath_entry = None
		ConfigListScreen.__init__(self, self.list, session = self.session)
		self.createSetup()
		self.updateAddress()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enabled"), config.hdmicec.enabled, _("Enable or disable using HDMI-CEC.")))
		if config.hdmicec.enabled.value:
			self.list.append(getConfigListEntry(_("Put TV in standby"), config.hdmicec.control_tv_standby, _("Put TV to standby when receiver goes to standby or to deep standby.")))
			self.list.append(getConfigListEntry(_("Wakeup TV from standby"), config.hdmicec.control_tv_wakeup, _("When receiver wakes up/starts, it will try wake up TV by sending the appropriate command.")))
			if config.hdmicec.control_tv_wakeup.value:
				self.list.append(getConfigListEntry(_("Wakeup command for TV"), config.hdmicec.tv_wakeup_command, _("Some tv's do not handle command 'Image View On' for wakingup correctly, so you can try sending 'Text View On' as alternative.")))
			self.list.append(getConfigListEntry(_("Regard deep standby as standby"), config.hdmicec.handle_deepstandby_events, _("Regard deep standby as standby. It will be sending same commands when box goest to deep standby.")))
			self.list.append(getConfigListEntry(_("Switch TV to correct input"), config.hdmicec.report_active_source, _("When receiver wakes up/starts, it will send command for switch TV to correct input to which the receiver is pluged.")))
			self.list.append(getConfigListEntry(_("Use TV remote control"), config.hdmicec.report_active_menu, _("Use TV remote control for your receiver.")))
			self.list.append(getConfigListEntry(_("Handle standby from TV"), config.hdmicec.handle_tv_standby, _("When TV is turned off, the receiver will switch to standby by a command received from the TV.")))
			self.list.append(getConfigListEntry(_("Handle wakeup from TV"), config.hdmicec.handle_tv_wakeup, _("When TV is turned on, the receiver will be awakened by a command received from the TV.")))
			if config.hdmicec.handle_tv_wakeup.value:
				self.list.append(getConfigListEntry(_("Wakeup signal from TV"), config.hdmicec.tv_wakeup_detection, _("A command sent from TV will wake up the receiver from standby.")))
			self.list.append(getConfigListEntry(_("Forward volume keys"), config.hdmicec.volume_forwarding, _("Forward volume keys")))
			self.list.append(getConfigListEntry(_("Put receiver in standby"), config.hdmicec.control_receiver_standby, _("Put A/V receiver to standby.")))
			self.list.append(getConfigListEntry(_("Wakeup receiver from standby"), config.hdmicec.control_receiver_wakeup, _("Wakeup A/V receiver from standby.")))
			self.list.append(getConfigListEntry(_("Minimum send interval"), config.hdmicec.minimum_send_interval, _("Delay in queue between sending CEC commands. For working HDMI-CEC protocol must be for some receivers used delay. Usualy between 50-150ms.")))
			self.list.append(getConfigListEntry(_("Repeat leave standby messages"), config.hdmicec.repeat_wakeup_timer, _("The wake up command can be sent multiple times.")))
			self.list.append(getConfigListEntry(_("Send 'sourceactive' before zap timers"), config.hdmicec.sourceactive_zaptimers, _("ZAP timers can send command 'sourceactive' before zap for set TV to correct input.")))
			self.list.append(getConfigListEntry(_("Detect next boxes before standby"), config.hdmicec.next_boxes_detect, _("Before sending command for switch TV to standby receiver tests if all other receivers pluged to TV are in standby. If are not, 'sourceactive' instead 'stanby' is sent to the TV.")))
			self.list.append(getConfigListEntry(_("Debug to file"), config.hdmicec.debug, _("If enabled, CEC protocol traffic can be saved to a logfile 'hdmicec.log'.")))
			self.logpath_entry = getConfigListEntry(_("Select path for logfile"), config.hdmicec.log_path, _("Press OK and select directory as path for logfile."))
			if config.hdmicec.debug.value != "0":
				self.list.append(self.logpath_entry)
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
	def getCurrentEntry(self):
		self["description"].setText(self.getCurrentDescription())
		return self["config"].getCurrent()[0]
	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())
	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary
	###

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def keyGo(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyOk(self):
		currentry = self["config"].getCurrent()
		if currentry == self.logpath_entry:
			self.set_path()
		else:
			self.keyGo()

	def setFixedAddress(self):
		import Components.HdmiCec
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress(Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		self.updateAddress()

	def clearFixedAddress(self):
		import Components.HdmiCec
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress("0.0.0.0")
		self.updateAddress()

	def updateAddress(self):
		import Components.HdmiCec
		self["current_address"].setText(_("Current CEC address") + ": " + Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		if config.hdmicec.fixed_physical_address.value == "0.0.0.0":
			fixedaddresslabel = ""
		else:
			fixedaddresslabel = _("Using fixed address") + ": " + config.hdmicec.fixed_physical_address.value
		self["fixed_address"].setText(fixedaddresslabel)

	def logPath(self, res):
		if res is not None:
			config.hdmicec.log_path.value = res

	def set_path(self):
		inhibitDirs = ["/autofs", "/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/tmp", "/usr"]
		from Screens.LocationBox import LocationBox
		txt = _("Select directory for logfile")
		self.session.openWithCallback(self.logPath, LocationBox, text=txt, currDir=config.hdmicec.log_path.value,
				bookmarks=config.hdmicec.bookmarks, autoAdd=False, editDir=True,
				inhibitDirs=inhibitDirs, minFree=1
				)

def main(session, **kwargs):
	session.open(HdmiCECSetupScreen)

def startSetup(menuid):
	# only show in the menu when set to intermediate or higher
	if menuid == "video" and config.av.videoport.value == "DVI" and config.usage.setup_level.index >= 1:
		return [(_("HDMI-CEC setup"), main, "hdmi_cec_setup", 0)]
	return []

def Plugins(**kwargs):
	from os import path
	if path.exists("/dev/hdmi_cec") or path.exists("/dev/misc/hdmi_cec0"):
		import Components.HdmiCec
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(where = PluginDescriptor.WHERE_MENU, fnc = startSetup)]
	return []
