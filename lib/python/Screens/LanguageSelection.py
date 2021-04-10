from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Language import language
from Components.config import config
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.InfoBar import InfoBar
from Screens.Rc import Rc
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

def LanguageEntryComponent(file, name, index):
	png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/" + index + ".png"))
	if png is None:
		png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/" + file + ".png"))
		if png is None:
			png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
	res = (index, name, png)
	return res

class LanguageSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Language selection"))
		self.oldActiveLanguage = language.getActiveLanguage()

		self.list = []
		self["languages"] = List(self.list)

		self.updateList()
		self.onLayoutFinish.append(self.selectActiveLanguage)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.save,
			"cancel": self.cancel,
		}, -1)

	def selectActiveLanguage(self):
		pos = 0
		for pos, x in enumerate(self.list):
			if x[0] == self.oldActiveLanguage:
				self["languages"].index = pos
				break

	def save(self):
		self.commit(self.run())
		if self.oldActiveLanguage != config.osd.language.value:
			if InfoBar.instance:
				self.session.openWithCallback(self.restartGUI, MessageBox,_("GUI needs a restart to apply a new language\nDo you want to restart the GUI now?"), MessageBox.TYPE_YESNO, title=_("Restart GUI now?"))
			else:
				self.restartGUI()
		else:
			self.close()

	def restartGUI(self, answer=True):
		answer and self.session.open(TryQuitMainloop, 3)

	def cancel(self):
		language.activateLanguage(self.oldActiveLanguage)
		self.close()

	def run(self):
		print "updating language..."
		lang = self["languages"].getCurrent()[0]
		if lang != config.osd.language.value:
			config.osd.language.value = lang
			config.osd.language.save()
		return lang

	def commit(self, lang):
		print "commit language"
		language.activateLanguage(lang)
		config.misc.languageselected.value = 0
		config.misc.languageselected.save()

	def updateList(self):
		languageList = language.getLanguageList()
		if not languageList: # no language available => display only english
			list = [ LanguageEntryComponent("en", "English", "en_EN") ]
		else:
			list = [ LanguageEntryComponent(file=x[1][2].lower(), name=x[1][0], index=x[0]) for x in languageList]
		self.list = list
		self["languages"].list = list

class LanguageWizard(LanguageSelection, Rc):
	def __init__(self, session):
		LanguageSelection.__init__(self, session)
		Rc.__init__(self)
		self.onLayoutFinish.append(self.selectKeys)
		self["wizard"] = Pixmap()
		self["text"] = Label()
		self.setText()

	def selectKeys(self):
		self.clearSelectedKeys()
		self.selectKey("UP")
		self.selectKey("DOWN")

	def setText(self):
		self["text"].setText(_("Please use the UP and DOWN keys to select your language. Afterwards press the OK button."))
