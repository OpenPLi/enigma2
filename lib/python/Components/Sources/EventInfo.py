from Components.PerServiceDisplay import PerServiceBase
from Components.Element import cached
from enigma import iPlayableService, iServiceInformation, eServiceReference, eEPGCache, eTimer
from Source import Source
from time import time

class EventInfo(PerServiceBase, Source, object):
	NOW = 0
	NEXT = 1

	def __init__(self, navcore, now_or_next):
		Source.__init__(self)
		self.epgTimer = eTimer()
		self.epgTimer.callback.append(self.epgTimerCheck)
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.gotEvent,
				iPlayableService.evUpdatedEventInfo: self.gotEvent,
				iPlayableService.evEnd: self.gotEvent
			}, with_event=True)
		self.now_or_next = now_or_next
		self.epgQuery = eEPGCache.getInstance().lookupEventTime
		self.NextStartTime = 0

	@cached
	def getEvent(self):
		service = self.navcore.getCurrentService()
		info = service and service.info()
		ret = None
		if info:
			refstr = info.getInfoString(iServiceInformation.sServiceref)
			ret = self.epgQuery(eServiceReference(refstr), -1, self.now_or_next and 1 or 0)

		if not ret or ret.getEventName() == "":
			ret = info and info.getEvent(self.now_or_next)

		now = int(time())
		if ret :
			start_time = ret.getBeginTime()
			duration = ret.getDuration()
			if self.now_or_next == 0:
				self.NextStartTime = start_time + duration
			elif self.now_or_next == 1:
				self.NextStartTime = start_time
			if self.NextStartTime > now :
				self.epgTimer.startLongTimer(self.NextStartTime - now + 8)
		return ret

	event = property(getEvent)

	def epgTimerCheck(self):
		now = int(time())
		if now > self.NextStartTime + 1:
			self.epgTimer.stop()
			self.changed((self.CHANGED_ALL,))

	def gotEvent(self, what):
		self.epgTimer.stop()
		if what == iPlayableService.evEnd:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))

	def destroy(self):
		PerServiceBase.destroy(self)
		Source.destroy(self)
