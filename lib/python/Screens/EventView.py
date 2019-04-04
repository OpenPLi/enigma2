from Screen import Screen
from Screens.TimerEdit import TimerSanityConflict
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.PluginComponent import plugins
from Components.TimerList import TimerList
from Components.UsageConfig import preferredTimerPath
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Components.Sources.Event import Event
from enigma import eEPGCache, eTimer, eServiceReference
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT, createRecordTimerEntry
from TimerEntry import TimerEntry
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction
from Tools.FallbackTimer import FallbackTimerList
from time import localtime
from Components.config import config

class EventViewBase:
	ADD_TIMER = 0
	REMOVE_TIMER = 1

	def __init__(self, event, Ref, callback=None, similarEPGCB=None, parent=None):
		self.similarEPGCB = similarEPGCB
		self.cbFunc = callback
		self.currentService=Ref
		self.isRecording = (not Ref.ref.flags & eServiceReference.isGroup) and Ref.ref.getPath()
		self.event = event
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self["epg_eventname"] = ScrollLabel()
		self["epg_description"] = ScrollLabel()
		self["FullDescription"] = ScrollLabel()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["duration"] = Label()
		self["key_red"] = StaticText("")
		if similarEPGCB is not None:
			self.SimilarBroadcastTimer = eTimer()
			self.SimilarBroadcastTimer.callback.append(self.getSimilarEvents)
		else:
			self.SimilarBroadcastTimer = None
		self.key_green_choice = self.ADD_TIMER
		if self.isRecording:
			self["key_green"] = StaticText("")
		else:
			self["key_green"] = StaticText(_("Add timer"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"pageUp": self.pageUp,
				"pageDown": self.pageDown,
				"prevEvent": self.prevEvent,
				"nextEvent": self.nextEvent,
				"timerAdd": self.timerAdd,
				"openSimilarList": self.openSimilarList,
				"contextMenu": self.doContext,
			})
		if parent and hasattr(parent, "fallbackTimer"):
			self.fallbackTimer = parent.fallbackTimer
			self.onLayoutFinish.append(self.onCreate)
		else:
			self.fallbackTimer = FallbackTimerList(self, self.onCreate)

	def onCreate(self):
		self.setService(self.currentService)
		self.setEvent(self.event)

	def prevEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, -1)

	def nextEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, +1)

	def removeTimer(self, timer):
		if timer.external:
			self.fallbackTimer.removeTimer(timer, self.setTimerState)
		else:
			timer.afterEvent = AFTEREVENT.NONE
			self.session.nav.RecordTimer.removeEntry(timer)
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		if self.isRecording:
			return
		event = self.event
		serviceref = self.currentService
		if event is None:
			return
		eventid = event.getEventId()
		begin = event.getBeginTime()
		end = begin + event.getDuration()
		refstr = ':'.join(serviceref.ref.toString().split(':')[:11])
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.getAllTimersList():
			needed_ref = ':'.join(timer.service_ref.ref.toString().split(':')[:11]) == refstr
			if needed_ref and timer.eit == eventid and (begin < timer.begin <= end or timer.begin <= begin <= timer.end):
				isRecordEvent = True
				break
			elif needed_ref and timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, event):
				isRecordEvent = True
				break
		if isRecordEvent:
			title_text = timer.repeated and _("Attention, this is repeated timer!\n") or ""
			menu = [(_("Delete timer"), "delete"),(_("Edit timer"), "edit")]
			buttons = ["red", "green"]
			def timerAction(choice):
				if choice is not None:
					if choice[1] == "delete":
						self.removeTimer(timer)
					elif choice[1] == "edit":
						self.session.openWithCallback(self.finishedEdit, TimerEntry, timer)
			self.session.openWithCallback(timerAction, ChoiceBox, title=title_text + _("Select action for timer '%s'.") % timer.name, list=menu, keys=buttons)
		else:
			newEntry = RecordTimerEntry(self.currentService, checkOldTimers = True, dirname = preferredTimerPath(), *parseEvent(self.event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedEdit(self, answer):
		if answer[0]:
			entry = answer[1]
			if entry.external_prev != entry.external:
				def removeEditTimer():
					entry.service_ref, entry.begin, entry.end, entry.external = entry.service_ref_prev, entry.begin_prev, entry.end_prev, entry.external_prev
					self.removeTimer(entry)
				def moveEditTimerError():
					entry.external = entry.external_prev
					self.onSelectionChanged()
				if entry.external:
					self.fallbackTimer.addTimer(entry, removeEditTimer, moveEditTimerError)
				else:
					newentry = createRecordTimerEntry(entry)
					entry.service_ref, entry.begin, entry.end = entry.service_ref_prev, entry.begin_prev, entry.end_prev
					self.fallbackTimer.removeTimer(entry, boundFunction(self.finishedAdd, (True, newentry)), moveEditTimerError)
			elif entry.external:
				self.fallbackTimer.editTimer(entry, self.setTimerState)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					for x in simulTimerList:
						if x.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(x)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, simulTimerList)
						return
					else:
						self.session.nav.RecordTimer.timeChanged(entry)
				if answer is not None and len(answer) > 1:
					entry = answer[1]
					if not entry.disabled:
						self["key_green"].setText(_("Change timer"))
						self.key_green_choice = self.REMOVE_TIMER
					else:
						self["key_green"].setText(_("Add timer"))
						self.key_green_choice = self.ADD_TIMER

	def finishedAdd(self, answer):
		print "finished add"
		if answer[0]:
			entry = answer[1]
			if entry.external:
				self.fallbackTimer.addTimer(entry, self.setTimerState)
			else:
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					for x in simulTimerList:
						if x.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(x)
					simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						if not entry.repeated and not config.recording.margin_before.value and not config.recording.margin_after.value and len(simulTimerList) > 1:
							change_time = False
							conflict_begin = simulTimerList[1].begin
							conflict_end = simulTimerList[1].end
							if conflict_begin == entry.end:
								entry.end -= 30
								change_time = True
							elif entry.begin == conflict_end:
								entry.begin += 30
								change_time = True
							elif entry.begin == conflict_begin and (entry.service_ref and entry.service_ref.ref and entry.service_ref.ref.flags & eServiceReference.isGroup):
								entry.begin += 30
								change_time = True
							if change_time:
								simulTimerList = self.session.nav.RecordTimer.record(entry)
						if simulTimerList is not None:
							self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
				self["key_green"].setText(_("Change timer"))
				self.key_green_choice = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER
			print "Timeredit aborted"

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def setService(self, service):
		self.currentService=service
		self["Service"].newService(service.ref)
		if self.isRecording:
			self["channel"].setText(_("Recording"))
		else:
			name = service.getServiceName()
			if name is not None:
				self["channel"].setText(name)
			else:
				self["channel"].setText(_("unknown service"))

	def sort_func(self,x,y):
		if x[1] < y[1]:
			return -1
		elif x[1] == y[1]:
			return 0
		else:
			return 1

	def setEvent(self, event):
		self.event = event
		self["Event"].newEvent(event)
		if event is None:
			return
		text = event.getEventName()
		short = event.getShortDescription()
		ext = event.getExtendedDescription()
		if short == text:
			short = ""
		if short and ext:
			ext = short + "\n\n" + ext
		elif short:
			ext = short

		if text and ext:
			text += "\n\n"
		text += ext

		self.setTitle(event.getEventName())
		self["epg_eventname"].setText(event.getEventName())
		self["epg_description"].setText(text)
		self["FullDescription"].setText(ext)
		self["datetime"].setText(event.getBeginTimeString())
		self["duration"].setText(_("%d min")%(event.getDuration()/60))
		self["key_red"].setText("")
		if self.SimilarBroadcastTimer is not None:
			self.SimilarBroadcastTimer.start(400,True)
		self.setTimerState()	

	def setTimerState(self):
		serviceref = self.currentService
		eventid = self.event.getEventId()
		begin = self.event.getBeginTime()
		end = begin + self.event.getDuration()
		refstr = ':'.join(serviceref.ref.toString().split(':')[:11])
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.getAllTimersList():
			needed_ref = ':'.join(timer.service_ref.ref.toString().split(':')[:11]) == refstr
			if needed_ref and (timer.eit == eventid and (begin < timer.begin <= end or timer.begin <= begin <= timer.end) or timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, self.event)):
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Change timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER

	def pageUp(self):
		self["epg_eventname"].pageUp()
		self["epg_description"].pageUp()
		self["FullDescription"].pageUp()

	def pageDown(self):
		self["epg_eventname"].pageDown()
		self["epg_description"].pageDown()
		self["FullDescription"].pageDown()

	def getSimilarEvents(self):
		# search similar broadcastings
		if not self.event:
			return
		refstr = str(self.currentService)
		id = self.event.getEventId()
		epgcache = eEPGCache.getInstance()
		ret = epgcache.search(('NB', 100, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, id))
		if ret is not None:
			text = '\n\n' + _('Similar broadcasts:')
			ret.sort(self.sort_func)
			for x in ret:
				t = localtime(x[1])
				text += '\n%02d.%02d.%d, %02d:%02d  -  %s' % (t[2], t[1], t[0], t[3], t[4], x[0])

			descr = self["epg_description"]
			descr.setText(descr.getText()+text)
			descr = self["FullDescription"]
			descr.setText(descr.getText()+text)
			self["key_red"].setText(_("Similar"))

	def openSimilarList(self):
		if self.similarEPGCB is not None and self["key_red"].getText():
			id = self.event and self.event.getEventId()
			refstr = str(self.currentService)
			if id is not None:
				self.similarEPGCB(id, refstr)

	def doContext(self):
		if self.event:
			text = _("Select action")
			menu = [(p.name, boundFunction(self.runPlugin, p)) for p in plugins.getPlugins(where = PluginDescriptor.WHERE_EVENTINFO) \
				if 'servicelist' not in p.__call__.func_code.co_varnames \
					if 'selectedevent' not in p.__call__.func_code.co_varnames ]
			if len(menu) == 1:
				menu and menu[0][1]()
			elif len(menu) > 1:
				def boxAction(choice):
					if choice:
						choice[1]()
				text += ": %s" % self.event.getEventName()
				self.session.openWithCallback(boxAction, ChoiceBox, title=text, list=menu, windowTitle=_("Event view context menu"))

	def runPlugin(self, plugin):
		plugin(session=self.session, service=self.currentService, event=self.event, eventName=self.event.getEventName())

class EventViewSimple(Screen, EventViewBase):
	def __init__(self, session, Event, Ref, callback=None, similarEPGCB=None, parent=None):
		Screen.__init__(self, session)
		self.skinName = "EventView"
		EventViewBase.__init__(self, Event, Ref, callback, similarEPGCB, parent)

class EventViewEPGSelect(Screen, EventViewBase):
	def __init__(self, session, Event, Ref, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None, parent=None):
		Screen.__init__(self, session)
		self.skinName = "EventView"
		self.singleEPGCB = singleEPGCB
		self.multiEPGCB = multiEPGCB
		EventViewBase.__init__(self, Event, Ref, callback, similarEPGCB, parent)
		self["key_yellow"].setText(_("Single EPG"))
		self["key_blue"].setText(_("Multi EPG"))
		self["epgactions"] = ActionMap(["EventViewEPGActions"],
			{
				"openSingleServiceEPG": self.openSingleEPG,
				"openMultiServiceEPG": self.openMultiEPG,
			})

	def openSingleEPG(self):
		self.hide()
		self.singleEPGCB()
		self.close()

	def openMultiEPG(self):
		self.hide()
		self.multiEPGCB()
		self.close()
