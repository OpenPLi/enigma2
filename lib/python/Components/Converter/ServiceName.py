# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference
from ServiceReference import resolveAlternate
from Components.Element import cached
from Tools.General import getServiceNum


class ServiceName(Converter):
	NAME = 0
	PROVIDER = 1
	REFERENCE = 2
	EDITREFERENCE = 3
	NUMBER = 4
	FORMAT_STRING = 5

	def __init__(self, type):
		Converter.__init__(self, type)

		self.parts = type.split(",")
		if len(self.parts) > 1:
			self.type = self.FORMAT_STRING
			self.separator = self.parts[0]
		else:
			if type == "Provider":
				self.type = self.PROVIDER
			elif type == "Reference":
				self.type = self.REFERENCE
			elif type == "EditReference":
				self.type = self.EDITREFERENCE
			elif type == "Number":
				self.type = self.NUMBER
			else:
				self.type = self.NAME

	@cached
	def getText(self):
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else: # reference
			info = service and self.source.info
			ref = service
		if not info:
			return ""
		if self.type == self.NAME:
			return self.getName(ref, info)
		elif self.type == self.PROVIDER:
			return self.getProvider(ref, info)
		elif self.type == self.REFERENCE or self.type == self.EDITREFERENCE and hasattr(self.source, "editmode") and self.source.editmode:
			if not ref:
				return info.getInfoString(iServiceInformation.sServiceref)
			nref = resolveAlternate(ref)
			if nref:
				ref = nref
			return ref.toString()
		elif self.type == self.NUMBER:
			return self.getNumber(ref, info)
		elif self.type == self.FORMAT_STRING:
			name = self.getName(ref, info)
			num = self.getNumber(ref, info)
			provider = self.getProvider(ref, info)
			orbpos = self.getOrbitalPos(ref, info)
			res_str = ""
			for x in self.parts[1:]:
				if x == "NUMBER" and num:
					res_str = self.appendToStringWithSeparator(res_str, num)
				if x == "NAME" and name:
					res_str = self.appendToStringWithSeparator(res_str, name)
				if x == "ORBPOS" and orbpos:
					res_str = self.appendToStringWithSeparator(res_str, orbpos)
				if x == "PROVIDER" and provider is not None and provider:
					res_str = self.appendToStringWithSeparator(res_str, provider)
			return res_str



	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)

	def getName(self, ref, info):
		name = ref and info.getName(ref)
		if name is None:
			name = info.getName()
		return name.replace('\xc2\x86', '').replace('\xc2\x87', '').replace('_', ' ')
	
	def getNumber(self, ref, info):
		from Screens.InfoBar import InfoBar
		channelSelectionServicelist = InfoBar.instance and InfoBar.instance.servicelist
		channelnum = ''
		ref = ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
		if channelSelectionServicelist and channelSelectionServicelist.inBouquet():
			myRoot = channelSelectionServicelist.getRoot()
			channelnum = getServiceNum(ref, myRoot)
		return channelnum
	
	def getProvider(self, ref, info):
		if ref:
			return info.getInfoString(ref, iServiceInformation.sProvider)
		return info.getInfoString(iServiceInformation.sProvider)
	
	def getOrbitalPos(self, ref, info):
		orbitalpos = ""
		if ref:
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
		return orbitalpos
