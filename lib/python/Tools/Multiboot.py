from Components.SystemInfo import SystemInfo
from Components.Console import Console
import os

def GetCurrentImage():
	if SystemInfo["canMultiBoot"]:
		if 'rootflags=data=journal' in open('/dev/mmcblk0p1').read():
			return (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[1].split('p')[1].split(' ')[0])-3)/2
		else:
			return	int(open('/sys/firmware/devicetree/base/chosen/kerneldev', 'r').read().replace('\0', '')[-1])

def GetCurrentImageMode():
	if SystemInfo["canMultiBoot"] and 'rootflags=data=journal' not in open('/dev/mmcblk0p1').read(): 
		return	int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[-1])

class GetImagelist():
	MOUNT = 0
	UNMOUNT = 1

	def __init__(self, callback):
		if SystemInfo["canMultiBoot"]:
			self.addin = SystemInfo["canMultiBoot"][0]
			self.endslot = SystemInfo["canMultiBoot"][1]
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
		if retval == 0 and self.phase == self.MOUNT:
			if os.path.isfile("/tmp/testmount/usr/bin/enigma2"):
				self.imagelist[self.slot] =  { 'imagename': open("/tmp/testmount/etc/issue").readlines()[-2].capitalize().strip()[:-6] + BuildVersion}
			else:
				self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			self.phase = self.UNMOUNT
			self.run()
		elif self.slot < self.endslot:
			self.slot += 1
			self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			self.phase = self.MOUNT
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback(self.imagelist)
