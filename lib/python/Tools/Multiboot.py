from Components.SystemInfo import SystemInfo
from Components.Console import Console
import os, glob

TMP_MOUNT = '/tmp/multibootcheck'

def getMultibootStartupDevice():
	if not os.path.isdir(TMP_MOUNT):
		os.mkdir(TMP_MOUNT)
	for device in ('/dev/block/by-name/bootoptions', '/dev/mmcblk0p1', '/dev/mmcblk1p1', '/dev/mmcblk0p3', '/dev/mmcblk0p4'):
		if os.path.exists(device):
			Console().ePopen('mount %s %s' % (device, TMP_MOUNT))
			if os.path.isfile(os.path.join(TMP_MOUNT, "STARTUP")):
				print '[Multiboot] Startupdevice found:', device
				return device
			Console().ePopen('umount %s' % TMP_MOUNT)
	if not os.path.ismount(TMP_MOUNT):
		os.rmdir(TMP_MOUNT)

def getparam(line, param):
	return line.rsplit('%s=' % param, 1)[1].split(' ', 1)[0]

def getMultibootslots():
	bootslots = {}
	mode12found = False
	if SystemInfo["MultibootStartupDevice"]:
		for file in glob.glob(os.path.join(TMP_MOUNT, 'STARTUP_*')):
			if 'MODE_' in file:
				mode12found = True
				slotnumber = file.rsplit('_', 3)[1]
			else:
				slotnumber = file.rsplit('_', 1)[1]
			if slotnumber.isdigit() and slotnumber not in bootslots:
				slot = {}
				for line in open(file).readlines():
					if 'root=' in line:
						device = getparam(line, 'root')
						if os.path.exists(device):
							slot['device'] = device
							slot['startupfile'] = os.path.basename(file)
							if 'rootsubdir' in line:
								slot['rootsubdir'] = getparam(line, 'rootsubdir')
						break
				if slot:
					bootslots[int(slotnumber)] = slot
		Console().ePopen('umount %s' % TMP_MOUNT)
		if not os.path.ismount(TMP_MOUNT):
			os.rmdir(TMP_MOUNT)
		if not mode12found and SystemInfo["canMode12"]:
			#the boot device has ancient content and does not contain the correct STARTUP files
			for slot in range(1,5):
				bootslots[slot] = { 'device': '/dev/mmcblk0p%s' % (slot * 2 + 1), 'startupfile': None}
	print '[Multiboot] Bootslots found:', bootslots
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
			self.slots = sorted(SystemInfo["canMultiBoot"].keys())
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
			self.container.ePopen('mount %s %s' % (SystemInfo["canMultiBoot"][self.slot]['device'], TMP_MOUNT), self.appClosed)

	def appClosed(self, data="", retval=0, extra_args=None):
		if retval:
			self.imagelist[self.slot] = { 'imagename': _("Empty slot") }
		if retval == 0 and self.phase == self.MOUNT:
			imagedir = os.sep.join(filter(None, [TMP_MOUNT, SystemInfo["canMultiBoot"][self.slot].get('rootsubdir', '')]))
			if os.path.isfile(os.path.join(imagedir, 'usr/bin/enigma2')):
				try:
					from datetime import datetime
					date = datetime.fromtimestamp(os.stat(os.path.join(imagedir, "var/lib/opkg/status")).st_mtime).strftime('%Y-%m-%d')
					if date.startswith("1970"):
						date = datetime.fromtimestamp(os.stat(os.path.join(imagedir, "usr/share/bootlogo.mvi")).st_mtime).strftime('%Y-%m-%d')
					date = max(date, datetime.fromtimestamp(os.stat(os.path.join(imagedir, "usr/bin/enigma2")).st_mtime).strftime('%Y-%m-%d'))
				except:
					date = _("Unknown")
				self.imagelist[self.slot] = { 'imagename': "%s (%s)" % (open(os.path.join(imagedir, "etc/issue")).readlines()[-2].capitalize().strip()[:-6], date) }
			else:
				self.imagelist[self.slot] = { 'imagename': _("Empty slot") }
			if self.slots and SystemInfo["canMultiBoot"][self.slot]['device'] == SystemInfo["canMultiBoot"][self.slots[0]]['device']:
				self.slot = self.slots.pop(0)
				self.appClosed()
			else:
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
