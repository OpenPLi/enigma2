# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference
from ServiceReference import resolveAlternate
from Components.Element import cached
from API import session
from Tools.General import GetServiceNameAndProvider, getServiceInfoValue, cleanServiceRefFull, getRealServiceRefForIPTV, getServiceNum, isIPTV


class ServiceName(Converter):
	NAME = 0
	PROVIDER = 1
	REFERENCE = 2
	EDITREFERENCE = 3
	NUMBER = 4
	NUMBER_NAME_PROVIDER = 5
	NUMBER_NAME = 6

	def __init__(self, type):
		Converter.__init__(self, type)

		if type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "EditReference":
			self.type = self.EDITREFERENCE
		elif type == "Number":
			self.type = self.NUMBER
		elif type == "ServiceNumberAndNameAndProvider":
			self.type = self.NUMBER_NAME_PROVIDER
		elif type == "ServiceNumberAndName":
			self.type = self.NUMBER_NAME
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
			refps = session and session.nav.getCurrentlyPlayingServiceReference() or None
		else: # reference
			info = service and self.source.info
			ref = getRealServiceRefForIPTV(service)
			refps = None
		if not info:
			#print("No Info::")
			return ""
			
		nametext, provider = GetServiceNameAndProvider(1, ref, refps, info)
		#print("NameProv::" + nametext)
		if self.type == self.NAME:
			return nametext
		elif self.type == self.PROVIDER:
			return provider
		elif self.type == self.REFERENCE or self.type == self.EDITREFERENCE and hasattr(self.source, "editmode") and self.source.editmode:
			if isIPTV(ref):
				return ref.toString()
			else:
				return getServiceInfoValue(self.type, info, iServiceInformation.sServiceref, ref, refps)
		#elif self.type == self.NUMBER:
		#	if not ref:
		#		ref = eServiceReference(info.getInfoString(iServiceInformation.sServiceref))
		#	num = ref and ref.getChannelNum() or None
		#	if num is None:
		#		num = '---'
		#	else:
		#		num = str(num)
		#	return num
		elif self.type == self.NUMBER_NAME_PROVIDER or self.type == self.NUMBER or self.type == self.NUMBER_NAME:
			from Screens.InfoBar import InfoBar
			channelSelectionServicelist = InfoBar.instance and InfoBar.instance.servicelist
			channelnum = ''
			orbitalpos = ''
			ref = ref or eServiceReference(getServiceInfoValue(self.type,info,iServiceInformation.sServiceref,ref,refps))
			if channelSelectionServicelist and channelSelectionServicelist.inBouquet():
				myRoot = channelSelectionServicelist.getRoot()
				channelnum = getServiceNum(ref, myRoot)

			if self.type == self.NUMBER_NAME_PROVIDER or self.type == self.NUMBER_NAME:
				if channelnum != '':
					resulttext = "%s  •  %s" % (channelnum, nametext)
				else:
					resulttext = nametext
			elif self.type == self.NUMBER:
				if channelnum != '':
					resulttext = "%s" % (channelnum)
				else:
					resulttext = "---"
			if self.type == self.NUMBER_NAME_PROVIDER:
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
				if orbitalpos != "":
					resulttext = "%s  •  %s" % (resulttext, orbitalpos) 
				if provider != "":
					resulttext = "%s  •  %s" % (resulttext, provider) 
				print("ResText: " + resulttext) 
			return resulttext

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)