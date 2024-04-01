import os
import re
from Components.Renderer.Renderer import Renderer
from enigma import ePixmap, ePicLoad, eServiceCenter, eServiceReference, iServiceInformation
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import pathExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename, sanitizeFilename
from Components.Harddisk import harddiskmanager
from ServiceReference import ServiceReference
from Components.config import config

searchPaths = []
lastPiconPath = None


def initPiconPaths():
	global searchPaths
	searchPaths = []
	for mp in ('/usr/share/enigma2/', '/'):
		onMountpointAdded(mp)
	for part in harddiskmanager.getMountedPartitions():
		onMountpointAdded(part.mountpoint)


def onMountpointAdded(mountpoint):
	global searchPaths
	try:
		path = os.path.join(mountpoint, 'picon') + '/'
		if os.path.isdir(path) and path not in searchPaths:
			for fn in os.listdir(path):
				if fn.endswith('.png') or fn.endswith('.svg'):
					print("[Picon] adding path:", path)
					searchPaths.append(path)
					break
	except Exception as ex:
		print("[Picon] Failed to investigate %s:" % mountpoint, ex)


def onMountpointRemoved(mountpoint):
	global searchPaths
	path = os.path.join(mountpoint, 'picon') + '/'
	try:
		searchPaths.remove(path)
		print("[Picon] removed path:", path)
	except:
		pass


def onPartitionChange(why, part):
	if why == 'add':
		onMountpointAdded(part.mountpoint)
	elif why == 'remove':
		onMountpointRemoved(part.mountpoint)


def findPicon(serviceName):
	global lastPiconPath
	if lastPiconPath is not None:
		for ext in ('.png', '.svg'):
			pngname = lastPiconPath + serviceName + ext
			if pathExists(pngname):
				return pngname
	global searchPaths
	for path in searchPaths:
		if pathExists(path):
			for ext in ('.png', '.svg'):
				pngname = path + serviceName + ext
				if pathExists(pngname):
					lastPiconPath = path
					return pngname
	return ""


def getPiconName(serviceRef):
	service = eServiceReference(serviceRef)
	if service.getPath().startswith("/") and serviceRef.startswith("1:"):
		info = eServiceCenter.getInstance().info(eServiceReference(serviceRef))
		refstr = info and info.getInfoString(service, iServiceInformation.sServiceref)
		serviceRef = refstr and eServiceReference(refstr).toCompareString()
	#remove the path and name fields, and replace ':' by '_'
	fields = GetWithAlternative(serviceRef).split(':', 10)[:10]
	if not fields or len(fields) < 10:
		return ""
	pngname = findPicon('_'.join(fields))
	if not pngname and not fields[6].endswith("0000"):
		#remove "sub-network" from namespace
		fields[6] = fields[6][:-4] + "0000"
		pngname = findPicon('_'.join(fields))
	if not pngname and fields[0] != '1':
		#fallback to 1 for IPTV streams
		fields[0] = '1'
		pngname = findPicon('_'.join(fields))
	if not pngname and fields[2] != '2':
		#fallback to 1 for TV services with non-standard service types
		fields[2] = '1'
		pngname = findPicon('_'.join(fields))
	if not pngname: # picon by channel name
		utf8_name = sanitizeFilename(ServiceReference(serviceRef).getServiceName()).lower()
		name = re.sub("[^a-z0-9]", "", utf8_name.replace("&", "and").replace("+", "plus").replace("*", "star"))
		if name:
			pngname = findPicon(name) or findPicon(re.sub("(fhd|uhd|hd|sd|4k)$", "", name).strip()) or findPicon(utf8_name)
			if not pngname and len(name) > 6:
				series = re.sub(r"s[0-9]*e[0-9]*$", "", name)
				pngname = findPicon(series)
	return pngname


class Picon(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.usePicLoad = False
		self.PicLoad = ePicLoad()
		self.PicLoad.PictureData.get().append(self.updatePicon)
		self.piconsize = (0, 0)
		self.pngname = ""
		self.service_text = ""
		self.lastPath = None
		pngname = findPicon("picon_default")
		self.defaultpngname = None
		self.showPicon = True
		if not pngname:
			tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
			if pathExists(tmp):
				pngname = tmp
			else:
				pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
		if os.path.getsize(pngname):
			self.defaultpngname = pngname

	def addPath(self, value):
		if pathExists(value):
			global searchPaths
			if not value.endswith('/'):
				value += '/'
			if value not in searchPaths:
				searchPaths.append(value)

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.addPath(value)
				attribs.remove((attrib, value))
			elif attrib == "isFrontDisplayPicon":
				self.showPicon = value == "0"
				attribs.remove((attrib, value))
			elif attrib == "usePicLoad":
				self.usePicLoad = value == "1"
				attribs.remove((attrib, value))
			elif attrib == "size":
				self.piconsize = value
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def updatePicon(self, picInfo=None):
		ptr = self.PicLoad.getData()
		if ptr is not None and self.instance:
			self.instance.setPixmap(ptr.__deref__())
			self.instance.show()

	def changed(self, what):
		if self.instance:
			if self.showPicon or config.usage.show_picon_in_display.value:
				pngname = ""
				if what[0] in (self.CHANGED_ALL, self.CHANGED_SPECIFIC):
					if self.usePicLoad and self.source.text and self.service_text and self.source.text == self.service_text:
						return
					self.service_text = self.source.text
					pngname = getPiconName(self.source.text)
				else:
					if what[0] == self.CHANGED_CLEAR:
						self.service_text = self.pngname = ""
						if self.visible:
							self.instance.hide()
					return
				if not pngname: # no picon for service found
					pngname = self.defaultpngname
				if self.pngname != pngname:
					if pngname:
						if self.usePicLoad:
							self.PicLoad.setPara((self.piconsize[0], self.piconsize[1], 0, 0, 1, 1, "#FF000000"))
							self.PicLoad.startDecode(pngname)
						else:
							self.instance.setScale(1)
							self.instance.setPixmapFromFile(pngname)
							self.instance.show()
					else:
						self.instance.hide()
					self.pngname = pngname
			elif self.visible:
				self.instance.hide()


harddiskmanager.on_partition_list_change.append(onPartitionChange)
initPiconPaths()
