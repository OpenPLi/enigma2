from time import time

from Components.PerServiceDisplay import PerServiceBase
from Components.Element import cached
from enigma import iPlayableService, iServiceInformation, eServiceReference, eEPGCache, eServiceCenter
from Components.Sources.Source import Source


# Fake eServiceEvent to fill Event_Now and Event_Next in Infobar for Streams
class pServiceEvent:
	NOW = 0
	NEXT = 1

	def __init__(self, info, now_or_next, service):
		self.now_or_next = now_or_next

		self.m_EventNameNow = ""
		self.m_EventNameNext = ""
		self.m_ShortDescriptionNow = ""
		self.m_ShortDescriptionNext = ""
		self.m_ExtendedDescriptionNow = ""
		self.m_ExtendedDescriptionNext = ""
		self.m_Duration = 0
		self.m_Begin = time()
		isPtr = not isinstance(service, eServiceReference)
		sTagTitle = info.getInfoString(iServiceInformation.sTagTitle) if isPtr else info.getInfoString(service, iServiceInformation.sTagTitle)
		if sTagTitle:
			sTagTitleList = sTagTitle.split(" - ")
			element1 = sTagTitleList[0] if len(sTagTitleList) >= 1 else ""
			element2 = sTagTitleList[1] if len(sTagTitleList) >= 2 else ""
			element3 = sTagTitleList[2] if len(sTagTitleList) >= 3 else ""
			if element3 == "":
				self.m_EventNameNow = element1
				self.m_EventNameNext = element2
			if element3 != "":
				self.m_EventNameNow = element1 + " - " + element2
				self.m_EventNameNext = element3

		sTagGenre = info.getInfoString(iServiceInformation.sTagGenre) if isPtr else info.getInfoString(service, iServiceInformation.sTagGenre)
		if sTagGenre:
			element4 = sTagGenre
			self.m_ShortDescriptionNow = element4

		sTagOrganization = info.getInfoString(iServiceInformation.sTagOrganization) if isPtr else info.getInfoString(service, iServiceInformation.sTagOrganization)
		if sTagOrganization:
			element5 = sTagOrganization
			self.m_ExtendedDescriptionNow = element5

		sTagLocation = info.getInfoString(iServiceInformation.sTagLocation) if isPtr else info.getInfoString(service, iServiceInformation.sTagLocation)
		if sTagLocation:
			element6 = sTagLocation
			self.m_ExtendedDescriptionNow += "\n\n" + element6

		seek = service and isPtr and service.seek()
		if seek:
			length = seek.getLength()
			if length[0] == 0:
				self.m_Duration = length[1] / 90000
			position = seek.getPlayPosition()
			if position[0] == 0:
				self.m_Begin = time() - position[1] / 90000

	def getEventName(self):
		return self.m_EventNameNow if self.now_or_next == self.NOW else self.m_EventNameNext

	def getShortDescription(self):
		return self.m_ShortDescriptionNow if self.now_or_next == self.NOW else self.m_ShortDescriptionNext

	def getExtendedDescription(self):
		return self.m_ExtendedDescriptionNow if self.now_or_next == self.NOW else self.m_ExtendedDescriptionNext

	def getBeginTime(self):
		return self.m_Begin if self.now_or_next == self.NOW else 0

	def getEndTime(self):
		return 0

	def getDuration(self):
		return self.m_Duration if self.now_or_next == self.NOW else 0

	def getEventId(self):
		return 0

	def getBeginTimeString(self):
		return ""

	def getPdcPil(self):
		return ""

	def getGenreData(self):
		return None

	def getParentalData(self):
		return None

	def getRunningStatus(self):
		return 0

	def getSeriesCrid(self):
		return ""

	def getEpisodeCrid(self):
		return ""

	def getComponentData(self):
		return 0

	def getNumOfLinkageServices(self):
		return 0

	def getLinkageService(self):
		return 0


class EventInfo(PerServiceBase, Source):
	NOW = 0
	NEXT = 1

	def __init__(self, navcore, now_or_next):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.gotEvent,
				iPlayableService.evUpdatedInfo: self.gotEvent,
				iPlayableService.evUpdatedEventInfo: self.gotEvent,
				iPlayableService.evEnd: self.gotEvent
			}, with_event=True)
		self.now_or_next = now_or_next
		self.epgQuery = eEPGCache.getInstance().lookupEventTime
		self.__service = None

	@cached
	def getEvent(self):
		isPtr = not isinstance(self.__service, eServiceReference)
		service = self.navcore.getCurrentService() if isPtr else self.__service
		if isPtr:
			info = service and service.info()
			ret = info and info.getEvent(self.now_or_next)
		else:
			info = eServiceCenter.getInstance().info(self.__service)
			ret = info and info.getEvent(self.__service, self.now_or_next)
		if info:
			if not ret or ret.getEventName() == "":
				refstr = info.getInfoString(iServiceInformation.sServiceref) if isPtr else self.__service.toString()
				ret = self.epgQuery(eServiceReference(refstr), -1, self.now_or_next and 1 or 0)
				if not ret and refstr.split(':')[0] in ['4097', '5001', '5002', '5003']:  # No EPG Try to get Meta
					ev = pServiceEvent(info, self.now_or_next, service)
					if ev.getEventName:
						return ev
		return ret

	event = property(getEvent)

	def gotEvent(self, what):
		if what == iPlayableService.evEnd:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))

	def updateSource(self, ref):
		if not ref:
			self.__service = None
			self.changed((self.CHANGED_CLEAR,))
			return
		self.__service = ref
		self.changed((self.CHANGED_ALL,))


	def destroy(self):
		PerServiceBase.destroy(self)
		Source.destroy(self)
