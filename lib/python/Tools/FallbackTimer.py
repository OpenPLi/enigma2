from ServiceReference import ServiceReference
from Components.config import config
from Screens.MessageBox import MessageBox
from timer import TimerEntry as TimerObject
from urllib.parse import quote
from xml.etree.ElementTree import fromstring
from json import loads
from base64 import encodebytes


class FallbackTimerList():

	def __init__(self, parent, fallbackFunction, fallbackFunctionNOK=None):
		self.fallbackFunction = fallbackFunction
		self.fallbackFunctionNOK = fallbackFunctionNOK or fallbackFunction
		self.parent = parent
		self.headers = {}
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_external_timer.value and config.usage.remote_fallback.value:
			self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = "%s:%s" % (self.url, config.usage.remote_fallback_openwebif_port.value)
				if config.usage.remote_fallback_openwebif_userid.value and config.usage.remote_fallback_openwebif_password.value:
					self.headers = {b"Authorization": "Basic %s" % encodebytes(("%s:%s" % (config.usage.remote_fallback_openwebif_userid.value, config.usage.remote_fallback_openwebif_password.value)).encode("UTF-8")).strip()}
			self.getFallbackTimerList()
		else:
			self.url = None
			self.list = []
			parent.onLayoutFinish.append(self.fallbackFunction)

	# remove any trailing channel name from the service reference
	def cleanServiceRef(self, service_ref):
		service_ref = str(service_ref)
		if not service_ref.endswith(":"):
			service_ref = service_ref.rsplit("::", 1)[0] + ":"
		return service_ref

	def getUrl(self, url):
		print("[FallbackTimer] getURL", url)
		from twisted.web.client import getPage
		return getPage(("%s/%s" % (self.url, url)).encode('utf-8'), headers=self.headers)

	def getFallbackTimerList(self):
		self.list = []
		if self.url:
			try:
				self.getUrl("api/timerlist").addCallback(self.gotFallbackTimerList).addErrback(self.fallback)
			except:
				self.fallback(_("Unexpected error while retrieving fallback tuner's timer information"))
		else:
			self.fallback()

	def gotFallbackTimerList(self, data):
		self.list = []
		try:
			timers = loads(data.decode('utf-8'))
			if 'result' in timers and timers['result'] == False:
				self.fallback(_("Fallback API did not return a valid result."))
			else:
				self.list = [
						FallbackTimerClass(
							service_ref=timer["serviceref"],
							name=timer["name"],
							disabled=timer["disabled"],
							timebegin=timer["begin"],
							timeend=timer["end"],
							duration=timer["duration"],
							startprepare=timer["startprepare"],
							state=timer["state"],
							repeated=timer["repeated"],
							justplay=timer["justplay"],
							eit=timer["eit"],
							afterevent=timer["afterevent"],
							dirname=timer["dirname"],
							description=timer["description"])
					for timer in timers['timers']
				]
				self.fallback()

		except Exception as e:
			self.fallback(e)

		print("[FallbackTimer] read %s timers from fallback tuner" % len(self.list))
		self.parent.session.nav.RecordTimer.setFallbackTimerList(self.list)

	def removeTimer(self, timer, fallbackFunction, fallbackFunctionNOK=None):
		self.fallbackFunction = fallbackFunction
		self.fallbackFunctionNOK = fallbackFunctionNOK or fallbackFunction
		self.getUrl("web/timerdelete?sRef=%s&begin=%s&end=%s" % (self.cleanServiceRef(timer.service_ref), timer.begin, timer.end)).addCallback(self.getUrlFallback).addErrback(self.fallback)

	def toggleTimer(self, timer, fallbackFunction, fallbackFunctionNOK=None):
		self.fallbackFunction = fallbackFunction
		self.fallbackFunctionNOK = fallbackFunctionNOK or fallbackFunction
		self.getUrl("web/timertogglestatus?sRef=%s&begin=%s&end=%s" % (self.cleanServiceRef(timer.service_ref), timer.begin, timer.end)).addCallback(self.getUrlFallback).addErrback(self.fallback)

	def cleanupTimers(self, fallbackFunction, fallbackFunctionNOK=None):
		self.fallbackFunction = fallbackFunction
		self.fallbackFunctionNOK = fallbackFunctionNOK or fallbackFunction
		if self.url:
			self.getUrl("web/timercleanup?cleanup=true").addCallback(self.getUrlFallback).addErrback(self.fallback)
		else:
			self.fallback()

	def addTimer(self, timer, fallbackFunction, fallbackFunctionNOK=None):
		self.fallbackFunction = fallbackFunction
		self.fallbackFunctionNOK = fallbackFunctionNOK or fallbackFunction
		url = "web/timeradd?sRef=%s&begin=%s&end=%s&name=%s&description=%s&disabled=%s&justplay=%s&afterevent=%s&repeated=%s&dirname=%s&eit=%s" % (
			self.cleanServiceRef(timer.service_ref),
			timer.begin,
			timer.end,
			quote(timer.name.encode()),
			quote(timer.description.encode()),
			timer.disabled,
			timer.justplay,
			timer.afterEvent,
			timer.repeated,
			quote(timer.dirname),
			timer.eit or 0,
		)
		self.getUrl(url).addCallback(self.getUrlFallback).addErrback(self.fallback)

	def editTimer(self, timer, fallbackFunction, fallbackFunctionNOK=None):
		self.fallbackFunction = fallbackFunction
		self.fallbackFunctionNOK = fallbackFunctionNOK or fallbackFunction
		url = "web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&disabled=%s&justplay=%s&afterevent=%s&repeated=%s&channelOld=%s&beginOld=%s&endOld=%s&dirname=%s&eit=%s" % (
			self.cleanServiceRef(timer.service_ref),
			timer.begin,
			timer.end,
			quote(timer.name.encode()),
			quote(timer.description.encode()),
			timer.disabled,
			timer.justplay,
			timer.afterEvent,
			timer.repeated,
			timer.service_ref_prev,
			timer.begin_prev,
			timer.end_prev,
			quote(timer.dirname),
			timer.eit or 0,
		)
		self.getUrl(url).addCallback(self.getUrlFallback).addErrback(self.fallback)

	def getUrlFallback(self, data):
		try:
			root = fromstring(data)
			if root[0].text == 'True':
				self.getFallbackTimerList()
			else:
				self.fallback(root[1].text)
		except:
				self.fallback("Unexpected Error")

	def fallback(self, message=None):
		if message:
			self.parent.session.openWithCallback(self.fallbackNOK, MessageBox, _("Error while retrieving fallback timer information\n%s") % message, MessageBox.TYPE_ERROR)
		else:
			self.fallbackFunction()

	def fallbackNOK(self, answer=None):
		self.fallbackFunctionNOK()


class FallbackTimerDirs(FallbackTimerList):

	def getFallbackTimerList(self):
		if self.url:
			try:
				self.getUrl("web/getlocations").addCallback(self.getlocations).addErrback(self.fallbackFunction)
			except:
				self.fallbackFunction()
		else:
			self.fallbackFunction()

	def getlocations(self, data):
		self.locations = [c.text for c in fromstring(data)]
		try:
			self.getUrl("web/getcurrlocation").addCallback(self.getcurrlocation).addErrback(self.fallbackFunction)
		except:
			self.fallbackFunction()

	def getcurrlocation(self, data):
		currlocation = [c.text for c in fromstring(data)]
		if currlocation:
			self.fallbackFunction(currlocation[0], self.locations)
		else:
			self.fallbackFunction()


class FallbackTimerClass(TimerObject):
	def __init__(self, service_ref="", name="", disabled=0,
			timebegin=0, timeend=0, duration=0, startprepare=0,
			state=0, repeated=0, justplay=0, eit=0, afterevent=0,
			dirname="", description=""):
		self.service_ref = ServiceReference(service_ref and ':'.join(service_ref.split(':')[:11]) or None)
		self.name = name
		self.disabled = disabled
		self.begin = timebegin
		self.end = timeend
		self.duration = duration
		self.startprepare = startprepare
		self.state = state
		self.repeated = repeated
		self.justplay = justplay
		self.eit = eit
		self.afterEvent = afterevent
		self.dirname = dirname
		self.description = description

		self.findRunningEvent = True
		self.findNextEvent = False

		self.flags = ""
		self.conflict_detection = True
		self.external = True
		self.always_zap = False
		self.zap_wakeup = False
		self.pipzap = False
		self.rename_repeat = False
		self.record_ecm = False
		self.descramble = True
		self.tags = []
		self.repeatedbegindate = timebegin
