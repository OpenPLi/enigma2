from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import ConfigSelection, getConfigListEntry, ConfigAction
from Components.ScrollLabel import ScrollLabel
from Tools.GetEcmInfo import GetEcmInfo

import os
from Tools.camcontrol import CamControl
from enigma import eTimer

class SoftcamSetup(Screen, ConfigListScreen):
	skin = """
	<screen name="SoftcamSetup" position="center,center" size="560,450" >
		<widget name="config" position="5,10" size="550,140" />
		<widget name="info" position="5,150" size="550,250" font="Fixed;18" />
		<ePixmap name="red" position="0,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap name="green" position="140,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		<ePixmap name="yellow" position="280,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
		<ePixmap name="blue" position="420,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
		<widget name="key_red" position="0,410" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;20" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_green" position="140,410" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;20" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_yellow" position="280,410" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;20" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_blue" position="420,410" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;20" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)

		self.setup_title = _("Softcam setup")
		self.setTitle(self.setup_title)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "CiSelectionActions"],
			{
				"cancel": self.cancel,
				"green": self.save,
				"red": self.cancel,
				"yellow": self.extraSetup,
				"blue": self.ppanelShortcut,
			},-1)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = session)

		self.softcam = CamControl('softcam')
		self.cardserver = CamControl('cardserver')

		self.ecminfo = GetEcmInfo()
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		self["info"] = ScrollLabel("".join(ecmInfo))
		self.EcmInfoPollTimer = eTimer()
		self.EcmInfoPollTimer.callback.append(self.setEcmInfo)
		self.EcmInfoPollTimer.start(1000)

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["key_yellow"] = Label(_("Extra setup"))
		self["key_blue"] = Label(_("Info"))

		self.createConfig()

	def createConfig(self):
		self.list = []
		self.softcams_list = self.softcam.getList()
		self.cardservers_list = self.cardserver.getList()
		self.softcams = ConfigSelection(choices = self.softcams_list)
		self.softcams.value = self.softcam.current()
		self.list.append(getConfigListEntry(_("Select Softcam"), self.softcams))
		if self.cardservers_list:
			self.cardservers = ConfigSelection(choices = self.cardservers_list)
			self.cardservers.value = self.cardserver.current()
			self.list.append(getConfigListEntry(_("Select Card Server"), self.cardservers))
		self.list.append(getConfigListEntry(_("Restart softcam"), ConfigAction(self.restart, "s")))
		if self.cardservers_list:
			self.list.append(getConfigListEntry(_("Restart cardserver"), ConfigAction(self.restart, "c")))
			self.list.append(getConfigListEntry(_("Restart both"), ConfigAction(self.restart, "sc")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def setEcmInfo(self):
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		if newEcmFound:
			self["info"].setText("".join(ecmInfo))

	def ppanelShortcut(self):
		ppanelFileName = '/etc/ppanels/' + self.softcams.value + '.xml'
		if "oscam" in self.softcams.value.lower() and os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/OscamStatus/plugin.py'):
			from Plugins.Extensions.OscamStatus.plugin import OscamStatus
			self.session.open(OscamStatus)
		elif "cccam" in self.softcams.value.lower() and os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/CCcamInfo/plugin.py'):
			from Plugins.Extensions.CCcamInfo.plugin import CCcamInfoMain
			self.session.open(CCcamInfoMain)
		elif os.path.isfile(ppanelFileName) and os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/PPanel/plugin.py'):
			from Plugins.Extensions.PPanel.ppanel import PPanel
			self.session.open(PPanel, name=self.softcams.value + ' PPanel', node=None, filename=ppanelFileName, deletenode=None)
		else:
			return 0

	def restart(self, what):
		self.what = what
		if "s" in what:
			if "c" in what:
				msg = _("Please wait, restarting softcam and cardserver.")
			else:
				msg  = _("Please wait, restarting softcam.")
		elif "c" in what:
			msg = _("Please wait, restarting cardserver.")
		self.mbox = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.doStop)
		self.activityTimer.start(100, False)

	def doStop(self):
		self.activityTimer.stop()
		if "c" in self.what:
			self.cardserver.command('stop')
		if "s" in self.what:
			self.softcam.command('stop')
		self.oldref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.doStart)
		self.activityTimer.start(1000, False)

	def doStart(self):
		self.activityTimer.stop()
		del self.activityTimer
		if "c" in self.what:
			self.cardserver.select(self.cardservers.value)
			self.cardserver.command('start')
		if "s" in self.what:
			self.softcam.select(self.softcams.value)
			self.softcam.command('start')
		if self.mbox:
			self.mbox.close()
		self.close()
		self.session.nav.playService(self.oldref, adjust=False)

	def restartCardServer(self):
		if hasattr(self, 'cardservers'):
			self.restart("c")

	def restartSoftcam(self):
		self.restart("s")

	def save(self):
		what = ''
		if hasattr(self, 'cardservers') and (self.cardservers.value != self.cardserver.current()):
			what = 'sc'
		elif self.softcams.value != self.softcam.current():
			what = 's'
		if what:
			self.restart(what)
		else:
			self.close()

	def cancel(self):
		self.close()

	def extraSetup(self):
		text = _("Select option:")
		menu = []
		self.add_to_softcam = ''
		self.add_to_cardserver = ''
		softcam_status = _("Enable")
		if os.path.exists('/etc/rc3.d/S50softcam'):
			softcam_status = _("Disable")
		menu.append((softcam_status + _(" autostart softcam"), "autostart_softcam"))
		self.current_softcam = self.softcam.current()
		self.current_cardserver = self.cardserver.current()
		if self.current_softcam != None and "softcam.None" not in self.current_softcam:
			if not os.path.exists('/etc/init.d/cardserver.' + self.current_softcam):
				menu.append((_("Add current as cardserver"), "as_cardserver"))
				self.add_to_softcam = 'add'
			else:
				menu.append((_("Remove current as cardserver"), "as_cardserver"))
				self.add_to_softcam = 'remove'
		if self.cardservers_list:
			cardserver_status = _("Enable")
			if os.path.exists('/etc/rcS.d/S45cardserver'):
				cardserver_status = _("Disable")
			menu.append((cardserver_status +_(" autostart cardserver"), "autostart_cardserver"))
			if self.current_cardserver != None and "cardserver.None" not in self.current_cardserver:
				if not os.path.exists('/etc/init.d/softcam.' + self.current_cardserver):
					menu.append((_("Add current as softcam"), "as_softcam"))
					self.add_to_cardserver = 'add'
				else:
					menu.append((_("Remove current as softcam"), "as_softcam"))
					self.add_to_cardserver = 'remove'
		def extraAction(choice):
			if choice:
				if choice[1] == "autostart_softcam":
					self.setUnsetAutostart(cam='softcam')
				elif choice[1] == "autostart_cardserver":
					self.setUnsetAutostart(cam='cardserver')
				elif choice[1] == "as_cardserver":
					self.setUnsetFile(cam='softcam')
				elif choice[1] == "as_softcam":
					self.setUnsetFile(cam='cardserver')
				self.createConfig()
		dlg = self.session.openWithCallback(extraAction, ChoiceBox, title=text, list=menu)
		dlg.setTitle(_("Extra setup"))

	def setUnsetFile(self, cam=''):
		msg = ""
		if cam == 'cardserver':
			if self.add_to_cardserver == 'add':
				os.system("cp /etc/init.d/cardserver.%s /etc/init.d/softcam.%s" % (self.current_cardserver, self.current_cardserver))
				if not os.path.exists('/etc/init.d/softcam.%s' % self.current_cardserver):
					msg = _("Failed create file!")
				else:
					msg = _("File added!")
				if not os.path.exists('/etc/init.d/softcam.None'):
					os.system("echo '# Placeholder for no cam' > /etc/init.d/softcam.None && chmod 755 /etc/init.d/softcam.None")
			elif self.add_to_cardserver == 'remove':
				os.system("rm -rf /etc/init.d/softcam.%s" % self.current_cardserver)
				if not os.path.exists('/etc/init.d/softcam.%s' % self.current_cardserver):
					msg = _("File remove!")
				else:
					msg = _("Failed remove file!")
		elif cam == 'softcam':
			if self.add_to_softcam == 'add':
				os.system("cp /etc/init.d/softcam.%s /etc/init.d/cardserver.%s" % (self.current_softcam, self.current_softcam))
				if not os.path.exists('/etc/init.d/cardserver.%s' % self.current_softcam):
					msg = _("Failed create file!")
				else:
					msg = _("File added!")
					if not os.path.exists('/etc/init.d/cardserver.None'):
						os.system("echo '# Placeholder for no cs' > /etc/init.d/cardserver.None && chmod 755 /etc/init.d/cardserver.None")
			elif self.add_to_softcam == 'remove':
				if self.current_cardserver != None and "cardserver.None" not in self.current_cardserver:
					os.system("/etc/init.d/cardserver.%s stop" % self.current_softcam)
				os.system("rm -rf /etc/init.d/cardserver.%s" % self.current_softcam)
				if not os.path.exists('/etc/init.d/cardserver.%s' % self.current_softcam):
					msg = _("File remove!")
					current_list_cardservers = self.cardserver.getList()
					if len(current_list_cardservers) == 1:
						if "None" in str(current_list_cardservers[0]):
							os.system("rm -rf /etc/init.d/cardserver.None")
				else:
					msg = _("Failed remove file!")
		if msg:
			self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=3)

	def setUnsetAutostart(self, cam=''):
		msg = ""
		if cam == 'cardserver':
			if not os.path.exists('/etc/init.d/cardserver.None'):
				os.system("echo '# Placeholder for no cs' > /etc/init.d/cardserver.None && chmod 755 /etc/init.d/cardserver.None")
			if os.path.exists('/etc/rcS.d/S45cardserver'):
				os.system("update-rc.d -f cardserver remove")
				if not os.path.exists('/etc/rcS.d/S45cardserver'):
					msg = _("Autostart disabled!")
				else:
					msg = _("Failed disable autostart!")
			else:
				if not os.path.exists('/etc/init.d/cardserver'):
					os.system("ln /etc/init.d/cardserver /etc/init.d/cardserver.None")
				os.system("update-rc.d cardserver start 45 S .")
				if os.path.exists('/etc/rcS.d/S45cardserver'):
					msg = _("Autostart enabled!")
				else:
					msg = _("Failed create autostart!")
		elif cam == 'softcam':
			if not os.path.exists('/etc/init.d/softcam.None'):
				os.system("echo '# Placeholder for no cam' > /etc/init.d/softcam.None && chmod 755 /etc/init.d/softcam.None")
			if os.path.exists('/etc/rc3.d/S50softcam'):
				os.system("update-rc.d -f softcam remove")
				if not os.path.exists('/etc/rc3.d/S50softcam'):
					msg = _("Autostart disabled!")
				else:
					msg = _("Failed disable autostart!")
			else:
				if not os.path.exists('/etc/init.d/softcam'):
					os.system("ln /etc/init.d/softcam /etc/init.d/softcam.None")
				os.system("update-rc.d softcam defaults 50")
				if os.path.exists('/etc/rc3.d/S50softcam'):
					msg = _("Autostart enabled!")
				else:
					msg = _("Failed create autostart!")
		if msg:
			self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=3)
