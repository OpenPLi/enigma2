from Components.VariableText import VariableText
from Renderer import Renderer
from enigma import eLabel, eEPGCache, eServiceReference
from time import localtime, strftime
from skin import parseColor

class NextEpgInfo(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.epgcache = eEPGCache.getInstance()
		self.numberOfItems = 1
		self.hideLabel = 0
		self.timecolor = ""
		self.labelcolor = ""
		self.foregroundColor = "00?0?0?0"
		self.numOfSpaces = 1

	GUI_WIDGET = eLabel

	def changed(self, what):
		self.text = ""
		reference = self.source.service
		info = reference and self.source.info
		if info:
			currentEvent = self.source.getCurrentEvent()
			if currentEvent:
				if not self.epgcache.startTimeQuery(eServiceReference(reference.toString()), currentEvent.getBeginTime() + currentEvent.getDuration()):
					spaces = " "*self.numOfSpaces
					if self.numberOfItems == 1:
						event = self.epgcache.getNextTimeEntry()
						if event:
							if self.hideLabel:
								self.text = "%s%s%s%s%s" % (self.timecolor, strftime("%H:%M", localtime(event.getBeginTime())), spaces, self.foregroundColor, event.getEventName())
							else:
								self.text = "%s%s:%s%s%s" % (self.labelcolor, pgettext("now/next: 'next' event label", "Next"), spaces, self.foregroundColor, event.getEventName())
					else:
						for x in range(self.numberOfItems):
							event = self.epgcache.getNextTimeEntry()
							if event:
								self.text += "%s%s%s%s%s\n" % (self.timecolor, strftime("%H:%M", localtime(event.getBeginTime())), spaces, self.foregroundColor, event.getEventName())
						if not self.hideLabel:
							self.text = self.text and "%s%s\n%s" % (self.labelcolor, pgettext("now/next: 'next' event label", "Next"), self.text) or ""

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes:
			if attrib == "NumberOfItems":
				self.numberOfItems = int(value)
				attribs.append((attrib, value))
			if attrib == "noLabel":
				self.hideLabel = int(value)
				attribs.append((attrib, value))
			if attrib == "numOfSpaces":
				self.numOfSpaces = int(value)
				attribs.append((attrib, value))
			if attrib == "timeColor":
				self.timecolor = self.hex2strColor(parseColor(value).argb())
				attribs.append((attrib, value))
			if attrib == "labelColor":
				self.labelcolor = self.hex2strColor(parseColor(value).argb())
				attribs.append((attrib, value))
			if attrib == "foregroundColor":
				self.foregroundColor = self.hex2strColor(parseColor(value).argb())
				attribs.append((attrib, value))
		for (attrib, value) in attribs:
			self.skinAttributes.remove((attrib, value))
		self.timecolor = self.formatColorString(self.timecolor)
		self.labelcolor  = self.formatColorString(self.labelcolor)
		self.foregroundColor  = self.formatColorString(self.foregroundColor)
		return Renderer.applySkin(self, desktop, parent)

# 	hex:
#	0 1 2 3 4 5 6 7 8 9 a b c d e f
# 	converts to:
#	0 1 2 3 4 5 6 7 8 9 : ; < = > ?
	def hex2strColor(self, rgb):
		out = ""
		for i in range(28,-1,-4):
			out += "%s" % chr(0x30 + (rgb>>i & 0xf))
		return  out

	def formatColorString(self, color):
		if color:
			return "%s%s" % ('\c', color)
		return "%s%s" % ('\c', self.foregroundColor)