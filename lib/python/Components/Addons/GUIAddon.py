from Components.GUIComponent import GUIComponent


class GUIAddon(GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)

	def connectRelatedElement(self, relatedElementName, container):
		self.source = container[relatedElementName]
		container.onShow.append(self.onContainerShown)

	def onContainerShown(self):
		pass
