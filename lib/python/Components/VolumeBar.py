from GUIComponent import GUIComponent
from VariableValue import VariableValue

from enigma import eSlider


class VolumeBar(VariableValue, GUIComponent):
	def __init__(self):
		VariableValue.__init__(self)
		GUIComponent.__init__(self)

	GUI_WIDGET = eSlider

	def postWidgetCreate(self, instance):
		instance.setRange(0, 100)
