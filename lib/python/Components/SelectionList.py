from MenuList import MenuList
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT
from Tools.LoadPixmap import LoadPixmap
from skin import applySkinFactor, fonts, parameters


def SelectionEntryComponent(description, value, index, selected):
	dx, dy, dw, dh = parameters.get("SelectionListDescr", applySkinFactor(25, 3, 650, 30))
	res = [
		(description, value, index, selected),
		(eListboxPythonMultiContent.TYPE_TEXT, dx, dy, dw, dh, 0, RT_HALIGN_LEFT, description)
	]
	if selected:
		selectionpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "icons/lock_on.png"))
	else:
		selectionpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "icons/lock_off.png"))
	ix, iy, iw, ih = parameters.get("SelectionListLock", applySkinFactor(0, 2, 25, 24))
	res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, ix, iy, iw, ih, selectionpng))
	return res


class SelectionList(MenuList):
	def __init__(self, list=None, enableWrapAround=False):
		MenuList.__init__(self, list or [], enableWrapAround, content=eListboxPythonMultiContent)
		font = fonts.get("SelectionList", applySkinFactor("Regular", 20, 30))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])

	def addSelection(self, description, value, index, selected=True):
		self.list.append(SelectionEntryComponent(description, value, index, selected))
		self.setList(self.list)

	def toggleSelection(self):
		if len(self.list):
			idx = self.getSelectedIndex()
			item = self.list[idx][0]
			self.list[idx] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
			self.setList(self.list)

	def getSelectionsList(self):
		return [(item[0][0], item[0][1], item[0][2]) for item in self.list if item[0][3]]

	def toggleAllSelection(self):
		for idx, item in enumerate(self.list):
			item = self.list[idx][0]
			self.list[idx] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
		self.setList(self.list)

	def removeSelection(self, item):
		for it in self.list:
			if it[0][0:3] == item[0:3]:
				self.list.pop(self.list.index(it))
				self.setList(self.list)
				return

	def toggleItemSelection(self, item):
		for idx, i in enumerate(self.list):
			if i[0][0:3] == item[0:3]:
				item = self.list[idx][0]
				self.list[idx] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
				self.setList(self.list)
				return

	def sort(self, sortType=False, flag=False):
		# sorting by sortType:
		# 0 - description
		# 1 - value
		# 2 - index
		# 3 - selected
		self.list.sort(key=lambda x: x[0][sortType], reverse=flag)
		self.setList(self.list)
