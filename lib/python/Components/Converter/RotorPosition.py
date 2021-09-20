# -*- coding: utf-8 -*-
from Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import orbpos
from Components.NimManager import nimmanager
from Components.SystemInfo import SystemInfo
from enigma import eDVBSatelliteEquipmentControl


class RotorPosition(Converter):
	DEFAULT = 0
	WITH_TEXT = 1
	TUNER_NAME = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		self.LastRotorPos = config.misc.lastrotorposition.value
		config.misc.lastrotorposition.addNotifier(self.forceChanged, initial_call=False)
		config.misc.showrotorposition.addNotifier(self.show_hide, initial_call=False)
		self.sec = eDVBSatelliteEquipmentControl.getInstance()

	@cached
	def getText(self):
		value = config.misc.showrotorposition.value
		if SystemInfo["isRotorTuner"] and value != "no":
			if value.isdigit():
				nim_text = nimmanager.rotorLastPositionForNim(int(value), number=False)
				if nim_text == _("undefined"):
					def frontendRotorPosition(slot):
						for x in nimmanager.nim_slots:
							if x.slot == slot:
								rotorposition = x.config.lastsatrotorposition.value
								if rotorposition.isdigit():
									return orbpos(int(rotorposition))
						return ""
					saved_text = frontendRotorPosition(int(value))
					if saved_text:
						nim_text = saved_text
				return "%s:%s" % ("\c0000f0f0" + chr(ord("A") + int(value)), "\c00f0f0f0" + nim_text)
			elif value == "all":
				all_text = ""
				for x in nimmanager.nim_slots:
					print x.slot
					nim_text = nimmanager.rotorLastPositionForNim(x.slot, number=False)
					if nim_text != _("rotor is not used"):
						if nim_text == _("undefined"):
							rotorposition = x.config.lastsatrotorposition.value
							if rotorposition.isdigit():
								nim_text = orbpos(int(rotorposition))
						all_text += "%s:%s " % ("\c0000f0f0" + chr(ord("A") + x.slot), "\c00f0f0f0" + nim_text)
				return all_text
			self.LastRotorPos = config.misc.lastrotorposition.value
			(rotor, tuner) = self.isMotorizedTuner()
			if rotor:
				self.actualizeCfgLastRotorPosition()
				if value == "withtext":
					return _("Rotor: ") + orbpos(config.misc.lastrotorposition.value)
				if value == "tunername":
					active_tuner = self.getActiveTuner()
					if tuner != active_tuner:
						return "%s:%s" % ("\c0000f0f0" + chr(ord("A") + tuner), "\c00f0f0f0" + orbpos(config.misc.lastrotorposition.value))
					return ""
				return orbpos(config.misc.lastrotorposition.value)
		return ""

	@cached
	def getBool(self):
		return bool(self.getText())

	text = property(getText)

	boolean = property(getBool)

	def isMotorizedTuner(self):
		for x in nimmanager.nim_slots:
			if nimmanager.getRotorSatListForNim(x.slot, only_first=True):
				return (True, x.slot)
		return (False, None)

	def actualizeCfgLastRotorPosition(self):
		if self.sec and self.sec.isRotorMoving():
			current_pos = self.sec and self.sec.getTargetOrbitalPosition() or -1
			if current_pos != -1 and current_pos != config.misc.lastrotorposition.value:
				self.LastRotorPos = config.misc.lastrotorposition.value = current_pos
				config.misc.lastrotorposition.save()

	def getActiveTuner(self):
		if self.sec and not self.sec.isRotorMoving():
			service = self.source.service
			feinfo = service and service.frontendInfo()
			tuner = feinfo and feinfo.getAll(True)
			if tuner:
				num = tuner.get("tuner_number")
				orb_pos = tuner.get("orbital_position")
				if isinstance(num, int) and orb_pos:
					satList = nimmanager.getRotorSatListForNim(num)
					for sat in satList:
						if sat[0] == orb_pos:
							return num
		return ""

	def forceChanged(self, configElement=None):
		if self.LastRotorPos != config.misc.lastrotorposition.value:
			Converter.changed(self, (self.CHANGED_ALL,))

	def show_hide(self, configElement=None):
		Converter.changed(self, (self.CHANGED_ALL,))
