from Components.SystemInfo import SystemInfo
from Components.Console import Console
import os

def GetCurrentImage():
	if SystemInfo["canMultiBoot"]:
		slot = [x[-1] for x in open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().split() if x.startswith('rootsubdir')]
		if slot:
			return int(slot[0])
		else:
			return (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read()[:-1].split("%sp" % SystemInfo["canMultiBoot"][2])[1].split(' ')[0])-SystemInfo["canMultiBoot"][0])/2

def GetCurrentImageMode():
	return SystemInfo["canMultiBoot"] and SystemInfo["canMode12"] and int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[-1])

class GetImagelist():
	MOUNT = 0
	UNMOUNT = 1

	def __init__(self, callback):
		if SystemInfo["canMultiBoot"]:
			(self.firstslot, self.numberofslots) = SystemInfo["canMultiBoot"][:2]
			self.callback = callback
			self.imagelist = {}
			if not os.path.isdir('/tmp/testmount'):
				os.mkdir('/tmp/testmount')
			self.container = Console()
			self.slot = 1
			self.phase = self.MOUNT
			self.run()
		else:	
			callback({})

	def run(self):
		if SystemInfo["HasRootSubdir"]:
			if self.slot == 1 and os.path.islink("/dev/block/by-name/linuxrootfs"):
				self.container.ePopen('mount /dev/block/by-name/linuxrootfs /tmp/testmount' if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
			else:
				self.container.ePopen('mount /dev/block/by-name/userdata /tmp/testmount' if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
		else:
			self.container.ePopen('mount /dev/%sp%s /tmp/testmount' % (SystemInfo["canMultiBoot"][2], str(self.slot * 2 + self.firstslot)) if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)

	def appClosed(self, data, retval, extra_args):
		if retval == 0 and self.phase == self.MOUNT:
			if SystemInfo["HasRootSubdir"]:
				if self.slot == 1 and os.path.isfile("/tmp/testmount/linuxrootfs1/usr/bin/enigma2"):
					import datetime
					self.imagelist[self.slot] =  { 'imagename': "%s (%s)" % (open("/tmp/testmount/linuxrootfs1/etc/issue").readlines()[-2].capitalize().strip()[:-6], datetime.datetime.fromtimestamp(os.stat("/tmp/testmount/linuxrootfs1/usr/share/bootlogo.mvi").st_mtime).strftime('%Y-%m-%d'))}
				elif os.path.isfile("/tmp/testmount/linuxrootfs%s/usr/bin/enigma2" % self.slot):
					import datetime
					self.imagelist[self.slot] =  { 'imagename': "%s (%s)" % (open("/tmp/testmount/linuxrootfs%s/etc/issue" % self.slot).readlines()[-2].capitalize().strip()[:-6], datetime.datetime.fromtimestamp(os.stat("/tmp/testmount/linuxrootfs%s/usr/share/bootlogo.mvi" % self.slot).st_mtime).strftime('%Y-%m-%d'))}
				else:
					self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			else:
				if os.path.isfile("/tmp/testmount/usr/bin/enigma2"):
					import datetime
					self.imagelist[self.slot] =  { 'imagename': "%s (%s)" % (open("/tmp/testmount/etc/issue").readlines()[-2].capitalize().strip()[:-6], datetime.datetime.fromtimestamp(os.stat("/tmp/testmount/usr/share/bootlogo.mvi").st_mtime).strftime('%Y-%m-%d'))}
				else:
					self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			self.phase = self.UNMOUNT
			self.run()
		elif self.slot < self.numberofslots:
			self.slot += 1
			self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			self.phase = self.MOUNT
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback(self.imagelist)