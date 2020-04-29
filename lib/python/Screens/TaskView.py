from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Sources.Progress import Progress
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Components.Task import job_manager
from InfoBarGenerics import InfoBarNotifications
from Tools import Notifications
from Screen import Screen
from Screens.MessageBox import MessageBox
import Screens.Standby

class JobView(InfoBarNotifications, Screen, ConfigListScreen):
	def __init__(self, session, job, parent=None, cancelable = True, backgroundable = True, afterEventChangeable = True):
		Screen.__init__(self, session, parent)
		InfoBarNotifications.__init__(self)
		ConfigListScreen.__init__(self, [])
		self.parent = parent
		self.job = job
		self.setTitle(_("Job overview"))

		self["job_name"] = StaticText(job.name)
		self["job_progress"] = Progress()
		self["job_task"] = StaticText()
		self["summary_job_name"] = StaticText(job.name)
		self["summary_job_progress"] = Progress()
		self["summary_job_task"] = StaticText()
		self["job_status"] = StaticText()

		self.cancelable = cancelable
		self.backgroundable = backgroundable

		self["key_green"] = StaticText("")

		if self.cancelable:
			self["key_red"] = StaticText(_("Cancel"))
		else:
			self["key_red"] = StaticText("")

		if self.backgroundable:
			self["key_blue"] = StaticText(_("Background"))
		else:
			self["key_blue"] = StaticText("")

		self.onShow.append(self.windowShow)
		self.onHide.append(self.windowHide)

		self["setupActions"] = ActionMap(["ColorActions", "SetupActions"],
		{
			"green": self.ok,
			"red": self.abort,
			"blue": self.background,
			"cancel": self.abort,
			"ok": self.ok,
		}, -2)

		self.settings = ConfigSubsection()
		if SystemInfo["DeepstandbySupport"]:
			shutdownString = _("go to deep standby")
		else:
			shutdownString = _("shut down")
		self.settings.afterEvent = ConfigSelection(choices = [("nothing", _("do nothing")), ("close", _("Close")), ("standby", _("go to standby")), ("deepstandby", shutdownString)], default = self.job.afterEvent or "nothing")
		self.job.afterEvent = self.settings.afterEvent.getValue()
		self.afterEventChangeable = afterEventChangeable
		self.setupList()
		self.state_changed()

	def setupList(self):
		if self.afterEventChangeable:
			self["config"].setList( [ getConfigListEntry(_("After event"), self.settings.afterEvent) ])
		else:
			self["config"].hide()
		self.job.afterEvent = self.settings.afterEvent.getValue()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setupList()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setupList()

	def windowShow(self):
		job_manager.visible = True
		self.job.state_changed.append(self.state_changed)

	def windowHide(self):
		job_manager.visible = False
		if len(self.job.state_changed) > 0:
			self.job.state_changed.remove(self.state_changed)

	def state_changed(self):
		j = self.job
		self["job_progress"].range = j.end
		self["summary_job_progress"].range = j.end
		self["job_progress"].value = j.progress
		self["summary_job_progress"].value = j.progress
		#print "JobView::state_changed:", j.end, j.progress
		self["job_status"].text = j.getStatustext()
		if j.status == j.IN_PROGRESS:
			self["job_task"].text = j.tasks[j.current_task].name
			self["summary_job_task"].text = j.tasks[j.current_task].name
		else:
			self["job_task"].text = ""
			self["summary_job_task"].text = j.getStatustext()
		if j.status in (j.FINISHED, j.FAILED):
			self.performAfterEvent()
			self.backgroundable = False
			self["key_blue"].setText("")
			if j.status == j.FINISHED:
				self["key_green"].setText(_("OK"))
				self.cancelable = False
				self["key_red"].setText("")
			elif j.status == j.FAILED:
				self.cancelable = True
				self["key_red"].setText(_("Cancel"))

	def background(self):
		if self.backgroundable:
			self.close(True)

	def ok(self):
		if self.job.status in (self.job.FINISHED, self.job.FAILED):
			self.close(False)
		else:
			self.background()

	def abort(self):
		if self.job.status == self.job.NOT_STARTED:
			job_manager.active_jobs.remove(self.job)
			self.close(False)
		elif self.job.status == self.job.IN_PROGRESS and self.cancelable:
			self.job.cancel()
		else:
			self.close(False)

	def performAfterEvent(self):
		self["config"].hide()
		if self.settings.afterEvent.getValue() == "nothing":
			return
		elif self.settings.afterEvent.getValue() == "close" and self.job.status == self.job.FINISHED:
			self.close(False)
		if self.settings.afterEvent.getValue() == "deepstandby":
			if not Screens.Standby.inTryQuitMainloop:
				Notifications.AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, _("A sleep timer wants to shut down\nyour receiver. Shutdown now?"), timeout = 20)
		elif self.settings.afterEvent.getValue() == "standby":
			if not Screens.Standby.inStandby:
				Notifications.AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, _("A sleep timer wants to set your\nreceiver to standby. Do that now?"), timeout = 20)

	def checkNotifications(self):
		InfoBarNotifications.checkNotifications(self)
		if not Notifications.notifications:
			if self.settings.afterEvent.getValue() == "close" and self.job.status == self.job.FAILED:
				self.close(False)

	def sendStandbyNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.Standby)

	def sendTryQuitMainloopNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, 1)
