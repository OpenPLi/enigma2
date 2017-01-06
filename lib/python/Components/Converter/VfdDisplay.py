from datetime import datetime

from enigma import iPlayableService
from Poll import Poll
from Components.Converter.Converter import Converter
from Components.Element import cached


class VfdDisplay(Poll, Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.num = None
		self.showclock = 0
		self.delay = 5000
		self.loop = -1
		self.type = type.split(';')
		if 'Number' in self.type and 'Clock' not in self.type:  # Only channel number
			self.delay = 0
			self.poll_enabled = False
		else:
			self.poll_enabled = True
			if 'Clock' in self.type and 'Number' not in self.type:  # Only clock
				self.showclock = 1
				self.delay = -1
			else:
				for x in self.type:
					if x.isdigit():
						self.delay = int(x) * 1000
						break
				if 'Loop' in self.type and self.delay:
					self.loop = self.delay
			if 'Nozero' in self.type:
				self.hour = '%'
			else:
				self.hour = '%02'
			if '12h' in self.type or '12H' in self.type:
				self.hour = self.hour + 'I'
			else:
				self.hour = self.hour + 'H'

	@cached
	def getText(self):
		if self.showclock == 0:
			if self.delay:
				self.poll_interval = self.delay
				self.showclock = 1
			if self.num:
				return self.num
		else:
			if self.showclock == 1:
				if 'Noblink' in self.type:
					self.poll_interval = self.delay
				else:
					self.poll_interval = 1000
					self.showclock = 3
				clockformat = self.hour + '%02M'
			elif self.showclock == 2:
				self.showclock = 3
				clockformat = self.hour + '%02M'
			else:
				self.showclock = 2
				clockformat = self.hour + ':%02M'
			if self.loop != -1:
				self.loop -= 1000
				if self.loop <= 0:
					self.loop = self.delay
					self.showclock = 0
			return datetime.today().strftime(clockformat)

	text = property(getText)

	def changed(self, what):
		if what[0] is self.CHANGED_SPECIFIC and self.delay >= 0 and what[1] == iPlayableService.evStart:
			self.showclock = 0
			if self.loop != -1:
				self.loop = self.delay
			service = self.source.serviceref
			if service:
				if 'Nozero' in self.type:
					self.num = '%d' % service.getChannelNum()
				else:
					self.num = '%04d' % service.getChannelNum()
			else:
				self.num = None
			Converter.changed(self, what)
		elif what[0] is self.CHANGED_POLL:
			Converter.changed(self, what)
