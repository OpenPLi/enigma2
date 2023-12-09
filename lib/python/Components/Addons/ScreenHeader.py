from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER

from skin import applySkinFactor, parseFont, parseColor

from Components.MultiContent import MultiContentEntryText
from Components.Sources.StaticText import StaticText



class ScreenHeader(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(36)
		self.l.setItemWidth(36)
		self.orientation = eListbox.orHorizontal
		self.titleFont = gFont("Regular", applySkinFactor(22))
		self.titleSingleFont = gFont("Regular", applySkinFactor(24))
		self.pathFont = gFont("Regular", applySkinFactor(16))
		self.titleForeground = 0xffffff
		self.pathForeground = 0xffffff
		self.backgroundColor = 0x000000

	def onContainerShown(self):
		for x, val in self.sources.items():
			if self.constructTitleItem not in val.onChanged:
				val.onChanged.append(self.constructTitleItem)
		self.l.setItemHeight(self.instance.size().height())
		self.l.setItemWidth(self.instance.size().width())
		self.constructTitleItem()

	GUI_WIDGET = eListbox

	def updateAddon(self, sequence):
		l_list = []
		l_list.append((sequence,))
		self.l.setList(l_list)

	def buildEntry(self, sequence):
		yPos = 0

		res = [None]
		isOneItem = len(sequence) == 1

		for idx, x in enumerate(sequence):
			foreColor = self.titleForeground if idx == 0 else self.pathForeground
			if isOneItem:
				itemHeight = self.instance.size().height()
			if not isOneItem and idx == 0:
				itemHeight = self.instance.size().height()*2 // 3
			elif idx == 1:
				yPos = self.instance.size().height()*2 // 3 - 3
				itemHeight = self.instance.size().height() // 3
			res.append(MultiContentEntryText(
					pos=(0, yPos),
					size=(self.instance.size().width(), itemHeight),
					font=2 if isOneItem and idx == 0 else idx, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
					text=x.text.rstrip(">"),
					color=foreColor, color_sel=foreColor,
					backcolor=self.backgroundColor, backcolor_sel=self.backgroundColor))
		return res

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def constructTitleItem(self):
		sequence = []
		for x, val in self.sources.items():
			if isinstance(val, StaticText) and val.text:
				if val not in sequence:
					sequence.append(val)

		self.updateAddon(sequence)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "titleFont":
				self.titleFont = parseFont(value, ((1, 1), (1, 1)))
			if attrib == "titleSingleFont":
				self.titleSingleFont = parseFont(value, ((1, 1), (1, 1)))
			elif attrib == "pathFont":
				self.pathFont = parseFont(value, ((1, 1), (1, 1)))
			elif attrib == "titleForegroundColor":
				self.titleForeground = parseColor(value).argb()
			elif attrib == "pathForegroundColor":
				self.pathForeground = parseColor(value).argb()
			elif attrib == "backgroundColor":
				self.backgroundColor = parseColor(value).argb()
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		self.l.setFont(0, self.titleFont)
		self.l.setFont(1, self.pathFont)
		self.l.setFont(2, self.titleSingleFont)
		return GUIAddon.applySkin(self, desktop, parent)
