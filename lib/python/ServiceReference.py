from enigma import eServiceReference, eServiceCenter, getBestPlayableServiceReference
import NavigationInstance

# Global helper functions


def getPlayingRef():
	playingref = None
	if NavigationInstance.instance:
		playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
	return playingref or eServiceReference()


def isPlayableForCur(serviceref):
	info = eServiceCenter.getInstance().info(serviceref)
	return info and info.isPlayable(serviceref, getPlayingRef())


def resolveAlternate(serviceref):
	nref = None
	if serviceref and serviceref.flags & eServiceReference.isGroup:
		nref = getBestPlayableServiceReference(serviceref, getPlayingRef())
		if not nref:
			nref = getBestPlayableServiceReference(serviceref, eServiceReference(), True)
	return nref

# Extensions to eServiceReference


@staticmethod
def __fromDirectory(path):
	ref = eServiceReference(eServiceReference.idFile,
			eServiceReference.flagDirectory |
			eServiceReference.shouldSort | eServiceReference.sort1, path)
	ref.setData(0, 1)
	return ref


eServiceReference.fromDirectory = __fromDirectory

eServiceReference.isPlayback = lambda serviceref: "0:0:0:0:0:0:0:0:0" in serviceref.toCompareString()

# Apply ServiceReference method proxies to the eServiceReference object so the two classes can be used interchangeably
# These are required for ServiceReference backwards compatibility
eServiceReference.isRecordable = lambda serviceref: serviceref.flags & eServiceReference.isGroup or (serviceref.type == eServiceReference.idDVB or serviceref.type == eServiceReference.idDVB + 0x100 or serviceref.type == 0x2000 or serviceref.type == 0x1001 or serviceref.type == eServiceReference.idServiceMP3)


def __repr(serviceref):
	chnum = serviceref.getChannelNum()
	chnum = ", ChannelNum=" + str(chnum) if chnum else ""
	return "eServiceReference(Name=%s%s, String=%s)" % (serviceref.getServiceName(), chnum, serviceref.toString())


eServiceReference.__repr__ = __repr


def __toString(serviceref):
	return serviceref.toString()


eServiceReference.__str__ = __toString


def __getServiceName(serviceref):
	info = eServiceCenter.getInstance().info(serviceref)
	return info and info.getName(serviceref) or ""


eServiceReference.getServiceName = __getServiceName


def __info(serviceref):
	return eServiceCenter.getInstance().info(serviceref)


eServiceReference.info = __info


def __list(serviceref):
	return eServiceCenter.getInstance().list(serviceref)


eServiceReference.list = __list

# ref is obsolete but kept for compatibility.
# A ServiceReference *is* an eServiceReference now, so you no longer need to use .ref


def __getRef(serviceref):
	return serviceref


def __setRef(self, serviceref):
	eServiceReference.__init__(self, serviceref)


eServiceReference.ref = property(__getRef, __setRef,)

# getType is obsolete but kept for compatibility. Use "serviceref.type" instead


def __getType(serviceref):
	return serviceref.type


eServiceReference.getType = __getType

# getFlags is obsolete but kept for compatibility. Use "serviceref.flags" instead


def __getFlags(serviceref):
	return serviceref.flags


eServiceReference.getFlags = __getFlags


# Compatibility class that exposes eServiceReference as ServiceReference
# Don't use this for new code. eServiceReference now supports everything in one single type
class ServiceReference(eServiceReference):
	def __new__(cls, ref, reftype=eServiceReference.idInvalid, flags=0, path=''):
		# if trying to copy an eServiceReference object, turn it into a ServiceReference type and return it
		if reftype == eServiceReference.idInvalid and isinstance(ref, eServiceReference):
			new = ref
			new.__class__ = ServiceReference
			return new
		return eServiceReference.__new__(cls)

	def __init__(self, ref, reftype=eServiceReference.idInvalid, flags=0, path=''):
		if reftype != eServiceReference.idInvalid:
			eServiceReference.__init__(self, reftype, flags, path)
		elif not isinstance(ref, eServiceReference):
			eServiceReference.__init__(self, ref or "")
