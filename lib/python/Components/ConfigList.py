from enigma import eListbox, eListboxPythonConfigContent, ePoint, eRCInput, eTimer, gRGB
from skin import parameters, applySkinFactor, parseColor

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigBoolean, ConfigElement, ConfigInteger, ConfigMacText, ConfigNothing, ConfigNumber, ConfigSelection, ConfigSequence, ConfigText, ACTIONKEY_0, ACTIONKEY_ASCII, ACTIONKEY_BACKSPACE, ACTIONKEY_DELETE, ACTIONKEY_ERASE, ACTIONKEY_FIRST, ACTIONKEY_LAST, ACTIONKEY_LEFT, ACTIONKEY_NUMBERS, ACTIONKEY_RIGHT, ACTIONKEY_SELECT, ACTIONKEY_TIMEOUT, ACTIONKEY_TOGGLE, configfile
from Components.GUIComponent import GUIComponent
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Standby import QUIT_RESTART, TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard


class ConfigList(GUIComponent):
	def __init__(self, list, session=None):
		GUIComponent.__init__(self)
		self.l = eListboxPythonConfigContent()  # noqa: E741
		seperation = parameters.get("ConfigListSeperator", applySkinFactor(200))
		self.l.setSeperation(seperation)
		height, space = parameters.get("ConfigListSlider", applySkinFactor(17, 0))
		self.l.setSlider(height, space)
		self.timer = eTimer()
		self.list = list
		self.onSelectionChanged = []
		self.current = None
		self.session = session
		self.sepLineColor = 0xFFFFFF
		self.sepLineThickness = 1
		self.l.setSeparatorLineColor(gRGB(self.sepLineColor))
		self.l.setSepLineThickness(self.sepLineThickness)

	def execBegin(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)
		self.timer.callback.append(self.timeout)

	def execEnd(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.timer.stop()
		self.timer.callback.remove(self.timeout)

	def timeout(self):
		self.handleKey(ACTIONKEY_TIMEOUT)

	def handleKey(self, key, callback=None):
		selection = self.getCurrent()
		if selection and len(selection) > 1 and selection[1].enabled:
			selection[1].handleKey(key, callback)
			self.invalidateCurrent()
			if key in ACTIONKEY_NUMBERS:
				self.timer.start(1000, 1)

	def toggle(self):
		self.getCurrent()[1].toggle()
		self.invalidateCurrent()

	def getCurrent(self):
		return self.l.getCurrentSelection()

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def invalidateCurrent(self):
		self.l.invalidateEntry(self.l.getCurrentSelectionIndex())

	def invalidate(self, entry):
		# When the entry to invalidate does not exist, just ignore the request.
		# This eases up conditional setup screens a lot.
		if entry in self.__list:
			self.l.invalidateEntry(self.__list.index(entry))

	GUI_WIDGET = eListbox

	def isChanged(self):
		for item in self.list:
			if len(item) > 1 and item[1].isChanged():
				return True
		return False

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def selectionChanged(self):
		if isinstance(self.current, tuple) and len(self.current) >= 2:
			self.current[1].onDeselect(self.session)
		self.current = self.getCurrent()
		if isinstance(self.current, tuple) and len(self.current) >= 2:
			self.current[1].onSelect(self.session)
		else:
			return
		for x in self.onSelectionChanged:
			x()

	def postWidgetCreate(self, instance):
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		if isinstance(self.current, tuple) and len(self.current) >= 2:
			self.current[1].onDeselect(self.session)
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def setList(self, configList):
		self.__list = configList
		self.l.setList(self.__list)
		if configList is not None:
			for x in configList:
				assert len(x) < 2 or isinstance(x[1], ConfigElement), "[ConfigList] Error: Entry in ConfigList '%s' must be a ConfigElement!" % str(x[1])

	def getList(self):
		return self.__list

	list = property(getList, setList)

	def moveTop(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveTop)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def moveUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def moveBottom(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveEnd)
	
	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "sepLineColor":
					self.sepLineColor = parseColor(value).argb()
				elif attrib == "sepLineThickness":
					self.sepLineThickness = int(value)
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.l.setSeparatorLineColor(gRGB(self.sepLineColor))
		self.l.setSepLineThickness(self.sepLineThickness)
		return rc


class ConfigListScreen:
	def __init__(self, list, session=None, on_change=None, fullUI=False, yellow_button=None, blue_button=None, menu_button=None):
		self.entryChanged = on_change if on_change is not None else lambda: None
		if fullUI:
			if "key_red" not in self:
				self["key_red"] = StaticText(_("Cancel"))
			if "key_green" not in self:
				self["key_green"] = StaticText(_("Save"))
			if "key_yellow" not in self and yellow_button:
				self["key_yellow"] = StaticText(yellow_button.get('text', ''))
				self["key_yellowActions"] = HelpableActionMap(self, ["ColorActions"], {
					"yellow": (yellow_button['function'], yellow_button.get('helptext', _("Yellow button function"))),
				}, prio=1, description=_("Common Setup Actions"))
			if "key_blue" not in self and blue_button:
				self["key_blue"] = StaticText(blue_button.get('text', ''))
				self["key_blueActions"] = HelpableActionMap(self, ["ColorActions"], {
					"blue": (blue_button['function'], blue_button.get('helptext', _("Blue button function"))),
				}, prio=1, description=_("Common Setup Actions"))
			if "key_menu" not in self and menu_button:
				self["key_menu"] = StaticText(menu_button.get('text', ''))
				self["menuConfigActions"] = HelpableActionMap(self, "ConfigListActions", {
					"menu": (menu_button['function'], menu_button.get('helptext', _("Menu button function"))),
				}, prio=1, description=_("Common Setup Actions"))
			self["fullUIActions"] = HelpableActionMap(self, ["ConfigListActions"], {
				"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
				"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus")),
				"save": (self.keySave, _("Save all changed settings and exit"))
			}, prio=1, description=_("Common Setup Actions"))
		if "HelpWindow" not in self:
			self["HelpWindow"] = Pixmap()
			self["HelpWindow"].hide()
		if "VKeyIcon" not in self:
			self["VKeyIcon"] = Boolean(False)
		self["configActions"] = HelpableActionMap(self, ["ConfigListActions"], {
			"select": (self.keySelect, _("Select, toggle, process or edit the current entry"))
		}, prio=1, description=_("Common Setup Actions"))
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self.keyTop, _("Move to first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyUp, _("Move up a line")),
			"first": (self.keyFirst, _("Jump to first item in list or the start of text")),
			"left": (self.keyLeft, _("Select the previous item in list or move cursor left")),
			"right": (self.keyRight, _("Select the next item in list or move cursor right")),
			"last": (self.keyLast, _("Jump to last item in list or the end of text")),
			"down": (self.keyDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=1, description=_("Common Setup Actions"))
		self["editConfigActions"] = HelpableNumberActionMap(self, ["NumberActions", "TextEditActions"], {
			"backspace": (self.keyBackspace, _("Delete character to left of cursor or select AM times")),
			"delete": (self.keyDelete, _("Delete character under cursor or select PM times")),
			"erase": (self.keyErase, _("Delete all the text")),
			"toggleOverwrite": (self.keyToggle, _("Toggle new text inserts before or overwrites existing text")),
			"1": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"2": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"3": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"4": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"5": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"6": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"7": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"8": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"9": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"0": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"gotAsciiCode": (self.keyGotAscii, _("Keyboard data entry"))
		}, prio=1, description=_("Common Setup Actions"))
		self["editConfigActions"].setEnabled(False if fullUI else True)
		self["virtualKeyBoardActions"] = HelpableActionMap(self, "VirtualKeyboardActions", {
			"showVirtualKeyboard": (self.keyText, _("Display the virtual keyboard for data entry"))
		}, prio=1, description=_("Common Setup Actions"))
		self["virtualKeyBoardActions"].setEnabled(False)

		# Temporary support for legacy code and plugins that hasn't yet been updated (next 4 lines).
		self["config_actions"] = DummyActions()
		self["config_actions"].setEnabled = self.dummyConfigActions
		self["VirtualKB"] = DummyActions()
		self["VirtualKB"].setEnabled = self.dummyVKBActions

		self["config"] = ConfigList(list, session=session)
		self.setCancelMessage(None)
		self.setRestartMessage(None)
		self.onChangedEntry = []
		self.onSave = []
		self.manipulatedItems = []  # keep track of all manipulated items including ones that have been removed from self["config"].list (currently used by Setup.py)
		if self.noNativeKeys not in self.onLayoutFinish:
			self.onLayoutFinish.append(self.noNativeKeys)
		if self.handleInputHelpers not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.handleInputHelpers)
		if self.showHelpWindow not in self.onExecBegin:
			self.onExecBegin.append(self.showHelpWindow)
		if self.hideHelpWindow not in self.onExecEnd:
			self.onExecEnd.append(self.hideHelpWindow)

	def setCancelMessage(self, msg):
		self.cancelMsg = _("Really close without saving settings?") if msg is None else msg

	def setRestartMessage(self, msg):
		self.restartMsg = _("Restart GUI now?") if msg is None else msg

	def getCurrentItem(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 1 and self["config"].getCurrent()[1] or None

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 1 and str(self["config"].getCurrent()[1].getText()) or ""

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def noNativeKeys(self):
		self["config"].instance.allowNativeKeys(False)

	def handleInputHelpers(self):
		currConfig = self["config"].getCurrent()
		if currConfig is not None:
			if isinstance(currConfig[1], (ConfigInteger, ConfigMacText, ConfigSequence, ConfigText)):
				self["editConfigActions"].setEnabled(True)
			else:
				self["editConfigActions"].setEnabled(False)
			if isinstance(currConfig[1], (ConfigText, ConfigMacText)) and "HelpWindow" in self and currConfig[1].help_window and currConfig[1].help_window.instance is not None:
				helpwindowpos = self["HelpWindow"].getPosition()
				currConfig[1].help_window.instance.move(ePoint(helpwindowpos[0], helpwindowpos[1]))
			if isinstance(currConfig[1], ConfigText):
				self.showVirtualKeyBoard(True)
			else:
				self.showVirtualKeyBoard(False)
			if "description" in self:
				self["description"].text = self.getCurrentDescription()

	def showVirtualKeyBoard(self, state):
		if "VKeyIcon" in self:
			self["VKeyIcon"].boolean = state
			self["virtualKeyBoardActions"].setEnabled(state)

	def showHelpWindow(self):
		self.displayHelp(True)

	def hideHelpWindow(self):
		self.displayHelp(False)

	def displayHelp(self, state):
		if "config" in self and "HelpWindow" in self and self["config"].getCurrent() is not None and len(self["config"].getCurrent()) > 1:
			currConf = self["config"].getCurrent()[1]
			if isinstance(currConf, (ConfigText, ConfigMacText)) and currConf.help_window is not None and currConf.help_window.instance is not None:
				if state:
					currConf.help_window.show()
				else:
					currConf.help_window.hide()

	def keySelect(self):
		if isinstance(self.getCurrentItem(), ConfigBoolean):
			self.keyToggle()
		elif isinstance(self.getCurrentItem(), ConfigSelection):
			self.keySelection()
		elif isinstance(self.getCurrentItem(), ConfigText) and not isinstance(self.getCurrentItem(), ConfigNumber):
			self.keyText()
		else:
			self["config"].handleKey(ACTIONKEY_SELECT, self.entryChanged)

	def keyOK(self):  # This is the deprecated version of keySelect!
		self.keySelect()

	def keyText(self):
		self.session.openWithCallback(self.keyTextCallback, VirtualKeyBoard, title=self.getCurrentEntry(), text=str(self.getCurrentValue()))

	def keyTextCallback(self, callback=None):
		if callback is not None:
			prev = str(self.getCurrentValue())
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidateCurrent()
			if callback != prev:
				self.entryChanged()

	def keySelection(self):
		currConfig = self["config"].getCurrent()
		if currConfig and currConfig[1].enabled and hasattr(currConfig[1], "description") and len(currConfig[1].choices.choices) > 1:
			self.session.openWithCallback(
				self.keySelectionCallback, ChoiceBox, title=currConfig[0],
				list=list(zip(currConfig[1].description, currConfig[1].choices)),
				selection=currConfig[1].getIndex(),
				keys=[]
			)

	def keySelectionCallback(self, answer):
		if answer:
			self["config"].getCurrent()[1].value = answer[1]
			self["config"].invalidateCurrent()
			self.entryChanged()

	def keyTop(self):
		self["config"].moveTop()

	def keyPageUp(self):
		self["config"].pageUp()

	def keyUp(self):
		self["config"].moveUp()

	def keyFirst(self):
		self["config"].handleKey(ACTIONKEY_FIRST, self.entryChanged)

	def keyLeft(self):
		self["config"].handleKey(ACTIONKEY_LEFT, self.entryChanged)

	def keyRight(self):
		self["config"].handleKey(ACTIONKEY_RIGHT, self.entryChanged)

	def keyLast(self):
		self["config"].handleKey(ACTIONKEY_LAST, self.entryChanged)

	def keyDown(self):
		self["config"].moveDown()

	def keyPageDown(self):
		self["config"].pageDown()

	def keyBottom(self):
		self["config"].moveBottom()

	def keyBackspace(self):
		self["config"].handleKey(ACTIONKEY_BACKSPACE, self.entryChanged)

	def keyDelete(self):
		self["config"].handleKey(ACTIONKEY_DELETE, self.entryChanged)

	def keyErase(self):
		self["config"].handleKey(ACTIONKEY_ERASE, self.entryChanged)

	def keyToggle(self):
		self["config"].handleKey(ACTIONKEY_TOGGLE, self.entryChanged)

	def keyGotAscii(self):
		self["config"].handleKey(ACTIONKEY_ASCII, self.entryChanged)

	def keyNumberGlobal(self, number):
		self["config"].handleKey(ACTIONKEY_0 + number, self.entryChanged)

	def keySave(self):
		for notifier in self.onSave:
			notifier()
		if self.saveAll():
			self.session.openWithCallback(self.restartConfirm, MessageBox, self.restartMsg, default=True, type=MessageBox.TYPE_YESNO)
		else:
			self.close()

	def restartConfirm(self, result):
		if result:
			self.session.open(TryQuitMainloop, retvalue=QUIT_RESTART)
			self.close()

	def saveAll(self):
		restart = False
		for item in set(self["config"].list + self.manipulatedItems):
			if len(item) > 1:
				if item[0].endswith("*") and item[1].isChanged():
					restart = True
				item[1].save()
		configfile.save()
		return restart

	def addSaveNotifier(self, notifier):
		if callable(notifier):
			self.onSave.append(notifier)
		else:
			raise TypeError("[ConfigList] Error: Notifier must be callable!")

	def removeSaveNotifier(self, notifier):
		while notifier in self.onSave:
			self.onSave.remove(notifier)

	def clearSaveNotifiers(self):
		self.onSave = []

	def keyCancel(self):
		self.closeConfigList(())

	def closeRecursive(self):
		self.closeConfigList((True,))

	def closeConfigList(self, closeParameters=()):
		if self["config"].isChanged() or self.manipulatedItems:
			self.closeParameters = closeParameters
			self.session.openWithCallback(self.cancelConfirm, MessageBox, self.cancelMsg, default=False, type=MessageBox.TYPE_YESNO)
		else:
			self.close(*closeParameters)

	def cancelConfirm(self, result):
		if not result:
			return
		for item in set(self["config"].list + self.manipulatedItems):
			if len(item) > 1:
				item[1].cancel()
		if not hasattr(self, "closeParameters"):
			self.closeParameters = ()
		self.close(*self.closeParameters)

	def createSummary(self):  # This should not be required if ConfigList is invoked via Setup (as it should).
		from Screens.Setup import SetupSummary
		return SetupSummary

	def run(self):  # Allow ConfigList based screens to be processed from the Wizard.
		self.keySave()

	def dummyConfigActions(self, value):  # Temporary support for legacy code and plugins that hasn't yet been updated.
		self["configActions"].setEnabled(value)
		self["navigationActions"].setEnabled(value)
		self["menuConfigActions"].setEnabled(value)
		self["editConfigActions"].setEnabled(value)

	def dummyVKBActions(self, value):  # Temporary support for legacy code and plugins that hasn't yet been updated.
		self["virtualKeyBoardActions"].setEnabled(value)


class DummyActions:  # Temporary support for legacy code and plugins that hasn't yet been updated.
	def setEnabled(self, enabled):
		pass

	def destroy(self):
		pass

	def execBegin(self):
		pass

	def execEnd(self):
		pass
