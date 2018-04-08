from Components.SystemInfo import SystemInfo
from Components.Console import Console
import os

def GetCurrentImage():
	if SystemInfo["canMultiBootHD"]:
		return	int(open('/sys/firmware/devicetree/base/chosen/kerneldev', 'r').read().replace('\0', '')[-1])
	elif SystemInfo["canMultiBootGB"]:
		x = open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[1]
		x = x.split('p')[1]
		f = int(x.split(' ')[0])
		return (f-3)/2
	else:
		return	0

def GetCurrentImageMode():
	return SystemInfo["canMultiBootHD"] and int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[-1])

class GetImagelist():
	MOUNT = 0
	UNMOUNT = 1

	def __init__(self, callback):
		if SystemInfo["canMultiBoot"]:
			if SystemInfo["canMultiBootHD"]:
				self.addin = 1
				self.endslot = 4
			if SystemInfo["canMultiBootGB"]:
				self.addin = 3
				self.endslot = 3
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
		self.container.ePopen('mount /dev/mmcblk0p%s /tmp/testmount' % str(self.slot * 2 + self.addin) if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
			
	def appClosed(self, data, retval, extra_args):
		SlotEmpty = "Empty Slot"
		if retval == 0 and self.phase == self.MOUNT:
			if os.path.isfile("/tmp/testmount/usr/bin/enigma2"):
				self.imagelist[self.slot] =  { 'imagename': open("/tmp/testmount/etc/issue").readlines()[-2].capitalize().strip()[:-6]}
			else:
				self.imagelist[self.slot] =  { 'imagename': SlotEmpty}
			self.phase = self.UNMOUNT
			self.run()
		elif self.slot < self.endslot:
			self.slot += 1
			self.imagelist[self.slot] =  { 'imagename': SlotEmpty}
			self.phase = self.MOUNT
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback(self.imagelist)
