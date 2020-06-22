from enigma import eWindow  # , getDesktop

from skin import GUI_SKIN_ID, applyAllAttributes
from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.Sources.StaticText import StaticText
from Tools.CList import CList


class ScreenPath():
	def __init__(self):
		self.pathList = []
		self.lastSelf = None


screenPath = ScreenPath()


class GUISkin:
	__module__ = __name__

	def __init__(self):
		self["Title"] = StaticText()
		self["screen_path"] = StaticText()
		self.onLayoutFinish = []
		self.summaries = CList()
		self.instance = None
		self.desktop = None
		self.screenPathMode = False

	def createGUIScreen(self, parent, desktop, updateonly=False):
		for val in self.renderer:
			if isinstance(val, GUIComponent):
				if not updateonly:
					val.GUIcreate(parent)
				if not val.applySkin(desktop, self):
					print("[GUISkin] Warning: Skin is missing renderer '%s' in %s." % (val, str(self)))
		for key in self:
			val = self[key]
			if isinstance(val, GUIComponent):
				if not updateonly:
					val.GUIcreate(parent)
				depr = val.deprecationInfo
				if val.applySkin(desktop, self):
					if depr:
						print("[GUISkin] WARNING: OBSOLETE COMPONENT '%s' USED IN SKIN. USE '%s' INSTEAD!" % (key, depr[0]))
						print("[GUISkin] OBSOLETE COMPONENT WILL BE REMOVED %s, PLEASE UPDATE!" % depr[1])
				elif not depr:
					print("[GUISkin] Warning: Skin is missing element '%s' in %s." % (key, str(self)))
		for w in self.additionalWidgets:
			if not updateonly:
				w.instance = w.widget(parent)
				# w.instance.thisown = 0
			applyAllAttributes(w.instance, desktop, w.skinAttributes, self.scale)
		for f in self.onLayoutFinish:
			# if type(f) is not type(self.close):  # Is this the best way to do this?
			if not isinstance(f, type(self.close)):
				exec f in globals(), locals()
			else:
				f()

	def deleteGUIScreen(self):
		for (name, val) in self.items():
			if isinstance(val, GUIComponent):
				val.GUIdelete()

	def close(self):
		self.deleteGUIScreen()

	def createSummary(self):
		return None

	def addSummary(self, summary):
		if summary is not None:
			self.summaries.append(summary)

	def removeSummary(self, summary):
		if summary is not None:
			self.summaries.remove(summary)

	def clearScreenPath(self):
		screenPath.pathList = []
		screenPath.lastSelf = None

	def removeScreenPath(self):
		screenPath.pathList = screenPath.pathList and screenPath.pathList[:-1]
		screenPath.lastSelf = None

	def setScreenPathMode(self, mode):
		self.screenPathMode = mode

	def setTitle(self, title):
		pathText = ""
		if self.screenPathMode is not None and title and config.usage.menu_path.value != "off":
			if self.screenPathMode and not screenPath.pathList or screenPath.pathList and screenPath.pathList[-1] != title:
				self.onClose.append(self.removeScreenPath)
				if screenPath.lastSelf != self:
					screenPath.pathList.append(title)
					screenPath.lastSelf = self
				elif screenPath.pathList:
					screenPath.pathList[-1] = title
			if config.usage.menu_path.value == "small":
				pathText = len(screenPath.pathList) > 1 and " > ".join(screenPath.pathList[:-1]) + " >" or ""
			else:
				title = screenPath.pathList and " > ".join(screenPath.pathList) or title
			# print("[GUISkin] DEBUG: title='%s', pathList='%s', self='%s'." % (title, str(screenPath.pathList), str(self)))
		if self.instance:
			self.instance.setTitle(title)
		self["Title"].text = title
		self["screen_path"].text = pathText
		self.summaries.setTitle(title)

	def getTitle(self):
		return self["Title"].text

	title = property(getTitle, setTitle)

	def setDesktop(self, desktop):
		self.desktop = desktop

	def applySkin(self):
		z = 0
		baseRes = (720, 576)  # FIXME: A skin might have set another resolution, which should be the base res.
		# baseRes = (getDesktop(GUI_SKIN_ID).size().width(), getDesktop(GUI_SKIN_ID).size().height())
		idx = 0
		skinTitleIndex = -1
		title = self.title
		for (key, value) in self.skinAttributes:
			if key == "zPosition":
				z = int(value)
			elif key == "title":
				skinTitleIndex = idx
				if title:
					self.skinAttributes[skinTitleIndex] = ("title", title)
				else:
					self["Title"].text = value
					self.summaries.setTitle(value)
			elif key == "baseResolution":
				baseRes = tuple([int(x) for x in value.split(",")])
			idx += 1
		self.scale = ((baseRes[0], baseRes[0]), (baseRes[1], baseRes[1]))
		if not self.instance:
			self.instance = eWindow(self.desktop, z)
		if skinTitleIndex == -1 and title:
			self.skinAttributes.append(("title", title))
		self.skinAttributes.sort(key=lambda a: {"position": 1}.get(a[0], 0))  # We need to make sure that certain attributes come last.
		applyAllAttributes(self.instance, self.desktop, self.skinAttributes, self.scale)
		self.createGUIScreen(self.instance, self.desktop)
