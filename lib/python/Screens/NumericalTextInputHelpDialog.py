from Screen import Screen
from Components.Label import Label
import enigma

class NumericalTextInputHelpDialog(Screen):
	def __init__(self, session, textinput):
		Screen.__init__(self, session)
		self["help1"] = Label(text="<")
		self["help2"] = Label(text=">")
		for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0):
			self["key%d" % x] = Label(text=textinput.mapping[x].encode("utf-8"))
		self.last_marked = 0
		self.onLayoutFinish.append(self.resizeFont)

	def update(self, textinput):
		if 0 <= self.last_marked <= 9:
			self["key%d" % self.last_marked].setMarkedPos(-1)
		if 0 <= textinput.lastKey <= 9:
			self["key%d" % textinput.lastKey].setMarkedPos(textinput.pos)
			self.last_marked = textinput.lastKey

	def resizeFont(self):
		key=0
		text_width=0
		for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0):
			item = self["key%d" % x]
			nowrap = item.instance.getNoWrap()
			item.instance.setNoWrap(1)
			width = item.instance.calculateSize().width()
			item.instance.setNoWrap(nowrap)
			if width > text_width:
				text_width = width
				key = x
		fnt = self["key%d" % key].instance.getFont()
		label_width = self["key%d" % key].instance.size().width()
		if label_width < text_width:
			newSize = fnt.pointSize * label_width / text_width
			fnt = enigma.gFont(fnt.family, newSize)
			for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0):
				self["key%d" % x].instance.setFont(fnt)
			self["help1"].instance.setFont(fnt)
			self["help2"].instance.setFont(fnt)
