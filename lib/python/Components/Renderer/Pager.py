from Components.Renderer.Renderer import Renderer
from Components.ActionMap import ActionMap
from skin import parseColor, parseFont, parseScale
import math

from enigma import eListbox, gFont, eListboxPythonMultiContent, RT_WRAP, RT_VALIGN_TOP, RT_VALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, BT_SCALE, BT_ALPHABLEND, BT_KEEP_ASPECT_RATIO, BT_ALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap

from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend


class Pager(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l_list = []
		self.l.setBuildFunc(self.buildEntry)
		self.current_index = 0
		self.itemHeight = 25
		self.sourceHeight = 25
		self.pagerForeground = 15774720
		self.pagerBackground = 624318628
		self.l.setItemHeight(self.itemHeight)
		self.l.setFont(1, gFont('Regular', 18))
		self.l.setFont(2, gFont('Regular', 22))
		self.l.setFont(3, gFont('Regular', 22))
		self.l.setFont(4, gFont('Regular', 22))
		self.l.setFont(5, gFont('Regular', 22))
		self.picDotPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dot.png"))
		self.picDotCurPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dotfull.png"))

	def onContainerShown(self):
		# disable listboxes default scrollbars
		if self.source.instance:
			self.source.instance.setScrollbarMode(2)

		if self.initPager not in self.source.onSelectionChanged:
			self.source.onSelectionChanged.append(self.initPager)
		self.initPager()

	def bindKeys(self, container):
		container["pager_actions"] = ActionMap(["DirectionActions"], {
			"left": self.keyPageUp,
			"right": self.keyPageDown,
			"up": self.keyUp,
			"down": self.keyDown,
			"upRepeated": self.keyUp,
		 	"downRepeated": self.keyDown,
		 	"leftRepeated": self.keyPageUp,
		 	"rightRepeated": self.keyPageDown
		}, -1)
		
	GUI_WIDGET = eListbox

	def buildEntry(self, currentPage, pageCount):
		width = self.l.getItemSize().width()
		xPos = width
		height = self.l.getItemSize().height()

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
					xPos += pixd_width + 5
		return res

	def selChange(self, currentPage, pagesCount):
		self.l_list = []
		self.l_list.append((currentPage, pagesCount))
		self.l.setList(self.l_list)

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)

	def getCurrentIndex(self):
		if hasattr(self.source, "index"):
			return self.source.index
		return self.source.l.getCurrentSelectionIndex()

	def getSourceHeight(self):
		return self.source.instance.size().height()

	def getListCount(self):
		if hasattr(self.source, 'listCount'):
			return self.source.listCount
		elif hasattr(self.source, 'list'):
			return len(self.source.list)
		else:
			return len(self.source.list)

	def getListItemHeight(self):
		if hasattr(self.source, 'content'):
			return self.source.content.getItemSize().height()
		return self.source.l.getItemSize().height()
	
	def initPager(self):
		listH = self.getSourceHeight()
		print("srcH: " + str(listH))
		if listH > 0:
			current_index = self.getCurrentIndex()
			print("current_index: " + str(current_index))
			listCount = self.getListCount()
			print("listCount: " + str(listCount))
			itemHeight = self.getListItemHeight()
			print("itemHeight: " + str(itemHeight))
			items_per_page = math.ceil(listH/itemHeight) - 1
			if items_per_page > 0:
				currentPageIndex = math.floor(current_index/items_per_page)
				pagesCount = math.ceil(listCount/items_per_page) - 1
				self.selChange(currentPageIndex,pagesCount)

	def keyUp(self):
		if self.source.instance is not None:
			self.source.instance.moveSelection(self.source.instance.moveUp)

	def keyDown(self):
		if self.source.instance is not None:
			self.source.instance.moveSelection(self.source.instance.moveDown)

	def keyPageDown(self):
		if self.source.instance is not None:
			self.source.instance.moveSelection(self.source.instance.pageDown)

	def keyPageUp(self):
		if self.source.instance is not None:
			self.source.instance.moveSelection(self.source.instance.pageUp)
		
	def applySkin(self, desktop, parent):
		attribs = [ ]
		for (attrib, value) in self.skinAttributes:
			if attrib == "pagerForeground":
				self.pagerForeground = parseColor(value).argb()
			elif attrib == "pagerBackground":
				self.pagerBackground = parseColor(value).argb()
			elif attrib == "picPage":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotPage = pic
			elif attrib == "picPageCurrent":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotCurPage = pic
			# elif attrib == "connection":
			# 	self.source = parent[value]
			# 	self.initializeKeyBindings(parent)
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	