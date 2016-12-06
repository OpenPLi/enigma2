from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, configfile
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Tools.Directories import fileExists

_hdmiCec = None
def inithdmiCec():
	global _hdmiCec
	if fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0") and _hdmiCec is None:
		import Components.HdmiCec
		_hdmiCec = Components.HdmiCec.hdmi_cec

class HdmiCECSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-300,c-250" size="600,500" title="HDMI-CEC setup">
		<widget name="config" position="25,25" size="550,350" />
		<widget source="current_address" render="Label" position="25,375" size="550,30" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<widget source="fixed_address" render="Label" position="25,405" size="550,30" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="20,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="160,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="300,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="440,e-45" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="20,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="160,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="300,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget source="key_blue" render="Label" position="440,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("HDMI-CEC setup"))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Set fixed"))
		self["key_blue"] = StaticText(_("Clear fixed"))
		self["current_address"] = StaticText()
		self["fixed_address"] = StaticText()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"yellow": self.setFixedAddress,
			"blue": self.clearFixedAddress,
			"menu": self.closeRecursive,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enabled"), config.hdmicec.enabled))
		if config.hdmicec.enabled.value:
			self.list.append(getConfigListEntry(_("Put TV in standby"), config.hdmicec.control_tv_standby))
			self.list.append(getConfigListEntry(_("Wakeup TV from standby"), config.hdmicec.control_tv_wakeup))
			self.list.append(getConfigListEntry(_("Regard deep standby as standby"), config.hdmicec.handle_deepstandby_events))
			self.list.append(getConfigListEntry(_("Switch TV to correct input"), config.hdmicec.report_active_source))
			self.list.append(getConfigListEntry(_("Use TV remote control"), config.hdmicec.report_active_menu))
			self.list.append(getConfigListEntry(_("Handle standby from TV"), config.hdmicec.handle_tv_standby))
			self.list.append(getConfigListEntry(_("Handle wakeup from TV"), config.hdmicec.handle_tv_wakeup))
			self.list.append(getConfigListEntry(_("Wakeup signal from TV"), config.hdmicec.tv_wakeup_detection))
			self.list.append(getConfigListEntry(_("Forward volume keys"), config.hdmicec.volume_forwarding))
			self.list.append(getConfigListEntry(_("Put receiver in standby"), config.hdmicec.control_receiver_standby))
			self.list.append(getConfigListEntry(_("Wakeup receiver from standby"), config.hdmicec.control_receiver_wakeup))
			self.list.append(getConfigListEntry(_("Minimum send interval"), config.hdmicec.minimum_send_interval))
			self.list.append(getConfigListEntry(_("Repeat leave standby messages"), config.hdmicec.repeat_wakeup_timer))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self.updateAddress()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		if self["config"].getCurrent()[0] == _("Enabled"):
			self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		if self["config"].getCurrent()[0] == _("Enabled"):
			self.createSetup()

	def keyGo(self):
		if self["config"].isChanged():
			for x in self["config"].list:
				x[1].save()
			configfile.save()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def setFixedAddress(self):
		_hdmiCec.setFixedPhysicalAddress(_hdmiCec.getPhysicalAddress())
		self.updateAddress()

	def clearFixedAddress(self):
		_hdmiCec.setFixedPhysicalAddress("0.0.0.0")
		self.updateAddress()

	def updateAddress(self):
		self["current_address"].setText(_("Current CEC address") + ": " + _hdmiCec.getPhysicalAddress())
		if config.hdmicec.fixed_physical_address.value == "0.0.0.0":
			fixedaddresslabel = ""
		else:
			fixedaddresslabel = _("Using fixed address") + ": " + config.hdmicec.fixed_physical_address.value
		self["fixed_address"].setText(fixedaddresslabel)

def main(session, **kwargs):
	session.open(HdmiCECSetupScreen)

def startSetup(menuid):
	if menuid == "system":
		return [(_("HDMI-CEC setup"), main, "hdmi_cec_setup", 0)]
	return []

def Plugins(**kwargs):
	inithdmiCec()
	if _hdmiCec is not None:
		return [PluginDescriptor(where = PluginDescriptor.WHERE_MENU, fnc = startSetup)]
	return []
