from Screens.MessageBox import MessageBox
from Screens.ParentalControlSetup import ProtectedScreen
from Components.config import config

class FactoryReset(MessageBox, ProtectedScreen):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Factory reset will restore your receiver to its default configuration. "
			"All user data including system settings, tuner configuration, bouquets, services and plugins will be DELETED. "
			"Recordings and other files stored on HDD and USB media will remain intact. "
			"After completion, the system will restart automatically!\n\n"
			"Do you really want to proceed?"), MessageBox.TYPE_YESNO, default=False)
		self.skinName = "MessageBox"
		ProtectedScreen.__init__(self)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and\
			(not config.ParentalControl.config_sections.main_menu.value and not config.ParentalControl.config_sections.configuration.value  or hasattr(self.session, 'infobar') and self.session.infobar is None) and\
			config.ParentalControl.config_sections.manufacturer_reset.value
