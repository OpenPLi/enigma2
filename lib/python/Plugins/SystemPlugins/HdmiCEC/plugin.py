import Components.HdmiCec
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigBoolean, ConfigSelection, getConfigListEntry
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.LocationBox import LocationBox
from Screens.Screen import Screen
from os import path


class HdmiCECSetupScreen(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["HdmiCECSetupScreen", "Setup"]
		self.setTitle(_("HDMI-CEC setup"))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Set fixed"))
		self["key_blue"] = StaticText(_("Clear fixed"))

		self["description"] = Label("")

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"green": self.keySave,
			"red": self.keyCancel,
			"yellow": self.setFixedAddress,
			"blue": self.clearFixedAddress,
			"menu": self.closeRecursive,
		}, -2)

		self.logpath_entry = None
		ConfigListScreen.__init__(self, [], session, self.changedEntry)
		self["config"].onSelectionChanged.append(self.updateDescription)
		self.createSetup()
		self.updateAddress()

	def changedEntry(self):
		if isinstance(self["config"].getCurrent()[1], ConfigBoolean) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
			self.createSetup()

	def createSetup(self):
		configlist = []
		configlist.append(getConfigListEntry(_("Enabled"), config.hdmicec.enabled, _("Enable or disable using HDMI-CEC.")))
		if config.hdmicec.enabled.value:
			configlist.append(getConfigListEntry(_("Put TV in standby"), config.hdmicec.control_tv_standby, _("Automatically put the TV in standby whenever the receiver goes into standby or deep standby.")))
			configlist.append(getConfigListEntry(_("Wakeup TV from standby"), config.hdmicec.control_tv_wakeup, _("When the receiver wakes from standby or deep standby, it will send a command to the TV to bring it out of standby too.")))
			if config.hdmicec.control_tv_wakeup.value:
				configlist.append(getConfigListEntry(_("Wakeup command for TV"), config.hdmicec.tv_wakeup_command, _("Some TVs do not wake from standby when they receive the 'Image View On' command. If this is the case try the 'Text View On' command instead.")))
			configlist.append(getConfigListEntry(_("Regard deep standby as standby"), config.hdmicec.handle_deepstandby_events, _("If set to 'yes' the same commands will be sent to the TV for deep standby events, as are sent during regular standby events.")))
			configlist.append(getConfigListEntry(_("Switch TV to correct input"), config.hdmicec.report_active_source, _("When receiver wakes from standby, it will command the TV to switch to the HDMI input the receiver is connected to.")))
			configlist.append(getConfigListEntry(_("Use TV remote control"), config.hdmicec.report_active_menu, _("Allows the TV remote to be used to control the receiver.")))
			configlist.append(getConfigListEntry(_("Handle standby from TV"), config.hdmicec.handle_tv_standby, _("When enabled the receiver will automatically return to standby when the TV is turned off.")))
			configlist.append(getConfigListEntry(_("Handle wakeup from TV"), config.hdmicec.handle_tv_wakeup, _("When enabled the receiver will automatically wake from standby when the TV is turned on.")))
			if config.hdmicec.handle_tv_wakeup.value:
				configlist.append(getConfigListEntry(_("Wakeup signal from TV"), config.hdmicec.tv_wakeup_detection, _("Wake the receiver from standby when selected wake command is sent from the TV.")))
			configlist.append(getConfigListEntry(_("Forward volume keys"), config.hdmicec.volume_forwarding, _("Volume keys on the receiver remote will control the TV volume.")))
			configlist.append(getConfigListEntry(_("Put receiver in standby"), config.hdmicec.control_receiver_standby, _("Put A/V receiver to standby too.")))
			configlist.append(getConfigListEntry(_("Wakeup receiver from standby"), config.hdmicec.control_receiver_wakeup, _("Wakeup A/V receiver from standby too.")))
			configlist.append(getConfigListEntry(_("Minimum send interval"), config.hdmicec.minimum_send_interval, _("Delay between CEC commands when sending a series of commands. Some devices require this delay for correct functioning, usually between 50-150ms.")))
			configlist.append(getConfigListEntry(_("Repeat leave standby messages"), config.hdmicec.repeat_wakeup_timer, _("The command to wake from standby will be sent multiple times.")))
			configlist.append(getConfigListEntry(_("Send 'sourceactive' before zap timers"), config.hdmicec.sourceactive_zaptimers, _("Command the TV to switch to the correct HDMI input when zap timers activate.")))
			configlist.append(getConfigListEntry(_("Detect next boxes before standby"), config.hdmicec.next_boxes_detect, _("Before sending the command to switch the TV to standby, the receiver tests if all the other devices plugged to TV are in standby. If they are not, the 'sourceinactive' command will be sent to the TV instead of the 'standby' command.")))
			configlist.append(getConfigListEntry(_("Debug to file"), config.hdmicec.debug, _("If enabled, a log will be kept of CEC protocol traffic ('hdmicec.log')")))
			self.logpath_entry = getConfigListEntry(_("Select path for logfile"), config.hdmicec.log_path, _("Press OK to select the save location of the log file."))
			if config.hdmicec.debug.value != "0":
				configlist.append(self.logpath_entry)
		self["config"].list = configlist

	def updateDescription(self):
		self["description"].setText("%s\n%s\n%s" % (self.current_address, self.fixed_address, self.getCurrentDescription()))

	def keyOk(self):
		if self["config"].getCurrent() == self.logpath_entry:
			self.set_path()

	def setFixedAddress(self):
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress(Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		self.updateAddress()

	def clearFixedAddress(self):
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress("0.0.0.0")
		self.updateAddress()

	def updateAddress(self):
		self.current_address = _("Current CEC address") + ": " + Components.HdmiCec.hdmi_cec.getPhysicalAddress()
		if config.hdmicec.fixed_physical_address.value == "0.0.0.0":
			self.fixed_address = ""
		else:
			self.fixed_address = _("Using fixed address") + ": " + config.hdmicec.fixed_physical_address.value
		self.updateDescription()

	def logPath(self, res):
		if res is not None:
			config.hdmicec.log_path.value = res

	def set_path(self):
		inhibitDirs = ["/autofs", "/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/tmp", "/usr"]
		txt = _("Select directory for logfile")
		self.session.openWithCallback(self.logPath, LocationBox, text=txt, currDir=config.hdmicec.log_path.value,
				bookmarks=config.hdmicec.bookmarks, autoAdd=False, editDir=True, inhibitDirs=inhibitDirs, minFree=1)


def main(session, **kwargs):
	session.open(HdmiCECSetupScreen)


def startSetup(menuid):
	# only show in the menu when set to intermediate or higher
	if menuid == "video" and config.av.videoport.value == "DVI" and config.usage.setup_level.index >= 1:
		return [(_("HDMI-CEC setup"), main, "hdmi_cec_setup", 0)]
	return []


def Plugins(**kwargs):
	if path.exists("/dev/hdmi_cec") or path.exists("/dev/misc/hdmi_cec0"):
		return [PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=startSetup)]
	return []
