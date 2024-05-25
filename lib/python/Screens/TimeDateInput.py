from Screens.Setup import Setup
from Components.config import ConfigClock, ConfigDateTime
import time
import datetime


class TimeDateInput(Setup):
	def __init__(self, session, config_time=None, config_date=None):
		self.createConfig(config_date, config_time)
		Setup.__init__(self, session, None)
		self.setTitle(_("Date/time input"))

	def createConfig(self, conf_date, conf_time):
		self.save_mask = 0
		if conf_time:
			self.save_mask |= 1
		else:
			conf_time = ConfigClock(default=time.time()),
		if conf_date:
			self.save_mask |= 2
		else:
			conf_date = ConfigDateTime(default=time.time(), formatstring=_("%d.%B %Y"), increment=86400)
		self.timeinput_date = conf_date
		self.timeinput_time = conf_time

	def createSetup(self):
		self.list = [
			(_("Date"), self.timeinput_date),
			(_("Time"), self.timeinput_time)
		]
		self["config"].list = self.list

	def keyPageDown(self):
		sel = self["config"].getCurrent()
		if sel and sel[1] == self.timeinput_time:
			self.timeinput_time.decrement()
			self["config"].invalidateCurrent()

	def keyPageUp(self):
		sel = self["config"].getCurrent()
		if sel and sel[1] == self.timeinput_time:
			self.timeinput_time.increment()
			self["config"].invalidateCurrent()

	def getTimestamp(self, date, mytime):
		d = time.localtime(date)
		dt = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(time.mktime(dt.timetuple()))

	def keySave(self):
		time = self.getTimestamp(self.timeinput_date.value, self.timeinput_time.value)
		if self.save_mask & 1:
			self.timeinput_time.save()
		if self.save_mask & 2:
			self.timeinput_date.save()
		self.close((True, time))

	def keyCancel(self):
		if self.save_mask & 1:
			self.timeinput_time.cancel()
		if self.save_mask & 2:
			self.timeinput_date.cancel()
		self.close((False,))
