from Components.SystemInfo import SystemInfo
from enigma import eConsoleAppContainer
import os

def GetCurrentImage():
	return SystemInfo["canMultiBoot"] and int(open('/sys/firmware/devicetree/base/chosen/kerneldev', 'r').read().replace('\0', '')[-1])

class GetImagelist():
	MOUNT = 0
	UNMOUNT = 1

	def __init__(self, callback):
		if SystemInfo["canMultiBoot"]:
			self.callback = callback
			self.imagelist = {}
			if not os.path.isdir('/tmp/testmount'):
				os.mkdir('/tmp/testmount')
			self.container = eConsoleAppContainer()
			self.container.appClosed.append(self.appClosed)
			self.slot = 1
			self.phase = self.MOUNT
			self.run()
		else:	
			callback({})
	
	def run(self):
		retval = self.container.execute('mount /dev/mmcblk0p%s /tmp/testmount' % str(self.slot * 2 + 1) if self.phase == self.MOUNT else 'umount /tmp/testmount')
		if retval:
			self.appClosed(retval)
			
	def appClosed(self, retval):
		if retval == 0 and self.phase == self.MOUNT:
			if os.path.isfile("/tmp/testmount/usr/bin/enigma2"):
				self.imagelist[self.slot] =  { 'imagename': open("/tmp/testmount/etc/issue").readlines()[-2].capitalize().strip()[:-6] }
			self.phase = self.UNMOUNT
			self.run()
		elif self.slot < 4:
			self.slot += 1
			self.phase = self.MOUNT
			self.run()
		else:
			del self.container.appClosed[:]
			del self.container
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback(self.imagelist)

