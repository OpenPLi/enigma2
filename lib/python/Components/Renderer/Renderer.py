from Components.GUIComponent import GUIComponent
from Components.Element import Element


class Renderer(GUIComponent, Element):
	def __init__(self):
		Element.__init__(self)
		GUIComponent.__init__(self)

	def onShow(self):
		self.suspended = False

	def onHide(self):
		self.suspended = True

	def onContainerShown(self):
		pass
	
	def bindKeys(self, container):
		pass

	def connectRelatedElement(self, relatedElementName, container):
		self.source = container[relatedElementName]
		self.bindKeys(container)
		container.onShow.append(self.onContainerShown)
