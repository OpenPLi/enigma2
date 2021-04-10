from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.SystemInfo import SystemInfo
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigBoolean, ConfigNothing
from Components.Label import Label
from Components.Sources.StaticText import StaticText

from VideoHardware import video_hw

config.misc.videowizardenabled = ConfigBoolean(default=True)


class VideoSetup(Screen, ConfigListScreen):

	def __init__(self, session, hw):
		Screen.__init__(self, session)
		# for the skin: first try VideoSetup, then Setup, this allows individual skinning
		self.skinName = ["VideoSetup", "Setup"]
		self.setup_title = _("A/V settings")
		self.setTitle(self.setup_title)
		self.hw = hw
		self.onChangedEntry = []

		# handle hotplug by re-creating setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		from Components.ActionMap import ActionMap
		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"menu": self.closeRecursive,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["description"] = Label("")

		self.createSetup()
		self.grabLastGoodMode()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def startHotplug(self):
		self.hw.on_hotplug.append(self.createSetup)

	def stopHotplug(self):
		self.hw.on_hotplug.remove(self.createSetup)

	def createSetup(self):
		level = config.usage.setup_level.index

		self.list = [
			getConfigListEntry(_("Video output"), config.av.videoport, _("Configures which video output connector will be used."))
		]

		# if we have modes for this port:
		if config.av.videoport.value in config.av.videomode:
			# add mode- and rate-selection:
			self.list.append(getConfigListEntry(pgettext("Video output mode", "Mode"), config.av.videomode[config.av.videoport.value], _("Configure the video output mode (or resolution).")))
			if config.av.videomode[config.av.videoport.value].value == 'PC':
				self.list.append(getConfigListEntry(_("Resolution"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("Configure the screen resolution in PC output mode.")))
			else:
				self.list.append(getConfigListEntry(_("Refresh rate"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("Configure the refresh rate of the screen.")))

		port = config.av.videoport.value
		if port not in config.av.videomode:
			mode = None
		else:
			mode = config.av.videomode[port].value

		# some modes (720p, 1080i) are always widescreen. Don't let the user select something here, "auto" is not what he wants.
		force_wide = self.hw.isWidescreenMode(port, mode)

		if not force_wide:
			self.list.append(getConfigListEntry(_("Aspect ratio"), config.av.aspect, _("Configure the aspect ratio of the screen.")))

		if force_wide or config.av.aspect.value in ("16_9", "16_10"):
			self.list.extend((
				getConfigListEntry(_("Display 4:3 content as"), config.av.policy_43, _("When the content has an aspect ratio of 4:3, choose whether to scale/stretch the picture.")),
				getConfigListEntry(_("Display >16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture."))
			))
		elif config.av.aspect.value == "4_3":
			self.list.append(getConfigListEntry(_("Display 16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture.")))

		if config.av.videoport.value == "DVI":
			if level >= 1:
				self.list.append(getConfigListEntry(_("Allow unsupported modes"), config.av.edid_override, _("When selected this allows video modes to be selected even if they are not reported as supported.")))
				if SystemInfo["HasBypassEdidChecking"]:
					self.list.append(getConfigListEntry(_("Bypass HDMI EDID checking"), config.av.bypassEdidChecking, _("Configure if the HDMI EDID checking should be bypassed as this might solve issue with some TVs.")))
				if SystemInfo["HasColorspace"]:
					self.list.append(getConfigListEntry(_("HDMI Colorspace"), config.av.hdmicolorspace, _("This option allows you to configure the Colorspace from Auto to RGB")))
				if SystemInfo["HasColordepth"]:
					self.list.append(getConfigListEntry(_("HDMI Colordepth"), config.av.hdmicolordepth, _("This option allows you to configure the Colordepth for UHD")))
				if SystemInfo["HasColorimetry"]:
					self.list.append(getConfigListEntry(_("HDMI Colorimetry"), config.av.hdmicolorimetry, _("This option allows you to configure the Colorimetry for HDR.")))
				if SystemInfo["HasHdrType"]:
					self.list.append(getConfigListEntry(_("HDMI HDR Type"), config.av.hdmihdrtype, _("This option allows you to configure the HDR type.")))
				if SystemInfo["HasHDMIpreemphasis"]:
					self.list.append(getConfigListEntry(_("Use HDMI pre-emphasis"), config.av.hdmipreemphasis, _("This option can be useful for long HDMI cables.")))
				if SystemInfo["HDRSupport"]:
					self.list.append(getConfigListEntry(_("HLG support"), config.av.hlg_support, _("This option allows you to force the HLG modes for UHD")))
					self.list.append(getConfigListEntry(_("HDR10 support"), config.av.hdr10_support, _("This option allows you to force the HDR10 modes for UHD")))
					self.list.append(getConfigListEntry(_("Allow 12bit"), config.av.allow_12bit, _("This option allows you to enable or disable the 12 bit color mode")))
					self.list.append(getConfigListEntry(_("Allow 10bit"), config.av.allow_10bit, _("This option allows you to enable or disable the 10 bit color mode")))
					
		if config.av.videoport.value == "Scart":
			self.list.append(getConfigListEntry(_("Color format"), config.av.colorformat, _("Configure which color format should be used on the SCART output.")))
			if level >= 1:
				self.list.append(getConfigListEntry(_("WSS on 4:3"), config.av.wss, _("When enabled, content with an aspect ratio of 4:3 will be stretched to fit the screen.")))
				if SystemInfo["ScartSwitch"]:
					self.list.append(getConfigListEntry(_("Auto scart switching"), config.av.vcrswitch, _("When enabled, your receiver will detect activity on the VCR SCART input.")))

		if level >= 1:
			self.list.append(getConfigListEntry(_("Audio volume step size"), config.av.volume_stepsize, _("Configure the general audio volume step size (limit 1-10).")))
			if SystemInfo["CanDownmixAC3"]:
				self.list.append(getConfigListEntry(_("AC3 downmix"), config.av.downmix_ac3, _("Configure whether multi channel sound tracks should be downmixed to stereo.")))
			if SystemInfo["CanDownmixDTS"]:
				self.list.append(getConfigListEntry(_("DTS downmix"), config.av.downmix_dts, _("Configure whether multi channel sound tracks should be downmixed to stereo.")))
			if SystemInfo["CanDownmixAAC"]:
				self.list.append(getConfigListEntry(_("AAC downmix"), config.av.downmix_aac, _("Configure whether multi channel sound tracks should be downmixed to stereo.")))
			self.list.extend((
				getConfigListEntry(_("General AC3 delay"), config.av.generalAC3delay, _("Configure the general audio delay of Dolby Digital sound tracks.")),
				getConfigListEntry(_("General PCM delay"), config.av.generalPCMdelay, _("Configure the general audio delay of stereo sound tracks."))
			))
			if SystemInfo["HasMultichannelPCM"]:
				self.list.append(getConfigListEntry(_("Multichannel PCM"), config.av.multichannel_pcm, _("Configure whether multi channel PCM sound should be enabled.")))
			if SystemInfo["HasAutoVolume"] or SystemInfo["HasAutoVolumeLevel"]:
				self.list.append(getConfigListEntry(_("Audio auto volume level"), SystemInfo["HasAutoVolume"] and config.av.autovolume or config.av.autovolumelevel, _("This option allows you can to set the auto volume level.")))
			if SystemInfo["Has3DSurround"]:
				self.list.append(getConfigListEntry(_("3D surround"), config.av.surround_3d, _("This option allows you to enable 3D surround sound.")))
				if SystemInfo["Has3DSpeaker"] and config.av.surround_3d.value != "none":
					self.list.append(getConfigListEntry(_("3D surround speaker position"), config.av.speaker_3d, _("This option allows you to change the virtuell loadspeaker position.")))
			if SystemInfo["Has3DSurroundSpeaker"]:
				self.list.append(getConfigListEntry(_("3D surround speaker position"), config.av.surround_3d_speaker, _("This option allows you to disable or change the virtuell loadspeaker position.")))
				if SystemInfo["Has3DSurroundSoftLimiter"] and config.av.surround_3d_speaker.value != "disabled":
					self.list.append(getConfigListEntry(_("3D surround softlimiter"), config.av.surround_softlimiter_3d, _("This option allows you to enable 3D surround softlimiter.")))

		if SystemInfo["CanChangeOsdAlpha"]:
			self.list.append(getConfigListEntry(_("OSD transparency"), config.av.osd_alpha, _("Configure the transparency of the OSD.")))

		if not isinstance(config.av.scaler_sharpness, ConfigNothing):
			self.list.append(getConfigListEntry(_("Scaler sharpness"), config.av.scaler_sharpness, _("Configure the sharpness of the video scaling.")))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def confirm(self, confirmed):
		if not confirmed:
			config.av.videoport.value = self.last_good[0]
			config.av.videomode[self.last_good[0]].value = self.last_good[1]
			config.av.videorate[self.last_good[1]].value = self.last_good[2]
			self.hw.setMode(*self.last_good)
		else:
			self.keySave()

	def grabLastGoodMode(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		self.last_good = (port, mode, rate)

	def apply(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		if (port, mode, rate) != self.last_good:
			self.hw.setMode(port, mode, rate)
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.confirm, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout=20, default=False)
		else:
			self.keySave()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


class VideomodeHotplug:
	def __init__(self, hw):
		self.hw = hw

	def start(self):
		self.hw.on_hotplug.append(self.hotplug)

	def stop(self):
		self.hw.on_hotplug.remove(self.hotplug)

	def hotplug(self, what):
		print "hotplug detected on port '%s'" % (what)
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value

		if not self.hw.isModeAvailable(port, mode, rate):
			print "mode %s/%s/%s went away!" % (port, mode, rate)
			modelist = self.hw.getModeList(port)
			if not len(modelist):
				print "sorry, no other mode is available (unplug?). Doing nothing."
				return
			mode = modelist[0][0]
			rate = modelist[0][1]
			print "setting %s/%s/%s" % (port, mode, rate)
			self.hw.setMode(port, mode, rate)


hotplug = None


def startHotplug():
	global hotplug, video_hw
	hotplug = VideomodeHotplug(video_hw)
	hotplug.start()


def stopHotplug():
	global hotplug
	hotplug.stop()


def autostart(reason, session=None, **kwargs):
	if session is not None:
		global my_global_session
		my_global_session = session
		return

	if reason == 0:
		startHotplug()
	elif reason == 1:
		stopHotplug()


def videoSetupMain(session, **kwargs):
	session.open(VideoSetup, video_hw)


def startSetup(menuid):
	if menuid != "video":
		return []

	return [(_("A/V settings"), videoSetupMain, "av_setup", 40)]


def VideoWizard(*args, **kwargs):
	from VideoWizard import VideoWizard
	return VideoWizard(*args, **kwargs)


def Plugins(**kwargs):
	list = [
#		PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
		PluginDescriptor(name=_("Video setup"), description=_("Advanced video setup"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=startSetup)
	]
	if config.misc.videowizardenabled.value:
		list.append(PluginDescriptor(name=_("Video wizard"), where=PluginDescriptor.WHERE_WIZARD, needsRestart=False, fnc=(20, VideoWizard)))
	return list
