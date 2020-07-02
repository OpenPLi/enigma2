from os import path
from fcntl import ioctl
from struct import pack, unpack
from time import time, localtime, gmtime
from enigma import getBoxType
from Tools.Directories import fileExists

def getFPVersion():
	ret = None
	if fileExists("/proc/stb/fp/version"):
		with open("/proc/stb/fp/version", "r") as fp:
			if getBoxType() in ('dm7080','dm820','dm520','dm525','dm900','dm920'):
				ret = fp.read()
			else:
				ret = long(fp.read())
		return ret
	elif fileExists("/dev/dbox/fp0"):
		with open("/dev/dbox/fp0") as fp:
			ret = ioctl(fp.fileno(),0)
		return ret
	elif fileExists("/sys/firmware/devicetree/base/bolt/tag"):
		with open("/sys/firmware/devicetree/base/bolt/tag", "r") as fp:
			ret = fp.read().rstrip("\0")
		return ret
	else:
		print "getFPVersion failed!"
		return ret

def setFPWakeuptime(wutime):
	if fileExists("/proc/stb/fp/wakeup_time"):
		with open("/proc/stb/fp/wakeup_time", "w") as fp:
			fp.write(str(wutime))
		return
	elif fileExists("/dev/dbox/fp0"):
		with open("/dev/dbox/fp0") as fp:
			ioctl(fp.fileno(), 6, pack('L', wutime))
		return
	else:
		print "setFPWakeupTime failed!"

def setRTCoffset(forsleep=None):
	if forsleep is None:
		forsleep = (localtime(time()).tm_hour-gmtime(time()).tm_hour)*3600
	with open("/proc/stb/fp/rtc_offset", "w") as fp:
		fp.write(str(forsleep))
	print "[RTC] set RTC offset to %s sec." % (forsleep)

def setRTCtime(wutime):
	if path.exists("/proc/stb/fp/rtc_offset"):
		setRTCoffset()
	if fileExists("/proc/stb/fp/rtc"):
		with open("/proc/stb/fp/rtc", "w") as fp:
			fp.write(str(wutime))
		return
	elif fileExists("/dev/dbox/fp0"):
		with open("/dev/dbox/fp0") as fp:
			ioctl(fp.fileno(), 0x101, pack('L', wutime))
		return
	else:
		print "setRTCtime failed!"

def getFPWakeuptime():
	ret = 0
	if fileExists("/proc/stb/fp/wakeup_time"):
		with open("/proc/stb/fp/wakeup_time", "r") as fp:
			ret = long(fp.read())
		return ret
	elif fileExists("/dev/dbox/fp0"):
		with open("/dev/dbox/fp0") as fp:
			ret = unpack('L', ioctl(fp.fileno(), 5, '    '))[0]
		return ret
	else:
		print "getFPWakeupTime failed!"
		return ret


wasTimerWakeup = None

def getFPWasTimerWakeup():
	global wasTimerWakeup
	if wasTimerWakeup is not None:
		return wasTimerWakeup
	wasTimerWakeup = False
	if fileExists("/proc/stb/fp/was_timer_wakeup"):
		with open("/proc/stb/fp/was_timer_wakeup", "r") as fp:
			wasTimerWakeup = int(fp.read()) and True or False
		if wasTimerWakeup:
			clearFPWasTimerWakeup()
		return wasTimerWakeup
	elif fileExists("/dev/dbox/fp0"):
		with open("/dev/dbox/fp0") as fp:
			wasTimerWakeup = unpack('B', ioctl(fp.fileno(), 9, ' '))[0] and True or False
		if wasTimerWakeup:
			clearFPWasTimerWakeup()
		return wasTimerWakeup
	else:
		print "wasTimerWakeup failed!"
		return wasTimerWakeup

def clearFPWasTimerWakeup():
	if fileExists("/proc/stb/fp/was_timer_wakeup"):
		with open("/proc/stb/fp/was_timer_wakeup", "w") as fp:
			fp.write('0')
		return
	elif fileExists("/dev/dbox/fp0"):
		with open("/dev/dbox/fp0") as fp:
			ioctl(fp.fileno(), 10)
		return
	else:
		print "clearFPWasTimerWakeup failed!"
