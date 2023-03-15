from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, BT_ALIGN_CENTER

from skin import parseScale

from Components.MultiContent import MultiContentEntryPixmapAlphaBlend

from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class Pager(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(25)
		self.spacing = 5
		self.picDotPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dot.png"))
		self.picDotCurPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dotfull.png"))

	def onContainerShown(self):
		# disable listboxes default scrollbars
		if hasattr(self.source, "instance") and hasattr(self.source.instance, "setScrollbarMode"):
			self.source.instance.setScrollbarMode(2)

		if self.initPager not in self.source.onSelectionChanged:
			self.source.onSelectionChanged.append(self.initPager)
		self.initPager()

	GUI_WIDGET = eListbox

	def buildEntry(self, currentPage, pageCount):
		width = self.l.getItemSize().width()
		xPos = width

		if self.picDotPage:
			pixd_size = self.picDotPage.size()
			pixd_width = pixd_size.width()
			pixd_height = pixd_size.height()
			width_dots = pixd_width + (pixd_width + 5)*pageCount
			xPos = (width - width_dots)/2 - pixd_width/2
		res = [ None ]
		if pageCount > 0:
			for x in range(pageCount + 1):
				if self.picDotPage and self.picDotCurPage:
					res.append(MultiContentEntryPixmapAlphaBlend(
								pos=(xPos, 0),
								size=(pixd_width, pixd_height),
								png=self.picDotCurPage if x == currentPage else self.picDotPage,
								backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					xPos += pixd_width + self.spacing
		return res

	def selChange(self, currentPage, pagesCount):
		l_list = []
		l_list.append((currentPage, pagesCount))
		self.l.setList(l_list)

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def getCurrentIndex(self):
		if hasattr(self.source, "index"):
			return self.source.index
		return self.source.l.getCurrentSelectionIndex()

	def getSourceHeight(self):
		if self.source.__class__.__name__ == "List": # Components.Sources.List, used by MainMenu
			return self.source.master.master.instance.size().height()
		return self.source.instance.size().height()

	def getListCount(self):
		if hasattr(self.source, 'listCount'):
			return self.source.listCount
		elif hasattr(self.source, 'list'):
			return len(self.source.list)
		else:
			return 0

	def getListItemHeight(self):
		if hasattr(self.source, 'content'):
			return self.source.content.getItemSize().height()
		if hasattr(self.source, 'item_height'): # Components.Sources.List, used by MainMenu
			return self.source.item_height
		return self.source.l.getItemSize().height()
	
	def initPager(self):
		if self.source.__class__.__name__ == "ScrollLabel":
			currentPageIndex = self.source.curPos//self.source.pageHeight
			if not ((self.source.TotalTextHeight - self.source.curPos) % self.source.pageHeight):
				currentPageIndex += 1
			pagesCount = -(-self.source.TotalTextHeight//self.source.pageHeight) - 1
			self.selChange(currentPageIndex,pagesCount)
		else:
			listH = self.getSourceHeight()
			if listH > 0:
				current_index = self.getCurrentIndex()
				listCount = self.getListCount()
				itemHeight = self.getListItemHeight()
				items_per_page = listH//itemHeight
				if items_per_page > 0:
					currentPageIndex = current_index//items_per_page
					pagesCount = -(listCount//-items_per_page) - 1
					self.selChange(currentPageIndex,pagesCount)

	def applySkin(self, desktop, parent):
		attribs = [ ]
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "picPage":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotPage = pic
			elif attrib == "picPageCurrent":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotCurPage = pic
			elif attrib == "itemHeight":
				self.l.setItemHeight(parseScale(value))
			elif attrib == "spacing":
				self.spacing = parseScale(value)
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return GUIAddon.applySkin(self, desktop, parent)