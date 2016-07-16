from Wizard import wizardManager
from Screens.MessageBox import MessageBox
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Tools.HardwareInfo import HardwareInfo
try:
	from Plugins.SystemPlugins.OSDPositionSetup.overscanwizard import OverscanWizard
except:
	OverscanWizard = None

from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from Components.config import config, ConfigBoolean, configfile, ConfigSubsection
from LanguageSelection import LanguageWizard

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
	import os
	for dir in [name for name in os.listdir("/media/") if os.path.isdir(os.path.join("/media/", name))]:
		if os.path.isfile("/%s/backup/PLi-AutoBackup.tar.gz" % dir):
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

wizardManager.registerWizard(AutoRestoreWizard, config.misc.firstrun.value and checkForAvailableAutoBackup(), priority = -10)
wizardManager.registerWizard(LanguageWizard, config.misc.languageselected.value, priority = 5)
if OverscanWizard:
	wizardManager.registerWizard(OverscanWizard, config.misc.do_overscanwizard.value, priority = 10)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority = 20)
