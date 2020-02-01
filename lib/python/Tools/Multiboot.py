from Components.SystemInfo import SystemInfo
from Components.Console import Console
import os

TMP_MOUNT = '/tmp/multibootcheck'

def GetCurrentImage():
	if SystemInfo["canMultiBoot"]:
		slot = [x[-1] for x in open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().split() if x.startswith('rootsubdir')]
		if slot:
			return int(slot[0])
		else:
			device = getparam(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read(), 'root')
			for slot in SystemInfo["canMultiBoot"].keys():
				if SystemInfo["canMultiBoot"][slot]['device'] == device:
					return slot

def GetCurrentImageMode():
	return bool(SystemInfo["canMultiBoot"]) and SystemInfo["canMode12"] and int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[-1])

class GetImagelist():
	MOUNT = 0
	UNMOUNT = 1

	def __init__(self, callback):
		if SystemInfo["canMultiBoot"]:
			self.slots = SystemInfo["canMultiBoot"].keys()
			self.callback = callback
			self.imagelist = {}
			if not os.path.isdir(TMP_MOUNT):
				os.mkdir(TMP_MOUNT)
			self.container = Console()
			self.phase = self.MOUNT
			self.run()
		else:
			callback({})

	def run(self):
		if self.phase == self.UNMOUNT:
			self.container.ePopen('umount %s' % TMP_MOUNT, self.appClosed)
		else:
			self.slot = self.slots.pop(0)
			if 'rootsubdir' in SystemInfo["canMultiBoot"][self.slot]:
				if self.slot == 1 and os.path.exists("/dev/block/by-name/linuxrootfs"):
					self.container.ePopen('mount /dev/block/by-name/linuxrootfs %s' % TMP_MOUNT, self.appClosed)
				else:
					self.container.ePopen('mount /dev/block/by-name/userdata %s'% TMP_MOUNT, self.appClosed)
			else:
				self.container.ePopen('mount %s %s' % (SystemInfo["canMultiBoot"][self.slot]['device'], TMP_MOUNT), self.appClosed)

	def appClosed(self, data, retval, extra_args=None):
		if retval == 0 and self.phase == self.MOUNT:
			def getImagename(target):
				from datetime import datetime
				date = datetime.fromtimestamp(os.stat(os.path.join(target, "var/lib/opkg/status")).st_mtime).strftime('%Y-%m-%d')
				if date.startswith("1970"):
					try:
						date = datetime.fromtimestamp(os.stat(os.path.join(target, "usr/share/bootlogo.mvi")).st_mtime).strftime('%Y-%m-%d')
					except:
						pass
					date = max(date, datetime.fromtimestamp(os.stat(os.path.join(target, "usr/bin/enigma2")).st_mtime).strftime('%Y-%m-%d'))
				return "%s (%s)" % (open(os.path.join(target, "etc/issue")).readlines()[-2].capitalize().strip()[:-6], date)
			if 'rootsubdir' in SystemInfo["canMultiBoot"][self.slot]:
				imagedir = "%s/%s/" % (TMP_MOUNT, SystemInfo["canMultiBoot"][self.slot]['rootsubdir'])
				if os.path.isfile('%s/usr/bin/enigma2' % imagedir):
					self.imagelist[self.slot] = { 'imagename': getImagename(imagedir) }
				else:
					self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			else:
				if os.path.isfile("%s/usr/bin/enigma2" % TMP_MOUNT):
					self.imagelist[self.slot] = { 'imagename': getImagename(TMP_MOUNT) }
				else:
					self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			self.phase = self.UNMOUNT
			self.run()
		elif self.slots:
			self.phase = self.MOUNT
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount(TMP_MOUNT):
				os.rmdir(TMP_MOUNT)
			self.callback(self.imagelist)
