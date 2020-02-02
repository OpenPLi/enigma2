from Components.SystemInfo import SystemInfo
from Components.Console import Console, PosixSpawn
import os, glob

TMP_MOUNT = '/tmp/multibootcheck'

def getMultibootStartupDevice(model):
	for device in ('/dev/block/by-name/bootoptions', '/dev/block/by-name/bootoptions', "/dev/mmcblk1p1" if model in ('osmio4k', 'osmio4kplus', 'osmini4k') else "/dev/mmcblk0p1"):
		if os.path.exists(device):
			return device

def getparam(line, param):
	return line.rsplit('%s=' % param, 1)[1].split(' ', 1)[0]

def getMultibootslots():
	bootslots = {}
	if SystemInfo["MultibootStartupDevice"]:
		if not os.path.isdir(TMP_MOUNT):
			os.mkdir(TMP_MOUNT)
		postix = PosixSpawn()
		postix.execute('mount %s %s' % (SystemInfo["MultibootStartupDevice"], TMP_MOUNT))
		for file in glob.glob('%s/STARTUP_*' % TMP_MOUNT):
			slotnumber = file.rsplit('_', 3 if 'BOXMODE' in file else 1)[1]
			if slotnumber.isdigit() and slotnumber not in bootslots:
				slot = {}
				for line in open(file).readlines():
					if 'root=' in line:
						device = getparam(line, 'root')
						if os.path.exists(device):
							slot['device'] = device
							slot['startupfile'] = os.path.basename(file).split('_BOXMODE')[0]
							if 'rootsubdir' in line:
								slot['rootsubdir'] = getparam(line, 'rootsubdir')
						break
				if slot:
					bootslots[int(slotnumber)] = slot
		postix.execute('umount %s' % TMP_MOUNT)
		if not os.path.ismount(TMP_MOUNT):
			os.rmdir(TMP_MOUNT)
	return bootslots

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
