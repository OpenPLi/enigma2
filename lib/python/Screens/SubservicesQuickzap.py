from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from InfoBarGenerics import InfoBarShowHide, InfoBarMenu, InfoBarInstantRecord, InfoBarTimeshift, InfoBarSeek, InfoBarTimeshiftState, InfoBarExtensions, InfoBarSubtitleSupport, InfoBarAudioSelection
from enigma import eServiceReference
from Components.ServiceEventTracker import InfoBarBase

class SubservicesQuickzap(InfoBarBase, InfoBarShowHide, InfoBarMenu, \
		InfoBarInstantRecord, InfoBarSeek, InfoBarTimeshift, \
		InfoBarTimeshiftState, InfoBarExtensions, InfoBarSubtitleSupport, \
		InfoBarAudioSelection, Screen):
	def __init__(self, session, subservices):
		Screen.__init__(self, session)
		self.setTitle(_("Subservices"))
		for x in InfoBarBase, InfoBarShowHide, InfoBarMenu, \
				InfoBarInstantRecord, InfoBarSeek, InfoBarTimeshift, \
				InfoBarTimeshiftState, InfoBarSubtitleSupport, \
				InfoBarExtensions, InfoBarAudioSelection:
			x.__init__(self)
		self.restoreService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.subservices = subservices
		self.n = None
		if self.subservices:
			self.n = len(self.subservices)
		self.__lastservice = self.currentlyPlayingSubservice = self.getSubserviceIndex(self.session.nav.getCurrentlyPlayingServiceReference())
		self["CurrentSubserviceNumber"] = Label("")
		self.currentSubserviceNumberLabel = self["CurrentSubserviceNumber"]
		self["actions"] = NumberActionMap( [ "InfobarSubserviceQuickzapActions", "NumberActions", "DirectionActions", "ColorActions" ],
			{
				"up": self.showSelection,
				"down": self.showSelection,
				"right": self.nextSubservice,
				"left": self.previousSubservice,
				"green": self.showSelection,
				"exit": self.quitQuestion,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal
			}, 0)
		self.onLayoutFinish.append(self.onLayoutFinished)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		self.session.nav.stopService()
		self.session.nav.playService(self.restoreService, checkParentalControl=False, adjust=False)

	def onLayoutFinished(self):
		cur_num = self.currentlyPlayingSubservice
		if cur_num is not None or cur_num != -1:
			self.currentSubserviceNumberLabel.setText(str(cur_num + 1))

	def nextSubservice(self):
		if self.n:
			if self.currentlyPlayingSubservice >= self.n - 1:
				self.playSubservice(0)
			else:
				self.playSubservice(self.currentlyPlayingSubservice + 1)

	def previousSubservice(self):
		if self.n:
			if self.currentlyPlayingSubservice > self.n:
				self.currentlyPlayingSubservice = self.n
			if self.currentlyPlayingSubservice == 0:
				self.playSubservice(self.n - 1)
			else:
				self.playSubservice(self.currentlyPlayingSubservice - 1)

	def getSubserviceIndex(self, service):
		if self.n is None or service is None:
			return -1
		for x in range(self.n):
			try:
				if service == eServiceReference(self.subservices[x][0]):
					return x
			except:
				pass
		return -1

	def keyNumberGlobal(self, number):
		if number == 0:
			self.playSubservice(self.__lastservice)
		elif self.n is not None and number <= self.n:
			self.playSubservice(number - 1)

	def showSelection(self):
		tlist = []
		n = self.n or 0
		if n:
			idx = 0
			while idx < n:
				i = self.subservices[idx]
				tlist.append((i[1], idx))
				idx += 1
			keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "green", "yellow"] + [""] * n
			self.session.openWithCallback(self.subserviceSelected, ChoiceBox, title=_("Please select a subservice..."), list=tlist, selection=self.currentlyPlayingSubservice, keys=keys, windowTitle=_("Subservices"))

	def subserviceSelected(self, service):
		if service:
			self.playSubservice(service[1])

	def keyOK(self):
		self.doShow()

	def quitQuestion(self):
		self.session.openWithCallback(self.quit, MessageBox, _("Really exit the subservices quickzap?"))

	def quit(self, answer):
		if answer:
			self.close()

	def playSubservice(self, number=0):
		try:
			newservice = eServiceReference(self.subservices[number][0])
		except:
			newservice = None
		if newservice and newservice.valid():
			self.__lastservice = self.currentlyPlayingSubservice
			self.session.nav.stopService()
			self.session.nav.playService(newservice, checkParentalControl=False, adjust=False)
			self.currentlyPlayingSubservice = number
			self.currentSubserviceNumberLabel.setText(str(number + 1))
			self.doShow()
