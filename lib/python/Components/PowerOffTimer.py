from RecordTimer import RecordTimerEntry
from Screens.MessageBox import MessageBox
from Screens import Standby
from Tools.Notifications import AddNotificationWithID
from Tools.Directories import mediafilesInUse
from Components.config import config
from Components.Task import job_manager
from Components.Converter.ClientsStreaming import ClientsStreaming
from enigma import eTimer, eDVBLocalTimeHandler
from time import time, localtime, mktime
import math

# format string ((Tool name, func status running))
exceptionsExternalTools = []

def isExternalToolsRunning():
	for func in exceptionsExternalTools:
		try:
			running = func[1]()
			if running:
				print("[PowerOffTimer] Found exception time for %s !!!" % func[0])
				return True
		except Exception as e:
			print("[PowerOffTimer] external tool status running error: ", e)
	return False

class PowerOffTimerPoller:
	def __init__(self):
		self.session = None
		self.wait_nextday = self.dont_currentday = False
		self.poweroff_time = self.nextday_time = -1
		self.wait_nextday_time = 300
		self.doPowerOffTimer = eTimer()
		self.doPowerOffTimer.callback.append(self.doPowerOffRun)
		self.timeHandler = None
		if config.usage.poweroff_enabled.value:
			self.timeHandler = eDVBLocalTimeHandler.getInstance()
			if self.timeHandler:
				if self.timeHandler.ready():
					self.timeHandler = None
					self.powerStateTimerChanged()
				else:
					self.timeHandler.m_timeUpdated.get().append(self.powerStateTimerChanged)

	def setSession(self, session=None):
		if session:
			self.session = session

	def getDontCurrentday(self):
		return self.dont_currentday

	def powerStateTimerChanged(self, wait_nextday_time=-1, dont_currentday=False):
		self.doPowerOffTimer.stop()
		self.wait_nextday = False
		self.dont_currentday = dont_currentday
		self.poweroff_time = self.nextday_time = -1
		if wait_nextday_time != -1 and isinstance(wait_nextday_time, int):
			self.wait_nextday_time = wait_nextday_time
		curtime = localtime(time())
		if curtime.tm_year > 1970:
			if self.timeHandler:
				self.timeHandler.m_timeUpdated.get().remove(self.powerStateTimerChanged)
				self.timeHandler = None
			if config.usage.poweroff_enabled.value:
				self.poweroff_time, self.nextday_time = self.isNextPoweroffTime()
				time_wait = math.trunc(self.poweroff_time - time())
				if self.poweroff_time != -1 and time_wait >= 0:
					print("[PowerOffTimer] Start power off timer (poweroff_time=%s, nextday_time=%s, time_wait=%s sec)" % (self.poweroff_time, self.nextday_time, time_wait))
					self.doPowerOffTimer.start(time_wait * 1000, True)

	def doPowerOffRun(self):
		if self.session:
			if self.wait_nextday:
				if time() >= self.nextday_time:
					print("[PowerOffTimer] Cancel waiting shutdown, over limit, set next day.")
					self.powerStateTimerChanged()
					return
			try_poweroff = True
			if isExternalToolsRunning():
				try_poweroff = False
			if RecordTimerEntry.wasInDeepStandby:
				try_poweroff = False
			if try_poweroff:
				if not self.session.nav.getRecordings():
					rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
					if rec_time > 0 and (rec_time - time()) < 360:
						try_poweroff = False
				else:
					try_poweroff = False
			if try_poweroff:
				jobs = len(job_manager.getPendingJobs())
				if Standby.inStandby is None:
					if not config.usage.poweroff_force.value:
						try_poweroff = False
				elif jobs or self.session.screen["TunerInfo"].tuner_use_mask or mediafilesInUse(self.session):
					try_poweroff = False
			if try_poweroff:
				if Standby.inStandby is None:
					reason = _("Power off timer") + '\n\n'
					if jobs:
						if jobs == 1:
							job = job_manager.getPendingJobs()[0]
							reason += "%s: %s (%d%%)\n" % (job.getStatustext(), job.name, int(100*job.progress/float(job.end)))
						else:
							reason += (ngettext("%d job is running in the background!", "%d jobs are running in the background!", jobs) % jobs) + '\n'
					if self.session.nav.getClientsStreaming():
						clients = ClientsStreaming("SHORT_ALL")
						reason += clients.getText() + '\n'
					if mediafilesInUse(self.session):
						reason += _("A file from media is in use!") + '\n'
					self.session.openWithCallback(self.doPowerOffAnswer, MessageBox, reason + _("Really shutdown now?"), type = MessageBox.TYPE_YESNO, timeout = 180)
				else:
					self.doPowerOffAnswer(True)
			else:
				print("[PowerOffTimer] Don't shutdown, box in use. Wait 5 min...")
				self.doPowerOffTimer.start(self.wait_nextday_time * 1000, True)
				self.wait_nextday = True

	def doPowerOffAnswer(self, answer):
		dont_currentday = time() > self.poweroff_time
		if answer:
			if not Standby.inTryQuitMainloop:
				print("[PowerOffTimer] Goto auto shutdown box.")
				if Standby.inStandby:
					RecordTimerEntry.TryQuitMainloop()
				else:
					AddNotificationWithID("Shutdown", Standby.TryQuitMainloop, 1)
					self.powerStateTimerChanged(dont_currentday=dont_currentday)
		else:
			print("[PowerOffTimer] Shutdown canceled by the user (dont_currentday=%s)" % dont_currentday)
			self.powerStateTimerChanged(dont_currentday=dont_currentday)

	def isNextPoweroffTime(self):
		if config.usage.poweroff_enabled.value:
			poweroff_day, poweroff_time, nextday_time = self.PoweroffDayTimeOfWeek()
			if poweroff_day == -1:
				return -1, -1
			elif poweroff_day == 0:
				return poweroff_time, nextday_time
			return poweroff_time + (86400 * poweroff_day), nextday_time
		return -1, -1

	def PoweroffDayTimeOfWeek(self):
		now = localtime()
		current_day = int(now.tm_wday)
		if current_day >= 0:
			if not self.dont_currentday and config.usage.poweroff_day[current_day].value:
				nextday_time = (int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.usage.poweroff_nextday.value[0], config.usage.poweroff_nextday.value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))) + 86400
				poweroff_time = int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.usage.poweroff_time[current_day].value[0], config.usage.poweroff_time[current_day].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
				if poweroff_time > time() and nextday_time > poweroff_time:
					return 0, poweroff_time, nextday_time
			for i in range(1,8):
				if config.usage.poweroff_day[(current_day+i)%7].value:
					nextday_time = (int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.usage.poweroff_nextday.value[0], config.usage.poweroff_nextday.value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))) + 86400 + (86400 * i)
					poweroff_time = int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.usage.poweroff_time[(current_day+i)%7].value[0], config.usage.poweroff_time[(current_day+i)%7].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
					return i, poweroff_time, nextday_time
		return -1, None, -1

powerOffTimer = PowerOffTimerPoller()
