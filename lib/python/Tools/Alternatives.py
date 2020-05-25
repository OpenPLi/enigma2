from enigma import eServiceCenter, eServiceReference
from Components.config import config
from ServiceReference import isPlayableForCur
from Tools.CIHelper import cihelper

def getAlternativeChannels(service):
	alternativeServices = eServiceCenter.getInstance().list(eServiceReference(service))
	return alternativeServices and alternativeServices.getContent("S", True)

def CompareWithAlternatives(serviceA, serviceB):
	return serviceA and serviceB and (
		serviceA == serviceB or
		serviceA.startswith('1:134:') and serviceB in getAlternativeChannels(serviceA) or
		serviceB.startswith('1:134:') and serviceA in getAlternativeChannels(serviceB))

def GetWithAlternative(service):
	if service.startswith('1:134:'):
		channels = getAlternativeChannels(service)
		if channels:
			return channels[0]
	return service

def ResolveCiAlternative(ref, ignore_ref=None, record_mode=False):
	if ref and isinstance(ref, eServiceReference):
		if ref.flags & eServiceReference.isGroup:
			serviceList = eServiceCenter.getInstance() and eServiceCenter.getInstance().list(ref)
			prio_list = []
			prio_val = int(config.usage.alternatives_priority.value)
			if serviceList:
				for service in serviceList.getContent("R"):
					if not ignore_ref or service != ignore_ref:
						refstr = service.toString()
						def resolveRecordLiveMode():
							if record_mode:
								is_assignment = cihelper.ServiceIsAssigned(refstr)
								if not is_assignment or is_assignment[0] != record_mode[0]:
									return True
								elif cihelper.canMultiDescramble(is_assignment[0]):
									eService = eServiceReference(record_mode[1])
									for x in (4, 2, 3):
										if service.getUnsignedData(x) != eService.getUnsignedData(x):
											return False
								else:
									return False
							return True
						if resolveRecordLiveMode() and (service.getPath() or isPlayableForCur(service)):
							if prio_val == 127:
								return service
							else:
								type = ("%3a//" in refstr and 4) or ('EEEE0000' in refstr and 2) or ('FFFF0000' in refstr and 3) or 1
								prio_list.append((service, type))
			num = len(prio_list)
			if num == 1:
				return prio_list[0][0]
			elif num > 1:
				prio_map = [(3, 2, 1),# -S -C -T
							(3, 1, 2),# -S -T -C
							(2, 3, 1),# -C -S -T
							(1, 3, 2),# -C -T -S
							(1, 2, 3),# -T -C -S
							(2, 1, 3) # -T -S -C
							]
				cur = tmp = 0
				stream_service = service = None
				for x in prio_list:
					if x[1] == 2:
						tmp = prio_map[prio_val][2]
					elif x[1] == 3:
						tmp = prio_map[prio_val][1]
					elif x[1] == 1:
						tmp = prio_map[prio_val][0]
					if tmp > cur:
						cur = tmp
						service = x[0]
					if x[1] == 4 and not stream_service:
						stream_service = x[0]
				if cur > 0:
					return service
				if stream_service:
					return stream_service
		elif ref.getPath() or isPlayableForCur(ref):
			return ref
	return None
