from Screen import Screen
from Components.Label import Label
import enigma
import skin

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
		def findLongerText():
			text_width=0
			key_with_max=0
			for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0):
				item = self["key%d" % x]
				nowrap = item.instance.getNoWrap()
				item.instance.setNoWrap(1)
				width = item.instance.calculateSize().width()
				item.instance.setNoWrap(nowrap)
				if width > text_width:
					text_width = width
					key_with_max = x
			return key_with_max, text_width

		def testFilling(key, label_width):
			item = self["key%d" % key]
			nowrap = item.instance.getNoWrap()
			item.instance.setNoWrap(1)
			res = label_width >= item.instance.calculateSize().width()
			item.instance.setNoWrap(nowrap)
			return res

		item = "key0"
		fnt = self[item].instance.getFont()
		label_width = self[item].instance.size().width()
		key, text_width = findLongerText()
		if label_width < text_width:
			for i in range(int(fnt.pointSize)-1, 10, -1): # minimum 11 px
				fnt = enigma.gFont(fnt.family, i)
				self["key%d" % key].instance.setFont(fnt)
				if testFilling(key, label_width):
					for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0):
						self["key%d" % x].instance.setFont(fnt)
					self["help1"].instance.setFont(fnt)
					self["help2"].instance.setFont(fnt)
					break
