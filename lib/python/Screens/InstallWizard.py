from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen, ConfigList
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigBoolean, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigIP, ConfigNothing
from Components.Network import iNetwork
from Components.Opkg import OpkgComponent
from enigma import eDVBDB

config.misc.installwizard = ConfigSubsection()
config.misc.installwizard.hasnetwork = ConfigBoolean(default = False)
config.misc.installwizard.opkgloaded = ConfigBoolean(default = False)
config.misc.installwizard.channellistdownloaded = ConfigBoolean(default = False)

class InstallWizard(Screen, ConfigListScreen):

	STATE_UPDATE = 0
	STATE_CHOISE_CHANNELLIST = 1
	INSTALL_PLUGINS = 2
	SCAN = 3

	def __init__(self, session, args = None):
		Screen.__init__(self, session)

		self.index = args
		self.list = []
		self.doNextStep = False
		ConfigListScreen.__init__(self, self.list)

		if self.index == self.STATE_UPDATE:
			config.misc.installwizard.hasnetwork.value = False
			config.misc.installwizard.opkgloaded.value = False
			modes = {0: " "}
			self.enabled = ConfigSelection(choices = modes, default = 0)
			self.adapters = [adapter for adapter in iNetwork.getAdapterList() if adapter in ('eth0', 'eth1')]
			self.checkNetwork()
		elif self.index == self.STATE_CHOISE_CHANNELLIST:
			self.enabled = ConfigYesNo(default = True, graphic = False)
			modes = {"19e-23e-basis": "Astra1 Astra3 basis", "19e-23e": "Astra 1 Astra 3", "19e-23e-28e": "Astra 1 Astra 2 Astra 3", "13e-19e-23e-28e": "Astra 1 Astra 2 Astra 3 Hotbird", "9e-13e-19e-23e-28e-rotating": "Rotating", "kabelnl": "Kabel-NL"}
			self.channellist_type = ConfigSelection(choices = modes, default = "19e-23e-basis")
			self.createMenu()
		elif self.index == self.INSTALL_PLUGINS:
			self.noplugins = ConfigNothing()
			self.doplugins = ConfigNothing()
			self.createMenu()
		elif self.index == self.SCAN:
			self.noscan = ConfigNothing()
			self.autoscan = ConfigNothing()
			self.manualscan = ConfigNothing()
			self.fastscan = ConfigNothing()
			self.cablescan = ConfigNothing()
			self.createMenu()

	def checkNetwork(self):
		if self.adapters:
			self.adapter = self.adapters.pop(0)
			if iNetwork.getAdapterAttribute(self.adapter, 'up'):
				iNetwork.checkNetworkState(self.checkNetworkStateCallback)
			else:
				iNetwork.restartNetwork(self.restartNetworkCallback)
		else:
			self.createMenu()

	def checkNetworkStateCallback(self, data):
		if data < 3:
			config.misc.installwizard.hasnetwork.value = True
			self.createMenu()
		else:
			self.checkNetwork()

	def restartNetworkCallback(self, retval):
		if retval:
			iNetwork.checkNetworkState(self.checkNetworkStateCallback)
		else:
			self.checkNetwork()

	def createMenu(self):
		try:
			test = self.index
		except:
			return
		self.list = []
		if self.index == self.STATE_UPDATE:
			if config.misc.installwizard.hasnetwork.value:
				ip = ".".join([str(x) for x in iNetwork.getAdapterAttribute(self.adapter, "ip")])
				self.list.append(getConfigListEntry(_("Your internet connection is working (ip: %s)") % ip, self.enabled))
			else:
				self.list.append(getConfigListEntry(_("Your receiver does not have an internet connection"), self.enabled))
		elif self.index == self.STATE_CHOISE_CHANNELLIST:
			self.list.append(getConfigListEntry(_("Install channel list"), self.enabled))
			if self.enabled.value:
				self.list.append(getConfigListEntry(_("Channel list type"), self.channellist_type))
		elif self.index == self.INSTALL_PLUGINS:
			self.list.append(getConfigListEntry(_("No, I do not want to install plugins"), self.noplugins))
			self.list.append(getConfigListEntry(_("Yes, I do want to install plugins"), self.doplugins))
		elif self.index == self.SCAN:
			self.list.append(getConfigListEntry(_("I do not want to perform any service scans"), self.noscan))
			self.list.append(getConfigListEntry(_("Do an automatic service scan now"), self.autoscan))
			self.list.append(getConfigListEntry(_("Do a manual service scan now"), self.manualscan))
			from Plugins.SystemPlugins.FastScan.plugin import getProviderList
			if getProviderList():
				self.list.append(getConfigListEntry(_("Do a fast service scan now"), self.fastscan))
			from Components.NimManager import nimmanager
			if nimmanager.getEnabledNimListOfType("DVB-C"):
				self.list.append(getConfigListEntry(_("Do a cable service scan now"), self.cablescan))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		if self.index == 0:
			return
		ConfigListScreen.keyLeft(self)
		self.createMenu()

	def keyRight(self):
		if self.index == 0:
			return
		ConfigListScreen.keyRight(self)
		self.createMenu()

	def run(self):
		if self.index == self.STATE_UPDATE and config.misc.installwizard.hasnetwork.value:
			self.session.open(InstallWizardOpkgUpdater, self.index, _('Please wait (updating packages)'), OpkgComponent.CMD_UPDATE)
			self.doNextStep = True
		elif self.index == self.STATE_CHOISE_CHANNELLIST:
			if self.enabled.value:
				self.session.open(InstallWizardOpkgUpdater, self.index, _('Please wait (downloading channel list)'), OpkgComponent.CMD_REMOVE, {'package': 'enigma2-plugin-settings-hans-' + self.channellist_type.value})
			self.doNextStep = True
		elif self.index == self.INSTALL_PLUGINS:
			if self["config"].getCurrent()[1] == self.doplugins:
				from PluginBrowser import PluginDownloadBrowser
				self.session.open(PluginDownloadBrowser, 0)
			self.doNextStep = True
		elif self.index == self.SCAN:
			if self["config"].getCurrent()[1] == self.autoscan:
				from Screens.ScanSetup import ScanSimple
				self.session.open(ScanSimple)
			elif self["config"].getCurrent()[1] == self.manualscan:
				from Screens.ScanSetup import ScanSetup
				self.session.open(ScanSetup)
			elif self["config"].getCurrent()[1] == self.fastscan:
				from Plugins.SystemPlugins.FastScan.plugin import FastScanMain
				FastScanMain(self.session)
			elif self["config"].getCurrent()[1] == self.cablescan:
				from Plugins.SystemPlugins.CableScan.plugin import CableScanMain
				CableScanMain(self.session)
			else:
				self.doNextStep = True

class InstallWizardOpkgUpdater(Screen):
	skin = """
	<screen position="c-300,c-25" size="600,50" title=" ">
		<widget source="statusbar" render="Label" position="10,5" zPosition="10" size="e-10,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
	</screen>"""

	def __init__(self, session, index, info, cmd, pkg = None):
		self.skin = InstallWizardOpkgUpdater.skin
		Screen.__init__(self, session)

		self["statusbar"] = StaticText(info)

		self.pkg = pkg
		self.index = index
		self.state = 0

		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)

		if self.index == InstallWizard.STATE_CHOISE_CHANNELLIST:
			self.opkg.startCmd(cmd, {'package': 'enigma2-plugin-settings-*'})
		else:
			self.opkg.startCmd(cmd, pkg)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_DONE:
			if self.index == InstallWizard.STATE_UPDATE:
				config.misc.installwizard.opkgloaded.value = True
			elif self.index == InstallWizard.STATE_CHOISE_CHANNELLIST:
				if self.state == 0:
					self.opkg.startCmd(OpkgComponent.CMD_INSTALL, self.pkg)
					self.state = 1
					return
				else:
					config.misc.installwizard.channellistdownloaded.value = True
					eDVBDB.getInstance().reloadBouquets()
					eDVBDB.getInstance().reloadServicelist()
			self.close()
