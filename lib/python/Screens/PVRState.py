from Screen import Screen

from Components.Label import Label
from Components.Pixmap import MultiPixmap

class PVRState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["state"] = Label(text="")
		self["statespeed"] = Label(text="")
		# this is multipixmap and pixmaps have to be ordered as follows: picFF,picRew,picPlay,picPause
		self["stateicon"] = MultiPixmap()
		self["stateicon"].hide()


class TimeshiftState(PVRState):
	pass
