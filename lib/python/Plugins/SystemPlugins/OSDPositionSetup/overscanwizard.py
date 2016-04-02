from Screens.Screen import Screen
from Screens.Standby import QuitMainloopScreen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSlider, getConfigListEntry, ConfigYesNo
from Components.Label import Label
from Plugins.SystemPlugins.OSDPositionSetup.plugin import setPosition, setConfiguredPosition
from enigma import quitMainloop, eTimer
import os

class OverscanWizard(Screen, ConfigListScreen):
	def __init__(self, session):
		self.skin = """<screen position="fill">
				<ePixmap pixmap="skin_default/overscan1920x1080.png" position="0,0" size="1920,1080" zPosition="-2" alphatest="on" />
				<eLabel position="378,180" size="1244,686" zPosition="-1"/>
				<widget name="title" position="383,185" size="1234,50" font="Regular;40" foregroundColor="blue"/>
				<widget name="introduction" position="383,235" size="1234,623" halign="center" valign="center" font="Regular;30"/>
				<widget name="config" position="383,635" size="1234,226" font="Regular;30" itemHeight="40"/>
			</screen>"""

		Screen.__init__(self, session)
		self.setup_title = _("Overscan wizard")

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["title"] = Label(_("Overscan Wizard"))
		self["introduction"] = Label()
		
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"ok": self.keyGo,
		}, -2)

		self.step = 1
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.onChangedEntry = []
		self.setScreen()
		
		self.countdown = 10
		self.Timer = eTimer()
		self.Timer.callback.append(self.TimerTimeout)
		self.Timer.start(1000)
		
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		from enigma import eSize, ePoint
		lenlist = len(self.list)*40
		self["config"].instance.move(ePoint(383, 863 - lenlist))
		self["config"].instance.resize(eSize(1234, lenlist))
		self["introduction"].instance.resize(eSize(1234, 623 - lenlist))

	def setScreen(self):
		self.list = []
		if self.step == 1:
			self["introduction"].setText(_("This overscan hazerd helps you to setup your TV in a proper way.\n\n"
				"It seems a lot of TVs remove the overscan area by default. "
				"This means you're always watching to \"zoomed in\" HD and this also means parts of our new Full-HD skin may be invisible on your TV.\n\n"
				"The yellow area is 5% underscanned on all sides.\n"
				"The green area is 10% underscanned on all sides.\n\n"
				"In other words, if the yellow box meets all for sides of your screen, then you have at least 5% overscan on all sides.\n\n"
				"If you see the tips of all eight arrowheads, then you have 0% overscan.\n\n"
				"Test Pattern by TigerDave - www.tigerdave.com/ht_menu.htm"))
			self.yes_no = ConfigYesNo(default = True)
			self.list.append(getConfigListEntry(_("Do you see all the eight arrorheads?"), self.yes_no))
		elif self.step == 2:
			self.Timer.stop()
			self["title"].setText(_("Overscan Wizard"))
			self["introduction"].setText(_("It seems you did not see all the eight error heads. This means your TV is "
				"not configured properly -or- your TV always removes the overscan area.\n\n" 
				"Please refer to your TVs manual or http://openpli.org/forum/ to find how your TV could be configured correctly. "
				"Find like terms as full-HD, picture-by-picture, enz...\n\n"))
			self.list.append(getConfigListEntry(_("Did you accomplished to see all eight arrow heads?"), self.yes_no))
			self.yes_no.value = True
		elif self.step == 3:
			self["introduction"].setText(_("You could not accomplished to see all eight error heads. This means your TV does "
				"zoom-in a full HD screen and you do not see the complete picture. In addition this "
				"may mean you could miss information of the OSD (e.g. volume bars and more).\n\n"
				"You can now change the OSD position and size with the options below until you see the eight arrow heads.\n\n"
				"When done press OK.\n\n"
				"Note: you can always repleat this Overscan Wizard via\n\nmenu->installation->system->OSD-setup"))
			self.dst_left = ConfigSlider(default = config.plugins.OSDPositionSetup.dst_left.value, increment = 1, limits = (0, 720))
			self.dst_width = ConfigSlider(default = config.plugins.OSDPositionSetup.dst_width.value, increment = 1, limits = (0, 720))
			self.dst_top = ConfigSlider(default = config.plugins.OSDPositionSetup.dst_top.value, increment = 1, limits = (0, 576))
			self.dst_height = ConfigSlider(default = config.plugins.OSDPositionSetup.dst_height.value, increment = 1, limits = (0, 576))
			self.list.append(getConfigListEntry(_("left"), self.dst_left))
			self.list.append(getConfigListEntry(_("width"), self.dst_width))
			self.list.append(getConfigListEntry(_("top"), self.dst_top))
			self.list.append(getConfigListEntry(_("height"), self.dst_height))
		elif self.step == 4:
			self["introduction"].setText(_("You could not accomplished to see all eight error heads. This means your TV does "
				"zoom-in a full HD screen and you do not see the complete picture. In addition this "
				"may mean you could miss information of the OSD (e.g. volume bars and more).\n\n"
				"You settop box is also not capable to ajust the OSD position and size. When want to have all parts of the skin visible "
				"you should revert to a skin that does not use the overscan area.\n\n"
				"When you choose to use an alternative skin enigma2 will be restarted"
				"Note: you can always repleat this Overscan Wizard via\n\nmenu->installation->system->OSD-setup"))
			self.yes_no.value = False
			self.list.append(getConfigListEntry(_("Do you want to select an alternative skin?"), self.yes_no))
		elif self.step == 5:
			self.Timer.stop()
			self["title"].setText(_("Overscan Wizard"))
			self["introduction"].setText(_("The overscan wizard has been completed."))
			self.yes_no.value = True
			self.list.append(getConfigListEntry(_("Do you want to quit the overscan wizard?"), self.yes_no))
		elif self.step == 6:
			config.skin.primary_skin.value = "PLi-HD/skin.xml"
			config.misc.do_overscanwizard.value = False
			config.save()
			self["introduction"].setText(_("Enigma2 will be rebooted to select the alternative skin"))
			quitMainloop(3)
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if self["config"].instance:
			self.__layoutFinished()
		
	def TimerTimeout(self):
		self.countdown -= 1
		self["title"].setText(_("Overscan Wizard") + " %s" % self.countdown)
		if not(self.countdown):
			self.keyCancel()
		
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 1 and str(self["config"].getCurrent()[1].getText()) or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		if self.step == 3:
			self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		if self.step == 3:
			self.setPreviewPosition()

	def keyGo(self):
		if self.step == 1:
			self.step = self.yes_no.value and 5 or 2
		elif self.step == 2:
			self.step = self.yes_no.value and 5 or os.path.exists("/proc/stb/fb/dst_left") and 3 or 4
		elif self.step == 3:
			config.plugins.OSDPositionSetup.dst_left.value = self.dst_left.value
			config.plugins.OSDPositionSetup.dst_width.value = self.dst_width.value
			config.plugins.OSDPositionSetup.dst_top.value = self.dst_top.value
			config.plugins.OSDPositionSetup.dst_height.value = self.dst_height.value
			config.plugins.OSDPositionSetup.save()
			self.step = 5
		elif self.step == 4:
			self.step = self.yes_no.value and 6 or 5
		elif self.step == 5:
			if self.yes_no.value:
				config.misc.do_overscanwizard.value = False
				config.save()
				self.keyCancel()
			else:
				self.step = 1
		self.setScreen()		
			
	def setPreviewPosition(self):
		setPosition(int(self.dst_left.value), int(self.dst_width.value), int(self.dst_top.value), int(self.dst_height.value))

	def keyCancel(self):
		if not self.step == 3:
			setConfiguredPosition()
		self.close()
