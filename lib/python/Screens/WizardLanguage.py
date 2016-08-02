from Wizard import Wizard
from Components.Label import Label
from Components.Language import language
from LanguageSelection import LanguageWizard

class WizardLanguage(Wizard):
	def __init__(self, session, showSteps = True, showStepSlider = True, showList = True, showConfig = True):
		Wizard.__init__(self, session, showSteps, showStepSlider, showList, showConfig)
		self["languagetext"] = Label()
		self.LanguageWizardCallback()

	def red(self):
		self.session.openWithCallback(self.LanguageWizardCallback, LanguageWizard)

	def LanguageWizardCallback(self, key="1234"):
		print "languageSelect", key
		self["languagetext"].setText(self.getTranslation(language.getLanguageList()[language.getActiveLanguageIndex()][1][0]))
		self.resetCounter()
