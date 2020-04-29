from Screen import Screen
from Components.Label import Label
import enigma

class NumericalTextInputHelpDialog(Screen):
	def __init__(self, session, textinput):
		Screen.__init__(self, session)
		self["help1"] = Label(text="<")
		self["help2"] = Label(text=">")
		for x in range(0, 10):
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
		def getsize(x):
			item = self["key%d" % x]
			nowrap = item.instance.getNoWrap()
			item.instance.setNoWrap(1)
			width = item.instance.calculateSize().width()
			item.instance.setNoWrap(nowrap)
			return width

		text_width = max([getsize(x) for x in range (0, 10)])
		label_width = self["key0"].instance.size().width()
		if label_width < text_width:
			fnt = self["key0"].instance.getFont()
			newSize = max(fnt.pointSize * label_width / text_width, int(0.6 * fnt.pointSize))
			fnt = enigma.gFont(fnt.family, newSize)
			for x in range(0, 10):
				self["key%d" % x].instance.setFont(fnt)
			self["help1"].instance.setFont(fnt)
			self["help2"].instance.setFont(fnt)
