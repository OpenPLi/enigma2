from Screens.Setup import Setup
from Screens.LocationBox import MovieLocationBox, TimeshiftLocationBox
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.config import config, ConfigSelection
from Tools.Directories import fileExists
from Components.UsageConfig import preferredPath


class RecordPathsSettings(Setup):
	def __init__(self, session):
		self.createConfig()
		Setup.__init__(self, session, None)
		self.setTitle(_("Recording paths"))

	def checkReadWriteDir(self, configele):
		value = configele.value
		print("checkReadWrite: ", value)
		if not value or value in [x[0] for x in self.styles] or fileExists(value, "w"):
			configele.last_value = value
			return True
		else:
			configele.value = configele.last_value
			self.session.open(
				MessageBox,
				_("The directory %s is not writable.\nMake sure you select a writable directory instead.") % value,
				type=MessageBox.TYPE_ERROR
				)
			return False

	def createConfig(self):
		self.styles = [("<default>", _("<Default movie location>")), ("<current>", _("<Current movielist location>")), ("<timer>", _("<Last timer location>"))]
		styles_keys = [x[0] for x in self.styles]
		tmp = config.movielist.videodirs.value
		default = config.usage.default_path.value
		if default and default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		print("DefaultPath: ", default, tmp)
		self.default_dirname = ConfigSelection(default=default, choices=[("", _("<Default movie location>"))] + tmp)
		tmp = config.movielist.videodirs.value
		default = config.usage.timer_path.value
		if default not in tmp and default not in styles_keys:
			tmp = tmp[:]
			tmp.append(default)
		print("TimerPath: ", default, tmp)
		self.timer_dirname = ConfigSelection(default=default, choices=self.styles + tmp)
		tmp = config.movielist.videodirs.value
		default = config.usage.instantrec_path.value
		if default not in tmp and default not in styles_keys:
			tmp = tmp[:]
			tmp.append(default)
		print("InstantrecPath: ", default, tmp)
		self.instantrec_dirname = ConfigSelection(default=default, choices=self.styles + tmp)
		default = config.usage.timeshift_path.value
		tmp = config.usage.allowed_timeshift_paths.value
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		print("TimeshiftPath: ", default, tmp)
		self.timeshift_dirname = ConfigSelection(default=default, choices=tmp)
		self.default_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.timer_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.instantrec_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.timeshift_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)

	def createSetup(self):
		self.list = []
		if config.usage.setup_level.index >= 2:
			self.default_entry = (_("Default movie location"), self.default_dirname)
			self.list.append(self.default_entry)
			self.timer_entry = (_("Timer recording location"), self.timer_dirname)
			self.list.append(self.timer_entry)
			self.instantrec_entry = (_("Instant recording location"), self.instantrec_dirname)
			self.list.append(self.instantrec_entry)
		else:
			self.default_entry = (_("Movie location"), self.default_dirname)
			self.list.append(self.default_entry)
		self.timeshift_entry = (_("Timeshift location"), self.timeshift_dirname)
		self.list.append(self.timeshift_entry)
		self["config"].setList(self.list)

	def keySelect(self):
		currentry = self["config"].getCurrent()
		self.lastvideodirs = config.movielist.videodirs.value
		self.lasttimeshiftdirs = config.usage.allowed_timeshift_paths.value
		if config.usage.setup_level.index >= 2:
			txt = _("Default movie location")
		else:
			txt = _("Movie location")
		if currentry == self.default_entry:
			self.entrydirname = self.default_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				txt,
				preferredPath(self.default_dirname.value)
			)
		elif currentry == self.timer_entry:
			self.entrydirname = self.timer_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				_("Initial location in new timers"),
				preferredPath(self.timer_dirname.value)
			)
		elif currentry == self.instantrec_entry:
			self.entrydirname = self.instantrec_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				_("Location for instant recordings"),
				preferredPath(self.instantrec_dirname.value)
			)
		elif currentry == self.timeshift_entry:
			self.entrydirname = self.timeshift_dirname
			config.usage.timeshift_path.value = self.timeshift_dirname.value
			self.session.openWithCallback(
				self.dirnameSelected,
				TimeshiftLocationBox
			)

	def dirnameSelected(self, res):
		if res is not None:
			self.entrydirname.value = res
			if config.movielist.videodirs.value != self.lastvideodirs:
				styles_keys = [x[0] for x in self.styles]
				tmp = config.movielist.videodirs.value
				default = self.default_dirname.value
				if default and default not in tmp:
					tmp = tmp[:]
					tmp.append(default)
				self.default_dirname.setChoices([("", _("<Default movie location>"))] + tmp, default=default)
				tmp = config.movielist.videodirs.value
				default = self.timer_dirname.value
				if default not in tmp and default not in styles_keys:
					tmp = tmp[:]
					tmp.append(default)
				self.timer_dirname.setChoices(self.styles + tmp, default=default)
				tmp = config.movielist.videodirs.value
				default = self.instantrec_dirname.value
				if default not in tmp and default not in styles_keys:
					tmp = tmp[:]
					tmp.append(default)
				self.instantrec_dirname.setChoices(self.styles + tmp, default=default)
				self.entrydirname.value = res
			if config.usage.allowed_timeshift_paths.value != self.lasttimeshiftdirs:
				tmp = config.usage.allowed_timeshift_paths.value
				default = self.instantrec_dirname.value
				if default not in tmp:
					tmp = tmp[:]
					tmp.append(default)
				self.timeshift_dirname.setChoices(tmp, default=default)
				self.entrydirname.value = res
			if self.entrydirname.last_value != res:
				self.checkReadWriteDir(self.entrydirname)

	def keySave(self):
		currentry = self["config"].getCurrent()
		if self.checkReadWriteDir(currentry[1]):
			config.usage.default_path.value = self.default_dirname.value
			config.usage.timer_path.value = self.timer_dirname.value
			config.usage.instantrec_path.value = self.instantrec_dirname.value
			config.usage.timeshift_path.value = self.timeshift_dirname.value
			config.usage.default_path.save()
			config.usage.timer_path.save()
			config.usage.instantrec_path.save()
			config.usage.timeshift_path.save()
			self.close()
