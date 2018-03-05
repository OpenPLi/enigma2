import threading, urllib2, os, shutil
from json import loads
from enigma import eDVBDB, eEPGCache
from Screens.MessageBox import MessageBox
from Components.ServiceList import refreshServiceList
from config import config
from Tools import Notifications

settingfiles = ('lamedb', 'bouquets.', 'userbouquet.', 'blacklist', 'whitelist', 'alternatives.')

class ImportChannels():
	
	def __init__(self, callback=None, progress=None):
		if config.usage.remote_fallback_import.value and config.usage.remote_fallback.value:
			self.callback = callback
			if "ChannelsImport" in [x.name for x in threading.enumerate()]:
				self.ImportChannelsCallback(False, "ChannelsImport already running")
			else:
				self.callback = callback
				self.progressCallback = progress
				self.url = config.usage.remote_fallback.value.rsplit(":", 1)[0]
				self.setProgress(0)
				self.thread = threading.Thread(target=self.threaded_function, name="ChannelsImport")
				self.thread.start()

	def threaded_function(self):
		self.setProgress(0)
		if "epg" in config.usage.remote_fallback_import.value:
			print "Writing epg.dat file on sever box"
			try:
				urllib2.urlopen("%s/web/saveepg" % self.url, timeout=5).read()
			except:
				self.ImportChannelsCallback(False, _("Error when writing epg.dat on server"))
				return
			self.setProgress(10)
			print "[Import Channels] Get EPG Location"
			try:
				try:
					files = [file for file in loads(urllib2.urlopen("%s/file?dir=/hdd" % self.url).read())["files"] if os.path.basename(file).startswith("epg.dat")]
				except:
					files = [file for file in loads(urllib2.urlopen("%s/file?dir=/" % self.url).read())["files"] if os.path.basename(file).startswith("epg.dat")] 
				epg_location = files[0] if files else None
			except:
				self.ImportChannelsCallback(False, _("Error while retreiving location of epg.dat on server"))
				return
			self.setProgress(12)
			if epg_location:
				print "[Import Channels] Copy EPG file..."
				try:
					open("/hdd/epg.dat" if os.path.isdir("/hdd") else "/epg.dat", "wb").write(urllib2.urlopen("%s/file?file=%s" % (self.url, epg_location), timeout=5).read())
				except:
					self.ImportChannelsCallback(False, _("Error while retreiving epg.dat from server"))
				self.setProgress(17)
				print "[Import Channels] Loading EPG cache..."
				eEPGCache.getInstance().load()
			else:
				self.ImportChannelsCallback(False, _("No epg.dat file found server"))
		if "channels" in config.usage.remote_fallback_import.value:
			try:
				os.mkdir("/tmp/tmp")
			except:
				pass
			self.setProgress(20)
			print "[Import Channels] reading dir"
			try:
				files = [file for file in loads(urllib2.urlopen("%s/file?dir=/etc/enigma2" % self.url).read())["files"] if os.path.basename(file).startswith(settingfiles)]
				count = 0
				for file in files:
					count += 1
					file = file.encode("UTF-8")
					print "[Import Channels] Downloading %s" % file
					destination = "/tmp/tmp"
					try:
						open("%s/%s" % (destination, os.path.basename(file)), "wb").write(urllib2.urlopen("%s/file?file=%s" % (self.url, file), timeout=5).read())
					except:
						self.ImportChannelsCallback(False, _("ERROR downloading file %s") % file)
						return
					self.setProgress(count * 70 / len(files) + 20)
			except:
				self.ImportChannelsCallback(False, _("Error %s") % self.url)
				return

			print "[Import Channels] Removing files..."
			files = [file for file in os.listdir("/etc/enigma2") if file.startswith(settingfiles)]
			for file in files:
				os.remove("/etc/enigma2/%s" % file)
			print "[Import Channels] copying files..."
			self.setProgress(95)
			files = [x for x in os.listdir("/tmp/tmp") if x.startswith(settingfiles)]
			for file in files:
				shutil.move("/tmp/tmp/%s" % file, "/etc/enigma2/%s" % file)
			os.rmdir("/tmp/tmp")
		self.ImportChannelsCallback(True, _("OK"))

	def ImportChannelsCallback(self, flag, errorstring):
		if flag:
			if config.usage.remote_fallback_ok.value:
				Notifications.AddNotification(MessageBox, _("Channels from fallback tuner imported"), type=MessageBox.TYPE_INFO, timeout=5)
			eDVBDB.getInstance().reloadBouquets()
			eDVBDB.getInstance().reloadServicelist()
		elif config.usage.remote_fallback_nok.value:
			Notifications.AddNotification(MessageBox, _("Channels from fallback tuner failed %s") % errorstring, type=MessageBox.TYPE_ERROR, timeout=5)
		if self.callback:
			self.callback(flag, errorstring)

	def setProgress(self, value):
		if self.progressCallback:
			self.progressCallback(value)