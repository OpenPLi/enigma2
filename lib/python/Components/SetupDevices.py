from Components.config import ConfigOnOff, ConfigSelection, ConfigSubsection, ConfigText, config
from Components.Keyboard import keyboard
from Components.Language import language


def InitSetupDevices():
	def languageNotifier(configElement):
		language.activateLanguage(configElement.value)

	config.osd = ConfigSubsection()
	config.osd.language = ConfigText(default="en_EN")
	config.osd.language.addNotifier(languageNotifier)

	def keyboardNotifier(configElement):
		keyboard.activateKeyboardMap(configElement.index)

	config.keyboard = ConfigSubsection()
	config.keyboard.keymap = ConfigSelection(default=keyboard.getDefaultKeyboardMap(), choices=keyboard.getKeyboardMaplist())
	config.keyboard.keymap.addNotifier(keyboardNotifier)

	config.parental = ConfigSubsection()
	config.parental.lock = ConfigOnOff(default=False)
	config.parental.setuplock = ConfigOnOff(default=False)

	config.expert = ConfigSubsection()
	config.expert.satpos = ConfigOnOff(default=True)
	config.expert.fastzap = ConfigOnOff(default=True)
	config.expert.skipconfirm = ConfigOnOff(default=False)
	config.expert.hideerrors = ConfigOnOff(default=False)
	config.expert.autoinfo = ConfigOnOff(default=True)
