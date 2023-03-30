from calendar import timegm
from datetime import datetime
from json import load
from os import listdir
from time import altzone, gmtime, strftime
from urllib.request import urlopen

from enigma import eTimer, eDVBDB
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.TextBox import TextBox
from Screens.About import CommitInfo
from Components.config import config
from Components.ActionMap import ActionMap
from Components.Opkg import OpkgComponent
from Components.Language import language
from Components.Sources.StaticText import StaticText
from Components.Slider import Slider
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists
from Tools.HardwareInfo import HardwareInfo


class UpdatePlugin(Screen, ProtectedScreen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		ProtectedScreen.__init__(self)

		self.title = _("Software update")
		self.slider = Slider(0, 100)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = StaticText(_("Please wait..."))
		self["status"] = self.status
		self.package = StaticText(_("Package list update"))
		self["package"] = self.package

		self.packages = 0
		self.error = 0
		self.processed_packages = []
		self.total_packages = 0
		self.update_step = 0

		self.channellist_only = 0
		self.channellist_name = ''
		self.updating = False
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onClose.append(self.__close)

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)

		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.callback.append(self.checkTraficLight)
		self.activityTimer.callback.append(self.doActivityTimer)
		self.activityTimer.start(100, True)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and\
			(not config.ParentalControl.config_sections.main_menu.value and not config.ParentalControl.config_sections.configuration.value or hasattr(self.session, 'infobar') and self.session.infobar is None) and\
			config.ParentalControl.config_sections.software_update.value

	def checkTraficLight(self):
		self.activityTimer.callback.remove(self.checkTraficLight)
		self.activityTimer.start(100, False)
		status = None
		message = None
		abort = False
		picon = MessageBox.TYPE_ERROR
		url = "https://openpli.org/trafficlight"

		# try to fetch the trafficlight json from the website
		try:
			status = dict(load(urlopen(url, timeout=5)))
			print("[SoftwareUpdate] status is: ", status)
		except Exception as er:
			print('[UpdatePlugin] Error in get status', er)

		# process the status fetched
		if status is not None:

			try:
				# get image version and machine name
				machine = HardwareInfo().get_machine_name()
				version = open("/etc/issue").readlines()[-2].split()[1]

				# do we have an entry for this version
				if (version in status or 'all' in status) and (machine in status[version]['machines'] or 'all' in status[version]['machines']):
					if 'abort' in status[version]:
						abort = status[version]['abort']
					if 'from' in status[version]:
						starttime = datetime.strptime(status[version]['from'], '%Y%m%d%H%M%S')
					else:
						starttime = 0
					if 'to' in status[version]:
						endtime = datetime.strptime(status[version]['to'], '%Y%m%d%H%M%S')
					else:
						endtime = datetime.now() + 1
					if 'message' in status[version]:
						if (starttime <= datetime.now() and endtime >= datetime.now()):
							message = status[version]['message']

				# check if we have per-language messages
				if isinstance(message, dict):
					lang = language.getLanguage()
					if lang in message:
						message = message[lang]
					elif 'en_EN' in message:
						message = message['en_EN']
					else:
						message = _("The current image might not be stable.\nFor more information see %s.") % ("https://forums.openpli.org")

			except Exception as er:
				print("[UpdatePlugin] status error", er)
				message = _("The current image might not be stable.\nFor more information see %s.") % ("https://forums.openpli.org")

		# or display a generic warning if fetching failed
		else:
			message = _("The status of the current image could not be checked because %s can not be reached.") % ("https://openpli.org")

		# show the user the message first
		if message is not None:
			if abort:
				self.session.openWithCallback(self.close, MessageBox, message, type=MessageBox.TYPE_MESSAGE, picon=picon)
			else:
				message += "\n\n" + _("Do you want to update your receiver?")
				self.session.openWithCallback(self.startActualUpdate, MessageBox, message, picon=picon)

		# no message, continue with the update
		else:
			self.startActualUpdate(True)

	def getLatestImageTimestamp(self):
		def gettime(url):
			try:
				return strftime("%Y-%m-%d %H:%M:%S", gmtime(timegm(urlopen("%s/Packages.gz" % url).info().getdate('Last-Modified')) - altzone))
			except Exception as er:
				print('[UpdatePlugin] Error in get timestamp', er)
				return ""
		return sorted([gettime(open("/etc/opkg/%s" % file, "r").readlines()[0].split()[2]) for file in listdir("/etc/opkg") if not file.startswith("3rd-party") and file not in ("arch.conf", "opkg.conf", "picons-feed.conf")], reverse=True)[0]

	def startActualUpdate(self, answer):
		if answer:
			self.updating = True
			self.opkg.startCmd(OpkgComponent.CMD_UPDATE)
		else:
			self.close()

	def doActivityTimer(self):
		self.activity += 1
		if self.activity == 100:
			self.activity = 0
		self.activityslider.value = self.activity

	def showUpdateCompletedMessage(self):
		self.setEndMessage(ngettext("Update completed, %d package was installed.", "Update completed, %d packages were installed.", self.packages) % self.packages)

	def opkgCallback(self, event, param):
		if event == OpkgComponent.EVENT_DOWNLOAD:
			self.status.text = _("Downloading")
		elif event == OpkgComponent.EVENT_UPGRADE:
			self.package.text = param
			self.status.text = _("Updating") + ": %s/%s" % (self.packages, self.total_packages)
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
			self.slider.value = int(self.update_step * self.packages)
		elif event == OpkgComponent.EVENT_INSTALL:
			self.package.text = param
			self.status.text = _("Installing")
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_REMOVE:
			self.package.text = param
			self.status.text = _("Removing")
			if param not in self.processed_packages:
				self.processed_packages.append(param)
				self.packages += 1
		elif event == OpkgComponent.EVENT_CONFIGURING:
			self.package.text = param
			self.status.text = _("Configuring")
		elif event == OpkgComponent.EVENT_MODIFIED:
			if config.plugins.softwaremanager.overwriteConfigFiles.value in ("N", "Y"):
				self.opkg.write(True and config.plugins.softwaremanager.overwriteConfigFiles.value)
			else:
				self.session.openWithCallback(
					self.modificationCallback,
					MessageBox,
					_("A configuration file (%s) has been modified since it was installed. Would you like to keep the modified version?") % (param)
				)
		elif event == OpkgComponent.EVENT_ERROR:
			self.error += 1
		elif event == OpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.opkg.startCmd(OpkgComponent.CMD_UPGRADE_LIST)
			elif self.opkg.currentCommand == OpkgComponent.CMD_UPGRADE_LIST:
				self.total_packages = len(self.opkg.getFetchedList())
				if self.total_packages:
					self.update_step = 100 / self.total_packages
					latestImageTimestamp = self.getLatestImageTimestamp()
					if latestImageTimestamp:
						message = _("Do you want to update your receiver to %s?") % latestImageTimestamp + "\n"
					else:
						message = _("Do you want to update your receiver?") + "\n"
					message += "(" + (ngettext("%s updated package available", "%s updated packages available", self.total_packages) % self.total_packages) + ")"
					if self.total_packages > 150:
						choices = [(_("Update and reboot"), "cold")]
						message += " " + _("Reflash recommended!")
					else:
						choices = [(_("Update and reboot (recommended)"), "cold"),
						(_("Update and ask to reboot"), "hot")]
					choices.append((_("Update channel list only"), "channels"))
					choices.append((_("Show packages to be updated"), "showlist"))
				else:
					message = _("No updates available")
					choices = []
				if fileExists("/home/root/opkgupgrade.log"):
					choices.append((_("Show latest update log"), "log"))
				choices.append((_("Show latest commits"), "commits"))
				choices.append((_("Cancel"), ""))
				self.session.openWithCallback(self.startActualUpgrade, ChoiceBox, title=message, list=choices, windowTitle=self.title)
			elif self.channellist_only > 0:
				if self.channellist_only == 1:
					self.setEndMessage(_("Could not find installed channel list."))
				elif self.channellist_only == 2:
					self.slider.value = 50
					self.opkg.startCmd(OpkgComponent.CMD_REMOVE, {'package': self.channellist_name})
					self.channellist_only += 1
				elif self.channellist_only == 3:
					self.slider.value = 75
					self.opkg.startCmd(OpkgComponent.CMD_INSTALL, {'package': self.channellist_name})
					self.channellist_only += 1
				elif self.channellist_only == 4:
					self.showUpdateCompletedMessage()
					eDVBDB.getInstance().reloadBouquets()
					eDVBDB.getInstance().reloadServicelist()
			elif self.error == 0:
				self.showUpdateCompletedMessage()
			else:
				self.activityTimer.stop()
				self.activityslider.value = 0
				error = _("Your receiver might be unusable now. Please consult the manual for further assistance before rebooting your receiver.")
				if self.packages == 0:
					error = _("No updates available. Please try again later.")
				if self.updating:
					error = _("Update failed. Your receiver does not have a working internet connection.")
				self.status.text = _("Error") + " - " + error
		elif event == OpkgComponent.EVENT_LISTITEM:
			if 'enigma2-plugin-settings-' in param[0] and self.channellist_only > 0:
				self.channellist_name = param[0]
				self.channellist_only = 2

	def setEndMessage(self, txt):
		self.slider.value = 100
		self.activityTimer.stop()
		self.activityslider.value = 0
		self.package.text = txt
		self.status.text = _("Press OK on your remote control to continue.")

	def startActualUpgrade(self, answer):
		if not answer or not answer[1]:
			self.close()
			return
		if answer[1] == "cold":
			self.session.open(TryQuitMainloop, retvalue=42)
			self.close()
		elif answer[1] == "channels":
			self.channellist_only = 1
			self.slider.value = 25
			self.opkg.startCmd(OpkgComponent.CMD_LIST, args={'installed_only': True})
		elif answer[1] == "commits":
			self.session.openWithCallback(boundFunction(self.opkgCallback, OpkgComponent.EVENT_DONE, None), CommitInfo)
		elif answer[1] == "showlist":
			text = "\n".join([x[0] for x in sorted(self.opkg.getFetchedList(), key=lambda d: d[0])])
			self.session.openWithCallback(boundFunction(self.opkgCallback, OpkgComponent.EVENT_DONE, None), TextBox, text, _("Packages to update"), True)
		elif answer[1] == "log":
			text = open("/home/root/opkgupgrade.log", "r").read()
			self.session.openWithCallback(boundFunction(self.opkgCallback, OpkgComponent.EVENT_DONE, None), TextBox, text, _("Latest update log"), True)
		else:
			self.opkg.startCmd(OpkgComponent.CMD_UPGRADE, args={'test_only': False})

	def modificationCallback(self, res):
		self.opkg.write(res and "N" or "Y")

	def exit(self):
		if not self.opkg.isRunning():
			if self.packages != 0 and self.error == 0 and self.channellist_only == 0:
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Update completed. Do you want to reboot your receiver?"))
			else:
				self.close()
		else:
			if not self.updating:
				self.close()

	def exitAnswer(self, result):
		if result is not None and result:
			self.session.open(TryQuitMainloop, retvalue=2)
		self.close()

	def __close(self):
		self.opkg.removeCallback(self.opkgCallback)
