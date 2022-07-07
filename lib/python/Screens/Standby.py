import os
import struct
import RecordTimer
import Components.ParentalControl
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from Components.Console import Console
from Components.ImportChannels import ImportChannels
from Components.SystemInfo import SystemInfo
from Components.Sources.StreamService import StreamServiceList
from Components.Task import job_manager
from Tools.Directories import mediafilesInUse
from Tools.Notifications import AddNotification
from time import time, localtime
from GlobalActions import globalActionMap
from enigma import eDVBVolumecontrol, eTimer, eDVBLocalTimeHandler, eServiceReference, eStreamServer, quitMainloop, iRecordableService

inStandby = None
infoBarInstance = None

QUIT_SHUTDOWN = 1
QUIT_REBOOT = 2
QUIT_RESTART = 3
QUIT_UPGRADE_FP = 4
QUIT_ERROR_RESTART = 5
QUIT_DEBUG_RESTART = 6
QUIT_MANUFACTURER_RESET = 7
QUIT_MAINT = 16
QUIT_UPGRADE_PROGRAM = 42
QUIT_IMAGE_RESTORE = 43


def isInfoBarInstance():
	global infoBarInstance
	if infoBarInstance is None:
		from Screens.InfoBar import InfoBar
		if InfoBar.instance:
			infoBarInstance = InfoBar.instance
	return infoBarInstance


def checkTimeshiftRunning():
	infobar_instance = isInfoBarInstance()
	return config.usage.check_timeshift.value and infobar_instance and infobar_instance.timeshiftEnabled() and infobar_instance.timeshift_was_activated


class StandbyScreen(Screen):
	def __init__(self, session, StandbyCounterIncrease=True):
		self.skinName = "Standby"
		Screen.__init__(self, session)
		self.avswitch = AVSwitch()

		print("[Standby] enter standby")

		if os.path.exists("/usr/script/standby_enter.sh"):
			Console().ePopen("/usr/script/standby_enter.sh")

		self["actions"] = ActionMap(["StandbyActions"],
		{
			"power": self.Power,
			"discrete_on": self.Power
		}, -1)

		globalActionMap.setEnabled(False)

		self.infoBarInstance = isInfoBarInstance()
		from Screens.SleepTimerEdit import isNextWakeupTime
		self.StandbyCounterIncrease = StandbyCounterIncrease
		self.standbyTimeoutTimer = eTimer()
		self.standbyTimeoutTimer.callback.append(self.standbyTimeout)
		self.standbyStopServiceTimer = eTimer()
		self.standbyStopServiceTimer.callback.append(self.stopService)
		self.standbyWakeupTimer = eTimer()
		self.standbyWakeupTimer.callback.append(self.standbyWakeup)
		self.timeHandler = None

		self.setMute()

		self.paused_service = self.paused_action = False

		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if Components.ParentalControl.parentalControl.isProtected(self.prev_running_service):
			self.prev_running_service = eServiceReference(config.tv.lastservice.value)
		service = self.prev_running_service and self.prev_running_service.toString()
		if service:
			if "%3a//" not in service and service.rsplit(":", 1)[1].startswith("/"):
				self.paused_service = hasattr(self.session.current_dialog, "pauseService") and hasattr(self.session.current_dialog, "unPauseService") and self.session.current_dialog or self.infoBarInstance
				self.paused_action = hasattr(self.paused_service, "seekstate") and hasattr(self.paused_service, "SEEK_STATE_PLAY") and self.paused_service.seekstate == self.paused_service.SEEK_STATE_PLAY
				self.paused_action and self.paused_service.pauseService()
		if not self.paused_service:
			self.timeHandler = eDVBLocalTimeHandler.getInstance()
			if self.timeHandler.ready():
				if self.session.nav.getCurrentlyPlayingServiceOrGroup():
					self.stopService()
				else:
					self.standbyStopServiceTimer.startLongTimer(5)
				self.timeHandler = None
			else:
				self.timeHandler.m_timeUpdated.get().append(self.stopService)

		if hasattr(self.session, "pipshown") and self.session.pipshown:
			self.infoBarInstance and hasattr(self.infoBarInstance, "showPiP") and self.infoBarInstance.showPiP()
		if hasattr(self.session, "pip"):
			del self.session.pip
		self.session.pipshown = False

		if SystemInfo["ScartSwitch"]:
			self.avswitch.setInput("SCART")
		else:
			self.avswitch.setInput("AUX")

		gotoShutdownTime = int(config.usage.standby_to_shutdown_timer.value)
		if gotoShutdownTime:
			self.standbyTimeoutTimer.startLongTimer(gotoShutdownTime)

		if self.StandbyCounterIncrease != 1:
			gotoWakeupTime = isNextWakeupTime(True)
			if gotoWakeupTime != -1:
				curtime = localtime(time())
				if curtime.tm_year > 1970:
					wakeup_time = int(gotoWakeupTime - time())
					if wakeup_time > 0:
						self.standbyWakeupTimer.startLongTimer(wakeup_time)

		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		global inStandby
		inStandby = None
		self.standbyTimeoutTimer.stop()
		self.standbyStopServiceTimer.stop()
		self.standbyWakeupTimer.stop()
		self.timeHandler and self.timeHandler.m_timeUpdated.get().remove(self.stopService)
		if self.paused_service:
			self.paused_action and self.paused_service.unPauseService()
		elif self.prev_running_service:
			service = self.prev_running_service.toString()
			if config.servicelist.startupservice_onstandby.value:
				self.session.nav.playService(eServiceReference(config.servicelist.startupservice.value))
				self.infoBarInstance and self.infoBarInstance.servicelist.correctChannelNumber()
			else:
				self.session.nav.playService(self.prev_running_service)
		self.session.screen["Standby"].boolean = False
		globalActionMap.setEnabled(True)
		if RecordTimer.RecordTimerEntry.receiveRecordEvents:
			RecordTimer.RecordTimerEntry.stopTryQuitMainloop()
		self.avswitch.setInput("ENCODER")
		self.leaveMute()
		if os.path.exists("/usr/script/standby_leave.sh"):
			Console().ePopen("/usr/script/standby_leave.sh")
		if config.usage.remote_fallback_import_standby.value:
			ImportChannels()

	def __onFirstExecBegin(self):
		global inStandby
		inStandby = self
		self.session.screen["Standby"].boolean = True
		if self.StandbyCounterIncrease:
			config.misc.standbyCounter.value += 1

	def Power(self):
		print("[Standby] leave standby")
		self.close(True)

	def setMute(self):
		self.wasMuted = eDVBVolumecontrol.getInstance().isMuted()
		if not self.wasMuted:
			eDVBVolumecontrol.getInstance().volumeMute()

	def leaveMute(self):
		if not self.wasMuted:
			eDVBVolumecontrol.getInstance().volumeUnMute()

	def stopService(self):
		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if Components.ParentalControl.parentalControl.isProtected(self.prev_running_service):
			self.prev_running_service = eServiceReference(config.tv.lastservice.value)
		self.session.nav.stopService()

	def standbyTimeout(self):
		if config.usage.standby_to_shutdown_timer_blocktime.value:
			curtime = localtime(time())
			if curtime.tm_year > 1970: #check if the current time is valid
				curtime = (curtime.tm_hour, curtime.tm_min, curtime.tm_sec)
				begintime = tuple(config.usage.standby_to_shutdown_timer_blocktime_begin.value)
				endtime = tuple(config.usage.standby_to_shutdown_timer_blocktime_end.value)
				if begintime <= endtime and (curtime >= begintime and curtime < endtime) or begintime > endtime and (curtime >= begintime or curtime < endtime):
					duration = (endtime[0] * 3600 + endtime[1] * 60) - (curtime[0] * 3600 + curtime[1] * 60 + curtime[2])
					if duration:
						if duration < 0:
							duration += 24 * 3600
						self.standbyTimeoutTimer.startLongTimer(duration)
						return
		if self.session.screen["TunerInfo"].tuner_use_mask or mediafilesInUse(self.session):
			self.standbyTimeoutTimer.startLongTimer(600)
		else:
			RecordTimer.RecordTimerEntry.TryQuitMainloop()

	def standbyWakeup(self):
		self.Power()

	def createSummary(self):
		return StandbySummary


class Standby(StandbyScreen):
	def __init__(self, session, StandbyCounterIncrease=True):
		if checkTimeshiftRunning():
			self.skin = """<screen position="0,0" size="0,0"/>"""
			Screen.__init__(self, session)
			self.infoBarInstance = isInfoBarInstance()
			self.StandbyCounterIncrease = StandbyCounterIncrease
			self.onFirstExecBegin.append(self.showCheckTimeshiftRunning)
			self.onHide.append(self.close)
		else:
			StandbyScreen.__init__(self, session, StandbyCounterIncrease)

	def showCheckTimeshiftRunning(self):
		self.infoBarInstance.checkTimeshiftRunning(self.showCheckTimeshiftRunningCallback, timeout=20)

	def showCheckTimeshiftRunningCallback(self, answer=False):
		if answer:
			self.onClose.append(self.goStandby)

	def goStandby(self):
		AddNotification(StandbyScreen, self.StandbyCounterIncrease)


class StandbySummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="0,0" size="132,64" font="Regular;40" halign="center">
			<convert type="ClockToText" />
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="0,0" size="132,64" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
	</screen>"""


class QuitMainloopScreen(Screen):
	def __init__(self, session, retvalue=QUIT_SHUTDOWN):
		self.skin = """<screen name="QuitMainloopScreen" position="fill" flags="wfNoBorder">
				<ePixmap pixmap="icons/input_info.png" position="c-27,c-60" size="53,53" alphatest="on" />
				<widget name="text" position="center,c+5" size="720,100" font="Regular;22" halign="center" />
			</screen>"""
		Screen.__init__(self, session)
		from Components.Label import Label
		text = {
			QUIT_SHUTDOWN: _("Your receiver is shutting down"),
			QUIT_REBOOT: _("Your receiver is rebooting"),
			QUIT_RESTART: _("The user interface of your receiver is restarting"),
			QUIT_UPGRADE_FP: _("Your frontprocessor will be updated\nPlease wait until your receiver reboots\nThis may take a few minutes"),
			QUIT_DEBUG_RESTART: _("The user interface of your receiver is restarting in debug mode"),
			QUIT_UPGRADE_PROGRAM: _("Unattended update in progress\nPlease wait until your receiver reboots\nThis may take a few minutes"),
			QUIT_MANUFACTURER_RESET: _("Manufacturer reset in progress\nPlease wait until enigma2 restarts")
		}.get(retvalue)
		self["text"] = Label(text)


inTryQuitMainloop = False


def getReasons(session, retvalue=QUIT_SHUTDOWN):
	recordings = session.nav.getRecordings()
	jobs = len(job_manager.getPendingJobs())
	reasons = []
	next_rec_time = -1
	if not recordings:
		next_rec_time = session.nav.RecordTimer.getNextRecordingTime()
	if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 360):
		reasons.append(_("Recording(s) are in progress or coming up in few seconds!"))
	if jobs:
		if jobs == 1:
			job = job_manager.getPendingJobs()[0]
			reasons.append("%s: %s (%d%%)" % (job.getStatustext(), job.name, int(100 * job.progress / float(job.end))))
		else:
			reasons.append((ngettext("%d job is running in the background!", "%d jobs are running in the background!", jobs) % jobs))
	if checkTimeshiftRunning():
		reasons.append(_("You seem to be in timeshift!"))
	if eStreamServer.getInstance().getConnectedClients() or StreamServiceList:
		reasons.append(_("Client is streaming from this box!"))
	if not reasons and mediafilesInUse(session) and retvalue in (QUIT_SHUTDOWN, QUIT_REBOOT, QUIT_UPGRADE_FP, QUIT_UPGRADE_PROGRAM):
		reasons.append(_("A file from media is in use!"))
	return "\n".join(reasons)


class TryQuitMainloop(MessageBox):
	def __init__(self, session, retvalue=QUIT_SHUTDOWN, timeout=-1, default_yes=False, check_reasons=True):
		self.retval = retvalue
		self.connected = False
		reason = check_reasons and getReasons(session, retvalue)
		if reason:
			text = {
				QUIT_SHUTDOWN: _("Really shutdown now?"),
				QUIT_REBOOT: _("Really reboot now?"),
				QUIT_RESTART: _("Really restart now?"),
				QUIT_UPGRADE_FP: _("Really update the frontprocessor and reboot now?"),
				QUIT_DEBUG_RESTART: _("Really restart in debug mode now?"),
				QUIT_UPGRADE_PROGRAM: _("Really update your settop box and reboot now?"),
				QUIT_MANUFACTURER_RESET: _("Really perform a manufacturer reset now?")
			}.get(retvalue, None)
			if text:
				MessageBox.__init__(self, session, "%s\n%s" % (reason, text), type=MessageBox.TYPE_YESNO, timeout=timeout, default=default_yes)
				self.skinName = "MessageBoxSimple"
				session.nav.record_event.append(self.getRecordEvent)
				self.connected = True
				self.onShow.append(self.__onShow)
				self.onHide.append(self.__onHide)
				return
		self.skin = """<screen position="0,0" size="0,0"/>"""
		Screen.__init__(self, session)
		self.close(True)

	def getRecordEvent(self, recservice, event):
		if event == iRecordableService.evEnd:
			recordings = self.session.nav.getRecordings()
			if not recordings: # no more recordings exist
				rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
				if rec_time > 0 and (rec_time - time()) < 360:
					self.initTimeout(360) # wait for next starting timer
					self.startTimer()
				else:
					self.close(True) # immediate shutdown
		elif event == iRecordableService.evStart:
			self.stopTimer()

	def close(self, value):
		if self.connected:
			self.connected = False
			self.session.nav.record_event.remove(self.getRecordEvent)
		if value:
			self.hide()
			if self.retval == QUIT_SHUTDOWN:
				config.misc.DeepStandby.value = True
				if not inStandby:
					if os.path.exists("/usr/script/standby_enter.sh"):
						Console().ePopen("/usr/script/standby_enter.sh")
					if SystemInfo["HasHDMI-CEC"] and config.hdmicec.enabled.value and config.hdmicec.control_tv_standby.value and config.hdmicec.next_boxes_detect.value:
						import Components.HdmiCec
						Components.HdmiCec.hdmi_cec.secondBoxActive()
						self.delay = eTimer()
						self.delay.timeout.callback.append(self.quitMainloop)
						self.delay.start(1500, True)
						return
			elif not inStandby:
				config.misc.RestartUI.value = True
				config.misc.RestartUI.save()
			self.quitMainloop()
		else:
			MessageBox.close(self, True)

	def quitMainloop(self):
		self.session.nav.stopService()
		self.quitScreen = self.session.instantiateDialog(QuitMainloopScreen, retvalue=self.retval)
		self.quitScreen.show()
		quitMainloop(self.retval)

	def __onShow(self):
		global inTryQuitMainloop
		inTryQuitMainloop = True

	def __onHide(self):
		global inTryQuitMainloop
		inTryQuitMainloop = False

class SwitchToAndroid(Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self["myActionMap"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.goAndroid,
			"cancel": self.close,
		}, -1)
		self.onShown.append(self.switchAndroid)

	def goAndroid(self, answer):
		from Screens.Standby import TryQuitMainloop
		if answer:
			with open('/dev/block/by-name/flag', 'wb') as f:
				f.write(struct.pack("B", 0))
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close()

	def switchAndroid(self):
		self.onShown.remove(self.switchAndroid)
		self.session.openWithCallback(self.goAndroid, MessageBox, _("\n Do you want to switch to Android ?"))
