from Components.ActionMap import HelpableActionMap
from Components.config import config, ConfigNothing, ConfigBoolean, ConfigSelection, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_SKIN, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

try:
	from boxbranding import getMachineBrand, getMachineName
	branding_available = True
except ImportError:
	# from models.owibranding import getBoxType, getMachineName
	branding_available = False
from gettext import dgettext
try:
	from skin import setups
except ImportError:
	setups = {}

import os
import xml.etree.cElementTree

__setupdoms = {}
__setupdates = {}
__setuptitles = {}

# Read the setupmenu
def setupdom(setup=None, plugin=None):
	if plugin:
		setupfile = resolveFilename(SCOPE_CURRENT_PLUGIN, plugin + "/setup.xml")
		msg = " from plugin '%s'" % plugin
	else:
		setupfile = resolveFilename(SCOPE_SKIN, "setup.xml")
		msg = ""
	try:
		mtime = os.path.getmtime(setupfile)
	except OSError as err:
		print "[Setup] ERROR: Unable to get '%s' modified time - Error (%d): %s!" % (setupfile, err.errno, err.strerror)
		return xml.etree.cElementTree.fromstring("<setupxml></setupxml>")
	cached = setupfile in __setupdoms and setupfile in __setupdates and __setupdates[setupfile] == mtime
	print "[Setup] XML%s source file: '%s'" % (" cached" if cached else "", setupfile)
	if setup is not None:
		print "[Setup] XML Setup menu '%s'%s" % (setup, msg)
	if cached:
		return __setupdoms[setupfile]
	try:
		fail = False
		setupfiledom = xml.etree.cElementTree.parse(setupfile)
	except (IOError, OSError) as err:
		fail = True
		print "[Setup] ERROR: Unable to open/read '%s' - Error (%d): %s!" % (setupfile, err.errno, err.strerror)
	except xml.etree.cElementTree.ParseError as err:
		fail = True
		print "[Setup] ERROR: Unable to load XML data from '%s' - %s!" % (setupfile, str(err))
	except Exception:
		fail = True
		print "[Setup] ERROR: Unable to process XML data from '%s'!" % setupfile
	if fail:
		setupfiledom = xml.etree.cElementTree.fromstring("<setupxml></setupxml>")
	else:
		__setupdoms[setupfile] = setupfiledom
		__setupdates[setupfile] = mtime
		if plugin is None:		# Don't allow plugin IDs to clobber setup.xml IDs
			xmldata = setupfiledom.getroot()
			for x in xmldata.findall("setup"):
				id = x.get("key", "")
				title = x.get("menuTitle", "").encode("UTF-8")
				if title == "":
					title = x.get("title", "").encode("UTF-8")
					if title == "":
						print "[Setup] Error: Setup ID '%s' title is missing or blank!" % id
						title = "** Setup error: '%s' title is missing or blank!" % id
				# print "[Setup] DEBUG XML Setup menu load: id='%s', title='%s', menuTitle='%s'" % (id, x.get("title", "").encode("UTF-8"), x.get("menuTitle", "").encode("UTF-8"))
				if title != "":
					title = _(title)
				__setuptitles[id] = title
	return setupfiledom


class SetupSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["SetupTitle"] = StaticText(_(parent.setup_title))
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if hasattr(self.parent, "onChangedEntry"):
			self.parent.onChangedEntry.append(self.selectionChanged)
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
			self.selectionChanged()

	def removeWatcher(self):
		if hasattr(self.parent, "onChangedEntry"):
			self.parent.onChangedEntry.remove(self.selectionChanged)
			self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()


class Setup(ConfigListScreen, Screen, HelpableScreen):

	ALLOW_SUSPEND = True

	def __init__(self, session, setup, plugin=None, menu_path=None, PluginLanguageDomain=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		# For the skin: First try a Setup_<setupID>, then Setup
		self.skinName = ["Setup_" + setup, "Setup"]
		self.setup = setup
		self.plugin = plugin
		self.menu_path = menu_path
		self.PluginLanguageDomain = PluginLanguageDomain
		self.setup_title = "Setup"
		self.item = None
		self.footnote = ""

		# If config.usage.sort_settings doesn't exist create it here to supress
		# errors later.
		if getattr(config.usage, "sort_settings", None) is None:
			config.usage.sort_settings = ConfigYesNo(default=False)
		# In OpenPLi the menu path code is handled globally in GUISkin.py. In
		# OpenViX and Beyonwiz the menu path code is handled here.
		self.show_menupath = ""
		if getattr(config.usage, "menu_path", None) is None:
			if getattr(config.usage, "show_menupath", None) is not None:
				self.show_menupath = config.usage.show_menupath.value
				self["menu_path_compressed"] = StaticText()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_help"] = StaticText(_("HELP"))
		self["description"] = Label("")
		self["footnote"] = Label("")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self["actions"] = HelpableActionMap(self, "SetupActions", {
			"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
			"save": (self.keySave, _("Save all changed settings and exit")),
			"menu": (self.closeRecursive, _("Cancel any changed settings and exit all menus"))
		}, prio=-2, description=_("Common Setup Functions"))

		defaultmenuimage = setups.get("default", "")
		menuimage = setups.get(self.setup, defaultmenuimage)
		if menuimage:
			if menuimage == defaultmenuimage:
				msg = "Default"
			else:
				msg = "Menu"
			menuimage = resolveFilename(SCOPE_CURRENT_SKIN, menuimage)
			print "[Setup] %s image: '%s'" % (msg, menuimage)
			self.menuimage = LoadPixmap(menuimage)
			if self.menuimage:
				self["menuimage"] = Pixmap()
			else:
				print "[Setup] ERROR: Unable to load menu image '%s'!" % menuimage
		else:
			self.menuimage = None

		self.list = []
		self.refill()
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)
		if config.usage.sort_settings.value:
			self["config"].list.sort()
		if self.levelChanged not in config.usage.setup_level.notifiers:
			config.usage.setup_level.notifiers.append(self.levelChanged)
		if self.cleanUp not in self.onClose:
			self.onClose.append(self.cleanUp)
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		if self.layoutFinished not in self.onLayoutFinish:
			self.onLayoutFinish.append(self.layoutFinished)

	def refill(self):
		xmldata = setupdom(self.setup, self.plugin).getroot()
		for x in xmldata.findall("setup"):
			if x.get("key") == self.setup:
				self.addItems(x)
				skin = x.get("skin", "")
				if skin != "":
					self.skinName = [skin] + self.skinName
				if self.show_menupath in ("large", "small") and x.get("menuTitle", "").encode("UTF-8") != "":
					self.setup_title = x.get("menuTitle", "").encode("UTF-8")
				else:
					self.setup_title = x.get("title", "").encode("UTF-8")

	def addItems(self, parentNode):
		for x in parentNode:
			if x.tag and x.tag == "item":
				item_level = int(x.get("level", 0))
				if item_level > config.usage.setup_level.index:
					continue

				requires = x.get("requires")
				if requires:
					negate = requires.startswith("!")
					if negate:
						requires = requires[1:]
					if requires.startswith("config."):
						item = eval(requires)
						SystemInfo[requires] = item.value and item.value != "0"
						clean = True
					else:
						clean = False
					result = bool(SystemInfo.get(requires, False))
					if clean:
						SystemInfo.pop(requires, None)
					if requires and negate == result:
						continue

				conditional = x.get("conditional")
				if conditional and not eval(conditional):
					continue

				if self.PluginLanguageDomain:
					item_text = dgettext(self.PluginLanguageDomain, x.get("text", "??").encode("UTF-8"))
					item_description = dgettext(self.PluginLanguageDomain, x.get("description", " ").encode("UTF-8"))
				else:
					item_text = _(x.get("text", "??").encode("UTF-8"))
					item_description = _(x.get("description", " ").encode("UTF-8"))
				if branding_available:
					item_text = item_text.replace("%s %s", "%s %s" % (getMachineBrand(), getMachineName()))
					item_description = item_description.replace("%s %s", "%s %s" % (getMachineBrand(), getMachineName()))
				else:
					msg = _("Enigma2 receiver")
					item_text = item_text.replace("%s %s", msg)
					item_description = item_description.replace("%s %s", msg)
				item = eval(x.text or "")
				if item != "" and not isinstance(item, ConfigNothing):
					# Add item to configlist.
					# The first item is the item itself, ignored by the configList.
					# The second one is converted to string.
					self.list.append((item_text, item, item_description))

	def selectionChanged(self):
		if len(self["config"].getList()):
			if self.footnote:
				self["footnote"].text = _(self.footnote)
			else:
				if self.getCurrentEntry().endswith("*"):
					self["footnote"].text = _("* = Restart Required")
				else:
					self["footnote"].text = ""
			self["description"].text = self.getCurrentDescription()
		else:
			self["description"].text = _("There are no items currently available for this menu.")

	def layoutFinished(self):
		if self.show_menupath == "large" and self.menu_path:
			title = self.menu_path + _(self.setup_title)
			self["menu_path_compressed"].setText("")
		elif self.show_menupath == "small" and self.menu_path:
			title = _(self.setup_title)
			self["menu_path_compressed"].setText(self.menu_path + " >" if not self.menu_path.endswith(" / ") else self.menu_path[:-3] + " >" or "")
		elif self.show_menupath == "off" and self.menu_path:
			title = _(self.setup_title)
			self["menu_path_compressed"].setText("")
		else:
			title = _(self.setup_title)
		self.setTitle(title)
		if self.menuimage:
			self["menuimage"].instance.setPixmap(self.menuimage)
		if len(self["config"].getList()) == 0:
			print "[Setup] No menu items available!"

	def changedEntry(self):
		self.item = self["config"].getCurrent()
		if isinstance(self.item[1], (ConfigBoolean, ConfigSelection)):
			self.createSetup()

	def levelChanged(self, configElement):
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.refill()
		self["config"].setList(self.list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()
		self.moveToItem(self.item)

	def moveToItem(self, item):
		newIdx = self.getIndexFromItem(item)
		if newIdx is None:
			newIdx = 0
		self["config"].setCurrentIndex(newIdx)

	def getIndexFromItem(self, item):
		if item is not None:
			for x in range(len(self["config"].list)):
				if self["config"].list[x][0] == item[0]:
					return x
		return None

	def cleanUp(self):
		config.usage.setup_level.notifiers.remove(self.levelChanged)

# Only used in AudioSelection screen...
def getConfigMenuItem(configElement):
	for item in setupdom().getroot().findall("./setup/item/."):
		if item.text == configElement:
			return _(item.attrib["text"]), eval(configElement)
	return "", None


class SetupError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return self.msg

# Only used in Menu screen...
def getSetupTitle(id):
	setupdom()		# Load (or check for an updated) setup.xml file
	id = str(id)
	title = __setuptitles.get(id, "")
	if title == "":
		print "[Setup] Error: Setup ID '%s' not found in setup file!" % id
		title = "** Setup error: '%s' section not found! **" % id
		#
		# Forcing a UI crash is VERY bad and, in this case, unnecessary but
		# I have been told that this must happen!  :(
		#
		raise SetupError("[Setup] Error: Unknown setup id '%s'!" % id)
	return title
