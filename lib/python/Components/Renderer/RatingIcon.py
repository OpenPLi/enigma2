from Components.Renderer.Renderer import Renderer
from Tools.Directories import SCOPE_GUISKIN, resolveFilename

from enigma import ePixmap


class RatingIcon(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.small = 0

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "small":
				if value == "1":
					self.small = 1
		self.skinAttributes = attribs
		rc = Renderer.applySkin(self, desktop, parent)
		self.changed((self.CHANGED_DEFAULT,))
		return rc

	def changed(self, what):
		if self.source and hasattr(self.source, "text") and self.instance:
			if what[0] == self.CHANGED_CLEAR:
				self.instance.setPixmap(None)
			else:
				if self.source.text:
					age = int(self.source.text.replace("+", ""))
					if age == 0:
						self.instance.setPixmap(None)
						self.instance.hide()
						return
					if age <= 15:
						age += 3

					pngEnding = "ratings/%d%s.png" % (age, "_s" if self.small else "")
					pngname = resolveFilename(SCOPE_GUISKIN, pngEnding)
					self.instance.setPixmapFromFile(pngname)
					self.instance.show()
				else:
					self.instance.setPixmap(None)
