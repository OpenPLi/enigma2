from os import path

import Components.HdmiCec
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.config import config
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.LocationBox import LocationBox
from Screens.Screen import Screen



class HdmiCECSetupScreen(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "Setup"
		self.setTitle(_("HDMI-CEC setup"))

		self["key_yellow"] = StaticText(_("Set fixed"))
		self["key_blue"] = StaticText(_("Clear fixed"))
		self["description"] = Label("")

		self["actions"] = ActionMap(["ColorActions"],
		{
			"yellow": self.setFixedAddress,
			"blue": self.clearFixedAddress,
		}, -2)

		self.list = []
		self.logpath_entry = None
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.createSetup, fullUI=True)
		self.createSetup()
		self.updateAddress()

	def createSetup(self):
		self.list = []
		self.list.append((_("Enabled"), config.hdmicec.enabled, _("Enable or disable using HDMI-CEC.")))
		if config.hdmicec.enabled.value:
			self.list.append((_("Put TV in standby"), config.hdmicec.control_tv_standby, _("Automatically put the TV in standby whenever the receiver goes into standby or deep standby.")))
			self.list.append((_("Wakeup TV from standby"), config.hdmicec.control_tv_wakeup, _("When the receiver wakes from standby or deep standby, it will send a command to the TV to bring it out of standby too.")))
			if config.hdmicec.control_tv_wakeup.value:
				self.list.append((_("Wakeup command for TV"), config.hdmicec.tv_wakeup_command, _("Some TVs do not wake from standby when they receive the 'Image View On' command. If this is the case try the 'Text View On' command instead.")))
			self.list.append((_("Regard deep standby as standby"), config.hdmicec.handle_deepstandby_events, _("If set to 'yes' the same commands will be sent to the TV for deep standby events, as are sent during regular standby events.")))
			self.list.append((_("Switch TV to correct input"), config.hdmicec.report_active_source, _("When receiver wakes from standby, it will command the TV to switch to the HDMI input the receiver is connected to.")))
			self.list.append((_("Use TV remote control"), config.hdmicec.report_active_menu, _("Allows the TV remote to be used to control the receiver.")))
			self.list.append((_("Handle standby from TV"), config.hdmicec.handle_tv_standby, _("When enabled the receiver will automatically return to standby when the TV is turned off.")))
			self.list.append((_("Handle wakeup from TV"), config.hdmicec.handle_tv_wakeup, _("When enabled the receiver will automatically wake from standby when the TV is turned on.")))
			if config.hdmicec.handle_tv_wakeup.value:
				self.list.append((_("Wakeup signal from TV"), config.hdmicec.tv_wakeup_detection, _("Wake the receiver from standby when selected wake command is sent from the TV.")))
			self.list.append((_("Forward volume keys"), config.hdmicec.volume_forwarding, _("Volume keys on the receiver remote will control the TV volume.")))
			if config.hdmicec.volume_forwarding.value:
				if config.hdmicec.minimum_send_interval.value != "0":
					self.list.append((_("Forwarded volume step size"), config.hdmicec.volume_forwarding_repeat, _("The number of steps to change the volume on the device the keys are forwarded to.")))
				else:
					self.list.append((_("Forwarded volume step size") + _(" - information"), config.hdmicec.volume_forwarding_repeat_empty, _("'Minimum send interval' needs to be enabled to use this option.")))
			self.list.append((_("Put receiver in standby"), config.hdmicec.control_receiver_standby, _("Put A/V receiver to standby too.")))
			self.list.append((_("Wakeup receiver from standby"), config.hdmicec.control_receiver_wakeup, _("Wakeup A/V receiver from standby too.")))
			self.list.append((_("Minimum send interval"), config.hdmicec.minimum_send_interval, _("Delay between CEC commands when sending a series of commands. Some devices require this delay for correct functioning, usually between 50-150ms.")))
			self.list.append((_("Repeat leave standby messages"), config.hdmicec.repeat_wakeup_timer, _("The command to wake from standby will be sent multiple times.")))
			self.list.append((_("Send 'sourceactive' before zap timers"), config.hdmicec.sourceactive_zaptimers, _("Command the TV to switch to the correct HDMI input when zap timers activate.")))
			self.list.append((_("Detect next boxes before standby"), config.hdmicec.next_boxes_detect, _("Before sending the command to switch the TV to standby, the receiver tests if all the other devices plugged to TV are in standby. If they are not, the 'sourceinactive' command will be sent to the TV instead of the 'standby' command.")))
			self.list.append((_("Debug to file"), config.hdmicec.debug, _("If enabled, a log will be kept of CEC protocol traffic ('hdmicec.log')")))
			self.logpath_entry = (_("Select path for logfile"), config.hdmicec.log_path, _("Press OK to select the save location of the log file."))
			if config.hdmicec.debug.value != "0":
				self.list.append(self.logpath_entry)
		self["config"].list = self.list

	def getCurrentDescription(self):
		description = ConfigListScreen.getCurrentDescription(self)
		return "%s\n%s\n\n%s" % (self.current_address, self.fixed_address, description) if config.hdmicec.enabled.value else description

	def keySelect(self):
		currentry = self["config"].getCurrent()
		if currentry == self.logpath_entry:
			self.set_path()
		else:
			ConfigListScreen.keySelect(self)

	def setFixedAddress(self):
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress(Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		self.updateAddress()

	def clearFixedAddress(self):
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress("0.0.0.0")
		self.updateAddress()

	def updateAddress(self):
		self.current_address = _("Current CEC address") + ":\t" + Components.HdmiCec.hdmi_cec.getPhysicalAddress()
		if config.hdmicec.fixed_physical_address.value == "0.0.0.0":
			self.fixed_address = _("Press yellow button to set CEC address again")
		else:
			self.fixed_address = _("Using fixed address") + ":\t" + config.hdmicec.fixed_physical_address.value
		self["description"].text = self.getCurrentDescription()

	def logPath(self, res):
		if res is not None:
			config.hdmicec.log_path.value = res

	def set_path(self):
		inhibitDirs = ["/autofs", "/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/tmp", "/usr"]
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
	if path.exists("/dev/hdmi_cec") or path.exists("/dev/misc/hdmi_cec0"):
		return [PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=startSetup)]
	return []
