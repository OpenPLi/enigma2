from Wizard import wizardManager
from Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Tools.HardwareInfo import HardwareInfo
try:
	from Plugins.SystemPlugins.OSDPositionSetup.overscanwizard import OverscanWizard
except:
	OverscanWizard = None

from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.config import config, ConfigBoolean, configfile
from LanguageSelection import LanguageWizard
from enigma import eConsoleAppContainer

import os

config.misc.firstrun = ConfigBoolean(default = True)
config.misc.languageselected = ConfigBoolean(default = True)
config.misc.do_overscanwizard = ConfigBoolean(default = OverscanWizard and config.skin.primary_skin.value == "PLi-FullNightHD/skin.xml")

class StartWizard(WizardLanguage, Rc):
	def __init__(self, session, silent = True, showSteps = False, neededTag = None):
		self.xmlfile = ["startwizard.xml"]
		WizardLanguage.__init__(self, session, showSteps = False)
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

def checkForAvailableAutoBackup():
	for dir in [name for name in os.listdir("/media/") if os.path.isdir(os.path.join("/media/", name))]:
		if os.path.isfile("/media/%s/backup/PLi-AutoBackup.tar.gz" % dir):
			return True
	return False

class AutoRestoreWizard(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Do you want to autorestore settings?"), type=MessageBox.TYPE_YESNO, timeout=10, default=True, simple=True)

	def close(self, value):
		if value:
			MessageBox.close(self, 43)
		else:
			MessageBox.close(self)

class AutoInstallWizard(Screen):
	skin = """<screen name="AutoInstall" position="fill" flags="wfNoBorder">
		<panel position="left" size="5%,*"/>
		<panel position="right" size="5%,*"/>
		<panel position="top" size="*,5%"/>
		<panel position="bottom" size="*,5%"/>
		<widget name="AboutScrollLabel" font="Fixed;20" position="fill"/>
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self["AboutScrollLabel"] = ScrollLabel(_("Please wait"), showscrollbar=False)
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.appClosed)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.run_console)

	def run_console(self):
		self["AboutScrollLabel"].setText("")
		try:
			if self.container.execute("/etc/init.d/autoinstall.sh"):
				raise Exception, "failed to execute autoinstall.sh script"
				self.appClosed(True)
		except Exception, e:
			self.appClosed(True)

	def dataAvail(self, data):
		self["AboutScrollLabel"].appendText(data)

	def appClosed(self, retval):
		if retval:
			self["AboutScrollLabel"].setText(_("Some error occured - Please try later"))
		self.container.appClosed.remove(self.appClosed)
		self.container.dataAvail.remove(self.dataAvail)
		self.container = None
		os.remove("/etc/.doAutoinstall")
		self.close(3)

if not os.path.isfile("/etc/installed"):
	from Components.Console import Console
	Console().ePopen("opkg list_installed | cut -d ' ' -f 1 > /etc/installed;chmod 444 /etc/installed")

wizardManager.registerWizard(AutoInstallWizard, os.path.isfile("/etc/.doAutoinstall"), priority=0)
wizardManager.registerWizard(AutoRestoreWizard, config.misc.languageselected.value and config.misc.firstrun.value and checkForAvailableAutoBackup(), priority=0)
wizardManager.registerWizard(LanguageWizard, config.misc.languageselected.value, priority=10)
if OverscanWizard:
	wizardManager.registerWizard(OverscanWizard, config.misc.do_overscanwizard.value, priority=30)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority=40)
