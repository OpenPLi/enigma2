from Screens.Screen import Screen
from Components.Button import Button
from Components.ActionMap import HelpableActionMap, ActionMap, NumberActionMap
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.MovieList import MovieList, resetMoviePlayState, AUDIO_EXTENSIONS, DVD_EXTENSIONS, IMAGE_EXTENSIONS, moviePlayState
from Components.DiskInfo import DiskInfo
from Components.Pixmap import Pixmap, MultiPixmap
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.config import config, ConfigSubsection, ConfigText, ConfigInteger, ConfigLocations, ConfigSet, ConfigYesNo, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.Sources.Boolean import Boolean
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
import Components.Harddisk
from Components.UsageConfig import preferredTimerPath
from Screens.VirtualKeyBoard import VirtualKeyBoard

from Plugins.Plugin import PluginDescriptor

from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
from Screens.HelpMenu import HelpableScreen
from Screens.InputBox import PinInput
import Screens.InfoBar

from Tools.NumericalTextInput import NumericalTextInput, MAP_SEARCH_UPCASE
from Tools.Directories import resolveFilename, SCOPE_HDD
from Tools.BoundFunction import boundFunction
import Tools.Trashcan
import NavigationInstance
import RecordTimer

from enigma import eServiceReference, eServiceCenter, eTimer, eSize, iPlayableService, iServiceInformation, getPrevAsciiCode, eRCInput
import os
import time
from time import localtime, strftime
import pickle

config.movielist = ConfigSubsection()
config.movielist.moviesort = ConfigInteger(default=MovieList.SORT_GROUPWISE)
config.movielist.listtype = ConfigInteger(default=MovieList.LISTTYPE_MINIMAL)
config.movielist.description = ConfigInteger(default=MovieList.SHOW_DESCRIPTION)
config.movielist.last_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.last_timer_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.videodirs = ConfigLocations(default=[resolveFilename(SCOPE_HDD)])
config.movielist.last_selected_tags = ConfigSet([], default=[])
config.movielist.play_audio_internal = ConfigYesNo(default=True)
config.movielist.settings_per_directory = ConfigYesNo(default=True)
config.movielist.root = ConfigSelection(default="/media", choices=["/", "/media", "/media/hdd", "/media/hdd/movie", "/media/usb", "/media/usb/movie"])
config.movielist.hide_extensions = ConfigYesNo(default=False)
config.movielist.stop_service = ConfigYesNo(default=True)
config.movielist.add_bookmark = ConfigYesNo(default=True)
config.movielist.show_underlines = ConfigYesNo(default=False)
config.movielist.useslim = ConfigYesNo(default=False)

userDefinedButtons = None
last_selected_dest = []
preferredTagEditor = None

# this kludge is needed because ConfigSelection only takes numbers
# and someone appears to be fascinated by 'enums'.
l_moviesort = [
	(str(MovieList.SORT_GROUPWISE), _("default"), '02/01 & A-Z'),
	(str(MovieList.SORT_RECORDED), _("by date"), '03/02/01'),
	(str(MovieList.SORT_ALPHANUMERIC), _("alphabetic"), 'A-Z'),
	(str(MovieList.SORT_ALPHANUMERIC_FLAT), _("flat alphabetic"), 'A-Z Flat'),
	(str(MovieList.SHUFFLE), _("shuffle"), '?'),
	(str(MovieList.SORT_RECORDED_REVERSE), _("reverse by date"), '01/02/03'),
	(str(MovieList.SORT_ALPHANUMERIC_REVERSE), _("alphabetic reverse"), 'Z-A'),
	(str(MovieList.SORT_ALPHANUMERIC_FLAT_REVERSE), _("flat alphabetic reverse"), 'Z-A Flat')]
l_listtype = [(str(MovieList.LISTTYPE_ORIGINAL), _("list style default")),
	(str(MovieList.LISTTYPE_COMPACT_DESCRIPTION), _("list style compact with description")),
	(str(MovieList.LISTTYPE_COMPACT), _("list style compact")),
	(str(MovieList.LISTTYPE_MINIMAL), _("list style single line"))]

try:
	from Plugins.Extensions import BlurayPlayer
except Exception as e:
	print("[ML] BlurayPlayer not installed:", e)
	BlurayPlayer = None


def defaultMoviePath():
	from Tools.Directories import defaultRecordingLocation
	return defaultRecordingLocation(config.usage.default_path.value)


def setPreferredTagEditor(te):
	global preferredTagEditor
	if preferredTagEditor is None:
		preferredTagEditor = te
		print("Preferred tag editor changed to", preferredTagEditor)
	else:
		print("Preferred tag editor already set to", preferredTagEditor, "ignoring", te)


def getPreferredTagEditor():
	global preferredTagEditor
	return preferredTagEditor


def isTrashFolder(ref):
	if not config.usage.movielist_trashcan.value or not ref.flags & eServiceReference.mustDescent:
		return False
	path = os.path.realpath(ref.getPath())
	return path.endswith('.Trash') and path.startswith(Tools.Trashcan.getTrashFolder(path))


def isInTrashFolder(ref):
	if not config.usage.movielist_trashcan.value or not ref.flags & eServiceReference.mustDescent:
		return False
	path = os.path.realpath(ref.getPath())
	return path.startswith(Tools.Trashcan.getTrashFolder(path))


def isSimpleFile(item):
	if not item:
		return False
	if not item[0] or not item[1]:
		return False
	return (item[0].flags & eServiceReference.mustDescent) == 0


def isFolder(item):
	if not item:
		return False
	if not item[0] or not item[1]:
		return False
	return (item[0].flags & eServiceReference.mustDescent) != 0


def canMove(item):
	if not item:
		return False
	if not item[0] or not item[1]:
		return False
	if item[0].flags & eServiceReference.mustDescent:
		return not isTrashFolder(item[0])
	return True


canDelete = canMove


def canCopy(item):
	if not item:
		return False
	if not item[0] or not item[1]:
		return False
	if item[0].flags & eServiceReference.mustDescent:
		return False
	return True


def createMoveList(serviceref, dest):
	#normpath is to remove the trailing '/' from directories
	ext_ts = "%s.ts" % serviceref
	src = isinstance(serviceref, str) and "%s.ts" % serviceref or os.path.normpath(serviceref.getPath()) if os.path.exists(ext_ts) else isinstance(serviceref, str) and "%s.stream" % serviceref or os.path.normpath(serviceref.getPath())
	srcPath, srcName = os.path.split(src)
	if os.path.normpath(srcPath) == dest:
		# move file to itself is allowed, so we have to check it
		raise Exception(_("Refusing to move to the same directory"))
	# Make a list of items to move
	moveList = [(src, os.path.join(dest, srcName))]
	if isinstance(serviceref, str) or not serviceref.flags & eServiceReference.mustDescent:
		# Real movie, add extra files...
		srcBase = os.path.splitext(src)[0]
		baseName = os.path.split(srcBase)[1]
		eitName = srcBase + '.eit'
		if os.path.exists(eitName):
			moveList.append((eitName, os.path.join(dest, baseName + '.eit')))
		baseName = os.path.split(src)[1]
		for ext in ('.ap', '.cuts', '.meta', '.sc'):
			candidate = src + ext
			if os.path.exists(candidate):
				moveList.append((candidate, os.path.join(dest, baseName + ext)))
	return moveList


def moveServiceFiles(serviceref, dest, name=None, allowCopy=True):
	moveList = createMoveList(serviceref, dest)
	# Try to "atomically" move these files
	movedList = []
	try:
		try:
			for item in moveList:
				os.rename(item[0], item[1])
				movedList.append(item)
		except OSError as e:
			if e.errno == 18 and allowCopy:
				print("[MovieSelection] cannot rename across devices, trying slow move")
				from Screens.CopyFiles import moveFiles
				# start with the smaller files, do the big one later.
				moveList.reverse()
				if name is None:
					name = os.path.split(moveList[-1][0])[1]
				moveFiles(moveList, name)
				print("[MovieSelection] Moving in background...")
			else:
				raise
	except Exception as e:
		print("[MovieSelection] Failed move:", e)
		for item in movedList:
			try:
				os.rename(item[1], item[0])
			except:
				print("[MovieSelection] Failed to undo move:", item)
		# rethrow exception
		raise


def copyServiceFiles(serviceref, dest, name=None):
	# current should be 'ref' type, dest a simple path string
	moveList = createMoveList(serviceref, dest)
	# Try to "atomically" move these files
	movedList = []
	try:
		for item in moveList:
			os.link(item[0], item[1])
			movedList.append(item)
		# this worked, we're done
		return
	except Exception as e:
		print("[MovieSelection] Failed copy using link:", e)
		for item in movedList:
			try:
				os.unlink(item[1])
			except:
				print("[MovieSelection] Failed to undo copy:", item)
	#Link failed, really copy.
	from Screens.CopyFiles import copyFiles
	# start with the smaller files, do the big one later.
	moveList.reverse()
	if name is None:
		name = os.path.split(moveList[-1][0])[1]
	copyFiles(moveList, name)
	print("[MovieSelection] Copying in background...")

# Appends possible destinations to the bookmarks object. Appends tuples
# in the form (description, path) to it.


def buildMovieLocationList(bookmarks):
	inlist = []
	for d in config.movielist.videodirs.value:
		d = os.path.normpath(d)
		bookmarks.append((d, d))
		inlist.append(d)
	for p in Components.Harddisk.harddiskmanager.getMountedPartitions():
		d = os.path.normpath(p.mountpoint)
		if d in inlist:
			# improve shortcuts to mountpoints
			try:
				bookmarks[bookmarks.index((d, d))] = (p.tabbedDescription(), d)
			except:
				pass # When already listed as some "friendly" name
		else:
			bookmarks.append((p.tabbedDescription(), d))
		inlist.append(d)


class MovieBrowserConfiguration(ConfigListScreen, Screen):
	def __init__(self, session, args=0):
		Screen.__init__(self, session)
		self.setTitle(_("Movie list configuration"))
		self.skinName = ['MovieBrowserConfiguration', 'Setup']
		cfg = ConfigSubsection()
		self.cfg = cfg
		cfg.moviesort = ConfigSelection(default=str(config.movielist.moviesort.value), choices=l_moviesort)
		cfg.listtype = ConfigSelection(default=str(config.movielist.listtype.value), choices=l_listtype)
		cfg.description = ConfigYesNo(default=(config.movielist.description.value != MovieList.HIDE_DESCRIPTION))
		configList = [
			(_("Sort"), cfg.moviesort, _("You can set sorting type for items in movielist.")),
			(_("Show extended description"), cfg.description, _("You can enable if will be displayed extended EPG description for item.")),
			(_("Type"), cfg.listtype, _("Set movielist type.")),
			(_("Use alternative skin"), config.movielist.useslim, _("Use the alternative screen")),
			(_("Use individual settings for each directory"), config.movielist.settings_per_directory, _("Settings can be different for each directory separately (for non removeable devices only).")),
			(_("Allow quitting movie player with exit"), config.usage.leave_movieplayer_onExit, _("When enabled, it is possible to leave the movie player with exit.")),
			(_("Behavior when a movie reaches the end"), config.usage.on_movie_eof, _("Set action when movie playback is finished.")),
			(_("Stop service on return to movie list"), config.movielist.stop_service, _("If is enabled and movie playback is finished, then after return to movielist will not be automaticaly start service playback.")),
			(_("Load length of movies in movie list"), config.usage.load_length_of_movies_in_moviellist, _("Display movie length in movielist (except single line style).")),
			(_("Show status icons in movie list"), config.usage.show_icons_in_movielist, _("Set if You want see status icons, progress bars or nothing.")),
			(_("Show icon for new/unseen items"), config.usage.movielist_unseen, _("If enabled, then there will be displayed icons for new/unseen items too.")),
			(_("Play audiofiles in list mode"), config.movielist.play_audio_internal, _("If set as 'Yes', then audiofiles are played in 'list mode' only, instead in full screen player.")),
			(_("Root directory"), config.movielist.root, _("You can set selected directory as 'root' directory for movie player.")),
			(_("Hide known extensions"), config.movielist.hide_extensions, _("Do not show file extensions for registered multimedia files.")),
			(_("Automatic bookmarks"), config.movielist.add_bookmark, _("If enabled, bookmarks will be updated with the new location when you move or copy a recording.")),
			(_("Show underline characters in filenames"), config.movielist.show_underlines, _("If disabled, underline characters in file and directory names are not shown and are replaced with spaces.")),
			]
		for btn in ('red', 'green', 'yellow', 'blue', 'TV', 'Radio', 'Text', 'F1', 'F2', 'F3'):
			configList.append((_(btn), userDefinedButtons[btn]))
		ConfigListScreen.__init__(self, configList, session=session, on_change=self.changedEntry)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"red": self.cancel,
			"green": self.save,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
			"menu": self.cancel,
		}, -2)

		self["description"] = Label()

		# For compatibility with the Setup screen
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.onChangedEntry = []

	def save(self):
		self.saveAll()
		cfg = self.cfg
		config.movielist.moviesort.value = int(cfg.moviesort.value)
		config.movielist.listtype.value = int(cfg.listtype.value)
		if cfg.description.value:
			config.movielist.description.value = MovieList.SHOW_DESCRIPTION
		else:
			config.movielist.description.value = MovieList.HIDE_DESCRIPTION
		if not config.movielist.settings_per_directory.value:
			config.movielist.moviesort.save()
			config.movielist.listtype.save()
			config.movielist.description.save()
			config.movielist.useslim.save()
			config.usage.on_movie_eof.save()
		self.close(True)

	def cancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelCallback, MessageBox, _("Really close without saving settings?"))
		else:
			self.cancelCallback(True)

	def cancelCallback(self, answer):
		if answer:
			for x in self["config"].list:
				x[1].cancel()
			self.close(False)


class MovieContextMenuSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["selected"] = StaticText("")
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

	def __onShow(self):
		self.parent["menu"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def __onHide(self):
		self.parent["menu"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		item = self.parent["menu"].getCurrent()
		self["selected"].text = item[0][0]


from Screens.ParentalControlSetup import ProtectedScreen


class MovieContextMenu(Screen, ProtectedScreen):
	# Contract: On OK returns a callable object (e.g. delete)
	def __init__(self, session, csel, service):
		Screen.__init__(self, session)
		self.csel = csel
		ProtectedScreen.__init__(self)
		self.title = _("Movielist menu")

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions", "MenuActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick,
				"yellow": boundFunction(self.close, csel.showNetworkSetup),
				"menu": boundFunction(self.close, csel.configure),
				"1": boundFunction(self.close, csel.unhideParentalServices),
				"2": boundFunction(self.close, csel.do_rename),
				"5": boundFunction(self.close, csel.do_copy),
				"6": boundFunction(self.close, csel.do_move),
				"7": boundFunction(self.close, csel.do_createdir),
				"8": boundFunction(self.close, csel.do_delete),
			})

		def append_to_menu(menu, args, key="dummy"):
			menu.append(ChoiceEntryComponent(key, args))

		menu = []
		if service:
			if (service.flags & eServiceReference.mustDescent) and isTrashFolder(service):
				append_to_menu(menu, (_("Permanently remove all deleted items"), csel.purgeAll), key="8")
			else:
				append_to_menu(menu, (_("Delete"), csel.do_delete), key="8")
				append_to_menu(menu, (_("Move"), csel.do_move), key="6")
				append_to_menu(menu, (_("Rename"), csel.do_rename), key="2")
				if not (service.flags & eServiceReference.mustDescent):
					append_to_menu(menu, (_("Copy"), csel.do_copy), key="5")
					if self.isResetable():
						append_to_menu(menu, (_("Reset playback position"), csel.do_reset))
					if service.getPath().endswith('.ts'):
						append_to_menu(menu, (_("Start offline decode"), csel.do_decode))
				elif BlurayPlayer is None and csel.isBlurayFolderAndFile(service):
					append_to_menu(menu, (_("Auto play blu-ray file"), csel.playBlurayFile))
				if config.ParentalControl.servicepin[0].value and config.ParentalControl.servicepinactive.value and config.ParentalControl.hideBlacklist.value and config.ParentalControl.storeservicepin.value != "never":
					from Components.ParentalControl import parentalControl
					if not parentalControl.sessionPinCached:
						append_to_menu(menu, (_("Unhide parental control services"), csel.unhideParentalServices), key="1")
				# Plugins expect a valid selection, so only include them if we selected a non-dir
				if not (service.flags & eServiceReference.mustDescent):
					for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
						append_to_menu(menu, (p.description, boundFunction(p, session, service)), key="bullet")
		if csel.exist_bookmark():
			append_to_menu(menu, (_("Remove bookmark"), csel.do_addbookmark))
		else:
			append_to_menu(menu, (_("Add bookmark"), csel.do_addbookmark))
		append_to_menu(menu, (_("Create directory"), csel.do_createdir), key="7")
		append_to_menu(menu, (_("Sort by") + "...", csel.selectSortby))
		append_to_menu(menu, (_("On end of movie") + "...", csel.do_movieoff_menu))
		append_to_menu(menu, (_("Network") + "...", csel.showNetworkSetup), key="yellow")
		append_to_menu(menu, (_("Settings"), csel.configure), key="menu")

		self["menu"] = ChoiceList(menu)

	def isProtected(self):
		return self.csel.protectContextMenu and config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.context_menus.value

	def isResetable(self):
		item = self.csel.getCurrentSelection()
		return not (item[1] and moviePlayState(item[0].getPath() + ".cuts", item[0], item[1].getLength(item[0])) is None)

	def pinEntered(self, answer):
		if answer:
			self.csel.protectContextMenu = False
		ProtectedScreen.pinEntered(self, answer)

	def createSummary(self):
		return MovieContextMenuSummary

	def okbuttonClick(self):
		self.close(self["menu"].getCurrent()[0][1])

	def cancelClick(self):
		self.close(None)


class SelectionEventInfo:
	def __init__(self):
		self["Service"] = ServiceEvent()
		self.list.connectSelChanged(self.__selectionChanged)
		self.timer = eTimer()
		self.timer.callback.append(self.updateEventInfo)
		self.onShown.append(self.__selectionChanged)

	def __selectionChanged(self):
		if self.execing and self.settings["description"] == MovieList.SHOW_DESCRIPTION:
			self.timer.start(100, True)

	def updateEventInfo(self):
		serviceref = self.getCurrent()
		self["Service"].newService(serviceref)
		info = serviceref and eServiceCenter.getInstance().info(serviceref)
		if info:
			timeCreate =  strftime("%A %d %b %Y", localtime(info.getInfo(serviceref, iServiceInformation.sTimeCreate)))
			duration = "%d min" % (info.getLength(serviceref) / 60) 
			filesize = "%d MB" % (info.getInfoObject(serviceref, iServiceInformation.sFileSize) / (1024*1024))
			moviedetails = "%s  •  %s  •  %s" % (timeCreate, duration, filesize)
			self["moviedetails"].setText(moviedetails)


class MovieSelectionSummary(Screen):
	# Kludgy component to display current selection on LCD. Should use
	# parent.Service as source for everything, but that seems to have a
	# performance impact as the MovieSelection goes through hoops to prevent
	# this when the info is not selected
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["name"] = StaticText("")
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

	def __onShow(self):
		self.parent.list.connectSelChanged(self.selectionChanged)
		self.selectionChanged()

	def __onHide(self):
		self.parent.list.disconnectSelChanged(self.selectionChanged)

	def selectionChanged(self):
		item = self.parent.getCurrentSelection()
		if item and item[0]:
			data = item[3]
			if (data is not None) and (data != -1):
				name = data.txt
			elif not item[1]:
				# special case, one up
				name = ".."
			else:
				name = item[1].getName(item[0])
			if item[0].flags & eServiceReference.mustDescent:
				if len(name) > 12:
					name = os.path.split(os.path.normpath(name))[1]
				name = "> " + name
			self["name"].text = name
		else:
			self["name"].text = ""


class MovieSelection(Screen, HelpableScreen, SelectionEventInfo, InfoBarBase, ProtectedScreen):
	# SUSPEND_PAUSES actually means "please call my pauseService()"
	ALLOW_SUSPEND = Screen.SUSPEND_PAUSES

	def __init__(self, session, selectedmovie=None, timeshiftEnabled=False):
		Screen.__init__(self, session)

		if config.movielist.useslim.value:
			self.skinName = ["MovieSelectionSlim", "MovieSelection"]
		else:
			self.skinName = "MovieSelection"

		HelpableScreen.__init__(self)
		if not timeshiftEnabled:
			InfoBarBase.__init__(self) # For ServiceEventTracker
		ProtectedScreen.__init__(self)

		self.setTitle(_("Movie selection"))
		self.protectContextMenu = True
		self.initialRun = True

		self.tags = {}
		if selectedmovie:
			self.selected_tags = config.movielist.last_selected_tags.value
		else:
			self.selected_tags = None
		self.selected_tags_ele = None
		self.nextInBackground = None

		self.movemode = False
		self.bouquet_mark_edit = False

		self.feedbackTimer = None
		self.pathselectEnabled = False

		self.numericalTextInput = NumericalTextInput(mapping=MAP_SEARCH_UPCASE)
		self["chosenletter"] = Label("")
		self["chosenletter"].visible = False

		self["waitingtext"] = Label(_("Please wait... Loading list..."))
		self["moviedetails"] = Label()

		# create optional description border and hide immediately
		self["DescriptionBorder"] = Pixmap()
		self["DescriptionBorder"].hide()

		if config.ParentalControl.servicepinactive.value:
			from Components.ParentalControl import parentalControl
			if not parentalControl.sessionPinCached and config.movielist.last_videodir.value and [x for x in config.movielist.last_videodir.value[1:].split("/") if x.startswith(".") and not x.startswith(".Trash")]:
				config.movielist.last_videodir.value = ""
		if not os.path.isdir(config.movielist.last_videodir.value):
			config.movielist.last_videodir.value = defaultMoviePath()
			config.movielist.last_videodir.save()
		self.setCurrentRef(config.movielist.last_videodir.value)

		self.settings = {
			"listtype": config.movielist.listtype.value,
			"moviesort": config.movielist.moviesort.value,
			"description": config.movielist.description.value,
			"movieoff": config.usage.on_movie_eof.value
		}
		self.movieOff = self.settings["movieoff"]

		self["list"] = MovieList(None, list_type=self.settings["listtype"], sort_type=self.settings["moviesort"], descr_state=self.settings["description"])
		self.list = self["list"]
		self.selectedmovie = selectedmovie

		self.playGoTo = None #1 - preview next item / -1 - preview previous

		# Need list for init
		SelectionEventInfo.__init__(self)

		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		self["movie_off"] = MultiPixmap()
		self["movie_off"].hide()
		self["movie_sort"] = MultiPixmap()
		self["movie_sort"].hide()

		self["freeDiskSpace"] = self.diskinfo = DiskInfo(config.movielist.last_videodir.value, DiskInfo.FREE, update=False)

		self["NumberActions"] = NumberActionMap(["NumberActions", "InputAsciiActions"],
			{
				"gotAsciiCode": self.keyAsciiCode,
				"0": self.keyNumberGlobal,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal
			})

		self["playbackActions"] = HelpableActionMap(self, ["MoviePlayerActions"],
			{
				"moveNext": (self.playNext, _("Play next")),
				"movePrev": (self.playPrev, _("Play previous")),
				"channelUp": (self.moveToFirstOrFirstFile, _("Go to first movie or top of list")),
				"channelDown": (self.moveToLastOrFirstFile, _("Go to first movie or last item")),
			})
		self["MovieSelectionActions"] = HelpableActionMap(self, ["MovieSelectionActions"],
			{
				"contextMenu": (self.doContext, _("Menu")),
				"showEventInfo": (self.showEventInformation, _("Show event details")),
			})

		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions"],
			{
				"cancel": (self.abort, _("Exit movie list")),
				"ok": (self.itemSelected, _("Select movie")),
			})
		self["DirectionActions"] = HelpableActionMap(self, ["DirectionActions"],
			{
				"up": (self.keyUp, _("Go up the list")),
				"down": (self.keyDown, _("Go down the list"))
			}, prio=-2)

		def getinitUserDefinedActionsDescription(key):
			return _(userDefinedActions.get(eval("config.movielist.%s.value" % key), _("Not defined")))

		self["InfobarActions"] = HelpableActionMap(self, ["InfobarActions"],
			{
				"showMovies": (self.doPathSelect, _("Select the movie path")),
				"showRadio": (self.btn_radio, boundFunction(getinitUserDefinedActionsDescription, "btn_radio")),
				"showTv": (self.btn_tv, boundFunction(getinitUserDefinedActionsDescription, "btn_tv")),
				"toggleTvRadio": (self.btn_tv, boundFunction(getinitUserDefinedActionsDescription, "btn_tv")),
				"showText": (self.btn_text, boundFunction(getinitUserDefinedActionsDescription, "btn_text")),
			})
		self["ColorActions"] = HelpableActionMap(self, ["ColorActions"],
			{
				"red": (self.btn_red, boundFunction(getinitUserDefinedActionsDescription, "btn_red")),
				"green": (self.btn_green, boundFunction(getinitUserDefinedActionsDescription, "btn_green")),
				"yellow": (self.btn_yellow, boundFunction(getinitUserDefinedActionsDescription, "btn_yellow")),
				"blue": (self.btn_blue, boundFunction(getinitUserDefinedActionsDescription, "btn_blue")),
			})
		self["FunctionKeyActions"] = HelpableActionMap(self, ["FunctionKeyActions"],
			{
				"f1": (self.btn_F1, boundFunction(getinitUserDefinedActionsDescription, "btn_F1")),
				"f2": (self.btn_F2, boundFunction(getinitUserDefinedActionsDescription, "btn_F2")),
				"f3": (self.btn_F3, boundFunction(getinitUserDefinedActionsDescription, "btn_F3")),
			})

		tPreview = _("Preview")
		tFwd = _("skip forward") + " (" + tPreview + ")"
		tBack = _("skip backward") + " (" + tPreview + ")"
		sfwd = lambda: self.seekRelative(1, config.seek.selfdefined_46.value * 90000)
		ssfwd = lambda: self.seekRelative(1, config.seek.selfdefined_79.value * 90000)
		sback = lambda: self.seekRelative(-1, config.seek.selfdefined_46.value * 90000)
		ssback = lambda: self.seekRelative(-1, config.seek.selfdefined_79.value * 90000)
		self["SeekActions"] = HelpableActionMap(self, ["InfobarSeekActions"],
			{
				"playpauseService": (self.preview, _("Preview")),
				"unPauseService": (self.preview, _("Preview")),
				"seekFwd": (sfwd, tFwd),
				"seekFwdManual": (ssfwd, tFwd),
				"seekBack": (sback, tBack),
				"seekBackManual": (ssback, tBack),
			}, prio=5)
		self.onShown.append(self.onFirstTimeShown)
		self.onLayoutFinish.append(self.saveListsize)
		self.onClose.append(self.__onClose)
		NavigationInstance.instance.RecordTimer.on_state_change.append(self.list.updateRecordings)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				#iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evEOF: self.__evEOF,
				#iPlayableService.evSOF: self.__evSOF,
			})
		self.onExecBegin.append(self.asciiOn)
		config.misc.standbyCounter.addNotifier(self.standbyCountChanged, initial_call=False)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.movie_list.value

	def standbyCountChanged(self, value):
		path = self.getTitle().split(" /", 1)
		if path and len(path) > 1:
			if [x for x in path[1].split("/") if x.startswith(".") and not x.startswith(".Trash")]:
				moviepath = defaultMoviePath()
				if moviepath:
					config.movielist.last_videodir.value = defaultMoviePath()
					self.close(None)

	def unhideParentalServices(self):
		if self.protectContextMenu:
			self.session.openWithCallback(self.unhideParentalServicesCallback, PinInput, pinList=[config.ParentalControl.servicepin[0].value], triesEntry=config.ParentalControl.retries.servicepin, title=_("Enter the service PIN"), windowTitle=_("Enter PIN code"))
		else:
			self.unhideParentalServicesCallback(True)

	def unhideParentalServicesCallback(self, answer):
		if answer:
			from Components.ParentalControl import parentalControl
			parentalControl.setSessionPinCached()
			parentalControl.hideBlacklist()
			self.reloadList()
		elif answer is not None:
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code you entered is wrong."), MessageBox.TYPE_ERROR)

	def asciiOn(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def asciiOff(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)

	def initUserDefinedActions(self):
		global userDefinedButtons, userDefinedActions
		if userDefinedButtons is None:
			userDefinedActions = {
				'delete': _("Delete"),
				'move': _("Move"),
				'copy': _("Copy"),
				'reset': _("Reset"),
				'tags': _("Tags"),
				'addbookmark': _("Add bookmark"),
				'bookmarks': _("Location"),
				'rename': _("Rename"),
				'gohome': _("Home"),
				'sort': _("Sort"),
				'sortby': _("Sort by"),
				'listtype': _("List type"),
				'preview': _("Preview"),
				'movieoff': _("On end of movie"),
				'movieoff_menu': _("On end of movie (as menu)")
			}
			for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
				userDefinedActions['@' + p.name] = p.description
			locations = []
			buildMovieLocationList(locations)
			prefix = _("Goto") + ": "
			for d, p in locations:
				if p and p.startswith('/'):
					userDefinedActions[p] = prefix + d
			config.movielist.btn_red = ConfigSelection(default='delete', choices=userDefinedActions)
			config.movielist.btn_green = ConfigSelection(default='move', choices=userDefinedActions)
			config.movielist.btn_yellow = ConfigSelection(default='bookmarks', choices=userDefinedActions)
			config.movielist.btn_blue = ConfigSelection(default='sort', choices=userDefinedActions)
			config.movielist.btn_radio = ConfigSelection(default='tags', choices=userDefinedActions)
			config.movielist.btn_tv = ConfigSelection(default='gohome', choices=userDefinedActions)
			config.movielist.btn_text = ConfigSelection(default='movieoff', choices=userDefinedActions)
			config.movielist.btn_F1 = ConfigSelection(default='movieoff_menu', choices=userDefinedActions)
			config.movielist.btn_F2 = ConfigSelection(default='preview', choices=userDefinedActions)
			config.movielist.btn_F3 = ConfigSelection(default='/media', choices=userDefinedActions)
		userDefinedButtons = {
			'red': config.movielist.btn_red,
			'green': config.movielist.btn_green,
			'yellow': config.movielist.btn_yellow,
			'blue': config.movielist.btn_blue,
			'Radio': config.movielist.btn_radio,
			'TV': config.movielist.btn_tv,
			'TV2': config.movielist.btn_tv,
			'Text': config.movielist.btn_text,
			'F1': config.movielist.btn_F1,
			'F2': config.movielist.btn_F2,
			'F3': config.movielist.btn_F3
		}
		self.list.connectSelChanged(self.updateButtons)
		self._updateButtonTexts()

	def _callButton(self, name):
		if name.startswith('@'):
			item = self.getCurrentSelection()
			if isSimpleFile(item):
				name = name[1:]
				for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
					if name == p.name:
						p(self.session, item[0])
		elif name.startswith('/'):
			self.gotFilename(name)
		else:
			try:
				a = getattr(self, 'do_' + name)
			except Exception:
				# Undefined action
				return
			a()

	def btn_red(self):
		self._callButton(config.movielist.btn_red.value)

	def btn_green(self):
		self._callButton(config.movielist.btn_green.value)

	def btn_yellow(self):
		self._callButton(config.movielist.btn_yellow.value)

	def btn_blue(self):
		self._callButton(config.movielist.btn_blue.value)

	def btn_radio(self):
		self._callButton(config.movielist.btn_radio.value)

	def btn_tv(self):
		self._callButton(config.movielist.btn_tv.value)

	def btn_text(self):
		self._callButton(config.movielist.btn_text.value)

	def btn_F1(self):
		self._callButton(config.movielist.btn_F1.value)

	def btn_F2(self):
		self._callButton(config.movielist.btn_F2.value)

	def btn_F3(self):
		self._callButton(config.movielist.btn_F3.value)

	def keyUp(self):
		if self["list"].getCurrentIndex() < 1:
			self["list"].moveToLast()
		else:
			self["list"].moveUp()

	def keyDown(self):
		if self["list"].getCurrentIndex() == len(self["list"]) - 1:
			self["list"].moveToFirst()
		else:
			self["list"].moveDown()

	def moveToFirstOrFirstFile(self):
		if self.list.getCurrentIndex() <= self.list.firstFileEntry: #selection above or on first movie
			if self.list.getCurrentIndex() < 1:
				self.list.moveToLast()
			else:
				self.list.moveToFirst()
		else:
			self.list.moveToFirstMovie()

	def moveToLastOrFirstFile(self):
		if self.list.getCurrentIndex() >= self.list.firstFileEntry or self.list.firstFileEntry == len(self.list): #selection below or on first movie or no files
			if self.list.getCurrentIndex() == len(self.list) - 1:
				self.list.moveToFirst()
			else:
				self.list.moveToLast()
		else:
			self.list.moveToFirstMovie()

	def keyNumberGlobal(self, number):
		charstr = self.numericalTextInput.getKey(number)
		if len(charstr) == 1:
			self.list.moveToChar(charstr[0], self["chosenletter"])

	def keyAsciiCode(self):
		charstr = chr(getPrevAsciiCode())
		if len(charstr) == 1:
			self.list.moveToString(charstr[0], self["chosenletter"])

	def isItemPlayable(self, index):
		item = self.list.getItem(index)
		if item:
			path = item.getPath()
			if not item.flags & eServiceReference.mustDescent:
				ext = os.path.splitext(path)[1].lower()
				if ext in IMAGE_EXTENSIONS:
					return False
				else:
					return True
		return False

	def goToPlayingService(self):
		service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if service:
			path = service.getPath()
			if path:
				path = os.path.split(os.path.normpath(path))[0]
				if not path.endswith('/'):
					path += '/'
				self.gotFilename(path, selItem=service)
				return True
		return False

	def playNext(self):
		if self.list.playInBackground:
			if self.list.moveTo(self.list.playInBackground):
				if self.isItemPlayable(self.list.getCurrentIndex() + 1):
					self.list.moveDown()
					self.callLater(self.preview)
			else:
				self.playGoTo = 1
				self.goToPlayingService()
		else:
			self.preview()

	def playPrev(self):
		if self.list.playInBackground:
			if self.list.moveTo(self.list.playInBackground):
				if self.isItemPlayable(self.list.getCurrentIndex() - 1):
					self.list.moveUp()
					self.callLater(self.preview)
			else:
				self.playGoTo = -1
				self.goToPlayingService()

	def __onClose(self):
		config.misc.standbyCounter.removeNotifier(self.standbyCountChanged)
		try:
			NavigationInstance.instance.RecordTimer.on_state_change.remove(self.list.updateRecordings)
		except Exception as e:
			print("[ML] failed to unsubscribe:", e)
			pass

	def createSummary(self):
		return MovieSelectionSummary

	def updateDescription(self):
		if self.settings["description"] == MovieList.SHOW_DESCRIPTION:
			self["DescriptionBorder"].show()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight - self["DescriptionBorder"].instance.size().height()))
		else:
			self["Service"].newService(None)
			self["DescriptionBorder"].hide()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight))

	def pauseService(self):
		# Called when pressing Power button (go to standby)
		self.playbackStop()
		self.session.nav.stopService()

	def unPauseService(self):
		# When returning from standby. It might have been a while, so
		# reload the list.
		self.reloadList()

	def can_delete(self, item):
		if not item:
			return False
		return canDelete(item) or isTrashFolder(item[0])

	def can_move(self, item):
		return canMove(item)

	def can_default(self, item):
		# returns whether item is a regular file
		return isSimpleFile(item)

	def can_sort(self, item):
		return True

	def can_listtype(self, item):
		return True

	def can_preview(self, item):
		return isSimpleFile(item)

	def _updateButtonTexts(self):
		for k in ('red', 'green', 'yellow', 'blue'):
			btn = userDefinedButtons[k]
			self['key_' + k].setText(userDefinedActions[btn.value])

	def updateButtons(self):
		item = self.getCurrentSelection()
		for name in ('red', 'green', 'yellow', 'blue'):
			action = userDefinedButtons[name].value
			if action.startswith('@'):
				check = self.can_default
			elif action.startswith('/'):
				check = self.can_gohome
			else:
				try:
					check = getattr(self, 'can_' + action)
				except:
					check = self.can_default
			if check(item):
				if item and isTrashFolder(item[0]) and userDefinedButtons[name].value == 'delete':
					self['key_%s' % name].setText(_("Empty Trash"))
				elif userDefinedButtons[name].value != "sort":
					self['key_%s' % name].setText(userDefinedActions[userDefinedButtons[name].value])
			else:
				self["key_%s" % name].setText("")

	def showEventInformation(self):
		from Screens.EventView import EventViewSimple
		from ServiceReference import ServiceReference
		evt = self["list"].getCurrentEvent()
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))

	def saveListsize(self):
			listsize = self["list"].instance.size()
			self.listWidth = listsize.width()
			self.listHeight = listsize.height()
			self.updateDescription()

	def onFirstTimeShown(self):
		self.onShown.remove(self.onFirstTimeShown) # Just once, not after returning etc.
		self.show()
		self.reloadList(self.selectedmovie, home=True)
		del self.selectedmovie

	def getCurrent(self):
		# Returns selected serviceref (may be None)
		return self["list"].getCurrent()

	def getCurrentSelection(self):
		# Returns None or (serviceref, info, begin, len)
		return self["list"].l.getCurrentSelection()

	def playAsBLURAY(self, path):
		try:
			from Plugins.Extensions.BlurayPlayer import BlurayUi
			self.session.open(BlurayUi.BlurayMain, path)
			return True
		except Exception as e:
			print("[ML] Cannot open BlurayPlayer:", e)

	def playAsDVD(self, path):
		try:
			from Screens import DVD
			self.session.open(DVD.DVDPlayer, dvd_filelist=[path])
			return True
		except Exception as e:
			print("[ML] DVD Player not installed:", e)

	def playSuburi(self, path):
		suburi = os.path.splitext(path)[0][:-7]
		for ext in AUDIO_EXTENSIONS:
			if os.path.exists("%s%s" % (suburi, ext)):
				current = eServiceReference(4097, 0, "file://%s&suburi=file://%s%s" % (path, suburi, ext))
				self.close(current)
				return True

	def __serviceStarted(self):
		if not self.list.playInBackground:
			return
		ref = self.session.nav.getCurrentService()
		cue = ref.cueSheet()
		if not cue:
			return
		# disable writing the stop position
		cue.setCutListEnable(2)
		# find "resume" position
		cuts = cue.getCutList()
		if not cuts:
			return
		for (pts, what) in cuts:
			if what == 3:
				last = pts
				break
		else:
			# no resume, jump to start of program (first marker)
			last = cuts[0][0]
		self.doSeekTo = last
		self.callLater(self.doSeek)

	def doSeek(self, pts=None):
		if pts is None:
			pts = self.doSeekTo
		seekable = self.getSeek()
		if seekable is None:
			return
		seekable.seekTo(pts)

	def getSeek(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		seek = service.seek()
		if seek is None or not seek.isCurrentlySeekable():
			return None
		return seek

	def __evEOF(self):
		playInBackground = self.list.playInBackground
		if not playInBackground:
			print("Not playing anything in background")
			return
		self.session.nav.stopService()
		self.list.playInBackground = None
		if config.movielist.play_audio_internal.value:
			index = self.list.findService(playInBackground)
			if index is None:
				return # Not found?
			next = self.list.getItem(index + 1)
			if not next:
				return
			path = next.getPath()
			ext = os.path.splitext(path)[1].lower()
			print("Next up:", path)
			if ext in AUDIO_EXTENSIONS:
				self.nextInBackground = next
				self.callLater(self.preview)
				self["list"].moveToIndex(index + 1)

	def preview(self):
		current = self.getCurrent()
		if current is not None:
			path = current.getPath()
			if current.flags & eServiceReference.mustDescent:
				self.gotFilename(path)
			else:
				Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(self.previewCheckTimeshiftCallback)

	def startPreview(self):
		if self.nextInBackground is not None:
			current = self.nextInBackground
			self.nextInBackground = None
		else:
			current = self.getCurrent()
		playInBackground = self.list.playInBackground
		if playInBackground:
			self.list.playInBackground = None
			self.session.nav.stopService()
			if playInBackground != current:
				# come back to play the new one
				self.callLater(self.preview)
		else:
			self.list.playInBackground = current
			self.session.nav.playService(current)

	def previewCheckTimeshiftCallback(self, answer):
		if answer:
			self.startPreview()

	def seekRelative(self, direction, amount):
		if self.list.playInBackground:
			seekable = self.getSeek()
			if seekable is None:
				return
			seekable.seekRelative(direction, amount)

	def playbackStop(self):
		if self.list.playInBackground:
			self.list.playInBackground = None
			self.session.nav.stopService()

	def itemSelected(self, answer=True):
		current = self.getCurrent()
		if current is not None:
			path = current.getPath()
			if current.flags & eServiceReference.mustDescent:
				if BlurayPlayer is not None and os.path.isdir(os.path.join(path, 'BDMV/STREAM/')):
					#force a BLU-RAY extention
					Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.itemSelectedCheckTimeshiftCallback, 'bluray', path))
					return
				if os.path.isdir(os.path.join(path, 'VIDEO_TS/')) or os.path.exists(os.path.join(path, 'VIDEO_TS.IFO')):
					#force a DVD extention
					Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.itemSelectedCheckTimeshiftCallback, '.img', path))
					return
				self.gotFilename(path)
			else:
				ext = os.path.splitext(path)[1].lower()
				if config.movielist.play_audio_internal.value and (ext in AUDIO_EXTENSIONS):
					self.preview()
					return
				if self.list.playInBackground:
					# Stop preview, come back later
					self.session.nav.stopService()
					self.list.playInBackground = None
					self.callLater(self.itemSelected)
					return
				if ext in IMAGE_EXTENSIONS:
					try:
						from Plugins.Extensions.PicturePlayer import ui
						# Build the list for the PicturePlayer UI
						filelist = []
						index = 0
						for item in self.list.list:
							p = item[0].getPath()
							if p == path:
								index = len(filelist)
							if os.path.splitext(p)[1].lower() in IMAGE_EXTENSIONS:
								filelist.append(((p, False), None))
						self.session.open(ui.Pic_Full_View, filelist, index, path)
					except Exception as ex:
						print("[ML] Cannot display", str(ex))
					return
				Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(boundFunction(self.itemSelectedCheckTimeshiftCallback, ext, path))

	def itemSelectedCheckTimeshiftCallback(self, ext, path, answer):
		if answer:
			if ext in (".iso", ".img", ".nrg") and BlurayPlayer is not None:
				try:
					from Plugins.Extensions.BlurayPlayer import blurayinfo
					if blurayinfo.isBluray(path) == 1:
						ext = 'bluray'
				except Exception as e:
					print("[ML] Error in blurayinfo:", e)
			if ext == 'bluray':
				if self.playAsBLURAY(path):
					return
			elif ext in DVD_EXTENSIONS:
				if self.playAsDVD(path):
					return
			elif "_suburi." in path:
				if self.playSuburi(path):
					return
			self.movieSelected()

	# Note: DVDBurn overrides this method, hence the itemSelected indirection.
	def movieSelected(self):
		current = self.getCurrent()
		if current is not None:
			self.saveconfig()
			self.close(current)

	def doContext(self):
		current = self.getCurrent()
		if current is not None:
			self.session.openWithCallback(self.doneContext, MovieContextMenu, self, current)

	def doneContext(self, action):
		if action is not None:
			action()

	def saveLocalSettings(self):
		if config.movielist.settings_per_directory.value:
			try:
				path = os.path.join(config.movielist.last_videodir.value, ".e2settings.pkl")
				pickle.dump(self.settings, open(path, "wb"))
			except Exception as e:
				print("Failed to save settings to %s: %s" % (path, e))
		# Also set config items, in case the user has a read-only disk
		config.movielist.moviesort.value = self.settings["moviesort"]
		config.movielist.listtype.value = self.settings["listtype"]
		config.movielist.description.value = self.settings["description"]
		config.usage.on_movie_eof.value = self.settings["movieoff"]
		# save moviesort and movieeof values for using by hotkeys
		config.movielist.moviesort.save()
		config.usage.on_movie_eof.save()

	def loadLocalSettings(self):
		'Load settings, called when entering a directory'
		if config.movielist.settings_per_directory.value:
			try:
				path = os.path.join(config.movielist.last_videodir.value, ".e2settings.pkl")
				updates = pickle.load(open(path, "rb"))
				self.applyConfigSettings(updates)
			except IOError as e:
				updates = {
					"listtype": config.movielist.listtype.default,
					"moviesort": config.movielist.moviesort.default,
					"description": config.movielist.description.default,
					"movieoff": config.usage.on_movie_eof.default
				}
				self.applyConfigSettings(updates)
				pass # ignore fail to open errors
			except Exception as e:
				print("Failed to load settings from %s: %s" % (path, e))
		else:
			updates = {
				"listtype": config.movielist.listtype.value,
				"moviesort": config.movielist.moviesort.value,
				"description": config.movielist.description.value,
				"movieoff": config.usage.on_movie_eof.value
				}
			self.applyConfigSettings(updates)

	def applyConfigSettings(self, updates):
		needUpdate = ("description" in updates) and (updates["description"] != self.settings["description"])
		self.settings.update(updates)
		if needUpdate:
			self["list"].setDescriptionState(self.settings["description"])
			self.updateDescription()
		if self.settings["listtype"] != self["list"].list_type:
			self["list"].setListType(self.settings["listtype"])
			needUpdate = True
		if self.settings["moviesort"] != self["list"].sort_type:
			self["list"].setSortType(self.settings["moviesort"])
			needUpdate = True
		if self.settings["movieoff"] != self.movieOff:
			self.movieOff = self.settings["movieoff"]
			needUpdate = True
		config.movielist.moviesort.value = self.settings["moviesort"]
		config.movielist.listtype.value = self.settings["listtype"]
		config.movielist.description.value = self.settings["description"]
		config.usage.on_movie_eof.value = self.settings["movieoff"]
		return needUpdate

	def sortBy(self, newType):
		self.settings["moviesort"] = newType
		self.saveLocalSettings()
		self.setSortType(newType)
		self.reloadList()

	def listType(self, newType):
		self.settings["listtype"] = newType
		self.saveLocalSettings()
		self.setListType(newType)
		self.reloadList()

	def showDescription(self, newType):
		self.settings["description"] = newType
		self.saveLocalSettings()
		self.setDescriptionState(newType)
		self.updateDescription()

	def abort(self):
		global playlist
		del playlist[:]
		if self.list.playInBackground:
			self.list.playInBackground = None
			self.session.nav.stopService()
			self.callLater(self.abort)
			return
		self.saveconfig()
		self.close(None)

	def saveconfig(self):
		config.movielist.last_selected_tags.value = self.selected_tags

	def configure(self):
		self.session.openWithCallback(self.configureDone, MovieBrowserConfiguration)

	def configureDone(self, result):
		if result:
			self.applyConfigSettings({
				"listtype": config.movielist.listtype.value,
				"moviesort": config.movielist.moviesort.value,
				"description": config.movielist.description.value,
				"movieoff": config.usage.on_movie_eof.value})
			self.saveLocalSettings()
			self._updateButtonTexts()
			self.reloadList()

	def can_sortby(self, item):
		return True

	def do_sortby(self):
		self.selectSortby()

	def selectSortby(self):
		menu = []
		index = 0
		used = 0
		for x in l_moviesort:
			if int(x[0]) == int(config.movielist.moviesort.value):
				used = index
			menu.append((x[1], x[0]))
			index += 1
		self.session.openWithCallback(self.sortbyMenuCallback, ChoiceBox, title=_("Sort list:"), list=menu, selection=used, skin_name="SortbyChoiceBox")

	def sortbyMenuCallback(self, choice):
		if choice is None:
			return
		self.sortBy(int(choice[1]))
		self["movie_sort"].setPixmapNum(int(choice[1]) - 1)

	def getTagDescription(self, tag):
		# TODO: access the tag database
		return tag

	def updateTags(self):
		# get a list of tags available in this list
		self.tags = self["list"].tags

	def setListType(self, type):
		self["list"].setListType(type)

	def setDescriptionState(self, val):
		self["list"].setDescriptionState(val)

	def setSortType(self, type):
		self["list"].setSortType(type)

	def setCurrentRef(self, path):
		self.current_ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + path.replace(':', '%3a'))
		# Magic: this sets extra things to show
		self.current_ref.setName('16384:jpg 16384:jpeg 16384:png 16384:gif 16384:bmp 16384:svg')

	def reloadList(self, sel=None, home=False):
		self.reload_sel = sel
		self.reload_home = home
		self["waitingtext"].visible = True
		self.pathselectEnabled = False
		self.callLater(self.reloadWithDelay)

	def reloadWithDelay(self):
		if self.initialRun:
			self.loadLocalSettings()
		if not os.path.isdir(config.movielist.last_videodir.value):
			path = defaultMoviePath()
			config.movielist.last_videodir.value = path
			config.movielist.last_videodir.save()
			self.setCurrentRef(path)
			self["freeDiskSpace"].path = path
		if self.reload_sel is None:
			self.reload_sel = self.getCurrent()
		self["list"].reload(self.current_ref, self.selected_tags)
		self.updateTags()
		title = _("Recorded files...")
		if config.usage.setup_level.index >= 2: # expert+
			title += "  " + config.movielist.last_videodir.value
		if self.selected_tags:
			title += " - " + ','.join(self.selected_tags)
		self.setTitle(title)
		
		self.displayMovieOffStatus()
		self.displaySortStatus()
		if not (self.reload_sel and self["list"].moveTo(self.reload_sel)):
			if self.reload_home:
				self["list"].moveToFirstMovie()
		self["freeDiskSpace"].update()
		self["waitingtext"].visible = False
		self.createPlaylist()
		if self.playGoTo:
			if self.isItemPlayable(self.list.getCurrentIndex() + 1):
				if self.playGoTo > 0:
					self.list.moveDown()
				else:
					self.list.moveUp()
				self.playGoTo = None
				self.callLater(self.preview)
		self.callLater(self.enablePathSelect)

	def enablePathSelect(self):
		self.pathselectEnabled = True
		if self.initialRun:
			self.callLater(self.initUserDefinedActions)
			self.initialRun = False

	def doPathSelect(self):
		if self.pathselectEnabled:
			self.session.openWithCallback(
				self.gotFilename,
				MovieLocationBox,
				_("Please select the movie path..."),
				config.movielist.last_videodir.value
			)

	def gotFilename(self, res, selItem=None, checkParentControl=True):
		def servicePinEntered(res, selItem, result):
			if result:
				from Components.ParentalControl import parentalControl
				parentalControl.setSessionPinCached()
				parentalControl.hideBlacklist()
				self.gotFilename(res, selItem, checkParentControl=False)
			elif result == False:
				self.session.open(MessageBox, _("The PIN code you entered is wrong."), MessageBox.TYPE_INFO, timeout=5)
		if not res:
			return
		# serviceref must end with /
		if not res.endswith('/'):
			res += '/'
		currentDir = config.movielist.last_videodir.value
		if res != currentDir:
			if os.path.isdir(res):
				baseName = os.path.basename(res[:-1])
				if checkParentControl and config.ParentalControl.servicepinactive.value and baseName.startswith(".") and not baseName.startswith(".Trash"):
					from Components.ParentalControl import parentalControl
					if not parentalControl.sessionPinCached:
						self.session.openWithCallback(boundFunction(servicePinEntered, res, selItem), PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the correct PIN code"), windowTitle=_("Enter PIN code"))
						return
				config.movielist.last_videodir.value = res
				config.movielist.last_videodir.save()
				self.loadLocalSettings()
				self.setCurrentRef(res)
				self["freeDiskSpace"].path = res
				if selItem:
					self.reloadList(home=True, sel=selItem)
				else:
					self.reloadList(home=True, sel=eServiceReference("2:0:1:0:0:0:0:0:0:0:" + currentDir.replace(':', '%3a')))
			else:
				self.session.open(MessageBox, _("Directory %s does not exist.") % (res), type=MessageBox.TYPE_ERROR, timeout=5)

	def showAll(self):
		self.selected_tags_ele = None
		self.selected_tags = None
		self.reloadList(home=True)

	def showTagsN(self, tagele):
		if not self.tags:
			self.showTagWarning()
		elif not tagele or (self.selected_tags and tagele.value in self.selected_tags) or not tagele.value in self.tags:
			self.showTagsMenu(tagele)
		else:
			self.selected_tags_ele = tagele
			self.selected_tags = self.tags[tagele.value]
			self.reloadList(home=True)

	def showTagsFirst(self):
		self.showTagsN(config.movielist.first_tags)

	def showTagsSecond(self):
		self.showTagsN(config.movielist.second_tags)

	def can_tags(self, item):
		return self.tags

	def do_tags(self):
		self.showTagsN(None)

	def tagChosen(self, tag):
		if tag is not None:
			if tag[1] is None: # all
				self.showAll()
				return
			# TODO: Some error checking maybe, don't wanna crash on KeyError
			self.selected_tags = self.tags[tag[0]]
			if self.selected_tags_ele:
				self.selected_tags_ele.value = tag[0]
				self.selected_tags_ele.save()
			self.reloadList(home=True)

	def showTagsMenu(self, tagele):
		self.selected_tags_ele = tagele
		lst = [(_("show all tags"), None)] + [(tag, self.getTagDescription(tag)) for tag in sorted(self.tags)]
		self.session.openWithCallback(self.tagChosen, ChoiceBox, title=_("Please select tag to filter..."), list=lst)

	def showTagWarning(self):
		self.session.open(MessageBox, _("No tags are set on these movies."), MessageBox.TYPE_ERROR)

	def selectMovieLocation(self, title, callback):
		bookmarks = [("(" + _("Other") + "...)", None)]
		buildMovieLocationList(bookmarks)
		self.onMovieSelected = callback
		self.movieSelectTitle = title
		self.session.openWithCallback(self.gotMovieLocation, ChoiceBox, title=title, list=bookmarks)

	def gotMovieLocation(self, choice):
		if not choice:
			# cancelled
			self.onMovieSelected(None)
			del self.onMovieSelected
			return
		if isinstance(choice, tuple):
			if choice[1] is None:
				# Display full browser, which returns string
				self.session.openWithCallback(
					self.gotMovieLocation,
					MovieLocationBox,
					self.movieSelectTitle,
					config.movielist.last_videodir.value
				)
				return
			choice = choice[1]
		choice = os.path.normpath(choice)
		self.rememberMovieLocation(choice)
		self.onMovieSelected(choice)
		del self.onMovieSelected

	def rememberMovieLocation(self, where):
		if where in last_selected_dest:
			last_selected_dest.remove(where)
		last_selected_dest.insert(0, where)
		if len(last_selected_dest) > 5:
			del last_selected_dest[-1]

	def playBlurayFile(self):
		if self.playfile:
			Screens.InfoBar.InfoBar.instance.checkTimeshiftRunning(self.autoBlurayCheckTimeshiftCallback)

	def autoBlurayCheckTimeshiftCallback(self, answer):
		if answer:
			playRef = eServiceReference(3, 0, self.playfile)
			self.playfile = ""
			self.close(playRef)

	def isBlurayFolderAndFile(self, service):
		self.playfile = ""
		folder = os.path.join(service.getPath(), "STREAM/")
		if "BDMV/STREAM/" not in folder:
			folder = folder[:-7] + "BDMV/STREAM/"
		if os.path.isdir(folder):
			fileSize = 0
			for name in os.listdir(folder):
				try:
					if name.endswith(".m2ts"):
						size = os.stat(folder + name).st_size
						if size > fileSize:
							fileSize = size
							self.playfile = folder + name
				except:
					print("[ML] Error calculate size for %s" % (folder + name))
			if self.playfile:
				return True
		return False

	def can_bookmarks(self, item):
		return True

	def do_bookmarks(self):
		self.selectMovieLocation(title=_("Please select the movie path..."), callback=self.gotFilename)

	def can_addbookmark(self, item):
		return True

	def exist_bookmark(self):
		path = config.movielist.last_videodir.value
		if path in config.movielist.videodirs.value:
			return True
		return False

	def do_addbookmark(self):
		path = config.movielist.last_videodir.value
		if path in config.movielist.videodirs.value:
			if len(path) > 40:
				path = '...' + path[-40:]
			self.session.openWithCallback(self.removeBookmark, MessageBox, _("Do you really want to remove your bookmark of %s?") % path)
		else:
			config.movielist.videodirs.value += [path]
			config.movielist.videodirs.save()

	def removeBookmark(self, yes):
		if not yes:
			return
		path = config.movielist.last_videodir.value
		bookmarks = config.movielist.videodirs.value
		bookmarks.remove(path)
		config.movielist.videodirs.value = bookmarks
		config.movielist.videodirs.save()

	def can_createdir(self, item):
		return True

	def do_createdir(self):
		self.session.openWithCallback(self.createDirCallback, VirtualKeyBoard,
			title=_("Please enter name of the new directory"),
			text="")

	def createDirCallback(self, name):
		if not name:
			return
		msg = None
		try:
			path = os.path.join(config.movielist.last_videodir.value, name)
			os.mkdir(path)
			if not path.endswith('/'):
				path += '/'
			self.reloadList(sel=eServiceReference("2:0:1:0:0:0:0:0:0:0:" + path))
		except OSError as e:
			print("Error %s:" % e.errno, e)
			if e.errno == 17:
				msg = _("The path %s already exists.") % name
			else:
				msg = _("Error") + '\n' + str(e)
		except Exception as e:
			print("[ML] Unexpected error:", e)
			msg = _("Error") + '\n' + str(e)
		if msg:
			self.session.open(MessageBox, msg, type=MessageBox.TYPE_ERROR, timeout=5)

	def can_rename(self, item):
		return canMove(item)

	def do_rename(self):
		item = self.getCurrentSelection()
		if not canMove(item):
			return
		self.extension = ""
		if isFolder(item):
			p = os.path.split(item[0].getPath())
			if not p[1]:
				# if path ends in '/', p is blank.
				p = os.path.split(p[0])
			name = p[1]
		else:
			info = item[1]
			name = info.getName(item[0])
			full_name = os.path.split(item[0].getPath())[1]
			if full_name == name: # split extensions for files without metafile
				name, self.extension = os.path.splitext(name)

		self.session.openWithCallback(self.renameCallback, VirtualKeyBoard,
			title=_("Rename"),
			text=name)

	def do_decode(self):
		from ServiceReference import ServiceReference
		item = self.getCurrentSelection()
		info = item[1]
		filepath = item[0].getPath()
		if not filepath.endswith('.ts'):
			return
		serviceref = ServiceReference(None, reftype=eServiceReference.idDVB, path=filepath)
		name = info.getName(item[0]) + ' - decoded'
		description = info.getInfoString(item[0], iServiceInformation.sDescription)
		begin = int(time.time())
		recording = RecordTimer.RecordTimerEntry(serviceref, begin, begin + 3600, name, description, 0, dirname=preferredTimerPath())
		recording.dontSave = True
		recording.autoincrease = True
		recording.setAutoincreaseEnd()
		new_eit_name = recording.calculateFilename(name)
		self.session.nav.RecordTimer.record(recording, ignoreTSC=True)
		self.copy_eit_file(filepath[:-3] + ".eit", new_eit_name + ".eit")

	def copy_eit_file(self, original_eit, new_eit):
		if os.path.isfile(original_eit):
			from shutil import copy2
			copy2(original_eit, new_eit)

	def renameCallback(self, newname):
		if not newname:
			return
		item = self.getCurrentSelection()
		newbasename = newname.strip()
		if item and item[0]:
			try:
				oldfilename = item[0].getPath().rstrip('/')
				meta = oldfilename + '.meta'
				if os.path.isfile(meta):
					# if .meta file is present don't rename files. Only set new name in .meta
					name = "".join((newbasename, self.extension))
					metafile = open(meta, "r+")
					sid = metafile.readline()
					oldtitle = metafile.readline()
					rest = metafile.read()
					metafile.seek(0)
					metafile.write("%s%s\n%s" % (sid, name, rest))
					metafile.truncate()
					metafile.close()
					index = self.list.getCurrentIndex()
					info = self.list.list[index]
					if hasattr(info[3], 'txt'):
						info[3].txt = name
					else:
						self.list.invalidateCurrentItem()
					return
				# rename all files
				msg = None
				path, filename = os.path.split(oldfilename)
				if item[0].flags & eServiceReference.mustDescent: # directory
					newfilename = os.path.join(path, newbasename)
					print("[ML] rename dir", oldfilename, "to", newfilename)
					os.rename(oldfilename, newfilename)
				else:
					if oldfilename.endswith(self.extension):
						oldbasename = oldfilename[:-len(self.extension)]
					renamelist = []
					dont_rename = False
					for ext in ('.eit', self.extension + '.cuts', self.extension):
						newfilename = os.path.join(path, newbasename) + ext
						oldfilename = os.path.join(path, oldbasename) + ext
						if not os.path.isfile(oldfilename): # .eit and .cuts maybe not present
							continue
						if not os.path.isfile(newfilename):
							renamelist.append((oldfilename, newfilename))
						else:
							msg = _("The path %s already exists.") % newname
							dont_rename = True
							break
					if not dont_rename:
						for r in renamelist:
							print("[ML] rename", r[0], "to", r[1])
							os.rename(r[0], r[1])
				self.reloadList(sel=eServiceReference("2:0:1:0:0:0:0:0:0:0:" + newfilename))
			except OSError as e:
				print("Error %s:" % e.errno, e)
				msg = _("Error") + '\n' + str(e)
			except Exception as e:
				import traceback
				print("[ML] Unexpected error:", e)
				traceback.print_exc()
				msg = _("Error") + '\n' + str(e)
			if msg:
				self.session.open(MessageBox, msg, type=MessageBox.TYPE_ERROR, timeout=5)

	def do_reset(self):
		current = self.getCurrent()
		if current:
			resetMoviePlayState(current.getPath() + ".cuts", current)
			self["list"].invalidateCurrentItem()
			idx = self["list"].getCurrentIndex()
			self["list"].moveToIndex(idx - 1)
			self["list"].moveToIndex(idx)

	def do_move(self):
		item = self.getCurrentSelection()
		if canMove(item):
			current = item[0]
			info = item[1]
			if info is None:
				# Special case
				return
			name = info and info.getName(current) or _("this recording")
			path = os.path.normpath(current.getPath())
			# show a more limited list of destinations, no point
			# in showing mountpoints.
			title = _("Select destination for:") + " " + name
			bookmarks = [("(" + _("Other") + "...)", None)]
			inlist = []
			# Subdirs
			try:
				base = os.path.split(path)[0]
				for fn in os.listdir(base):
					if not fn.startswith('.'): # Skip hidden things
						d = os.path.join(base, fn)
						if os.path.isdir(d) and (d not in inlist):
							bookmarks.append((fn, d))
							inlist.append(d)
			except Exception as e:
				print("[MovieSelection]", e)
			# Last favourites
			for d in last_selected_dest:
				if d not in inlist:
					bookmarks.append((d, d))
			# Other favourites
			for d in config.movielist.videodirs.value:
				d = os.path.normpath(d)
				bookmarks.append((d, d))
				inlist.append(d)
			for p in Components.Harddisk.harddiskmanager.getMountedPartitions():
				d = os.path.normpath(p.mountpoint)
				if d not in inlist:
					bookmarks.append((p.description, d))
					inlist.append(d)
			self.onMovieSelected = self.gotMoveMovieDest
			self.movieSelectTitle = title
			self.session.openWithCallback(self.gotMovieLocation, ChoiceBox, title=title, list=bookmarks)

	def gotMoveMovieDest(self, choice):
		if not choice:
			return
		dest = os.path.normpath(choice)
		try:
			item = self.getCurrentSelection()
			current = item[0]
			if item[1] is None:
				name = None
			else:
				name = item[1].getName(current)
			moveServiceFiles(current, dest, name)
			self["list"].removeService(current)
		except Exception as e:
			self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)

	def can_copy(self, item):
		return canCopy(item)

	def do_copy(self):
		item = self.getCurrentSelection()
		if canMove(item):
			current = item[0]
			info = item[1]
			if info is None:
				# Special case
				return
			name = info and info.getName(current) or _("this recording")
			self.selectMovieLocation(title=_("Select copy destination for:") + " " + name, callback=self.gotCopyMovieDest)

	def gotCopyMovieDest(self, choice):
		if not choice:
			return
		dest = os.path.normpath(choice)
		try:
			item = self.getCurrentSelection()
			current = item[0]
			if item[1] is None:
				name = None
			else:
				name = item[1].getName(current)
			copyServiceFiles(current, dest, name)
		except Exception as e:
			self.session.open(MessageBox, str(e), MessageBox.TYPE_ERROR)

	def stopTimer(self, timer):
		if timer.isRunning():
			if timer.repeated:
				if not timer.disabled:
					timer.enable()
				timer.processRepeated(findRunningEvent=False)
				self.session.nav.RecordTimer.doActivate(timer)
			else:
				timer.afterEvent = RecordTimer.AFTEREVENT.NONE
				NavigationInstance.instance.RecordTimer.removeEntry(timer)

	def onTimerChoice(self, choice):
		if isinstance(choice, tuple) and choice[1]:
			choice, timer = choice[1]
			if not choice:
				# cancel
				return
			if "s" in choice:
				self.stopTimer(timer)
			if "d" in choice:
				self.delete(True)

	def do_delete(self):
		self.delete()

	def delete(self, *args):
		if args and (not args[0]):
			# cancelled by user (passing any arg means it's a dialog return)
			return
		item = self.getCurrentSelection()
		if not canDelete(item):
			if item and isTrashFolder(item[0]):
				# Red button to empty trashcan...
				self.purgeAll()
			return
		current = item[0]
		info = item[1]
		cur_path = os.path.realpath(current.getPath())
		try:
			st = os.stat(cur_path)
		except OSError as e:
			msg = _("Cannot move to trash can") + "\n" + str(e) + "\n"
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
			return
		name = info and info.getName(current) or _("this recording")
		are_you_sure = _("Do you really want to delete %s?") % (name)
		if current.flags & eServiceReference.mustDescent:
			files = 0
			subdirs = 0
			if args:
				# already confirmed...
				# but not implemented yet...
				msg = ''
				if config.usage.movielist_trashcan.value:
					try:
						# Move the files to the trash can in a way that their CTIME is
						# set to "now". A simple move would not correctly update the
						# ctime, and hence trigger a very early purge.
						trash = Tools.Trashcan.createTrashFolder(cur_path)
						trash = os.path.join(trash, os.path.split(cur_path)[1])
						os.mkdir(trash)
						for root, dirnames, filenames in os.walk(cur_path):
							trashroot = os.path.join(trash, root[len(cur_path) + 1:])
							for fn in filenames:
								print("Move %s -> %s" % (os.path.join(root, fn), os.path.join(trashroot, fn)))
								os.rename(os.path.join(root, fn), os.path.join(trashroot, fn))
							for dn in dirnames:
								print("MkDir", os.path.join(trashroot, dn))
								os.mkdir(os.path.join(trashroot, dn))
						# second pass to remove the empty directories
						for root, dirnames, filenames in os.walk(cur_path, topdown=False):
							for dn in dirnames:
								print("rmdir", os.path.join(trashroot, dn))
								os.rmdir(os.path.join(root, dn))
						os.rmdir(cur_path)
						self["list"].removeService(current)
						self.showActionFeedback(_("Deleted") + " " + name)
						# Files were moved to .Trash, ok.
						return
					except OSError as e:
						print("[MovieSelection] Cannot move to trash", e)
						if e.errno == 18:
							# This occurs when moving across devices
							msg = _("Cannot move files on a different disk or system to the trash can") + ". "
						else:
							msg = _("Cannot move to trash can") + ".\n" + str(e) + "\n"
					except Exception as e:
						print("[MovieSelection] Weird error moving to trash", e)
						# Failed to create trash or move files.
						msg = _("Cannot move to trash can") + "\n" + str(e) + "\n"
				msg += _("Sorry, deleting directories can (for now) only be done through the trash can.")
				self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
				return
			for fn in os.listdir(cur_path):
				if (fn != '.') and (fn != '..'):
					ffn = os.path.join(cur_path, fn)
					if os.path.isdir(ffn):
						subdirs += 1
					else:
						files += 1
			if files or subdirs:
				msg = _("Directory contains %(file)s and %(subdir)s.") % {"file": ngettext("%d file", "%d files", files) % files, "subdir": ngettext("%d subdirectory", "%d subdirectories", subdirs) % subdirs} + '\n' + are_you_sure
				if isInTrashFolder(current):
					# Red button to empty trashcan item or subdir
					msg = _("Deleted items") + "\n" + msg
					callback = self.purgeConfirmed
				else:
					callback = self.delete
				self.session.openWithCallback(callback, MessageBox, msg)
				return
			else:
				try:
					os.rmdir(cur_path)
				except Exception as e:
					print("[MovieSelection] Failed delete", e)
					self.session.open(MessageBox, _("Delete failed!") + "\n" + str(e), MessageBox.TYPE_ERROR)
				else:
					self["list"].removeService(current)
					self.showActionFeedback(_("Deleted") + " " + name)
		else:
			if not args:
				rec_filename = os.path.split(current.getPath())[1]
				if rec_filename.endswith(".ts"):
					rec_filename = rec_filename[:-3]
				if rec_filename.endswith(".stream"):
					rec_filename = rec_filename[:-7]
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if timer.isRunning() and not timer.justplay and os.path.split(timer.Filename)[1] in rec_filename:
						choices = [
							(_("Cancel"), None),
							(_("Stop recording"), ("s", timer)),
							(_("Stop recording and delete"), ("sd", timer))]
						self.session.openWithCallback(self.onTimerChoice, ChoiceBox, title=_("Recording in progress") + ":\n%s" % name, list=choices)
						return
				if time.time() - st.st_mtime < 5:
					if not args:
						self.session.openWithCallback(self.delete, MessageBox, _("File appears to be busy.\n") + are_you_sure)
						return
			if config.usage.movielist_trashcan.value:
				try:
					trash = Tools.Trashcan.createTrashFolder(cur_path)
					# Also check whether we're INSIDE the trash, then it's a purge.
					if cur_path.startswith(trash):
						msg = _("Deleted items") + "\n"
					else:
						moveServiceFiles(current, trash, name, allowCopy=False)
						self["list"].removeService(current)
						# Files were moved to .Trash, ok.
						from Screens.InfoBarGenerics import delResumePoint
						delResumePoint(current)
						self.showActionFeedback(_("Deleted") + " " + name)
						return
				except OSError as e:
					print("[MovieSelection] Cannot move to trash", e)
					if e.errno == 18:
						# This occurs when moving across devices
						msg = _("Cannot move files on a different disk or system to the trash can") + ". "
					else:
						msg = _("Cannot move to trash can") + ".\n" + str(e) + "\n"
				except Exception as e:
					print("[MovieSelection] Weird error moving to trash", e)
					# Failed to create trash or move files.
					msg = _("Cannot move to trash can") + "\n" + str(e) + "\n"
			else:
				msg = ''
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, msg + are_you_sure)

	def deleteConfirmed(self, confirmed):
		if not confirmed:
			return
		item = self.getCurrentSelection()
		if item is None:
			return # huh?
		current = item[0]
		info = item[1]
		name = info and info.getName(current) or _("this recording")
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(current)
		try:
			if offline is None:
				from enigma import eBackgroundFileEraser
				eBackgroundFileEraser.getInstance().erase(os.path.realpath(current.getPath()))
			else:
				if offline.deleteFromDisk(0):
					raise Exception("Offline delete failed")
			self["list"].removeService(current)
			from Screens.InfoBarGenerics import delResumePoint
			delResumePoint(current)
			self.showActionFeedback(_("Deleted") + " " + name)
		except Exception as ex:
			self.session.open(MessageBox, _("Delete failed!") + "\n" + name + "\n" + str(ex), MessageBox.TYPE_ERROR)

	def purgeAll(self):
		recordings = self.session.nav.getRecordings()
		next_rec_time = -1
		msg = _("Permanently delete all recordings in the trash can?")
		if not recordings:
			next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time > 0 and (next_rec_time - time.time()) < 120):
			msg += "\n" + _("Recording(s) are in progress or coming up in few seconds!")
		self.session.openWithCallback(self.purgeConfirmed, MessageBox, msg)

	def purgeConfirmed(self, confirmed):
		if not confirmed:
			return
		item = self.getCurrentSelection()
		current = item[0]
		cur_path = os.path.realpath(current.getPath())
		Tools.Trashcan.cleanAll(cur_path)

	def showNetworkSetup(self):
		from Screens import NetworkSetup
		self.session.open(NetworkSetup.NetworkAdapterSelection)

	def showActionFeedback(self, text):
		if self.feedbackTimer is None:
			self.feedbackTimer = eTimer()
			self.feedbackTimer.callback.append(self.hideActionFeedback)
		else:
			self.feedbackTimer.stop()
		self.feedbackTimer.start(3000, 1)
		self.diskinfo.setText(text)

	def hideActionFeedback(self):
		print("[ML] hide feedback")
		self.diskinfo.update()

	def can_gohome(self, item):
		return True

	def do_gohome(self):
		self.gotFilename(defaultMoviePath())

	def do_sort(self):
		index = 0
		for index, item in enumerate(l_moviesort):
			if int(item[0]) == int(config.movielist.moviesort.value):
				break
		if index >= len(l_moviesort) - 1:
			index = 0
		else:
			index += 1
		#descriptions in native languages too long...
		sorttext = l_moviesort[index][2]
		if config.movielist.btn_red.value == "sort":
			self['key_red'].setText(sorttext)
		if config.movielist.btn_green.value == "sort":
			self['key_green'].setText(sorttext)
		if config.movielist.btn_yellow.value == "sort":
			self['key_yellow'].setText(sorttext)
		if config.movielist.btn_blue.value == "sort":
			self['key_blue'].setText(sorttext)
		self.sorttimer = eTimer()
		self.sorttimer.callback.append(self._updateButtonTexts)
		self.sorttimer.start(1500, True) #time for displaying sorting type just applied
		self.sortBy(int(l_moviesort[index][0]))
		self["movie_sort"].setPixmapNum(int(l_moviesort[index][0]) - 1)

	def do_listtype(self):
		index = 0
		for index, item in enumerate(l_listtype):
			if int(item[0]) == int(config.movielist.listtype.value):
				break
		if index >= len(l_listtype) - 1:
			index = 0
		else:
			index += 1
		self.listType(int(l_listtype[index][0]))

	def do_preview(self):
		self.preview()

	def displaySortStatus(self):
		self["movie_sort"].setPixmapNum(int(config.movielist.moviesort.value) - 1)
		self["movie_sort"].show()

	def can_movieoff(self, item):
		return True

	def do_movieoff(self):
		self.setNextMovieOffStatus()
		self.displayMovieOffStatus()

	def displayMovieOffStatus(self):
		self["movie_off"].setPixmapNum(config.usage.on_movie_eof.getIndex())
		self["movie_off"].show()

	def setNextMovieOffStatus(self):
		config.usage.on_movie_eof.selectNext()
		self.settings["movieoff"] = config.usage.on_movie_eof.value
		self.saveLocalSettings()

	def can_movieoff_menu(self, item):
		return True

	def do_movieoff_menu(self):
		current_movie_eof = config.usage.on_movie_eof.value
		menu = []
		for x in config.usage.on_movie_eof.choices:
			config.usage.on_movie_eof.value = x
			menu.append((config.usage.on_movie_eof.getText(), x))
		config.usage.on_movie_eof.value = current_movie_eof
		used = config.usage.on_movie_eof.getIndex()
		self.session.openWithCallback(self.movieoffMenuCallback, ChoiceBox, title=_("On end of movie"), list=menu, selection=used, skin_name="MovieoffChoiceBox")

	def movieoffMenuCallback(self, choice):
		if choice is None:
			return
		self.settings["movieoff"] = choice[1]
		self.saveLocalSettings()
		self.displayMovieOffStatus()

	def createPlaylist(self):
		global playlist
		items = playlist
		del items[:]
		for index, item in enumerate(self["list"]):
			if item:
				item = item[0]
				if not item.flags & eServiceReference.mustDescent:
					ext = os.path.splitext(item.getPath())[1].lower()
					if ext not in IMAGE_EXTENSIONS:
						items.append(item)


playlist = []
