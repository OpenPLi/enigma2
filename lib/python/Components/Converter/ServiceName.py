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

		self.parts = [(arg.strip() if i else arg) for i, arg in enumerate(type.split(","))]
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
		info = None
		ref = service
		if isinstance(service, eServiceReference):
			info = self.source.info
		elif isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else: # reference
			info = service and self.source.info

		if not info:
			return ""
		if self.type == self.NAME:
			return self.getName(ref, info)
		elif self.type == self.PROVIDER:
			return self.getProvider(ref, info)
		elif self.type == self.REFERENCE or self.type == self.EDITREFERENCE and hasattr(self.source, "editmode") and self.source.editmode:
			if not ref:
				if self.source.info:
					sref = hasattr(self.source, "serviceref") and self.source.serviceref
					nref = sref and resolveAlternate(sref)
					if nref:
						sref = nref
					return sref and sref.toString()
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				return refstr
			nref = resolveAlternate(ref)
			if nref:
				ref = nref
			return ref.toString()
		elif self.type == self.NUMBER:
			return self.getNumber()
		elif self.type == self.STREAM_URL:
			srpart = "//%s:%s/" % (config.misc.softcam_streamrelay_url.getHTML(), config.misc.softcam_streamrelay_port.value)
			path = ""
			if not ref:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				path = refstr and refstr.split(":")[10].replace("%3a", ":")
			else:
				path = ref.getPath()
			return "" if path.startswith("//") and path.find(srpart) > -1 and "://" not in path else path
		elif self.type == self.FORMAT_STRING:
			name = self.getName(ref, info)
			num = self.getNumber() or ""
			orbpos, tp_data = self.getOrbitalPos(ref, info)
			provider = self.getProvider(ref, info)
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
		sref = hasattr(self.source, "serviceref") and self.source.serviceref
		name = (ref and info.getName(ref)) or (sref and (self.source.info and self.source.info.getName(sref)) or sref.getName())
		if not name:
			if not ref:
				name = info.getName()

		return name.replace('\xc2\x86', '').replace('\xc2\x87', '').replace('_', ' ')
	
	def getNumber(self):
		numservice = hasattr(self.source, "serviceref") and self.source.serviceref
		cnannelNumInt = numservice and numservice.getChannelNum() or 0
		channelnum = str(cnannelNumInt) if cnannelNumInt else ""
		return channelnum

	def getProvider(self, ref, info):
		sref = hasattr(self.source, "serviceref") and self.source.serviceref
		prov = ((ref and hasattr(ref, "getProvider") and ref.getProvider()) or (ref and info.getInfoString(ref, iServiceInformation.sProvider))) or (sref and ref and (self.source.info and self.source.info.getInfoString(sref, iServiceInformation.sProvider)) or (hasattr(sref, "getProvider") and sref.getProvider()))
		if not prov:
			if not ref:
				prov = info.getInfoString(iServiceInformation.sProvider)
			else:
				prov = ""
		return prov

	def getOrbitalPos(self, ref, info):
		orbitalpos = ""
		tp_data = None
		sref = hasattr(self.source, "serviceref") and self.source.serviceref
		if ref:
			tp_data = info.getInfoObject(ref, iServiceInformation.sTransponderData)
		elif not self.source.info:
			tp_data = info.getInfoObject(iServiceInformation.sTransponderData)
		else:
			tp_data = sref and self.source.info.getInfoObject(sref, iServiceInformation.sTransponderData)
			

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
