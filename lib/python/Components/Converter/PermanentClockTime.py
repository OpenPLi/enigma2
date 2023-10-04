from Components.Converter.Converter import Converter
from Components.Element import cached
from time import localtime, strftime


class PermanentClockTime(Converter, object):
	SECHAND = 1
	MINHAND = 2
	HOURHAND = 3

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "secHand":
			self.type = self.SECHAND
		elif type == "hourHand":
			self.type = self.HOURHAND
		else:
			self.type = self.MINHAND

	@cached
	def getValue(self):
		time = self.source.time
		if time is None:
			return 0
		if self.type == self.SECHAND:
			t = localtime(time)
			c = t.tm_sec
			return c
		elif self.type == self.MINHAND:
			t = localtime(time)
			c = t.tm_min
			return c
		elif self.type == self.HOURHAND:
			t = localtime(time)
			c = t.tm_hour
			m = t.tm_min
			if c > 11:
				c = c - 12
			val = (c * 5) + (m / 12)
			return val
		return 0

	value = property(getValue)