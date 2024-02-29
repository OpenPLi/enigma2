# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference
from ServiceReference import resolveAlternate
from Components.config import config
from Components.Element import cached
from Tools.Transponder import ConvertToHumanReadable


class ServiceName(Converter):
	NAME = 0
	PROVIDER = 1
	REFERENCE = 2
	EDITREFERENCE = 3
	NUMBER = 4
	STREAM_URL = 5
	FORMAT_STRING = 6

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
			elif type == "StreamUrl":
				self.type = self.STREAM_URL
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
			numservice = self.source.serviceref
			return self.getNumber(numservice, info)
		elif self.type == self.STREAM_URL:
			srpart = "//%s:%s/" % (config.misc.softcam_streamrelay_url.getHTML(), config.misc.softcam_streamrelay_port.value)
			if not ref:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				path = refstr and eServiceReference(refstr).getPath()
				if not path.startswith("//") and path.find(srpart) == -1:
					return path
				else:
					return ""
			path = ref.getPath()
			return "" if path.startswith("//") and path.find(srpart) == -1 else path
		elif self.type == self.FORMAT_STRING:
			name = self.getName(ref, info)
			numservice = hasattr(self.source, "serviceref") and self.source.serviceref
			num = numservice and self.getNumber(numservice, info) or ""
			orbpos, tp_data = self.getOrbitalPos(ref, info)
			provider = self.getProvider(ref, info, tp_data)
			tuner_system = ref and info and self.getServiceSystem(ref, info, tp_data)
			res_str = ""
			for x in self.parts[1:]:
				if x == "NUMBER" and num:
					res_str = self.appendToStringWithSeparator(res_str, num)
				if x == "NAME" and name:
					res_str = self.appendToStringWithSeparator(res_str, name)
				if x == "ORBPOS" and orbpos:
					res_str = self.appendToStringWithSeparator(res_str, orbpos)
				if x == "PROVIDER" and provider:
					res_str = self.appendToStringWithSeparator(res_str, provider)
				if x == "TUNERSYSTEM" and tuner_system:
					res_str = self.appendToStringWithSeparator(res_str, tuner_system)
			return res_str



	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart, ):
			Converter.changed(self, what)

	def getName(self, ref, info):
		name = ref and info.getName(ref)
		if name is None:
			name = info.getName()
		return name.replace('\xc2\x86', '').replace('\xc2\x87', '').replace('_', ' ')
	
	def getNumber(self, ref, info):
		if not ref:
			ref = eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
		num = ref and ref.getChannelNum() or None
		if num is None:
			num = '---'
		else:
			num = str(num)
		return num

	def getProvider(self, ref, info, tp_data=None):
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
					orbitalpos = "%.1f " %(float(3600 - position)/10) + _("°W")
				else:
					orbitalpos = "%.1f " %(float(position)/10) + _("°E")
			except:
				pass
		return orbitalpos, tp_data
	
	def getServiceSystem(self, ref, info, feraw):
		if ref:
			sref = info.getInfoObject(ref, iServiceInformation.sServiceref)
		else:
			sref = info.getInfoObject(iServiceInformation.sServiceref)
		
		if not sref:
			sref = ref.toString()
			
		if sref and "%3a//" in sref:
			return "IPTV"
			
		fedata = ConvertToHumanReadable(feraw)

		return fedata.get("system") or ""
