from os import path
from fcntl import ioctl
from struct import pack, unpack
from time import time, localtime, gmtime
from enigma import getBoxType

def getFPVersion():
	ret = None
	try:
		fp = open("/proc/stb/fp/version", "r")
		if getBoxType() in ('dm7080','dm820','dm520','dm525','dm900','dm920'):
			ret = fp.read()
		else:
			ret = long(fp.read())
		return ret
	except IOError:
		pass
	finally:
    		fp.close()
	try:
		fp = open("/dev/dbox/fp0")
		ret = ioctl(fp.fileno(),0)
		return ret
	except IOError:
		pass
	finally:
    		fp.close()
	try:
		fp = open("/sys/firmware/devicetree/base/bolt/tag", "r")
		ret = fp.read().rstrip("\0")
		return ret
	except IOError:
		pass
	finally:
    		fp.close()
	print "getFPVersion failed!"
	return ret

def setFPWakeuptime(wutime):
	try:
		fp = open("/proc/stb/fp/wakeup_time", "w")
		fp.write(str(wutime))
		return
	except IOError:
		pass
	finally:
    		fp.close()
	try:
		fp = open("/dev/dbox/fp0")
		ioctl(fp.fileno(), 6, pack('L', wutime))
		return
	except IOError:
		pass
	finally:
    		fp.close()
	print "setFPWakeupTime failed!"

def setRTCoffset(forsleep=None):
	if forsleep is None:
		forsleep = (localtime(time()).tm_hour-gmtime(time()).tm_hour)*3600
	try:
		fp = open("/proc/stb/fp/rtc_offset", "w")
		fp.write(str(forsleep))
		print "[RTC] set RTC offset to %s sec." % (forsleep)
	except IOError:
		print "setRTCoffset failed!"
	finally:
    		fp.close()

def setRTCtime(wutime):
	if path.exists("/proc/stb/fp/rtc_offset"):
		setRTCoffset()
	try:
		fp = open("/proc/stb/fp/rtc", "w")
		fp.write(str(wutime))
		return
	except IOError:
		pass
	finally:
    		fp.close()
	try:
		fp = open("/dev/dbox/fp0")
		ioctl(fp.fileno(), 0x101, pack('L', wutime))
		return
	except IOError:
		pass
	finally:
    		fp.close()
	print "setRTCtime failed!"

def getFPWakeuptime():
	ret = 0
	try:
		fp = open("/proc/stb/fp/wakeup_time", "r")
		ret = long(fp.read())
		return ret
	except IOError:
		pass
	finally:
    		fp.close()
	try:
		fp = open("/dev/dbox/fp0")
		ret = unpack('L', ioctl(fp.fileno(), 5, '    '))[0]
		return ret
	except IOError:
		pass
	finally:
    		fp.close()
	print "getFPWakeupTime failed!"
	return ret

wasTimerWakeup = None

def getFPWasTimerWakeup():
	global wasTimerWakeup
	if wasTimerWakeup is not None:
		return wasTimerWakeup
	wasTimerWakeup = False
	try:
		fp = open("/proc/stb/fp/was_timer_wakeup", "r")
		wasTimerWakeup = int(fp.read()) and True or False
		if wasTimerWakeup:
			clearFPWasTimerWakeup()
		return wasTimerWakeup
	except IOError:
		pass
	finally:
    		fp.close()
	try:
		fp = open("/dev/dbox/fp0")
		wasTimerWakeup = unpack('B', ioctl(fp.fileno(), 9, ' '))[0] and True or False
		if wasTimerWakeup:
			clearFPWasTimerWakeup()
		return wasTimerWakeup
	except IOError:
		pass
	finally:
    		fp.close()
	print "wasTimerWakeup failed!"
	return wasTimerWakeup

def clearFPWasTimerWakeup():
	try:
		fp = open("/proc/stb/fp/was_timer_wakeup", "w")
		fp.write('0')
		return
	except IOError:
		pass
	finally:
    		fp.close()
	try:
		fp = open("/dev/dbox/fp0")
		ioctl(fp.fileno(), 10)
		return
	except IOError:
		pass
	finally:
    		fp.close()
	print "clearFPWasTimerWakeup failed!"
