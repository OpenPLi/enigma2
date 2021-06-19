from enigma import iPlayableService, eDVBResourceManager, eDVBSatelliteEquipmentControl
from Source import Source
from Components.PerServiceDisplay import PerServiceBase
from Components.NimManager import nimmanager
from Components.config import config


class FrontendInfo(Source, PerServiceBase):
	def __init__(self, service_source=None, frontend_source=None, navcore=None):
		self.navcore = None
		Source.__init__(self)
		if navcore:
			PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evTunedIn: self.updateFrontendData,
				iPlayableService.evEnd: self.serviceEnd
			})
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			res_mgr.frontendUseMaskChanged.get().append(self.updateTunerMask)
		self.service_source = service_source
		self.frontend_source = frontend_source
		self.tuner_mask = 0
		sec = eDVBSatelliteEquipmentControl.getInstance()
		if sec:
			sec.slotRotorSatPosChanged.get().append(self.updateSlotRotorSatPosition)
		self.updateFrontendData()

	def serviceEnd(self):
		self.slot_number = self.frontend_type = None
		self.changed((self.CHANGED_CLEAR, ))

	def updateFrontendData(self):
		data = self.getFrontendData()
		if not data:
			self.slot_number = self.frontend_type = None
		else:
			self.slot_number = data.get("tuner_number")
			self.frontend_type = data.get("tuner_type")
		self.changed((self.CHANGED_ALL, ))

	def updateTunerMask(self, mask):
		self.tuner_mask = mask
		self.changed((self.CHANGED_ALL, ))

	def getFrontendData(self):
		if self.frontend_source:
			frontend = self.frontend_source()
			dict = {}
			if frontend:
				frontend.getFrontendData(dict)
			return dict
		elif self.service_source:
			service = self.navcore and self.service_source()
			feinfo = service and service.frontendInfo()
			return feinfo and feinfo.getFrontendData()
		elif self.navcore:
			service = self.navcore.getCurrentService()
			feinfo = service and service.frontendInfo()
			return feinfo and feinfo.getFrontendData()
		else:
			return None

	def updateSlotRotorSatPosition(self, slot, orbital_position):
		for nim in nimmanager.nim_slots:
			if nim.slot == slot:
				nim.config.lastsatrotorposition.value = str(orbital_position)
				config.misc.lastrotorposition.value = orbital_position
				nim.config.lastsatrotorposition.save()
				config.misc.lastrotorposition.save()
				self.changed((self.CHANGED_ALL, ))
				break

	def destroy(self):
		if not self.frontend_source and not self.service_source:
			PerServiceBase.destroy(self)
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			res_mgr.frontendUseMaskChanged.get().remove(self.updateTunerMask)
		sec = eDVBSatelliteEquipmentControl.getInstance()
		if sec:
			sec.slotRotorSatPosChanged.get().remove(self.updateSlotRotorSatPosition)
		Source.destroy(self)
