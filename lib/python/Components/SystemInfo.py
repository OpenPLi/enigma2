import re
from hashlib import md5
from ast import literal_eval
from enigma import Misc_Options, eDVBCIInterfaces, eDVBResourceManager, eGetEnigmaDebugLvl
from Tools.Directories import SCOPE_PLUGINS, fileCheck, fileExists, fileHas, pathExists, resolveFilename


class immutableDict(dict):
	def __init__(self, *args, **kws):
		self.immutablelist = []
		self.checkimmutable = False
		dict.__init__(self, *args, **kws)

	def setImmutable(self):
		self.checkimmutable = True

	def __hash__(self):
		return id(self)

	def _immutable(self, *args, **kws):
		raise TypeError('object is immutable')

	def __setitem__(self, key, value):
		if self.checkimmutable and key in self.immutablelist:
			self._immutable()
		if not self.checkimmutable and key not in self.immutablelist:
			self.immutablelist.append(key)
		dict.__setitem__(self, key, value)

	def __delitem__(self, key):
		if self.checkimmutable and key in self.immutablelist:
			self._immutable()
		else:
			dict.__delitem__(self, key)

	clear = _immutable
	update = _immutable
	setdefault = _immutable
	pop = _immutable
	popitem = _immutable


class BoxInformation:
	def __init__(self, root=""):
		self.boxInfo = immutableDict({"machine": "default", "checksum": None}) #add one key to the boxInfoCollector as it always should exist to satisfy the CI test on github and predefine checksum
		checksumcollectionstring = ""
		file = root + "/usr/lib/enigma.info"
		if fileExists(file):
			for line in open(file, 'r').readlines():
				if line.startswith("checksum="):
					self.boxInfo["checksum"] = md5(bytearray(checksumcollectionstring, "UTF-8", errors="ignore")).hexdigest() == line.strip().split('=')[1]
					break
				checksumcollectionstring += line
				if line.startswith("#") or line.strip() == "":
					continue
				if '=' in line:
					item, value = line.split('=', 1)
					self.boxInfo[item.strip()] = self.processValue(value.strip())
			if self.boxInfo["checksum"]:
				print("[SystemInfo] Enigma information file data loaded into BoxInfo.")
			else:
				print("[SystemInfo] Enigma information file data loaded, but checksum failed.")
		else:
			print("[SystemInfo] ERROR: %s is not available!  The system is unlikely to boot or operate correctly." % file)
		self.boxInfo.setImmutable() #make what is derived from enigma.info immutable

	def processValue(self, value):
		try:
			return literal_eval(value)
		except (ValueError, SyntaxError):
			value_upper = value.upper()
			if value_upper == "NONE":
				return None
			elif value_upper in ("FALSE", "NO", "OFF", "DISABLED"):
				return False
			elif value_upper in ("TRUE", "YES", "ON", "ENABLED"):
				return True
			return value

	def getEnigmaInfoList(self):
		return sorted(self.boxInfo.immutablelist)

	def getEnigmaConfList(self):  # not used by us
		return []

	def getItemsList(self):
		return sorted(self.boxInfo.keys())

	def getItem(self, item, default=None):
		return self.boxInfo.get(item, default)

	def setItem(self, item, value, *args, **kws):
		self.boxInfo[item] = value
		return True

	def deleteItem(self, item, *args, **kws):
		del self.boxInfo[item]
		return True


BoxInfo = BoxInformation()


# Parse the boot commandline.
#
with open("/proc/cmdline", "r") as fd:
	cmdline = fd.read()
cmdline = {k: v.strip('"') for k, v in re.findall(r'(\S+)=(".*?"|\S+)', cmdline)}


def getNumVideoDecoders():
	numVideoDecoders = 0
	while fileExists("/dev/dvb/adapter0/video%d" % numVideoDecoders, "f"):
		numVideoDecoders += 1
	return numVideoDecoders


def countFrontpanelLEDs():
	numLeds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists("/proc/stb/fp/led%d_pattern" % numLeds):
		numLeds += 1
	return numLeds


def hassoftcaminstalled():
	from Tools.camcontrol import CamControl
	return len(CamControl("softcam").getList()) > 1


def getBootdevice():
	dev = ("root" in cmdline and cmdline["root"].startswith("/dev/")) and cmdline["root"][5:]
	while dev and not fileExists("/sys/block/%s" % dev):
		dev = dev[:-1]
	return dev

#This line makes the new BoxInfo backwards compatible with SystemInfo without duplicating the dictionary.
SystemInfo = BoxInfo.boxInfo
from Tools.Multiboot import getMultibootStartupDevice, getMultibootslots  # This import needs to be here to avoid a SystemInfo load loop!


def setBoxInfoItems():
	model = BoxInfo.getItem("machine")
	BoxInfo.setItem("InDebugMode", eGetEnigmaDebugLvl() >= 4)
	BoxInfo.setItem("CommonInterface", model in ("h9combo", "h9combose", "h10", "pulse4kmini") and 1 or eDVBCIInterfaces.getInstance().getNumOfSlots())
	BoxInfo.setItem("CommonInterfaceCIDelay", fileCheck("/proc/stb/tsmux/rmx_delay"))
	for cislot in range(0, BoxInfo.getItem("CommonInterface")):
		BoxInfo.setItem("CI%dSupportsHighBitrates" % cislot, fileCheck("/proc/stb/tsmux/ci%d_tsclk" % cislot))
		BoxInfo.setItem("CI%dRelevantPidsRoutingSupport" % cislot, fileCheck("/proc/stb/tsmux/ci%d_relevant_pids_routing" % cislot))
	BoxInfo.setItem("HasSoftcamInstalled", hassoftcaminstalled())
	BoxInfo.setItem("NumVideoDecoders", getNumVideoDecoders())
	BoxInfo.setItem("PIPAvailable", BoxInfo.getItem("NumVideoDecoders") > 1)
	BoxInfo.setItem("CanMeasureFrontendInputPower", eDVBResourceManager.getInstance().canMeasureFrontendInputPower())
	BoxInfo.setItem("12V_Output", Misc_Options.getInstance().detected_12V_output())
	BoxInfo.setItem("ZapMode", fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode"))
	BoxInfo.setItem("NumFrontpanelLEDs", countFrontpanelLEDs())
	BoxInfo.setItem("FrontpanelDisplay", fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0"))
	BoxInfo.setItem("LCDsymbol_circle_recording", fileCheck("/proc/stb/lcd/symbol_circle") or model in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_recording"))
	BoxInfo.setItem("LCDsymbol_timeshift", fileCheck("/proc/stb/lcd/symbol_timeshift"))
	BoxInfo.setItem("LCDshow_symbols", (model.startswith("et9") or model in ("hd51", "vs1500")) and fileCheck("/proc/stb/lcd/show_symbols"))
	BoxInfo.setItem("LCDsymbol_hdd", model in ("hd51", "vs1500") and fileCheck("/proc/stb/lcd/symbol_hdd"))
	BoxInfo.setItem("FrontpanelDisplayGrayscale", fileExists("/dev/dbox/oled0"))
	BoxInfo.setItem("DeepstandbySupport", model != "dm800")
	BoxInfo.setItem("Fan", fileCheck("/proc/stb/fp/fan"))
	BoxInfo.setItem("FanPWM", BoxInfo.getItem("Fan") and fileCheck("/proc/stb/fp/fan_pwm"))
	BoxInfo.setItem("PowerLED", fileCheck("/proc/stb/power/powerled") or model in ("gbue4k", "gbquad4k") and fileCheck("/proc/stb/fp/led1_pattern"))
	BoxInfo.setItem("StandbyLED", fileCheck("/proc/stb/power/standbyled") or model in ("gbue4k", "gbquad4k") and fileCheck("/proc/stb/fp/led0_pattern"))
	BoxInfo.setItem("SuspendLED", fileCheck("/proc/stb/power/suspendled") or fileCheck("/proc/stb/fp/enable_led"))
	BoxInfo.setItem("Display", BoxInfo.getItem("FrontpanelDisplay") or BoxInfo.getItem("StandbyLED"))
	BoxInfo.setItem("LedPowerColor", fileCheck("/proc/stb/fp/ledpowercolor"))
	BoxInfo.setItem("LedStandbyColor", fileCheck("/proc/stb/fp/ledstandbycolor"))
	BoxInfo.setItem("LedSuspendColor", fileCheck("/proc/stb/fp/ledsuspendledcolor"))
	BoxInfo.setItem("Power4x7On", fileCheck("/proc/stb/fp/power4x7on"))
	BoxInfo.setItem("Power4x7Standby", fileCheck("/proc/stb/fp/power4x7standby"))
	BoxInfo.setItem("Power4x7Suspend", fileCheck("/proc/stb/fp/power4x7suspend"))
	BoxInfo.setItem("PowerOffDisplay", model not in "formuler1" and fileCheck("/proc/stb/power/vfd") or fileCheck("/proc/stb/lcd/vfd"))
	BoxInfo.setItem("WakeOnLAN", not model.startswith("et8000") and fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol"))
	BoxInfo.setItem("HasExternalPIP", not (model.startswith("et9") or model in ("e4hd",)) and fileCheck("/proc/stb/vmpeg/1/external"))
	BoxInfo.setItem("VideoDestinationConfigurable", fileExists("/proc/stb/vmpeg/0/dst_left"))
	BoxInfo.setItem("hasPIPVisibleProc", fileCheck("/proc/stb/vmpeg/1/visible"))
	BoxInfo.setItem("MaxPIPSize", model in ("hd51", "h7", "vs1500", "e4hd") and (360, 288) or (540, 432))
	BoxInfo.setItem("VFD_scroll_repeats", not model.startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_repeats"))
	BoxInfo.setItem("VFD_scroll_delay", not model.startswith("et8500") and fileCheck("/proc/stb/lcd/scroll_delay"))
	BoxInfo.setItem("VFD_initial_scroll_delay", not model.startswith("et8500") and fileCheck("/proc/stb/lcd/initial_scroll_delay"))
	BoxInfo.setItem("VFD_final_scroll_delay", not model.startswith("et8500") and fileCheck("/proc/stb/lcd/final_scroll_delay"))
	BoxInfo.setItem("LcdLiveTV", fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable"))
	BoxInfo.setItem("LcdLiveTVMode", fileCheck("/proc/stb/lcd/mode"))
	BoxInfo.setItem("LcdLiveDecoder", fileCheck("/proc/stb/lcd/live_decoder"))
	BoxInfo.setItem("FastChannelChange", False)
	BoxInfo.setItem("3DMode", fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d"))
	BoxInfo.setItem("3DZNorm", fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset"))
	BoxInfo.setItem("Blindscan_t2_available", fileCheck("/proc/stb/info/vumodel") and model.startswith("vu"))
	BoxInfo.setItem("RcTypeChangable", not (model in ("gbquad4k", "gbue4k", "et8500") or model.startswith("et7")) and pathExists("/proc/stb/ir/rc/type"))
	BoxInfo.setItem("HasFullHDSkinSupport", model not in ("et4000", "et5000", "sh1", "hd500c", "hd1100", "xp1000", "lc"))
	BoxInfo.setItem("HasBypassEdidChecking", fileCheck("/proc/stb/hdmi/bypass_edid_checking"))
	BoxInfo.setItem("HasMMC", "root" in cmdline and cmdline["root"].startswith("/dev/mmcblk"))
	BoxInfo.setItem("HasColorspace", fileCheck("/proc/stb/video/hdmi_colorspace"))
	BoxInfo.setItem("HasColorspaceSimple", BoxInfo.getItem("HasColorspace") and BoxInfo.getItem("HasMMC") and BoxInfo.getItem("Blindscan_t2_available"))
	BoxInfo.setItem("HasTranscoding", pathExists("/proc/stb/encoder/0") or fileCheck("/dev/bcm_enc0"))
	BoxInfo.setItem("HasH265Encoder", fileHas("/proc/stb/encoder/0/vcodec_choices", "h265"))
	BoxInfo.setItem("CanNotDoSimultaneousTranscodeAndPIP", model in ("vusolo4k", "gbquad4k", "gbue4k"))
	BoxInfo.setItem("HasColordepth", fileCheck("/proc/stb/video/hdmi_colordepth"))
	BoxInfo.setItem("HasFrontDisplayPicon", model in ("et8500", "vusolo4k", "vuuno4kse", "vuduo4k", "vuduo4kse", "vuultimo4k", "gbquad4k", "gbue4k"))
	BoxInfo.setItem("Has24hz", fileCheck("/proc/stb/video/videomode_24hz"))
	BoxInfo.setItem("Has2160p", fileHas("/proc/stb/video/videomode_preferred", "2160p50"))
	BoxInfo.setItem("HasHDMIpreemphasis", fileCheck("/proc/stb/hdmi/preemphasis"))
	BoxInfo.setItem("HasColorimetry", fileCheck("/proc/stb/video/hdmi_colorimetry"))
	BoxInfo.setItem("HasHdrType", fileCheck("/proc/stb/video/hdmi_hdrtype"))
	BoxInfo.setItem("HasScaler_sharpness", pathExists("/proc/stb/vmpeg/0/pep_scaler_sharpness"))
	BoxInfo.setItem("HasHDMIin", BoxInfo.getItem("dmifhdin") or BoxInfo.getItem("hdmihdin"))
	BoxInfo.setItem("HasHDMI-CEC", BoxInfo.getItem("hdmi") and fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/HdmiCEC/plugin.pyc")) and (fileExists("/dev/cec0") or fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0")))
	BoxInfo.setItem("HasYPbPr", model in ("dm8000", "et5000", "et6000", "et6500", "et9000", "et9200", "et9500", "et10000", "formuler1", "mbtwinplus", "spycat", "vusolo", "vuduo", "vuduo2", "vuultimo"))
	BoxInfo.setItem("HasScart", model in ("dm8000", "et4000", "et6500", "et8000", "et9000", "et9200", "et9500", "et10000", "formuler1", "hd1100", "hd1200", "hd1265", "hd2400", "vusolo", "vusolo2", "vuduo", "vuduo2", "vuultimo", "vuuno", "xp1000"))
	BoxInfo.setItem("HasSVideo", model in ("dm8000"))
	BoxInfo.setItem("HasComposite", model not in ("i55", "gbquad4k", "gbue4k", "hd1500", "osnino", "osninoplus", "purehd", "purehdse", "revo4k", "vusolo4k", "vuzero4k", "vuduo4k", "vuduo4kse", "vuuno4k", "vuuno4kse", "vuultimo4k"))
	BoxInfo.setItem("hasXcoreVFD", model in ("osmega", "spycat4k", "spycat4kmini", "spycat4kcombo") and fileCheck("/sys/module/brcmstb_%s/parameters/pt6302_cgram" % model))
	BoxInfo.setItem("HasOfflineDecoding", model not in ("osmini", "osminiplus", "et7000mini", "et11000", "mbmicro", "mbtwinplus", "mbmicrov2", "et7000", "et8500"))
	BoxInfo.setItem("hasKexec", fileHas("/proc/cmdline", "kexec=1"))
	BoxInfo.setItem("canKexec", not BoxInfo.getItem("hasKexec") and fileExists("/usr/bin/kernel_auto.bin") and fileExists("/usr/bin/STARTUP.cpio.gz") and (model in ("vuduo4k", "vuduo4kse") and ["mmcblk0p9", "mmcblk0p6"] or model in ("vusolo4k", "vuultimo4k", "vuuno4k", "vuuno4kse") and ["mmcblk0p4", "mmcblk0p1"] or model == "vuzero4k" and ["mmcblk0p7", "mmcblk0p4"]))
	BoxInfo.setItem("MultibootStartupDevice", getMultibootStartupDevice())
	BoxInfo.setItem("canMode12", "%s_4.boxmode" % model in cmdline and cmdline["%s_4.boxmode" % model] in ("1", "12") and "192M")
	BoxInfo.setItem("canMultiBoot", getMultibootslots())
	BoxInfo.setItem("canDualBoot", fileExists("/dev/block/by-name/flag"))
	BoxInfo.setItem("canFlashWithOfgwrite", not (model.startswith("dm")))
	BoxInfo.setItem("HDRSupport", fileExists("/proc/stb/hdmi/hlg_support_choices") and fileCheck("/proc/stb/hdmi/hlg_support"))
	BoxInfo.setItem("CanProc", BoxInfo.getItem("HasMMC") and not BoxInfo.getItem("Blindscan_t2_available"))
	BoxInfo.setItem("HasMultichannelPCM", fileCheck("/proc/stb/audio/multichannel_pcm"))
	BoxInfo.setItem("HasAutoVolume", fileExists("/proc/stb/audio/avl_choices") and fileCheck("/proc/stb/audio/avl"))
	BoxInfo.setItem("HasAutoVolumeLevel", fileExists("/proc/stb/audio/autovolumelevel_choices") and fileCheck("/proc/stb/audio/autovolumelevel"))
	BoxInfo.setItem("Has3DSurround", fileExists("/proc/stb/audio/3d_surround_choices") and fileCheck("/proc/stb/audio/3d_surround"))
	BoxInfo.setItem("Has3DSpeaker", fileExists("/proc/stb/audio/3d_surround_speaker_position_choices") and fileCheck("/proc/stb/audio/3d_surround_speaker_position"))
	BoxInfo.setItem("Has3DSurroundSpeaker", fileExists("/proc/stb/audio/3dsurround_choices") and fileCheck("/proc/stb/audio/3dsurround"))
	BoxInfo.setItem("Has3DSurroundSoftLimiter", fileExists("/proc/stb/audio/3dsurround_softlimiter_choices") and fileCheck("/proc/stb/audio/3dsurround_softlimiter"))
	BoxInfo.setItem("CanDownmixAC3", fileHas("/proc/stb/audio/ac3_choices", "downmix"))
	BoxInfo.setItem("CanDownmixDTS", fileHas("/proc/stb/audio/dts_choices", "downmix"))
	BoxInfo.setItem("CanDownmixAAC", fileHas("/proc/stb/audio/aac_choices", "downmix"))
	BoxInfo.setItem("HDMIAudioSource", fileCheck("/proc/stb/hdmi/audio_source"))
	BoxInfo.setItem("CanAC3Transcode", fileHas("/proc/stb/audio/ac3plus_choices", "force_ac3"))
	BoxInfo.setItem("CanDTSHD", fileHas("/proc/stb/audio/dtshd_choices", "downmix"))
	BoxInfo.setItem("CanDownmixAACPlus", fileHas("/proc/stb/audio/aacplus_choices", "downmix"))
	BoxInfo.setItem("CanAACTranscode", fileHas("/proc/stb/audio/aac_transcode_choices", "off"))
	BoxInfo.setItem("CanWMAPRO", fileHas("/proc/stb/audio/wmapro_choices", "downmix"))
	BoxInfo.setItem("CanBTAudio", fileHas("/proc/stb/audio/btaudio_choices", "off"))
	BoxInfo.setItem("CanBTAudioDelay", fileCheck("/proc/stb/audio/btaudio_delay") or fileCheck("/proc/stb/audio/btaudio_delay_pcm"))
	BoxInfo.setItem("BootDevice", getBootdevice())
	BoxInfo.setItem("NimExceptionVuSolo2", model == "vusolo2")
	BoxInfo.setItem("NimExceptionVuDuo2", model == "vuduo2")
	BoxInfo.setItem("NimExceptionDMM8000", model == "dm8000")
	BoxInfo.setItem("FbcTunerPowerAlwaysOn", model in ("vusolo4k", "vuduo4k", "vuduo4kse", "vuultimo4k", "vuuno4k", "vuuno4kse"))
	BoxInfo.setItem("HasPhysicalLoopthrough", ["Vuplus DVB-S NIM(AVL2108)", "GIGA DVB-S2 NIM (Internal)"])
	if model in ("et7500", "et8500"):
		BoxInfo.setItem("HasPhysicalLoopthrough", BoxInfo.getItem("HasPhysicalLoopthrough") + ["AVL6211"])
	BoxInfo.setItem("HasFBCtuner", ["Vuplus DVB-C NIM(BCM3158)", "Vuplus DVB-C NIM(BCM3148)", "Vuplus DVB-S NIM(7376 FBC)", "Vuplus DVB-S NIM(45308X FBC)", "Vuplus DVB-S NIM(45208 FBC)", "DVB-S2 NIM(45208 FBC)", "DVB-S2X NIM(45308X FBC)", "DVB-S2 NIM(45308 FBC)", "DVB-C NIM(3128 FBC)", "BCM45208", "BCM45308X", "BCM3158"])
	BoxInfo.setItem("HasHiSi", pathExists("/proc/hisi"))
	BoxInfo.setItem("FCCactive", False)
	BoxInfo.setItem("Autoresolution_proc_videomode", model in ("gbue4k", "gbquad4k") and "/proc/stb/video/videomode_50hz" or "/proc/stb/video/videomode")


setBoxInfoItems()