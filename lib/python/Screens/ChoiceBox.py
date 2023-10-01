from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.config import config, ConfigSubsection, ConfigText
from Components.Label import Label
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Sources.StaticText import StaticText
from enigma import ePoint, eSize, getDesktop

config.misc.pluginlist = ConfigSubsection()
config.misc.pluginlist.eventinfo_order = ConfigText(default="")
config.misc.pluginlist.extension_order = ConfigText(default="")


class ChoiceBox(Screen):
	def __init__(self, session, title="", list=[], keys=None, selection=0, skin_name=[], reorderConfig="", windowTitle=None):
		Screen.__init__(self, session)

		if isinstance(skin_name, str):
			skin_name = [skin_name]
		self.skinName = skin_name + ["ChoiceBox"]

		self.reorder_config = reorderConfig
		self["autoresize"] = Label("")  # do not remove, used for autoResize()
		self["description"] = Label()
		self["text"] = Label(title)
		self.list = []
		self.summarylist = []
		self.keymap = {}

		if keys is None:
			self.__keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue"] + (len(list) - 14) * ["dummy"]
		else:
			self.__keys = keys + (len(list) - len(keys)) * ["dummy"]

		if self.reorder_config:
			self.config_type = eval("config.misc.pluginlist." + self.reorder_config)
			if self.config_type.value:
				prev_list = [x for x in zip(list, self.__keys)]  # list() can not be used as it is also a parameter name!
				new_list = []
				for x in self.config_type.value.split(","):
					for entry in prev_list:
						if entry[0][0] == x:
							new_list.append(entry)
							prev_list.remove(entry)
				list = [x for x in zip(*(new_list + prev_list))]  # list() can not be used as it is also a parameter name!
				list, self.__keys = list[0], list[1]
				number = 1
				new_keys = []
				for x in self.__keys:
					if (not x or x.isdigit()) and number <= 10:
						new_keys.append(str(number % 10))
						number += 1
					else:
						new_keys.append(not x.isdigit() and x or "")
				self.__keys = new_keys
		for pos, x in enumerate(list):
			if x:
				strpos = str(self.__keys[pos])
				self.list.append(ChoiceEntryComponent(key=strpos, text=x))
				if self.__keys[pos] != "dummy":
					self.keymap[self.__keys[pos]] = list[pos]
				self.summarylist.append((self.__keys[pos], x[0]))

		self["list"] = ChoiceList(list=self.list, selection=selection)
		self["summary_list"] = StaticText()
		self["summary_selection"] = StaticText()
		self.updateSummary(selection)

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "ColorActions", "DirectionActions", "MenuActions"],
		{
			"ok": self.go,
			"back": self.cancel,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"up": self.up,
			"down": self.down,
			"moveUp": self.additionalMoveUp,
			"moveDown": self.additionalMoveDown,
			"menu": self.setDefaultChoiceList,
			"rightUp": self.rightUp,
			"leftUp": self.leftUp
		}, -1)
		self.title = windowTitle or _("Select")

	def autoResize(self):
		def x_offset():
			return max([line[1][1] for line in self.list])

		def x_width(textsize):
			def getListLineTextWidth(text):
				self["autoresize"].text = text
				return self["autoresize"].instance.calculateSize().width()
			return max(max([getListLineTextWidth(line[0][0]) for line in self.list]), textsize)

		def getMaxDescriptionHeight():
			def getDescrLineHeight(text):
				if len(text) > 2 and isinstance(text[2], str):
					self["description"].text = text[2]
					return self["description"].instance.calculateSize().height()
				return 0
			return max([getDescrLineHeight(line[0]) for line in self.list])

		textsize = self["text"].getSize()
		count = len(self.list)
		count, scrollbar = (10, self["list"].instance.getScrollbarWidth() + 5) if count > 10 else (count, 0)
		offset = self["list"].l.getItemSize().height() * count
		wsizex = x_width(textsize[0]) + x_offset() + 10 + scrollbar
		# precount description size
		descry = self["description"].instance.calculateSize().width()
		self["description"].resize(wsizex - 20, descry if descry > 0 else 0)
		# then get true description height
		descriptionHeight = getMaxDescriptionHeight()
		wsizey = textsize[1] + offset + descriptionHeight
		# move and resize screen
		self["list"].move(0, textsize[1])
		self.instance.resize(eSize(*(wsizex, wsizey)))
		# move and resize description
		self["description"].move(10, textsize[1] + offset)
		self["description"].resize(wsizex - 20, descriptionHeight)
		# resize list
		self["list"].resize(wsizex, offset)
		# center window
		width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
		self.instance.move(ePoint((width - wsizex) // 2, (height - wsizey) // 2))

	def keyLeft(self):
		pass

	def keyRight(self):
		pass

	def rightUp(self):
		self.leftUp()

	def leftUp(self):
		if self.list:
			self.updateSummary(self["list"].getSelectionIndex())

	def updateDescription(self):
		if self.list:
			self.displayDescription(self["list"].getSelectionIndex())

	def up(self):
		if self.list:
			while True:
				self["list"].up()
				curpos = self["list"].getSelectionIndex()
				if self["list"].getCurrent()[0][0] != "--" or curpos == 0:
					self.updateSummary(curpos)
					break

	def down(self):
		if self.list:
			while True:
				self["list"].down()
				curpos = self["list"].getSelectionIndex()
				if self["list"].getCurrent()[0][0] != "--" or curpos == len(self.list) - 1:
					self.updateSummary(curpos)
					break

	# runs a number shortcut
	def keyNumberGlobal(self, number):
		self.goKey(str(number))

	# runs the current selected entry
	def go(self):
		cursel = self["list"].getCurrent()
		if cursel:
			self.goEntry(cursel[0])
		else:
			self.cancel()

	# runs a specific entry
	def goEntry(self, entry):
		if len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			# CALLFUNC wants to have the current selection as argument
			entry[2](entry)
		else:
			self.close(entry)

	# lookups a key in the keymap, then runs it
	def goKey(self, key):
		if key in self.keymap:
			entry = self.keymap[key]
			self.goEntry(entry)

	# runs a color shortcut
	def keyRed(self):
		self.goKey("red")

	def keyGreen(self):
		self.goKey("green")

	def keyYellow(self):
		self.goKey("yellow")

	def keyBlue(self):
		self.goKey("blue")

	def updateSummary(self, curpos=0):
		self.displayDescription(curpos)
		summarytext = ""
		for pos, entry in enumerate(self.summarylist):
			if curpos - 2 < pos < curpos + 5:
				if pos == curpos:
					summarytext += ">"
					self["summary_selection"].text = entry[1]
				elif entry[0] != "dummy":
					summarytext += entry[0]
				summarytext += " " + entry[1] + "\n"
		self["summary_list"].text = summarytext

	def displayDescription(self, curpos=0):
		self["description"].text = self.list[curpos][0][2] if self.list and len(self.list[curpos][0]) > 2 and isinstance(self.list[curpos][0][2], str) else ""

	def cancel(self):
		self.close(None)

	def setDefaultChoiceList(self):
		if self.reorder_config:
			if self.list and self.config_type.value != "":
				self.session.openWithCallback(self.setDefaultChoiceListCallback, MessageBox, _("Sort list to default and exit?"), MessageBox.TYPE_YESNO)
		elif "menu" in self.keymap:
			self.goKey("menu")
		else:
			self.cancel()

	def setDefaultChoiceListCallback(self, answer):
		if answer:
			self.config_type.value = ""
			self.config_type.save()
			self.cancel()

	def additionalMoveUp(self):
		if self.reorder_config:
			self.additionalMove(-1)

	def additionalMoveDown(self):
		if self.reorder_config:
			self.additionalMove(1)

	def additionalMove(self, direction):
		if len(self.list) > 1:
			currentIndex = self["list"].getSelectionIndex()
			swapIndex = (currentIndex + direction) % len(self.list)
			if currentIndex == 0 and swapIndex != 1:
				self.list = self.list[1:] + [self.list[0]]
			elif swapIndex == 0 and currentIndex != 1:
				self.list = [self.list[-1]] + self.list[:-1]
			else:
				self.list[currentIndex], self.list[swapIndex] = self.list[swapIndex], self.list[currentIndex]
			self["list"].setList(self.list)
			if direction == 1:
				self["list"].down()
			else:
				self["list"].up()
			self.config_type.value = ",".join(x[0][0] for x in self.list)
			self.config_type.save()
