from enigma import eConsoleAppContainer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText

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
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.cancel,
			"back": self.cancel,
			"up": self["text"].pageUp,
			"down": self["text"].pageDown
		}, -1)

		self.cmdlist = isinstance(cmdlist, list) and cmdlist or [cmdlist]
		self.newtitle = title == "Console" and _("Console") or title

		self.onShown.append(self.updateTitle)

		self.container = eConsoleAppContainer()
		self.run = 0
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
		self.run += 1
		if self.run != len(self.cmdlist):
			if self.container.execute(self.cmdlist[self.run]): #start of container application failed...
				self.runFinished(-1) # so we must call runFinished manual
		else:
			lastpage = self["text"].isAtLastPage()
			if self.showStartStopText:
				self["text"].appendText(_("Execution finished!!"))
			if self.finishedCallback is not None:
				self.finishedCallback()
			if not self.errorOcurred and self.closeOnSuccess:
				self.cancel()
			else:
				self["text"].appendText(_("\nPress OK or Exit to abort!"))
				self["key_red"].setText(_("Exit"))

	def cancel(self):
		if self.run == len(self.cmdlist):
			self.close()
			self.container.appClosed.remove(self.runFinished)
			self.container.dataAvail.remove(self.dataAvail)

	def dataAvail(self, str):
		self["text"].appendText(str)
