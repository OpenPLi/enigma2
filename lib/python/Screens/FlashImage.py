from Screens.ChoiceBox import ChoiceBox
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
from Components.SystemInfo import BoxInfo
from Tools.BoundFunction import boundFunction
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists, pathExists, fileHas
from Tools.Downloader import downloadWithProgress
from Tools.HardwareInfo import HardwareInfo
from Tools.Multiboot import getImagelist, getCurrentImage, getCurrentImageMode, deleteImage, restoreImages
import os
import re
from urllib.request import urlopen, Request
import xml.etree.ElementTree
import json
import time
import zipfile
import shutil
import tempfile
import struct

from enigma import eEPGCache, eEnv


def checkimagefiles(files):
	return len([x for x in files if 'kernel' in x and '.bin' in x or x in ('uImage', 'rootfs.bin', 'root_cfe_auto.bin', 'root_cfe_auto.jffs2', 'oe_rootfs.bin', 'e2jffs2.img', 'rootfs.tar.bz2', 'rootfs.ubi')]) == 2


class SelectImage(Screen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.imageBrandList = {}
		self.jsonlist = {}
		self.imagesList = {}
		self.setIndex = 0
		self.expanded = []
		self.model = HardwareInfo().get_machine_name()
		self.selectedImage = ["OpenPLi", {"url": "https://downloads.openpli.org/json/%s" % self.model, "model": self.model}]
		self.models = [self.model]
		self.setTitle(_("Select image"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText(_("Initialize Multiboot")) if BoxInfo.getItem("canKexec") else StaticText()
		self["key_blue"] = StaticText()
		self["description"] = Label()
		self["list"] = ChoiceList(list=[ChoiceEntryComponent('', ((_("Retrieving image list - Please wait...")), "Waiter"))])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": boundFunction(self.close, None),
			"red": boundFunction(self.close, None),
			"green": self.keyOk,
			"yellow": self.keyYellow,
			"blue": self.otherImages,
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
			for file in files:
				try:
					if checkimagefiles([x.split(os.sep)[-1] for x in zipfile.ZipFile(file).namelist()]):
						imagetyp = _("Downloaded Images")
						if 'backup' in file.split(os.sep)[-1]:
							imagetyp = _("Fullbackup Images")
						if imagetyp not in self.imagesList:
							self.imagesList[imagetyp] = {}
						self.imagesList[imagetyp][file] = {'link': file, 'name': file.split(os.sep)[-1]}
				except:
					pass

		def checkModels(file):
			for model in self.models:
				if '-%s-' % model or '-%_' % model in file:
					return True
			return False

		def conditional_sort(ls, f):
			y = iter(reversed(sorted(w for w in ls if f(w))))
			return [w if not f(w) else next(y) for w in ls]

		if not self.imageBrandList:
				url = "%s%s" % ("https://raw.githubusercontent.com/OpenPLi/FlashImage/main/", self.model)
				try:
					self.imageBrandList = json.load(urlopen(url, timeout=3))
				except:
					print("[FlashImage] getImageBrandList Error: Unable to load json data from URL '%s'!" % url)
				if self.imageBrandList:
					self.imageBrandList.update({self.selectedImage[0]: self.selectedImage[1]})
					self.models = set([self.imageBrandList[image]['model'] for image in self.imageBrandList.keys()])
					if len(self.imageBrandList) > 1:
						self["key_blue"].setText(_("Other Images"))
		if not self.imagesList:
			if not self.jsonlist:
				try:
					self.jsonlist = dict(json.load(urlopen(self.selectedImage[1]["url"], timeout=3)))
				except:
					print("[FlashImage] getImagesList Error: Unable to load json data from URL '%s'!" % self.selectedImage[1]["url"])
				alternative_imagefeed = config.usage.alternative_imagefeed.value
				if alternative_imagefeed:
					if "http" in alternative_imagefeed:
						url = "%s%s" % (config.usage.alternative_imagefeed.value, self.model)
						try:
							self.jsonlist.update(dict(json.load(urlopen(url, timeout=3))))
						except:
							print("[FlashImage] getImagesList Error: Unable to load json data from alternative URL '%s'!" % url)

			self.imagesList = dict(self.jsonlist)

			for media in ['/media/%s' % x for x in os.listdir('/media')] + (['/media/net/%s' % x for x in os.listdir('/media/net')] if os.path.isdir('/media/net') else []):
				try:
					getImages(media, [os.path.join(media, x) for x in os.listdir(media) if os.path.splitext(x)[1] == ".zip" and checkModels(x)])
					for folder in ["images", "downloaded_images", "imagebackups"]:
						if folder in os.listdir(media):
							subfolder = os.path.join(media, folder)
							if os.path.isdir(subfolder) and not os.path.islink(subfolder) and not os.path.ismount(subfolder):
								getImages(subfolder, [os.path.join(subfolder, x) for x in os.listdir(subfolder) if os.path.splitext(x)[1] == ".zip" and checkModels(x)])
								for dir in [dir for dir in [os.path.join(subfolder, dir) for dir in os.listdir(subfolder)] if os.path.isdir(dir) and os.path.splitext(dir)[1] == ".unzipped"]:
									shutil.rmtree(dir)
				except:
					pass

		list = []
		for catagorie in conditional_sort(self.imagesList.keys(), lambda w: _("Downloaded Images") not in w and _("Fullbackup Images") not in w):
			if catagorie in self.expanded:
				list.append(ChoiceEntryComponent('expanded', ((str(catagorie)), "Expander")))
				for image in reversed(sorted(self.imagesList[catagorie].keys())):
					list.append(ChoiceEntryComponent('verticalline', ((str(self.imagesList[catagorie][image]['name'])), str(self.imagesList[catagorie][image]['link']))))
			else:
				for image in self.imagesList[catagorie].keys():
					list.append(ChoiceEntryComponent('expandable', ((str(catagorie)), "Expander")))
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
			self["list"].setList([ChoiceEntryComponent('', ((_("Cannot find images - please try later or select an alternate image")), "Waiter"))])

	def keyOk(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if currentSelected[0][1] == "Expander":
			if currentSelected[0][0] in self.expanded:
				self.expanded.remove(currentSelected[0][0])
			else:
				self.expanded.append(currentSelected[0][0])
			self.getImagesList()
		elif currentSelected[0][1] != "Waiter":
			self.session.openWithCallback(self.reloadImagesList, FlashImage, currentSelected[0][0], currentSelected[0][1])

	def reloadImagesList(self):
		self["list"].setList([ChoiceEntryComponent('', ((_("Retrieving image list - Please wait...")), "Waiter"))])
		self["list"].moveToIndex(0)
		self.selectionChanged()
		self.imagesList = {}
		self.callLater(self.getImagesList)

	def keyYellow(self):
		currentSelected = self["list"].l.getCurrentSelection()[0][1]
		if not ("://" in currentSelected or currentSelected in ["Expander", "Waiter"]):
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
		elif BoxInfo.getItem("canKexec"):
			self.session.open(KexecInit)

	def otherImages(self):
		if len(self.imageBrandList) > 1:
			self.session.openWithCallback(self.otherImagesCallback, ChoiceBox, list=[(key, self.imageBrandList[key]) for key in self.imageBrandList.keys()], windowTitle=_("Select an image brand"))

	def otherImagesCallback(self, image):
		if image:
			self.selectedImage = image
			self.jsonlist = {}
			self.expanded = []
			self.reloadImagesList()

	def selectionChanged(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if "://" in currentSelected[0][1] or currentSelected[0][1] in ["Expander", "Waiter"]:
			self["key_yellow"].setText(_("Initialize Multiboot") if BoxInfo.getItem("canKexec") else "")
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
	skin = """<screen position="center,center" size="640,180" flags="wfNoBorder" backgroundColor="#54242424">
		<widget name="header" position="5,10" size="e-10,50" font="Regular;40" backgroundColor="#54242424"/>
		<widget name="info" position="5,60" size="e-10,130" font="Regular;24" backgroundColor="#54242424"/>
		<widget name="progress" position="5,e-39" size="e-10,24" backgroundColor="#54242424"/>
	</screen>"""

	BACKUP_SCRIPT = resolveFilename(SCOPE_PLUGINS, "Extensions/AutoBackup/settings-backup.sh")

	def __init__(self, session, imagename, source):
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
		if BoxInfo.getItem("canMultiBoot"):
			imagesList = getImagelist()
			currentimageslot = getCurrentImage()
			choices = []
			slotdict = {k: v for k, v in BoxInfo.getItem("canMultiBoot").items() if not v['device'].startswith('/dev/sd')}
			for x in range(1, len(slotdict) + 1):
				choices.append(((_("slot%s - %s (current image) with, backup") if x == currentimageslot else _("slot%s - %s, with backup")) % (x, imagesList[x]['imagename']), (x, "with backup")))
			for x in range(1, len(slotdict) + 1):
				choices.append(((_("slot%s - %s (current image), without backup") if x == currentimageslot else _("slot%s - %s, without backup")) % (x, imagesList[x]['imagename']), (x, "without backup")))
			if "://" in self.source:
				choices.append((_("No, only download"), (1, "only download")))
			choices.append((_("No, do not flash image"), False))
			self.session.openWithCallback(self.checkMedia, MessageBox, self.message, list=choices, default=currentimageslot, simple=True)
		else:
			choices = [(_("Yes, with backup"), "with backup"), (_("Yes, without backup"), "without backup")]
			if "://" in self.source:
				choices.append((_("No, only download"), "only download"))
			choices.append((_("No, do not flash image"), False))
			self.session.openWithCallback(self.checkMedia, MessageBox, self.message, list=choices, default=False, simple=True)

	def checkMedia(self, retval):
		if retval:
			if BoxInfo.getItem("canMultiBoot"):
				self.multibootslot = retval[0]
				doBackup = retval[1] == "with backup"
				self.onlyDownload = retval[1] == "only download"
			else:
				doBackup = retval == "with backup"
				self.onlyDownload = retval == "only download"

			def findmedia(path):
				def avail(path):
					if not path.startswith('/mmc') and os.path.isdir(path) and os.access(path, os.W_OK):
						try:
							statvfs = os.statvfs(path)
							return (statvfs.f_bavail * statvfs.f_frsize) // (1 << 20)
						except OSError as err:
							print("[FlashImage] checkMedia Error %d: Unable to get status for '%s'! (%s)" % (err.errno, path, err.strerror))
					return 0

				def checkIfDevice(path, diskstats):
					st_dev = os.stat(path).st_dev
					return (os.major(st_dev), os.minor(st_dev)) in diskstats

				diskstats = [(int(x[0]), int(x[1])) for x in [x.split()[0:3] for x in open('/proc/diskstats').readlines()] if x[2].startswith("sd")]
				if os.path.isdir(path) and checkIfDevice(path, diskstats) and avail(path) > 500:
					return (path, True)
				mounts = []
				devices = []
				for path in ['/media/%s' % x for x in os.listdir('/media')] + (['/media/net/%s' % x for x in os.listdir('/media/net')] if os.path.isdir('/media/net') else []):
					try:
						if checkIfDevice(path, diskstats):
							devices.append((path, avail(path)))
						else:
							mounts.append((path, avail(path)))
					except OSError:
						pass
				devices.sort(key=lambda x: x[1], reverse=True)
				mounts.sort(key=lambda x: x[1], reverse=True)
				return ((devices[0][1] > 500 and (devices[0][0], True)) if devices else mounts and mounts[0][1] > 500 and (mounts[0][0], False)) or (None, None)

			self.destination, isDevice = findmedia(os.path.isfile(self.BACKUP_SCRIPT) and hasattr(config.plugins, "autobackup") and config.plugins.autobackup.where.value or "/media/hdd")

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
			self.session.openWithCallback(self.abort, MessageBox, _("Error during backup settings\n%s") % retval, type=MessageBox.TYPE_ERROR, simple=True)

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
		if self.onlyDownload:
			self.session.openWithCallback(self.abort, MessageBox, _("Download Successful\n%s") % self.imagename, type=MessageBox.TYPE_INFO, simple=True)
		else:
			self["header"].setText(_("Unzipping Image"))
			self["info"].setText("%s\n%s" % (self.imagename, _("Please wait")))
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
			if BoxInfo.getItem("canMultiBoot"):
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
		SelectImage.__init__(self, session)
		self.skinName = ["MultibootSelection", "Setup"]
		self.expanded = []
		self.tmp_dir = None
		self.setTitle(_("Multiboot image selector"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Reboot"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["description"] = Label()
		self["config"] = ChoiceList([])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.keyOk,
			"yellow": self.deleteImage,
			"blue": self.order,
			"up": self.keyUp,
			"down": self.keyDown,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.cancel, True),
		}, -1)

		self.blue = False
		self.currentimageslot = getCurrentImage()
		self.tmp_dir = tempfile.mkdtemp(prefix="MultibootSelection")
		Console().ePopen('mount %s %s' % (BoxInfo.getItem("MultibootStartupDevice"), self.tmp_dir))
		self.getImagesList()

	def cancel(self, value=None):
		Console().ePopen('umount %s' % self.tmp_dir)
		if not os.path.ismount(self.tmp_dir):
			os.rmdir(self.tmp_dir)
		if value == 2:
			from Screens.Standby import TryQuitMainloop
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close(value)

	def getImagesList(self):
		list = []
		list12 = []
		imagesList = getImagelist()
		mode = getCurrentImageMode() or 0
		self.deletedImagesExists = False
		if imagesList:
			for index, x in enumerate(imagesList):
				if imagesList[x]["imagename"] == _("Deleted image"):
					self.deletedImagesExists = True
				elif imagesList[x]["imagename"] != _("Empty slot"):
					if BoxInfo.getItem("canMode12"):
						list.insert(index, ChoiceEntryComponent('', ((_("slot%s - %s mode 1 (current image)") if x == self.currentimageslot and mode != 12 else _("slot%s - %s mode 1")) % (x, imagesList[x]['imagename']), (x, 1))))
						list12.insert(index, ChoiceEntryComponent('', ((_("slot%s - %s mode 12 (current image)") if x == self.currentimageslot and mode == 12 else _("slot%s - %s mode 12")) % (x, imagesList[x]['imagename']), (x, 12))))
					else:
						list.append(ChoiceEntryComponent('', ((_("slot%s - %s (current image)") if x == self.currentimageslot and mode != 12 else _("slot%s - %s")) % (x, imagesList[x]['imagename']), (x, 1))))

		if list12:
			self.blue = True
			self["key_blue"].setText(_("Order by modes") if config.usage.multiboot_order.value else _("Order by slots"))
			list += list12
			list = sorted(list) if config.usage.multiboot_order.value else list

		if os.path.isfile(os.path.join(self.tmp_dir, "STARTUP_RECOVERY")):
			if BoxInfo.getItem("hasKexec"):
				recovery_booted = fileHas("/proc/cmdline", "rootsubdir=linuxrootfs0")
				self["description"].setText(_("Attention - forced loading recovery image!\nCreate an empty STARTUP_RECOVERY file at the root of your HDD/USB drive and hold the Power button for more than 12 seconds for reboot receiver!"))
				list.append(ChoiceEntryComponent('', (_("Boot to Recovery image - slot0 %s") % (recovery_booted and _("(current image)") or ""), "Recovery")))
			else:
				list.append(ChoiceEntryComponent('', (_("Boot to Recovery menu"), "Recovery")))
		if os.path.isfile(os.path.join(self.tmp_dir, "STARTUP_ANDROID")):
			list.append(ChoiceEntryComponent('', ((_("Boot to Android image")), "Android")))
		if not list:
			list.append(ChoiceEntryComponent('', ((_("No images found")), "Waiter")))
		self["config"].setList(list)
		for index, slot in enumerate(list):
			if type(slot[0][1]) is tuple and self.currentimageslot == slot[0][1][0] and (not BoxInfo.getItem("canMode12") or mode == slot[0][1][1]) or BoxInfo.getItem("hasKexec") and slot[0][1] == "Recovery" and recovery_booted:
				self["config"].moveToIndex(index)
				break
		self.selectionChanged()

	def deleteImage(self):
		if self["key_yellow"].text == _("Restore deleted images"):
			self.session.openWithCallback(self.deleteImageCallback, MessageBox, _("Are you sure to restore all deleted images"), simple=True)
		elif self["key_yellow"].text == _("Delete Image"):
			self.session.openWithCallback(self.deleteImageCallback, MessageBox, "%s:\n%s" % (_("Are you sure to delete image:"), self.currentSelected[0][0]), simple=True)

	def deleteImageCallback(self, answer):
		if answer:
			if self["key_yellow"].text == _("Restore deleted images"):
				restoreImages()
			else:
				deleteImage(self.currentSelected[0][1][0])
			self.getImagesList()

	def order(self):
		if self.blue:
			self["config"].setList([])
			config.usage.multiboot_order.value = not config.usage.multiboot_order.value
			config.usage.multiboot_order.save()
			self.getImagesList()

	def keyOk(self):
		self.session.openWithCallback(self.doReboot, MessageBox, "%s:\n%s" % (_("Are you sure to reboot to"), self.currentSelected[0][0]), simple=True)

	def keyUp(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
		self.selectionChanged()

	def keyDown(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
		self.selectionChanged()

	def doReboot(self, answer):
		if answer:
			slot = self.currentSelected[0][1]
			if slot == "Recovery":
				shutil.copyfile(os.path.join(self.tmp_dir, "STARTUP_RECOVERY"), os.path.join(self.tmp_dir, "STARTUP"))
			elif slot == "Android":
				shutil.copyfile(os.path.join(self.tmp_dir, "STARTUP_ANDROID"), os.path.join(self.tmp_dir, "STARTUP"))
			elif BoxInfo.getItem("canMultiBoot")[slot[0]]['startupfile']:
				if BoxInfo.getItem("canMode12"):
					startupfile = os.path.join(self.tmp_dir, "%s_%s" % (BoxInfo.getItem("canMultiBoot")[slot[0]]['startupfile'].rsplit('_', 1)[0], slot[1]))
				else:
					startupfile = os.path.join(self.tmp_dir, "%s" % BoxInfo.getItem("canMultiBoot")[slot[0]]['startupfile'])
				if BoxInfo.getItem("canDualBoot"):
					with open('/dev/block/by-name/flag', 'wb') as f:
						f.write(struct.pack("B", int(slot[0])))
					startupfile = os.path.join("/boot", "%s" % BoxInfo.getItem("canMultiBoot")[slot[0]]['startupfile'])
					shutil.copyfile(startupfile, os.path.join("/boot", "STARTUP"))
				else:
					shutil.copyfile(startupfile, os.path.join(self.tmp_dir, "STARTUP"))
			else:
				model = HardwareInfo().get_machine_name()
				if slot[1] == 1:
					startupFileContents = "boot emmcflash0.kernel%s 'root=/dev/mmcblk0p%s rw rootwait %s_4.boxmode=1'\n" % (slot[0], slot[0] * 2 + 1, model)
				else:
					startupFileContents = "boot emmcflash0.kernel%s 'brcm_cma=520M@248M brcm_cma=%s@768M root=/dev/mmcblk0p%s rw rootwait %s_4.boxmode=12'\n" % (slot[0], BoxInfo.getItem("canMode12"), slot[0] * 2 + 1, model)
				open(os.path.join(self.tmp_dir, "STARTUP"), 'w').write(startupFileContents)
			self.cancel(2)

	def selectionChanged(self):
		self.currentSelected = self["config"].l.getCurrentSelection()
		if isinstance(self.currentSelected[0][1], tuple) and self.currentimageslot != self.currentSelected[0][1][0]:
			self["key_yellow"].setText(_("Delete Image"))
		elif self.deletedImagesExists:
			self["key_yellow"].setText(_("Restore deleted images"))
		else:
			self["key_yellow"].setText("")


class KexecInit(Screen):
	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.skinName = ["KexecInit", "Setup"]
		self.setTitle(_("Kexec MultiBoot Manager"))
		self.kexec_files = fileExists("/usr/bin/kernel_auto.bin") and fileExists("/usr/bin/STARTUP.cpio.gz")
		self["description"] = Label(_("Press Green key to enable MultiBoot!\n\nWill reboot within 10 seconds,\nunless you have eMMC slots to restore.\nRestoring eMMC slots can take from 1 -> 5 minutes per slot."))
		self["key_red"] = StaticText(self.kexec_files and _("Remove forever") or "")
		self["key_green"] = StaticText(_("Init"))
		self["actions"] = ActionMap(["TeletextActions"],
		{
			"green": self.RootInit,
			"ok": self.close,
			"exit": self.close,
			"red": self.removeFiles,
		}, -1)

	def RootInit(self):
		self["actions"].setEnabled(False)  # This function takes time so disable the ActionMap to avoid responding to multiple button presses
		if self.kexec_files:
			modelMtdRootKernel = BoxInfo.getItem("canKexec")
			self.setTitle(_("Kexec MultiBoot Initialisation - will reboot after 10 seconds."))
			self["description"].setText(_("Kexec MultiBoot Initialisation in progress!\n\nWill reboot after restoring any eMMC slots.\nThis can take from 1 -> 5 minutes per slot."))
			open("/STARTUP", 'w').write("kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % modelMtdRootKernel[0])
			open("/STARTUP_RECOVERY", 'w').write("kernel=/zImage root=/dev/%s rootsubdir=linuxrootfs0" % modelMtdRootKernel[0])
			open("/STARTUP_1", 'w').write("kernel=/linuxrootfs1/zImage root=/dev/%s rootsubdir=linuxrootfs1" % modelMtdRootKernel[0])
			open("/STARTUP_2", 'w').write("kernel=/linuxrootfs2/zImage root=/dev/%s rootsubdir=linuxrootfs2" % modelMtdRootKernel[0])
			open("/STARTUP_3", 'w').write("kernel=/linuxrootfs3/zImage root=/dev/%s rootsubdir=linuxrootfs3" % modelMtdRootKernel[0])
			cmdlist = []
			cmdlist.append("dd if=/dev/%s of=/zImage" % modelMtdRootKernel[1])  # backup old kernel
			cmdlist.append("dd if=/usr/bin/kernel_auto.bin of=/dev/%s" % modelMtdRootKernel[1])  # create new kernel
			cmdlist.append("mv /usr/bin/STARTUP.cpio.gz /STARTUP.cpio.gz")  # copy userroot routine
			Console().eBatch(cmdlist, self.RootInitEnd, debug=True)
		else:
			self.session.open(MessageBox, _("Unable to complete - Kexec Multiboot files missing!"), MessageBox.TYPE_INFO, timeout=10)
			self.close()

	def RootInitEnd(self, *args, **kwargs):
		from Screens.Standby import TryQuitMainloop
		model = HardwareInfo().get_machine_name()
		for usbslot in range(1, 4):
			if pathExists("/media/hdd/%s/linuxrootfs%s" % (model, usbslot)):
				Console().ePopen("cp -R /media/hdd/%s/linuxrootfs%s . /" % (model, usbslot))
		self.session.open(TryQuitMainloop, 2)

	def removeFiles(self):
		if self.kexec_files:
			self.session.openWithCallback(self.removeFilesAnswer, MessageBox, _("Really permanently delete MultiBoot files?\n%s") % "(/usr/bin/kernel_auto.bin /usr/bin/STARTUP.cpio.gz)", simple=True)

	def removeFilesAnswer(self, answer=None):
		if answer:
			Console().ePopen("rm -rf /usr/bin/kernel_auto.bin /usr/bin/STARTUP.cpio.gz")
			self.close()
