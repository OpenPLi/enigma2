from enigma import eTimer

from Components.Language import language

MAP_SEARCH_UPCASE = "SearchUpper"  # NOTE: Legacy interface for previous and deprecated versions of NumericalTextInput.
MAP_SEARCH = "SearchLower"

MODES = {
	"DEFAULT": 0,
	"DEFAULTUPPER": 1,
	"DEFAULTLOWER": 2,
	"HEX": 6,
	"HEXUPPER": 7,
	"HEXLOWER": 8,
	"HEXFAST": 9,
	"HEXFASTUPPER": 10,
	"HEXFASTLOWER": 11,
	"HEXFASTLOGICAL": 12,
	"HEXFASTLOGICALUPPER": 13,
	"HEXFASTLOGICALLOWER": 14,
	"SEARCH": 3,
	"SEARCHUPPER": 4,
	"SEARCHLOWER": 5
}

PUNCTUATION0 = u"0,?!'\"\\()<>[]{}~^`|"
PUNCTUATION1 = u"1 .:;+-*/=_@#$%&"

MAPPINGS = (
	# Text, TextUpper, TextLower, Search, SearchUpper, SearchLower, Hex, HexUpper, HexLower, HexFast, HexFastUpper, HexFastLower, HexLogical, HexLogicalUpper, HexLogicalLower
	(PUNCTUATION0, PUNCTUATION0, PUNCTUATION0, u"%_0", u"%_0", u"%_0", u"0", u"0", u"0", u"0", u"0", u"0", u"0Aa", u"0A", u"0a"),
	(PUNCTUATION1, PUNCTUATION1, PUNCTUATION1, u" 1", u" 1", u" 1", u"1AaBbCc", u"1ABC", u"1abc", u"1Aa", u"1A", u"1a", u"1Bb", u"1B", u"1b"),
	(u"abc2ABC", u"ABC2", u"abc2", u"abc2ABC", u"ABC2", u"abc2", u"2DdEeFf", u"2DEF", u"2def", u"2Bb", u"2B", u"2b", u"2Cc", u"2C", u"2c"),
	(u"def3DEF", u"DEF3", u"def3", u"def3DEF", u"DEF3", u"def3", u"3", u"3", u"3", u"3Cc", u"3C", u"3c", u"3Dd", u"3D", u"3d"),
	(u"ghi4GHI", u"GHI4", u"ghi4", u"ghi4GHI", u"GHI4", u"ghi4", u"4", u"4", u"4", u"4Dd", u"4D", u"4d", u"4Ee", u"4E", u"4e"),
	(u"jkl5JKL", u"JKL5", u"jkl5", u"jkl5JKL", u"JKL5", u"jkl5", u"5", u"5", u"5", u"5Ee", u"5E", u"5e", u"5Ff", u"5F", u"5f"),
	(u"mno6MNO", u"MNO6", u"mno6", u"mno6MNO", u"MNO6", u"mno6", u"6", u"6", u"6", u"6Ff", u"6F", u"6f", u"6", u"6", u"6"),
	(u"pqrs7PQRS", u"PQRS7", u"pqrs7", u"pqrs6PQRS", u"PQRS7", u"pqrs7", u"7", u"7", u"7", u"7", u"7", u"7", u"7", u"7", u"7"),
	(u"tuv8TUV", u"TUV8", u"tuv8", u"tuv8TUV", u"TUV8", u"tuv8", u"8", u"8", u"8", u"8", u"8", u"8", u"8", u"8", u"8"),
	(u"wxyz9WXYZ", u"WXYZ9", u"wxyz9", u"wxyz9WXYZ", u"WXYZ9", u"wxyz9", u"9", u"9", u"9", u"9", u"9", u"9", u"9", u"9", u"9")
)

LOCALE_SE = (
	(u"abc\u00E5\u00E42ABC\u00C5\u00C4", u"ABC\u00C5\u00C42", u"abc\u00E5\u00E42"),
	(u"def\u00E93DEF\u00C9", u"DEF\u00C93", u"def\u00E93"),
	(None, None, None),
	(None, None, None),
	(u"mno\u00F66MNO\u00D6", u"MNO\u00D66", u"mno\u00F66"),
	(None, None, None),
	(None, None, None),
	(None, None, None)
)

LOCALES = {
	"cs_CZ": (
		(u"abc\u00E1\u010D2ABC\u00C1\u010C", u"ABC\u00C1\u010C2", u"abc\u00E1\u010D2"),
		(u"def\u010F\u00E9\u011B3DEF\u010E\u00C9\u011A", u"DEF\u010E\u00C9\u011A3", u"def\u010F\u00E9\u011B3"),
		(u"ghi\u00ED4GHI\u00CD", u"GHI\u00CD4", u"ghi\u00ED4"),
		(None, None, None),
		(u"mno\u0148\u00F36MNO\u0147\u00D3", u"MNO\u0147\u00D36", u"mno\u0148\u00F36"),
		(u"pqrs\u0159\u01617PQRS\u0158\u0160", u"PQRS\u0158\u01607", u"pqrs\u0159\u01617"),
		(u"tuv\u0165\u00FA\u016F8TUV\u0164\u00DA\u016E", u"TUV\u0164\u00DA\u016E8", u"tuv\u0165\u00FA\u016F8"),
		(u"wxyz\u00FD\u017E9WXYZ\u00DD\u017D", u"WXYZ\u00DD\u017D9", u"wxyz\u00FD\u017E9")
	),
	"de_DE": (
		(u"abc\u00E42ABC\u00C4", u"ABC\u00C42", u"abc\u00E42"),
		(None, None, None),
		(None, None, None),
		(None, None, None),
		(u"mno\u00F66MNO\u00D6", u"MNO\u00D66", u"mno\u00F66"),
		(u"pqrs\u00DF7PQRS\u00DF", u"PQRS\u00DF7", u"pqrs\u00DF7"),
		(u"tuv\u00FC8TUV\u00DC", u"TUV\u00DC8", u"tuv\u00FC8"),
		(None, None, None)
	),
	"es_ES": (
		(u"abc\u00E1\u00E02ABC\u00C1\u00C0", u"ABC\u00C1\u00C02", u"abc\u00E1\u00E02"),
		(u"def\u00E9\u00E83DEF\u00C9\u00C8", u"DEF\u00C9\u00C83", u"def\u00E9\u00E83"),
		(u"ghi\u00ED\u00EC4GHI\u00CD\u00CC", u"GHI\u00CD\u00CC4", u"ghi\u00ED\u00EC4"),
		(None, None, None),
		(u"mno\u00F1\u00F3\u00F26MNO\u00D1\u00D3\u00D2", u"MNO\u00D1\u00D3\u00D26", u"mno\u00F1\u00F3\u00F26"),
		(None, None, None),
		(u"tuv\u00FA\u00F98TUV\u00DA\u00D9", u"TUV\u00DA\u00D98", u"tuv\u00FA\u00F98"),
		(None, None, None)
	),
	"et_EE": (
		(u"abc\u00E42ABC\u00C4", u"ABC\u00C42", u"abc\u00E42"),
		(None, None, None),
		(None, None, None),
		(None, None, None),
		(u"mno\u00F5\u00F66MNO\u00D5\u00D6", u"MNO\u00D5\u00D66", u"mno\u00F5\u00F66"),
		(u"pqrs\u01617PQRS\u0160", u"PQRS\u01607", u"pqrs\u01617"),
		(u"tuv\u00FC8TUV\u00DC", u"TUV\u00DC8", u"tuv\u00FC8"),
		(u"wxyz\u017E9WXYZ\u017D", u"WXYZ\u017D9", u"wxyz\u017E9")
	),
	"fi_FI": LOCALE_SE,
	"lv_LV": (
		(u"abc\u0101\u010D2ABC\u0100\u010C", u"ABC\u0100\u010C2", u"abc\u0101\u010D2"),
		(u"def\u01133DEF\u0112", u"DEF\u01123", u"def\u01133"),
		(u"ghi\u0123\u012B4GHI\u0122\u012A", u"GHI\u0122\u012A4", u"ghi\u0123\u012B4"),
		(u"jkl\u0137\u013C5JKL\u0136\u013B", u"JKL\u0136\u013B5", u"jkl\u0137\u013C5"),
		(u"mno\u01466MNO\u0145", u"MNO\u01456", u"mno\u01466"),
		(u"pqrs\u01617PQRS\u0160", u"PQRS\u01607", u"pqrs\u01617"),
		(u"tuv\u016B8TUV\u016A", u"TUV\u016A8", u"tuv\u016B8"),
		(u"wxyz\u017E9WXYZ\u017D", u"WXYZ\u017D9", u"wxyz\u017E9")
	),
	"nl_NL": (
		(None, None, None),
		(u"def\u00EB3DEF\u00CB", u"DEF\u00CB3", u"def\u00EB3"),
		(u"ghi\u00EF4GHI\u00CF", u"GHI\u00CF4", u"ghi\u00EF4"),
		(None, None, None),
		(None, None, None),
		(None, None, None),
		(None, None, None),
		(None, None, None),
	),
	"pl_PL": (
		(u"abc\u0105\u01072ABC\u0104\u0106", u"ABC\u0104\u01062", u"abc\u0105\u01072"),
		(u"def\u01193DEF\u0118", u"DEF\u01183", u"def\u01193"),
		(None, None, None),
		(u"jkl\u01425JKL\u0141", u"JKL\u01415", u"jkl\u01425"),
		(u"mno\u0144\u00F36MNO\u0143\u00D3", u"MNO\u0143\u00D36", u"mno\u0144\u00F36"),
		(u"pqrs\u015B7PQRS\u015A", u"PQRS\u015A7", u"pqrs\u015B7"),
		(None, None, None),
		(u"wxyz\u017A\u017C9WXYZ\u0179\u017B", u"WXYZ\u0179\u017B9", u"wxyz\u017A\u017C9")
	),
	"ru_RU": (
		(u"abc\u0430\u0431\u0432\u04332ABC\u0410\u0411\u0412\u0413", u"ABC\u0410\u0411\u0412\u04132", u"abc\u0430\u0431\u0432\u04332"),
		(u"def\u0434\u0435\u0436\u04373DEF\u0414\u0415\u0416\u0417", u"DEF\u0414\u0415\u0416\u04173", u"def\u0434\u0435\u0436\u04373"),
		(u"ghi\u0438\u0439\u043A\u043B4GHI\u0418\u0419\u041A\u041B", u"GHI\u0418\u0419\u041A\u041B4", u"ghi\u0438\u0439\u043A\u043B4"),
		(u"jkl\u043C\u043D\u043E\u043F5JKL\u041C\u041D\u041E\u041F", u"JKL\u041C\u041D\u041E\u041F5", u"jkl\u043C\u043D\u043E\u043F5"),
		(u"mno\u0440\u0441\u0442\u04436MNO\u0420\u0421\u0422\u0423", u"MNO\u0420\u0421\u0422\u04236", u"mno\u0440\u0441\u0442\u04436"),
		(u"pqrs\u0444\u0445\u0446\u04477PQRS\u0424\u0425\u0426\u0427", u"PQRS\u0424\u0425\u0426\u04277", u"pqrs\u0444\u0445\u0446\u04477"),
		(u"tuv\u0448\u0449\u044C\u044B8TUV\u0428\u0429\u042C\u042B", u"TUV\u0428\u0429\u042C\u042B8", u"tuv\u0448\u0449\u044C\u044B8"),
		(u"wxyz\u044A\u044D\u044E\u044F9WXYZ\u042A\u042D\u042E\u042F", u"WXYZ\u042A\u042D\u042E\u042F9", u"wxyz\u044A\u044D\u044E\u044F9")
	),
	"sv_SE": LOCALE_SE,
	"sk_SK": (
		(u"abc\u00E1\u00E4\u010D2ABC\u00C1\u00C4\u010C", u"ABC\u00C1\u00C4\u010C2", u"abc\u00E1\u00E4\u010D2"),
		(u"def\u010F\u00E9\u011B3DEF\u010E\u00C9\u011A", u"DEF\u010E\u00C9\u011A3", u"def\u010F\u00E9\u011B3"),
		(u"ghi\u00ED4GHI\u00CD", u"GHI\u00CD4", u"ghiGHI\u00CD4"),
		(u"jkl\u013E\u013A5JKL\u013D\u0139", u"JKL\u013D\u01395", u"jkl\u013E\u013A5"),
		(u"mno\u0148\u00F3\u00F6\u00F46MNO\u0147\u00D3\u00D6\u00D4", u"MNO\u0147\u00D3\u00D6\u00D46", u"mno\u0148\u00F3\u00F6\u00F46"),
		(u"pqrs\u0159\u0155\u01617PQRS\u0158\u0154\u0160", u"PQRS\u0158\u0154\u01607", u"pqrs\u0159\u0155\u01617"),
		(u"tuv\u0165\u00FA\u016F\u00FC8TUV\u0164\u00DA\u016E\u00DC", u"TUV\u0164\u00DA\u016E\u00DC8", u"tuv\u0165\u00FA\u016F\u00FC8"),
		(u"wxyz\u00FD\u017E9WXYZ\u00DD\u017D", u"WXYZ\u00DD\u017D9", u"wxyz\u00FD\u017E9")
	),
	"uk_UA": (
		(u"abc\u0430\u0431\u0432\u0433\u04912ABC\u0410\u0411\u0412\u0413\u0490", u"ABC\u0410\u0411\u0412\u0413\u04902", u"abc\u0430\u0431\u0432\u0433\u04912"),
		(u"def\u0434\u0435\u0454\u0436\u04373DEF\u0414\u0415\u0404\u0416\u0417", u"DEF\u0414\u0415\u0404\u0416\u04173", u"def\u0434\u0435\u0454\u0436\u04373"),
		(u"ghi\u0438\u0456\u0457\u04394GHI\u0418\u0406\u0407\u0419", u"GHI\u0418\u0406\u0407\u04194", u"ghi\u0438\u0456\u0457\u04394"),
		(u"jkl\u043A\u043B\u043C\u043D5JKL\u041A\u041B\u041C\u041D", u"JKL\u041A\u041B\u041C\u041D5", u"jkl\u043A\u043B\u043C\u043D5"),
		(u"mno\u043E\u043F\u0440\u04416MNO\u041E\u041F\u0420\u0421", u"MNO\u041E\u041F\u0420\u04216", u"mno\u043E\u043F\u0440\u04416"),
		(u"pqrs\u0442\u0443\u0444\u04457PQRS\u0422\u0423\u0424\u0425", u"PQRS\u0422\u0423\u0424\u04257", u"pqrs\u0442\u0443\u0444\u04457"),
		(u"tuv\u0446\u0447\u0448\u04498TUV\u0426\u0427\u0428\u0429", u"TUV\u0426\u0427\u0428\u04298", u"tuv\u0446\u0447\u0448\u04498"),
		(u"wxyz\u044C\u044E\u044F9WXYZ\u042C\u042E\u042F", u"WXYZ\u042C\u042E\u042F9", u"wxyz\u044C\u044E\u044F9")
	)
}


# For more information about using NumericalTextInput see /doc/NUMERICALTEXTINPUT
#
class NumericalTextInput:
	def __init__(self, nextFunc=None, handleTimeout=True, search=False, mapping=None, mode=None):
		self.nextFunction = nextFunc
		if handleTimeout:
			self.timer = eTimer()
			self.timer.callback.append(self.timeout)
		else:
			self.timer = None
		if mapping and isinstance(mapping, (list, tuple)):
			self.mapping = mapping
		else:
			if mode is None:
				if search:  # NOTE: This will be removed when deprecated "search" is removed and "mode" is widely adopted.
					mode = "Search"
				if isinstance(mapping, str):  # NOTE: Legacy interface for previous and deprecated versions of NumericalTextInput.
					mode = mapping
			self.mapping = []
			index = MODES.get(str(mode).upper(), 0)
			self.mapping = []
			for num in range(0, 10):
				self.mapping.append((MAPPINGS[num][index]))
			locale = LOCALES.get(language.getLanguage(), None)
			if locale is not None and index in range(0, 6):
				index = index % 3
				for num in range(2, 10):
					if locale[num - 2][index] is not None:
						self.mapping[num] = locale[num - 2][index]
			self.mapping = tuple(self.mapping)
		self.useableChars = None
		self.lastKey = -1
		self.pos = -1

	def timeout(self):
		if self.lastKey != -1:
			self.nextChar()

	def nextChar(self):
		self.nextKey()
		if self.nextFunction:
			self.nextFunction()

	def nextKey(self):
		if self.timer is not None:
			self.timer.stop()
		self.lastKey = -1

	def getKey(self, num):
		if self.lastKey != num:
			if self.lastKey != -1:
				self.nextChar()
			self.lastKey = num
			self.pos = -1
		if self.timer is not None:
			self.timer.start(1000, True)
		length = len(self.mapping[num])
		cnt = length
		while True:
			self.pos += 1
			if self.pos >= length:
				self.pos = 0
			if not self.useableChars or self.useableChars.find(self.mapping[num][self.pos]) != -1:
				break
			cnt -= 1
			if cnt == 0:
				return None
		return self.mapping[num][self.pos]

	def setUseableChars(self, useable):
		self.useableChars = unicode(useable)
