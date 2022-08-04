from xml.etree.ElementTree import parse
from enigma import eDVBCIInterfaces, eDVBCI_UI, eEnv, eServiceCenter, eServiceReference, getBestPlayableServiceReference, iRecordableService
from Components.SystemInfo import SystemInfo
from Components.config import config
import NavigationInstance
import os


class CIHelper:

	CI_ASSIGNMENT_LIST = None
	CI_ASSIGNMENT_SERVICES_LIST = None
	CI_MULTIDESCRAMBLE = None
	CI_RECORDS_LIST = None
	CI_INIT_NOTIFIER = None
	CI_MULTIDESCRAMBLE_MODULES = ("AlphaCrypt", "M7 CAM701 Multi-2")

	def parse_ci_assignment(self):
		NUM_CI = SystemInfo["CommonInterface"]
		if NUM_CI and NUM_CI > 0:
			self.CI_ASSIGNMENT_LIST = []

			def getValue(definitions, default):
				Len = len(definitions)
				return Len > 0 and definitions[Len - 1].text or default

			for ci in range(NUM_CI):
				filename = eEnv.resolve("${sysconfdir}/enigma2/ci") + str(ci) + ".xml"

				if not os.path.exists(filename):
					continue

				try:
					tree = parse(filename).getroot()
					read_services = []
					read_providers = []
					usingcaid = []
					for slot in tree.findall("slot"):
						read_slot = getValue(slot.findall("id"), False)
						if read_slot and self.CI_ASSIGNMENT_SERVICES_LIST is None:
							self.CI_ASSIGNMENT_SERVICES_LIST = {}

						for caid in slot.findall("caid"):
							read_caid = caid.get("id")
							usingcaid.append(int(read_caid, 16))

						for service in slot.findall("service"):
							read_service_ref = service.get("ref")
							read_services.append(read_service_ref)
							if read_slot and not self.CI_ASSIGNMENT_SERVICES_LIST.get(read_service_ref, False):
								self.CI_ASSIGNMENT_SERVICES_LIST[read_service_ref] = read_slot

						for provider in slot.findall("provider"):
							read_provider_name = provider.get("name")
							read_provider_dvbname = provider.get("dvbnamespace")
							read_providers.append((read_provider_name, int(read_provider_dvbname, 16)))
							if read_slot:
								provider_services_refs = self.getProivderServices([read_provider_name])
								if provider_services_refs:
									for ref in provider_services_refs:
										if not self.CI_ASSIGNMENT_SERVICES_LIST.get(ref, False):
											self.CI_ASSIGNMENT_SERVICES_LIST[ref] = read_slot

						if read_slot:
							self.CI_ASSIGNMENT_LIST.append((int(read_slot), (read_services, read_providers, usingcaid)))
				except:
					print("[CI_ASSIGNMENT %d] ERROR parsing xml..." % ci)
					try:
						os.remove(filename)
					except:
						print("[CI_ASSIGNMENT %d] ERROR remove damaged xml..." % ci)
			if self.CI_ASSIGNMENT_LIST:
				for item in self.CI_ASSIGNMENT_LIST:
					try:
						eDVBCIInterfaces.getInstance().setDescrambleRules(item[0], item[1])
						print("[CI_ASSIGNMENT %d] activate with following settings" % item[0])
					except:
						print("[CI_ASSIGNMENT %d] ERROR setting DescrambleRules" % item[0])

	def ciRecordEvent(self, service, event):
		if event in (iRecordableService.evEnd, iRecordableService.evStart, None):
			self.CI_RECORDS_LIST = []
			if NavigationInstance.instance.getRecordings()  and hasattr(NavigationInstance.instance, "RecordTimer") and hasattr(NavigationInstance.instance.RecordTimer, "timer_list"):
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if not timer.justplay and timer.state in (1, 2) and timer.record_service and not (timer.record_ecm and not timer.descramble):
						if timer.service_ref.ref.flags & eServiceReference.isGroup:
							timerservice = hasattr(timer, "rec_ref") and timer.rec_ref
							if not timerservice:
								timerservice = getBestPlayableServiceReference(timer.service_ref.ref, eServiceReference())
						else:
							timerservice = timer.service_ref.ref
						if timerservice:
							timerstr = timerservice.toString()
							is_assignment = self.ServiceIsAssigned(timerstr)
							if is_assignment:
								if is_assignment[0] not in self.CI_RECORDS_LIST:
									self.CI_RECORDS_LIST.insert(0, is_assignment[0])
								if is_assignment not in self.CI_RECORDS_LIST:
									self.CI_RECORDS_LIST.append(is_assignment)

	def load_ci_assignment(self, force=False):
		if self.CI_ASSIGNMENT_LIST is None or force:
			self.parse_ci_assignment()

	def getProivderServices(self, providers):
		provider_services_refs = []
		if len(providers):
			serviceHandler = eServiceCenter.getInstance()
			for x in providers:
				refstr = '1:7:0:0:0:0:0:0:0:0:(provider == "%s") && (type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 31) || (type == 134) || (type == 195) ORDER BY name:%s' % (x, x)
				myref = eServiceReference(refstr)
				servicelist = serviceHandler.list(myref)
				if not servicelist is None:
					while True:
						service = servicelist.getNext()
						if not service.valid():
							break
						provider_services_refs.append(service.toString())
		return provider_services_refs

	def ServiceIsAssigned(self, ref, timer=None):
		if self.CI_ASSIGNMENT_SERVICES_LIST is not None:
			if self.CI_RECORDS_LIST is None and NavigationInstance.instance and hasattr(NavigationInstance.instance, "RecordTimer") and hasattr(NavigationInstance.instance, "record_event"):
				NavigationInstance.instance.record_event.append(self.ciRecordEvent)
				self.ciRecordEvent(None, None)
			if ref and ref.startswith('1:134:'):
				if timer:
					if timer.state == 2 and not timer.justplay:
						ref = hasattr(timer, "rec_ref") and timer.rec_ref and timer.rec_ref.toString()
					else:
						alternativeServices = eServiceCenter.getInstance().list(eServiceReference(ref))
						if alternativeServices:
							count = 0
							is_ci_service = 0
							ci_slot = []
							for service in alternativeServices.getContent("S", True):
								count += 1
								is_assignment = self.CI_ASSIGNMENT_SERVICES_LIST.get(service, False)
								if is_assignment:
									is_ci_service += 1
									if is_assignment not in ci_slot:
										ci_slot.append(is_assignment)
										if len(ci_slot) > 1:
											return False
							if ci_slot and count == is_ci_service:
								return (ci_slot[0], "")
						return False
				else:
					return False
			if ref:
				is_assignment = self.CI_ASSIGNMENT_SERVICES_LIST.get(ref, False)
				return is_assignment and (is_assignment, ref) or False
		return False

	def forceUpdateMultiDescramble(self, configElement):
		self.CI_MULTIDESCRAMBLE = None

	def canMultiDescramble(self, ci):
		if self.CI_MULTIDESCRAMBLE is None:
			NUM_CI = SystemInfo["CommonInterface"]
			if NUM_CI and NUM_CI > 0:
				self.CI_MULTIDESCRAMBLE = []
				for slot in range(NUM_CI):
					appname = eDVBCI_UI.getInstance().getAppName(slot)
					multipleServices = config.ci[slot].canDescrambleMultipleServices.value
					if self.CI_INIT_NOTIFIER is None:
						config.ci[slot].canDescrambleMultipleServices.addNotifier(self.forceUpdateMultiDescramble, initial_call=False, immediate_feedback=False)
					if multipleServices == "yes" or (appname in self.CI_MULTIDESCRAMBLE_MODULES and multipleServices == "auto"):
						self.CI_MULTIDESCRAMBLE.append(str(slot))
				self.CI_INIT_NOTIFIER = True
		else:
			return self.CI_MULTIDESCRAMBLE and ci in self.CI_MULTIDESCRAMBLE

	def isPlayable(self, service):
		is_assignment = self.ServiceIsAssigned(service)
		if is_assignment and self.CI_RECORDS_LIST and is_assignment[0] in self.CI_RECORDS_LIST and is_assignment not in self.CI_RECORDS_LIST:
			if self.canMultiDescramble(is_assignment[0]):
				for timerservice in self.CI_RECORDS_LIST:
					if len(timerservice) > 1:
						if timerservice[0] == is_assignment[0]:
							eService = eServiceReference(timerservice[1])
							eService1 = eServiceReference(service)
							for x in (4, 2, 3):
								if eService.getUnsignedData(x) != eService1.getUnsignedData(x):
									return 0
			else:
				return 0
		return 1


cihelper = CIHelper()


def isPlayable(service):
	ret = cihelper.isPlayable(service)
	return ret
