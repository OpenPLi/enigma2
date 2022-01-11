from Screens.Screen import Screen
from Components.Sources.CurrentService import CurrentService
from Components.Sources.EventInfo import EventInfo
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.FrontendInfo import FrontendInfo
from Components.Sources.Source import Source
from Components.Sources.TunerInfo import TunerInfo
from Components.Sources.Boolean import Boolean
from Components.Sources.RecordState import RecordState
from Components.Converter.Combine import Combine
from Components.Renderer.FrontpanelLed import FrontpanelLed, PATTERN_OFF, PATTERN_BLINK


class SessionGlobals(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["CurrentService"] = CurrentService(session.nav)
		self["Event_Now"] = EventInfo(session.nav, EventInfo.NOW)
		self["Event_Next"] = EventInfo(session.nav, EventInfo.NEXT)
		self["FrontendStatus"] = FrontendStatus(service_source=session.nav.getCurrentService)
		self["FrontendInfo"] = FrontendInfo(navcore=session.nav)
		self["VideoPicture"] = Source()
		self["TunerInfo"] = TunerInfo()
		self["RecordState"] = RecordState(session)
		self["Standby"] = Boolean(fixed=False)

		from Components.SystemInfo import SystemInfo

		nr_leds = SystemInfo.get("NumFrontpanelLEDs", 0)

		if nr_leds > 0:
			combine = Combine(func=lambda s: {(False, False): 0, (False, True): 1, (True, False): 2, (True, True): 3}[(s[0].boolean, s[1].boolean)])
			combine.connect(self["Standby"])
			combine.connect(self["RecordState"])

			if nr_leds == 1:
				FrontpanelLed(which=0, boolean=False, patterns=[PATTERN_OFF, PATTERN_BLINK, PATTERN_OFF, PATTERN_BLINK]).connect(combine)
			elif nr_leds == 2:
				FrontpanelLed(which=0, boolean=False, get_patterns=True).connect(combine)
				FrontpanelLed(which=1, boolean=False, get_patterns=True).connect(combine)
