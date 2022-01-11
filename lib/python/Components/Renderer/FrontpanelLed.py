from Components.Element import Element

# this is not a GUI renderer.

#                      |  two leds  | single led |
# recordstate  standby   red green
#    false      false    off   on     off
#    true       false    blnk  on     blnk
#    false      true      on   off    off
#    true       true     blnk  off    blnk
PATTERN_ON = (20, 0xffffffff, 0xffffffff)
PATTERN_OFF = (20, 0, 0)
PATTERN_BLINK = (20, 0x55555555, 0xa7fccf7a)


class LedPatterns():
	def __init__(self):
		self.__led0_patterns = [PATTERN_OFF, PATTERN_BLINK, PATTERN_ON, PATTERN_BLINK]
		self.__led1_patterns = [PATTERN_ON, PATTERN_ON, PATTERN_OFF, PATTERN_OFF]

	def setLedPatterns(self, which, patterns):
		if which == 0:
			self.__led0_patterns = patterns
		else:
			self.__led1_patterns = patterns

	def getLedPatterns(self, which):
		if which == 0:
			return self.__led0_patterns
		return self.__led1_patterns


ledPatterns = LedPatterns()


class FrontpanelLed(Element):
	def __init__(self, which=0, patterns=[PATTERN_ON, PATTERN_BLINK], boolean=True, get_patterns=None):
		self.which = which
		self.boolean = boolean
		self.patterns = get_patterns if get_patterns else patterns
		Element.__init__(self)

	def changed(self, *args, **kwargs):
		if self.boolean:
			val = self.source.boolean and 0 or 1
		else:
			val = self.source.value

		(speed, pattern, pattern_4bit) = self.patterns[val] if self.patterns != True else ledPatterns.getLedPatterns(self.which)[val]

		try:
			open("/proc/stb/fp/led%d_pattern" % self.which, "w").write("%08x" % pattern)
		except IOError:
			pass
		if self.which == 0:
			try:
				open("/proc/stb/fp/led_set_pattern", "w").write("%08x" % pattern_4bit)
				open("/proc/stb/fp/led_set_speed", "w").write("%d" % speed)
			except IOError:
				pass
			try:
				open("/proc/stb/fp/led_pattern_speed", "w").write("%d" % speed)
			except IOError:
				pass
