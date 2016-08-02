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
SystemInfo["FrontpanelDisplayGrayscale"] = fileExists("/dev/dbox/oled0")
SystemInfo["DeepstandbySupport"] = HardwareInfo().get_device_name() != "dm800"
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled")
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
SystemInfo["HasFullHDSkinSupport"] = HardwareInfo().get_device_model() not in "et4000 et5000 sh1 hd500c hd1100 xp1000 vusolo"
SystemInfo["HasForceLNBOn"] = fileCheck("/proc/stb/frontend/fbc/force_lnbon")
SystemInfo["HasForceToneburst"] = fileCheck("/proc/stb/frontend/fbc/force_toneburst")
SystemInfo["HasBypassEdidChecking"] = fileCheck("/proc/stb/hdmi/bypass_edid_checking")
SystemInfo["HasColorspace"] = fileCheck("/proc/stb/video/hdmi_colorspace")
SystemInfo["HasColorspaceSimple"] = SystemInfo["HasColorspace"] and HardwareInfo().get_device_model() in "vusolo4k"
