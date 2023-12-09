# copied from OpenViX

from enigma import iPlayableService

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached

# Common function to standardize the display of Audio Codecs
# _acedits is a list of text conversions (from, to) that are done in the
# order given.
#
_acedits = (
	("A_", ""),
	("AC-3", "AC3"),
	("(ATSC A/52)", ""),
	("(ATSC A/52B)", ""),
	(" Layer 2 (MP2)", ""),
	(" Layer 3 (MP3)", "MP3"),
	("-1", ""),
	("-2", ""),
	("2-", ""),
	("-4 AAC", "AAC"),
	("4-AAC", "HE-AAC"),
	("audio", ""),
	("/L3", ""),
	("/mpeg", "AAC"),
	("/x-", ""),
	("raw", "Dolby TrueHD"),
	("E-AC3", "AC3+"),
	("EAC3", "AC3+"),
	("IPCM", "AC3"),
	("LPCM", "AC3+"),
	("AAC_PLUS", "AAC+"),
	("AAC_LATM", "AAC"),
	("WMA/PRO", "WMA Pro"),
	("MPEG", "MPEG1 Layer II"),
	("MPEG1 Layer II AAC", "AAC"),
	("MPEG1 Layer IIAAC", "AAC"),
	("MPEG1 Layer IIMP3", "MP3"),
)


def StdAudioDesc(description):
	for orig, repl in _acedits:
		description = description.replace(orig, repl)
	return description


class VAudioInfo(Poll, Converter, object):
	GET_AUDIO_ICON = 0
	GET_AUDIO_CODEC = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type
		self.poll_interval = 1000
		self.poll_enabled = True
		self.lang_strings = ("english", "englisch", "eng")
		self.codecs = {
			"01_dolbydigitalplus": ("digital+", "digitalplus", "ac3+",),
			"02_dolbydigital": ("ac3", "dolbydigital",),
			"03_mp3": ("mp3",),
			"04_wma": ("wma",),
			"05_flac": ("flac",),
			"06_he-aac": ("he-aac",),
			"07_aac": ("aac",),
			"08_lpcm": ("lpcm",),
			"09_dts-hd": ("dts-hd",),
			"10_dts": ("dts",),
			"11_pcm": ("pcm",),
			"12_mpeg": ("mpeg",),
			"13_dolbytruehd": ("truehd",),
			"14_aacplus": ("aac+",),
			"15_ipcm": ("ipcm",),
			"16_wma-pro": ("wma pro",),
			"17_vorbis": ("vorbis",),
			"18_opus": ("opus",),
			"19_amr": ("amr",),
		}
		self.codec_info = {
			"dolbytruehd": ("51", "20", "71"),
			"dolbydigitalplus": ("51", "20", "71"),
			"dolbydigital": ("51", "20", "71"),
			"wma": ("8", "9"),
		}
		self.type, self.interesting_events = {
			"AudioIcon": (self.GET_AUDIO_ICON, (iPlayableService.evUpdatedInfo,)),
			"AudioCodec": (self.GET_AUDIO_CODEC, (iPlayableService.evUpdatedInfo,)),
		}[type]

	def getAudio(self):
		service = self.source.service
		audio = service.audioTracks()
		if audio:
			self.current_track = audio.getCurrentTrack()
			self.number_of_tracks = audio.getNumberOfTracks()
			if self.number_of_tracks > 0 and self.current_track > -1:
				self.audio_info = audio.getTrackInfo(self.current_track)
				return True
		return False

	def getLanguage(self):
		languages = self.audio_info.getLanguage()
		for lang in self.lang_strings:
			if lang in languages:
				languages = "English"
				break
		languages = languages.replace("und", "")
		return languages

	def getAudioCodec(self, info):
		description_str = _("N/A")
		if self.getAudio():
			languages = self.getLanguage()
			description = StdAudioDesc(self.audio_info.getDescription()) or ""
			description_str = description.split(" ")
			if len(description_str) and description_str[0] in languages:
				return languages
			if description.lower() in languages.lower():
				languages = ""
			description_str = description
		return description_str

	def getAudioIcon(self, info):
		description_str = self.get_short(self.getAudioCodec(info).translate(str.maketrans('  ', ' .')).lower())
		return description_str

	def get_short(self, audioName):
		for return_codec, codecs in sorted(self.codecs.items()):
			for codec in codecs:
				if codec in audioName:
					codec = return_codec.split('_')[1]
					if codec in self.codec_info:
						for ex_codec in self.codec_info[codec]:
							if ex_codec in audioName:
								codec += ex_codec
								break
					return codec
		return audioName

	@cached
	def getText(self):
		service = self.source.service
		if service:
			info = service and service.info()
			if info:
				if self.type == self.GET_AUDIO_CODEC:
					return self.getAudioCodec(info)
				if self.type == self.GET_AUDIO_ICON:
					return self.getAudioIcon(info)
		return _("invalid type")

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
