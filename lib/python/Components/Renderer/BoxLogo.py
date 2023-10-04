from enigma import ePixmap
from Components.Renderer.Renderer import Renderer
from Tools.HardwareInfo import HardwareInfo
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename

class BoxLogo(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.width = 302
		self.height = 60
		defaultPngName = resolveFilename(SCOPE_CURRENT_SKIN, "icons/logos/deflogo.svg")
		is_svg = defaultPngName.endswith(".svg")
		self.defaultLogo = LoadPixmap(defaultPngName, width=self.width, height=0 if is_svg else self.height)
		
	GUI_WIDGET = ePixmap

	def changed(self, what):
		pass
				
	def onShow(self):
		print("[BoxLogo] show")
		if self.instance:
			model = HardwareInfo().get_device_model()
			print("[BoxLogo] model: " + model)
			pngname = resolveFilename(SCOPE_CURRENT_SKIN, "icons/logos/" + model + ".svg")
			is_svg = pngname.endswith(".svg")
			png = LoadPixmap(pngname, width=self.width, height=0 if is_svg else self.height)
			if png != None:
				self.instance.setPixmap(png)
			elif self.defaultLogo != None:
				self.instance.setPixmap(self.defaultLogo)