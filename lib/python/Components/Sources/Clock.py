from Components.Element import cached
from enigma import eTimer
from time import time as getTime

from Components.Sources.Source import Source


class Clock(Source):
	def __init__(self):
		Source.__init__(self)
		self.clock_timer = eTimer()
		self.clock_timer.callback.append(self.poll)
		self.startTimer()

	@cached
	def getClock(self):
		return getTime()

	time = property(getClock)

	def poll(self):
		self.changed((self.CHANGED_POLL,))
		self.startTimer()

	def startTimer(self):
		delay = int((1.0 - (getTime() % 1.0)) * 1000) + 20
		self.clock_timer.start(delay, True)

	def doSuspend(self, suspended):
		if suspended:
			self.clock_timer.stop()
		else:
			self.poll()

	def destroy(self):
		self.clock_timer.callback.remove(self.poll)
		Source.destroy(self)
