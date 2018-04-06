from Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.config import config, ConfigNothing, ConfigBoolean, ConfigSelection
from Components.Label import Label
from Components.SystemInfo import SystemInfo
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_SKIN

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

class SetupSummary(Screen):

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["SetupTitle"] = StaticText(_(parent.setup_title))
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if hasattr(self.parent,"onChangedEntry"):
			self.parent.onChangedEntry.append(self.selectionChanged)
			self.parent["config"].onSelectionChanged.append(self.selectionChanged)
			self.selectionChanged()

	def removeWatcher(self):
		if hasattr(self.parent,"onChangedEntry"):
			self.parent.onChangedEntry.remove(self.selectionChanged)
			self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()
		if hasattr(self.parent,"getCurrentDescription") and "description" in self.parent:
			self.parent["description"].text = self.parent.getCurrentDescription()

class Setup(ConfigListScreen, Screen):

	ALLOW_SUSPEND = True

	def refill(self):
		self.list = []
		xmldata = setupdom(self.setup, self.plugin).getroot()
		for x in xmldata.findall("setup"):
			if x.get("key") != self.setup:
				continue
			self.addItems(x)
			self.setup_title = x.get("title", "").encode("UTF-8")
			self.seperation = int(x.get('separation', '0'))

	def __init__(self, session, setup, plugin=None, menu_path=None, PluginLanguageDomain=None):
		Screen.__init__(self, session)
		# for the skin: first try a setup_<setupID>, then Setup
		self.skinName = ["setup_" + setup, "Setup" ]
		self.setup = setup
		self.plugin = plugin
		self.menu_path = menu_path
		self.PluginLanguageDomain = PluginLanguageDomain
		self.force_update_list = False

		#check for list.entries > 0 else self.close
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["description"] = Label("")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self["actions"] = NumberActionMap(["SetupActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"menu": self.closeRecursive,
			}, -2)

		self.list = []
		self.refill()
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)
		self["config"].onSelectionChanged.append(self.__onSelectionChanged)

		self.setTitle(_(self.setup_title))

	def addItems(self, parentNode):
		for x in parentNode:
			if not x.tag:
				continue
			if x.tag == 'item':
				item_level = int(x.get("level", 0))

				if item_level > config.usage.setup_level.index:
					continue

				requires = x.get("requires")
				if requires:
					if requires[0] == '!':
						if SystemInfo.get(requires[1:], False):
							continue
					elif not SystemInfo.get(requires, False):
						continue
				conditional = x.get("conditional")
				if conditional and not eval(conditional):
					continue

				item_text = _(x.get("text", "??").encode("UTF-8"))
				item_description = _(x.get("description", " ").encode("UTF-8"))
				b = eval(x.text or "");
				if b == "":
					continue
				#add to configlist
				item = b
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				if not isinstance(item, ConfigNothing):
					self.list.append((item_text, item, item_description))

	def changedEntry(self):
		if isinstance(self["config"].getCurrent()[1], ConfigBoolean) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
			self.refill()
			self["config"].setList(self.list)

	def __onSelectionChanged(self):
		if self.force_update_list:
			self["config"].onSelectionChanged.remove(self.__onSelectionChanged)
			self.refill()
			self["config"].setList(self.list)
			self["config"].onSelectionChanged.append(self.__onSelectionChanged)
			self.force_update_list = False
		if not (isinstance(self["config"].getCurrent()[1], ConfigBoolean) or isinstance(self["config"].getCurrent()[1], ConfigSelection)):
			self.force_update_list = True

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
