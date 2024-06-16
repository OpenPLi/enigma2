from Screens.InfoBar import InfoBar
from Screens.Setup import Setup
from Components.config import config
from enigma import eEPGCache
from time import time, localtime, mktime


class SleepTimerEdit(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, yellow_button={'function': self.stopSleeptimer, 'helptext': _("Stop Sleeptimer")}, blue_button={'function': self.startSleeptimer, 'helptext': _("Start Sleeptimer")})
		self.skinName = ["SleepTimerSetup", "Setup"]
		self.setTitle(_("SleepTimer Configuration"))

	def createSetup(self):
		conflist = []
		if InfoBar.instance and InfoBar.instance.sleepTimer.isActive():
			statusSleeptimerText = _("(activated +%d min)") % InfoBar.instance.sleepTimerState()
			self["key_blue"].text = "" if config.usage.sleep_timer.value == "0" else _("Restart Sleeptimer")
			self["key_yellow"].text = _("Stop Sleeptimer")
		else:
			statusSleeptimerText = _("(not activated)")
			self["key_blue"].text = "" if config.usage.sleep_timer.value == "0" else _("Start Sleeptimer")
		conflist.append((_("Sleeptimer") + " " + statusSleeptimerText,
			config.usage.sleep_timer,
			_("Configure the duration in minutes for the sleeptimer. Select this entry and press blue to start/restart the sleeptimer or use yellow for stop active sleeptimer.")))
		conflist.append((_("Inactivity Sleeptimer"),
			config.usage.inactivity_timer,
			_("Configure the duration in hours the receiver should go to standby when the receiver is not controlled.")))
		if int(config.usage.inactivity_timer.value):
			conflist.append((_("Specify timeframe to ignore inactivity sleeptimer"),
				config.usage.inactivity_timer_blocktime,
				_("When enabled you can specify a timeframe when the inactivity sleeptimer is ignored. Not the detection is disabled during this timeframe but the inactivity timeout is disabled")))
			if config.usage.inactivity_timer_blocktime.value:
				conflist.append((_("Set blocktimes by weekday"),
					config.usage.inactivity_timer_blocktime_by_weekdays,
					_("Specify if you want to set the blocktimes separately by weekday")))
				if config.usage.inactivity_timer_blocktime_by_weekdays.value:
					for i in range(7):
						conflist.append(([_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")][i],
							config.usage.inactivity_timer_blocktime_day[i]))
						if config.usage.inactivity_timer_blocktime_day[i].value:
							conflist.append((_("Start time to ignore inactivity sleeptimer"),
								config.usage.inactivity_timer_blocktime_begin_day[i],
								_("Specify the start time when the inactivity sleeptimer should be ignored")))
							conflist.append((_("End time to ignore inactivity sleeptimer"),
								config.usage.inactivity_timer_blocktime_end_day[i],
								_("Specify the end time until the inactivity sleeptimer should be ignored")))
							conflist.append((_("Specify extra timeframe to ignore inactivity sleeptimer"),
								config.usage.inactivity_timer_blocktime_extra_day[i],
								_("When enabled you can specify an extra timeframe when the inactivity sleeptimer is ignored. Not the detection is disabled during this timeframe but the inactivity timeout is disabled")))
							if config.usage.inactivity_timer_blocktime_extra_day[i].value:
								conflist.append((_("Extra start time to ignore inactivity sleeptimer"),
									config.usage.inactivity_timer_blocktime_extra_begin_day[i],
									_("Specify the extra start time when the inactivity sleeptimer should be ignored")))
								conflist.append((_("Extra end time to ignore inactivity sleeptimer"),
									config.usage.inactivity_timer_blocktime_extra_end_day[i],
									_("Specify the extra end time until the inactivity sleeptimer should be ignored")))
				else:
					conflist.append((_("Start time to ignore inactivity sleeptimer"),
						config.usage.inactivity_timer_blocktime_begin,
						_("Specify the start time when the inactivity sleeptimer should be ignored")))
					conflist.append((_("End time to ignore inactivity sleeptimer"),
						config.usage.inactivity_timer_blocktime_end,
						_("Specify the end time until the inactivity sleeptimer should be ignored")))
					conflist.append((_("Specify extra timeframe to ignore inactivity sleeptimer"),
						config.usage.inactivity_timer_blocktime_extra,
						_("When enabled you can specify an extra timeframe when the inactivity sleeptimer is ignored. Not the detection is disabled during this timeframe but the inactivity timeout is disabled")))
					if config.usage.inactivity_timer_blocktime_extra.value:
						conflist.append((_("Extra start time to ignore inactivity sleeptimer"),
							config.usage.inactivity_timer_blocktime_extra_begin,
							_("Specify the extra start time when the inactivity sleeptimer should be ignored")))
						conflist.append((_("Extra end time to ignore inactivity sleeptimer"),
							config.usage.inactivity_timer_blocktime_extra_end,
							_("Specify the extra end time until the inactivity sleeptimer should be ignored")))
		conflist.append((_("Shutdown when in Standby"),
			config.usage.standby_to_shutdown_timer,
			_("Configure the duration when the receiver should go to shut down in case the receiver is in standby mode.")))
		if int(config.usage.standby_to_shutdown_timer.value):
			conflist.append((_("Specify timeframe to ignore the shutdown in standby"),
				config.usage.standby_to_shutdown_timer_blocktime,
				_("When enabled you can specify a timeframe to ignore the shutdown timer when the receiver is in standby mode")))
			if config.usage.standby_to_shutdown_timer_blocktime.value:
				conflist.append((_("Start time to ignore shutdown in standby"),
					config.usage.standby_to_shutdown_timer_blocktime_begin,
					_("Specify the start time to ignore the shutdown timer when the receiver is in standby mode")))
				conflist.append((_("End time to ignore shutdown in standby"),
					config.usage.standby_to_shutdown_timer_blocktime_end,
					_("Specify the end time to ignore the shutdown timer when the receiver is in standby mode")))
		conflist.append((_("Enable wakeup timer"),
			config.usage.wakeup_enabled,
			_("Note: when enabled, and you do want standby mode after wake up, set option 'Startup to Standby' as 'No, except Wakeup timer'.")))
		if config.usage.wakeup_enabled.value != "no":
			for i in range(7):
				conflist.append(([_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")][i],
					config.usage.wakeup_day[i]))
				if config.usage.wakeup_day[i].value:
					conflist.append((_("Wakeup time"),
						config.usage.wakeup_time[i]))
		conflist.append((_("Enable power off timer"),
			config.usage.poweroff_enabled,
			_("Automatically power off box to deep standby mode.")))
		if config.usage.poweroff_enabled.value:
			for i in range(7):
				conflist.append(([_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"), _("Saturday"), _("Sunday")][i],
					config.usage.poweroff_day[i]))
				if config.usage.poweroff_day[i].value:
					conflist.append((_("Power off time"),
						config.usage.poweroff_time[i]))
			conflist.append((_("Next day starts at"),
				config.usage.poweroff_nextday,
				_("If the box is supposed to enter deep standby e.g. monday night at 1 AM, it actually is already tuesday. To enable this anyway, differing next day start time can be specified here.")))
			conflist.append((_("Force power off (even when not in standby)"),
				config.usage.poweroff_force,
				_("Forces deep standby, even when not in standby mode. Scheduled recordings remain unaffected.")))
		self["config"].list = conflist

	def keySave(self):
		if self["config"].isChanged():
			from Components.PowerOffTimer import powerOffTimer
			powerOffTimer.powerStateTimerChanged(dont_currentday=powerOffTimer.getDontCurrentday())
			active_on = active_off = False
			for i in range(7):
				if config.usage.wakeup_day[i].value:
					active_on = True
				if config.usage.poweroff_day[i].value:
					active_off = True
			if not active_on:
				config.usage.wakeup_enabled.value = "no"
			if not active_off:
				config.usage.poweroff_enabled.value = False
			for x in self["config"].list:
				x[1].save()
		self.close()

	def startSleeptimer(self):
		if self["key_blue"].text:
			config.usage.sleep_timer.save()
			sleepTimer = config.usage.sleep_timer.value
			if sleepTimer == "event_standby":
				sleepTimer = self.currentEventTime()
			else:
				sleepTimer = int(sleepTimer)
			if sleepTimer or not self.getCurrentEntry().endswith(_("(not activated)")):
				InfoBar.instance and InfoBar.instance.setSleepTimer(sleepTimer)
			self.close(True)

	def stopSleeptimer(self):
		if self["key_yellow"].text:
			InfoBar.instance and InfoBar.instance.setSleepTimer(0)
			self.close(True)

	def currentEventTime(self):
		remaining = 0
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref:
			refstr = ref.toString()
			if "%3a//" not in refstr and refstr.rsplit(":", 1)[1].startswith("/"): # Movie
				service = self.session.nav.getCurrentService()
				seek = service and service.seek()
				if seek:
					length = seek.getLength()
					position = seek.getPlayPosition()
					if length and position:
						remaining = length[1] - position[1]
						if remaining > 0:
							remaining = remaining / 90000
			else: # DVB
				epg = eEPGCache.getInstance()
				event = epg.lookupEventTime(ref, -1, 0)
				if event:
					now = int(time())
					start = event.getBeginTime()
					duration = event.getDuration()
					end = start + duration
					remaining = end - now
		if remaining > 0:
			return remaining + config.recording.margin_after.value * 60
		return remaining


def isNextWakeupTime(standby_timer=False):
	wakeup_enabled = config.usage.wakeup_enabled.value
	if wakeup_enabled != "no":
		if not standby_timer:
			if wakeup_enabled == "standby":
				return -1
		else:
			if wakeup_enabled == "deepstandby":
				return -1
		wakeup_day, wakeup_time = WakeupDayTimeOfWeek()
		if wakeup_day == -1:
			return -1
		elif wakeup_day == 0:
			return wakeup_time
		return wakeup_time + (86400 * wakeup_day)
	return -1


def WakeupDayTimeOfWeek():
	now = localtime()
	current_day = int(now.tm_wday)
	if current_day >= 0:
		if config.usage.wakeup_day[current_day].value:
			wakeup_time = int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.usage.wakeup_time[current_day].value[0], config.usage.wakeup_time[current_day].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
			if wakeup_time > time():
				return 0, wakeup_time
		for i in range(1, 8):
			if config.usage.wakeup_day[(current_day + i) % 7].value:
				return i, int(mktime((now.tm_year, now.tm_mon, now.tm_mday, config.usage.wakeup_time[(current_day + i) % 7].value[0], config.usage.wakeup_time[(current_day + i) % 7].value[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
	return -1, None
