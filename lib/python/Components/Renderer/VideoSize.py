from Components.VariableText import VariableText
from enigma import eLabel, iServiceInformation, eServiceReference
from Components.Renderer.Renderer import Renderer

#
# borrowed from vali, addapter for openpli
#


class VideoSize(Renderer, VariableText):
	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	GUI_WIDGET = eLabel

	def changed(self, what):
		service = self.source.service
		isRef = isinstance(service, eServiceReference)
		info = service.info() if (service and not isRef) else None
		if info is None:
			self.text = ""
			return
		xresol = info.getInfo(iServiceInformation.sVideoWidth)
		yresol = info.getInfo(iServiceInformation.sVideoHeight)
		if xresol > 0:
			self.text = str(xresol) + 'x' + str(yresol)
		else:
			self.text = ''
