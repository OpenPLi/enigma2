# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceCenter
from Components.Element import cached
from ServiceReference import resolveAlternate, ServiceReference
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
			ref = ref.toString().replace("%3a", ":")
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
					return "%s %s-%s %s %d MHz %s" % (transponderdata["system"], tsid, onid, transponderdata["channel"], transponderdata["frequency"] / 1000000 + 0.5, transponderdata["bandwidth"])
				elif "DVB-C" in transponderdata["system"]:
					return "%s %s-%s %d MHz %d %s %s" % (transponderdata["system"], tsid, onid, transponderdata["frequency"] / 1000 + 0.5, transponderdata["symbol_rate"] / 1000 + 0.5, transponderdata["fec_inner"],
						transponderdata["modulation"])
				elif "ATSC" in transponderdata["system"]:
					return "%s %s-%s %d MHz %s" % (transponderdata["system"], tsid, onid, transponderdata["frequency"] / 1000 + 0.5, transponderdata["modulation"])
				return "%s %s-%s %d %s %d %s %s %s" % (transponderdata["system"], tsid, onid, transponderdata["frequency"] / 1000 + 0.5, transponderdata["polarization_abbreviation"], transponderdata["symbol_rate"] / 1000 + 0.5,
					transponderdata["fec_inner"], transponderdata["modulation"], transponderdata["detailed_satpos" in self.type and "orbital_position" or "orb_pos"])
			except:
				return ""
		if "://" in ref:
			return _("Stream") + " " + ref.rsplit("://", 1)[1].split("/")[0]
		return ""

	text = property(getText)

	@cached
	def getBoolean(self):
		# finds "DVB-S", "DVB-S2", "DVB-T", "DVB-T2", "DVB-C", "ATSC", "Stream"  or combinations of these,
		# e.g. <convert type="TransponderInfo">DVB-S;DVB-S2</convert> to return True for either.
		s = self.getText()
		# get the first group of characters, and, convert to lower case
		s = s and s.strip().split() and s.strip().split()[0].lower()
		# only populated entries, and, convert to lower case
		t = self.type and [x.lower() for x in self.type if x]
		return bool(s and t and s in t)
	
	boolean = property(getBoolean)

	def rootBouquet(self):
		servicelist = Screens.InfoBar.InfoBar.instance.servicelist
		epg_bouquet = servicelist and servicelist.getRoot()
		if ServiceReference(epg_bouquet).getServiceName():
			return False
		return True

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)
