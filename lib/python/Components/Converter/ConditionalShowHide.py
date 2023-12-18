from enigma import eTimer
from Components.Converter.Converter import Converter


class ConditionalShowHide(Converter):
	def __init__(self, argstr):
		Converter.__init__(self, argstr)
		args = argstr.split(',')
		self.invert = "Invert" in args
		self.blink = "Blink" in args
		if self.blink:
			self.blinktime = len(args) > 1 and args[1].isdigit() and int(args[1]) or 500
			if len(args) == 3:
				self.asymmetric = True
				self.blinkhide = args[2].isdigit() and int(args[2]) or 500
			else:
				self.asymmetric = False
			self.timer = eTimer()
			self.timer.callback.append(self.blinkFunc)
		else:
			self.timer = None

	# Make ConditionalShowHide transparent to upstream attribute requests
	def __getattr__(self, name):
		return getattr(self.source, name)

	def blinkFunc(self):
		if self.blinking:
			show = False
			for x in self.downstream_elements:
				x.visible = not x.visible
				show = x.visible
			if self.asymmetric:
				self.timer.start(self.blinkhide if show else self.blinktime, True)

	def startBlinking(self):
		self.blinking = True
		if self.asymmetric:
			self.timer.start(self.blinktime, True)
		else:
			self.timer.start(self.blinktime)

	def stopBlinking(self):
		self.blinking = False
		for x in self.downstream_elements:
			if x.visible:
				x.hide()
		self.timer.stop()

	def calcVisibility(self):
		b = self.source.boolean
		if b is None:
			b = False
		b ^= self.invert
		return b

	def changed(self, what):
		vis = self.calcVisibility()
		if self.blink:
			if vis:
				self.startBlinking()
			else:
				self.stopBlinking()
		else:
			for x in self.downstream_elements:
				x.visible = vis
		super(Converter, self).changed(what)

	def connectDownstream(self, downstream):
		Converter.connectDownstream(self, downstream)
		vis = self.calcVisibility()
		if self.blink:
			if vis:
				self.startBlinking()
			else:
				self.stopBlinking()
		else:
			downstream.visible = self.calcVisibility()

	def destroy(self):
		if self.timer:
			self.timer.callback.remove(self.blinkFunc)
