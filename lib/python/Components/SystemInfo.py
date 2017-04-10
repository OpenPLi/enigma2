from enigma import eDVBResourceManager, Misc_Options
from Tools.Directories import fileExists, fileCheck, pathExists
from Tools.HardwareInfo import HardwareInfo

SystemInfo = {}

def getNumVideoDecoders():
	number_of_video_decoders = 0
	while fileExists("/dev/dvb/adapter0/video%d" % (number_of_video_decoders), 'f'):
		number_of_video_decoders += 1
	return number_of_video_decoders

def countFrontpanelLEDs():
	number_of_leds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists("/proc/stb/fp/led%d_pattern" % number_of_leds):
		number_of_leds += 1
	return number_of_leds

SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["PIPAvailable"] = SystemInfo["NumVideoDecoders"] > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["LCDsymbol_circle_recording"] = fileCheck("/proc/stb/lcd/symbol_circle") or HardwareInfo().get_device_model() in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_recording")
SystemInfo["LCDsymbol_timeshift"] = fileCheck("/proc/stb/lcd/symbol_timeshift")
SystemInfo["LCDshow_symbols"] = (HardwareInfo().get_device_model().startswith("et9") or HardwareInfo().get_device_model() in ("hd51", "vs1500")) and fileCheck("/proc/stb/lcd/show_symbols")
SystemInfo["LCDsymbol_hdd"] = HardwareInfo().get_device_model() in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_hdd")
SystemInfo["FrontpanelDisplayGrayscale"] = fileExists("/dev/dbox/oled0")
SystemInfo["DeepstandbySupport"] = HardwareInfo().get_device_name() != "dm800"
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled")
SystemInfo["PowerOffDisplay"] = HardwareInfo().get_device_model() not in "formuler1" and fileCheck("/proc/stb/power/vfd") or fileCheck("/proc/stb/lcd/vfd")
SystemInfo["WakeOnLAN"] = not HardwareInfo().get_device_model().startswith("et8000") and fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HasExternalPIP"] = not HardwareInfo().get_device_model().startswith("et9") and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["VFD_scroll_repeats"] = not HardwareInfo().get_device_model().startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = not HardwareInfo().get_device_model().startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = not HardwareInfo().get_device_model().startswith("et8500") and fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = not HardwareInfo().get_device_model().startswith("et8500") and fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["Blindscan_t2_available"] = fileCheck("/proc/stb/info/vumodel")
SystemInfo["RcTypeChangable"] = not(HardwareInfo().get_device_model().startswith('et8500') or HardwareInfo().get_device_model().startswith('et7')) and pathExists('/proc/stb/ir/rc/type')
SystemInfo["HasFullHDSkinSupport"] = HardwareInfo().get_device_model() not in ("et4000", "et5000", "sh1", "hd500c", "hd1100", "xp1000", "lc")
SystemInfo["HasForceLNBOn"] = fileCheck("/proc/stb/frontend/fbc/force_lnbon")
SystemInfo["HasForceToneburst"] = fileCheck("/proc/stb/frontend/fbc/force_toneburst")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = SystemInfo["HasColorspace"] and HardwareInfo().get_device_model() in "vusolo4k"
SystemInfo["HasMultichannelPCM"] = fileCheck("/proc/stb/audio/multichannel_pcm")
SystemInfo["HasMMC"] = HardwareInfo().get_device_model() in ('vusolo4k', 'vuuno4k', 'vuultimo4k', 'hd51', 'hd52', 'vs1500')
SystemInfo["CommonInterfaceCIDelay"] = fileCheck("/proc/stb/tsmux/rmx_delay")
SystemInfo["CanDoTranscodeAndPIP"] = HardwareInfo().get_device_model() in "vusolo4k"
SystemInfo["HasColordepth"] = fileCheck("/proc/stb/video/hdmi_colordepth")
SystemInfo["HasFrontDisplayPicon"] = HardwareInfo().get_device_model() in ("vusolo4k", "et8500")
SystemInfo["HasHDMIpreemphasis"] = fileCheck("/proc/stb/hdmi/preemphasis")
SystemInfo["HasColorimetry"] = fileCheck("/proc/stb/video/hdmi_colorimetry")
SystemInfo["HasHDMI-CEC"] = HardwareInfo().has_hdmi() and fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/HdmiCEC/plugin.pyo")
SystemInfo["HasAutoVolume"] = fileExists("/proc/stb/audio/avl_choices") and fileCheck("/proc/stb/audio/avl")
SystemInfo["HasAutoVolumeLevel"] = fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel")
SystemInfo["Has3DSurround"] = fileExists("/proc/stb/audio/3d_surround_choices") and fileCheck("/proc/stb/audio/3d_surround")
SystemInfo["Has3DSpeaker"] = fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") and fileCheck("/proc/stb/audio/3d_surround_speaker_position")
SystemInfo["Has3DSurroundSpeaker"] = fileExists("/proc/stb/audio/3dsurround_choices") and fileCheck("/proc/stb/audio/3dsurround")
SystemInfo["Has3DSurroundSoftLimiter"] = fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter")
