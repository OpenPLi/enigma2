from enigma import iServiceInformation, eServiceReference, eServiceCenter
	
def isIPTV(service):
	path = service and service.getPath()
	return path and not path.startswith("/") and service.type in [0x1, 0x1001, 0x138A, 0x1389]
