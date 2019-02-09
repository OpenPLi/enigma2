from __future__ import absolute_import
from .Screen import Screen
from Components.Pixmap import Pixmap

class UnhandledKey(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["UnhandledKeyPixmap"] = Pixmap()
