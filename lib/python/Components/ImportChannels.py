import threading, urllib2, os, shutil
from json import loads
from enigma import eDVBDB, eEPGCache
from Screens.MessageBox import MessageBox
from config import config, ConfigText
from Tools import Notifications
from base64 import encodestring

settingfiles = ('lamedb', 'bouquets.', 'userbouquet.', 'blacklist', 'whitelist', 'alternatives.')

class ImportChannels():

	def __init__(self):
		if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and not "ChannelsImport" in [x.name for x in threading.enumerate()]:
			self.header = None
			if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
				self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
			else:
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
			if config.usage.remote_fallback_openwebif_customize.value:
				self.url = "%s:%s" % (self.url, config.usage.remote_fallback_openwebif_port.value)
				if config.usage.remote_fallback_openwebif_userid.value and config.usage.remote_fallback_openwebif_password.value:
					self.header = "Basic %s" % encodestring("%s:%s" % (config.usage.remote_fallback_openwebif_userid.value, config.usage.remote_fallback_openwebif_password.value)).strip()
			self.thread = threading.Thread(target=self.threaded_function, name="ChannelsImport")
			self.thread.start()

	def getUrl(self, url, timeout=5):
		request = urllib2.Request(url)
		if self.header:
			request.add_header("Authorization", self.header)
		return urllib2.urlopen(request, timeout=timeout)

	def threaded_function(self):
		if "epg" in config.usage.remote_fallback_import.value:
			config.misc.epgcache_filename = ConfigText(default="/epg.dat")
			print "Writing epg.dat file on sever box"
			try:
				self.getUrl("%s/web/saveepg" % self.url, timeout=30).read()
			except:
				self.ImportChannelsDone(False, _("Error when writing epg.dat on server"))
				return
			print "[Import Channels] Get EPG Location"
			try:
				epgdatfile = [x for x in self.getUrl("%s/file?file=/etc/enigma2/settings" % self.url).readlines() if x.startswith('config.misc.epgcache_filename=')]
				epgdatfile = epgdatfile and epgdatfile[0].split('=')[1].strip() or "/hdd/epg.dat"
				try:
					files = [file for file in loads(self.getUrl("%s/file?dir=%s" % (self.url, os.path.dirname(epgdatfile))).read())["files"] if os.path.basename(file).startswith(os.path.basename(epgdatfile))]
				except:
					files = [file for file in loads(self.getUrl("%s/file?dir=/" % self.url).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
			except:
				self.ImportChannelsDone(False, _("Error while retreiving location of epg.dat on server"))
				return
			if epg_location:
				print "[Import Channels] Copy EPG file..."
				try:
					open(config.misc.epgcache_filename.value, "wb").write(self.getUrl("%s/file?file=%s" % (self.url, epg_location)).read())
				except:
					self.ImportChannelsDone(False, _("Error while retreiving epg.dat from server"))
			else:
				self.ImportChannelsDone(False, _("No epg.dat file found server"))
		if "channels" in config.usage.remote_fallback_import.value:
			try:
				os.mkdir("/tmp/tmp")
			except:
				pass
			print "[Import Channels] reading dir"
			try:
				files = [file for file in loads(self.getUrl("%s/file?dir=/etc/enigma2" % self.url).read())["files"] if os.path.basename(file).startswith(settingfiles)]
				for file in files:
					file = file.encode("UTF-8")
					print "[Import Channels] Downloading %s" % file
					destination = "/tmp/tmp"
					try:
						open("%s/%s" % (destination, os.path.basename(file)), "wb").write(self.getUrl("%s/file?file=%s" % (self.url, file)).read())
					except:
						self.ImportChannelsDone(False, _("ERROR downloading file %s") % file)
						return
			except:
				self.ImportChannelsDone(False, _("Error %s") % self.url)
				return

			print "[Import Channels] Removing files..."
			files = [file for file in os.listdir("/etc/enigma2") if file.startswith(settingfiles)]
			for file in files:
				os.remove("/etc/enigma2/%s" % file)
			print "[Import Channels] copying files..."
			files = [x for x in os.listdir("/tmp/tmp") if x.startswith(settingfiles)]
			for file in files:
				shutil.move("/tmp/tmp/%s" % file, "/etc/enigma2/%s" % file)
			os.rmdir("/tmp/tmp")
		self.ImportChannelsDone(True, {"channels": _("Channels"), "epg": _("EPG"), "channels_epg": _("Channels and EPG")}[config.usage.remote_fallback_import.value])

	def ImportChannelsDone(self, flag, message=None):
		if flag:
			Notifications.AddNotificationWithID("ChannelsImportOK", MessageBox, _("%s imported from fallback tuner") % message, type=MessageBox.TYPE_INFO, timeout=5)
		else:
			Notifications.AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Import from fallback tuner failed, %s") % message, type=MessageBox.TYPE_ERROR, timeout=5)
