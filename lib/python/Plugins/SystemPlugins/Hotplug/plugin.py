from Plugins.Plugin import PluginDescriptor
from Components.Harddisk import harddiskmanager
from Screens.Screen import Screen
from Screens.Opkg import Opkg
from Components.Opkg import OpkgComponent
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.SelectionList import SelectionList
from twisted.internet.protocol import Protocol, Factory
import os

# globals
hotplugNotifier = []
audiocd = False


def AudiocdAdded():
	global audiocd
	if audiocd:
		return True
	else:
		return False


def processHotplugData(self, v):
	print("[Hotplug.plugin.py]:", v)
	action = v.get("ACTION")
	device = v.get("DEVPATH")
	physdevpath = v.get("PHYSDEVPATH")
	media_state = v.get("X_E2_MEDIA_STATUS")
	global audiocd

	dev = device.split('/')[-1]

	if action == "add":
		error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugPartition(dev, physdevpath)
	elif action == "remove":
		harddiskmanager.removeHotplugPartition(dev)
	elif action == "audiocdadd":
		audiocd = True
		media_state = "audiocd"
		error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugAudiocd(dev, physdevpath)
		print("[Hotplug.plugin.py] AUDIO CD ADD")
	elif action == "audiocdremove":
		audiocd = False
		file = []
		# Removing the invalid playlist.e2pls If its still the audio cd's list
		# Default setting is to save last playlist on closing Mediaplayer.
		# If audio cd is removed after Mediaplayer was closed,
	# the playlist remains in if no other media was played.
		if os.path.isfile('/etc/enigma2/playlist.e2pls'):
			with open('/etc/enigma2/playlist.e2pls', 'r') as f:
				file = f.readline().strip()
		if file:
			if '.cda' in file:
				try:
					os.remove('/etc/enigma2/playlist.e2pls')
				except OSError:
					pass
		harddiskmanager.removeHotplugPartition(dev)
		print("[Hotplug.plugin.py] REMOVING AUDIOCD")
	elif media_state is not None:
		if media_state == '1':
			harddiskmanager.removeHotplugPartition(dev)
			harddiskmanager.addHotplugPartition(dev, physdevpath)
		elif media_state == '0':
			harddiskmanager.removeHotplugPartition(dev)

	for callback in hotplugNotifier:
		try:
			callback(dev, action or media_state)
		except AttributeError:
			hotplugNotifier.remove(callback)


class Hotplug(Protocol):
	def connectionMade(self):
		print("[Hotplug.plugin.py] connection!")
		self.received = ""

	def dataReceived(self, data):
		self.received += data.decode()
		print("[Hotplug.plugin.py] complete", self.received)

	def connectionLost(self, reason):
		print("[Hotplug.plugin.py] connection lost!")
		data = self.received.split('\0')[:-1]
		v = {}
		for x in data:
			i = x.find('=')
			var, val = x[:i], x[i + 1:]
			v[var] = val
		processHotplugData(self, v)


class OpkgInstaller(Screen):
	skin = """
		<screen name="OpkgInstaller" position="center,center" size="550,450" title="Install extensions" >
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="list" position="5,50" size="540,360" />
			<ePixmap pixmap="div-h.png" position="0,410" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="introduction" render="Label" position="5,420" zPosition="10" size="550,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, list):
		Screen.__init__(self, session)

		self.list = SelectionList()
		self["list"] = self.list

		p = 0
		if len(list):
			p = list[0].rfind("/")
			title = list[0][:p]
			self.title = ("%s %s %s") % (_("Install extensions"), _("from"), title)

		for listindex in range(len(list)):
			self.list.addSelection(list[listindex][p + 1:], list[listindex], listindex, False)
		self.list.sort()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("Invert"))
		self["introduction"] = StaticText(_("Press OK to toggle the selection."))

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.list.toggleSelection,
			"cancel": self.close,
			"red": self.close,
			"green": self.install,
			"blue": self.list.toggleAllSelection
		}, -1)

	def install(self):
		list = self.list.getSelectionsList()
		cmdList = []
		for item in list:
			cmdList.append((OpkgComponent.CMD_INSTALL, {"package": item[1]}))
		self.session.open(Opkg, cmdList=cmdList)


def filescan_open(list, session, **kwargs):
	filelist = [x.path for x in list]
	session.open(OpkgInstaller, filelist) # list


def autostart(reason, **kwargs):
	if reason == 0:
		from twisted.internet import reactor, error
		try:
			if os.path.exists("/tmp/hotplug.socket"):
				os.remove("/tmp/hotplug.socket")
			factory = Factory()
			factory.protocol = Hotplug
			reactor.listenUNIX("/tmp/hotplug.socket", factory)
		except (OSError, error.CannotListenError) as err:
			print("[Hotplug]", err)


def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return \
		Scanner(mimetypes=["application/x-debian-package"],
			paths_to_scan=[
					ScanPath(path="ipk", with_subdirs=True),
					ScanPath(path="", with_subdirs=False),
				],
			name="Opkg",
			description=_("Install extensions"),
			openfnc=filescan_open, )


def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Hotplug"), description=_("listens to hotplug events"), where=PluginDescriptor.WHERE_AUTOSTART, needsRestart=True, fnc=autostart),
		PluginDescriptor(name=_("Opkg"), where=PluginDescriptor.WHERE_FILESCAN, needsRestart=False, fnc=filescan)]
