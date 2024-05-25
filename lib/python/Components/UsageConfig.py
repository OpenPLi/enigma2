from Components.Harddisk import harddiskmanager
from Components.Console import Console
from Components.config import ConfigSubsection, ConfigYesNo, config, ConfigSelection, ConfigText, ConfigNumber, ConfigSet, ConfigLocations, ConfigSelectionNumber, ConfigClock, ConfigSlider, ConfigEnableDisable, ConfigSubDict, ConfigDictionarySet, ConfigInteger, ConfigPassword, ConfigIP
from Tools.Directories import defaultRecordingLocation
from enigma import setTunerTypePriorityOrder, setPreferredTuner, setSpinnerOnOff, setEnableTtCachingOnOff, eEnv, eDVBDB, Misc_Options, eBackgroundFileEraser, eServiceEvent, eDVBLocalTimeHandler, eEPGCache
from Components.About import GetIPsFromNetworkInterfaces
from Components.NimManager import nimmanager
from Components.Renderer.FrontpanelLed import ledPatterns, PATTERN_ON, PATTERN_OFF, PATTERN_BLINK
from Components.ServiceList import refreshServiceList, redrawServiceList
from Components.SystemInfo import BoxInfo
import os
import time


originalAudioTracks = "orj dos ory org esl qaa qaf und mis mul ORY ORJ Audio_ORJ oth"
visuallyImpairedCommentary = "NAR qad"


def InitUsageConfig():
	config.usage = ConfigSubsection()
	config.usage.subnetwork = ConfigYesNo(default=True)
	config.usage.subnetwork_cable = ConfigYesNo(default=True)
	config.usage.subnetwork_terrestrial = ConfigYesNo(default=True)
	config.usage.showdish = ConfigYesNo(default=True)
	config.usage.multibouquet = ConfigYesNo(default=True)

	showrotorpositionChoicesUpdate()

	config.usage.alternative_number_mode = ConfigYesNo(default=False)

	def alternativeNumberModeChange(configElement):
		eDVBDB.getInstance().setNumberingMode(configElement.value)
		refreshServiceList()
	config.usage.alternative_number_mode.addNotifier(alternativeNumberModeChange)

	config.usage.servicelist_twolines = ConfigSelection(default="0", choices=[("0", _("None")), ("1", _("Two lines")), ("2", _("Two lines and next event"))])
	config.usage.servicelist_twolines.addNotifier(redrawServiceList, initial_call=False)

	config.usage.hide_number_markers = ConfigYesNo(default=True)
	config.usage.hide_number_markers.addNotifier(redrawServiceList, initial_call=False)

	config.usage.servicetype_icon_mode = ConfigSelection(default="0", choices=[("0", _("None")), ("1", _("Left from servicename")), ("2", _("Right from servicename"))])
	config.usage.servicetype_icon_mode.addNotifier(redrawServiceList, initial_call=False)
	config.usage.crypto_icon_mode = ConfigSelection(default="0", choices=[("0", _("None")), ("1", _("Left from servicename")), ("2", _("Right from servicename"))])
	config.usage.crypto_icon_mode.addNotifier(redrawServiceList, initial_call=False)
	config.usage.record_indicator_mode = ConfigSelection(default="0", choices=[("0", _("None")), ("1", _("Left from servicename")), ("2", _("Right from servicename")), ("3", _("Red colored"))])
	config.usage.record_indicator_mode = ConfigSelection(default="3", choices=[("0", _("None")), ("1", _("Left from servicename")), ("2", _("Right from servicename")), ("3", _("Red colored"))])
	config.usage.record_indicator_mode.addNotifier(redrawServiceList, initial_call=False)

	choicelist = [("-1", _("Disable"))]
	for i in range(0, 1300, 100):
		choicelist.append((str(i), ngettext("%d pixel wide", "%d pixels wide", i) % i))
	config.usage.servicelist_column = ConfigSelection(default="-1", choices=choicelist)
	config.usage.servicelist_column.addNotifier(redrawServiceList, initial_call=False)

	config.usage.service_icon_enable = ConfigYesNo(default=False)
	config.usage.service_icon_enable.addNotifier(redrawServiceList, initial_call=False)
	config.usage.servicelist_cursor_behavior = ConfigSelection(default="keep", choices=[
		("standard", _("Standard")),
		("keep", _("Keep service")),
		("reverseB", _("Reverse bouquet buttons")),
		("keep reverseB", _("Keep service") + " + " + _("Reverse bouquet buttons"))])
	
	config.usage.servicenum_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.usage.servicenum_fontsize.addNotifier(redrawServiceList, initial_call=False)
	config.usage.servicename_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.usage.servicename_fontsize.addNotifier(redrawServiceList, initial_call=False)
	config.usage.serviceinfo_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.usage.serviceinfo_fontsize.addNotifier(redrawServiceList, initial_call=False)

	choicelist = [(0, _("Use skin default"))] + [(i, "%d" % i) for i in range(5, 41)]
	config.usage.servicelist_number_of_services = ConfigSelection(default=0, choices=choicelist)
	config.usage.servicelist_number_of_services.addNotifier(redrawServiceList, initial_call=False)

	config.usage.multiepg_ask_bouquet = ConfigYesNo(default=False)

	config.usage.quickzap_bouquet_change = ConfigYesNo(default=False)
	config.usage.e1like_radio_mode = ConfigYesNo(default=True)
	config.usage.e1like_radio_mode_last_play = ConfigYesNo(default=True)
	choicelist = [("0", _("No timeout"))]
	for i in range(1, 12):
		choicelist.append((str(i), ngettext("%d second", "%d seconds", i) % i))
	config.usage.infobar_timeout = ConfigSelection(default="5", choices=choicelist)
	config.usage.show_infobar_on_zap = ConfigYesNo(default=True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default=True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default=False)
	config.usage.show_second_infobar = ConfigSelection(default="0", choices=[("", _("None"))] + choicelist + [("EPG", _("EPG"))])
	config.usage.show_simple_second_infobar = ConfigYesNo(default=False)
	config.usage.show_infobar_adds = ConfigYesNo(default=False)
	config.usage.infobar_frontend_source = ConfigSelection(default="settings", choices=[("settings", _("Settings")), ("tuner", _("Tuner"))])
	config.usage.oldstyle_zap_controls = ConfigYesNo(default=False)
	config.usage.oldstyle_channel_select_controls = ConfigYesNo(default=False)
	config.usage.zap_with_ch_buttons = ConfigYesNo(default=False)
	config.usage.ok_is_channelselection = ConfigYesNo(default=False)
	config.usage.changebouquet_set_history = ConfigYesNo(default=False)
	config.usage.volume_instead_of_channelselection = ConfigYesNo(default=False)
	config.usage.channelselection_preview = ConfigYesNo(default=False)
	config.usage.show_spinner = ConfigYesNo(default=True)
	config.usage.menu_sort_weight = ConfigDictionarySet(default={"mainmenu": {"submenu": {}}})
	config.usage.menu_sort_mode = ConfigSelection(default="default", choices=[("a_z", _("alphabetical")), ("default", _("Default")), ("user", _("user defined")), ("user_hidden", _("user defined hidden"))])
	config.usage.menu_show_numbers = ConfigSelection(default="no", choices=[("no", _("no")), ("menu&plugins", _("in menu and plugins")), ("menu", _("in menu only")), ("plugins", _("in plugins only"))])
	config.usage.showScreenPath = ConfigSelection(default="small", choices=[("off", _("Disabled")), ("small", _("Small")), ("large", _("Large"))])
	config.usage.enable_tt_caching = ConfigYesNo(default=True)
	config.usage.sort_settings = ConfigYesNo(default=False)
	choicelist = []
	for i in (10, 30):
		choicelist.append((str(i), ngettext("%d second", "%d seconds", i) % i))
	for i in (60, 120, 300, 600, 1200, 1800):
		m = i / 60
		choicelist.append((str(i), ngettext("%d minute", "%d minutes", m) % m))
	for i in (3600, 7200, 14400):
		h = i / 3600
		choicelist.append((str(i), ngettext("%d hour", "%d hours", h) % h))
	config.usage.hdd_standby = ConfigSelection(default="300", choices=[("0", _("No standby"))] + choicelist)
	config.usage.output_12V = ConfigSelection(default="do not change", choices=[
		("do not change", _("Do not change")), ("off", _("Off")), ("on", _("On"))])

	config.usage.pip_zero_button = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")), ("swap", _("Swap PiP and main picture")),
		("swapstop", _("Move PiP to main picture")), ("stop", _("Stop PiP"))])
	config.usage.pip_hideOnExit = ConfigSelection(default="without popup", choices=[
		("no", _("no")), ("popup", _("With popup")), ("without popup", _("Without popup"))])
	choicelist = [("-1", _("Disabled")), ("0", _("No timeout"))]
	for i in [60, 300, 600, 900, 1800, 2700, 3600]:
		m = i / 60
		choicelist.append((str(i), ngettext("%d minute", "%d minutes", m) % m))
	config.usage.pip_last_service_timeout = ConfigSelection(default="0", choices=choicelist)

	config.usage.default_path = ConfigText(default="")
	config.usage.timer_path = ConfigText(default="<default>")
	config.usage.instantrec_path = ConfigText(default="<default>")
	config.usage.timeshift_path = ConfigText(default="/media/hdd/")
	config.usage.allowed_timeshift_paths = ConfigLocations(default=["/media/hdd/"])
	config.usage.timeshift_skipreturntolive = ConfigYesNo(default=False)
	config.usage.movielist_trashcan = ConfigYesNo(default=True)
	config.usage.movielist_trashcan_days = ConfigNumber(default=8)
	config.usage.movielist_trashcan_reserve = ConfigNumber(default=40)
	config.usage.on_movie_start = ConfigSelection(default="resume", choices=[
		("ask yes", _("Ask user") + " " + _("default") + " " + _("yes")),
		("ask no", _("Ask user") + " " + _("default") + " " + _("no")),
		("resume", _("Resume from last position")),
		("beginning", _("Start from the beginning"))])
	config.usage.on_movie_stop = ConfigSelection(default="movielist", choices=[
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service"))])
	config.usage.on_movie_eof = ConfigSelection(default="movielist", choices=[
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")), ("pause", _("Pause movie at end")), ("playlist", _("Play next (return to movie list)")),
		("playlistquit", _("Play next (return to previous service)")), ("loop", _("Continuous play (loop)")), ("repeatcurrent", _("Repeat"))])
	config.usage.next_movie_msg = ConfigYesNo(default=True)
	config.usage.last_movie_played = ConfigText()
	config.usage.leave_movieplayer_onExit = ConfigSelection(default="popup", choices=[
		("no", _("no")), ("popup", _("With popup")), ("without popup", _("Without popup")), ("movielist", _("Return to movie list"))])

	config.usage.setup_level = ConfigSelection(default="simple", choices=[
		("simple", _("Normal")),
		("intermediate", _("Advanced")),
		("expert", _("Expert"))])

	config.usage.startup_to_standby = ConfigSelection(default="no", choices=[
		("no", _("no")),
		("yes", _("yes")),
		("except", _("No, except Wakeup timer"))])

	config.usage.wakeup_enabled = ConfigSelection(default="no", choices=[
		("no", _("no")),
		("yes", _("yes")),
		("standby", _("Yes, only from standby")),
		("deepstandby", _("Yes, only from deep standby"))])
	config.usage.wakeup_day = ConfigSubDict()
	config.usage.wakeup_time = ConfigSubDict()
	for i in range(7):
		config.usage.wakeup_day[i] = ConfigEnableDisable(default=False)
		config.usage.wakeup_time[i] = ConfigClock(default=((6 * 60 + 0) * 60))

	config.usage.poweroff_enabled = ConfigYesNo(default=False)
	config.usage.poweroff_force = ConfigYesNo(default=False)
	config.usage.poweroff_nextday = ConfigClock(default=((6 * 60 + 0) * 60))
	config.usage.poweroff_day = ConfigSubDict()
	config.usage.poweroff_time = ConfigSubDict()
	for i in range(7):
		config.usage.poweroff_day[i] = ConfigEnableDisable(default=False)
		config.usage.poweroff_time[i] = ConfigClock(default=((1 * 60 + 0) * 60))

	choicelist = [("0", _("Do nothing")), ("1800", _("Standby in ") + _("half an hour"))]
	for i in range(3600, 21601, 3600):
		h = abs(i / 3600)
		h = ngettext("%d hour", "%d hours", h) % h
		choicelist.append((str(i), _("Standby in ") + h))
	config.usage.inactivity_timer = ConfigSelection(default="0", choices=choicelist)
	config.usage.inactivity_timer_blocktime = ConfigYesNo(default=True)
	config.usage.inactivity_timer_blocktime_begin = ConfigClock(default=time.mktime((1970, 1, 1, 18, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_end = ConfigClock(default=time.mktime((1970, 1, 1, 23, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_extra = ConfigYesNo(default=False)
	config.usage.inactivity_timer_blocktime_extra_begin = ConfigClock(default=time.mktime((1970, 1, 1, 6, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_extra_end = ConfigClock(default=time.mktime((1970, 1, 1, 9, 0, 0, 0, 0, 0)))
	config.usage.inactivity_timer_blocktime_by_weekdays = ConfigYesNo(default=False)
	config.usage.inactivity_timer_blocktime_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_begin_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_end_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_extra_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_extra_begin_day = ConfigSubDict()
	config.usage.inactivity_timer_blocktime_extra_end_day = ConfigSubDict()
	for i in range(7):
		config.usage.inactivity_timer_blocktime_day[i] = ConfigYesNo(default=False)
		config.usage.inactivity_timer_blocktime_begin_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 18, 0, 0, 0, 0, 0)))
		config.usage.inactivity_timer_blocktime_end_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 23, 0, 0, 0, 0, 0)))
		config.usage.inactivity_timer_blocktime_extra_day[i] = ConfigYesNo(default=False)
		config.usage.inactivity_timer_blocktime_extra_begin_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 6, 0, 0, 0, 0, 0)))
		config.usage.inactivity_timer_blocktime_extra_end_day[i] = ConfigClock(default=time.mktime((1970, 1, 1, 9, 0, 0, 0, 0, 0)))

	choicelist = [("0", _("Disabled")), ("event_standby", _("Standby after current event"))]
	for i in range(900, 7201, 900):
		m = abs(i / 60)
		m = ngettext("%d minute", "%d minutes", m) % m
		choicelist.append((str(i), _("Standby in ") + m))
	config.usage.sleep_timer = ConfigSelection(default="0", choices=choicelist)

	choicelist = [("0", _("Disabled"))]
	for i in [300, 600] + list(range(900, 14401, 900)):
		m = abs(i / 60)
		m = ngettext("%d minute", "%d minutes", m) % m
		choicelist.append((str(i), _("after ") + m))
	config.usage.standby_to_shutdown_timer = ConfigSelection(default="0", choices=choicelist)
	config.usage.standby_to_shutdown_timer_blocktime = ConfigYesNo(default=False)
	config.usage.standby_to_shutdown_timer_blocktime_begin = ConfigClock(default=time.mktime((1970, 1, 1, 6, 0, 0, 0, 0, 0)))
	config.usage.standby_to_shutdown_timer_blocktime_end = ConfigClock(default=time.mktime((1970, 1, 1, 23, 0, 0, 0, 0, 0)))

	choicelist = [("0", _("Disabled"))]
	for m in (1, 5, 10, 15, 30, 60):
		choicelist.append((str(m * 60), ngettext("%d minute", "%d minutes", m) % m))
	config.usage.screen_saver = ConfigSelection(default="300", choices=choicelist)

	config.usage.check_timeshift = ConfigYesNo(default=True)

	choicelist = [("0", _("Disabled"))]
	for i in (2, 3, 4, 5, 10, 20, 30):
		choicelist.append((str(i), ngettext("%d second", "%d seconds", i) % i))
	for i in (60, 120, 300):
		m = i / 60
		choicelist.append((str(i), ngettext("%d minute", "%d minutes", m) % m))
	config.usage.timeshift_start_delay = ConfigSelection(default="0", choices=choicelist)

	config.usage.alternatives_priority = ConfigSelection(default="0", choices=[
		("0", "DVB-S/-C/-T"),
		("1", "DVB-S/-T/-C"),
		("2", "DVB-C/-S/-T"),
		("3", "DVB-C/-T/-S"),
		("4", "DVB-T/-C/-S"),
		("5", "DVB-T/-S/-C"),
		("127", _("No priority"))])

	def remote_fallback_changed(configElement):
		if configElement.value:
			configElement.value = "%s%s" % (not configElement.value.startswith("http://") and "http://" or "", configElement.value)
			configElement.value = "%s%s" % (configElement.value, configElement.value.count(":") == 1 and ":8001" or "")
	config.usage.remote_fallback_enabled = ConfigYesNo(default=False)
	config.usage.remote_fallback = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_import_url = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_import_url.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_alternative = ConfigYesNo(default=False)
	config.usage.remote_fallback_dvb_t = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_dvb_t.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_dvb_c = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_dvb_c.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_atsc = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_atsc.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_import = ConfigSelection(default="", choices=[("", _("No")), ("channels", _("Channels only")), ("channels_epg", _("Channels and EPG")), ("epg", _("EPG only"))])
	config.usage.remote_fallback_import_restart = ConfigYesNo(default=False)
	config.usage.remote_fallback_import_standby = ConfigYesNo(default=False)
	config.usage.remote_fallback_ok = ConfigYesNo(default=False)
	config.usage.remote_fallback_nok = ConfigYesNo(default=False)
	config.usage.remote_fallback_extension_menu = ConfigYesNo(default=False)
	config.usage.remote_fallback_external_timer = ConfigYesNo(default=False)
	config.usage.remote_fallback_external_timer_default = ConfigYesNo(default=True)
	config.usage.remote_fallback_openwebif_customize = ConfigYesNo(default=False)
	config.usage.remote_fallback_openwebif_userid = ConfigText(default="root")
	config.usage.remote_fallback_openwebif_password = ConfigPassword(default="default")
	config.usage.remote_fallback_openwebif_port = ConfigInteger(default=80, limits=(0, 65535))
	config.usage.remote_fallback_dvbt_region = ConfigText(default="fallback DVB-T/T2 Europe")

	choicelist = [("0", _("Disabled"))]
	for i in (10, 50, 100, 500, 1000, 2000):
		choicelist.append(("%d" % i, _("%d ms") % i))

	config.usage.http_startdelay = ConfigSelection(default="0", choices=choicelist)

	config.usage.show_timer_conflict_warning = ConfigYesNo(default=True)

	preferredTunerChoicesUpdate()

	config.misc.disable_background_scan = ConfigYesNo(default=False)
	config.misc.use_ci_assignment = ConfigYesNo(default=False)
	config.usage.show_event_progress_in_servicelist = ConfigSelection(default='barright', choices=[
		('barleft', _("Progress bar left")),
		('barright', _("Progress bar right")),
		('percleft', _("Percentage left")),
		('percright', _("Percentage right")),
		('no', _("No"))])
	config.usage.show_channel_numbers_in_servicelist = ConfigYesNo(default=True)
	config.usage.show_event_progress_in_servicelist.addNotifier(redrawServiceList, initial_call=False)
	config.usage.show_channel_numbers_in_servicelist.addNotifier(redrawServiceList, initial_call=False)

	config.usage.blinking_display_clock_during_recording = ConfigYesNo(default=False)

	config.usage.show_message_when_recording_starts = ConfigYesNo(default=True)

	config.usage.load_length_of_movies_in_moviellist = ConfigYesNo(default=True)
	config.usage.show_icons_in_movielist = ConfigSelection(default='i', choices=[
		('o', _("Off")),
		('p', _("Progress")),
		('s', _("Small progress")),
		('i', _("Icons")),
	])
	config.usage.movielist_unseen = ConfigYesNo(default=False)

	config.usage.swap_snr_on_osd = ConfigYesNo(default=False)

	def SpinnerOnOffChanged(configElement):
		setSpinnerOnOff(int(configElement.value))
	config.usage.show_spinner.addNotifier(SpinnerOnOffChanged)

	def EnableTtCachingChanged(configElement):
		setEnableTtCachingOnOff(int(configElement.value))
	config.usage.enable_tt_caching.addNotifier(EnableTtCachingChanged)

	def TunerTypePriorityOrderChanged(configElement):
		setTunerTypePriorityOrder(int(configElement.value))
	config.usage.alternatives_priority.addNotifier(TunerTypePriorityOrderChanged, immediate_feedback=False)

	def PreferredTunerChanged(configElement):
		setPreferredTuner(int(configElement.value))
	config.usage.frontend_priority.addNotifier(PreferredTunerChanged)

	config.usage.show_picon_in_display = ConfigYesNo(default=True)
	config.usage.hide_zap_errors = ConfigYesNo(default=False)
	config.usage.show_cryptoinfo = ConfigYesNo(default=True)
	config.usage.show_eit_nownext = ConfigYesNo(default=True)
	config.usage.show_vcr_scart = ConfigYesNo(default=False)
	config.usage.show_update_disclaimer = ConfigYesNo(default=True)
	config.usage.pic_resolution = ConfigSelection(default=None, choices=[(None, _("Same resolution as skin")), ("(720, 576)", "720x576"), ("(1280, 720)", "1280x720"), ("(1920, 1080)", "1920x1080")][:BoxInfo.getItem("HasFullHDSkinSupport") and 4 or 3])

	if BoxInfo.getItem("Fan"):
		choicelist = [('off', _("Off")), ('on', _("On")), ('auto', _("Auto"))]
		if os.path.exists("/proc/stb/fp/fan_choices"):
			choicelist = [x for x in choicelist if x[0] in open("/proc/stb/fp/fan_choices", "r").read().strip().split(" ")]
		config.usage.fan = ConfigSelection(choicelist)

		def fanChanged(configElement):
			open(BoxInfo.getItem("Fan"), "w").write(configElement.value)
		config.usage.fan.addNotifier(fanChanged)

	if BoxInfo.getItem("FanPWM"):
		def fanSpeedChanged(configElement):
			open(BoxInfo.getItem("FanPWM"), "w").write(hex(configElement.value)[2:])
		config.usage.fanspeed = ConfigSlider(default=127, increment=8, limits=(0, 255))
		config.usage.fanspeed.addNotifier(fanSpeedChanged)

	if BoxInfo.getItem("PowerLED"):
		def powerLEDChanged(configElement):
			if "fp" in BoxInfo.getItem("PowerLED"):
				open(BoxInfo.getItem("PowerLED"), "w").write(configElement.value and "1" or "0")
				patterns = [PATTERN_ON, PATTERN_ON, PATTERN_OFF, PATTERN_ON] if configElement.value else [PATTERN_OFF, PATTERN_OFF, PATTERN_OFF, PATTERN_OFF]
				ledPatterns.setLedPatterns(1, patterns)
			else:
				open(BoxInfo.getItem("PowerLED"), "w").write(configElement.value and "on" or "off")
		config.usage.powerLED = ConfigYesNo(default=True)
		config.usage.powerLED.addNotifier(powerLEDChanged)

	if BoxInfo.getItem("StandbyLED"):
		def standbyLEDChanged(configElement):
			if "fp" in BoxInfo.getItem("StandbyLED"):
				patterns = [PATTERN_OFF, PATTERN_BLINK, PATTERN_ON, PATTERN_BLINK] if configElement.value else [PATTERN_OFF, PATTERN_OFF, PATTERN_OFF, PATTERN_OFF]
				ledPatterns.setLedPatterns(0, patterns)
			else:
				open(BoxInfo.getItem("StandbyLED"), "w").write(configElement.value and "on" or "off")
		config.usage.standbyLED = ConfigYesNo(default=True)
		config.usage.standbyLED.addNotifier(standbyLEDChanged)

	if BoxInfo.getItem("SuspendLED"):
		def suspendLEDChanged(configElement):
			if "fp" in BoxInfo.getItem("SuspendLED"):
				open(BoxInfo.getItem("SuspendLED"), "w").write(configElement.value and "1" or "0")
			else:
				open(BoxInfo.getItem("SuspendLED"), "w").write(configElement.value and "on" or "off")
		config.usage.suspendLED = ConfigYesNo(default=True)
		config.usage.suspendLED.addNotifier(suspendLEDChanged)

	if BoxInfo.getItem("PowerOffDisplay"):
		def powerOffDisplayChanged(configElement):
			open(BoxInfo.getItem("PowerOffDisplay"), "w").write(configElement.value and "1" or "0")
		config.usage.powerOffDisplay = ConfigYesNo(default=True)
		config.usage.powerOffDisplay.addNotifier(powerOffDisplayChanged)

	if BoxInfo.getItem("LCDshow_symbols"):
		def lcdShowSymbols(configElement):
			open(BoxInfo.getItem("LCDshow_symbols"), "w").write(configElement.value and "1" or "0")
		config.usage.lcd_show_symbols = ConfigYesNo(default=True)
		config.usage.lcd_show_symbols.addNotifier(lcdShowSymbols)

	if BoxInfo.getItem("WakeOnLAN"):
		f = open(BoxInfo.getItem("WakeOnLAN"), "r")
		status = f.read().strip()
		f.close()

		def wakeOnLANChanged(configElement):
			if status in ("enable", "disable"):
				open(BoxInfo.getItem("WakeOnLAN"), "w").write(configElement.value and "enable" or "disable")
			else:
				open(BoxInfo.getItem("WakeOnLAN"), "w").write(configElement.value and "on" or "off")
		config.usage.wakeOnLAN = ConfigYesNo(default=False)
		config.usage.wakeOnLAN.addNotifier(wakeOnLANChanged)

	if BoxInfo.getItem("hasXcoreVFD"):
		def set12to8characterVFD(configElement):
			open(BoxInfo.getItem("hasXcoreVFD"), "w").write(not configElement.value and "1" or "0")
		config.usage.toggle12to8characterVFD = ConfigYesNo(default=False)
		config.usage.toggle12to8characterVFD.addNotifier(set12to8characterVFD)

	if BoxInfo.getItem("LcdLiveTVMode"):
		def setLcdLiveTVMode(configElement):
			open(BoxInfo.getItem("LcdLiveTVMode"), "w").write(configElement.value)
		config.usage.LcdLiveTVMode = ConfigSelection(default="0", choices=[str(x) for x in range(0, 9)])
		config.usage.LcdLiveTVMode.addNotifier(setLcdLiveTVMode)

	if BoxInfo.getItem("LcdLiveDecoder"):
		def setLcdLiveDecoder(configElement):
			open(BoxInfo.getItem("LcdLiveDecoder"), "w").write(configElement.value)
		config.usage.LcdLiveDecoder = ConfigSelection(default="0", choices=[str(x) for x in range(0, 4)])
		config.usage.LcdLiveDecoder.addNotifier(setLcdLiveDecoder)

	config.usage.boolean_graphic = ConfigSelection(default="true", choices={"false": _("no"), "true": _("yes"), "only_bool": _("yes, but not in multi selections")})

	config.usage.multiboot_order = ConfigYesNo(default=True)

	config.usage.setupShowDefault = ConfigSelection(default="spaces", choices=[
		("", _("Don't show default")),
		("spaces", _("Show default after description")),
		("newline", _("Show default on new line"))
	])

	config.epg = ConfigSubsection()
	config.epg.eit = ConfigYesNo(default=True)
	config.epg.mhw = ConfigYesNo(default=False)
	config.epg.freesat = ConfigYesNo(default=True)
	config.epg.viasat = ConfigYesNo(default=True)
	config.epg.netmed = ConfigYesNo(default=True)
	config.epg.virgin = ConfigYesNo(default=False)
	config.epg.opentv = ConfigYesNo(default=False)
	config.misc.showradiopic = ConfigYesNo(default=True)

	def EpgSettingsChanged(configElement):
		from enigma import eEPGCache
		mask = 0xffffffff
		if not config.epg.eit.value:
			mask &= ~(eEPGCache.NOWNEXT | eEPGCache.SCHEDULE | eEPGCache.SCHEDULE_OTHER)
		if not config.epg.mhw.value:
			mask &= ~eEPGCache.MHW
		if not config.epg.freesat.value:
			mask &= ~(eEPGCache.FREESAT_NOWNEXT | eEPGCache.FREESAT_SCHEDULE | eEPGCache.FREESAT_SCHEDULE_OTHER)
		if not config.epg.viasat.value:
			mask &= ~eEPGCache.VIASAT
		if not config.epg.netmed.value:
			mask &= ~(eEPGCache.NETMED_SCHEDULE | eEPGCache.NETMED_SCHEDULE_OTHER)
		if not config.epg.virgin.value:
			mask &= ~(eEPGCache.VIRGIN_NOWNEXT | eEPGCache.VIRGIN_SCHEDULE)
		if not config.epg.opentv.value:
			mask &= ~eEPGCache.OPENTV
		eEPGCache.getInstance().setEpgSources(mask)
	config.epg.eit.addNotifier(EpgSettingsChanged)
	config.epg.mhw.addNotifier(EpgSettingsChanged)
	config.epg.freesat.addNotifier(EpgSettingsChanged)
	config.epg.viasat.addNotifier(EpgSettingsChanged)
	config.epg.netmed.addNotifier(EpgSettingsChanged)
	config.epg.virgin.addNotifier(EpgSettingsChanged)
	config.epg.opentv.addNotifier(EpgSettingsChanged)

	config.epg.histminutes = ConfigSelectionNumber(min=0, max=120, stepwidth=15, default=0, wraparound=True)

	def EpgHistorySecondsChanged(configElement):
		from enigma import eEPGCache
		eEPGCache.getInstance().setEpgHistorySeconds(config.epg.histminutes.getValue() * 60)
	config.epg.histminutes.addNotifier(EpgHistorySecondsChanged)

	choicelist = [("newline", _("new line")), ("2newlines", _("2 new lines")), ("space", _("space")), ("dot", " . "), ("dash", " - "), ("asterisk", " * "), ("nothing", _("nothing"))]
	config.epg.fulldescription_separator = ConfigSelection(default="2newlines", choices=choicelist)
	choicelist = [("no", _("no")), ("nothing", _("omit")), ("space", _("space")), ("dot", ". "), ("dash", " - "), ("asterisk", " * "), ("hashtag", " # ")]
	config.epg.replace_newlines = ConfigSelection(default="no", choices=choicelist)

	def correctInvalidEPGDataChange(configElement):
		eServiceEvent.setUTF8CorrectMode(int(configElement.value))
	config.epg.correct_invalid_epgdata = ConfigSelection(default="1", choices=[("0", _("Disabled")), ("1", _("Enabled")), ("2", _("Debug"))])
	config.epg.correct_invalid_epgdata.addNotifier(correctInvalidEPGDataChange)

	def setHDDStandby(configElement):
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(configElement.value))
	config.usage.hdd_standby.addNotifier(setHDDStandby, immediate_feedback=False)

	if BoxInfo.getItem("12V_Output"):
		def set12VOutput(configElement):
			Misc_Options.getInstance().set_12V_output(configElement.value == "on" and 1 or 0)
		config.usage.output_12V.addNotifier(set12VOutput, immediate_feedback=False)

	config.usage.keymap = ConfigText(default=eEnv.resolve("${datadir}/enigma2/keymap.xml"))
	keytranslation = eEnv.resolve("${sysconfdir}/enigma2/keytranslation.xml")
	if not os.path.exists(keytranslation):
		keytranslation = eEnv.resolve("${datadir}/enigma2/keytranslation.xml")
	config.usage.keytrans = ConfigText(default=keytranslation)
	config.usage.alternative_imagefeed = ConfigText(default="", fixed_size=False)

	config.seek = ConfigSubsection()
	config.seek.selfdefined_13 = ConfigNumber(default=15)
	config.seek.selfdefined_46 = ConfigNumber(default=60)
	config.seek.selfdefined_79 = ConfigNumber(default=300)

	config.seek.speeds_forward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_backward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_slowmotion = ConfigSet(default=[2, 4, 8], choices=[2, 4, 6, 8, 12, 16, 25])

	config.seek.enter_forward = ConfigSelection(default="2", choices=["2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])
	config.seek.enter_backward = ConfigSelection(default="1", choices=["1", "2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])

	config.seek.on_pause = ConfigSelection(default="play", choices=[
		("play", _("Play")),
		("step", _("Single step (GOP)")),
		("last", _("Last speed"))])

	config.usage.timerlist_finished_timer_position = ConfigSelection(default="end", choices=[("beginning", _("At beginning")), ("end", _("At end"))])

	def updateEnterForward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_forward, configElement.value)

	config.seek.speeds_forward.addNotifier(updateEnterForward, immediate_feedback=False)

	def updateEnterBackward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_backward, configElement.value)

	config.seek.speeds_backward.addNotifier(updateEnterBackward, immediate_feedback=False)

	def updateEraseSpeed(el):
		eBackgroundFileEraser.getInstance().setEraseSpeed(int(el.value))

	def updateEraseFlags(el):
		eBackgroundFileEraser.getInstance().setEraseFlags(int(el.value))
	config.misc.erase_speed = ConfigSelection(default="20", choices=[
		("10", _("10 MB/s")),
		("20", _("20 MB/s")),
		("50", _("50 MB/s")),
		("100", _("100 MB/s"))])
	config.misc.erase_speed.addNotifier(updateEraseSpeed, immediate_feedback=False)
	config.misc.erase_flags = ConfigSelection(default="1", choices=[
		("0", _("Disable")),
		("1", _("Internal hdd only")),
		("3", _("Everywhere"))])
	config.misc.erase_flags.addNotifier(updateEraseFlags, immediate_feedback=False)

	if BoxInfo.getItem("ZapMode"):
		def setZapmode(el):
			open(BoxInfo.getItem("ZapMode"), "w").write(el.value)
		config.misc.zapmode = ConfigSelection(default="mute", choices=[
			("mute", _("Black screen")), ("hold", _("Hold screen")), ("mutetilllock", _("Black screen till locked")), ("holdtilllock", _("Hold till locked"))])
		config.misc.zapmode.addNotifier(setZapmode, immediate_feedback=False)

	if BoxInfo.getItem("VFD_scroll_repeats"):
		def scroll_repeats(el):
			open(BoxInfo.getItem("VFD_scroll_repeats"), "w").write(el.value)
		choicelist = []
		for i in range(1, 11, 1):
			choicelist.append((str(i)))
		config.usage.vfd_scroll_repeats = ConfigSelection(default="3", choices=choicelist)
		config.usage.vfd_scroll_repeats.addNotifier(scroll_repeats, immediate_feedback=False)

	if BoxInfo.getItem("VFD_scroll_delay"):
		def scroll_delay(el):
			open(BoxInfo.getItem("VFD_scroll_delay"), "w").write(el.value)
		choicelist = []
		for i in range(0, 1001, 50):
			choicelist.append((str(i)))
		config.usage.vfd_scroll_delay = ConfigSelection(default="150", choices=choicelist)
		config.usage.vfd_scroll_delay.addNotifier(scroll_delay, immediate_feedback=False)

	if BoxInfo.getItem("VFD_initial_scroll_delay"):
		def initial_scroll_delay(el):
			open(BoxInfo.getItem("VFD_initial_scroll_delay"), "w").write(el.value)
		choicelist = []
		for i in range(0, 20001, 500):
			choicelist.append((str(i)))
		config.usage.vfd_initial_scroll_delay = ConfigSelection(default="1000", choices=choicelist)
		config.usage.vfd_initial_scroll_delay.addNotifier(initial_scroll_delay, immediate_feedback=False)

	if BoxInfo.getItem("VFD_final_scroll_delay"):
		def final_scroll_delay(el):
			open(BoxInfo.getItem("VFD_final_scroll_delay"), "w").write(el.value)
		choicelist = []
		for i in range(0, 20001, 500):
			choicelist.append((str(i)))
		config.usage.vfd_final_scroll_delay = ConfigSelection(default="1000", choices=choicelist)
		config.usage.vfd_final_scroll_delay.addNotifier(final_scroll_delay, immediate_feedback=False)

	config.subtitles = ConfigSubsection()
	config.subtitles.show = ConfigYesNo(default=True)
	config.subtitles.ttx_subtitle_colors = ConfigSelection(default="1", choices=[
		("0", _("original")),
		("1", _("white")),
		("2", _("yellow"))])
	config.subtitles.ttx_subtitle_original_position = ConfigYesNo(default=False)
	config.subtitles.subtitle_position = ConfigSelection(default="50", choices=["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "150", "200", "250", "300", "350", "400", "450"])
	config.subtitles.subtitle_alignment = ConfigSelection(default="center", choices=[("left", _("left")), ("center", _("center")), ("right", _("right"))])
	config.subtitles.subtitle_rewrap = ConfigYesNo(default=False)
	config.subtitles.colourise_dialogs = ConfigYesNo(default=False)
	config.subtitles.subtitle_borderwidth = ConfigSelection(default="3", choices=["1", "2", "3", "4", "5"])
	config.subtitles.subtitle_fontsize = ConfigSelection(default="40", choices=["%d" % x for x in range(16, 101) if not x % 2])
	config.subtitles.showbackground = ConfigYesNo(default=False)

	subtitle_delay_choicelist = []
	for i in range(-900000, 1845000, 45000):
		if i == 0:
			subtitle_delay_choicelist.append(("0", _("No delay")))
		else:
			subtitle_delay_choicelist.append((str(i), _("%2.1f sec") % (i / 90000.)))
	config.subtitles.subtitle_noPTSrecordingdelay = ConfigSelection(default="315000", choices=subtitle_delay_choicelist)

	config.subtitles.dvb_subtitles_yellow = ConfigYesNo(default=False)
	config.subtitles.dvb_subtitles_original_position = ConfigSelection(default="0", choices=[("0", _("Original")), ("1", _("Fixed")), ("2", _("Relative"))])
	config.subtitles.dvb_subtitles_centered = ConfigYesNo(default=False)
	config.subtitles.subtitle_bad_timing_delay = ConfigSelection(default="0", choices=subtitle_delay_choicelist)
	config.subtitles.dvb_subtitles_backtrans = ConfigSelection(default="0", choices=[
		("0", _("No transparency")),
		("25", "10%"),
		("50", "20%"),
		("75", "30%"),
		("100", "40%"),
		("125", "50%"),
		("150", "60%"),
		("175", "70%"),
		("200", "80%"),
		("225", "90%"),
		("255", _("Full transparency"))])
	config.subtitles.pango_subtitle_colors = ConfigSelection(default="1", choices=[
		("0", _("alternative")),
		("1", _("white")),
		("2", _("yellow"))])
	config.subtitles.pango_subtitle_fontswitch = ConfigYesNo(default=True)
	config.subtitles.pango_subtitles_delay = ConfigSelection(default="0", choices=subtitle_delay_choicelist)
	config.subtitles.pango_subtitles_fps = ConfigSelection(default="1", choices=[
		("1", _("Original")),
		("23976", _("23.976")),
		("24000", _("24")),
		("25000", _("25")),
		("29970", _("29.97")),
		("30000", _("30"))])
	config.subtitles.pango_autoturnon = ConfigYesNo(default=True)

	config.autolanguage = ConfigSubsection()
	audio_language_choices = [
		("", _("None")),
		(originalAudioTracks, _("Original")),
		("ara", _("Arabic")),
		("eus baq", _("Basque")),
		("bul", _("Bulgarian")),
		("hrv", _("Croatian")),
		("chn sgp", _("Chinese - Simplified")),
		("twn hkn", _("Chinese - Traditional")),
		("ces cze", _("Czech")),
		("dan", _("Danish")),
		("dut ndl nld", _("Dutch")),
		("eng", _("English")),
		("est", _("Estonian")),
		("fin", _("Finnish")),
		("fra fre", _("French")),
		("deu ger", _("German")),
		("ell gre grc", _("Greek")),
		("heb", _("Hebrew")),
		("hun", _("Hungarian")),
		("ind", _("Indonesian")),
		("ita", _("Italian")),
		("lav", _("Latvian")),
		("lit", _("Lithuanian")),
		("ltz", _("Luxembourgish")),
		("nor", _("Norwegian")),
		("fas per fa pes", _("Persian")),
		("pol", _("Polish")),
		("por dub Dub DUB ud1", _("Portuguese")),
		("ron rum", _("Romanian")),
		("rus", _("Russian")),
		("srp scc", _("Serbian")),
		("slk slo", _("Slovak")),
		("slv", _("Slovenian")),
		("spa", _("Spanish")),
		("swe", _("Swedish")),
		("tha", _("Thai")),
		("tur Audio_TUR", _("Turkish")),
		("ukr Ukr", _("Ukrainian")),
		(visuallyImpairedCommentary, _("Audio description for the visually impaired"))]

	epg_language_choices = audio_language_choices[:1] + audio_language_choices[2:]

	def setEpgLanguage(configElement):
		eServiceEvent.setEPGLanguage(configElement.value)

	def setEpgLanguageAlternative(configElement):
		eServiceEvent.setEPGLanguageAlternative(configElement.value)

	def epglanguage(configElement):
		config.autolanguage.audio_epglanguage.setChoices([x for x in epg_language_choices if x[0] and x[0] != config.autolanguage.audio_epglanguage_alternative.value or not x[0] and not config.autolanguage.audio_epglanguage_alternative.value])
		config.autolanguage.audio_epglanguage_alternative.setChoices([x for x in epg_language_choices if x[0] and x[0] != config.autolanguage.audio_epglanguage.value or not x[0]])
	config.autolanguage.audio_epglanguage = ConfigSelection(epg_language_choices, default="")
	config.autolanguage.audio_epglanguage_alternative = ConfigSelection(epg_language_choices, default="")
	config.autolanguage.audio_epglanguage.addNotifier(setEpgLanguage)
	config.autolanguage.audio_epglanguage.addNotifier(epglanguage, initial_call=False)
	config.autolanguage.audio_epglanguage_alternative.addNotifier(setEpgLanguageAlternative)
	config.autolanguage.audio_epglanguage_alternative.addNotifier(epglanguage)

	def getselectedlanguages(range):
		return [eval("config.autolanguage.audio_autoselect%x.value" % x) for x in range]

	def autolanguage(configElement):
		config.autolanguage.audio_autoselect1.setChoices([x for x in audio_language_choices if x[0] and x[0] not in getselectedlanguages((2, 3, 4)) or not x[0] and not config.autolanguage.audio_autoselect2.value])
		config.autolanguage.audio_autoselect2.setChoices([x for x in audio_language_choices if x[0] and x[0] not in getselectedlanguages((1, 3, 4)) or not x[0] and not config.autolanguage.audio_autoselect3.value])
		config.autolanguage.audio_autoselect3.setChoices([x for x in audio_language_choices if x[0] and x[0] not in getselectedlanguages((1, 2, 4)) or not x[0] and not config.autolanguage.audio_autoselect4.value])
		config.autolanguage.audio_autoselect4.setChoices([x for x in audio_language_choices if x[0] and x[0] not in getselectedlanguages((1, 2, 3)) or not x[0]])
	config.autolanguage.audio_autoselect1 = ConfigSelection(choices=audio_language_choices, default="")
	config.autolanguage.audio_autoselect2 = ConfigSelection(choices=audio_language_choices, default="")
	config.autolanguage.audio_autoselect3 = ConfigSelection(choices=audio_language_choices, default="")
	config.autolanguage.audio_autoselect4 = ConfigSelection(choices=audio_language_choices, default="")
	config.autolanguage.audio_autoselect1.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect2.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect3.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect4.addNotifier(autolanguage)
	config.autolanguage.audio_defaultac3 = ConfigYesNo(default=True)
	config.autolanguage.audio_defaultddp = ConfigYesNo(default=False)
	config.autolanguage.audio_usecache = ConfigYesNo(default=True)

	subtitle_language_choices = audio_language_choices[:1] + audio_language_choices[2:]

	def getselectedsublanguages(range):
		return [eval("config.autolanguage.subtitle_autoselect%x.value" % x) for x in range]

	def autolanguagesub(configElement):
		config.autolanguage.subtitle_autoselect1.setChoices([x for x in subtitle_language_choices if x[0] and x[0] not in getselectedsublanguages((2, 3, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect2.value])
		config.autolanguage.subtitle_autoselect2.setChoices([x for x in subtitle_language_choices if x[0] and x[0] not in getselectedsublanguages((1, 3, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect3.value])
		config.autolanguage.subtitle_autoselect3.setChoices([x for x in subtitle_language_choices if x[0] and x[0] not in getselectedsublanguages((1, 2, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect4.value])
		config.autolanguage.subtitle_autoselect4.setChoices([x for x in subtitle_language_choices if x[0] and x[0] not in getselectedsublanguages((1, 2, 3)) or not x[0]])
		choicelist = [('0', _("None"))]
		for y in range(1, 15 if config.autolanguage.subtitle_autoselect4.value else (7 if config.autolanguage.subtitle_autoselect3.value else (4 if config.autolanguage.subtitle_autoselect2.value else (2 if config.autolanguage.subtitle_autoselect1.value else 0)))):
			choicelist.append((str(y), ", ".join([eval("config.autolanguage.subtitle_autoselect%x.getText()" % x) for x in (y & 1, y & 2, y & 4 and 3, y & 8 and 4) if x])))
		if config.autolanguage.subtitle_autoselect3.value:
			choicelist.append((str(y + 1), "All"))
		config.autolanguage.equal_languages.setChoices(choicelist, default="0")
	config.autolanguage.equal_languages = ConfigSelection(default="0", choices=[str(x) for x in range(0, 16)])
	config.autolanguage.subtitle_autoselect1 = ConfigSelection(choices=subtitle_language_choices, default="")
	config.autolanguage.subtitle_autoselect2 = ConfigSelection(choices=subtitle_language_choices, default="")
	config.autolanguage.subtitle_autoselect3 = ConfigSelection(choices=subtitle_language_choices, default="")
	config.autolanguage.subtitle_autoselect4 = ConfigSelection(choices=subtitle_language_choices, default="")
	config.autolanguage.subtitle_autoselect1.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect2.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect3.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect4.addNotifier(autolanguagesub)
	config.autolanguage.subtitle_hearingimpaired = ConfigYesNo(default=False)
	config.autolanguage.subtitle_defaultimpaired = ConfigYesNo(default=False)
	config.autolanguage.subtitle_defaultdvb = ConfigYesNo(default=False)
	config.autolanguage.subtitle_usecache = ConfigYesNo(default=True)

	config.streaming = ConfigSubsection()
	config.streaming.stream_ecm = ConfigYesNo(default=False)
	config.streaming.descramble = ConfigYesNo(default=True)
	config.streaming.descramble_client = ConfigYesNo(default=False)
	config.streaming.stream_eit = ConfigYesNo(default=True)
	config.streaming.stream_ait = ConfigYesNo(default=True)
	config.streaming.authentication = ConfigYesNo(default=False)

	config.mediaplayer = ConfigSubsection()
	config.mediaplayer.useAlternateUserAgent = ConfigYesNo(default=False)
	config.mediaplayer.alternateUserAgent = ConfigText(default="")

	config.misc.softcam_setup = ConfigSubsection()
	config.misc.softcam_setup.extension_menu = ConfigYesNo(default=True)
	config.misc.softcam_streamrelay_url = ConfigIP(default=[127, 0, 0, 1], auto_jump=True)
	config.misc.softcam_streamrelay_port = ConfigInteger(default=17999, limits=(0, 65535))
	config.misc.softcam_streamrelay_delay = ConfigSelectionNumber(min=0, max=2000, stepwidth=50, default=100, wraparound=True)

	config.ntp = ConfigSubsection()

	def timesyncChanged(configElement):
		if configElement.value == "ntp" or configElement.value == "auto":
			if not os.path.isfile('/var/spool/cron/crontabs/root') or not 'ntpdate-sync' in open('/var/spool/cron/crontabs/root').read():
				Console().ePopen("echo '30 * * * *    /usr/bin/ntpdate-sync silent' >> /var/spool/cron/crontabs/root")
			if not os.path.islink('/etc/network/if-up.d/ntpdate-sync'):
				Console().ePopen("ln -s /usr/bin/ntpdate-sync /etc/network/if-up.d/ntpdate-sync")
		else:
			if os.path.isfile('/var/spool/cron/crontabs/root'):
				Console().ePopen("sed -i '/ntpdate-sync/d' /var/spool/cron/crontabs/root;")
			if os.path.islink('/etc/network/if-up.d/ntpdate-sync'):
				Console().ePopen("unlink /etc/network/if-up.d/ntpdate-sync")

		if configElement.value == "ntp":
			print("[UsageConfig] NTP enabled, DVB time disabled")
			eDVBLocalTimeHandler.getInstance().setUseDVBTime(False)
		elif configElement.value == "auto":
			res = os.system('grep ntpdate /var/log/messages | tail -n 1 | grep -q "adjust time server"')
			if res >> 8 == 0:
				print("[UsageConfig] NTP auto and active, DVB time disabled")
				eDVBLocalTimeHandler.getInstance().setUseDVBTime(False)
			else:
				res = os.system('/usr/bin/ntpdate-sync && sleep 5 && grep ntpdate /var/log/messages | tail -n 1 | grep -q "adjust time server"')
				if res >> 8 == 0:
					print("[UsageConfig] NTP auto and active, DVB time disabled")
					eDVBLocalTimeHandler.getInstance().setUseDVBTime(False)
				else:
					print("[UsageConfig] NTP auto but not active, DVB time enabled")
					eDVBLocalTimeHandler.getInstance().setUseDVBTime(True)
		else:
			print("[UsageConfig] NTP disabled, DVB time enabled")
			eDVBLocalTimeHandler.getInstance().setUseDVBTime(True)

		eEPGCache.getInstance().timeUpdated()

	config.ntp.timesync = ConfigSelection(default="auto", choices=[("auto", _("auto")), ("dvb", _("Transponder Time")), ("ntp", _("Internet (ntp)"))])
	config.ntp.timesync.addNotifier(timesyncChanged)
	config.ntp.server = ConfigText("pool.ntp.org", fixed_size=False)


def updateChoices(sel, choices):
	if choices:
		defval = None
		val = int(sel.value)
		if not val in choices:
			tmp = choices[:]
			tmp.reverse()
			for x in tmp:
				if x < val:
					defval = str(x)
					break
		sel.setChoices(list(map(str, choices)), defval)


def preferredPath(path):
	if config.usage.setup_level.index < 2 or path == "<default>" or not path:
		return None  # config.usage.default_path.value, but delay lookup until usage
	elif path == "<current>":
		return config.movielist.last_videodir.value
	elif path == "<timer>":
		return config.movielist.last_timer_videodir.value
	else:
		return path


def preferredTimerPath():
	return preferredPath(config.usage.timer_path.value)


def preferredInstantRecordPath():
	return preferredPath(config.usage.instantrec_path.value)


def defaultMoviePath():
	return defaultRecordingLocation(config.usage.default_path.value)


def showrotorpositionChoicesUpdate(update=False):
	choiceslist = [("no", _("no")), ("yes", _("yes")), ("withtext", _("with text")), ("tunername", _("with tuner name"))]
	count = 0
	for x in nimmanager.nim_slots:
		if nimmanager.getRotorSatListForNim(x.slot, only_first=True):
			choiceslist.append((str(x.slot), x.getSlotName() + _(" (auto detection)")))
			count += 1
	if count > 1:
		choiceslist.append(("all", _("all tuners") + _(" (auto detection)")))
		choiceslist.remove(("tunername", _("with tuner name")))
	if not update:
		config.misc.showrotorposition = ConfigSelection(default="no", choices=choiceslist)
	else:
		config.misc.showrotorposition.setChoices(choiceslist, "no")
	BoxInfo.setItem("isRotorTuner", count > 0)


def preferredTunerChoicesUpdate(update=False):
	dvbs_nims = [("-2", _("disabled"))]
	dvbt_nims = [("-2", _("disabled"))]
	dvbc_nims = [("-2", _("disabled"))]
	atsc_nims = [("-2", _("disabled"))]

	nims = [("-1", _("auto"))]
	for slot in nimmanager.nim_slots:
		if hasattr(slot.config, "configMode") and slot.config.configMode.value == "nothing":
			continue
		if slot.isCompatible("DVB-S"):
			dvbs_nims.append((str(slot.slot), slot.getSlotName()))
		elif slot.isCompatible("DVB-T"):
			dvbt_nims.append((str(slot.slot), slot.getSlotName()))
		elif slot.isCompatible("DVB-C"):
			dvbc_nims.append((str(slot.slot), slot.getSlotName()))
		elif slot.isCompatible("ATSC"):
			atsc_nims.append((str(slot.slot), slot.getSlotName()))
		nims.append((str(slot.slot), slot.getSlotName()))

	if not update:
		config.usage.frontend_priority = ConfigSelection(default="-1", choices=list(nims))
	else:
		config.usage.frontend_priority.setChoices(list(nims), "-1")
	nims.insert(0, ("-2", _("disabled")))
	if not update:
		config.usage.recording_frontend_priority = ConfigSelection(default="-2", choices=nims)
	else:
		config.usage.recording_frontend_priority.setChoices(nims, "-2")
	if not update:
		config.usage.frontend_priority_dvbs = ConfigSelection(default="-2", choices=list(dvbs_nims))
	else:
		config.usage.frontend_priority_dvbs.setChoices(list(dvbs_nims), "-2")
	dvbs_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_dvbs = ConfigSelection(default="-2", choices=dvbs_nims)
	else:
		config.usage.recording_frontend_priority_dvbs.setChoices(dvbs_nims, "-2")
	if not update:
		config.usage.frontend_priority_dvbt = ConfigSelection(default="-2", choices=list(dvbt_nims))
	else:
		config.usage.frontend_priority_dvbt.setChoices(list(dvbt_nims), "-2")
	dvbt_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_dvbt = ConfigSelection(default="-2", choices=dvbt_nims)
	else:
		config.usage.recording_frontend_priority_dvbt.setChoices(dvbt_nims, "-2")
	if not update:
		config.usage.frontend_priority_dvbc = ConfigSelection(default="-2", choices=list(dvbc_nims))
	else:
		config.usage.frontend_priority_dvbc.setChoices(list(dvbc_nims), "-2")
	dvbc_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_dvbc = ConfigSelection(default="-2", choices=dvbc_nims)
	else:
		config.usage.recording_frontend_priority_dvbc.setChoices(dvbc_nims, "-2")
	if not update:
		config.usage.frontend_priority_atsc = ConfigSelection(default="-2", choices=list(atsc_nims))
	else:
		config.usage.frontend_priority_atsc.setChoices(list(atsc_nims), "-2")
	atsc_nims.insert(1, ("-1", _("auto")))
	if not update:
		config.usage.recording_frontend_priority_atsc = ConfigSelection(default="-2", choices=atsc_nims)
	else:
		config.usage.recording_frontend_priority_atsc.setChoices(atsc_nims, "-2")

	BoxInfo.setItem("DVB-S_priority_tuner_available", len(dvbs_nims) > 3 and any(len(i) > 2 for i in (dvbt_nims, dvbc_nims, atsc_nims)))
	BoxInfo.setItem("DVB-T_priority_tuner_available", len(dvbt_nims) > 3 and any(len(i) > 2 for i in (dvbs_nims, dvbc_nims, atsc_nims)))
	BoxInfo.setItem("DVB-C_priority_tuner_available", len(dvbc_nims) > 3 and any(len(i) > 2 for i in (dvbs_nims, dvbt_nims, atsc_nims)))
	BoxInfo.setItem("ATSC_priority_tuner_available", len(atsc_nims) > 3 and any(len(i) > 2 for i in (dvbs_nims, dvbc_nims, dvbt_nims)))


def dropEPGNewLines(text):
	if config.epg.replace_newlines.value != "no":
		text = text.replace('\x0a', replaceEPGSeparator(config.epg.replace_newlines.value))
	return text


def replaceEPGSeparator(code):
	return {"newline": "\n", "2newlines": "\n\n", "space": " ", "dash": " - ", "dot": " . ", "asterisk": " * ", "hashtag": " # ", "nothing": ""}.get(code)
