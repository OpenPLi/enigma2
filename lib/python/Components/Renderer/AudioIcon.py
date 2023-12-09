from Components.Renderer.Renderer import Renderer
from enigma import ePixmap
from Tools.Directories import fileExists, SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap

class AudioIcon(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.size = None
		self.width = 51
		self.height = 30
		self.nameAudioCache = { }
		self.pngname = ""
		self.path = ""

	def applySkin(self, desktop, parent):
		attribs = [ ]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.path = value
				if value.endswith("/"):
					self.path = value
				else:
					self.path = value + "/"
			else:
				attribs.append((attrib,value))
			if attrib == "size":
				value = value.split(',')
				if len(value) == 2:
					self.width = int(value[0])
					self.height = int(value[1])
					self.size = value[0] + "x" + value[1]
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] != self.CHANGED_CLEAR:
				sname = self.source.text
				pngname = self.nameAudioCache.get(sname, "")
				if pngname == "":
					pngname = self.findAudioIcon(sname)
					if pngname != "":
						self.nameAudioCache[sname] = pngname
			if pngname == "":
				self.instance.hide()
			else:
				self.instance.show()
			if pngname != "" and self.pngname != pngname:
				is_svg = pngname.endswith(".svg")
				png = LoadPixmap(pngname, width=self.width, height=0 if is_svg else self.height)
				self.instance.setPixmap(png)
				self.pngname = pngname

	def findAudioIcon(self, audioName):
		pngname =  resolveFilename(SCOPE_GUISKIN, self.path + audioName + ".svg") 
		if fileExists(pngname):
			return pngname
		return ""

