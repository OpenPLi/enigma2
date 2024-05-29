#
# This is a legacy converter. No new skins should be using it
# but it has left in place for old skins.
#
# Skinners that want to use menu icons should read:
# https://github.com/OpenPLi/enigma2/blob/develop/doc/MENU
#

from Components.Converter.Converter import Converter
from Components.Element import cached

legacyIDs = [
	"info_screen": "information",
	"setup_selection": "setup",
	"service_searching_selection": "scan",
	"system_selection": "system",
	"video_selection": "video",
	"gui_settings": "gui",
	"epg_menu": "epg",
	"expert_selection": "expert",
	"hardisk_selection": "harddisk",
	"cam_setup": "cam",
	"standby_restart_list": "shutdown",
]


class MenuEntryCompare(Converter):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.entry_id = legacyIDs.get(type, type)

	def selChanged(self):
		self.downstream_elements.changed((self.CHANGED_ALL, 0))

	@cached
	def getBool(self):
		id = self.entry_id
		cur = self.source.current
		if cur and len(cur) > 2:
			EntryID = cur[2]
			return EntryID and id and id == EntryID
		return False

	boolean = property(getBool)

	def changed(self, what):
		if what[0] == self.CHANGED_DEFAULT:
			self.source.onSelectionChanged.append(self.selChanged)
		Converter.changed(self, what)
