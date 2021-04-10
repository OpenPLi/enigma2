import mmap
import re

from enigma import ePicLoad, getDesktop
from os import listdir
from os.path import dirname, exists, isdir, join as pathjoin

from skin import DEFAULT_SKIN, DEFAULT_DISPLAY_SKIN, EMERGENCY_NAME, EMERGENCY_SKIN, currentDisplaySkin, currentPrimarySkin, domScreens
from Components.ActionMap import HelpableNumberActionMap
from Components.config import config
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop, QUIT_RESTART
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_LCDSKIN, SCOPE_SKIN


class SkinSelector(Screen, HelpableScreen):
	skin = ["""
	<screen name="SkinSelector" position="center,center" size="%d,%d">
		<widget name="preview" position="center,%d" size="%d,%d" alphatest="blend" />
		<widget source="skins" render="Listbox" position="center,%d" size="%d,%d" enableWrapAround="1" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template": [
					MultiContentEntryText(pos = (%d, 0), size = (%d, %d), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 1),
					MultiContentEntryText(pos = (%d, 0), size = (%d, %d), font = 0, flags = RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text = 2)
				],
				"fonts": [gFont("Regular",%d)],
				"itemHeight": %d
				}
			</convert>
		</widget>
		<widget source="description" render="Label" position="center,e-%d" size="%d,%d" font="Regular;%d" valign="center" />
		<widget source="key_red" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_red" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center" />
		<widget source="key_green" render="Label" position="%d,e-%d" size="%d,%d" backgroundColor="key_green" font="Regular;%d" foregroundColor="key_text" halign="center" valign="center" />
	</screen>""",
		670, 570,
		10, 356, 200,
		230, 650, 240,
		10, 350, 30,
		370, 260, 30,
		25,
		30,
		85, 650, 25, 20,
		10, 50, 140, 40, 20,
		160, 50, 140, 40, 20
	]

	def __init__(self, session, screenTitle=_("GUI Skin")):
		Screen.__init__(self, session, mandatoryWidgets=["description", "skins"])
		HelpableScreen.__init__(self)

		element = domScreens.get("SkinSelector", (None, None))[0]
		Screen.setTitle(self, screenTitle)
		self.rootDir = resolveFilename(SCOPE_SKIN)
		self.config = config.skin.primary_skin
		self.current = currentPrimarySkin
		self.xmlList = ["skin.xml"]
		self.onChangedEntry = []
		self["skins"] = List(enableWrapAround=True)
		self["preview"] = Pixmap()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = StaticText(_("Please wait... Loading list..."))
		self["actions"] = HelpableNumberActionMap(self, ["SetupActions", "DirectionActions", "ColorActions"], {
			"ok": (self.save, _("Save and activate the currently selected skin")),
			"cancel": (self.cancel, _("Cancel any changes to the currently active skin")),
			"close": (self.cancelRecursive, _("Cancel any changes to the currently active skin and exit all menus")),
			"red": (self.cancel, _("Cancel any changes to the currently active skin")),
			"green": (self.save, _("Save and activate the currently selected skin")),
			"up": (self.up, _("Move to the previous skin")),
			"down": (self.down, _("Move to the next skin")),
			"left": (self.left, _("Move to the previous page")),
			"right": (self.right, _("Move to the next page"))
		}, -1, description=_("Skin Selection Actions"))
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)
		self.onLayoutFinish.append(self.layoutFinished)

	def showPic(self, picInfo=""):
		ptr = self.picload.getData()
		if ptr is not None:
			self["preview"].instance.setPixmap(ptr.__deref__())

	def layoutFinished(self):
		self.picload.setPara((self["preview"].instance.size().width(), self["preview"].instance.size().height(), 1.0, 1, 1, 1, "#ff000000"))
		self.refreshList()

	def refreshList(self):
		emergency = _("Emergency")
		default = _("Default")
		defaultPicon = _("Default+Picon")
		current = _("Current")
		pending = _("Pending restart")
		displayPicon = pathjoin(dirname(DEFAULT_DISPLAY_SKIN), "skin_display_picon.xml")
		skinList = []
		# Find and list the available skins...
		for dir in [dir for dir in listdir(self.rootDir) if isdir(pathjoin(self.rootDir, dir))]:
			previewPath = pathjoin(self.rootDir, dir)
			for skinFile in self.xmlList:
				skin = pathjoin(dir, skinFile)
				skinPath = pathjoin(self.rootDir, skin)
				if exists(skinPath):
					resolution = None
					if skinFile == "skin.xml":
						try:
							with open(skinPath, "r") as fd:
								resolutions = {
									"480": _("NTSC"),
									"576": _("PAL"),
									"720": _("HD"),
									"1080": _("FHD"),
									"2160": _("4K"),
									"4320": _("8K"),
									"8640": _("16K")
								}
								mm = mmap.mmap(fd.fileno(), 0, prot=mmap.PROT_READ)
								skinheight = re.search("\<?resolution.*?\syres\s*=\s*\"(\d+)\"", mm).group(1)
								resolution = skinheight and resolutions.get(skinheight, None)
								mm.close()
						except:
							pass
						print("[SkinSelector] Resolution of skin '%s': '%s'." % (skinPath, "Unknown" if resolution is None else resolution))
						# Code can be added here to reject unsupported resolutions.
					# The "piconprev.png" image should be "prevpicon.png" to keep it with its partner preview image.
					preview = pathjoin(previewPath, "piconprev.png" if skinFile == "skin_display_picon.xml" else "prev.png")
					if skin == EMERGENCY_SKIN:
						list = [EMERGENCY_NAME, emergency, dir, skin, resolution, preview]
					elif skin == DEFAULT_SKIN:
						list = [dir, default, dir, skin, resolution, preview]
					elif skin == DEFAULT_DISPLAY_SKIN:
						list = [default, default, dir, skin, resolution, preview]
					elif skin == displayPicon:
						list = [dir, defaultPicon, dir, skin, resolution, preview]
					else:
						list = [dir, "", dir, skin, resolution, preview]
					if skin == self.current:
						list[1] = current
					elif skin == self.config.value:
						list[1] = pending
					list.append("%s (%s)" % (list[0], list[1]) if list[1] else list[0])
					if list[1]:
						list[1] = "<%s>" % list[1]
					#0=SortKey, 1=Label, 2=Flag, 3=Directory, 4=Skin, 5=Resolution, 6=Preview, 7=Label + Flag
					skinList.append(tuple([list[0].upper()] + list))
		skinList.sort()
		self["skins"].setList(skinList)
		# Set the list pointer to the current skin...
		for index in range(len(skinList)):
			if skinList[index][4] == self.config.value:
				self["skins"].setIndex(index)
				break
		self.loadPreview()

	def loadPreview(self):
		self.currentSelectedSkin = self["skins"].getCurrent()
		preview, resolution, skin = self.currentSelectedSkin[6], self.currentSelectedSkin[5], self.currentSelectedSkin[4]
		self.changedEntry()
		if not exists(preview):
			preview = resolveFilename(SCOPE_CURRENT_SKIN, "noprev.png")
		self.picload.startDecode(preview)
		if skin == self.config.value:
			self["description"].setText(_("Press OK to keep the currently selected %s skin.") % resolution)
		else:
			self["description"].setText(_("Press OK to activate the selected %s skin.") % resolution)

	def cancel(self):
		self.close(False)

	def cancelRecursive(self):
		self.close(True)

	def save(self):
		label, skin = self.currentSelectedSkin[1], self.currentSelectedSkin[4]
		if skin == self.config.value:
			if skin == self.current:
				print("[SkinSelector] Selected skin: '%s' (Unchanged!)" % pathjoin(self.rootDir, skin))
				self.cancel()
			else:
				print("[SkinSelector] Selected skin: '%s' (Trying to restart again!)" % pathjoin(self.rootDir, skin))
				restartBox = self.session.openWithCallback(self.restartGUI, MessageBox, _("To apply the selected '%s' skin the GUI needs to restart. Would you like to restart the GUI now?") % label, MessageBox.TYPE_YESNO)
				restartBox.setTitle(_("SkinSelector: Restart GUI"))
		elif skin == self.current:
			print("[SkinSelector] Selected skin: '%s' (Pending skin '%s' cancelled!)" % (pathjoin(self.rootDir, skin), pathjoin(self.rootDir, self.config.value)))
			self.config.value = skin
			self.config.save()
			self.cancel()
		else:
			print("[SkinSelector] Selected skin: '%s'" % pathjoin(self.rootDir, skin))
			restartBox = self.session.openWithCallback(self.restartGUI, MessageBox, _("To save and apply the selected '%s' skin the GUI needs to restart. Would you like to save the selection and restart the GUI now?") % label, MessageBox.TYPE_YESNO)
			restartBox.setTitle(_("SkinSelector: Restart GUI"))

	def restartGUI(self, answer):
		if answer is True:
			self.config.value = self.currentSelectedSkin[4]
			self.config.save()
			self.session.open(TryQuitMainloop, QUIT_RESTART)
		self.refreshList()

	def up(self):
		self["skins"].up()
		self.loadPreview()

	def down(self):
		self["skins"].down()
		self.loadPreview()

	def left(self):
		self["skins"].pageUp()
		self.loadPreview()

	def right(self):
		self["skins"].pageDown()
		self.loadPreview()

	# For summary screen.
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def createSummary(self):
		return SkinSelectorSummary

	def getCurrentName(self):
		current = self["skins"].getCurrent()[1]
		if current:
			current = current.replace("_", " ")
		return current


class LcdSkinSelector(SkinSelector):
	def __init__(self, session, screenTitle=_("Display Skin")):
		SkinSelector.__init__(self, session, screenTitle=screenTitle)
		self.skinName = ["LcdSkinSelector", "SkinSelector"]
		self.rootDir = resolveFilename(SCOPE_LCDSKIN)
		self.config = config.skin.display_skin
		self.current = currentDisplaySkin
		self.xmlList = ["skin_display.xml", "skin_display_picon.xml"]


class SkinSelectorSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["Name"] = StaticText("")
		if hasattr(self.parent, "onChangedEntry"):
			self.onShow.append(self.addWatcher)
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if hasattr(self.parent, "onChangedEntry"):
			self.parent.onChangedEntry.append(self.selectionChanged)
			self.selectionChanged()

	def removeWatcher(self):
		if hasattr(self.parent, "onChangedEntry"):
			self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self):
		self["Name"].text = self.parent.getCurrentName()
