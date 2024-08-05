from copy import copy as copy_copy
from os import fsync, path as os_path, rename, sep
from time import localtime, strftime, mktime

from enigma import getPrevAsciiCode
from Tools.Directories import fileExists, resolveFilename, SCOPE_CONFIG
from Tools.NumericalTextInput import NumericalTextInput
from Components.Harddisk import harddiskmanager

ACTIONKEY_LEFT = 0
ACTIONKEY_RIGHT = 1
ACTIONKEY_SELECT = 2
ACTIONKEY_DELETE = 3
ACTIONKEY_BACKSPACE = 4
ACTIONKEY_FIRST = 5
ACTIONKEY_LAST = 6
ACTIONKEY_TOGGLE = 7
ACTIONKEY_ASCII = 8
ACTIONKEY_TIMEOUT = 9
ACTIONKEY_0 = 12
ACTIONKEY_1 = 13
ACTIONKEY_2 = 14
ACTIONKEY_3 = 15
ACTIONKEY_4 = 16
ACTIONKEY_5 = 17
ACTIONKEY_6 = 18
ACTIONKEY_7 = 19
ACTIONKEY_8 = 20
ACTIONKEY_9 = 21
ACTIONKEY_NUMBERS = [ACTIONKEY_0, ACTIONKEY_1, ACTIONKEY_2, ACTIONKEY_3, ACTIONKEY_4, ACTIONKEY_5, ACTIONKEY_6, ACTIONKEY_7, ACTIONKEY_8, ACTIONKEY_9]
ACTIONKEY_PAGEUP = 22
ACTIONKEY_PAGEDOWN = 23
ACTIONKEY_PREV = 24
ACTIONKEY_NEXT = 25
ACTIONKEY_ERASE = 26

# Deprecated / Legacy action key names...
#
KEY_LEFT = ACTIONKEY_LEFT
KEY_RIGHT = ACTIONKEY_RIGHT
KEY_OK = ACTIONKEY_SELECT
KEY_DELETE = ACTIONKEY_DELETE
KEY_BACKSPACE = ACTIONKEY_BACKSPACE
KEY_HOME = ACTIONKEY_FIRST
KEY_END = ACTIONKEY_LAST
KEY_TOGGLEOW = ACTIONKEY_TOGGLE
KEY_ASCII = ACTIONKEY_ASCII
KEY_TIMEOUT = ACTIONKEY_TIMEOUT
KEY_NUMBERS = ACTIONKEY_NUMBERS
KEY_0 = ACTIONKEY_0
KEY_9 = ACTIONKEY_9


# ConfigElement, the base class of all ConfigElements.
#
# ConfigElement stores:
#   value       The current value, usually encoded.
#               A property which retrieves _value, and maybe does some reformatting.
#   _value      A value to be saved in the configfile, though still in non-string form.
#               This is the object which is actually worked on.
#   default     The initial value. If _value is equal to default, it will not be stored in the config file
#   saved_value Is a text representation of _value, stored in the config file
#
# ConfigElement has (at least) the following methods:
#   load()   loads _value from saved_value, or 
#            loads the default if saved_value is 'None' (default) or invalid.
#   save()   stores _value into saved_value, or stores 'None' if it should not be stored.
#
class ConfigElement:
	def __init__(self):
		self.saved_value = None
		self.save_forced = False
		self.last_value = None
		self.save_disabled = False
		self.__notifiers = None
		self.__notifiers_final = None
		self.enabled = True
		self.callNotifiersOnSaveAndCancel = False  # this is here for compatibility only. Do not use.

	def getNotifiers(self):
		if self.__notifiers is None:
			self.__notifiers = []
		return self.__notifiers

	def setNotifiers(self, val):
		self.__notifiers = val

	notifiers = property(getNotifiers, setNotifiers)

	def getNotifiersFinal(self):
		if self.__notifiers_final is None:
			self.__notifiers_final = []
		return self.__notifiers_final

	def setNotifiersFinal(self, val):
		self.__notifiers_final = val

	notifiers_final = property(getNotifiersFinal, setNotifiersFinal)

	# you need to override this to do input validation
	def setValue(self, value):
		prev = self._value if hasattr(self, "_value") else None
		self._value = value
		if prev != value:
			self.changed()

	def getValue(self):
		return self._value

	value = property(getValue, setValue)

	# you need to override this if self.value is not a string
	def fromstring(self, value):
		return value

	# you can overide this for fancy default handling
	def load(self):
		sv = self.saved_value
		if sv is None:
			self.value = self.default
		else:
			self.value = self.fromstring(sv)
		self.last_value = self.tostring(self.value)

	def tostring(self, value):
		return str(value)

	def toDisplayString(self, value):
		return str(value)

	# you need to override this if str(self.value) doesn't work
	def save(self):
		if self.save_disabled or (self.value == self.default and not self.save_forced):
			self.saved_value = None
		else:
			self.saved_value = self.tostring(self.value)

		if self.last_value != self.tostring(self.value):
			self.last_value = self.tostring(self.value)
			self.changedFinal()

	def cancel(self):
		self.load()

	def isChanged(self):
		# NOTE - self.saved_value should already be stringified!
		#        self.default may be a string or None
		sv = self.saved_value or self.tostring(self.default)
		strv = self.tostring(self.value)
		return strv != sv

	def changed(self):
		if self.__notifiers:
			for x in self.notifiers:
				x(self)

	def changedFinal(self):
		if self.__notifiers_final:
			for x in self.notifiers_final:
				x(self)

	def addNotifier(self, notifier, initial_call=True, immediate_feedback=True):
		# "initial_call=True" triggers the notifier as soon as "addNotifier" is encountered in the code.
		#
		# "initial_call=False" skips the above activation of the notifier.
		#
		# "immediate_feedback=True" notifiers are called on every single change of the config item,
		# e.g. if going left/right through a ConfigSelection it will trigger on every step.
		#
		# "immediate_feedback=False" notifiers are called on ConfigElement.save() only.
		#
		# Use of the "self.callNotifiersOnSaveAndCancel" flag serves no purpose in the current code.
		#
		assert callable(notifier), "notifiers must be callable"
		if immediate_feedback:
			self.notifiers.append(notifier)
		else:
			self.notifiers_final.append(notifier)
		# CHECKME:
		# do we want to call the notifier
		#  - at all when adding it? (yes, though optional)
		#  - when the default is active? (yes)
		#  - when no value *yet* has been set,
		#    because no config has ever been read (currently yes)
		#    (though that's not so easy to detect.
		#     the entry could just be new.)
		if initial_call:
			notifier(self)

	def removeNotifier(self, notifier):
		notifier in self.notifiers and self.notifiers.remove(notifier)
		notifier in self.notifiers_final and self.notifiers_final.remove(notifier)
		try:
			del self.__notifiers[str(notifier)]
		except BaseException:
			pass
		try:
			del self.__notifiers_final[str(notifier)]
		except BaseException:
			pass

	def clearNotifiers(self):
		self.__notifiers = {}
		self.__notifiers_final = {}

	def disableSave(self):
		self.save_disabled = True

	def __call__(self, selected):
		return self.getMulti(selected)

	def onSelect(self, session):
		pass

	def onDeselect(self, session):
		pass

	def hideHelp(self, session):
		pass

	def showHelp(self, session):
		pass

def getKeyNumber(key):
	assert key in ACTIONKEY_NUMBERS
	return key - ACTIONKEY_0


class choicesList:  # XXX: we might want a better name for this
	LIST_TYPE_LIST = 1
	LIST_TYPE_DICT = 2

	def __init__(self, choices, type=None):
		self.choices = choices
		if type is None:
			if isinstance(choices, list):
				self.type = choicesList.LIST_TYPE_LIST
			elif isinstance(choices, dict):
				self.type = choicesList.LIST_TYPE_DICT
			else:
				assert False, "choices must be dict or list!"
		else:
			self.type = type

	def __list__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[0] for x in self.choices]
		else:
			ret = list(self.choices.keys())
		return ret or [""]

	def __iter__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[0] for x in self.choices]
		else:
			ret = self.choices
		return iter(ret or [""])

	def __len__(self):
		return len(self.choices) or 1

	def __getitem__(self, index):
		if index == 0 and not self.choices:
			return ""
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = self.choices[index]
			if isinstance(ret, tuple):
				ret = ret[0]
			return ret
		return list(self.choices.keys())[index]

	def index(self, value):
		try:
			return list(map(str, self.__list__())).index(str(value))
		except (ValueError, IndexError):
			# occurs e.g. when default is not in list
			return 0

	def __setitem__(self, index, value):
		if index == 0 and not self.choices:
			return
		if self.type == choicesList.LIST_TYPE_LIST:
			orig = self.choices[index]
			if isinstance(orig, tuple):
				self.choices[index] = (value, orig[1])
			else:
				self.choices[index] = value
		else:
			key = list(self.choices.keys())[index]
			orig = self.choices[key]
			del self.choices[key]
			self.choices[value] = orig

	def default(self):
		choices = self.choices
		if not choices:
			return ""
		if self.type is choicesList.LIST_TYPE_LIST:
			default = choices[0]
			if isinstance(default, tuple):
				default = default[0]
		else:
			default = list(choices.keys())[0]
		return default


class descriptionList(choicesList):  # XXX: we might want a better name for this
	def __list__(self):
		if self.type == choicesList.LIST_TYPE_LIST:
			ret = [not isinstance(x, tuple) and x or x[1] for x in self.choices]
		else:
			ret = list(self.choices.values())
		return ret or [""]

	def __iter__(self):
		return iter(self.__list__())

	def __getitem__(self, index):
		if self.type == choicesList.LIST_TYPE_LIST:
			for x in self.choices:
				if isinstance(x, tuple):
					if str(x[0]) == str(index):
						return str(x[1])
				elif str(x) == str(index):
					return str(x)
			return str(index)  # Fallback!
		else:
			return str(self.choices.get(index, ""))

	def __setitem__(self, index, value):
		if not self.choices:
			return
		if self.type == choicesList.LIST_TYPE_LIST:
			i = self.index(index)
			orig = self.choices[i]
			if isinstance(orig, tuple):
				self.choices[i] = (orig[0], value)
			else:
				self.choices[i] = value
		else:
			self.choices[index] = value

#
# ConfigSelection is a "one of.."-type.
# it has the "choices", usually a list, which contains
# (id, desc)-tuples (or just only the ids, in case the id
# will be used as description)
# ConfigSelection is a "one of.."-type.  it has the "choices", usually
# a list, which contains (id, desc)-tuples (or just only the ids, in
# case str(id) will be used as description)
#
# The ids in "choices" may be of any type, provided that for there
# is a one-to-one mapping between x and str(x) for every x in "choices".
# The ids do not necessarily all have to have the same type, but
# managing that is left to the programmer.  For example:
#  choices=[1, 2, "3", "4"] is permitted, but
#  choices=[1, 2, "1", "2"] is not,
# because str(1) == "1" and str("1") =="1", and because str(2) == "2"
# and str("2") == "2".
#
# This requirement is not enforced by the code.
#
# config.item.value and config.item.getValue always return an object
# of the type of the selected item.
#
# When assigning to config.item.value or using config.item.setValue,
# where x is in the "choices" list, either x or str(x) may be used
# to set the choice. The form of the assignment will not affect the
# choices list or the type returned by the ConfigSelection instance.
#
# This replaces the former requirement that all ids MUST be plain
# strings, but is compatible with that requirement.
#


class ConfigSelection(ConfigElement):
	def __init__(self, choices, default=None, graphic=True):
		ConfigElement.__init__(self)
		self.choices = choicesList(choices)

		if default is None:
			default = self.choices.default()

		self._descr = None
		self.default = self._value = default
		self.last_value = self.tostring(default)
		self.graphic = graphic

	def setChoices(self, choices, default=None):
		value = self.value
		self.choices = choicesList(choices)

		if default is None:
			default = self.choices.default()
		self.default = default

		if self.value not in self.choices:
			self.value = default
		if self.value != value:
			self.changed()

	def setValue(self, value):
		prev = str(self._value) if hasattr(self, "_value") else None
		if str(value) in map(str, self.choices):
			self._value = self.choices[self.choices.index(value)]
		else:
			self._value = self.default
		self._descr = None
		if prev != str(self._value):
			self.changed()

	def tostring(self, val):
		return str(val)

	def toDisplayString(self, val):
		return self.description[val]

	def getValue(self):
		return self._value

	def load(self):
		sv = self.saved_value
		if sv is None:
			self.value = self.default
		else:
			self.value = self.choices[self.choices.index(sv)]
		self.last_value = self.tostring(self.value)

	def setCurrentText(self, text):
		i = self.choices.index(self.value)
		self.choices[i] = text
		self._descr = self.description[text] = text
		self._value = text

	value = property(getValue, setValue)

	def getIndex(self):
		return self.choices.index(self.value)

	index = property(getIndex)

	# GUI
	def handleKey(self, key, callback=None):
		nchoices = len(self.choices)
		if nchoices > 1:
			prev = str(self.value)
			i = self.choices.index(self.value)
			if key == ACTIONKEY_LEFT:
				self.value = self.choices[(i + nchoices - 1) % nchoices]
			elif key == ACTIONKEY_RIGHT:
				self.value = self.choices[(i + 1) % nchoices]
			elif key == ACTIONKEY_FIRST:
				self.value = self.choices[0]
			elif key == ACTIONKEY_LAST:
				self.value = self.choices[nchoices - 1]
			if str(self.value) != prev and callable(callback):
				callback()

	def selectNext(self):
		nchoices = len(self.choices)
		i = self.choices.index(self.value)
		self.value = self.choices[(i + 1) % nchoices]

	def getText(self):
		if self._descr is None:
			self._descr = self.description[self.value]
		return self._descr

	def getMulti(self, selected):
		if self._descr is None:
			self._descr = self.description[self.value]
		from Components.config import config
		if self.graphic and config.usage.boolean_graphic.value == "true":
			from skin import switchPixmap
			if "menu_on" in switchPixmap and "menu_off" in switchPixmap:
				pixmap = "menu_on" if self._descr in (_('True'), _('true'), _('Yes'), _('yes'), _('Enable'), _('enable'), _('Enabled'), _('enabled'), _('On'), _('on')) else "menu_off" if self._descr in (_('False'), _('false'), _('No'), _('no'), _("Disable"), _('disable'), _('Disabled'), _('disabled'), _('Off'), _('off'), _('None'), _('none')) else None
				if pixmap:
					return ('pixmap', switchPixmap[pixmap])
		return ("text", self._descr)

	# HTML
	def getHTML(self, id):
		res = ""
		for v in self.choices:
			descr = self.description[v]
			if self.value == v:
				checked = 'checked="checked" '
			else:
				checked = ''
			res += '<input type="radio" name="' + id + '" ' + checked + 'value="' + v + '">' + descr + "</input></br>\n"
		return res

	def unsafeAssign(self, value):
		# setValue does check if value is in choices. This is safe enough.
		self.value = value

	description = property(lambda self: descriptionList(self.choices.choices, self.choices.type))


# This is the control, and base class, for binary decisions.
#
# Several customized versions exist for different descriptions.
#
class ConfigBoolean(ConfigElement):
	def __init__(self, default=False, descriptions={False: _("False"), True: _("True")}, graphic=True):
		ConfigElement.__init__(self)
		self.value = self.default = default
		self.last_value = self.tostring(self.value)
		self.descriptions = descriptions
		self.graphic = graphic

	def handleKey(self, key, callback=None):
		value = bool(self.value)
		if key in (ACTIONKEY_TOGGLE, ACTIONKEY_SELECT, ACTIONKEY_LEFT, ACTIONKEY_RIGHT):
			value = not value
		elif key == ACTIONKEY_FIRST:
			value = False
		elif key == ACTIONKEY_LAST:
			value = True
		if self.value != value:
			self.value = value
			if callable(callback):
				callback()

	def fromstring(self, val):
		return str(val).lower() in self.trueValues()

	def tostring(self, value):
		return "True" if value and str(value).lower() in self.trueValues() else "False"
		# Use the following if settings should be saved using the same values as displayed to the user.
		# self.descriptions[True] if value or str(value).lower() in ("1", "enable", "on", "true", "yes") else self.descriptions[True]

	def toDisplayString(self, value):
		return self.descriptions[True] if value or str(value).lower() in self.trueValues() else self.descriptions[False]

	def getText(self):
		return self.descriptions[self.value]

	def getMulti(self, selected):
		from Components.config import config
		if self.graphic and config.usage.boolean_graphic.value in ("true", "only_bool"):
			from skin import switchPixmap
			if "menu_on" in switchPixmap and "menu_off" in switchPixmap:
				return ('pixmap', switchPixmap["menu_on" if self.value else "menu_off"])
		return ("text", self.descriptions[self.value])

	# For HTML Interface - Is this still used?

	def getHTML(self, id):  # DEBUG: Is this still used?
		return "<input type=\"checkbox\" name=\"%s\" value=\"1\"%s />" % (id, " checked=\"checked\"" if self.value else "")

	def unsafeAssign(self, value):  # DEBUG: Is this still used?
		self.value = value.lower() in self.trueValues()

	def trueValues(self):
		# This should be set in the __init__() but has been done this way as a workaround for a stupid broken plugin that fails to call ConfigBoolean.__init__().
		return ("1", "enable", "on", "true", "yes")

	def isChanged(self):
		#Make booleans checks with saved value non case sensitive
		sv = self.saved_value or self.tostring(self.default)
		strv = self.tostring(self.value)
		return strv.lower() != sv.lower()

class ConfigEnableDisable(ConfigBoolean):
	def __init__(self, default=False, graphic=True):
		ConfigBoolean.__init__(self, default=default, descriptions={False: _("Disable"), True: _("Enable")}, graphic=graphic)


class ConfigOnOff(ConfigBoolean):
	def __init__(self, default=False, graphic=True):
		ConfigBoolean.__init__(self, default=default, descriptions={False: _("Off"), True: _("On")}, graphic=graphic)


class ConfigYesNo(ConfigBoolean):
	def __init__(self, default=False, graphic=True):
		ConfigBoolean.__init__(self, default=default, descriptions={False: _("No"), True: _("Yes")}, graphic=graphic)


class ConfigDateTime(ConfigElement):
	def __init__(self, default, formatstring, increment=86400):
		ConfigElement.__init__(self)
		self.increment = increment
		self.formatstring = formatstring
		self.value = self.default = int(default)
		self.last_value = self.tostring(self.value)

	def handleKey(self, key, callback=None):
		prev = str(self.value)
		if key == ACTIONKEY_LEFT:
			self.value -= self.increment
		elif key == ACTIONKEY_RIGHT:
			self.value += self.increment
		elif key == ACTIONKEY_FIRST or key == ACTIONKEY_LAST:
			self.value = self.default
		if str(self.value) != prev and callable(callback):
			callback()

	def getText(self):
		return strftime(self.formatstring, localtime(self.value))

	def toDisplayString(self, value):
		return strftime(self.formatstring, localtime(value))

	def getMulti(self, selected):
		return "text", strftime(self.formatstring, localtime(self.value))

	def fromstring(self, val):
		return int(val)

# *THE* mighty config element class
#
# allows you to store/edit a sequence of values.
# can be used for IP-addresses, dates, plain integers, ...
# several helper exist to ease this up a bit.
#


class ConfigSequence(ConfigElement):
	def __init__(self, seperator, limits, default, censor_char=""):
		ConfigElement.__init__(self)
		assert isinstance(limits, list) and len(limits[0]) == 2, "limits must be [(min, max),...]-tuple-list"
		assert censor_char == "" or len(censor_char) == 1, "censor char must be a single char (or \"\")"
		# assert isinstance(default, list), "default must be a list"
		# assert isinstance(default[0], int), "list must contain numbers"
		# assert len(default) == len(limits), "length must match"

		self.marked_pos = 0
		self.seperator = seperator
		self.limits = limits
		self.censor_char = censor_char

		self.default = default
		self.value = copy_copy(default)
		self.last_value = self.tostring(self.value)
		self.endNotifier = None

	def validate(self):
		max_pos = 0
		num = 0
		for i in self._value:
			max_pos += len(str(self.limits[num][1]))

			if self._value[num] < self.limits[num][0]:
				self._value[num] = self.limits[num][0]

			if self._value[num] > self.limits[num][1]:
				self._value[num] = self.limits[num][1]

			num += 1

		if self.marked_pos >= max_pos:
			if self.endNotifier:
				for x in self.endNotifier:
					x(self)
			self.marked_pos = max_pos - 1

		if self.marked_pos < 0:
			self.marked_pos = 0

	def validatePos(self):
		if self.marked_pos < 0:
			self.marked_pos = 0

		total_len = sum([len(str(x[1])) for x in self.limits])

		if self.marked_pos >= total_len:
			self.marked_pos = total_len - 1

	def addEndNotifier(self, notifier):
		if self.endNotifier is None:
			self.endNotifier = []
		self.endNotifier.append(notifier)

	def handleKey(self, key, callback=None):
		prev = str(self._value)
		if key == ACTIONKEY_LEFT:
			self.marked_pos -= 1
			self.validatePos()

		elif key == ACTIONKEY_RIGHT:
			self.marked_pos += 1
			self.validatePos()

		elif key == ACTIONKEY_FIRST:
			self.marked_pos = 0
			self.validatePos()

		elif key == ACTIONKEY_LAST:
			max_pos = 0
			num = 0
			for i in self._value:
				max_pos += len(str(self.limits[num][1]))
				num += 1
			self.marked_pos = max_pos - 1
			self.validatePos()

		elif key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)

			block_len = [len(str(x[1])) for x in self.limits]

			pos = 0
			blocknumber = 0
			block_len_total = [0]
			for x in block_len:
				pos += block_len[blocknumber]
				block_len_total.append(pos)
				if pos - 1 >= self.marked_pos:
					pass
				else:
					blocknumber += 1

			# length of numberblock
			number_len = len(str(self.limits[blocknumber][1]))

			# position in the block
			posinblock = self.marked_pos - block_len_total[blocknumber]

			oldvalue = abs(self._value[blocknumber])  # we are using abs in order to allow change negative values like default -1 on mis
			olddec = oldvalue % 10 ** (number_len - posinblock) - (oldvalue % 10 ** (number_len - posinblock - 1))
			newvalue = oldvalue - olddec + (10 ** (number_len - posinblock - 1) * number)

			self._value[blocknumber] = newvalue
			self.marked_pos += 1

			self.validate()
		if not isinstance(self, ConfigClock) and prev != str(self._value):  # callback for ConfigClock handled in ConfigClock
			self.changed()  # this is here only because SetValue() has not been called
			if callable(callback):
				callback()

	def genText(self):
		value = ""
		mPos = self.marked_pos
		num = 0
		for i in self._value:
			if value:		# fixme no heading separator possible
				value += self.seperator
				if mPos >= len(value) - 1:
					mPos += 1
			if self.censor_char == "":
				value += ("%0" + str(len(str(self.limits[num][1]))) + "d") % i
			else:
				value += (self.censor_char * len(str(self.limits[num][1])))
			num += 1
		return value, mPos

	def getText(self):
		(value, mPos) = self.genText()
		return value

	def getMulti(self, selected):
		(value, mPos) = self.genText()
		# only mark cursor when we are selected
		# (this code is heavily ink optimized!)
		if self.enabled:
			return "mtext"[1 - selected:], value, [mPos]
		else:
			return "text", value

	def tostring(self, val):
		if val:
			return self.seperator.join([self.saveSingle(x) for x in val])
		return None

	def saveSingle(self, v):
		return str(v)

	def fromstring(self, value):
		ret = [int(x) for x in value.split(self.seperator)]
		return ret + [int(x[0]) for x in self.limits[len(ret):]]


ip_limits = [(0, 255), (0, 255), (0, 255), (0, 255)]


class ConfigIP(ConfigSequence):
	def __init__(self, default, auto_jump=False):
		ConfigSequence.__init__(self, seperator=".", limits=ip_limits, default=default)
		self.block_len = [len(str(x[1])) for x in self.limits]
		self.marked_block = 0
		self.overwrite = True
		self.auto_jump = auto_jump

	def handleKey(self, key, callback=None):
		prev = str(self.value)
		self.execHandleKey(key)
		if prev != str(self.value):
			self.changed()
			if callable(callback):
				callback()

	def execHandleKey(self, key):
		if key == ACTIONKEY_LEFT:
			if self.marked_block > 0:
				self.marked_block -= 1
			self.overwrite = True

		elif key == ACTIONKEY_RIGHT:
			if self.marked_block < len(self.limits) - 1:
				self.marked_block += 1
			self.overwrite = True

		elif key == ACTIONKEY_FIRST:
			self.marked_block = 0
			self.overwrite = True

		elif key == ACTIONKEY_LAST:
			self.marked_block = len(self.limits) - 1
			self.overwrite = True

		elif key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			oldvalue = self._value[self.marked_block]

			if self.overwrite:
				self._value[self.marked_block] = number
				self.overwrite = False
			else:
				oldvalue *= 10
				newvalue = oldvalue + number
				if self.auto_jump and newvalue > self.limits[self.marked_block][1] and self.marked_block < len(self.limits) - 1:
					self.execHandleKey(ACTIONKEY_RIGHT)
					self.execHandleKey(key)
					return
				else:
					self._value[self.marked_block] = newvalue

			if len(str(self._value[self.marked_block])) >= self.block_len[self.marked_block]:
				self.execHandleKey(ACTIONKEY_RIGHT)

			self.validate()

	def genText(self):
		value = ""
		block_strlen = []
		if self._value:
			for i in self._value:
				block_strlen.append(len(str(i)))
				if value:
					value += self.seperator
				value += str(i)
		leftPos = sum(block_strlen[:self.marked_block]) + self.marked_block
		rightPos = sum(block_strlen[:(self.marked_block + 1)]) + self.marked_block
		mBlock = list(range(leftPos, rightPos))
		return value, mBlock

	def getMulti(self, selected):
		(value, mBlock) = self.genText()
		if self.enabled:
			return "mtext"[1 - selected:], value, mBlock
		else:
			return "text", value

	def getHTML(self, id=0):
		# I do not know why id is here but it is used in the sources renderer and I'm afraid we should keep it for compatibily. It is not used here but I give at a default value
		# we definitely don't want leading zeros
		return '.'.join(["%d" % d for d in self.value])


mac_limits = [(1, 255), (1, 255), (1, 255), (1, 255), (1, 255), (1, 255)]


class ConfigMAC(ConfigSequence):
	def __init__(self, default):
		ConfigSequence.__init__(self, seperator=":", limits=mac_limits, default=default)


class ConfigMacText(ConfigElement, NumericalTextInput):
	def __init__(self, default="", visible_width=False):
		ConfigElement.__init__(self)
		NumericalTextInput.__init__(self, nextFunc=self.nextFunc, handleTimeout=False)

		self.marked_pos = 0
		self.allmarked = (default != "")
		self.fixed_size = 17
		self.visible_width = visible_width
		self.offset = 0
		self.overwrite = 17
		self.help_window = None
		self.value = self.default = default
		self.last_value = self.tostring(self.value)
		self.useableChars = '0123456789ABCDEF'

	def validateMarker(self):
		textlen = len(self.text)
		if self.marked_pos > textlen - 1:
			self.marked_pos = textlen - 1
		elif self.marked_pos < 0:
			self.marked_pos = 0

	def insertChar(self, ch, pos, owr):
		if self.text[pos] == ':':
			pos += 1
		if owr or self.overwrite:
			self.text = self.text[0:pos] + ch + self.text[pos + 1:]
		elif self.fixed_size:
			self.text = self.text[0:pos] + ch + self.text[pos:-1]
		else:
			self.text = self.text[0:pos] + ch + self.text[pos:]

	def handleKey(self, key, callback=None):
		prev = str(self.value)
		if key == ACTIONKEY_LEFT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = len(self.text)
				self.allmarked = False
			else:
				if self.text[self.marked_pos - 1] == ':':
					self.marked_pos -= 2
				else:
					self.marked_pos -= 1
		elif key == ACTIONKEY_RIGHT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = 0
				self.allmarked = False
			else:
				if self.marked_pos < (len(self.text) - 1):
					if self.text[self.marked_pos + 1] == ':':
						self.marked_pos += 2
					else:
						self.marked_pos += 1
		elif key in ACTIONKEY_NUMBERS:
			owr = self.lastKey == getKeyNumber(key)
			newChar = self.getKey(getKeyNumber(key))
			self.insertChar(newChar, self.marked_pos, owr)
		elif key == ACTIONKEY_TIMEOUT:
			self.timeout()
			if self.help_window:
				self.help_window.update(self)
			if self.text[self.marked_pos] == ':':
				self.marked_pos += 1
			return

		if self.help_window:
			self.help_window.update(self)
		self.validateMarker()
		if prev != str(self.value):
			self.changed()
			if callable(callback):
				callback()

	def nextFunc(self):
		self.marked_pos += 1
		self.validateMarker()
		self.changed()

	def getValue(self):
		# print(f"[Config][getValue] {self.text}")
		return str(self.text)

	def setValue(self, val):
		# print(f"[Config][setValue] val:{val}")
		prev = self.text if hasattr(self, "text") else None
		if val != prev:
			self.text = val
			self.changed()

	value = property(getValue, setValue)
	_value = property(getValue, setValue)

	def getText(self):
		# print(f"[Config][getText] {self.text}")
		return self.text

	def getMulti(self, selected):
		# print(f"[Config][getMulti] {self.text}")
		if self.visible_width:
			if self.allmarked:
				mark = list(range(0, min(self.visible_width, len(self.text))))
			else:
				mark = [self.marked_pos - self.offset]
			return "mtext"[1 - selected:], str(self.text[self.offset:self.offset + self.visible_width]) + " ", mark
		else:
			if self.allmarked:
				mark = list(range(0, len(self.text)))
			else:
				mark = [self.marked_pos]
			return "mtext"[1 - selected:], str(self.text) + " ", mark

	def onSelect(self, session):
		self.allmarked = (self.value != "")
		if session is not None:
			from Screens.NumericalTextInputHelpDialog import NumericalTextInputHelpDialog
			self.help_window = session.instantiateDialog(NumericalTextInputHelpDialog, self)
			self.help_window.show()

	def onDeselect(self, session):
		self.marked_pos = 0
		self.offset = 0
		if self.help_window:
			session.deleteDialog(self.help_window)
			self.help_window = None

	def getHTML(self, id):
		return '<input type="text" name="' + id + '" value="' + self.value + '" /><br>\n'

	def unsafeAssign(self, value):
		self.value = str(value)


class ConfigPosition(ConfigSequence):
	def __init__(self, default, args):
		ConfigSequence.__init__(self, seperator=",", limits=[(0, args[0]), (0, args[1]), (0, args[2]), (0, args[3])], default=default)


clock_limits = [(0, 23), (0, 59)]


class ConfigClock(ConfigSequence):
	def __init__(self, default):
		# dafault can either be a timestamp
		# or an (hours, minutes) tuple.
		if isinstance(default, tuple):
			itemList = list(localtime())
			itemList[3] = default[0]  # hours
			itemList[4] = default[1]  # minutes
			default = int(mktime(tuple(itemList)))
		t = localtime(default)
		ConfigSequence.__init__(self, seperator=":", limits=clock_limits, default=[t.tm_hour, t.tm_min])

	def increment(self):
		# Check if Minutes maxed out
		if self._value[1] == 59:
			# Increment Hour, reset Minutes
			if self._value[0] < 23:
				self._value[0] += 1
			else:
				self._value[0] = 0
			self._value[1] = 0
		else:
			# Increment Minutes
			self._value[1] += 1
		# Trigger change
		self.changed()

	def decrement(self):
		# Check if Minutes is minimum
		if self._value[1] == 0:
			# Decrement Hour, set Minutes to 59
			if self._value[0] > 0:
				self._value[0] -= 1
			else:
				self._value[0] = 23
			self._value[1] = 59
		else:
			# Decrement Minutes
			self._value[1] -= 1
		# Trigger change
		self.changed()

	def handleKey(self, key, callback=None):
		prev = str(self.value)
		if key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				digit = code - 48
			else:
				digit = getKeyNumber(key)

			hour = self._value[0]
			pmadjust = 0
			if self.marked_pos == 0 and digit >= 3:  # Only 0, 1, 2 allowed (24 hour clock)
				return
			if self.marked_pos == 1 and hour > 19 and digit >= 4:  # Only 20, 21, 22, 23 allowed
				return
			if self.marked_pos == 2 and digit >= 6:  # Only 0, 1, ..., 5 allowed (tens digit of minutes)
				return

			value = bytearray(b"%02d%02d" % (hour, self._value[1]))  # Must be ASCII!
			value[self.marked_pos] = digit + ord(b'0')
			hour = int(value[:2])
			minute = int(value[2:])

			if hour > 23:
				hour = 20

			self._value[0] = hour
			self._value[1] = minute
			self.marked_pos += 1
			self.validate()
		else:
			ConfigSequence.handleKey(self, key)
		if prev != str(self.value):
			self.changed()
			if callable(callback):
				callback()

	def toDisplayString(self, value):
		newtime = list(localtime())
		newtime[3] = value[0]
		newtime[4] = value[1]
		retval = strftime(_("%R"), tuple(newtime))
		return retval

	def genText(self):
		mPos = self.marked_pos
		if mPos >= 2:
			mPos += 1  # Skip over the separator
		value = self.toDisplayString(self._value)
		return value, mPos


date_limits = [(1, 31), (1, 12), (1970, 2050)]


class ConfigDate(ConfigSequence):
	def __init__(self, default):
		d = localtime(default)
		ConfigSequence.__init__(self, seperator=".", limits=date_limits, default=[d.tm_mday, d.tm_mon, d.tm_year])


integer_limits = (0, 9999999999)


class ConfigInteger(ConfigSequence):
	def __init__(self, default, limits=integer_limits):
		ConfigSequence.__init__(self, seperator=":", limits=[limits], default=default)

	# you need to override this to do input validation
	def setValue(self, value):
		prev = str(self._value) if hasattr(self, "_value") and len(self._value) else None
		self._value = [value]
		if str(self._value) != prev:
			self.changed()

	def getValue(self):
		return self._value[0]

	value = property(getValue, setValue)

	def fromstring(self, value):
		return int(value)

	def tostring(self, value):
		return str(value)


class ConfigPIN(ConfigInteger):
	def __init__(self, default, len=4, censor=""):
		assert isinstance(default, int), "ConfigPIN default must be an integer"
		ConfigSequence.__init__(self, seperator=":", limits=[(0, (10 ** len) - 1)], censor_char=censor, default=default)
		self.len = len

	def getLength(self):
		return self.len


class ConfigFloat(ConfigSequence):
	def __init__(self, default, limits):
		ConfigSequence.__init__(self, seperator=".", limits=limits, default=default)

	def getFloat(self):
		return float(self.value[1] / float(self.limits[1][1] + 1) + self.value[0])

	float = property(getFloat)

	def getFloatInt(self):
		return int(self.value[0] * float(self.limits[1][1] + 1) + self.value[1])

	def setFloatInt(self, val):
		self.value[0] = val / float(self.limits[1][1] + 1)
		self.value[1] = val % float(self.limits[1][1] + 1)

	floatint = property(getFloatInt, setFloatInt)

# An editable text item.
#


class ConfigText(ConfigElement, NumericalTextInput):
	def __init__(self, default="", fixed_size=True, visible_width=False):
		ConfigElement.__init__(self)
		NumericalTextInput.__init__(self, nextFunc=self.nextFunc, handleTimeout=False)
		self.marked_pos = 0
		self.allmarked = (default != "")
		self.fixed_size = fixed_size
		self.visible_width = visible_width
		self.offset = 0
		self.overwrite = fixed_size
		self.help_window = None
		self.value = self.default = default
		self.last_value = self.tostring(self.value)

	def validateMarker(self):
		textlen = len(self.text)
		if self.fixed_size:
			if self.marked_pos > textlen - 1:
				self.marked_pos = textlen - 1
		else:
			if self.marked_pos > textlen:
				self.marked_pos = textlen
		if self.marked_pos < 0:
			self.marked_pos = 0
		if self.visible_width:
			if self.marked_pos < self.offset:
				self.offset = self.marked_pos
			if self.marked_pos >= self.offset + self.visible_width:
				if self.marked_pos == textlen:
					self.offset = self.marked_pos - self.visible_width
				else:
					self.offset = self.marked_pos - self.visible_width + 1
			if self.offset > 0 and self.offset + self.visible_width > textlen:
				self.offset = max(0, textlen - self.visible_width)

	def insertChar(self, ch, pos, owr):
		if owr or self.overwrite:
			self.text = self.text[0:pos] + ch + self.text[pos + 1:]
		elif self.fixed_size:
			self.text = self.text[0:pos] + ch + self.text[pos:-1]
		else:
			self.text = self.text[0:pos] + ch + self.text[pos:]

	def deleteChar(self, pos):
		if not self.fixed_size:
			self.text = self.text[0:pos] + self.text[pos + 1:]
		elif self.overwrite:
			self.text = self.text[0:pos] + " " + self.text[pos + 1:]
		else:
			self.text = self.text[0:pos] + self.text[pos + 1:] + " "

	def deleteAllChars(self):
		if self.fixed_size:
			self.text = " " * len(self.text)
		else:
			self.text = ""
		self.marked_pos = 0

	def handleKey(self, key, callback=None):
		# This will not change anything on the value itself
		# so we can handle it here in gui element.
		prev = str(self.value)
		if key == ACTIONKEY_FIRST:
			self.timeout()
			self.allmarked = False
			self.marked_pos = 0
		elif key == ACTIONKEY_LEFT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = len(self.text)
				self.allmarked = False
			else:
				self.marked_pos -= 1
		elif key == ACTIONKEY_RIGHT:
			self.timeout()
			if self.allmarked:
				self.marked_pos = 0
				self.allmarked = False
			else:
				self.marked_pos += 1
		elif key == ACTIONKEY_LAST:
			self.timeout()
			self.allmarked = False
			self.marked_pos = len(self.text)
		elif key == ACTIONKEY_BACKSPACE:
			self.timeout()
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			elif self.marked_pos > 0:
				self.deleteChar(self.marked_pos - 1)
				if not self.fixed_size and self.offset > 0:
					self.offset -= 1
				self.marked_pos -= 1
		elif key == ACTIONKEY_DELETE:
			self.timeout()
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			else:
				self.deleteChar(self.marked_pos)
				if self.fixed_size and self.overwrite:
					self.marked_pos += 1
		elif key == ACTIONKEY_ERASE:
			self.timeout()
			self.deleteAllChars()
		elif key == ACTIONKEY_TOGGLE:
			self.timeout()
			self.overwrite = not self.overwrite
		elif key == ACTIONKEY_ASCII:
			self.timeout()
			newChar = chr(getPrevAsciiCode())
			if not self.useableChars or newChar in self.useableChars:
				if self.allmarked:
					self.deleteAllChars()
					self.allmarked = False
				self.insertChar(newChar, self.marked_pos, False)
				self.marked_pos += 1
		elif key in ACTIONKEY_NUMBERS:
			owr = self.lastKey == getKeyNumber(key)
			newChar = self.getKey(getKeyNumber(key))
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			self.insertChar(newChar, self.marked_pos, owr)
		elif key == ACTIONKEY_TIMEOUT:
			self.timeout()
			if self.help_window:
				self.help_window.update(self)
			return

		if self.help_window:
			self.help_window.update(self)
		self.validateMarker()
		if prev != str(self.value):
			self.changed()
			if callable(callback):
				callback()

	def nextFunc(self):
		self.marked_pos += 1
		self.validateMarker()
		self.changed()

	def getValue(self):
		return self.text

	def setValue(self, val):
		prev = self.text if hasattr(self, "text") else None
		if val != prev:
			self.text = val
			self.changed()

	value = property(getValue, setValue)
	_value = property(getValue, setValue)

	def getText(self):
		# print(f"[Config][getText2] {self.text}")
		return self.text

	def getMulti(self, selected):
		# print(f"[Config][getMulti2] {self.text}")
		if self.visible_width:
			if self.allmarked:
				mark = list(range(0, min(self.visible_width, len(self.text))))
			else:

				mark = [self.marked_pos - self.offset]
			return "mtext"[1 - selected:], str(self.text[self.offset:self.offset + self.visible_width]) + " ", mark
		else:
			if self.allmarked:
				mark = list(range(0, len(self.text)))
			else:
				mark = [self.marked_pos]
			return "mtext"[1 - selected:], str(self.text) + " ", mark

	def onSelect(self, session):
		self.allmarked = (self.value != "")
		if session is not None:
			from Screens.NumericalTextInputHelpDialog import NumericalTextInputHelpDialog
			self.help_window = session.instantiateDialog(NumericalTextInputHelpDialog, self)
			self.help_window.show()

	def onDeselect(self, session):
		self.marked_pos = 0
		self.offset = 0
		if self.help_window:
			session.deleteDialog(self.help_window)
			self.help_window = None

	def hideHelp(self, session):
		if session is not None and self.help_window is not None:
			self.help_window.hide()

	def showHelp(self, session):
		if session is not None and self.help_window is not None:
			self.help_window.show()

	def getHTML(self, id):
		return '<input type="text" name="' + id + '" value="' + self.value + '" /><br>\n'

	def unsafeAssign(self, value):
		self.value = str(value)


class ConfigPassword(ConfigText):
	def __init__(self, default="", fixed_size=False, visible_width=False, censor="*"):
		ConfigText.__init__(self, default=default, fixed_size=fixed_size, visible_width=visible_width)
		self.censor_char = censor
		self.hidden = True

	def getMulti(self, selected):
		mtext, text, mark = ConfigText.getMulti(self, selected)
		if self.hidden:
			text = len(text) * self.censor_char
		return mtext, text, mark

	def onSelect(self, session):
		ConfigText.onSelect(self, session)
		self.hidden = False

	def onDeselect(self, session):
		ConfigText.onDeselect(self, session)
		self.hidden = True

# lets the user select between [min, min + stepwidth, min + (stepwidth * 2)..., maxval] with maxval <= max depending
# on the stepwidth
# min, max, stepwidth, default are int values
# wraparound: pressing RIGHT key at max value brings you to min value and vice versa if set to True


class ConfigSelectionNumber(ConfigSelection):
	def __init__(self, min, max, stepwidth, default=None, wraparound=False):
		self.wraparound = wraparound
		if default is None:
			default = min
		default = str(default)
		choices = []
		step = min
		while step <= max:
			choices.append(str(step))
			step += stepwidth

		ConfigSelection.__init__(self, choices, default)

	def getValue(self):
		return int(ConfigSelection.getValue(self))

	def setValue(self, val):
		ConfigSelection.setValue(self, str(val))

	value = property(getValue, setValue)

	def getIndex(self):
		return self.choices.index(self.value)

	index = property(getIndex)

	def handleKey(self, key, callback=None):
		if not self.wraparound:
			if key == ACTIONKEY_RIGHT:
				if len(self.choices) == (self.choices.index(str(self.value)) + 1):
					return
			if key == ACTIONKEY_LEFT:
				if self.choices.index(str(self.value)) == 0:
					return
		ConfigSelection.handleKey(self, key, callback)


class ConfigNumber(ConfigText):
	def __init__(self, default=0):
		ConfigText.__init__(self, str(default), fixed_size=False)

	def getValue(self):
		return int(self.text) if len(self.text) else self.text

	def setValue(self, val):
		prev = str(self.text) if hasattr(self, "text") else None
		self.text = str(val)
		if str(self.text) != prev:
			self.changed()

	value = property(getValue, setValue)
	_value = property(getValue, setValue)

	def conform(self):
		pos = len(self.text) - self.marked_pos
		self.text = self.text.lstrip("0")
		if self.text == "":
			self.text = "0"
		if pos > len(self.text):
			self.marked_pos = 0
		else:
			self.marked_pos = len(self.text) - pos

	def handleKey(self, key, callback=None):
		prev = str(self.value)
		if key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				ascii = getPrevAsciiCode()
				if not (48 <= ascii <= 57):
					return
			else:
				ascii = getKeyNumber(key) + 48
			newChar = chr(ascii)
			if self.allmarked:
				self.deleteAllChars()
				self.allmarked = False
			self.insertChar(newChar, self.marked_pos, False)
			self.marked_pos += 1
			if prev != str(self.value):
				self.changed()
				if callable(callback):
					callback()
		else:
			ConfigText.handleKey(self, key, callback)
		self.conform()

	def onSelect(self, session):
		self.allmarked = (self.value != "")

	def onDeselect(self, session):
		self.marked_pos = 0
		self.offset = 0


class ConfigSearchText(ConfigText):
	def __init__(self, default="", fixed_size=False, visible_width=False):
		ConfigText.__init__(self, default=default, fixed_size=fixed_size, visible_width=visible_width)
		NumericalTextInput.__init__(self, nextFunc=self.nextFunc, handleTimeout=False, search=True)


class ConfigDirectory(ConfigText):
	def __init__(self, default="", visible_width=60):
		ConfigText.__init__(self, default, fixed_size=True, visible_width=visible_width)

	def handleKey(self, key, callback=None):
		pass

	def getValue(self):
		if self.text == "":
			return None
		else:
			return ConfigText.getValue(self)

	def setValue(self, val):
		if val is None:
			val = ""
		ConfigText.setValue(self, val)

	value = property(getValue, setValue)

	def getMulti(self, selected):
		if self.text == "":
			return "mtext"[1 - selected:], _("List of storage devices"), list(range(0))
		else:
			return ConfigText.getMulti(self, selected)

	def onSelect(self, session):
		self.allmarked = (self.value != "")

# a slider.


class ConfigSlider(ConfigElement):
	def __init__(self, default=0, increment=1, limits=(0, 100)):
		ConfigElement.__init__(self)
		self.value = self.default = default
		self.last_value = self.tostring(self.value)
		self.min = limits[0]
		self.max = limits[1]
		self.increment = increment

	def handleKey(self, key, callback=None):
		if key in (ACTIONKEY_LEFT, ACTIONKEY_RIGHT, ACTIONKEY_FIRST, ACTIONKEY_LAST):
			value = self.value
			if key == ACTIONKEY_LEFT:
				value = max(value - self.increment, self.min)
			elif key == ACTIONKEY_RIGHT:
				value = min(value + self.increment, self.max)
			elif key == ACTIONKEY_FIRST:
				value = self.min
			elif key == ACTIONKEY_LAST:
				value = self.max
			if value != self.value:
				self.value = value  # self.value calls the notifier
				if callable(callback):
					callback()

	def getText(self):
		return "%d / %d" % (self.value, self.max)

	def getMulti(self, selected):
		return "slider", self.value, self.max

	def fromstring(self, value):
		return int(value)

# a satlist. in fact, it's a ConfigSelection.


class ConfigSatlist(ConfigSelection):
	def __init__(self, list, default=None):
		if default is not None:
			default = str(default)
		ConfigSelection.__init__(self, choices=[(str(orbpos), desc) for (orbpos, desc, flags) in list], default=default)

	def getOrbitalPosition(self):
		if self.value == "":
			return None
		return int(self.value)

	orbital_position = property(getOrbitalPosition)


# This is the control, and base class, for a set of selection toggle fields.
#
class ConfigSet(ConfigElement):
	def __init__(self, choices, default=None):
		ConfigElement.__init__(self)
		if isinstance(choices, list):
			choices.sort()
			self.choices = choicesList(choices, choicesList.LIST_TYPE_LIST)
		else:
			assert False, "[Config] Error: 'ConfigSet' choices must be a list!"
		if default is None:
			default = []
		default.sort()
		self.default = default
		self.value = default[:]
		self.last_value = self.tostring(self.value)
		self.pos = 0

	def handleKey(self, key, callback=None):
		count = len(self.choices)
		if key in [ACTIONKEY_TOGGLE, ACTIONKEY_SELECT, ACTIONKEY_DELETE, ACTIONKEY_BACKSPACE] + ACTIONKEY_NUMBERS:
			value = self.value
			choice = self.choices[self.pos]
			if choice in value:
				value.remove(choice)
			else:
				value.append(choice)
				value.sort()
			self.changed()
			if callable(callback):
				callback()
		elif key == ACTIONKEY_LEFT:
			self.pos = (self.pos - 1) % count
		elif key == ACTIONKEY_RIGHT:
			self.pos = (self.pos + 1) % count
		elif key == ACTIONKEY_FIRST:
			self.pos = 0
		elif key == ACTIONKEY_LAST:
			self.pos = count - 1

	def load(self):
		ConfigElement.load(self)
		if not self.value:
			self.value = []
		if not isinstance(self.value, list):
			self.value = list(self.value)
		self.value.sort()
		self.last_value = self.tostring(self.value[:])

	def fromstring(self, val):
		return eval(val)

	def tostring(self, val):
		return str(val)

	def toDisplayString(self, val):
		return ", ".join([self.description[x] for x in val])

	def getText(self):
		return " ".join([self.description[x] for x in self.value])

	def getMulti(self, selected):
		if selected:
			text = []
			pos = 0
			start = 0
			end = 0
			for item in self.choices:
				itemStr = str(item)
				text.append(" %s " % itemStr if item in self.value else "(%s)" % itemStr)
				length = 2 + len(itemStr)
				if item == self.choices[self.pos]:
					start = pos
					end = start + length
				pos += length
			return "mtext", "".join(text), list(range(start, end))
		else:
			return "text", " ".join([self.description[x] for x in self.value])

	def onDeselect(self, session):
		# self.pos = 0  # Enable this to reset the position marker to the first element.
		pass

	description = property(lambda self: descriptionList(self.choices.choices, choicesList.LIST_TYPE_LIST))


class ConfigDictionarySet(ConfigElement):
	def __init__(self, default={}):
		ConfigElement.__init__(self)
		self.default = default
		self.dirs = {}
		self.value = self.default

	def setValue(self, value):
		if value == self.dirs:
			return
		if isinstance(value, dict):
			self.dirs = value
			self.changed()

	def getValue(self):
		return self.dirs

	value = property(getValue, setValue)

	def tostring(self, value):
		return str(value)

	def fromstring(self, val):
		return eval(val)

	def load(self):
		sv = self.saved_value
		if sv is None:
			tmp = self.default
		else:
			tmp = self.fromstring(sv)
		self.dirs = tmp

	def changeConfigValue(self, value, config_key, config_value):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs:
				self.dirs[value][config_key] = config_value
			else:
				self.dirs[value] = {config_key: config_value}
			self.changed()

	def getConfigValue(self, value, config_key):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs and config_key in self.dirs[value]:
				return self.dirs[value][config_key]
		return None

	def removeConfigValue(self, value, config_key):
		if isinstance(value, str) and isinstance(config_key, str):
			if value in self.dirs and config_key in self.dirs[value]:
				try:
					del self.dirs[value][config_key]
				except KeyError:
					pass
				self.changed()

	def save(self):
		del_keys = []
		for key in self.dirs:
			if not len(self.dirs[key]):
				del_keys.append(key)
		for del_key in del_keys:
			try:
				del self.dirs[del_key]
			except KeyError:
				pass
			self.changed()
		self.saved_value = self.tostring(self.dirs)


class ConfigLocations(ConfigElement):
	def __init__(self, default=None, visible_width=False):
		if not default:
			default = []
		ConfigElement.__init__(self)
		self.visible_width = visible_width
		self.pos = -1
		self.default = default
		self.locations = []
		self.mountpoints = []
		self.value = default[:]

	def setValue(self, value):
		locations = self.locations
		loc = [x[0] for x in locations if x[3]]
		add = [x for x in value if x not in loc]
		diff = add + [x for x in loc if x not in value]
		locations = [x for x in locations if x[0] not in diff] + [[x, self.getMountpoint(x), True, True] for x in add]
		# locations.sort(key = lambda x: x[0]) # Do not sort here. Fix the input. config.py should not be modifying any list sent in by the calling code.
		if self.locations != locations:
			self.locations = locations
			self.changed()

	def getValue(self):
		self.checkChangedMountpoints()
		locations = self.locations
		for x in locations:
			x[3] = x[2]
		return [x[0] for x in locations if x[3]]

	value = property(getValue, setValue)

	def tostring(self, value):
		return str(value)

	def fromstring(self, val):
		return eval(val)

	def load(self):
		sv = self.saved_value
		if sv is None:
			tmp = self.default
		else:
			tmp = self.fromstring(sv)
		locations = [[x, None, False, False] for x in tmp]
		self.refreshMountpoints()
		for x in locations:
			if fileExists(x[0]):
				x[1] = self.getMountpoint(x[0])
				x[2] = True
		self.locations = locations

	def save(self):
		locations = self.locations
		if self.save_disabled or not locations:
			self.saved_value = None
		else:
			self.saved_value = self.tostring([x[0] for x in locations])

	def isChanged(self):
		sv = self.saved_value
		locations = self.locations
		if sv is None and not locations:
			return False
		return self.tostring([x[0] for x in locations]) != sv

	def addedMount(self, mp):
		for x in self.locations:
			if x[1] == mp:
				x[2] = True
			elif x[1] is None and fileExists(x[0]):
				x[1] = self.getMountpoint(x[0])
				x[2] = True

	def removedMount(self, mp):
		for x in self.locations:
			if x[1] == mp:
				x[2] = False

	def refreshMountpoints(self):
		self.mountpoints = [p.mountpoint for p in harddiskmanager.getMountedPartitions() if p.mountpoint != sep]
		self.mountpoints.sort(key=lambda x: -len(x))

	def checkChangedMountpoints(self):
		oldmounts = self.mountpoints
		self.refreshMountpoints()
		newmounts = self.mountpoints
		if oldmounts == newmounts:
			return
		for x in oldmounts:
			if x not in newmounts:
				self.removedMount(x)
		for x in newmounts:
			if x not in oldmounts:
				self.addedMount(x)

	def getMountpoint(self, file):
		file = os_path.realpath(file) + sep
		for m in self.mountpoints:
			if file.startswith(m):
				return m
		return None

	def handleKey(self, key, callback=None):
		count = len(self.value)
		if key == ACTIONKEY_LEFT:
			self.pos = (self.pos - 1) % count
		elif key == ACTIONKEY_RIGHT:
			self.pos = (self.pos + 1) % count
		elif key == ACTIONKEY_FIRST:
			self.pos = 0
		elif key == ACTIONKEY_LAST:
			self.pos = count - 1
		# don't call callback

	def getText(self):
		return " ".join(self.value)

	def getMulti(self, selected):
		if not selected:
			valstr = " ".join(self.value)
			if self.visible_width and len(valstr) > self.visible_width:
				return "text", valstr[0:self.visible_width]
			else:
				return "text", valstr
		else:
			i = 0
			valstr = ""
			ind1 = 0
			ind2 = 0
			for val in self.value:
				if i == self.pos:
					ind1 = len(valstr)
				valstr += str(val) + " "
				if i == self.pos:
					ind2 = len(valstr)
				i += 1
			if self.visible_width and len(valstr) > self.visible_width:
				if ind1 + 1 < self.visible_width // 2:
					off = 0
				else:
					off = min(ind1 + 1 - self.visible_width // 2, len(valstr) - self.visible_width)
				return "mtext", valstr[off:off + self.visible_width], list(range(ind1 - off, ind2 - off))
			else:
				return "mtext", valstr, list(range(ind1, ind2))

	def onDeselect(self, session):
		self.pos = -1

# nothing.


class ConfigNothing(ConfigSelection):
	def __init__(self):
		ConfigSelection.__init__(self, choices=[("", "")])

# until here, 'saved_value' always had to be a *string*.
# now, in ConfigSubsection, and only there, saved_value
# is a dict, essentially forming a tree.
#
# config.foo.bar=True
# config.foobar=False
#
# turns into:
# config.saved_value == {"foo": {"bar": "True"}, "foobar": "False"}
#


class ConfigSubsectionContent:
	pass

# we store a backup of the loaded configuration
# data in self.stored_values, to be able to deploy
# them when a new config element will be added,
# so non-default values are instantly available

# A list, for example:
# config.dipswitches = ConfigSubList()
# config.dipswitches.append(ConfigYesNo())
# config.dipswitches.append(ConfigYesNo())
# config.dipswitches.append(ConfigYesNo())


class ConfigSubList(list):
	def __init__(self):
		list.__init__(self)
		self.stored_values = {}

	def load(self):
		for item in self:
			item.load()

	def save(self):
		for item in self:
			item.save()

	def getSavedValue(self):
		values = {}
		for index, val in enumerate(self):
			saved = val.saved_value
			if saved is not None:
				values[str(index)] = saved
		return values

	def setSavedValue(self, values):
		self.stored_values = dict(values)
		for (key, val) in self.stored_values.items():
			if int(key) < len(self):
				self[int(key)].saved_value = val

	saved_value = property(getSavedValue, setSavedValue)

	def append(self, item):
		index = str(len(self))
		list.append(self, item)
		if index in self.stored_values:
			item.saved_value = self.stored_values[index]
			item.load()

	def dict(self):
		return dict([(str(index), value) for index, value in enumerate(self)])

# Same as ConfigSubList, just as a dictionary.
# Care must be taken that the 'key' has a proper str() method, because it will be used in the config file.


class ConfigSubDict(dict):
	def __init__(self):
		dict.__init__(self)
		self.stored_values = {}

	def load(self):
		for item in self.values():
			item.load()

	def save(self):
		for item in self.values():
			item.save()

	def getSavedValue(self):
		values = {}
		for (key, val) in self.items():
			saved = val.saved_value
			if saved is not None:
				values[str(key)] = saved
		return values

	def setSavedValue(self, values):
		self.stored_values = dict(values)
		for (key, val) in self.items():
			if str(key) in self.stored_values:
				val.saved_value = self.stored_values[str(key)]

	saved_value = property(getSavedValue, setSavedValue)

	def __setitem__(self, key, item):
		dict.__setitem__(self, key, item)
		if str(key) in self.stored_values:
			item.saved_value = self.stored_values[str(key)]
			item.load()

	def dict(self):
		return self

# Like the classes above, just with a more "native"
# syntax.
#
# some evil stuff must be done to allow instant
# loading of added elements. this is why this class
# is so complex.
#
# we need the 'content' because we overwrite
# __setattr__.
# If you don't understand this, try adding
# __setattr__ to a usual exisiting class and you will.


class ConfigSubsection:
	def __init__(self):
		self.__dict__["content"] = ConfigSubsectionContent()
		self.content.items = {}
		self.content.stored_values = {}

	def __setattr__(self, name, value):
		if name == "saved_value":
			return self.setSavedValue(value)
		assert isinstance(value, (ConfigSubsection, ConfigElement, ConfigSubList, ConfigSubDict)), "ConfigSubsections can only store ConfigSubsections, ConfigSubLists, ConfigSubDicts or ConfigElements"
		content = self.content
		content.items[name] = value
		val = content.stored_values.get(name, None)
		if val is not None:
			# print(f"[Config] Ok, now we have a new item '{name}' and have the following value for it '{str(val)}'.")
			value.saved_value = val
			value.load()

	def __getattr__(self, name):
		if name in self.content.items:
			return self.content.items[name]
		raise AttributeError(name)

	def getSavedValue(self):
		values = self.content.stored_values
		for (key, val) in self.content.items.items():
			saved = val.saved_value
			if saved is not None:
				values[key] = saved
			elif key in values:
				del values[key]
		return values

	def setSavedValue(self, values):
		values = dict(values)
		self.content.stored_values = values
		for (key, val) in self.content.items.items():
			value = values.get(key, None)
			if value is not None:
				val.saved_value = value

	saved_value = property(getSavedValue, setSavedValue)

	def save(self):
		for item in self.content.items.values():
			item.save()

	def load(self):
		for item in self.content.items.values():
			item.load()

	def cancel(self):
		for item in self.content.items.values():
			item.cancel()

	def dict(self):
		return self.content.items

# The root config object, which also can "pickle" (=serialize) down the whole config tree.
#
# We try to keep non-existing config entries, to apply them whenever a new config entry is added to a subsection
# Also, non-existing config entries will be saved, so they won't be lost when a config entry disappears.


class Config(ConfigSubsection):
	def __init__(self):
		ConfigSubsection.__init__(self)

	def pickle_this(self, prefix, topickle, result):
		for (key, val) in sorted(topickle.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0].lower()):
			name = '.'.join((prefix, key))
			if isinstance(val, dict):
				self.pickle_this(name, val, result)
			elif isinstance(val, tuple):
				result += [name, '=', str(val[0]), '\n']
			else:
				result += [name, '=', str(val), '\n']

	def pickle(self):
		result = []
		self.pickle_this("config", self.saved_value, result)
		return ''.join(result)

	def unpickle(self, lines, base_file=True):
		tree = {}
		configbase = tree.setdefault("config", {})
		for element in lines:
			if not element or element[0] == '#':
				continue

			result = element.split('=', 1)
			if len(result) != 2:
				continue
			(name, val) = result
			val = val.strip()

			names = name.split('.')
			base = configbase

			for n in names[1:-1]:
				base = base.setdefault(n, {})

			base[names[-1]] = val

			if not base_file:  # not the initial config file..
				# update config.x.y.value when exist
				try:
					configEntry = eval(name)
					if configEntry is not None:
						configEntry.value = val
				except (SyntaxError, KeyError):
					pass

		# we inherit from ConfigSubsection, so ...
		# object.__setattr__(self, "saved_value", tree["config"])
		if "config" in tree:
			self.setSavedValue(tree["config"])

	def saveToFile(self, filename):
		text = self.pickle()
		try:
			with open(filename + ".writing", "w", encoding="UTF-8") as f:
				f.write(text)
				f.flush()
				fsync(f.fileno())
			rename(filename + ".writing", filename)
		except OSError:
			print("[Config] Couldn't write %s" % filename)

	def loadFromFile(self, filename, base_file=True):
		with open(filename, "r", encoding="UTF-8") as f:
			self.unpickle(f, base_file)


config = Config()
config.misc = ConfigSubsection()


class ConfigFile:
	def __init__(self):
		pass

	CONFIG_FILE = resolveFilename(SCOPE_CONFIG, "settings")

	def load(self):
		try:
			config.loadFromFile(self.CONFIG_FILE, True)
			print("[Config] Config file loaded ok...")
		except OSError as error:
			print("[Config] unable to load config (%s), assuming defaults..." % str(error))

	def save(self):
		# config.save()
		config.saveToFile(self.CONFIG_FILE)

	def __resolveValue(self, pickles, cmap):
		key = pickles[0]
		if key in cmap:
			if len(pickles) > 1:
				return self.__resolveValue(pickles[1:], cmap[key].dict())
			else:
				return str(cmap[key].value)
		return None

	def getResolvedKey(self, key):
		names = key.split('.')
		if len(names) > 1:
			if names[0] == "config":
				ret = self.__resolveValue(names[1:], config.content.items)
				if ret and len(ret):
					return ret
		# print("[Config] getResolvedKey", key, "empty variable.")
		return ""


def NoSave(element):
	element.disableSave()
	return element


configfile = ConfigFile()

configfile.load()


def getConfigListEntry(*args):
	assert len(args) > 0, "getConfigListEntry needs a minimum of one argument (descr)"
	return args


def updateConfigElement(element, newelement):
	newelement.value = element.value
	return newelement

# def _(x):
# 	return x
#
# config.bla = ConfigSubsection()
# config.bla.test = ConfigYesNo()
# config.nim = ConfigSubList()
# config.nim.append(ConfigSubsection())
# config.nim[0].bla = ConfigYesNo()
# config.nim.append(ConfigSubsection())
# config.nim[1].bla = ConfigYesNo()
# config.nim[1].blub = ConfigYesNo()
# config.arg = ConfigSubDict()
# config.arg["Hello"] = ConfigYesNo()
#
# config.arg["Hello"].handleKey(ACTIONKEY_RIGHT)
# config.arg["Hello"].handleKey(ACTIONKEY_RIGHT)
#
# #config.saved_value
#
# #configfile.save()
# config.save()
# print config.pickle()


cec_limits = [(0, 15), (0, 15), (0, 15), (0, 15)]


class ConfigCECAddress(ConfigSequence):
	def __init__(self, default, auto_jump=False):
		ConfigSequence.__init__(self, seperator=".", limits=cec_limits, default=default)
		self.block_len = [len(str(x[1])) for x in self.limits]
		self.marked_block = 0
		self.overwrite = True
		self.auto_jump = auto_jump

	def handleKey(self, key, callback=None):
		prev = str(self.value)
		self.execHandleKey(key)
		if prev != str(self.value):
			self.changed()
			if callable(callback):
				callback()

	def execHandleKey(self, key):
		if key == ACTIONKEY_LEFT:
			if self.marked_block > 0:
				self.marked_block -= 1
			self.overwrite = True

		elif key == ACTIONKEY_RIGHT:
			if self.marked_block < len(self.limits) - 1:
				self.marked_block += 1
			self.overwrite = True

		elif key == ACTIONKEY_FIRST:
			self.marked_block = 0
			self.overwrite = True

		elif key == ACTIONKEY_LAST:
			self.marked_block = len(self.limits) - 1
			self.overwrite = True

		elif key in ACTIONKEY_NUMBERS or key == ACTIONKEY_ASCII:
			if key == ACTIONKEY_ASCII:
				code = getPrevAsciiCode()
				if code < 48 or code > 57:
					return
				number = code - 48
			else:
				number = getKeyNumber(key)
			oldvalue = self._value[self.marked_block]

			if self.overwrite:
				self._value[self.marked_block] = number
				self.overwrite = False
			else:
				oldvalue *= 10
				newvalue = oldvalue + number
				if self.auto_jump and newvalue > self.limits[self.marked_block][1] and self.marked_block < len(self.limits) - 1:
					self.execHandleKey(ACTIONKEY_RIGHT)
					self.execHandleKey(key)
					return
				else:
					self._value[self.marked_block] = newvalue

			if len(str(self._value[self.marked_block])) >= self.block_len[self.marked_block]:
				self.execHandleKey(ACTIONKEY_RIGHT)

			self.validate()

	def genText(self):
		value = ""
		block_strlen = []
		for i in self._value:
			block_strlen.append(len(str(i)))
			if value:
				value += self.seperator
			value += str(i)
		leftPos = sum(block_strlen[:self.marked_block]) + self.marked_block
		rightPos = sum(block_strlen[:(self.marked_block + 1)]) + self.marked_block
		mBlock = list(range(leftPos, rightPos))
		return value, mBlock

	def getMulti(self, selected):
		(value, mBlock) = self.genText()
		if self.enabled:
			return "mtext"[1 - selected:], value, mBlock
		else:
			return "text", value

	def getHTML(self, id):
		# we definitely don't want leading zeros
		return '.'.join(["%d" % d for d in self.value])


class ConfigAction(ConfigElement):
	def __init__(self, action, *args):
		ConfigElement.__init__(self)
		self.value = "(OK)"
		self.default = self.value
		self.action = action
		self.actionargs = args

	def handleKey(self, key, callback=None):
		if (key == KEY_OK):
			self.action(*self.actionargs)

	def getMulti(self, dummy):
		pass

	def getText(self):
		pass