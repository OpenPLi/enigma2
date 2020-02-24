from Screens.MessageBox import MessageBox
from Tools import Notifications
from twisted.web.http_headers import Headers
from base64 import encodestring
import xml.etree.cElementTree
from json import loads
import os, datetime, shutil
from config import config

SETTINGFILES = ('lamedb', 'bouquets.', 'userbouquet.', 'blacklist', 'whitelist', 'alternatives.')
TMPDIR = "/tmp/.importchannels"

class Import:
	isRunning = False

class ImportChannels():
	def __init__(self):
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and not Import.isRunning:
			Import.isRunning = True
			self.headers = {}
			if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
				self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
			else:
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = "%s:%s" % (self.url, config.usage.remote_fallback_openwebif_port.value)
				if config.usage.remote_fallback_openwebif_userid.value and config.usage.remote_fallback_openwebif_password.value:
					self.headers = {"Authorization": "Basic %s" % encodestring("%s:%s" % (config.usage.remote_fallback_openwebif_userid.value, config.usage.remote_fallback_openwebif_password.value))}
			try:
				os.mkdir(TMPDIR)
			except:
				pass
			if "epg" in config.usage.remote_fallback_import.value:
				self.getUrl("web/saveepg", timeout=30).addCallback(self.saveEpgCallback).addErrback(self.endFallback)
			else:
				self.startDownloadSettings()

	def setMessage(self, message):
		self.message = _(message)
		print "[ImportChannels] %s" % message

	def getUrl(self, url, timeout=5):
		from twisted.web.client import getPage
		self.setMessage("getting url %s/%s" % (self.url, url))
		return getPage("%s/%s" % (self.url, url), headers=self.headers, timeout=timeout)

	def downloadUrl(self, url, file, timeout=5):
		from twisted.web.client import downloadPage
		self.setMessage("downloading %s/%s" % (self.url, url))
		return downloadPage("%s/%s" % (self.url, url.encode("utf-8")), file.encode("utf-8"), headers=self.headers, timeout=timeout)

	def saveEpgCallback(self, data):
		if xml.etree.cElementTree.fromstring(data).find("e2state").text == "True":
			self.getUrl("file?file=/etc/enigma2/settings").addCallback(self.getSettingsCallback).addErrback(self.endFallback)
		else:
			self.endFallback()

	def getSettingsCallback(self, data):
		self.epgdatfile = [x for x in data if x.startswith('config.misc.epgcache_filename=')]
		self.epgdatfile = self.epgdatfile and self.epgdatfile[0].split('=')[1].strip() or "/hdd/epg.dat"
		self.getUrl("file?dir=%s" % os.path.dirname(self.epgdatfile)).addCallback(self.getEPGDatLocationFallback).addErrback(self.getEPGDatLocationError)

	def getEPGDatLocationError(self, message=None):
		self.getUrl("file?dir=/").addCallback(self.getEPGDatLocationFallback).addErrback(self.endFallback)

	def getEPGDatLocationFallback(self, data):
		files = [file for file in loads(data)["files"] if os.path.basename(file).startswith(os.path.basename(self.epgdatfile))]
		if files:
			self.downloadUrl("file?file=%s" % files[0], os.path.join(TMPDIR, "epg.dat")).addCallback(self.EPGDatDownloadedCallback).addErrback(self.endFallback)
		elif os.path.dirname(self.epgdatfile) != os.sep:
			self.epgdatfile = "/epg.dat"
			self.getEPGDatLocationError()
		else:
			self.endFallback(_("Could not locate epg file on fallback tuner"))

	def EPGDatDownloadedCallback(self, data=None):
		destination = config.misc.epgcache_filename.value if os.path.isdir(os.path.dirname(config.misc.epgcache_filename.value)) else "/epg.dat"
		shutil.move(os.path.join(TMPDIR, "epg.dat"), destination)
		self.startDownloadSettings()

	def startDownloadSettings(self):
		if "channels" in config.usage.remote_fallback_import.value:
			self.getUrl("file?dir=/etc/enigma2").addCallback(self.getSettingDir).addErrback(self.endFallback)
		else:
			self.endFallback()

	def getSettingDir(self, data=None):
		self.files = [file for file in loads(data)["files"] if os.path.basename(file).startswith(SETTINGFILES)]
		if self.files:
			self.getSettingFile()
		else:
			self.endFallback(_("No settings files to download on fallback tuner"))

	def getSettingFile(self, data=None):
		if self.files:
			file = self.files.pop(0)
			self.downloadUrl("file?file=%s" % file, os.path.join(TMPDIR, os.path.basename(file))).addCallback(self.getSettingFile).addErrback(self.endFallback)
		else:
			print "[ImportChannels] Removing files..."
			for file in [file for file in os.listdir("/etc/enigma2") if file.startswith(SETTINGFILES)]:
				os.remove(os.path.join("/etc/enigma2", file))
			print "[ImportChannels] copying files..."
			for file in [x for x in os.listdir(TMPDIR) if x.startswith(SETTINGFILES)]:
				shutil.move(os.path.join(TMPDIR, file), os.path.join("/etc/enigma2", file))
			self.endFallback()

	def endFallback(self, message=""):
		if message:
			message = "%s\n%s" % (self.message, str(message).translate(None, '[]').strip())
			Notifications.AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Import from fallback tuner failed, %s") % message, MessageBox.TYPE_ERROR, timeout=5)
		else:
			message = {"channels": _("Channels"), "epg": _("EPG"), "channels_epg": _("Channels and EPG")}[config.usage.remote_fallback_import.value]
			Notifications.AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s imported from fallback tuner") % message, MessageBox.TYPE_INFO, timeout=5)
		if os.path.isdir(TMPDIR):
			os.rmdir(TMPDIR)
		Import.isRunning = False
