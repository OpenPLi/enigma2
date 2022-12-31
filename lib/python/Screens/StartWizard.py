from Screens.Wizard import wizardManager
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Tools.HardwareInfo import HardwareInfo
try:
	from Plugins.SystemPlugins.OSDPositionSetup.overscanwizard import OverscanWizard
except:
	OverscanWizard = None

from Components.Network import iNetwork, NetworkCheck
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.config import config, ConfigBoolean, configfile
from Screens.LanguageSelection import LanguageWizard
from enigma import eConsoleAppContainer, eTimer, eActionMap, quitMainloop

import os

config.misc.firstrun = ConfigBoolean(default=True)
config.misc.languageselected = ConfigBoolean(default=True)
config.misc.do_overscanwizard = ConfigBoolean(default=OverscanWizard and config.skin.primary_skin.value == "PLi-FullNightHD/skin.xml")


class StartWizard(WizardLanguage, Rc):
	def __init__(self, session, silent=True, showSteps=False, neededTag=None):
		self.xmlfile = ["startwizard.xml"]
		WizardLanguage.__init__(self, session, showSteps=False)
		Rc.__init__(self)
		self["wizard"] = Pixmap()

	def markDone(self):
		# setup remote control, all stb have same settings except dm8000 which uses a different settings
		if HardwareInfo().get_device_name() == 'dm8000':
			config.misc.rcused.value = 0
		else:
			config.misc.rcused.value = 1
		config.misc.rcused.save()

		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()


def setLanguageFromBackup(backupfile):
	try:
		import tarfile
		tar = tarfile.open(backupfile)
		for member in tar.getmembers():
			if member.name == 'etc/enigma2/settings':
				for line in tar.extractfile(member):
					line = line.decode()
					if line.startswith('config.osd.language'):
						languageToSelect = line.strip().split('=')[1]
						if languageToSelect:
							from Components.Language import language
							language.activateLanguage(languageToSelect)
							break
		tar.close()
	except:
		pass


def checkForAvailableAutoBackup():
	for backupfile in ["/media/%s/backup/PLi-AutoBackup.tar.gz" % media for media in os.listdir("/media/") if os.path.isdir(os.path.join("/media/", media))]:
		if os.path.isfile(backupfile):
			setLanguageFromBackup(backupfile)
			return True


class AutoRestoreWizard(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Do you want to autorestore settings?"), type=MessageBox.TYPE_YESNO, timeout=20, default=True, simple=True)

	def close(self, value):
		if value:
			if os.path.isfile("/etc/.doNotAutoInstall"):
				os.unlink("/etc/.doNotAutoInstall")
				MessageBox.close(self, 43)
			else:
				# restore network config first, we need it to autoinstall
				self.console = eConsoleAppContainer()
				self.console.execute('/etc/init.d/settings-restore.sh network')
				iNetwork.restartNetwork()
				networkCheck = NetworkCheck()
				networkCheck.Start(10)
				self.session.open(AutoInstall)
		MessageBox.close(self)


class AutoInstall(Screen):
	skin = """<screen name="AutoInstall" position="fill" flags="wfNoBorder">
		<panel position="left" size="5%,*"/>
		<panel position="right" size="5%,*"/>
		<panel position="top" size="*,5%"/>
		<panel position="bottom" size="*,5%"/>
		<widget name="header" position="top" size="*,48" font="Regular;38" noWrap="1"/>
		<widget name="progress" position="top" size="*,24" backgroundColor="#00242424"/>
		<eLabel position="top" size="*,2"/>
		<widget name="AboutScrollLabel" font="Fixed;20" position="fill"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)
		self["AboutScrollLabel"] = ScrollLabel("", showscrollbar=False)
		self["header"] = Label(_("Autoinstalling please wait for packages being updated"))

		self.logfile = open('/home/root/autoinstall.log', 'w')
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.appClosed)
		self.container.dataAvail.append(self.dataAvail)
		self.package = None

		import glob
		mac_address = open('/sys/class/net/eth0/address', 'r').readline().strip().replace(":", "")
		autoinstallfiles = glob.glob('/media/*/backup/autoinstall%s' % mac_address) + glob.glob('/media/net/*/backup/autoinstall%s' % mac_address)
		if not autoinstallfiles:
			autoinstallfiles = glob.glob('/media/*/backup/autoinstall') + glob.glob('/media/net/*/backup/autoinstall')
		autoinstallfiles.sort(key=os.path.getmtime, reverse=True)
		for autoinstallfile in autoinstallfiles:
			if os.path.isfile(autoinstallfile):
				autoinstalldir = os.path.dirname(autoinstallfile)
				self.packages = [package.strip() for package in open(autoinstallfile).readlines()] + [os.path.join(autoinstalldir, file) for file in os.listdir(autoinstalldir) if file.endswith(".ipk")]
				if self.packages:
					self.number_of_packages = len(self.packages)
					# make sure we have a valid package list before attempting to restore packages
					self.container.execute("opkg update")
					return

		self.abort()

	def run_console(self):
		self["progress"].setValue(100 * (self.number_of_packages - len(self.packages)) / self.number_of_packages)
		try:
			open("/proc/progress", "w").write(str(self["progress"].value))
		except IOError:
			pass
		self.package = self.packages.pop(0)
		self["header"].setText(_("Autoinstalling %s") % self.package + " - %s%%" % self["progress"].value)
		try:
			if self.container.execute('opkg install "%s"' % self.package):
				raise Exception("failed to execute command!")
				self.appClosed(True)
		except Exception as e:
			self.appClosed(True)

	def dataAvail(self, data):
		if isinstance(data, bytes):
			data = data.decode()
		self["AboutScrollLabel"].appendText(data)
		self.logfile.write(data)

	def appClosed(self, retval=False):
		if retval:
			if self.package:
				self.dataAvail("An error occurred during installing %s - Please try again later\n" % self.package)
			else:
				self.dataAvail("An error occurred during opkg update - Please try again later\n")
		installed = [line.strip().split(":", 1)[1].strip() for line in open('/var/lib/opkg/status').readlines() if line.startswith('Package:')]
		self.packages = [package for package in self.packages if package not in installed]
		if self.packages:
			self.run_console()
		else:
			self["progress"].setValue(100)
			self["header"].setText(_("Autoinstalling Completed"))
			self.delay = eTimer()
			self.delay.callback.append(self.abort)
			eActionMap.getInstance().bindAction('', 0, self.abort)
			self.delay.startLongTimer(5)

	def abort(self, key=None, flag=None):
		if hasattr(self, 'delay'):
			self.delay.stop()
			eActionMap.getInstance().unbindAction('', self.abort)
			self.container.appClosed.remove(self.appClosed)
			self.container.dataAvail.remove(self.dataAvail)
		self.container = None
		self.logfile.close()
		quitMainloop(43)


if not os.path.isfile("/etc/installed"):
	from Components.Console import Console
	Console().ePopen("opkg list_installed | cut -d ' ' -f 1 > /etc/installed;chmod 444 /etc/installed")

wizardManager.registerWizard(AutoRestoreWizard, config.misc.languageselected.value and config.misc.firstrun.value and checkForAvailableAutoBackup(), priority=0)
wizardManager.registerWizard(LanguageWizard, config.misc.languageselected.value, priority=10)
if OverscanWizard:
	wizardManager.registerWizard(OverscanWizard, config.misc.do_overscanwizard.value, priority=30)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority=40)
