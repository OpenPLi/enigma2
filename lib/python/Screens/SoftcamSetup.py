from Screens.Setup import Setup
from Screens.MessageBox import MessageBox
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.config import ConfigSelection, ConfigAction
from Components.ScrollLabel import ScrollLabel
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Tools.GetEcmInfo import GetEcmInfo
from Components.Sources.StaticText import StaticText

import os
from Tools.camcontrol import CamControl
from enigma import eTimer


class SoftcamSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, blue_button={'function': self.key_blue, 'helptext': _("Show softcam information")})
		self.setTitle(_("Softcam setup"))
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

		self.softcams = ConfigSelection(choices=softcams)
		self.softcams.value = self.softcam.current()

		self.softcams_text = _("Select Softcam")
		self.list.append((self.softcams_text, self.softcams))
		if cardservers:
			self.cardservers = ConfigSelection(choices=cardservers)
			self.cardservers.value = self.cardserver.current()
			self.list.append((_("Select Card Server"), self.cardservers))

		self.list.append((_("Restart softcam"), ConfigAction(self.restart, "s")))
		if cardservers:
			self.list.append((_("Restart cardserver"), ConfigAction(self.restart, "c")))
			self.list.append((_("Restart both"), ConfigAction(self.restart, "sc")))
		self.blueButton()

	def changedEntry(self):
		if self["config"].getCurrent()[0] == self.softcams_text:
			self.blueButton()

	def blueButton(self):
		if self.softcams.value and self.softcams.value.lower() != "none":
			self["key_blue"].setText(_("Info"))
		else:
			self["key_blue"].setText("")

	def setEcmInfo(self):
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		if newEcmFound:
			self["info"].setText("".join(ecmInfo))

	def key_blue(self):
		ppanelFileName = '/etc/ppanels/' + self.softcams.value + '.xml'
		if "oscam" in self.softcams.value.lower() and os.path.isfile(resolveFilename(SCOPE_PLUGINS, 'Extensions/OscamStatus/plugin.pyc')):
			from Plugins.Extensions.OscamStatus.plugin import OscamStatus
			self.session.open(OscamStatus)
		elif "cccam" in self.softcams.value.lower() and os.path.isfile(resolveFilename(SCOPE_PLUGINS, 'Extensions/CCcamInfo/plugin.pyc')):
			from Plugins.Extensions.CCcamInfo.plugin import CCcamInfoMain
			self.session.open(CCcamInfoMain)
		elif os.path.isfile(ppanelFileName) and os.path.isfile(resolveFilename(SCOPE_PLUGINS, 'Extensions/PPanel/plugin.pyc')):
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
				msg = _("Please wait, restarting softcam.")
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

	def saveAll(self):
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
