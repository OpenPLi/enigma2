from enigma import eConsoleAppContainer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox

class Console(Screen):
	#TODO move this to skin.xml
	skin = """
		<screen position="100,100" size="550,400" title="Command execution..." >
			<widget name="text" position="0,0" size="550,400" font="Console;14" />
		</screen>"""

	def __init__(self, session, title = "Console", cmdlist = None, finishedCallback = None, closeOnSuccess = False, showStartStopText=True, skin=None):
		Screen.__init__(self, session)

		self.finishedCallback = finishedCallback
		self.closeOnSuccess = closeOnSuccess
		self.showStartStopText = showStartStopText
		if skin:
			self.skinName = [skin, "Console"]

		self.errorOcurred = False

		self["text"] = ScrollLabel("")
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Hide"))
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions"],
		{
			"ok": self.closeConsole,
			"back": self.closeConsole,
			"up": self["text"].pageUp,
			"down": self["text"].pageDown,
			"green": self.toggleHideShow,
			"red": self.cancel,
		}, -1)

		self.cmdlist = isinstance(cmdlist, list) and cmdlist or [cmdlist]
		self.newtitle = title == "Console" and _("Console") or title
		self.cancel_msg = None

		self.onShown.append(self.updateTitle)

		self.container = eConsoleAppContainer()
		self.run = 0
		self.finished = False
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun) # dont start before gui is finished

	def updateTitle(self):
		self.setTitle(self.newtitle)

	def startRun(self):
		if self.showStartStopText:
			self["text"].setText(_("Execution progress:") + "\n\n")
		print "Console: executing in run", self.run, " the command:", self.cmdlist[self.run]
		if self.container.execute(self.cmdlist[self.run]): #start of container application failed...
			self.runFinished(-1) # so we must call runFinished manual

	def runFinished(self, retval):
		if retval:
			self.errorOcurred = True
			self.show()
		self.run += 1
		if self.run != len(self.cmdlist):
			if self.container.execute(self.cmdlist[self.run]): #start of container application failed...
				self.runFinished(-1) # so we must call runFinished manual
		else:
			self.show()
			self.finished = True
			lastpage = self["text"].isAtLastPage()
			if self.cancel_msg:
				self.cancel_msg.close()
			if self.showStartStopText:
				self["text"].appendText(_("Execution finished!!"))
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOcurred and self.closeOnSuccess:
				self.closeConsole()
			else:
				self["text"].appendText(_("\nPress OK or Exit to abort!"))
				self["key_red"].setText(_("Exit"))
				self["key_green"].setText("")

	def toggleHideShow(self):
		if self.finished:
			return
		if self.shown:
			self.hide()
		else:
			self.show()


	def cancel(self):
		if self.finished:
			self.closeConsole()
		else:
			self.cancel_msg = self.session.openWithCallback(self.cancelCallback, MessageBox, _("Cancel execution?"), type=MessageBox.TYPE_YESNO, default=False)

	def cancelCallback(self, ret = None):
		self.cancel_msg = None
		if ret:
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)
			self.container.kill()
			self.close()

	def closeConsole(self):
		if self.finished:
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)
			self.close()
		else:
			self.show()

	def dataAvail(self, str):
		self["text"].appendText(str)
