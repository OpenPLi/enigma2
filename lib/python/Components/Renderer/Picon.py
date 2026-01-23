from os import listdir, path as ospath
from re import sub

from enigma import ePixmap, ePicLoad, eServiceCenter, eServiceReference, iServiceInformation

from Components.config import config
from Components.Harddisk import harddiskmanager
from Components.Renderer.Renderer import Renderer
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import pathExists, SCOPE_CURRENT_SKIN, resolveFilename, sanitizeFilename


class PiconLocator:
	def __init__(self, piconDirectories=["picon"]):
		harddiskmanager.on_partition_list_change.append(self.__onPartitionChange)
		self.piconDirectories = piconDirectories
		self.activePiconPath = None
		self.searchPaths = []
		for mp in ("/usr/share/enigma2/", "/"):
			self.__onMountpointAdded(mp)
		for part in harddiskmanager.getMountedPartitions():
			self.__onMountpointAdded(part.mountpoint)

	def __onMountpointAdded(self, mountpoint):
		for piconDirectory in self.piconDirectories:
			try:
				path = ospath.join(mountpoint, piconDirectory) + "/"
				if ospath.isdir(path) and path not in self.searchPaths:
					for fn in listdir(path):
						if fn.endswith(".png") or fn.endswith(".svg"):
							print("[PiconLocator] adding path:", path)
							self.searchPaths.append(path)
							break
			except:
				pass

	def __onMountpointRemoved(self, mountpoint):
		for piconDirectory in self.piconDirectories:
			path = ospath.join(mountpoint, piconDirectory) + "/"
			try:
				self.searchPaths.remove(path)
				print("[PiconLocator] removed path:", path)
			except:
				pass

	def __onPartitionChange(self, why, part):
		if why == "add":
			self.__onMountpointAdded(part.mountpoint)
		elif why == "remove":
			self.__onMountpointRemoved(part.mountpoint)

	def findPicon(self, service):
		exts = [".png", ".svg"]
		if self.activePiconPath is not None:
			for ext in exts:
				pngname = self.activePiconPath + service + ext
				if pathExists(pngname):
					return pngname
		else:
			for path in self.searchPaths:
				for ext in exts:
					pngname = path + service + ext
					if pathExists(pngname):
						self.activePiconPath = path
						return pngname
		return ""

	def addSearchPath(self, value):
		if pathExists(value):
			if not value.endswith("/"):
				value += "/"
			if not value.startswith(("/media/net", "/media/autofs")) and value not in self.searchPaths:
				self.searchPaths.append(value)

	def getPiconName(self, serviceRef):
		if serviceRef is None:
			return ""
		service = eServiceReference(serviceRef)
		if service.getPath().startswith("/") and serviceRef.startswith("1:"):  # for when serviceRef is a recording path
			info = eServiceCenter.getInstance().info(eServiceReference(serviceRef))
			refstr = info and info.getInfoString(service, iServiceInformation.sServiceref)
			serviceRef = refstr and eServiceReference(refstr).toCompareString()
		# remove the path and name fields, and replace ":" by "_"
		fields = GetWithAlternative(serviceRef).split(":", 10)[:10]
		if not fields or len(fields) < 10:
			return ""
		basenames = ["_".join(fields), (p := "1_0_1_%s_0_0_0") % (x := ("_".join(fields[3:7]))), p % (x[:-4] + "0000")]
		for basename in dict.fromkeys(basenames).keys():  # skip duplicates, maintain order
			if pngname := self.findPicon(basename):
				break
		if not pngname:  # picon by channel name
			if (sname := eServiceReference(serviceRef).getServiceName()) and "SID 0x" not in sname and (utf8_name := sanitizeFilename(sname).lower()) and utf8_name != "__":  # avoid lookups on zero length service names
				legacy_name = sub("[^a-z0-9]", "", utf8_name.replace("&", "and").replace("+", "plus").replace("*", "star"))  # legacy ascii service name picons
				pngname = self.findPicon(utf8_name) or legacy_name and self.findPicon(legacy_name) or self.findPicon(sub(r"(fhd|uhd|hd|sd|4k)$", "", utf8_name).strip()) or legacy_name and self.findPicon(sub(r"(fhd|uhd|hd|sd|4k)$", "", legacy_name).strip())
		return pngname


piconLocator = None


def initPiconPaths():
	global piconLocator
	piconLocator = PiconLocator()


initPiconPaths()


def getPiconName(serviceRef):
	return piconLocator.getPiconName(serviceRef)


class Picon(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.pngname = None
		self.defaultpngname = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
		self.usePicLoad = False
		self.PicLoad = ePicLoad()
		self.PicLoad.PictureData.get().append(self.updatePicon)
		self.piconsize = (0, 0)
		self.service_text = ""
		self.lastPath = None
		self.showPicon = True

	def addPath(self, value):
		if pathExists(value):
			if not value.endswith('/'):
				value += '/'
			if value not in piconLocator.searchPaths:
				piconLocator.searchPaths.append(value)

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
					pngname = piconLocator.getPiconName(self.source.text)
				else:
					if what[0] == self.CHANGED_CLEAR:
						self.service_text = self.pngname = ""
						if self.visible:
							self.instance.hide()
					return
				if not pngname:  # no picon for service found
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
