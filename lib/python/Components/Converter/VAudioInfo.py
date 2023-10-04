from enigma import iPlayableService
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll

class VAudioInfo(Poll, Converter, object):
	GET_AUDIO_ICON = 0
	GET_AUDIO_CODEC = 1

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type
		self.poll_interval = 1000
		self.poll_enabled = True
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
		languages = languages.replace("und ", "")
		return languages

	def getAudioCodec(self,service):
		description_str = _("unknown")
		audio = service.audioTracks()
		if audio:
			currentTrack = audio.getCurrentTrack()
			if currentTrack != -1:
				i = audio.getTrackInfo(currentTrack)
				description = i.getDescription()
				return description
			else:
				return "NO"
		return description_str

	def getAudioIcon(self,service):
		description_str = self.getAudioCodec(service).lower()
		return description_str

	def get_short(self, audioName):
		return audioName

	@cached
	def getText(self):
		service = self.source.service
		if service:
			info = service and service.info()
			if info:
				if self.type == self.GET_AUDIO_CODEC:
					return self.getAudioCodec(service)
				if self.type == self.GET_AUDIO_ICON:
					return self.getAudioIcon(service)
		return _("invalid type")

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
