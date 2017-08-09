from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Button import Button
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, configfile
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Tools.BoundFunction import boundFunction
from Tools.Downloader import downloadWithProgress
from Tools.HardwareInfo import HardwareInfo
import os, urllib2, json, time, zipfile
from enigma import eTimer, eEPGCache, eConsoleAppContainer

def checkimagefiles(files):
	return len([x for x in files if 'kernel' in x and '.bin' in x or x in ('uImage', 'rootfs.bin', 'root_cfe_auto.bin', 'root_cfe_auto.jffs2', 'oe_rootfs.bin', 'e2jffs2.img', 'rootfs.tar.bz2')]) == 2

class SelectImage(Screen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.skinName="ChoiceBox"
		self.session = session
		self.imagesList = None
		self.expanded = []
		self.setTitle(_("Select Image"))
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Flash Image"))
		self["list"] = ChoiceList(list=[ChoiceEntryComponent('',((_("Retreiving image list - Please wait...")), "Waiter"))])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": boundFunction(self.close, None), 
			"red": boundFunction(self.close, None),
			"green": self.keyOk,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, -1)
		
		self.delay = eTimer()
		self.delay.callback.append(self.getImagesList)
		self.delay.start(0, True)

	def getImagesList(self, reply=None):
		list = []
		model = HardwareInfo().get_device_model()
		if not self.imagesList:
			try:
				self.imagesList = json.load(urllib2.urlopen('https://openpli.org/download/json/%s' % model))
			except:
				self.imagesList = {}
			for path, dirs, files in [x for x in os.walk('/media') if x[0].count(os.sep) <= 3]:
				for file in ['/'.join([path, x]) for x in files if x.endswith('.zip') and model in x]:
					try:
						if checkimagefiles([x.split(os.sep)[-1] for x in zipfile.ZipFile(file).namelist()]):
							medium = path.split(os.sep)[-1]
							if medium not in self.imagesList:
								self.imagesList[medium] = {}
							self.imagesList[medium][file] = { 'link': file, 'name': file.split(os.sep)[-1]}
					except:
						pass
		for catagorie in reversed(sorted(self.imagesList.keys())):
			if catagorie in self.expanded:
				list.append(ChoiceEntryComponent('expanded',((str(catagorie)), "Expander")))
				for image in reversed(sorted(self.imagesList[catagorie].keys())):
					list.append(ChoiceEntryComponent('verticalline',((str(self.imagesList[catagorie][image]['name'])), str(self.imagesList[catagorie][image]['link']))))
			else:
				list.append(ChoiceEntryComponent('expandable',((str(catagorie)), "Expander")))
		if list:
			self["list"].setList(list)
		else:
			self.session.openWithCallback(self.close, MessageBox, _("Cannot find images - please try later"), type=MessageBox.TYPE_ERROR, timeout=3)

	def keyOk(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if currentSelected[0][1] == "Expander":
			if currentSelected[0][0] in self.expanded:
				self.expanded.remove(currentSelected[0][0])
			else:
				self.expanded.append(currentSelected[0][0])
			self.getImagesList()
		elif currentSelected[0][1] != "Waiter":
			self.session.openWithCallback(self.getImagesList, FlashImage, currentSelected[0][0], currentSelected[0][1])

	def keyLeft(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)

	def keyRight(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)

	def keyUp(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)

	def keyDown(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)

class FlashImage(Screen):
	skin = """<screen position="center,center" size="640,150" flags="wfNoBorder" backgroundColor="#54242424">
		<widget name="header" position="5,10" size="e-10,50" font="Regular;40" backgroundColor="#54242424"/>
		<widget name="info" position="5,60" size="e-10,130" font="Regular;24" backgroundColor="#54242424"/>
		<widget name="progress" position="5,e-39" size="e-10,24" backgroundColor="#54242424"/>
	</screen>"""
	
	def __init__(self, session,  imagename, source):
		Screen.__init__(self, session)
		self.container = None
		
		self.downloader = None
		self.source = source
		self.imagename = imagename

		self["header"] = Label(_("Backup settings"))
		self["info"] = Label(_("Save settings and EPG data"))
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.abort,
			"red": self.abort,
		}, -1)

		self.delay = eTimer()
		self.delay.callback.append(self.confirmation)
		self.delay.start(0, True)

	def confirmation(self):
		recordings = self.session.nav.getRecordings()
		if not recordings:
			next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time > 0 and (next_rec_time - time.time()) < 360):
			message = _("Recording(s) are in progress or coming up in few seconds!\nDo you still want to flash image\n%s?") % self.imagename
		else:
			message = _("Do you want to flash image\n%s?") % self.imagename
		self.session.openWithCallback(self.backupsettings, MessageBox, message , default=False, simple=True)

	def backupsettings(self, retval):
		if retval:
		
			BACKUP_SCRIPT = "/usr/lib/enigma2/python/Plugins/Extensions/AutoBackup/settings-backup.sh"
		
			def findmedia(destination):
				def avail(path):
					if os.path.isdir(path) and not os.path.islink(path):
						statvfs = os.statvfs(path)
						return (statvfs.f_bavail * statvfs.f_frsize) / (1 << 20) >= 500 and path
				for path in [destination] + ['/media/%s' % x for x in os.listdir('/media')]:
					if avail(path):
						return path

			self.destination = findmedia(os.path.isfile(BACKUP_SCRIPT) and config.plugins.autobackup.where.value or "/media/hdd")

			if self.destination:

				destination = "/".join([self.destination, 'downloaded_images'])
				self.zippedimage = "://" in self.source and "/".join([destination, self.imagename]) or self.source
				self.unzippedimage = "/".join([destination, '%s.unzipped' % self.imagename[:-4]])
			
				if os.path.isfile(destination):
					os.remove(destination)
				if not os.path.isdir(destination):
					os.mkdir(destination)

				if os.path.isfile(BACKUP_SCRIPT):
					self["info"].setText(_("Backing up to: %s") % self.destination)
					configfile.save()
					if config.plugins.autobackup.epgcache.value:
						eEPGCache.getInstance().save()
					self.container = eConsoleAppContainer()
					self.container.appClosed.append(self.backupsettingsDone)
					try:
						if self.container.execute("%s%s'%s' %s" % (BACKUP_SCRIPT, config.plugins.autobackup.autoinstall.value and " -a " or " ", self.destination, int(config.plugins.autobackup.prevbackup.value))):
							raise Exception, "failed to execute backup script"
					except Exception, e:
						self.backupsettingsDone(e)
				else:
					self.session.openWithCallback(self.startDownload, MessageBox, _("Unable to backup settings as the AutoBackup plugin is missing, do you want to continue?"), default=False, simple=True)
			else:
				self.session.openWithCallback(self.abort, MessageBox, _("Could not find suitable media - Please insert a media (e.g. USB stick) and try again!"), type=MessageBox.TYPE_ERROR, simple=True)
		else:
			self.abort()

	def backupsettingsDone(self, retval):
		self.container = None
		if retval == 0:
			self.startDownload()
		else:	
			self.session.openWithCallback(self.abort, MessageBox, _("Error during backup settings\n%s") % reval, type=MessageBox.TYPE_ERROR, simple=True)
		
	def startDownload(self, reply=True):
		if reply:
			if "://" in self.source:
				from Tools.Downloader import downloadWithProgress
				self["header"].setText(_("Downloading Image"))
				self["info"].setText(self.imagename)
				self.downloader = downloadWithProgress(self.source, self.zippedimage)
				self.downloader.addProgress(self.downloadProgress)
				self.downloader.addEnd(self.downloadEnd)
				self.downloader.addError(self.downloadError)
				self.downloader.start()
			else:
				self.unzip()
		else:
			self.abort()

	def downloadProgress(self, current, total):
		self["progress"].setValue(int(100 * current / total))

	def downloadError(self, reason, status):
		self.downloader.stop()
		self.session.openWithCallback(self.abort, MessageBox, _("Error during downloading image\n%s\n%s") % (self.imagename, reason), type=MessageBox.TYPE_ERROR, simple=True)
		
	def downloadEnd(self):
		self.downloader.stop()
		self.unzip()
		
	def unzip(self):
		try:
			zipfile.ZipFile(self.zippedimage, 'r').extractall(self.unzippedimage)
			self.flashimage()	
		except:
			self.session.openWithCallback(self.abort, MessageBox, _("Error during unzipping image\n%s\n%s") % (self.imagename, reason), type=MessageBox.TYPE_ERROR, simple=True)

	def flashimage(self):
		def findimagefiles(path):
			for path, subdirs, files in os.walk(path):
				if not subdirs and files:
					return checkimagefiles(files) and path
		imagefiles = findimagefiles(self.unzippedimage)
		if imagefiles:
				self.container = eConsoleAppContainer()
				self.container.appClosed.append(self.FlashimageDone)
				try:
					if self.container.execute("/usr/bin/ofgwrite '%s'" % imagefiles):
						raise Exception, "failed to execute ofgwrite"
				except Exception, e:
					self.FlashimageDone(e)
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Image to install is invalid\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def FlashimageDone(self, retval):
		if retval == 0:
				self["header"].setText(_("Flashing image completed"))
				self["info"].setText(_("Press exit to continue"))
				self["progress"].hide()
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Flashing image was not succesfull\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def abort(self, reply=None):
		if self.downloader:
			self.downloader.stop()
		if self.container:
			self.container = None
		self.close()
