# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference
from Components.Element import cached
from Tools.General import GetServiceNameAndProvider, getServiceInfoValue, getRealServiceRefForIPTV, getServiceNum, isIPTV
import NavigationInstance


class ServiceNameEx(Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.parts = type.split(",")
		self.separator = self.parts[0]
		print("[ServiceNameEx] " + type)

	@cached
	def getText(self):
		service = self.source.service
		if not service:
			service = NavigationInstance.instance and NavigationInstance.instance.getCurrentService() or None
		isRef = False
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
			refps = NavigationInstance.instance and NavigationInstance.instance.getCurrentlyPlayingServiceReference() or None
		else: # reference
			info = service and self.source.info
			ref = getRealServiceRefForIPTV(service)
			isRef = True
			refps = None
		if not info:
			return ""
			
		nametext, provider = GetServiceNameAndProvider(1, ref, refps, info)

		if isIPTV(ref):
			ref_str = ref.toString()
		else:
			ref_str = getServiceInfoValue(2, info, iServiceInformation.sServiceref, ref, refps)

		from Screens.InfoBar import InfoBar
		channelSelectionServicelist = InfoBar.instance and InfoBar.instance.servicelist
		channelnum = ''
		orbitalpos = ''
		ref = ref or eServiceReference(getServiceInfoValue(2,info,iServiceInformation.sServiceref,ref,refps))
		if channelSelectionServicelist and channelSelectionServicelist.inBouquet():
			myRoot = channelSelectionServicelist.getRoot()
			channelnum = getServiceNum(ref, myRoot)

		if isRef:
			tp_data = info.getInfoObject(ref, iServiceInformation.sTransponderData)
		else:
			tp_data = info.getInfoObject(iServiceInformation.sTransponderData)
		if tp_data is not None:
			try:
				position = tp_data["orbital_position"]
				if position > 1800: # west
					orbitalpos = "%.1f " %(float(3600 - position)/10) + _("W")
				else:
					orbitalpos = "%.1f " %(float(position)/10) + _("E")
			except:
				pass
		res_str = ""
		for x in self.parts[1:]:
			print("[ServiceNameEx] Processing " + x)
			if x == "NUMBER" and channelnum != '':
				res_str = self.appendToStringWithSeparator(res_str, channelnum)
			if x == "NAME" and nametext != '':
				res_str = self.appendToStringWithSeparator(res_str, nametext)
			if x == "ORBPOS" and orbitalpos != '':
				res_str = self.appendToStringWithSeparator(res_str, orbitalpos)
			if x == "PROVIDER" and provider != '':
				res_str = self.appendToStringWithSeparator(res_str, provider)
			if x == "REFERENCE" and ref_str != '':
				res_str = self.appendToStringWithSeparator(res_str, ref_str)
		print("[ServiceNameEx] return " + res_str)
		return res_str

	text = property(getText)

	def appendToStringWithSeparator(self, str, part):
		if str == "":
			str = part
		else:
			str = str + "  " + self.separator + "  " + part
		return str

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart, ):
			Converter.changed(self, what)