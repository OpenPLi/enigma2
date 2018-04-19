import threading, urllib2, os, shutil
from json import loads
from enigma import eDVBDB, eEPGCache
from Screens.MessageBox import MessageBox
from config import config
from Tools import Notifications

settingfiles = ('lamedb', 'bouquets.', 'userbouquet.', 'blacklist', 'whitelist', 'alternatives.')

class ImportChannels():

	def __init__(self):
		if config.usage.remote_fallback_import.value and config.usage.remote_fallback.value and not "ChannelsImport" in [x.name for x in threading.enumerate()]:
				if config.usage.remote_fallback_enabled.value and config.usage.remote_fallback_import.value and config.usage.remote_fallback_import_url.value != "same" and config.usage.remote_fallback_import_url.value:
					self.url = config.usage.remote_fallback_import_url.value.rsplit(":", 1)[0]
				else:
					self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
				self.thread = threading.Thread(target=self.threaded_function, name="ChannelsImport")
				self.thread.start()

	def threaded_function(self):
		if "epg" in config.usage.remote_fallback_import.value:
			print "Writing epg.dat file on sever box"
			try:
				urllib2.urlopen("%s/web/saveepg" % self.url, timeout=5).read()
			except:
				self.ImportChannelsDone(False, _("Error when writing epg.dat on server"))
				return
			print "[Import Channels] Get EPG Location"
			try:
				try:
					files = [file for file in loads(urllib2.urlopen("%s/file?dir=/hdd" % self.url, timeout=5).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				except:
					files = [file for file in loads(urllib2.urlopen("%s/file?dir=/" % self.url, timeout=5).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				epg_location = files[0] if files else None
			except:
				self.ImportChannelsDone(False, _("Error while retreiving location of epg.dat on server"))
				return
			if epg_location:
				print "[Import Channels] Copy EPG file..."
				try:
					open("/hdd/epg.dat" if os.path.isdir("/hdd") else "/epg.dat", "wb").write(urllib2.urlopen("%s/file?file=%s" % (self.url, epg_location), timeout=5).read())
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
				files = [file for file in loads(urllib2.urlopen("%s/file?dir=/etc/enigma2" % self.url, timeout=5).read())["files"] if os.path.basename(file).startswith(settingfiles)]
				count = 0
				for file in files:
					count += 1
					file = file.encode("UTF-8")
					print "[Import Channels] Downloading %s" % file
					destination = "/tmp/tmp"
					try:
						open("%s/%s" % (destination, os.path.basename(file)), "wb").write(urllib2.urlopen("%s/file?file=%s" % (self.url, file), timeout=5).read())
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
		self.ImportChannelsDone(True)

	def ImportChannelsDone(self, flag, errorstring=None):
		if flag:
			Notifications.AddNotificationWithID("ChannelsImportOK", MessageBox, _("Channels from fallback tuner imported"), type=MessageBox.TYPE_INFO, timeout=5)
		else:
			Notifications.AddNotificationWithID("ChannelsImportNOK", MessageBox, _("Channels from fallback tuner failed %s") % errorstring, type=MessageBox.TYPE_ERROR, timeout=5)
