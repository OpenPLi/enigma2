from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, BT_ALIGN_CENTER, BT_VALIGN_CENTER

from skin import parseScale, applySkinFactor

from Components.MultiContent import MultiContentEntryPixmapAlphaBlend
from Components.Sources.List import List

from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class Pager(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(25)  # 25 is the height of the default images. For other images set the height in the skin.
		self.l.setItemWidth(25)  # 25 is the width of the default images. For other images set the width in the skin.
		self.spacing = applySkinFactor(5)
		self.picDotPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dot.png"))
		self.picDotCurPage = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/dotfull.png"))
		self.picShevronLeft = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevronleft.png"))
		self.picShevronRight = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevronright.png"))
		self.picShevronUp = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevronup.png"))
		self.picShevronDown = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/shevrondown.png"))
		self.showIcons = "showAll"  # can be "showAll", "onlyFirst", "onlyLast"
		self.orientations = {"orHorizontal": eListbox.orHorizontal, "orVertical": eListbox.orVertical}
		self.orientation = eListbox.orHorizontal
		self.max_pages = 10

	def onContainerShown(self):
		# disable listboxes default scrollbars
		if hasattr(self.source, "instance") and hasattr(self.source.instance, "setScrollbarMode"):
			self.source.instance.setScrollbarMode(eListbox.showNever)

		if self.source and hasattr(self.source, "onVisibilityChange"):
			self.source.onVisibilityChange.append(self.onSourceVisibleChanged)

		onSelectionChanged = x if (x := getattr(self.source, "onSelectionChanged", None)) is not None else getattr(self.source, "onSelChanged", None)

		if isinstance(onSelectionChanged, list) and self.initPager not in onSelectionChanged:
			onSelectionChanged.append(self.initPager)
				
		self.initPager()

	GUI_WIDGET = eListbox

	def onSourceVisibleChanged(self, visible):
		if visible:
			self.show()
		else:
			self.hide()

	def buildEntry(self, currentPage, pageCount):
		width = self.l.getItemSize().width()
		height = self.l.getItemSize().height()
		xPos = width
		yPos = height

		if self.picDotPage:
			pixd_size = self.picDotPage.size()
			pixd_width = pixd_size.width()
			pixd_height = pixd_size.height()
			width_dots = pixd_width + (pixd_width + self.spacing) * pageCount
			height_dots = pixd_height + (pixd_height + self.spacing) * pageCount
			xPos = (width - width_dots) / 2 - pixd_width / 2 if self.showIcons == "showAll" else 0
			yPos = (height - height_dots) / 2 - pixd_height / 2 if self.showIcons == "showAll" else 0
		res = [None]
		if self.showIcons == "showAll" and pageCount > 0 and self.max_pages > 0 and pageCount > self.max_pages:
			width_dots = pixd_width + (pixd_width + self.spacing) * (2 if currentPage > 0 and currentPage < pageCount else 1)
			xPos = (width - width_dots) / 2 - pixd_width / 2
			yPos = (height - height_dots) / 2 - pixd_height / 2
			if self.orientation == eListbox.orHorizontal:
				if currentPage > 0:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(xPos, 0),
						size=(pixd_width, pixd_height),
						png=self.picShevronLeft,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					xPos += pixd_width + self.spacing
				res.append(MultiContentEntryPixmapAlphaBlend(
					pos=(xPos, 0),
					size=(pixd_width, pixd_height),
					png=self.picDotCurPage,
					backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
				xPos += pixd_width + self.spacing
				if currentPage < pageCount:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(xPos, 0),
						size=(pixd_width, pixd_height),
						png=self.picShevronRight,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
			else:
				if currentPage > 0:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(0, yPos),
						size=(pixd_width, pixd_height),
						png=self.picShevronLeft,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					yPos += pixd_height + self.spacing
				res.append(MultiContentEntryPixmapAlphaBlend(
					pos=(0, yPos),
					size=(pixd_width, pixd_height),
					png=self.picDotCurPage,
					backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
				yPos += pixd_height + self.spacing
				if currentPage < pageCount:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(0, yPos),
						size=(pixd_width, pixd_height),
						png=self.picShevronRight,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
		elif pageCount > (0 if self.showIcons == "showAll" else -1):
			pages = list(range(pageCount + 1))
			# add option to show just first or last icon
			if self.showIcons == "onlyFirst":
				pages = [pages[0]]
			elif self.showIcons == "onlyLast":
				pages = [pages[-1]]
			for x in pages:
				if self.picDotPage and self.picDotCurPage:
					if self.orientation == eListbox.orHorizontal:
						res.append(
							MultiContentEntryPixmapAlphaBlend(
								pos=(xPos, 0),
								size=(pixd_width, pixd_height),
								png=self.picDotCurPage if x == currentPage else self.picDotPage,
								backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
						xPos += pixd_width + self.spacing
					else:
						res.append(
							MultiContentEntryPixmapAlphaBlend(
								pos=(0, yPos),
								size=(pixd_width, pixd_height),
								png=self.picDotCurPage if x == currentPage else self.picDotPage,
								backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER | BT_VALIGN_CENTER))
						yPos += pixd_height + self.spacing

		return res

	def selChange(self, currentPage, pagesCount):
		l_list = []
		l_list.append((currentPage, pagesCount))
		self.l.setList(l_list)

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def getSourceOrientation(self):
		if isinstance(self.source, List):  # Components.Sources.List
			orig_source = self.source.master.master
		else:
			orig_source = self.source
		if hasattr(orig_source, "instance") and hasattr(orig_source.instance, "getOrientation"):
			return orig_source.instance.getOrientation()
		return eListbox.orVertical

	def getCurrentIndex(self):
		if hasattr(self.source, "index"):
			return self.source.index
		return self.source.l.getCurrentSelectionIndex()

	def getSourceSize(self):
		if isinstance(self.source, List):  # Components.Sources.List
			return self.source.master.master.instance.size()
		return self.source.instance.size()

	def getListCount(self):
		if hasattr(self.source, 'listCount'):
			return self.source.listCount
		elif hasattr(self.source, 'list'):
			return len(self.source.list)
		elif hasattr(self.source, 'l') and hasattr(self.source.l, 'getListSize'):
			return self.source.l.getListSize()
		return 0

	def getListItemSize(self):
		if isinstance(self.source, List):  # Components.Sources.List
			orig_source = self.source.master.master
		else:
			orig_source = self.source
		if hasattr(orig_source, 'content'):
			return orig_source.content.getItemSize()

		return orig_source.l.getItemSize()

	def initPager(self):
		if self.source.__class__.__name__ == "ScrollLabel":
			currentPageIndex = self.source.curPos // self.source.pageHeight
			if not ((self.source.TotalTextHeight - self.source.curPos) % self.source.pageHeight):
				currentPageIndex += 1
			pagesCount = -(-self.source.TotalTextHeight // self.source.pageHeight) - 1
			self.selChange(currentPageIndex, pagesCount)
		else:
			l_orientation = self.getSourceOrientation()
			if l_orientation == eListbox.orVertical:
				listControledlSize = self.getSourceSize().height()
			else:
				listControledlSize = self.getSourceSize().width()

			if listControledlSize > 0:
				current_index = self.getCurrentIndex()
				listCount = self.getListCount()
				if l_orientation == eListbox.orVertical:
					itemControlledSizeParam = self.getListItemSize().height()
				else:
					itemControlledSizeParam = self.getListItemSize().width()
				items_per_page = listControledlSize // itemControlledSizeParam
				if items_per_page > 0:
					currentPageIndex = current_index // items_per_page
					pagesCount = -(listCount // -items_per_page) - 1
					self.selChange(currentPageIndex, pagesCount)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "picPage":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotPage = pic
			elif attrib == "picPageCurrent":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picDotCurPage = pic
			elif attrib == "picL":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronLeft = pic
			elif attrib == "picR":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronRight = pic
			elif attrib == "picU":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronUp = pic
			elif attrib == "picD":
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
				if pic:
					self.picShevronDown = pic
			elif attrib == "itemHeight":
				self.l.setItemHeight(parseScale(value))
			elif attrib == "itemWidth":
				self.l.setItemWidth(parseScale(value))
			elif attrib == "spacing":
				self.spacing = parseScale(value)
			elif attrib == "showIcons":
				self.showIcons = value
			elif attrib == "maxPages":
				self.max_pages = parseScale(value)
			elif attrib == "orientation":
				self.orientation = self.orientations.get(value, self.orientations["orHorizontal"])
				if self.orientation == eListbox.orHorizontal:
					self.instance.setOrientation(eListbox.orVertical)
					self.l.setOrientation(eListbox.orVertical)
				else:
					self.instance.setOrientation(eListbox.orHorizontal)
					self.l.setOrientation(eListbox.orHorizontal)
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return GUIAddon.applySkin(self, desktop, parent)
