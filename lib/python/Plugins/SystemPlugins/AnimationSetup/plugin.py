from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigNumber, ConfigSelection, ConfigSelectionNumber, getConfigListEntry
from Plugins.Plugin import PluginDescriptor

from enigma import setAnimation_current, setAnimation_speed, setAnimation_current_listbox


g_animation_paused = False
g_orig_show = None
g_orig_doClose = None

config.misc.window_animation_default = ConfigNumber(default = 6)
config.misc.window_animation_speed = ConfigSelectionNumber(1, 30, 1, default = 20)
config.misc.listbox_animation_default = ConfigSelection(default = "0", choices = [("0", _("Disable")), ("1", _("Enable")), ("2", _("Same behavior as current animation"))])

class AnimationSetupConfig(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="600,140" title="Animation Settings">
			<widget name="config" position="0,0" size="600,100" scrollbarMode="showOnDemand" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="0,100" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,100" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,100" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="0,100" zPosition="1" size="140,40" \
				font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="140,100" zPosition="1" size="140,40" \
				font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,100" zPosition="1" size="140,40" \
				font="Regular;20" halign="center" valign="center" transparent="1" />
		</screen>
		"""

	def __init__(self, session):
		self.session = session
		self.entrylist = []

		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, self.entrylist)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions",], {
			"ok"     : self.keyGreen,
			"green"  : self.keyGreen,
			"yellow" : self.keyYellow,
			"red"    : self.keyRed,
			"cancel" : self.keyRed,
		}, -2)
		self["key_red"]   = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Default"))

		self.makeConfigList()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_('Animation Setup'))

	def keyGreen(self):
		config.misc.window_animation_speed.save()
		setAnimation_speed(int(config.misc.window_animation_speed.value))
		setAnimation_speed(int(config.misc.window_animation_speed.value))
		config.misc.listbox_animation_default.save()
		setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))
		self.close()

	def keyRed(self):
		config.misc.window_animation_speed.cancel()
		config.misc.listbox_animation_default.cancel()
		self.close()

	def keyYellow(self):
		config.misc.window_animation_speed.value = 20
		config.misc.listbox_animation_default.value = "0"
		self.makeConfigList()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def makeConfigList(self):
		self.entrylist = []

		self.entrylist.append(getConfigListEntry(_("Animation Speed"), config.misc.window_animation_speed))
		self.entrylist.append(getConfigListEntry(_("Enable Focus Animation"), config.misc.listbox_animation_default))
		self["config"].list = self.entrylist
		self["config"].l.setList(self.entrylist)


class AnimationSetupScreen(Screen):
	animationSetupItems = [
		{"idx":0, "name":_("Disable Animations")},
		{"idx":1, "name":_("Simple fade")},
		{"idx":2, "name":_("Grow drop")},
		{"idx":3, "name":_("Grow from left")},
		{"idx":4, "name":_("Popup")},
		{"idx":5, "name":_("Slide drop")},
		{"idx":6, "name":_("Slide left to right")},
		{"idx":7, "name":_("Slide top to bottom")},
		{"idx":8, "name":_("Stripes")},
	]

	skin = """
		<screen name="AnimationSetup" position="center,center" size="580,400" title="Animation Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" \
				font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" \
				font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" \
				font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" \
				font="Regular;20" halign="center" valign="center" transparent="1" />

			<widget name="list" position="10,60" size="560,364" scrollbarMode="showOnDemand" />
				<widget source="introduction" render="Label" position="0,370" size="560,40" \
					font="Regular;20" valign="center" transparent="1" />
		</screen>
		"""

	def __init__(self, session):

		self.skin = AnimationSetupScreen.skin
		Screen.__init__(self, session)

		self.animationList = []

		self["introduction"] = StaticText(_("* current animation"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Settings"))
		self["key_blue"] = StaticText(_("Preview"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyclose,
				"save": self.ok,
				"ok" : self.ok,
				"yellow": self.config,
				"blue": self.preview
			}, -3)

		self["list"] = MenuList(self.animationList)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		l = []
		for x in self.animationSetupItems:
			key = x.get("idx", 0)
			name = x.get("name", "??")
			if key == config.misc.window_animation_default.value:
				name = "* %s" % (name)
			l.append( (name, key) )

		self["list"].setList(l)

	def ok(self):
		current = self["list"].getCurrent()
		if current:
			key = current[1]
			config.misc.window_animation_default.value = key
			config.misc.window_animation_default.save()
			setAnimation_current(key)
			setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))
		self.close()

	def keyclose(self):
		setAnimation_current(config.misc.window_animation_default.value)
		setAnimation_speed(int(config.misc.window_animation_speed.value))
		setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))
		self.close()

	def config(self):
		self.session.open(AnimationSetupConfig)

	def preview(self):
		current = self["list"].getCurrent()
		if current:
			global g_animation_paused
			tmp = g_animation_paused
			g_animation_paused = False

			setAnimation_current(current[1])
			self.session.open(MessageBox, current[0], MessageBox.TYPE_INFO, timeout=3)
			g_animation_paused = tmp

def checkAttrib(self, paused):
	if g_animation_paused is paused:
		try:
			for (attr, value) in self.skinAttributes:
				if attr == "animationPaused" and value in ("1", "on"):
					return True
		except:
			pass
	return False

def screen_show(self):
	global g_animation_paused
	if g_animation_paused:
		setAnimation_current(0)

	g_orig_show(self)

	if checkAttrib(self, False):
		g_animation_paused = True

def screen_doClose(self):
	global g_animation_paused
	if checkAttrib(self, True):
		g_animation_paused = False
		setAnimation_current(config.misc.window_animation_default.value)
	g_orig_doClose(self)

def animationSetupMain(session, **kwargs):
	session.open(AnimationSetupScreen)

def startAnimationSetup(menuid):
	if menuid == "system":
		return [( _("Animations"), animationSetupMain, "animation_setup", None)]
	return []

def sessionAnimationSetup(session, reason, **kwargs):
	setAnimation_current(config.misc.window_animation_default.value)
	setAnimation_speed(int(config.misc.window_animation_speed.value))
	setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))

	global g_orig_show, g_orig_doClose
	if g_orig_show is None:
		g_orig_show = Screen.show
	if g_orig_doClose is None:
		g_orig_doClose = Screen.doClose
	Screen.show = screen_show
	Screen.doClose = screen_doClose

def Plugins(**kwargs):
	return [
		PluginDescriptor(
			name = "Animations",
			description = "Setup UI animations",
			where = PluginDescriptor.WHERE_MENU,
			needsRestart = False,
			fnc = startAnimationSetup),
		PluginDescriptor(
			where = PluginDescriptor.WHERE_SESSIONSTART,
			needsRestart = False,
			fnc = sessionAnimationSetup),
		]
