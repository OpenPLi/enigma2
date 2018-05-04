from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, ConfigSelection, ConfigIP, ConfigInteger, getConfigListEntry, ConfigBoolean
from Components.ConfigList import ConfigListScreen

from enigma import getPeerStreamingBoxes

class SetupFallbacktuner(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Fallback tuner setup"))
		self.skinName = ["FallbackTunerSetup", "Setup"]
		self.onChangedEntry = []
		self.session = session
		ConfigListScreen.__init__(self, [], session = session, on_change = self.changedEntry)

		self["actions2"] = ActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"menu": self.keyCancel,
			"cancel": self.keyCancel,
			"save": self.keyGo,
		}, -2)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))

		self["description"] = Label("")
		self["VKeyIcon"] = Boolean(False)
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()

		self.force_update_list = False
		self.createConfig()
		self.createSetup()

		self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def createConfig(self):

		def set_avahiselect_seperate(configElement):
			if config.usage.remote_fallback_import_url.value and config.usage.remote_fallback_import_url.value != config.usage.remote_fallback.value:
				peerDefault_sepearate = config.usage.remote_fallback_import_url.value
			else:
				peerDefault_sepearate = "same"
				config.usage.remote_fallback_import_url.value = config.usage.remote_fallback.value
			self.seperateBoxes = [("same", _("Same as stream"))] + self.peerStreamingBoxes
			if configElement.value not in ("url", "ip") and configElement.value in self.seperateBoxes:
				self.seperateBoxes.remove(configElement.value)
			self.avahiselect_seperate = ConfigSelection(default=peerDefault_sepearate, choices=self.seperateBoxes)

		self.peerStreamingBoxes = getPeerStreamingBoxes() + [("ip", _("Enter IP address")), ("url", _("Enter URL"))]
		peerDefault = peerDefault_sepearate = None
		if config.usage.remote_fallback.value:
			peerDefault = peerDefault_sepearate = config.usage.remote_fallback.value
			if config.usage.remote_fallback.value and config.usage.remote_fallback.value not in self.peerStreamingBoxes:
				self.peerStreamingBoxes = [config.usage.remote_fallback.value] + self.peerStreamingBoxes
			if config.usage.remote_fallback_import_url.value and config.usage.remote_fallback_import_url.value not in self.peerStreamingBoxes:
				self.peerStreamingBoxes = [config.usage.remote_fallback_import_url.value] + self.peerStreamingBoxes
		self.avahiselect = ConfigSelection(default=peerDefault, choices=self.peerStreamingBoxes)
		self.avahiselect.addNotifier(set_avahiselect_seperate)
		try:
			ipDefault = [int(x) for x in config.usage.remote_fallback.value.split(":")[1][2:].split(".")]
			portDefault = int( config.usage.remote_fallback.value.split(":")[2])
		except:
			ipDefault = [0, 0, 0, 0]
			portDefault = 8001
		self.ip = ConfigIP(default=ipDefault, auto_jump=True)
		self.port = ConfigInteger(default=portDefault, limits=(1,65535))
		self.ip_seperate = ConfigIP( default=ipDefault, auto_jump=True)
		self.port_seperate = ConfigInteger(default=portDefault, limits=(1,65535))

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enable fallback remote receiver"),
			config.usage.remote_fallback_enabled,
			_("Enable remote enigma2 receiver to be tried to tune into services that cannot be tuned into locally (e.g. tuner is occupied or service type is unavailable on the local tuner. Specify complete URL including http:// and port number (normally ...:8001), e.g. http://second_box:8001.")))
		self.list.append(getConfigListEntry(_("Import from remote receiver URL"),
			config.usage.remote_fallback_import,
			_("Import channels and/or EPG from remote receiver URL when receiver is booted")))
		if config.usage.remote_fallback_enabled.value or config.usage.remote_fallback_import.value:
			self.list.append(getConfigListEntry(_("Fallback remote receiver"),
				self.avahiselect,
				_("Destination of fallback remote receiver")))
			if self.avahiselect.value == "ip":
				self.list.append(getConfigListEntry(_("Fallback remote receiver IP"),
					self.ip,
					_("IP of fallback remote receiver")))			
				self.list.append(getConfigListEntry(_("Fallback remote receiver Port"),
					self.port,
					_("Port of fallback remote receiver")))			
			if self.avahiselect.value == "url":
				self.list.append(getConfigListEntry(_("Fallback remote receiver URL"),
					config.usage.remote_fallback,
					_("URL of fallback remote receiver")))
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value:
			self.list.append(getConfigListEntry(_("Import remote receiver URL"),
				self.avahiselect_seperate,
				_("URL of fallback remote receiver")))
			if self.avahiselect_seperate.value == "ip":
				self.list.append(getConfigListEntry(_("Fallback remote receiver IP"),
					self.ip_seperate,
					_("IP of fallback remote receiver")))			
				self.list.append(getConfigListEntry(_("Fallback remote receiver Port"),
					self.port_seperate,
					_("Port of fallback remote receiver")))			
			if self.avahiselect_seperate.value == "url":
				self.list.append(getConfigListEntry(_("Fallback remote receiver URL"),
					config.usage.remote_fallback_import_url,
					_("URL of fallback remote receiver")))
		if config.usage.remote_fallback.value and config.usage.remote_fallback_import.value:
			self.list.append(getConfigListEntry(_("Also import at reboot/restart enigma2"),
				config.usage.remote_fallback_import_restart,
				_("Import channels and/or EPG from remote receiver URL when receiver or enigma2 is restarted")))
			self.list.append(getConfigListEntry(_("Also import when box is leaving standby"),
				config.usage.remote_fallback_import_standby,
				_("Import channels and/or EPG from remote receiver URL also when the receiver is getting out of standby")))
			self.list.append(getConfigListEntry(_("Also import from the extension menu"),
				config.usage.remote_fallback_extension_menu,
				_("Make it possible to manually initiate the channels import and/or EPG via the extension menu")))
			self.list.append(getConfigListEntry(_("Show notification when import channels was successful"),
				config.usage.remote_fallback_ok,
				_("Show notification when import channels and/or EPG from remote receiver URL is completed")))
			self.list.append(getConfigListEntry(_("Show notification when import channels was not successful"),
				config.usage.remote_fallback_nok,
				_("Show notification when import channels and/or EPG from remote receiver URL did not complete")))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def selectionChanged(self):
		if self.force_update_list:
			self["config"].onSelectionChanged.remove(self.selectionChanged)
			self.createSetup()
			self["config"].onSelectionChanged.append(self.selectionChanged)
			self.force_update_list = False
		if not (isinstance(self["config"].getCurrent()[1], ConfigBoolean) or isinstance(self["config"].getCurrent()[1], ConfigSelection)):
			self.force_update_list = True
		self["description"].setText(self.getCurrentDescription())

	def changedEntry(self):
		if isinstance(self["config"].getCurrent()[1], ConfigBoolean) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
			self.createSetup()

	def keyGo(self):
		if self.avahiselect.value == "ip":
			config.usage.remote_fallback.value = "http://%d.%d.%d.%d:%d" % (tuple(self.ip.value) + (self.port.value,))
		elif self.avahiselect.value != "url":
			config.usage.remote_fallback.value = self.avahiselect.value
		if self.avahiselect_seperate.value == "ip":
			config.usage.remote_fallback_import_url.value = "http://%d.%d.%d.%d:%d" % (tuple(self.ip_seperate.value) + (self.port_seperate.value,))
		elif self.avahiselect_seperate.value == "same":
			config.usage.remote_fallback_import_url.value = ""
		elif self.avahiselect_seperate.value != "url":
			config.usage.remote_fallback_import_url.value = self.avahiselect_seperate.value
		if config.usage.remote_fallback_import_url.value == config.usage.remote_fallback.value:
			config.usage.remote_fallback_import_url.value = ""
		config.usage.remote_fallback_enabled.save()
		config.usage.remote_fallback_import.save()
		config.usage.remote_fallback_import_url.save()
		config.usage.remote_fallback_import_restart.save()
		config.usage.remote_fallback_import_standby.save()
		config.usage.remote_fallback_extension_menu.save()
		config.usage.remote_fallback_ok.save()
		config.usage.remote_fallback_nok.save()
		config.usage.remote_fallback.save()
		configfile.save()
		self.close(False)
