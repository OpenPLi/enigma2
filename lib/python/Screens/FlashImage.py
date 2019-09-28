from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Standby import getReasons
from Components.Sources.StaticText import StaticText
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, configfile
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.SystemInfo import SystemInfo
from Tools.BoundFunction import boundFunction
from Tools.Downloader import downloadWithProgress
from Tools.HardwareInfo import HardwareInfo
from Tools.Multiboot import GetImagelist, GetCurrentImage, GetCurrentImageMode
import os, urllib2, json, time, zipfile, shutil

from enigma import eEPGCache

def checkimagefiles(files):
	return len([x for x in files if 'kernel' in x and '.bin' in x or x in ('uImage', 'rootfs.bin', 'root_cfe_auto.bin', 'root_cfe_auto.jffs2', 'oe_rootfs.bin', 'e2jffs2.img', 'rootfs.tar.bz2', 'rootfs.ubi')]) == 2

class SelectImage(Screen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.session = session
		self.jsonlist = {}
		self.imagesList = {}
		self.setIndex = 0
		self.expanded = []
		self.setTitle(_("Select Image"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["description"] = StaticText()
		self["list"] = ChoiceList(list=[ChoiceEntryComponent('',((_("Retrieving image list - Please wait...")), "Waiter"))])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": boundFunction(self.close, None),
			"red": boundFunction(self.close, None),
			"green": self.keyOk,
			"yellow": self.keyDelete,
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

		self.callLater(self.getImagesList)

	def getImagesList(self):

		def getImages(path, files):
			for file in [x for x in files if os.path.splitext(x)[1] == ".zip" and model in x]:
				try:
					if checkimagefiles([x.split(os.sep)[-1] for x in zipfile.ZipFile(file).namelist()]):
						if "Downloaded Images" not in self.imagesList:
							self.imagesList["Downloaded Images"] = {}
						self.imagesList["Downloaded Images"][file] = {'link': file, 'name': file.split(os.sep)[-1]}
				except:
					pass

		model = HardwareInfo().get_machine_name()

		if not self.imagesList:
			if not self.jsonlist:
				try:
					self.jsonlist = dict(json.load(urllib2.urlopen('http://downloads.openpli.org/json/%s' % model)))
					if config.usage.alternative_imagefeed.value:
						self.jsonlist.update(dict(json.load(urllib2.urlopen('%s%s' % (config.usage.alternative_imagefeed.value, model)))))
				except:
					pass
			self.imagesList = dict(self.jsonlist)

			for media in ['/media/%s' % x for x in os.listdir('/media')] + (['/media/net/%s' % x for x in os.listdir('/media/net')] if os.path.isdir('/media/net') else []):
				if not(SystemInfo['HasMMC'] and "/mmc" in media) and os.path.isdir(media):
					try:
						getImages(media, [os.path.join(media, x) for x in os.listdir(media) if os.path.splitext(x)[1] == ".zip" and model in x])
						if "downloaded_images" in os.listdir(media):
							media = os.path.join(media, "downloaded_images")
							if os.path.isdir(media) and not os.path.islink(media) and not os.path.ismount(media):
								getImages(media, [os.path.join(media, x) for x in os.listdir(media) if os.path.splitext(x)[1] == ".zip" and model in x])
								for dir in [dir for dir in [os.path.join(media, dir) for dir in os.listdir(media)] if os.path.isdir(dir) and os.path.splitext(dir)[1] == ".unzipped"]:
									shutil.rmtree(dir)
					except:
						pass

		list = []
		for catagorie in reversed(sorted(self.imagesList.keys())):
			if catagorie in self.expanded:
				list.append(ChoiceEntryComponent('expanded',((str(catagorie)), "Expander")))
				for image in reversed(sorted(self.imagesList[catagorie].keys())):
					list.append(ChoiceEntryComponent('verticalline',((str(self.imagesList[catagorie][image]['name'])), str(self.imagesList[catagorie][image]['link']))))
			else:
				for image in self.imagesList[catagorie].keys():
					list.append(ChoiceEntryComponent('expandable',((str(catagorie)), "Expander")))
					break
		if list:
			self["list"].setList(list)
			if self.setIndex:
				self["list"].moveToIndex(self.setIndex if self.setIndex < len(list) else len(list) - 1)
				if self["list"].l.getCurrentSelection()[0][1] == "Expander":
					self.setIndex -= 1
					if self.setIndex:
						self["list"].moveToIndex(self.setIndex if self.setIndex < len(list) else len(list) - 1)
				self.setIndex = 0
			self.selectionChanged()
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

	def keyDelete(self):
		currentSelected= self["list"].l.getCurrentSelection()[0][1]
		if not("://" in currentSelected or currentSelected in ["Expander", "Waiter"]):
			try:
				os.remove(currentSelected)
				currentSelected = ".".join([currentSelected[:-4], "unzipped"])
				if os.path.isdir(currentSelected):
					shutil.rmtree(currentSelected)
				self.setIndex = self["list"].getSelectedIndex()
				self.imagesList = []
				self.getImagesList()
			except:
				self.session.open(MessageBox, _("Cannot delete downloaded image"), MessageBox.TYPE_ERROR, timeout=3)

	def selectionChanged(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if "://" in currentSelected[0][1] or currentSelected[0][1] in ["Expander", "Waiter"]:
			self["key_yellow"].setText("")
		else:
			self["key_yellow"].setText(_("Delete image"))
		if currentSelected[0][1] == "Waiter":
			self["key_green"].setText("")
		else:
			if currentSelected[0][1] == "Expander":
				self["key_green"].setText(_("Compress") if currentSelected[0][0] in self.expanded else _("Expand"))
				self["description"].setText("")
			else:
				self["key_green"].setText(_("Flash Image"))
				self["description"].setText(currentSelected[0][1])

	def keyLeft(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)
		self.selectionChanged()

	def keyRight(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)
		self.selectionChanged()

	def keyUp(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.selectionChanged()

	def keyDown(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.selectionChanged()

class FlashImage(Screen):
	skin = """<screen position="center,center" size="640,150" flags="wfNoBorder" backgroundColor="#54242424">
		<widget name="header" position="5,10" size="e-10,50" font="Regular;40" backgroundColor="#54242424"/>
		<widget name="info" position="5,60" size="e-10,130" font="Regular;24" backgroundColor="#54242424"/>
		<widget name="progress" position="5,e-39" size="e-10,24" backgroundColor="#54242424"/>
	</screen>"""

	BACKUP_SCRIPT = "/usr/lib/enigma2/python/Plugins/Extensions/AutoBackup/settings-backup.sh"

	def __init__(self, session,  imagename, source):
		Screen.__init__(self, session)
		self.containerbackup = None
		self.containerofgwrite = None
		self.getImageList = None
		self.downloader = None
		self.source = source
		self.imagename = imagename
		self.reasons = getReasons(session)

		self["header"] = Label(_("Backup settings"))
		self["info"] = Label(_("Save settings and EPG data"))
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.abort,
			"red": self.abort,
			"ok": self.ok,
			"green": self.ok,
		}, -1)

		self.callLater(self.confirmation)

	def confirmation(self):
		if self.reasons:
			self.message = _("%s\nDo you still want to flash image\n%s?") % (self.reasons, self.imagename)
		else:
			self.message = _("Do you want to flash image\n%s") % self.imagename
		if SystemInfo["canMultiBoot"]:
			self.getImageList = GetImagelist(self.getImagelistCallback)
		else:
			choices = [(_("Yes, with backup"), "with backup"), (_("Yes, without backup"), "without backup"), (_("No, do not flash image"), False)]
			self.session.openWithCallback(self.checkMedia, MessageBox, self.message , list=choices, default=False, simple=True)

	def getImagelistCallback(self, imagedict):
		self.getImageList = None
		choices = []
		currentimageslot = GetCurrentImage()
		for x in range(1, SystemInfo["canMultiBoot"][1] + 1):
			choices.append(((_("slot%s - %s (current image) with, backup") if x == currentimageslot else _("slot%s - %s, with backup")) % (x, imagedict[x]['imagename']), (x, "with backup")))
		for x in range(1, SystemInfo["canMultiBoot"][1] + 1):
			choices.append(((_("slot%s - %s (current image), without backup") if x == currentimageslot else _("slot%s - %s, without backup")) % (x, imagedict[x]['imagename']), (x, "without backup")))
		choices.append((_("No, do not flash image"), False))
		self.session.openWithCallback(self.checkMedia, MessageBox, self.message, list=choices, default=currentimageslot, simple=True)

	def checkMedia(self, retval):
		if retval:
			if SystemInfo["canMultiBoot"]:
				self.multibootslot = retval[0]
				doBackup = retval[1] == "with backup"
			else:
				doBackup = retval == "with backup"

			def findmedia(path):
				def avail(path):
					if not '/mmc' in path and os.path.isdir(path) and os.access(path, os.W_OK):
						try:
							statvfs = os.statvfs(path)
							return (statvfs.f_bavail * statvfs.f_frsize) / (1 << 20)
						except:
							pass

				def checkIfDevice(path, diskstats):
					st_dev = os.stat(path).st_dev
					return (os.major(st_dev), os.minor(st_dev)) in diskstats

				diskstats = [(int(x[0]), int(x[1])) for x in [x.split()[0:3] for x in open('/proc/diskstats').readlines()] if x[2].startswith("sd")]
				if os.path.isdir(path) and checkIfDevice(path, diskstats) and avail(path) > 500:
					return (path, True)
				mounts = []
				devices = []
				for path in ['/media/%s' % x for x in os.listdir('/media')] + (['/media/net/%s' % x for x in os.listdir('/media/net')] if os.path.isdir('/media/net') else []):
					if checkIfDevice(path, diskstats):
						devices.append((path, avail(path)))
					else:
						mounts.append((path, avail(path)))
				devices.sort(key=lambda x: x[1], reverse=True)
				mounts.sort(key=lambda x: x[1], reverse=True)
				return ((devices[0][1] > 500 and (devices[0][0], True)) if devices else mounts and mounts[0][1] > 500 and (mounts[0][0], False)) or (None, None)

			self.destination, isDevice = findmedia(os.path.isfile(self.BACKUP_SCRIPT) and config.plugins.autobackup.where.value or "/media/hdd")

			if self.destination:

				destination = os.path.join(self.destination, 'downloaded_images')
				self.zippedimage = "://" in self.source and os.path.join(destination, self.imagename) or self.source
				self.unzippedimage = os.path.join(destination, '%s.unzipped' % self.imagename[:-4])

				try:
					if os.path.isfile(destination):
						os.remove(destination)
					if not os.path.isdir(destination):
						os.mkdir(destination)
					if doBackup:
						if isDevice:
							self.startBackupsettings(True)
						else:
							self.session.openWithCallback(self.startBackupsettings, MessageBox, _("Can only find a network drive to store the backup this means after the flash the autorestore will not work. Alternativaly you can mount the network drive after the flash and perform a manufacurer reset to autorestore"), simple=True)
					else:
						self.startDownload()
				except:
					self.session.openWithCallback(self.abort, MessageBox, _("Unable to create the required directories on the media (e.g. USB stick or Harddisk) - Please verify media and try again!"), type=MessageBox.TYPE_ERROR, simple=True)
			else:
				self.session.openWithCallback(self.abort, MessageBox, _("Could not find suitable media - Please remove some downloaded images or insert a media (e.g. USB stick) with sufficiant free space and try again!"), type=MessageBox.TYPE_ERROR, simple=True)
		else:
			self.abort()

	def startBackupsettings(self, retval):
		if retval:
			if os.path.isfile(self.BACKUP_SCRIPT):
				self["info"].setText(_("Backing up to: %s") % self.destination)
				configfile.save()
				if config.plugins.autobackup.epgcache.value:
					eEPGCache.getInstance().save()
				self.containerbackup = Console()
				self.containerbackup.ePopen("%s%s'%s' %s" % (self.BACKUP_SCRIPT, config.plugins.autobackup.autoinstall.value and " -a " or " ", self.destination, int(config.plugins.autobackup.prevbackup.value)), self.backupsettingsDone)
			else:
				self.session.openWithCallback(self.startDownload, MessageBox, _("Unable to backup settings as the AutoBackup plugin is missing, do you want to continue?"), default=False, simple=True)
		else:
			self.abort()

	def backupsettingsDone(self, data, retval, extra_args):
		self.containerbackup = None
		if retval == 0:
			self.startDownload()
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Error during backup settings\n%s") % reval, type=MessageBox.TYPE_ERROR, simple=True)

	def startDownload(self, reply=True):
		self.show()
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
		self["header"].setText(_("Unzipping Image"))
		self["info"].setText("%s\n%s"% (self.imagename, _("Please wait")))
		self["progress"].hide()
		self.callLater(self.doUnzip)

	def doUnzip(self):
		try:
			zipfile.ZipFile(self.zippedimage, 'r').extractall(self.unzippedimage)
			self.flashimage()
		except:
			self.session.openWithCallback(self.abort, MessageBox, _("Error during unzipping image\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def flashimage(self):
		self["header"].setText(_("Flashing Image"))
		def findimagefiles(path):
			for path, subdirs, files in os.walk(path):
				if not subdirs and files:
					return checkimagefiles(files) and path
		imagefiles = findimagefiles(self.unzippedimage)
		if imagefiles:
			if SystemInfo["canMultiBoot"]:
				command = "/usr/bin/ofgwrite -k -r -m%s '%s'" % (self.multibootslot, imagefiles)
			else:
				command = "/usr/bin/ofgwrite -k -r '%s'" % imagefiles
			self.containerofgwrite = Console()
			self.containerofgwrite.ePopen(command, self.FlashimageDone)
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Image to install is invalid\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def FlashimageDone(self, data, retval, extra_args):
		self.containerofgwrite = None
		if retval == 0:
			self["header"].setText(_("Flashing image successful"))
			self["info"].setText(_("%s\nPress ok for multiboot selection\nPress exit to close") % self.imagename)
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Flashing image was not successful\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def abort(self, reply=None):
		if self.getImageList or self.containerofgwrite:
			return 0
		if self.downloader:
			self.downloader.stop()
		if self.containerbackup:
			self.containerbackup.killAll()
		self.close()

	def ok(self):
		if self["header"].text == _("Flashing image successful"):
			self.session.openWithCallback(self.abort, MultibootSelection)
		else:
			return 0

class MultibootSelection(SelectImage):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.skinName = "SelectImage"
		self.session = session
		self.imagesList = None
		self.expanded = []
		self.setTitle(_("Select Multiboot"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Reboot"))
		self["list"] = ChoiceList(list=[ChoiceEntryComponent('',((_("Retrieving image slots - Please wait...")), "Waiter"))])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.keyOk,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.cancel, True),
		}, -1)

		self.callLater(self.getBootOptions)

	def cancel(self, value=None):
		self.container = Console()
		self.container.ePopen('umount /tmp/startupmount', boundFunction(self.unmountCallback, value))

	def unmountCallback(self, value, data=None, retval=None, extra_args=None):
		self.container.killAll()
		if not os.path.ismount('/tmp/startupmount'):
			os.rmdir('/tmp/startupmount')
		self.close(value)

	def getBootOptions(self, value=None):
		self.container = Console()
		if os.path.isdir('/tmp/startupmount'):
			self.getImagesList()
		else:
			if os.path.islink("/dev/block/by-name/bootoptions"):
				os.mkdir('/tmp/startupmount')
				self.container.ePopen('mount /dev/block/by-name/bootoptions /tmp/startupmount', self.getImagesList)
			elif os.path.islink("/dev/block/by-name/boot"):
				os.mkdir('/tmp/startupmount')
				self.container.ePopen('mount /dev/block/by-name/boot /tmp/startupmount', self.getImagesList)
			else:
				os.mkdir('/tmp/startupmount')
				self.container.ePopen('mount /dev/%sp1 /tmp/startupmount' % SystemInfo["canMultiBoot"][2], self.getImagesList)

	def getImagesList(self, data=None, retval=None, extra_args=None):
		self.container.killAll()
		self.getImageList = GetImagelist(self.getImagelistCallback)

	def getImagelistCallback(self, imagesdict):
		list = []
		currentimageslot = GetCurrentImage()
		mode = GetCurrentImageMode() or 0
		if imagesdict:
			for index, x in enumerate(sorted(imagesdict.keys())):
				if imagesdict[x]["imagename"] != _("Empty slot"):
					if SystemInfo["canMode12"]:
						list.insert(index, ChoiceEntryComponent('',((_("slot%s - %s mode 1 (current image)") if x == currentimageslot and mode != 12 else _("slot%s - %s mode 1")) % (x, imagesdict[x]['imagename']), x)))
						list.append(ChoiceEntryComponent('',((_("slot%s - %s mode 12 (current image)") if x == currentimageslot and mode == 12 else _("slot%s - %s mode 12")) % (x, imagesdict[x]['imagename']), x + 12)))
					else:
						list.append(ChoiceEntryComponent('',((_("slot%s - %s (current image)") if x == currentimageslot and mode != 12 else _("slot%s - %s")) % (x, imagesdict[x]['imagename']), x)))
		if os.path.isfile("/tmp/startupmount/STARTUP_RECOVERY"):
			list.append(ChoiceEntryComponent('',((_("Boot to Recovery menu")), "Recovery")))
		if os.path.isfile("/tmp/startupmount/STARTUP_ANDROID"):
			list.append(ChoiceEntryComponent('',((_("Boot to Android image")), "Android")))
		if not list:
			list.append(ChoiceEntryComponent('',((_("No images found")), "Waiter")))
		self["list"].setList(list)

	def keyOk(self):
		self.currentSelected = self["list"].l.getCurrentSelection()
		self.slot = self.currentSelected[0][1]
		if self.slot != "Waiter":
			self.session.openWithCallback(self.doReboot, MessageBox, "%s:\n%s" % (_("Are you sure to reboot to"), self.currentSelected[0][0]), simple=True)

	def doReboot(self, answer):
		if answer:
			if self.slot == "Recovery":
				shutil.copyfile("/tmp/startupmount/STARTUP_RECOVERY", "/tmp/startupmount/STARTUP")
			elif self.slot == "Android":
				shutil.copyfile("/tmp/startupmount/STARTUP_ANDROID", "/tmp/startupmount/STARTUP")
			else:
				model = HardwareInfo().get_machine_name()
				if SystemInfo["canMultiBoot"][3]:
					shutil.copyfile("/tmp/startupmount/STARTUP_%s" % self.slot, "/tmp/startupmount/STARTUP")
				elif os.path.isfile("/tmp/startupmount/STARTUP_LINUX_4_BOXMODE_12"):
					if self.slot < 12:
						shutil.copyfile("/tmp/startupmount/STARTUP_LINUX_%s_BOXMODE_1" % self.slot, "/tmp/startupmount/STARTUP")
					else:
						self.slot -= 12
						shutil.copyfile("/tmp/startupmount/STARTUP_LINUX_%s_BOXMODE_12" % self.slot, "/tmp/startupmount/STARTUP")
				elif os.path.isfile("/tmp/startupmount/STARTUP_LINUX_4"):
					shutil.copyfile("/tmp/startupmount/STARTUP_LINUX_%s" % self.slot, "/tmp/startupmount/STARTUP")
				elif os.path.isfile("/tmp/startupmount/STARTUP_4"):
					shutil.copyfile("/tmp/startupmount/STARTUP_%s" % self.slot, "/tmp/startupmount/STARTUP")
				else:
					if self.slot < 12:
						startupFileContents = "boot emmcflash0.kernel%s 'root=/dev/mmcblk0p%s rw rootwait %s_4.boxmode=1'\n" % (self.slot, self.slot * 2 + 1, model)
					else:
						self.slot -= 12
						startupFileContents = "boot emmcflash0.kernel%s 'brcm_cma=520M@248M brcm_cma=%s@768M root=/dev/mmcblk0p%s rw rootwait %s_4.boxmode=12'\n" % (self.slot, SystemInfo["canMode12"], self.slot * 2 + 1, model)
					open('/tmp/startupmount/STARTUP', 'w').write(startupFileContents)
			from Screens.Standby import TryQuitMainloop
			self.session.open(TryQuitMainloop, 2)

	def selectionChanged(self):
		pass
