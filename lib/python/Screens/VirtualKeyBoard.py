import copy
import skin

from enigma import eListboxPythonMultiContent, gFont, getPrevAsciiCode, RT_HALIGN_CENTER, RT_VALIGN_CENTER

from Components.ActionMap import HelpableNumberActionMap
from Components.Input import Input
from Components.Label import Label
from Components.Language import language
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput


class VirtualKeyBoardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts.get("VirtualKeyBoard", ("Regular", 28, 45))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setFont(1, gFont(font[0], font[1] * 5 / 9))  # Smaller font is 56% the height of bigger font
		self.l.setItemHeight(font[2])


class VirtualKeyBoardEntryComponent:
	def __init__(self):
		pass


# For more information about using VirtualKeyBoard see /doc/VIRTUALKEYBOARD
#
class VirtualKeyBoard(Screen, HelpableScreen):
	def __init__(self, session, title=_("Virtual KeyBoard Text:"), text="", maxSize=False, visible_width=False, type=Input.TEXT, currPos=0, allMarked=False, keyGreen=_("Enter")):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Virtual keyboard"))
		prompt = title  # Title should only be used for screen titles!
		self.key_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_bg.png"))
		self.key_sel = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_sel.png"))
		self.key_longl_sel = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_longl_sel.png"))
		self.key_longm_sel = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_longm_sel.png"))
		self.key_longr_sel = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_longr_sel.png"))
		key_longl_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_longl_bg.png"))
		key_longm_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_longm_bg.png"))
		key_longr_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_longr_bg.png"))
		key_red_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_red.png"))
		key_green_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_green.png"))
		key_yellow_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_yellow.png"))
		key_blue_bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_blue.png"))
		key_backspace = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_backspace.png"))
		key_enter = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_enter.png"))
		key_first = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_first.png"))
		key_last = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_last.png"))
		key_left = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_left.png"))
		key_right = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_right.png"))
		key_shift0 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift0.png"))
		key_shift1 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift1.png"))
		key_shift2 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift2.png"))
		key_shift3 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift3.png"))
		# self.key_space = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_space.png"))
		key_space_alt = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_space_alt.png"))
		self.key_sel_width = self.key_sel.size().width()
		self.keyBackgrounds = {
			"EXIT": key_red_bg,
			"OK": key_green_bg,
			"ENTER": key_green_bg,
			"LOC": key_yellow_bg,
			"SHFT": key_blue_bg,
			"LongL": key_longl_bg,
			"LongM": key_longm_bg,
			"LongR": key_longr_bg
		}
		self.keyImages = [{
			"BACKSPACE": key_backspace,
			"ENTER": key_enter,
			"FIRST": key_first,
			"LAST": key_last,
			"LEFT": key_left,
			"RIGHT": key_right,
			"SHIFT": key_shift0,
			"SPACE": key_space_alt
		}, {
			"BACKSPACE": key_backspace,
			"ENTER": key_enter,
			"FIRST": key_first,
			"LAST": key_last,
			"LEFT": key_left,
			"RIGHT": key_right,
			"SHIFT": key_shift1,
			"SPACE": key_space_alt
		}, {
			"BACKSPACE": key_backspace,
			"ENTER": key_enter,
			"FIRST": key_first,
			"LAST": key_last,
			"LEFT": key_left,
			"RIGHT": key_right,
			"SHIFT": key_shift2,
			"SPACE": key_space_alt
		}, {
			"BACKSPACE": key_backspace,
			"ENTER": key_enter,
			"FIRST": key_first,
			"LAST": key_last,
			"LEFT": key_left,
			"RIGHT": key_right,
			"SHIFT": key_shift3,
			"SPACE": key_space_alt
		}]
		self.shiftMsgs = [
			_("Lower case"),
			_("Upper case"),
			_("Special 1"),
			_("Special 2")
		]
		self.english = [
			[
				[u"`", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACE"],
				[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"[", u"]", u"\\"],
				[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"", u"ENTER"],
				[u"SHIFT", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"/", u"", u"", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
			], [
				[u"~", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"_", u"+", u"BACKSPACE"],
				[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"{", u"}", u"|"],
				[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u":", u"\"", u"", u"ENTER"],
				[u"SHIFT", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"<", u">", u"?", u"", u"", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
			]
		]
		self.english_EN_US = [
			[
				[u"`", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACE"],
				[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"[", u"]", u"\\"],
				[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"LongL__ENTER__HIDE", u"LongR__Enter"],
				[u"LongL__Shift", u"LongR__SHIFT__HIDE", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"/", u"LongL__SHIFT__HIDE", u"LongR__Shift"],
				[u"LongL__Esc", u"LongR__ESC__HIDE", u"Loc", u"All", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"LEFT", u"RIGHT", u"LongL__CLR__HIDE", u"LongR__Clr"]
			], [
				[u"~", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"_", u"+", u"BACKSPACE"],
				[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"{", u"}", u"|"],
				[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u":", u"\"", u"LongL__ENTER__HIDE", u"LongR__Enter"],
				[u"LongL__Shift", u"LongR__SHIFT__HIDE", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"<", u">", u"?", u"LongL__SHIFT__HIDE", u"LongR__Shift"],
				[u"LongL__Esc", u"LongR__ESC__HIDE", u"Loc", u"All", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"LEFT", u"RIGHT", u"LongL__CLR__HIDE", u"LongR__Clr"]
			]
		]
		self.french = [
			[
				[u"\u00B2", u"&", u"\u00E9", u"\"", u"'", u"(", u"-", u"\u00E8", u"_", u"\u00E7", u"\u00E0", u")", u"=", u"BACKSPACE"],
				[u"FIRST", u"a", u"z", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"$", u"[", u"]"],
				[u"LAST", u"q", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"m", u"\u00F9", u"*", u"ENTER"],
				[u"SHIFT", u"<", u"w", u"x", u"c", u"v", u"b", u"n", u",", u";", u":", u"!", u"\u20AC", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"#", u"@", u"`"]
			], [
				[u"", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"\u00B0", u"+", u"BACKSPACE"],
				[u"FIRST", u"A", u"Z", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"\u00A3", u"{", u"}"],
				[u"LAST", u"Q", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"M", u"%", u"\u00B5", u"ENTER"],
				[u"SHIFT", u">", u"W", u"X", u"C", u"V", u"B", u"N", u"?", u".", u"/", u"\u00A7", u"\u00A6", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"~", u"^", u"\\"]
			], [
				[u"", u"", u"\u00E2", u"\u00EA", u"\u00EE", u"\u00F4", u"\u00FB", u"\u00E4", u"\u00EB", u"\u00EF", u"\u00F6", u"\u00FC", u"", u"BACKSPACE"],
				[u"FIRST", u"", u"\u00E0", u"\u00E8", u"\u00EC", u"\u00F2", u"\u00F9", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"", u""],
				[u"LAST", u"", u"\u00C2", u"\u00CA", u"\u00CE", u"\u00D4", u"\u00DB", u"\u00C4", u"\u00CB", u"\u00CF", u"\u00D6", u"\u00DC", u"", u"ENTER"],
				[u"SHIFT", u"", u"\u00C0", u"\u00C8", u"\u00CC", u"\u00D2", u"\u00D9", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
			]
		]
		self.german = [
			[
				[u"", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"\u00DF", u"'", u"BACKSPACE"],
				[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"\u00FC", u"[", u"]"],
				[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u00F6", u"\u00E4", u"+", U"ENTER"],
				[u"SHIFT", u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"#", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"|", u"\\", u"\u00B5"]
			], [
				[u"\u00B0", u"!", u"\"", u"\u00A7", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"?", u"`", u"BACKSPACE"],
				[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"\u00DC", u"{", u"}"],
				[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\u00D6", u"\u00C4", u"*", U"ENTER"],
				[u"SHIFT", u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"@", U"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"\u20AC", u"\u00B2", u"\u00B3"]
			]
		]
		self.latvian = [
			[
				[u"`", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACE"],
				[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"[", u"]", u"\\"],
				[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"LongL__ENTER__HIDE", u"LongR__Enter"],
				[u"LongL__Shift", u"LongR__SHIFT__HIDE", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"/", u"LongL__SHIFT__HIDE", u"LongR__Shift"],
				[u"LongL__Esc", u"LongR__ESC__HIDE", u"Loc", u"All", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"LEFT", u"RIGHT", u"LongL__CLR__HIDE", u"LongR__Clr"]
			], [
				[u"~", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"_", u"+", u"BACKSPACE"],
				[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"{", u"}", u"|"],
				[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u":", u"\"", u"LongL__ENTER__HIDE", u"LongR__Enter"],
				[u"LongL__Shift", u"LongR__SHIFT__HIDE", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"<", u">", u"?", u"LongL__SHIFT__HIDE", u"LongR__Shift"],
				[u"LongL__Esc", u"LongR__ESC__HIDE", u"Loc", u"All", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"LEFT", u"RIGHT", u"LongL__CLR__HIDE", u"LongR__Clr"]
			], [
				[u"\u00b4", u"\u00b9", u"\u00b2", u"\u00b3", u"\u20ac", u"\u00bd", u"\u00be", u"\u007b", u"\u005b", u"\u005d", u"\u007d ", u"\u005c", u"\u2013", u"BACKSPACE"],
				[u"FIRST", u"q", u"\u0113", u"\u0112", u"\u0157", u"\u0156", u"\u016B", u"\u016A", u"\u012B", u"\u012A", u"\u014D", u"\u014C", u"\u00ab", u"\u00bb"],
				[u"LAST", u"\u0101", u"\u0100", u"\u0161", u"\u0160", u"\u0123", u"\u0122", u"\u0137", u"\u0136", u"\u013C", u"\u013B", u"\u003b", u"LongL__ENTER__HIDE", u"LongR__Enter"],
				[u"LongL__Shift", u"LongR__SHIFT__HIDE", u"\u017E", u"\u017D", u"\u010D", u"\u010C", u"b", u"\u0146", u"\u0145", u"\u0060", u"\u00b7", u"\u002f", u"LongL__SHIFT__HIDE", u"LongR__Shift"],
				[u"LongL__Esc", u"LongR__ESC__HIDE", u"Loc", u"All", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"LEFT", u"RIGHT", u"LongL__CLR__HIDE", u"LongR__Clr"]
			]
		]
		self.russian = [
			[
				[u"\u0451", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACE"],
				[u"FIRST", u"\u0439", u"\u0446", u"\u0443", u"\u043A", u"\u0435", u"\u043D", u"\u0433", u"\u0448", u"\u0449", u"\u0437", u"\u0445", u"\u044A", u"\u00A7"],
				[u"LAST", u"\u0444", u"\u044B", u"\u0432", u"\u0430", u"\u043F", u"\u0440", u"\u043E", u"\u043B", u"\u0434", u"\u0436", u"\u044D", u"\\", u"ENTER"],
				[u"SHIFT", u"\u044F", u"\u0447", u"\u0441", u"\u043C", u"\u0438", u"\u0442", u"\u044C", u"\u0431", u"\u044E", u".", u"@", u"&", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"<"]
			], [
				[u"\u0401", u"!", u"\"", u"\u2116", u";", u"%", u":", u"?", u"*", u"(", u")", u"_", u"+", u"BACKSPACE"],
				[u"FIRST", u"\u0419", u"\u0426", u"\u0423", u"\u041A", u"\u0415", u"\u041D", u"\u0413", u"\u0428", u"\u0429", u"\u0417", u"\u0425", u"\u042A", u"\u20BD"],
				[u"LAST", u"\u0424", u"\u042B", u"\u0412", u"\u0410", u"\u041F", u"\u0420", u"\u041E", u"\u041B", u"\u0414", u"\u0416", u"\u042D", u"/", u"ENTER"],
				[u"SHIFT", u"\u042F", u"\u0427", u"\u0421", u"\u041C", u"\u0418", u"\u0422", u"\u042C", u"\u0411", u"\u042E", u",", u"#", u"$", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u">"]
			]
		]
		self.scandinavian = [
			[
				[u"\u00A7", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"+", u"@", u"BACKSPACE"],
				[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"\u00E5", u"[", u"]"],
				[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u00F6", u"\u00E4", u"'", u"ENTER"],
				[u"SHIFT", u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"\u00AB", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
			], [
				[u"\u00BD", u"!", u"\"", u"#", u"\u00A4", u"%", u"&", u"/", u"(", u")", u"=", u"?", u"|", u"BACKSPACE"],
				[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"\u00C5", u"{", u"}"],
				[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\u00D6", u"\u00C4", u"*", u"ENTER"],
				[u"SHIFT", u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"\u00BB", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
			], [
				[u"", u"\u00E2", u"\u00EA", u"\u00EE", u"\u00F4", u"\u00FB", u"\u00E4", u"\u00EB", u"\u00EF", u"\u00F6", u"\u00FC", u"\u00E3", u"\u00F5", u"BACKSPACE"],
				[u"FIRST", u"\u00E0", u"\u00E8", u"\u00EC", u"\u00F2", u"\u00F9", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"", u"", u""],
				[u"LAST", u"\u00C2", u"\u00CA", u"\u00CE", u"\u00D4", u"\u00DB", u"\u00C4", u"\u00CB", u"\u00CF", u"\u00D6", u"\u00DC", u"\u00C3", u"\u00D5", u"ENTER"],
				[u"SHIFT", u"\u00C0", u"\u00C8", u"\u00CC", u"\u00D2", u"\u00D9", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"", u"", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
			]
		]
		self.spanish = [
			[
				[u"\\", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"'", u"\u00A1", u"BACKSPACE"],
				[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"@", u"+", u"\u00E7"],
				[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u00F1", u"[", u"]", u"ENTER"],
				[u"SHIFT", u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"\u20AC", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"\u00FC"]
			], [
				[u"|", u"!", u"\"", u"\u00B7", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"?", u"\u00BF", u"BACKSPACE"],
				[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"#", u"*", u"\u00C7"],
				[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\u00D1", u"{", u"}", u"ENTER"],
				[u"SHIFT", u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"\u00AC", u"SHIFT"],
				[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"\u00DC"]
			]
		]
		self.locales = {
			"ar_BH": [_("Arabic"), _("Bahrain"), self.arabic(self.english)],
			"ar_EG": [_("Arabic"), _("Egypt"), self.arabic(self.english)],
			"ar_JO": [_("Arabic"), _("Jordan"), self.arabic(self.english)],
			"ar_KW": [_("Arabic"), _("Kuwait"), self.arabic(self.english)],
			"ar_LB": [_("Arabic"), _("Lebanon"), self.arabic(self.english)],
			"ar_OM": [_("Arabic"), _("Oman"), self.arabic(self.english)],
			"ar_QA": [_("Arabic"), _("Qatar"), self.arabic(self.english)],
			"ar_SA": [_("Arabic"), _("Saudi Arabia"), self.arabic(self.english)],
			"ar_SY": [_("Arabic"), _("Syrian Arab Republic"), self.arabic(self.english)],
			"ar_AE": [_("Arabic"), _("United Arab Emirates"), self.arabic(self.english)],
			"ar_YE": [_("Arabic"), _("Yemen"), self.arabic(self.english)],
			"cs_CZ": [_("Czech"), _("Czechia"), [
				[
					[u";", u"+", u"\u011B", u"\u0161", u"\u010D", u"\u0159", u"\u017E", u"\u00FD", u"\u00E1", u"\u00ED", u"\u00E9", u"=", u"", u"BACKSPACE"],
					[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"\u00FA", u")", u""],
					[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u016F", u"\u00A7", u"", u"ENTER"],
					[u"SHIFT", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"\u0148", u"", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"ALL", u"CLR", u"DEL"]
				], [
					[u".", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"%", u"", u"BACKSPACE"],
					[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"/", u"(", u""],
					[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\"", u"!", u"'", u"ENTER"],
					[u"SHIFT", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u"?", u":", u"_", u"\u0147", u"", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"ALL", u"CLR", u"DEL"]
				], [
					[u"", u"~", u"\u011A", u"\u0160", u"\u010C", u"\u0158", u"\u017D", u"\u00DD", u"\u00C1", u"\u00CD", u"\u00C9", u"`", u"", u"BACKSPACE"],
					[u"FIRST", u"\\", u"|", u"\u20AC", u"\u0165", u"\u0164", u"", u"", u"", u"\u00F3", u"\u00D3", u"\u00DA", u"\u00F7", u"\u00D7"],
					[u"LAST", u"", u"\u0111", u"\u00D0", u"[", u"]", u"\u010F", u"\u010E", u"\u0142", u"\u0141", u"\u016E", u"$", u"\u00DF", u"ENTER"],
					[u"SHIFT", u"", u"#", u"&", u"@", u"{", u"}", u"", u"<", u">", u"*", u"", u"\u00A4", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"LongL__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongM__SPACE__HIDE", u"LongR__SPACE__HIDE", u"ALL", u"CLR", u"DEL"]
				]
			]],
			"nl_NL": [_("Dutch"), _("Netherlands"), self.dutch(self.english)],
			"en_AU": [_("English"), _("Australian"), self.australian(self.english)],
			"en_GB": [_("English"), _("United Kingdom"), self.unitedKingdom(self.english)],
			"en_US": [_("English"), _("United States"), self.english_EN_US],
			"en_EN": [_("English"), _("Various"), self.english_EN_US],
			"et_EE": [_("Estonian"), _("Estonia"), self.estonian(self.scandinavian)],
			"fi_FI": [_("Finnish"), _("Finland"), self.finnish(self.scandinavian)],
			"fr_BE": [_("French"), _("Belgian"), self.belgian(self.french)],
			"fr_FR": [_("French"), _("France"), self.french],
			"de_CH": [_("German"), _("Switzerland"), self.swiss(self.german)],
			"de_DE": [_("German"), _("Germany"), self.german],
			"el_GR": [_("Greek (Modern)"), _("Greece"), [
				[
					[u"`", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACE"],
					[u"FIRST", u";", u"\u03C2", u"\u03B5", u"\u03C1", u"\u03C4", u"\u03C5", u"\u03B8", u"\u03B9", u"\u03BF", u"\u03C0", u"[", u"]", u"/"],
					[u"LAST", u"\u03B1", u"\u03C3", u"\u03B4", u"\u03C6", u"\u03B3", u"\u03B7", u"\u03BE", u"\u03BA", u"\u03BB", u"", u"'", u"\\", u"ENTER"],
					[u"SHIFT", u"<", u"\u03B6", u"\u03C7", u"\u03C8", u"\u03C9", u"\u03B2", u"\u03BD", u"\u03BC", u",", ".", u"\u03CA", u"\u03CB", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"\u03AC", u"\u03AD", u"\u03AE", u"\u03AF", u"\u03CC", u"\u03CD", u"\u03CE"]
				], [
					[u"~", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"_", u"+", u"BACKSPACE"],
					[u"FIRST", u":", u"", u"\u0395", u"\u03A1", u"\u03A4", u"\u03A5", u"\u0398", u"\u0399", u"\u039F", u"\u03A0", u"{", u"}", u"?"],
					[u"LAST", u"\u0391", u"\u03A3", u"\u0394", u"\u03A6", u"\u0393", u"\u0397", u"\u039E", u"\u039A", u"\u039B", u"", u"\"", u"|", u"ENTER"],
					[u"SHIFT", u">", u"\u0396", u"\u03A7", u"\u03A8", u"\u03A9", u"\u0392", u"\u039D", u"\u039C", u"<", u">", u"\u03AA", u"\u03AB", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"\u0386", u"\u0388", u"\u0389", u"\u038A", u"\u038C", u"\u038E", u"\u038F"]
				], [
					[u"", u"", u"\u00B2", u"\u00B3", u"\u00A3", u"\u00A7", u"\u00B6", u"\u20AC", u"\u00A4", u"\u00A6", u"\u00B0", u"\u00B1", u"\u00BD", u"BACKSPACE"],
					[u"FIRST", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u""],
					[u"LAST", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"ENTER"],
					[u"SHIFT", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
				]
			]],
			"lv_LV": [_("Latvian"), _("Latvia"), self.latvian],
			"lt_LT": [_("Lithuanian"), _("Lithuania"), self.lithuanian(self.english)],
			"nb_NO": [_("Norwegian"), _("Norway"), self.norwegian(self.scandinavian)],
			"fa_IR": [_("Persian"), _("Iran, Islamic Republic"), self.persian(self.english)],
			"pl_PL": [_("Polish"), _("Poland"), self.polish(self.english)],
			"ru_RU": [_("Russian"), _("Russian Federation"), self.russian],
			"sk_SK": [_("Slovak"), _("Slovakia"), [
				[
					[u"~", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"\u00E1", u"\u00E4", u"BACKSPACE"],
					[u"FIRST", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"\u010D", u"\u010F", u"\u00E9"],
					[u"LAST", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u00ED", u"\u013A", u"\u013E", u"ENTER"],
					[u"SHIFT", u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"\u0148", u"\u00F3", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"\u00F4", u"\u0155", u"\u0161", u"\u0165", u"\u00FA", u"\u00FD", u"\u017E"]
				], [
					[u"`", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"\u00C1", u"\u00C4", u"BACKSPACE"],
					[u"FIRST", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"\u010C", u"\u010E", u"\u00C9"],
					[u"LAST", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\u00CD", u"\u0139", u"\u013D", u"ENTER"],
					[u"SHIFT", u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"?", u":", u"\u0147", u"\u00D3", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE", u"\u00D4", u"\u0154", u"\u0160", u"\u0164", u"\u00DA", u"\u00DD", u"\u017D"]
				], [
					[u"", u"", u"\u00A7", u"\u00B0", u"\u00A4", u"\u20AC", u"\u00DF", u"\u0111", u"\u0110", u"\u0142", u"\u0141", u"", u"", u"BACKSPACE"],
					[u"FIRST", u"", u"", u"'", u"\"", u"+", u"-", u"\u00D7", u"\u00F7", u"=", u"_", u"~", u"", u""],
					[u"LAST", u"", u"", u"/", u"\\", u";", u"[", u"]", u"{", u"}", u"|", u"", u"", u"ENTER"],
					[u"SHIFT", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
				]
			]],
			"es_ES": [_("Spanish"), _("Spain"), self.spanish],
			"sv_SE": [_("Swedish"), _("Sweden"), self.swedish(self.scandinavian)],
			"th_TH": [_("Thai"), _("Thailand"), [
				[
					[u"", u"", u"\u0E45", u"\u0E20", u"\u0E16", u"\u0E38", u"\u0E36", u"\u0E04", u"\u0E15", u"\u0E08", u"\u0E02", u"\u0E0A", u"", u"BACKSPACE"],
					[u"FIRST", u"\u0E46", u"\u0E44", u"\u0E33", u"\u0E1E", u"\u0E30", u"\u0E31", u"\u0E35", u"\u0E23", u"\u0E19", u"\u0E22", u"\u0E1A", u"\u0E25", u""],
					[u"LAST", u"\u0E1F", u"\u0E2B", u"\u0E01", u"\u0E14", u"\u0E40", u"\u0E49", u"\u0E48", u"\u0E32", u"\u0E2A", u"\u0E27", u"\u0E07", u"\u0E03", u"OK"],
					[u"SHIFT", u"\u0E1C", u"\u0E1B", u"\u0E41", u"\u0E2D", u"\u0E34", u"\u0E37", u"\u0E17", u"\u0E21", u"\u0E43", u"\u0E1D", u"", u"", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
				], [
					[u"", u"", u"\u0E51", u"\u0E52", u"\u0E53", u"\u0E54", u"\u0E39", u"\u0E55", u"\u0E56", u"\u0E57", u"\u0E58", u"\u0E59", u"", u"BACKSPACE"],
					[u"FIRST", u"\u0E50", u"", u"\u0E0E", u"\u0E11", u"\u0E18", u"\u0E4D", u"\u0E4A", u"\u0E13", u"\u0E2F", u"\u0E0D", u"\u0E10", u"\u0E05", u""],
					[u"LAST", u"\u0E24", u"\u0E06", u"\u0E0F", u"\u0E42", u"\u0E0C", u"\u0E47", u"\u0E4B", u"\u0E29", u"\u0E28", u"\u0E0B", u"", u"\u0E3F", u"OK"],
					[u"SHIFT", u"", u"", u"\u0E09", u"\u0E2E", u"\u0E3A", u"\u0E4C", u"", u"\u0E12", u"\u0E2C", u"\u0E26", u"", u"", u"SHIFT"],
					[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
				]
			]],
			"uk_UA": [_("Ukrainian"), _("Ukraine"), self.ukranian(self.russian)]
		}

		self["actions"] = HelpableNumberActionMap(self, "VirtualKeyBoardActions", {
			"cancel": (self.cancel, _("Cancel any text changes and exit")),
			"save": (self.enter, _("Enter text and exit")),
			"locale": (self.localeMenu, _("Select the virtual keyboard locale from a menu")),
			"shift": (self.shiftClicked, _("Select the virtual keyboard shifted character set")),
			"select": (self.processSelect, _("Select the character or action under the virtual keyboard cursor")),
			"up": (self.up, _("Move the virtual keyboard cursor up")),
			"left": (self.left, _("Move the virtual keyboard cursor left")),
			"right": (self.right, _("Move the virtual keyboard cursor right")),
			"down": (self.down, _("Move the virtual keyboard cursor down")),
			"first": (self.cursorFirst, _("Move the text buffer cursor to the first character")),
			"prev": (self.cursorLeft, _("Move the text buffer cursor left")),
			"next": (self.cursorRight, _("Move the text buffer cursor right")),
			"last": (self.cursorLast, _("Move the text buffer cursor to the last character")),
			"toggleOverwrite": (self.keyToggleOW, _("Toggle new text inserts before or overwrites existing text")),
			"backspace": (self.backClicked, _("Delete the character to the left of text buffer cursor")),
			"delete": (self.forwardClicked, _("Delete the character under the text buffer cursor")),
			"1": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"2": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"3": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"4": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"5": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"6": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"7": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"8": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"9": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"0": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"gotAsciiCode": (self.keyGotAscii, _("Keyboard data entry"))
		}, -2, description=_("Virtual KeyBoard Functions"))

		self.lang = language.getLanguage()
		self["prompt"] = Label(prompt)
		self["text"] = Input(text=text, maxSize=maxSize, visible_width=visible_width, type=type, currPos=len(text.decode("utf-8", "ignore")), allMarked=allMarked)
		self["list"] = VirtualKeyBoardList([])
		self["mode"] = Label(_("INS"))
		self["locale"] = Label(_("Locale") + ": " + self.lang)
		self["language"] = Label(_("Language") + ": " + self.lang)
		self["key_info"] = StaticText(_("INFO"))
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(keyGreen)
		self["key_yellow"] = StaticText(_("Select locale"))
		self["key_blue"] = StaticText(self.shiftMsgs[1])
		self["key_help"] = StaticText(_("HELP"))

		width, self.height = skin.parameters.get("VirtualKeyBoard", (45, 45))
		self.width = self.key_bg and self.key_bg.size().width() or width
		self.shiftColors = skin.parameters.get("VirtualKeyBoardShiftColors", (0x00ffffff, 0x00ffffff, 0x0000ffff, 0x00ff00ff))  # Ensure there is a color for each shift level!
		self.language = None
		self.location = None
		self.keyList = []
		self.previousSelectedKey = []
		self.shiftLevels = 0
		self.shiftLevel = 0
		self.keyboardWidth = 0
		self.keyboardHeight = 0
		self.maxKey = 0
		self.overwrite = False
		self.selectedKey = None
		self.sms = NumericalTextInput(self.smsGotChar)
		self.smsChar = None
		self.setLocale()
		self.onExecBegin.append(self.setKeyboardModeAscii)
		self.onLayoutFinish.append(self.buildVirtualKeyBoard)

	def arabic(self, base):
		keyList = copy.deepcopy(base)
		keyList[1][0][8] = u"\u066D"
		keyList.extend([[
			[u"\u0630", u"\u0661", u"\u0662", u"\u0663", u"\u0664", u"\u0665", u"\u0666", u"\u0667", u"\u0668", u"\u0669", u"\u0660", u"-", u"=", u"BACKSPACE"],
			[u"FIRST", u"\u0636", u"\u0635", u"\u062B", u"\u0642", u"\u0641", u"\u063A", u"\u0639", u"\u0647", u"\u062E", u"\u062D", u"\u062C", u"\u062F", u"\\"],
			[u"LAST", u"\u0634", u"\u0633", u"\u064A", u"\u0628", u"\u0644", u"\u0627", u"\u062A", u"\u0646", u"\u0645", u"\u0643", u"\u0637", u"", u"ENTER"],
			[u"SHIFT", u"\u0626", u"\u0621", u"\u0624", u"\u0631", u"\uFEFB", u"\u0649", u"\u0629", u"\u0648", u"\u0632", u"\u0638", u"", u"", u"SHIFT"],
			[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
		], [
			[u"\u0651", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"\u066D", u"(", u")", u"_", u"+", u"BACKSPACE"],
			[u"FIRST", u"\u0636", u"\u0635", u"\u062B", u"\u0642", u"\u0641", u"\u063A", u"\u0639", u"\u00F7", u"\u00D7", u"\u061B", u">", u"<", u"|"],
			[u"LAST", u"\u0634", u"\u0633", u"\u064A", u"\u0628", u"\u0644", u"\u0623", u"\u0640", u"\u060C", u"/", u":", u"\"", u"", u"ENTER"],
			[u"SHIFT", u"\u0626", u"\u0621", u"\u0624", u"\u0631", u"\uFEF5", u"\u0622", u"\u0629", u",", u".", u"\u061F", u"", u"", u"SHIFT"],
			[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
		]])
		return keyList

	def australian(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][-1].extend([u"www.", u".com", u".net", u".org", u".edu", u".au", u".tv"])
		keyList[1][-1].extend([u"www.", u".com", u".net", u".org", u".edu", u".au", u".tv"])
		return keyList

	def belgian(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][0][6] = u"\u00A7"
		keyList[0][0][8] = u"!"
		keyList[0][0][12] = u"-"
		keyList[0][2][12] = u"\u00B5"
		keyList[0][3][11] = u"="
		keyList[1][0][0] = u"\u00B3"
		keyList[1][0][12] = u"_"
		keyList[1][1][11] = u"*"
		keyList[1][2][12] = u"\u00A3"
		keyList[1][3][11] = u"+"
		return keyList

	def dutch(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][0][0] = u"@"
		keyList[0][0][11] = u"/"
		keyList[0][0][12] = u"\u00BA"
		keyList[0][1][11] = u"\u00A8"
		keyList[0][1][12] = u"*"
		keyList[0][1][13] = u"<"
		keyList[0][2][10] = u"+"
		keyList[0][2][11] = u"\u00B4"
		keyList[0][2][12] = u"\\"
		keyList[0][3] = [u"SHIFT", u"]", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"-", u"{", u"SHIFT"]
		keyList[0][-1].extend([u"www.", u".com", u".net", u".org", u".edu", u".nl", u".tv"])
		keyList[1][0] = [u"\u00A7", u"!", u"\"", u"#", u"$", u"%", u"&", u"_", u"(", u")", u"'", u"?", u"~", u"BACKSPACE"]
		keyList[1][1][11] = u"^"
		keyList[1][1][12] = u"|"
		keyList[1][1][13] = u">"
		keyList[1][2][10] = u"\u00B1"
		keyList[1][2][11] = u"`"
		keyList[1][2][12] = u"\u00A6"
		keyList[1][3] = [u"SHIFT", u"[", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"=", u"}", u"SHIFT"]
		keyList[1][-1].extend([u"www.", u".com", u".net", u".org", u".edu", u".nl", u".tv"])
		keyList.append([
			[u"\u00AC", u"\u00B9", u"\u00B2", u"\u00B3", u"\u00BC", u"\u00BD", u"\u00BE", u"\u00A3", u"{", u"}", u"$", u"\\", u"", u"BACKSPACE"],
			[u"FIRST", u"", u"", u"\u20AC", u"\u00B6", u"", u"", u"", u"", u"", u"", u"", u"", u""],
			[u"LAST", u"", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"", u"ENTER"],
			[u"SHIFT", u"\u00A6", u"\u00AB", u"\u00BB", u"\u00A2", u"", u"", u"", u"\u00B5", u"", u"\u00B7", u"", u"", u"SHIFT"],
			[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
		])
		return keyList

	def estonian(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][1][11] = u"\u00FC"
		keyList[0][1][12] = u"\u00F5"
		keyList[0][1][13] = u"\u0161"
		keyList[0][3][12] = u"\u017E"
		keyList[0][4].extend([u"[", u"]", u"\\"])
		keyList[1][1][11] = u"\u00DC"
		keyList[1][1][12] = u"\u00D5"
		keyList[1][1][13] = u"\u0160"
		keyList[1][3][12] = u"\u017D"
		keyList[1][4].extend([u"{", u"}", u"\u00A3", u"$", u"\u20AC"])
		del keyList[2]
		return keyList

	def finnish(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][4].append(u"\\")
		keyList[1][4].extend([u"\u00A3", u"$", u"\u20AC"])
		return keyList

	def lithuanian(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][0] = [u"`", u"\u0105", u"\u010D", u"\u0119", u"\u0117", u"\u012F", u"\u0161", u"\u0173", u"\u016B", u"", u"", u"", u"\u017E", u"BACKSPACE"]
		keyList[0][1][13] = u""
		keyList[0][2][12] = u"\\"
		keyList[1][0] = [u"~", u"\u0104", u"\u010C", u"\u0118", u"\u0116", u"\u012E", u"\u0160", u"\u0172", u"\u016A", u"\u201E", u"\u201C", u"", u"\u017D", u"BACKSPACE"]
		keyList[1][1][13] = u""
		keyList[1][2][12] = u"|"
		keyList.append([
			[u"\u02DC", u"\u00BC", u"\u00BD", u"\u00BE", u"\u00A4", u"\u00A2", u"\u00B0", u"\u00A7", u"\u00D7", u"\u00AB", u"\u00BB", u"\u00F7", u"\u00B1", u"BACKSPACE"],
			[u"FIRST", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"\u00AD"],
			[u"LAST", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"_", u"+", u"ENTER"],
			[u"SHIFT", u"", u"\u00DF", u"\u00A9", u"\u00AE", u"\u2122", u"\u00AC", u"\u00A3", u"\u20AC", u"\u00B7", u"\u00B9", u"\u00B2", u"\u00B3", u"SHIFT"],
			[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
		])
		return keyList

	def norwegian(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][0][0] = u"|"
		keyList[0][0][12] = u"\\"
		keyList[0][2][10] = u"\u00F8"
		keyList[0][2][11] = u"\u00E6"
		keyList[0][3][12] = u"\u00B5"
		keyList[1][0][0] = u"\u00A7"
		keyList[1][0][12] = u"@"
		keyList[1][2][10] = u"\u00D8"
		keyList[1][2][11] = u"\u00C6"
		keyList[1][3][12] = u""
		keyList[1][4].extend([u"\u00A3", u"$", u"\u20AC"])
		return keyList

	def persian(self, base):
		keyList = copy.deepcopy(base)
		keyList.append([
			[u"\u00F7", u"\u06F1", u"\u06F2", u"\u06F3", u"\u06F4", u"\u06F5", u"\u06F6", u"\u06F7", u"\u06F8", u"\u06F9", u"\u06F0", u"-", u"=", u"BACKSPACE"],
			[u"FIRST", u"\u0636", u"\u0635", u"\u062B", u"\u0642", u"\u0641", u"\u063A", u"\u0639", u"\u0647", u"\u062E", u"\u062D", u"\u062C", u"\u0686", u"\u067E"],
			[u"LAST", u"\u0634", u"\u0633", u"\u0649", u"\u0628", u"\u0644", u"\u0622", u"\u0627", u"\u062A", u"\u0646", u"\u0645", u"\u06A9", u"\u06AF", u"ENTER"],
			[u"SHIFT", u"\u0638", u"\u0637", u"\u0698", u"\u0632", u"\u0631", u"\u0630", u"\u062F", u"\u0626", u"\u0621", u"\u0648", u"\u060C", u"\u061F", u"SHIFT"],
			[u"EXIT", u"LOC", u"LEFT", u"RIGHT", u"ALL", u"CLR", u"SPACE"]
		])
		return keyList

	def polish(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][3][11] = u"\u0105"
		keyList[0][3][12] = u"\u0107"
		keyList[0][-1].extend([u"\u0119", u"\u0142", u"\u0144", u"\u00F3", u"\u015B", u"\u017A", u"\u017C"])
		keyList[1][2][12] = u"\u20AC"
		keyList[1][3][11] = u"\u0104"
		keyList[1][3][12] = u"\u0106"
		keyList[1][-1].extend([u"\u0118", u"\u0141", u"\u0143", u"\u00D3", u"\u015A", u"\u0179", u"\u017B"])
		return keyList

	def swedish(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][4].extend([u"\\", u"\u00B5"])
		keyList[1][4].extend([u"\u00A3", u"$", u"\u20AC"])
		return keyList

	def swiss(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][0][0] = u"\u00A7"
		keyList[0][0][11] = u"'"
		keyList[0][0][12] = u"^"
		keyList[0][2][12] = u"$"
		keyList[0][3][12] = u"\u20AC"
		keyList[0][4][7] = u"\u00E0"
		keyList[0][4][8] = u"\u00E8"
		keyList[0][4][9] = u"\u00E9"
		keyList[0][4].extend([u"@", u"!", u"\u00AC", u"\\"])
		keyList[1][0][1] = u"+"
		keyList[1][0][3] = u"*"
		keyList[1][0][4] = u"\u00E7"
		keyList[1][0][11] = u"?"
		keyList[1][0][12] = u"`"
		keyList[1][2][12] = u"\u00A3"
		keyList[1][3][12] = u"\u00A2"
		keyList[1][4][9] = u"\u00AC"
		keyList[1][4][9] = u"\u00A6"
		keyList[1][4][7] = u"\u00C0"
		keyList[1][4][8] = u"\u00C8"
		keyList[1][4][9] = u"\u00C9"
		keyList[1][4].extend([u"#", u"|", u"\u00A6"])
		return keyList

	def ukranian(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][1][12] = u"\u0457"
		keyList[0][2][2] = u"\u0456"
		keyList[0][2][11] = u"\u0454"
		keyList[0][3][11] = u"\u0491"
		keyList[0][4].append(u"@")
		keyList[1][1][12] = u"\u0407"
		keyList[1][2][2] = u"\u0406"
		keyList[1][2][11] = u"\u0404"
		keyList[1][3][11] = u"\u0490"
		keyList[1][4].append(u"#")
		return keyList

	def unitedKingdom(self, base):
		keyList = copy.deepcopy(base)
		keyList[0][1][13] = u"\u00A6"
		keyList[0][2][12] = u"#"
		keyList[0][3] = [u"SHIFT", u"\\", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"/", u"", u"SHIFT"]
		# keyList[0][-1].extend([u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA"])  # English users don't use the accented characters.
		keyList[1][0][0] = u"\u00AC"
		keyList[1][0][2] = u"\""
		keyList[1][0][3] = u"\u00A3"
		keyList[1][1][13] = u"\u20AC"
		keyList[1][2][11] = u"@"
		keyList[1][2][12] = u"~"
		keyList[1][3] = [u"SHIFT", u"|", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"<", u">", u"?", u"", u"SHIFT"]
		# keyList[1][-1].extend([u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA"])  # English users don't use the accented characters.
		return keyList

	def smsGotChar(self):
		if self.smsChar and self.selectAsciiKey(self.smsChar):
			self.processSelect()

	def setLocale(self):
		self.language, self.location, self.keyList = self.locales.get(self.lang, [None, None, None])
		if self.language is None or self.location is None or self.keyList is None:
			self.lang = "en_EN"
			self.language = _("English")
			self.location = _("Various")
			self.keyList = self.english_EN_US
		self.shiftLevel = 0
		self["locale"].setText(_("Locale") + ": " + self.lang + "  (" + self.language + " - " + self.location + ")")

	def buildVirtualKeyBoard(self):
		self.shiftLevels = len(self.keyList)
		if self.shiftLevel >= self.shiftLevels:
			self.shiftLevel = 0
		self.keyboardWidth = len(self.keyList[self.shiftLevel][0])
		self.keyboardHeight = len(self.keyList[self.shiftLevel])
		self.maxKey = self.keyboardWidth * (self.keyboardHeight - 1) + len(self.keyList[self.shiftLevel][-1]) - 1
		# print "[VirtualKeyBoard] DEBUG: Width=%d, Height=%d, Keys=%d, maxKey=%d, shiftLevels=%d" % (self.keyboardWidth, self.keyboardHeight, self.maxKey + 1, self.maxKey, self.shiftLevels)
		self.list = []
		for keys in self.keyList[self.shiftLevel]:
			self.list.append(self.virtualKeyBoardEntryComponent(keys))
		self.previousSelectedKey = []
		if self.selectedKey is None:
			self.selectedKey = self.keyboardWidth
		self.markSelectedKey()

	def virtualKeyBoardEntryComponent(self, keys):
		res = [keys]
		text = []
		offset = 14 - self.keyboardWidth  # 14 represents the maximum buttons per row as defined here and in the skin (14 x self.width).
		x = self.width * offset / 2
		if offset % 2:
			x += self.width / 2
		for key in keys:
			image = self.keyImages[self.shiftLevel].get(key, None)
			if image:
				width = image.size().width()
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, self.height), png=image))
			else:
				width = self.width
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, self.height), png=self.keyBackgrounds.get(key.split("__")[0], self.key_bg)))
				if "__" in key:
					key = key.split("__")[1] if not "__HIDE" in key else u""
				if len(key) > 1:  # NOTE: UTF8 / Unicode glyphs only count as one character here.
					text.append(MultiContentEntryText(pos=(x, 0), size=(width, self.height), font=1, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=_(key.encode("utf-8")), color=self.shiftColors[self.shiftLevel]))
				else:
					text.append(MultiContentEntryText(pos=(x, 0), size=(width, self.height), font=0, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=key.encode("utf-8"), color=self.shiftColors[self.shiftLevel]))

			x += width
		return res + text

	def markSelectedKey(self):
		for key in self.previousSelectedKey:
			self.list[key] = self.list[key][:-1]
		self.previousSelectedKey = []
		if self.selectedKey > self.maxKey:
			self.selectedKey = self.maxKey
		selectedKeyboardKey = self.selectedKey / self.keyboardWidth
		selectedKeyModulus = self.selectedKey % self.keyboardWidth
		if "__" not in self.keyList[self.shiftLevel][selectedKeyboardKey][selectedKeyModulus]:
			x = self.list[selectedKeyboardKey][selectedKeyModulus + 1][1]
			self.list[selectedKeyboardKey].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(self.key_sel_width, self.height), png=self.key_sel))
			self.previousSelectedKey.append(selectedKeyboardKey)
		else:
			selectedKeyShift = self.selectedKey
			while True:
				selectedKeyboardKey = selectedKeyShift / self.keyboardWidth
				selectedKeyModulus = selectedKeyShift % self.keyboardWidth
				selectedBg = self.keyList[self.shiftLevel][selectedKeyboardKey][selectedKeyModulus].split("__")[0]
				x = self.list[selectedKeyboardKey][selectedKeyModulus + 1][1]
				if selectedBg == "LongL":
					self.list[selectedKeyboardKey].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(self.key_sel_width, self.height), png=self.key_longl_sel))
					self.previousSelectedKey.append(selectedKeyboardKey)
					break
				elif selectedBg == "LongM":
					self.list[selectedKeyboardKey].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(self.key_sel_width, self.height), png=self.key_longm_sel))
					self.previousSelectedKey.append(selectedKeyboardKey)
				selectedKeyShift -= 1
				if selectedKeyShift < 0:
					break
			selectedKeyShift = self.selectedKey
			while True:
				selectedKeyboardKey = selectedKeyShift / self.keyboardWidth
				selectedKeyModulus = selectedKeyShift % self.keyboardWidth
				selectedBg = self.keyList[self.shiftLevel][selectedKeyboardKey][selectedKeyModulus].split("__")[0]
				x = self.list[selectedKeyboardKey][selectedKeyModulus + 1][1]
				if selectedBg == "LongR":
					self.list[selectedKeyboardKey].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(self.key_sel_width, self.height), png=self.key_longr_sel))
					self.previousSelectedKey.append(selectedKeyboardKey)
					break
				elif selectedBg == "LongM" and selectedKeyShift > self.selectedKey:
					self.list[selectedKeyboardKey].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(self.key_sel_width, self.height), png=self.key_longm_sel))
					self.previousSelectedKey.append(selectedKeyboardKey)
				selectedKeyShift += 1
				if selectedKeyShift > self.maxKey:
					break
		self["list"].setList(self.list)

	def processSelect(self):
		self.smsChar = None
		text = self.keyList[self.shiftLevel][self.selectedKey / self.keyboardWidth][self.selectedKey % self.keyboardWidth].encode("UTF-8")
		upperText = text.upper()
		if "__" in upperText:
			upperText = upperText.split("__")[1]
		if text == u"":
			pass
		elif upperText == u"ALL":
			self["text"].markAll()
		elif upperText == u"BACK":
			self["text"].deleteBackward()
		elif upperText == u"BACKSPACE":
			self["text"].deleteBackward()
		elif upperText == u"BLANK":
			pass
		elif upperText == u"CLR":
			self["text"].deleteAllChars()
			self["text"].update()
		elif upperText == u"DEL":
			self["text"].deleteForward()
		elif upperText == u"ENTER":
			self.enter()
		elif upperText == u"ESC":
			self.cancel()
		elif upperText == u"EXIT":
			self.cancel()
		elif upperText == u"FIRST":
			self["text"].home()
		elif upperText == u"LOC":
			self.localeMenu()
		elif upperText == u"LAST":
			self["text"].end()
		elif upperText == u"LEFT":
			self["text"].left()
		elif upperText == u"OK":
			self.enter()
		elif upperText == u"RIGHT":
			self["text"].right()
		elif upperText == u"ENTER":
			self.enter()
		elif upperText == u"SHIFT":
			self.shiftClicked()
		elif upperText == u"Shift":
			self.shiftClicked()
		elif upperText == u"SPACE":
			self["text"].char(" ".encode("UTF-8"))
		else:
			self["text"].char(text.encode("UTF-8"))

	def cancel(self):
		self.close(None)

	def save(self):  # Deprecated legacy interface to new enter
		self.enter()

	def enter(self):
		self.close(self["text"].getText())

	def localeMenu(self):
		languages = []
		for locale, data in self.locales.iteritems():
			languages.append((data[0] + "  -  " + data[1] + "  (" + locale + ")", locale))
		languages = sorted(languages)
		index = 0
		default = 0
		for item in languages:
			if item[1] == self.lang:
				default = index
				break
			index += 1
		self.session.openWithCallback(self.localeMenuCallback, ChoiceBox, _("Available locales are:"), list=languages, selection=default, keys=[])

	def localeMenuCallback(self, choice):
		if choice:
			self.lang = choice[1]
			self.setLocale()
			self.buildVirtualKeyBoard()

	def shiftClicked(self):
		self.smsChar = None
		self.shiftLevel = (self.shiftLevel + 1) % self.shiftLevels
		nextLevel = (self.shiftLevel + 1) % self.shiftLevels
		self["key_blue"].setText(self.shiftMsgs[nextLevel])
		self.buildVirtualKeyBoard()

	def keyToggleOW(self):
		self["text"].toggleOverwrite()
		self.overwrite = not self.overwrite
		if self.overwrite:
			self["mode"].setText(_("OVR"))
		else:
			self["mode"].setText(_("INS"))

	def backClicked(self):
		self["text"].deleteBackward()

	def forwardClicked(self):
		self["text"].deleteForward()

	def cursorFirst(self):
		self["text"].home()

	def cursorLeft(self):
		self["text"].left()

	def cursorRight(self):
		self["text"].right()

	def cursorLast(self):
		self["text"].end()

	def up(self):
		self.smsChar = None
		self.selectedKey -= self.keyboardWidth
		if self.selectedKey < 0:
			self.selectedKey = self.maxKey / self.keyboardWidth * self.keyboardWidth + self.selectedKey % self.keyboardWidth
			if self.selectedKey > self.maxKey:
				self.selectedKey -= self.keyboardWidth
		self.markSelectedKey()

	def left(self):
		self.smsChar = None
		selectedKeyboardKey = self.selectedKey / self.keyboardWidth
		self.selectedKey = selectedKeyboardKey * self.keyboardWidth + (self.selectedKey + self.keyboardWidth - 1) % self.keyboardWidth
		if self.selectedKey > self.maxKey:
			self.selectedKey = self.maxKey
		selectedBg = self.keyList[self.shiftLevel][selectedKeyboardKey][self.selectedKey % self.keyboardWidth].split("__")[0]
		if self.selectedKey < self.maxKey and selectedBg == "LongM" or selectedBg == "LongL":
			self.left()
		else:
			self.markSelectedKey()

	def right(self):
		self.smsChar = None
		selectedKeyboardKey = self.selectedKey / self.keyboardWidth
		self.selectedKey = selectedKeyboardKey * self.keyboardWidth + (self.selectedKey + 1) % self.keyboardWidth
		if self.selectedKey > self.maxKey:
			self.selectedKey = selectedKeyboardKey * self.keyboardWidth
		selectedBg = self.keyList[self.shiftLevel][selectedKeyboardKey][self.selectedKey % self.keyboardWidth].split("__")[0]
		if self.selectedKey > 0 and selectedBg == "LongM" or selectedBg == "LongR":
			self.right()
		else:
			self.markSelectedKey()

	def down(self):
		self.smsChar = None
		self.selectedKey += self.keyboardWidth
		if self.selectedKey > self.maxKey:
			self.selectedKey %= self.keyboardWidth
		self.markSelectedKey()

	def keyNumberGlobal(self, number):
		self.smsChar = self.sms.getKey(number)
		self.selectAsciiKey(self.smsChar)

	def keyGotAscii(self):
		self.smsChar = None
		if self.selectAsciiKey(str(unichr(getPrevAsciiCode()).encode("utf-8"))):
			self.processSelect()

	def selectAsciiKey(self, char):
		if char == u" ":
			char = u"SPACE"
		self.shiftLevel = -1
		for keyList in (self.keyList):
			self.shiftLevel = (self.shiftLevel + 1) % self.shiftLevels
			self.buildVirtualKeyBoard()
			selkey = 0
			for keys in keyList:
				for key in keys:
					if key == char:
						self.selectedKey = selkey
						self.markSelectedKey()
						return True
					selkey += 1
		return False
