from os import path
from fcntl import ioctl
from struct import pack, unpack
from time import time, localtime, gmtime
from enigma import getBoxType
from Tools.Directories import fileExists

def getFPVersion():
	ret = None
	if fileExists("/proc/stb/fp/version"):
		fp = open("/proc/stb/fp/version", "r")
		if getBoxType() in ('dm7080','dm820','dm520','dm525','dm900','dm920'):
			ret = fp.read()
		else:
			ret = long(fp.read())
		fp.close()
	elif fileExists("/dev/dbox/fp0"):
		fp = open("/dev/dbox/fp0")
		ret = ioctl(fp.fileno(),0)
		fp.close()
	elif fileExists("/sys/firmware/devicetree/base/bolt/tag"):
		fp = open("/sys/firmware/devicetree/base/bolt/tag", "r")
		ret = fp.read().rstrip("\0")
		fp.close()
	else:
		print "getFPVersion failed!"
	return ret

def setFPWakeuptime(wutime):
	if fileExists("/proc/stb/fp/wakeup_time"):
		fp = open("/proc/stb/fp/wakeup_time", "w")
		fp.write(str(wutime))
	elif fileExists("/dev/dbox/fp0"):
		fp = open("/dev/dbox/fp0")
		ioctl(fp.fileno(), 6, pack('L', wutime))
	else:
		print "setFPWakeupTime failed!"

def setRTCoffset(forsleep=None):
	if forsleep is None:
		forsleep = (localtime(time()).tm_hour-gmtime(time()).tm_hour)*3600
	if fileExists("/proc/stb/fp/rtc_offset"):
		fp = open("/proc/stb/fp/rtc_offset", "w")
		fp.write(str(forsleep))
		print "[RTC] set RTC offset to %s sec." % (forsleep)
		fp.close()

def setRTCtime(wutime):
	if path.exists("/proc/stb/fp/rtc_offset"):
		setRTCoffset()
	if fileExists("/proc/stb/fp/rtc"):
		fp = open("/proc/stb/fp/rtc", "w")
		fp.write(str(wutime))
		fp.close()
	elif fileExists("/dev/dbox/fp0"):
		fp = open("/dev/dbox/fp0")
		ioctl(fp.fileno(), 0x101, pack('L', wutime))
		fp.close()
	else:
		print "setRTCtime failed!"

def getFPWakeuptime():
	ret = 0
	if fileExists("/proc/stb/fp/wakeup_time"):
		fp = open("/proc/stb/fp/wakeup_time", "r")
		ret = long(fp.read())
		fp.close()
	elif fileExists("/dev/dbox/fp0"):
		fp = open("/dev/dbox/fp0")
		ret = unpack('L', ioctl(fp.fileno(), 5, '    '))[0]
		fp.close()
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
		fp = open("/proc/stb/fp/was_timer_wakeup", "r")
		wasTimerWakeup = int(fp.read()) and True or False
		if wasTimerWakeup:
			clearFPWasTimerWakeup()
		fp.close()
	elif fileExists("/dev/dbox/fp0"):
		fp = open("/dev/dbox/fp0")
		wasTimerWakeup = unpack('B', ioctl(fp.fileno(), 9, ' '))[0] and True or False
		if wasTimerWakeup:
			clearFPWasTimerWakeup()
		fp.close()
	else:
		print "wasTimerWakeup failed!"
	return wasTimerWakeup

def clearFPWasTimerWakeup():
	if fileExists("/proc/stb/fp/was_timer_wakeup"):
		fp = open("/proc/stb/fp/was_timer_wakeup", "w")
		fp.write('0')
		fp.close()
	elif fileExists("/dev/dbox/fp0"):
		fp = open("/dev/dbox/fp0")
		ioctl(fp.fileno(), 10)
		fp.close()
	else:
		print "clearFPWasTimerWakeup failed!"
