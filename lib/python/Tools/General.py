from enigma import iServiceInformation, eServiceReference, eServiceCenter

def GetServiceNameAndProvider(type, serviceRef, servicerefPs, info):
	name = _("N/A")
	provider = _("N/A")
	if not serviceRef and not servicerefPs:
		return name, provider
		
	if type == 1:
		name = serviceRef and info.getName(serviceRef)
		if name is None:
			name = info.getName()
	elif type == 8:
		name = serviceRef and serviceRef.getServiceName()
		
	nametext = name.replace('\xc2\x86', '').replace('\xc2\x87', '')
	provider = info and getServiceInfoValue(2, info, iServiceInformation.sProvider, serviceRef, None, type)
	if nametext.find("|") > -1:
		namesplitted = nametext.split("|")
		nametext = namesplitted[0]
		provider = namesplitted[1]
	return nametext, provider
		
def getServiceInfoValue(type, info, what, ref=None, refps=None, typeEx=0):
		#v = ref and info.getInfo(ref, what) or info.getInfo(what)
		if info and typeEx == 8:
			ret = info.getInfoString(what)
		elif ref:
			if what == iServiceInformation.sProvider:
				ret = info.getInfoString(ref, what) or "IPTV"
			else:
				ret = info.getInfoString(ref, what) or type == 2 and ref.toString()
		elif refps:
			ret = refps.toString()
		else:
			ret = info and info.getInfoString(what)
		#if v != iServiceInformation.resIsString:
		#	print "v=" + str(v)
		#	ret = "N/A" if not ref or self.type != self.REFERENCE else ref.toString()
		return ret

def cleanServiceRef(ref):
	splitted = ref.split(":")
	cleaned_ref = ":".join(splitted[:10])
	return cleaned_ref
	
def getCompareReference(ref):
	splitted = ref.split(":")
	compare_ref = "1:" + ":".join(splitted[1:10])
	return compare_ref
	
def cleanServiceRefFull(ref):
	if ref:
		service = ref
		service_ref_str = service.toString()
		if service_ref_str.find("127.0.0.1") > -1: #ICAM SkyDE channels
			service_ref_cleaned = service_ref_str.split("17999/")[1].split(":")[0].replace("%3a", ":")
			service = eServiceReference(service_ref_cleaned + ":")
		try:
			from Plugins.Extensions.IPTV.IPTVProcessor import idIPTV
		except:
			idIPTV = 0x13E9
		if service.type == idIPTV:
			type = "1:"
			if service_ref_str.find(".m3u8") > -1:
				type = "4097:"
			service_ref_cleaned = type + ":".join(service_ref_str.split(":")[1:12])
			service = eServiceReference(service_ref_cleaned)
		return service
	return ref
	
def getRealServiceRef(ref):
	service_ref_str = ref.toString()
	service_ref_cleaned = service_ref_str
	if service_ref_str.find("127.0.0.1") > -1: #ICAM SkyDE channels
		service_ref_cleaned = service_ref_str.split("17999/")[1].split(":")[0].replace("%3a", ":")
	return service_ref_cleaned
	
def getRealServiceRefForIPTV(ref, useStrRef = False):
	try:
		from Plugins.Extensions.IPTV.IPTVProcessor import idIPTV
	except:
		idIPTV = 0x13E9
	if useStrRef:
		if ref and ref.startswith("5097:"):
			if ref.find(".m3u8") > -1:
				return "4097:" + ":".join(ref.split(":")[1:])
			else:
				return "1:" + ":".join(ref.split(":")[1:])
		else:
			return ref
	elif ref and ref.type == idIPTV:
		if ref.toString().find(".m3u8") > -1:
			service_ref_cleaned = "4097:" + ":".join(ref.toString().split(":")[1:])
		else:
			service_ref_cleaned = "1:" + ":".join(ref.toString().split(":")[1:])
		ref = eServiceReference(service_ref_cleaned)
	return ref
	
def cleanServiceName(serviceName):
	return serviceName.split("|")[0]
	
def isIPTV(service):
	try:
		from Plugins.Extensions.IPTV.IPTVProcessor import idIPTV
	except:
		idIPTV = 0x13E9
	path = service and service.getPath()
	return path and not path.startswith("/") and service.type in [0x1, 0x1001, 0x138A, 0x1389, idIPTV]
def isIPTVR(service):
	path = service and service.getPath()
	return path and not path.startswith("/")

def getIPTVInfo(ref):
	isBackUpAvailable = False
	catchUpDays = 0
	if ref:
		iptvinfo = ref.split(":")[10:11][0]
		if iptvinfo.find("@") > -1:
			isBackUpAvailable = True
		if iptvinfo.find("|<|") > -1:
			catchUpDays = int(iptvinfo.split("|<|")[1].split("@")[0])
		
	return isBackUpAvailable, catchUpDays
	
def getServiceNum(service, myRoot, isalternatenum = True):
	channelnum = ""
	markeroffset = 0
	bouquetoffset = 0
	serviceHandler = eServiceCenter.getInstance()
	services = serviceHandler.list(eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195) FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
	bouquets = services and services.getContent("SN", True)
	for bouquet in bouquets:
		if not isalternatenum or eServiceReference(bouquet[0]) == myRoot:
			services = serviceHandler.list(eServiceReference(bouquet[0]))
			channels = services and services.getContent("SN", True)
			for idx in range(1, len(channels) + 1):
				if not channels[idx-1][0].startswith("1:64:"):
					if service.toString() == channels[idx-1][0] or ":".join(getCompareReference(service.toString()).split(":")[:10]) == getCompareReference(":".join(channels[idx-1][0].split(":")[:10])):
						if isalternatenum:
							channelnum = str(idx - markeroffset)
						else:
							channelnum = str(idx - markeroffset + bouquetoffset)
						break
				else:
					markeroffset = markeroffset + 1
			bouquetoffset = bouquetoffset + len(channels)
	return channelnum
	
def compareServiceReferences(ref1, ref2):
	if ref1.flags & 0x7 and ref2.flags & 0x7:
		return ref1 == ref2
	else:
		return "1:" + ":".join(ref1.toString().split(":")[1:10]) == "1:" + ":".join(ref2.toString().split(":")[1:10])
		