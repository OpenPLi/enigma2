from Screens.MessageBox import MessageBox
from enigma import eStreamServer


class ServiceStopScreen:
	def __init__(self):
		try:
			self.session
		except:
			print("[ServiceStopScreen] ERROR: no self.session set")
		self.oldref = self.oldAlternativeref = None
		self.slot_number = -1
		self.onClose.append(self.__onClose)

	def pipAvailable(self):
		# pip isn't available in every state of e2
		try:
			self.session.pipshown
			pipavailable = True
		except:
			pipavailable = False
		return pipavailable

	def serviceSlotNumber(self):
		slot_number = -1
		if self.session.nav.getCurrentlyPlayingServiceOrGroup():
			service = self.session.nav.getCurrentService()
			feinfo = service and service.frontendInfo()
			if feinfo:
				frontendData = hasattr(feinfo, 'getFrontendData') and feinfo.getFrontendData()
				if frontendData:
					slot_number = frontendData.get("tuner_number", -1)
		return slot_number

	def stopService(self):
		if not self.oldref:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				refstr = ref.toString()
				if "%3a//" not in refstr and not refstr.rsplit(":", 1)[1].startswith("/"):
					self.slot_number = self.serviceSlotNumber()
					self.oldref = ref
					self.oldAlternativeref = self.session.nav.getCurrentlyPlayingServiceReference()
					self.session.nav.stopService()
			if self.pipAvailable():
				if self.session.pipshown: # try to disable pip
					if hasattr(self.session, 'infobar'):
						if self.session.infobar.servicelist and self.session.infobar.servicelist.dopipzap:
							self.session.infobar.servicelist.togglePipzap()
					if hasattr(self.session, 'pip'):
						del self.session.pip
					self.session.pipshown = False
			if self.session.nav.getClientsStreaming():
				eStreamServer.getInstance().stopStream()

	def __onClose(self):
		if self.oldref:
			self.session.nav.playService(self.oldref)

	def restoreService(self, msg=_("Zap back to previously tuned service?")):
		if self.oldref:
			self.session.openWithCallback(self.restartPrevService, MessageBox, msg, MessageBox.TYPE_YESNO)
		else:
			self.restartPrevService(False)

	def restartPrevService(self, yesno=True, close=True):
		if not yesno:
			self.oldref = self.oldAlternativeref = None
			self.slot_number = -1
		if close:
			self.close()
		else:
			self.__onClose()
			self.oldref = self.oldAlternativeref = None
			self.slot_number = -1
