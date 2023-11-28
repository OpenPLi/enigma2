from Screens.Screen import Screen

from Components.Label import Label
from Components.Pixmap import MultiPixmap


class PVRState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["state"] = Label(text="")
		self["speed"] = Label()
		self["statusicon"] = MultiPixmap()

class TimeshiftState(PVRState):
	pass
