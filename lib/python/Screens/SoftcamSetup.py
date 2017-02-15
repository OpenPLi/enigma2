from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.FileList import FileEntryComponent, FileList
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Button import Button
from Components.Label import Label
from Components.config import config, ConfigElement, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_OK
from Components.ConfigList import ConfigList
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Tools.GetEcmInfo import GetEcmInfo

import os
from Tools.camcontrol import CamControl
from enigma import eTimer, eDVBCI_UI, eListboxPythonStringContent, eListboxPythonConfigContent

class ConfigAction(ConfigElement):
	def __init__(self, action, *args):
		ConfigElement.__init__(self)
		self.value = "(OK)"
		self.action = action
		self.actionargs = args
	def handleKey(self, key):
		if (key == KEY_OK):
			self.action(*self.actionargs)
	def getMulti(self, dummy):
		pass

class SoftcamSetup(Screen, ConfigListScreen):
	skin = """
	<screen name="SoftcamSetup" position="center,center" size="560,450" >
		<widget name="config" position="5,10" size="550,90" />
		<widget name="info" position="5,100" size="550,300" font="Fixed;18" />
		<ePixmap name="red" position="0,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap name="green" position="140,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		<ePixmap name="blue" position="420,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
		<widget name="key_red" position="0,410" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_green" position="140,410" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_blue" position="420,410" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
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
				"blue": self.ppanelShortcut,
			},-1)

		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session = session)

		self.softcam = CamControl('softcam')
		self.cardserver = CamControl('cardserver')

		self.ecminfo = GetEcmInfo()
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		self["info"] = ScrollLabel("".join(ecmInfo))
		self.EcmInfoPollTimer = eTimer()
		self.EcmInfoPollTimer.callback.append(self.setEcmInfo)
		self.EcmInfoPollTimer.start(1000)

		softcams = self.softcam.getList()
		cardservers = self.cardserver.getList()

		self.softcams = ConfigSelection(choices = softcams)
		self.softcams.value = self.softcam.current()

		self.list.append(getConfigListEntry(_("Select Softcam"), self.softcams))
		if cardservers:
			self.cardservers = ConfigSelection(choices = cardservers)
			self.cardservers.value = self.cardserver.current()
			self.list.append(getConfigListEntry(_("Select Card Server"), self.cardservers))

		self.list.append(getConfigListEntry(_("Restart softcam"), ConfigAction(self.restart, "s")))
		if cardservers:
			self.list.append(getConfigListEntry(_("Restart cardserver"), ConfigAction(self.restart, "c")))
			self.list.append(getConfigListEntry(_("Restart both"), ConfigAction(self.restart, "sc")))

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["key_blue"] = Label(_("Info"))

	def setEcmInfo(self):
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		if newEcmFound:
			self["info"].setText("".join(ecmInfo))

	def ppanelShortcut(self):
		if "oscam" in self.softcams.value.lower() and os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/OscamStatus/plugin.py'):
			from Plugins.Extensions.OscamStatus.plugin import OscamStatus
			self.session.open(OscamStatus)
		ppanelFileName = '/etc/ppanels/' + self.softcams.value + '.xml'
		if os.path.isfile(ppanelFileName) and os.path.isfile('/usr/lib/enigma2/python/Plugins/Extensions/PPanel/plugin.py'):
			from Plugins.Extensions.PPanel.ppanel import PPanel
			self.session.open(PPanel, name = self.softcams.value + ' PPanel', node = None, filename = ppanelFileName, deletenode = None)
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
		self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		# Delay a second to give 'em a chance to stop
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
		self.session.nav.playService(self.oldref)
		del self.oldref

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
