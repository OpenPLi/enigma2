# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceCenter
from Components.Element import cached
from ServiceReference import resolveAlternate,  ServiceReference
from Tools.Transponder import ConvertToHumanReadable
import Screens.InfoBar

class TransponderInfo(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type.split(";")

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
		if ref:
			nref = resolveAlternate(ref)
			if nref:
				ref = nref
				info = eServiceCenter.getInstance().info(ref)
			transponderraw = info.getInfoObject(ref, iServiceInformation.sTransponderData)
			ref = ref.toString().replace("%3a",":")
		else:
			transponderraw = info.getInfoObject(iServiceInformation.sTransponderData)
			ref = info.getInfoString(iServiceInformation.sServiceref)
		if transponderraw:
			transponderdata = ConvertToHumanReadable(transponderraw)
			# retreive onid and tsid from service reference
			[onid, tsid] = [int(x, 16) for x in ref.split(':')[4:6]]
			if not transponderdata["system"]:
				transponderdata["system"] = transponderraw.get("tuner_type", "None")
			try:
				if "DVB-T" in transponderdata["system"]:
					return "%s %s-%s %s %d MHz %s" % (transponderdata["system"], tsid, onid, transponderdata["channel"], transponderdata["frequency"]/1000000 + 0.5 , transponderdata["bandwidth"])
				elif "DVB-C" in transponderdata["system"]:
					return "%s %s-%s %d MHz %d %s %s" % (transponderdata["system"], tsid, onid, transponderdata["frequency"]/1000 + 0.5, transponderdata["symbol_rate"]/1000 + 0.5, transponderdata["fec_inner"], \
						transponderdata["modulation"])
				elif "ATSC" in transponderdata["system"]:
					return "%s %s-%s %d MHz %s" % (transponderdata["system"], tsid, onid, transponderdata["frequency"]/1000 + 0.5, transponderdata["modulation"])
				return "%s %s-%s %d %s %d %s %s %s" % (transponderdata["system"], tsid, onid, transponderdata["frequency"]/1000 + 0.5, transponderdata["polarization_abbreviation"], transponderdata["symbol_rate"]/1000 + 0.5, \
					transponderdata["fec_inner"], transponderdata["modulation"], transponderdata["detailed_satpos" in self.type and "orbital_position" or "orb_pos"])
			except:
				return ""
		if "://" in ref:
			return _("Stream") + " " + ref.rsplit("://", 1)[1].split("/")[0]
		return ""

	text = property(getText)

	def rootBouquet(self):
		servicelist = Screens.InfoBar.InfoBar.instance.servicelist
		epg_bouquet = servicelist and servicelist.getRoot()
		if ServiceReference(epg_bouquet).getServiceName():
			return False
		return True

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
