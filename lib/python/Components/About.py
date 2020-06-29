# -*- coding: utf-8 -*-
import sys, os, time
import re
from Tools.HardwareInfo import HardwareInfo
from enigma import getBoxType
from Tools.Directories import fileExists
from glob import glob

def getFlashMemory(folder='/'):
	try:
		diskSpace = os.statvfs(folder)
		available = float(diskSpace.f_bsize * diskSpace.f_bavail)
		fspace=round(float((available) / (1024.0*1024.0)),2)
		spacestr=str(fspace)+'M'
		return spacestr
	except:
		pass
	return _("unavailable")

def getVersionString():
	return getImageVersionString()

def getImageVersionString():
	try:
		if os.path.isfile('/var/lib/opkg/status'):
			st = os.stat('/var/lib/opkg/status')
		tm = time.localtime(st.st_mtime)
		if tm.tm_year >= 2011:
			return time.strftime("%Y-%m-%d %H:%M:%S", tm)
	except:
		pass
	return _("unavailable")

# WW -placeholder for BC purposes, commented out for the moment in the Screen
def getFlashDateString():
	return _("unknown")

def getBuildDateString():
	try:
		if os.path.isfile('/etc/version'):
			f = open("/etc/version","r")
			version = f.read()
			f.close()
			return "%s-%s-%s" % (version[:4], version[4:6], version[6:8])
	except:
		pass
	return _("unknown")

def getUpdateDateString():
	if fileExists("/var/lib/opkg/info/openpli-bootlogo.control"):
		with open("/var/lib/opkg/info/openpli-bootlogo.control", "r") as fp:
			build = [x.split("-")[-2:-1][0][-8:] for x in fp if x.startswith("Version:")][0]
			if build.isdigit():
				return  "%s-%s-%s" % (build[:4], build[4:6], build[6:])
	return _("unknown")

def getEnigmaVersionString():
	import enigma
	enigma_version = enigma.getEnigmaVersionString()
	if '-(no branch)' in enigma_version:
		enigma_version = enigma_version [:-12]
	return enigma_version

def getGStreamerVersionString(cpu):
	if fileExists(glob("/var/lib/opkg/info/gstreamer[0-9].[0-9].control")[0]):
		with open(glob("/var/lib/opkg/info/gstreamer[0-9].[0-9].control")[0], "r") as fp:
			gst = [x.split("Version: ") for x in fp if x.startswith("Version:")][0]
			return "%s" % gst[1].split("+")[0].replace("\n","")
	else:
		return _("Not Required") if cpu.upper().startswith('HI') else _("Not Installed")

def getFFmpegVersionString():
	if fileExists("/var/lib/opkg/info/ffmpeg.control"):
		with open("/var/lib/opkg/info/ffmpeg.control", "r") as fp:
			ffmpeg = [x.split("Version: ") for x in fp if x.startswith("Version:")][0]
			version = ffmpeg[1].split("-")[0].replace("\n","")
			return "%s" % version.split("+")[0]
	else:
		return ""

def getKernelVersionString():
	if fileExists("/proc/version"):
		f = open("/proc/version","r")
		return f.read().split(' ', 4)[2].split('-',2)[0]
		f.close()
	else:
		return _("unknown")

def getHardwareTypeString():
	return HardwareInfo().get_device_string()

def getImageTypeString():
	if fileExists("/etc/issue"):
		f = open("/etc/issue")
		image_type = f.readlines()[-2].strip()[:-6]
		return image_type.capitalize()
		f.close()
	else:
		return _("undefined")

def getCPUInfoString():
	try:
		cpu_count = 0
		cpu_speed = 0
		processor = ""
		with open("/proc/cpuinfo") as f:
			for line in f.readlines():
				line = [x.strip() for x in line.strip().split(":")]
				if not processor and line[0] in ("system type", "model name", "Processor"):
					processor = line[1].split()[0]
				elif not cpu_speed and line[0] == "cpu MHz":
					cpu_speed = "%1.0f" % float(line[1])
				elif line[0] == "processor":
					cpu_count += 1

		if processor.startswith("ARM") and os.path.isfile("/proc/stb/info/chipset"):
			f = open("/proc/stb/info/chipset")
			processor = "%s (%s)" % (f.readline().strip().upper(), processor)
			f.close()

		if not cpu_speed:
			if fileExists("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"):
				f = open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
				cpu_speed = int(f.read()) / 1000
				f.close()
			elif fileExists("/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency"):
				import binascii
				f = open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb')
				cpu_speed = int(int(binascii.hexlify(f.read()), 16) / 100000000) * 100
				f.close()

		temperature = None
		if os.path.isfile('/proc/stb/fp/temp_sensor_avs'):
			f = open("/proc/stb/fp/temp_sensor_avs")
			temperature = f.readline().replace('\n','')
			f.close()
		elif os.path.isfile('/proc/stb/power/avs'):
			f = open("/proc/stb/power/avs")
			temperature = f.readline().replace('\n','')
			f.close()
		elif os.path.isfile('/proc/stb/fp/temp_sensor'):
			f = open("/proc/stb/fp/temp_sensor")
			temperature = f.readline().replace('\n','')
			f.close()
		elif os.path.isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
			f = open("/sys/devices/virtual/thermal/thermal_zone0/temp")
			try:
				temperature = int(f.read().strip())/1000
			except:
				pass
			f.close()
		elif os.path.isfile("/proc/hisi/msp/pm_cpu"):
			f = open("/proc/hisi/msp/pm_cpu")
			try:
				temperature = re.search('temperature = (\d+) degree', f.read()).group(1)
			except:
				pass
			f.close()
		if temperature:
			return "%s %s MHz (%s) %s\xb0C" % (processor, cpu_speed, ngettext("%d core", "%d cores", cpu_count) % cpu_count, temperature)
		return "%s %s MHz (%s)" % (processor, cpu_speed, ngettext("%d core", "%d cores", cpu_count) % cpu_count)
	except:
		return _("undefined")

def getDriverInstalledDate():
	if fileExists(glob("/var/lib/opkg/info/*-dvb-modules-*.control")[0]):
		with open(glob("/var/lib/opkg/info/*-dvb-modules-*.control")[0], "r") as fp:
			if getBoxType() in ("dm800","dm8000"):
				driver = [x.split("-")[-2:-1][0][-9:] for x in fp if x.startswith("Version:")][0]
				return  "%s-%s-%s" % (driver[:4], driver[4:6], driver[6:])
			else:
				driver = [x.split("-")[-2:-1][0][-8:] for x in fp if x.startswith("Version:")][0]
				return  "%s-%s-%s" % (driver[:4], driver[4:6], driver[6:])
	elif fileExists(glob("/var/lib/opkg/info/*-dvb-proxy-*.control")[0]):
		with open(glob("/var/lib/opkg/info/*-dvb-proxy-*.control")[0], "r") as fp:
			driver = [x.split("Version:") for x in fp if x.startswith("Version:")][0]
			return  "%s" % driver[1].replace("\n","")
	elif fileExists(glob("/var/lib/opkg/info/*-platform-util-*.control")[0]):
		with open(glob("/var/lib/opkg/info/*-platform-util-*.control")[0], "r") as fp:
			driver = [x.split("Version:") for x in fp if x.startswith("Version:")][0]
			return  "%s" % driver[1].replace("\n","")	
	else:
		return _("unknown")

def getPythonVersionString():
	try:
		import commands
		status, output = commands.getstatusoutput("python -V")
		return output.split(' ')[1]
	except:
		return _("unknown")

def GetIPsFromNetworkInterfaces():
	import socket, fcntl, struct, array, sys
	is_64bits = sys.maxsize > 2**32
	struct_size = 40 if is_64bits else 32
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	max_possible = 8 # initial value
	while True:
		_bytes = max_possible * struct_size
		names = array.array('B')
		for i in range(0, _bytes):
			names.append(0)
		outbytes = struct.unpack('iL', fcntl.ioctl(
			s.fileno(),
			0x8912,  # SIOCGIFCONF
			struct.pack('iL', _bytes, names.buffer_info()[0])
		))[0]
		if outbytes == _bytes:
			max_possible *= 2
		else:
			break
	namestr = names.tostring()
	ifaces = []
	for i in range(0, outbytes, struct_size):
		iface_name = bytes.decode(namestr[i:i+16]).split('\0', 1)[0].encode('ascii')
		if iface_name != 'lo':
			iface_addr = socket.inet_ntoa(namestr[i+20:i+24])
			ifaces.append((iface_name, iface_addr))
	return ifaces

def getBoxUptime():
	if not fileExists("/proc/uptime"):
		return '-'
	try:
		time = ''
		f = open("/proc/uptime", "rb")
		secs = int(f.readline().split('.')[0])
		f.close()
		if secs > 86400:
			days = secs / 86400
			secs = secs % 86400
			time = ngettext("%d day","%d days", days) % days + " "
		h = secs / 3600
		m = (secs % 3600) / 60
		time += ngettext("%d hour", "%d hours", h) % h + " "
		time += ngettext("%d minute", "%d minutes", m) % m
		return  "%s" % time
	except:
		return '-'

# For modules that do "from About import about"
about = sys.modules[__name__]
