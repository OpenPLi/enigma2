from Components.config import config, ConfigSubsection, ConfigSelection, ConfigPIN, ConfigYesNo, ConfigSubList, ConfigInteger
from Components.ServiceList import refreshServiceList
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from ServiceReference import ServiceReference
from Tools import Notifications
from Tools.Directories import resolveFilename, SCOPE_CONFIG
from Tools.Notifications import AddPopup
from enigma import eTimer, eServiceCenter, iServiceInformation, eServiceReference, eDVBDB
import time

TYPE_SERVICE = "SERVICE"
TYPE_BOUQUETSERVICE = "BOUQUETSERVICE"
TYPE_BOUQUET = "BOUQUET"
LIST_BLACKLIST = "blacklist"

FLAG_IS_PARENTAL_PROTECTED_HIDDEN = 256


def InitParentalControl():
	config.ParentalControl = ConfigSubsection()
	config.ParentalControl.storeservicepin = ConfigSelection(default="never", choices=[("never", _("never")), ("5", _("%d minutes") % 5), ("15", _("%d minutes") % 15), ("30", _("%d minutes") % 30), ("60", _("%d minutes") % 60), ("120", _("%d minutes") % 120), ("standby", _("until standby/restart"))])
	config.ParentalControl.configured = ConfigYesNo(default=False)
	config.ParentalControl.setuppinactive = ConfigYesNo(default=False)
	config.ParentalControl.retries = ConfigSubsection()
	config.ParentalControl.retries.servicepin = ConfigSubsection()
	config.ParentalControl.retries.servicepin.tries = ConfigInteger(default=3)
	config.ParentalControl.retries.servicepin.time = ConfigInteger(default=3)
	config.ParentalControl.servicepin = ConfigSubList()
	config.ParentalControl.servicepin.append(ConfigPIN(default=0))
	config.ParentalControl.age = ConfigSelection(default="18", choices=[("0", _("No age block"))] + list((str(x), "%d+" % x) for x in range(3, 19)))
	config.ParentalControl.hideBlacklist = ConfigYesNo(default=False)
	config.ParentalControl.config_sections = ConfigSubsection()
	config.ParentalControl.config_sections.main_menu = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.configuration = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.timer_menu = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.plugin_browser = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.standby_menu = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.software_update = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.manufacturer_reset = ConfigYesNo(default=True)
	config.ParentalControl.config_sections.movie_list = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.context_menus = ConfigYesNo(default=False)
	config.ParentalControl.config_sections.menu_sort = ConfigYesNo(default=False)

	#Added for backwards compatibility with some 3rd party plugins that depend on this config
	config.ParentalControl.servicepinactive = config.ParentalControl.configured
	config.ParentalControl.setuppin = config.ParentalControl.servicepin[0]
	config.ParentalControl.retries.setuppin = config.ParentalControl.retries.servicepin
	config.ParentalControl.type = ConfigSelection(default="blacklist", choices=[(LIST_BLACKLIST, _("blacklist"))])

	global parentalControl
	parentalControl = ParentalControl()


class ParentalControl:
	def __init__(self):
		self.filesOpened = False
		self.PinDlg = None
		self.sessionPinTimer = eTimer()
		self.sessionPinTimer.callback.append(self.resetSessionPin)
		self.getConfigValues()

	def serviceMethodWrapper(self, service, method, *args):
		if TYPE_BOUQUET in service:
			method(service, TYPE_BOUQUET, *args)
			servicelist = self.readServicesFromBouquet(service, "C")
			for ref in servicelist:
				sRef = str(ref[0])
				method(sRef, TYPE_BOUQUETSERVICE, *args)
		else:
			ref = ServiceReference(service)
			sRef = str(ref)
			method(sRef, TYPE_SERVICE, *args)

	def isProtected(self, ref):
		if not config.ParentalControl.servicepin[0].value or not config.ParentalControl.servicepinactive.value or not ref:
			return False
		if self.storeServicePin != config.ParentalControl.storeservicepin.value:
			self.getConfigValues()
		service = ref.toCompareString()
		path = ref.getPath()
		info = eServiceCenter.getInstance().info(ref)
		age = 0
		if path.startswith("/"):
			if service.startswith("1:"):
				refstr = info and info.getInfoString(ref, iServiceInformation.sServiceref)
				service = refstr and eServiceReference(refstr).toCompareString()
			if [x for x in path[1:].split("/") if x.startswith(".") and not x == ".Trash"]:
				age = 18
		elif int(config.ParentalControl.age.value):
			event = info and info.getEvent(ref)
			rating = event and event.getParentalData()
			age = rating and rating.getRating()
			age = age and age <= 15 and age + 3 or 0
		return (age and age >= int(config.ParentalControl.age.value)) or service and service in self.blacklist

	def isServicePlayable(self, ref, callback, session=None):
		self.session = session
		if self.isProtected(ref):
			if self.sessionPinCached:
				return True
			self.callback = callback
			service = ref.toCompareString()
			title = 'FROM BOUQUET "userbouquet.' in service and _("This bouquet is protected by a parental control PIN") or _("This service is protected by a parental control PIN")
			if session:
				Notifications.RemovePopup("Parental control")
				if self.PinDlg:
					self.PinDlg.close()
				self.PinDlg = session.openWithCallback(boundFunction(self.servicePinEntered, ref), PinInput, triesEntry=config.ParentalControl.retries.servicepin, pinList=self.getPinList(), service=ServiceReference(ref).getServiceName(), title=title, windowTitle=_("Parental control"), simple=False, zap=True)
			else:
				Notifications.AddNotificationParentalControl(boundFunction(self.servicePinEntered, ref), PinInput, triesEntry=config.ParentalControl.retries.servicepin, pinList=self.getPinList(), service=ServiceReference(ref).getServiceName(), title=title, windowTitle=_("Parental control"), zap=True)
			return False
		else:
			return True

	def protectService(self, service):
		if service not in self.blacklist:
			self.serviceMethodWrapper(service, self.addServiceToList, self.blacklist)
			if config.ParentalControl.hideBlacklist.value and not self.sessionPinCached and config.ParentalControl.storeservicepin.value != "never":
				self.setHideFlag(service, True)

	def unProtectService(self, service):
		if service in self.blacklist:
			self.serviceMethodWrapper(service, self.removeServiceFromList, self.blacklist)

	def getProtectionLevel(self, service):
		return service not in self.blacklist and -1 or 0

	def isServiceProtectionBouquet(self, service):
		return service in self.blacklist and TYPE_BOUQUETSERVICE in self.blacklist[service]

	def getConfigValues(self):
		self.checkPinInterval = False
		self.checkPinIntervalCancel = False
		self.checkSessionPin = False

		self.sessionPinCached = False
		self.pinIntervalSeconds = 0
		self.pinIntervalSecondsCancel = 0

		self.storeServicePin = config.ParentalControl.storeservicepin.value

		if self.storeServicePin == "standby":
			self.checkSessionPin = True
		elif self.storeServicePin != "never":
			self.checkPinInterval = True
			iMinutes = float(self.storeServicePin)
			iSeconds = int(iMinutes * 60)
			self.pinIntervalSeconds = iSeconds

	def standbyCounterCallback(self, configElement):
		self.resetSessionPin()

	def resetSessionPin(self):
		self.sessionPinCached = False
		self.hideBlacklist()
		refreshServiceList()

	def getCurrentTimeStamp(self):
		return time.time()

	def getPinList(self):
		return [x.value for x in config.ParentalControl.servicepin]

	def setSessionPinCached(self):
		if self.checkSessionPin:
			self.sessionPinCached = True
		if self.checkPinInterval:
			self.sessionPinCached = True
			self.sessionPinTimer.startLongTimer(self.pinIntervalSeconds)

	def servicePinEntered(self, service, result=None):
		if result in ("zapup", "zapdown"):
			from Screens.InfoBar import InfoBar
			InfoBarInstance = InfoBar.instance
			if InfoBarInstance and hasattr(InfoBarInstance, "servicelist"):
				InfoBarInstance.servicelist.servicelist.setCurrent(service)
				if result == "zapdown":
					InfoBarInstance.servicelist.servicelist.moveDown()

				else:
					InfoBarInstance.servicelist.servicelist.moveUp()
				InfoBarInstance.servicelist.zap()
		elif result:
			self.setSessionPinCached()
			self.hideBlacklist()
			self.callback(ref=service)
		elif result == False:
			messageText = _("The PIN code you entered is wrong.")
			if self.session:
				self.session.open(MessageBox, messageText, MessageBox.TYPE_INFO, timeout=5)
			else:
				AddPopup(messageText, MessageBox.TYPE_ERROR, timeout=5)

	def saveListToFile(self, sWhichList, vList):
		file = open(resolveFilename(SCOPE_CONFIG, sWhichList), 'w')
		for sService, sType in vList.iteritems():
			if (TYPE_SERVICE in sType or TYPE_BOUQUET in sType) and not sService.startswith("-"):
				file.write(str(sService) + "\n")
		file.close()

	def openListFromFile(self, sWhichList):
		result = {}
		try:
			for x in open(resolveFilename(SCOPE_CONFIG, sWhichList), 'r'):
				sPlain = x.strip()
				self.serviceMethodWrapper(sPlain, self.addServiceToList, result)
		except:
			pass
		return result

	def addServiceToList(self, service, type, vList):
		if service in vList:
			if not type in vList[service]:
				vList[service].append(type)
		else:
			vList[service] = [type]

	def removeServiceFromList(self, service, type, vList):
		if service in vList:
			if type in vList[service]:
				vList[service].remove(type)
			if not vList[service]:
				del vList[service]

	def readServicesFromBouquet(self, sBouquetSelection, formatstring):
		serviceHandler = eServiceCenter.getInstance()
		refstr = sBouquetSelection
		root = eServiceReference(refstr)
		list = serviceHandler and serviceHandler.list(root)
		if list:
			services = list.getContent("CN", True)
			return services
		return []

	def save(self):
		self.saveListToFile(LIST_BLACKLIST, self.blacklist)

	def open(self, save=False):
		if save:
			self.save()
		self.blacklist = self.openListFromFile(LIST_BLACKLIST)
		self.hideBlacklist()
		if not self.filesOpened:
			config.misc.standbyCounter.addNotifier(self.standbyCounterCallback, initial_call=False)
			self.filesOpened = True
		refreshServiceList()

	def __getattr__(self, name):
		if name in ('blacklist', 'whitelist'):
			if not self.filesOpened:
				self.open()
				return getattr(self, name)
		raise AttributeError, name

	def hideBlacklist(self):
		if self.blacklist:
			flag = config.ParentalControl.servicepinactive.value and config.ParentalControl.storeservicepin.value != "never" and config.ParentalControl.hideBlacklist.value and not self.sessionPinCached
			for ref in self.blacklist:
				self.setHideFlag(ref, flag)

	def setHideFlag(self, ref, flag):
		if TYPE_BOUQUET in ref:
			if "alternatives" in ref or TYPE_BOUQUETSERVICE in self.blacklist[ref]:
				return
			ref = ref.split(":")
			ref[1], ref[9] = '519', '1'
			ref_remove = eServiceReference(":".join(ref))
			ref[1], ref[9] = '7', '0'
			ref_add = eServiceReference(":".join(ref))
			if flag:
				ref_remove, ref_add = ref_add, ref_remove
			list = eServiceCenter.getInstance().list(eServiceReference('1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.%s" ORDER BY bouquet' % ('tv' if ref[2] == '1' else 'radio')))
			if list:
				mutableList = list.startEdit()
				if not mutableList.addService(ref_add, ref_remove):
					mutableList.removeService(ref_remove, False)
		else:
			if flag:
				eDVBDB.getInstance().addFlag(eServiceReference(ref), FLAG_IS_PARENTAL_PROTECTED_HIDDEN)
			else:
				eDVBDB.getInstance().removeFlag(eServiceReference(ref), FLAG_IS_PARENTAL_PROTECTED_HIDDEN)
