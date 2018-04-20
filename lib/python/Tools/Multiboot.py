from Components.SystemInfo import SystemInfo
from Components.Console import Console
import os

def GetCurrentImage():
	if SystemInfo["canMultiBoot"]:
		if not SystemInfo["canMode12"]:
			return (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[1].split('p')[1].split(' ')[0])-3)/2
		else:
			return	int(open('/sys/firmware/devicetree/base/chosen/kerneldev', 'r').read().replace('\0', '')[-1])

def GetCurrentImageMode():
	if SystemInfo["canMultiBoot"] and SystemInfo["canMode12"]: 
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
				self.imagelist[self.slot] =  { 'imagename': open("/tmp/testmount/etc/issue").readlines()[-2].capitalize().strip()[:-6]}
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

class WriteStartup():
	MOUNT = 0
	UNMOUNT = 1

	def __init__(self, Contents, callback):
		if SystemInfo["canMultiBoot"]:
			if not os.path.isdir('/tmp/testmount'):
				os.mkdir('/tmp/testmount')
			self.callback = callback
			self.container = Console()
			self.phase = self.MOUNT
			if not SystemInfo["canMode12"]:
				self.slot = Contents
			else:
				self.contents = Contents			
			self.run()
		else:	
			callback({})
	
	def run(self):
		volume = SystemInfo["canMultiBoot"][2]
		self.container.ePopen('mount /dev/%s /tmp/testmount' %volume if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
#	If GigaBlue then Contents = slot, use slot to read STARTUP_slot
#	If multimode and bootmode 1 or 12, then Contents is STARTUP file, so just write it to STARTUP.			
	def appClosed(self, data, retval, extra_args):
		if retval == 0 and self.phase == self.MOUNT:
			if os.path.isfile("/tmp/testmount/STARTUP"):
				if 'coherent_poll=2M' in open("/proc/cmdline", "r").read():
					self.contents = open('/tmp/testmount/STARTUP_%s'% self.slot).read()
				open('/tmp/testmount/STARTUP', 'w').write(self.contents)
			self.phase = self.UNMOUNT
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback()
