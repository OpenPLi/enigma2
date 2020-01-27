from Tools.Profile import profile
profile("LOAD:ElementTree")
import errno
import os
import xml.etree.cElementTree

profile("LOAD:enigma_skin")
from enigma import addFont, eLabel, ePixmap, ePoint, eRect, eSize, eWindow, eWindowStyleManager, eWindowStyleSkinned, getDesktop, gFont, getFontFaces, gRGB
from Components.config import ConfigSubsection, ConfigText, config
from Components.RcModel import rc_model
from Components.Sources.Source import ObsoleteSource
from Components.SystemInfo import SystemInfo
from Tools.Directories import SCOPE_CONFIG, SCOPE_CURRENT_LCDSKIN, SCOPE_CURRENT_SKIN, SCOPE_FONTS, SCOPE_SKIN, SCOPE_SKIN_IMAGE, fileExists, resolveFilename
from Tools.Import import my_import
from Tools.LoadPixmap import LoadPixmap

DEFAULT_SKIN = SystemInfo["HasFullHDSkinSupport"] and "PLi-FullNightHD/skin.xml" or "PLi-HD/skin.xml"  # SD hardware is no longer supported by the default skin.
EMERGENCY_SKIN = "skin_default.xml"
DEFAULT_DISPLAY_SKIN = "skin_display.xml"
USER_SKIN = "skin_user.xml"
USER_SKIN_TEMPLATE = "skin_user_%s.xml"
# BOX_SKIN = "skin_box.xml"  # DEBUG: Is this actually used?
# SECOND_INFOBAR_SKIN = "skin_second_infobar.xml"  # DEBUG: Is this actually used?
SUBTITLE_SKIN = "skin_subtitles.xml"

GUI_SKIN_ID = 0  # Main frame-buffer.
DISPLAY_SKIN_ID = 1  # Front panel / display / LCD.

domSkins = []  # List of skins to be processed into the domScreens dictionary.
domScreens = {}  # Dictionary of skin based screens.
colorNames = {}  # Dictionary of skin color names.
switchPixmap = {}  # Dictionary of switch images.
parameters = {}  # Dictionary of skin parameters used to modify code behavior.
menus = {}  # Dictionary of images associated with menu entries.
setups = {}  # Dictionary of images associated with setup menus.
fonts = {  # Dictionary of predefined and skin defined font aliases.
	"Body": ("Regular", 18, 22, 16),
	"ChoiceList": ("Regular", 20, 24, 18),
}

# Skins are loaded in order of priority.  Skin with highest priority is
# loaded first.  This is usually the user-specified skin.
#
# Currently, loadSingleSkinData (colors, bordersets etc.) are applied
# one-after-each, in order of ascending priority.  The domSkin will keep
# all screens in descending priority, so the first screen found will be
# used.
#
# GUI skins are saved in the settings file as the path relative to
# SCOPE_SKIN.  The full path is NOT saved.  E.g. "MySkin/skin.xml"
#
# Display skins are saved in the settings file as the path relative to
# SCOPE_CURRENT_LCDSKIN.  The full path is NOT saved.
# E.g. "MySkin/skin_display.xml"
#
config.skin = ConfigSubsection()
skin = resolveFilename(SCOPE_SKIN, DEFAULT_SKIN)
if not fileExists(skin) or not os.path.isfile(skin):
	print "[Skin] Error: Default skin '%s' is not readable or is not a file!  Using emergency skin." % skin
	DEFAULT_SKIN = EMERGENCY_SKIN
config.skin.primary_skin = ConfigText(default=DEFAULT_SKIN)
config.skin.display_skin = ConfigText(default=DEFAULT_DISPLAY_SKIN)

# Look for a skin related user skin "skin_user_<SkinName>.xml" file,
# if one exists.  If a skin related user skin does not exist then a
# generic user skin "skin_user.xml" will be used, if one exists.
#
# ...but first check that the relevant base dir exists, otherwise
# we may well get into a start-up loop with skin failures
#
def findUserRelatedSkin():
	if os.path.isfile(resolveFilename(SCOPE_SKIN, config.skin.primary_skin.value)):
		name = USER_SKIN_TEMPLATE % os.path.dirname(config.skin.primary_skin.value)
		if fileExists(resolveFilename(SCOPE_CURRENT_SKIN, name)):
			return name
	return None

def addSkin(name, scope=SCOPE_CURRENT_SKIN):
	global domSkins
	filename = resolveFilename(scope, name)
	try:
		# This open gets around a possible file handle leak in Python's XML parser.
		with open(filename, "r") as fd:
			try:
				domSkins.append((scope, "%s/" % os.path.dirname(filename), xml.etree.cElementTree.parse(fd).getroot()))
				print "[Skin] Skin '%s' added successfully." % filename
				return True
			except xml.etree.cElementTree.ParseError as e:
				fd.seek(0)
				content = fd.readlines()
				line, column = e.position
				print "[Skin] XML Parse Error: '%s' in '%s'!" % (e, filename)
				data = content[line - 1].replace("\t", " ").rstrip()
				print "[Skin] XML Parse Error: '%s'" % data
				print "[Skin] XML Parse Error: '%s^%s'" % ("-" * column, " " * (len(data) - column - 1))
			except Exception as e:
				print "[Skin] Error: Unable to parse skin data in '%s' - '%s'!" % (filename, e)
	except IOError as e:
		if e.errno == errno.ENOENT:  #  No such file or directory
			print "[Skin] Warning: Skin file '%s' does not exist!" % filename
		else:
			print "[Skin] Error %d: Opening skin file '%s'! (%s)" % (e.errno, filename, os.strerror(e.errno))
	except Exception as e:
		print "[Skin] Error: Unexpected error opening skin file '%s'! (%s)" % (filename, e)
	return False


profile("LoadSkin")

# Add an optional skin related user skin "user_skin_<SkinName>.xml".  If there is
# not a skin related user skin then try to add am optional generic user skin.
result = None
name = findUserRelatedSkin()
if name:
	result = addSkin(name, scope=SCOPE_CURRENT_SKIN)
if not name or not result:
	addSkin(USER_SKIN, scope=SCOPE_CURRENT_SKIN)

# Add the main GUI skin.
result = []
for skin, name in [(config.skin.primary_skin.value, "current"), (DEFAULT_SKIN, "default"), (EMERGENCY_SKIN, "emergency")]:
	if skin in result:  # Don't try to add a skin that has already failed.
		continue
	config.skin.primary_skin.value = skin
	if addSkin(config.skin.primary_skin.value, scope=SCOPE_CURRENT_SKIN):
		break
	print "[Skin] Error: Adding %s GUI skin '%s' has failed!" % (name, config.skin.primary_skin.value)
	result.append(skin)

# Add the front panel / display / lcd skin.
result = []
for skin, name in [(config.skin.display_skin.value, "current"), (DEFAULT_DISPLAY_SKIN, "default")]:
	if skin in result:  # Don't try to add a skin that has already failed.
		continue
	config.skin.display_skin.value = skin
	if addSkin(config.skin.display_skin.value, scope=SCOPE_CURRENT_SKIN):
		break
	print "[Skin] Error: Adding %s display skin '%s' has failed!" % (name, config.skin.display_skin.value)
	result.append(skin)

# Add an optional adjustment skin as some boxes lie about their dimensions.
# addSkin(BOX_SKIN, scope=SCOPE_CURRENT_SKIN)

# Add an optional discrete second infobar skin.
# addSkin(SECOND_INFOBAR_SKIN, scope=SCOPE_CURRENT_SKIN)

# Add the subtitle skin.
addSkin(SUBTITLE_SKIN, scope=SCOPE_CURRENT_SKIN)

# Add the emergency skin.  This skin should provide enough functionality
# to enable basic GUI functions to work.
if config.skin.primary_skin.value != EMERGENCY_SKIN:
	addSkin(EMERGENCY_SKIN, scope=SCOPE_CURRENT_SKIN)

# Remove global working variables.
del skin
del name
del result

profile("LoadSkinDefaultDone")


class SkinError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return "[Skin] {%s}: %s!  Please contact the skin's author!" % (config.skin.primary_skin.value, self.msg)

# Convert a coordinate string into a number.  Used to convert object position and
# size attributes into a number.
#    s is the input string.
#    e is the the parent object size to do relative calculations on parent
#    size is the size of the object size (e.g. width or height)
#    font is a font object to calculate relative to font sizes
# Note some constructs for speeding up simple cases that are very common.
#
# Can do things like:  10+center-10w+4%
# To center the widget on the parent widget,
#    but move forward 10 pixels and 4% of parent width
#    and 10 character widths backward
# Multiplication, division and subexpressions are also allowed: 3*(e-c/2)
#
# Usage:  center : Center the object on parent based on parent size and object size.
#         e      : Take the parent size/width.
#         c      : Take the center point of parent size/width.
#         %      : Take given percentage of parent size/width.
#         w      : Multiply by current font width.
#         h      : Multiply by current font height.
#
def parseCoordinate(s, e, size=0, font=None):
	s = s.strip()
	if s == "center":  # For speed as this can be common case.
		val = 0 if not size else (e - size) / 2
	elif s == "*":
		return None
	else:
		try:
			val = int(s)  # For speed try a simple number first.
		except ValueError:
			if "t" in s:
				s = s.replace("center", str((e - size) / 2.0))
			if "e" in s:
				s = s.replace("e", str(e))
			if "c" in s:
				s = s.replace("c", str(e / 2.0))
			if "w" in s:
				s = s.replace("w", "*%s" % str(fonts[font][3]))
			if "h" in s:
				s = s.replace("h", "*%s" % str(fonts[font][2]))
			if "%" in s:
				s = s.replace("%", "*%s" % str(e / 100.0))
			try:
				val = int(s)  # For speed try a simple number first.
			except ValueError:
				val = int(eval(s))
	# print "[Skin] DEBUG: parseCoordinate s='%s', e='%s', size=%s, font='%s', val='%s'" % (s, e, size, font, val)
	if val < 0:
		val = 0
	return val

def getParentSize(object, desktop):
	if object:
		parent = object.getParent()
		# For some widgets (e.g. ScrollLabel) the skin attributes are applied to a
		# child widget, instead of to the widget itself.  In that case, the parent
		# we have here is not the real parent, but it is the main widget.  We have
		# to go one level higher to get the actual parent.  We can detect this
		# because the 'parent' will not have a size yet.  (The main widget's size
		# will be calculated internally, as soon as the child widget has parsed the
		# skin attributes.)
		if parent and parent.size().isEmpty():
			parent = parent.getParent()
		if parent:
			return parent.size()
		elif desktop:
			# Widget has no parent, use desktop size instead for relative coordinates.
			return desktop.size()
	return eSize()

def parseValuePair(s, scale, object=None, desktop=None, size=None):
	x, y = s.split(",")
	parentsize = eSize()
	if object and ("c" in x or "c" in y or "e" in x or "e" in y or "%" in x or "%" in y):  # Need parent size for ce%
		parentsize = getParentSize(object, desktop)
	xval = parseCoordinate(x, parentsize.width(), size and size.width() or 0)
	yval = parseCoordinate(y, parentsize.height(), size and size.height() or 0)
	return (xval * scale[0][0] / scale[0][1], yval * scale[1][0] / scale[1][1])

def parsePosition(s, scale, object=None, desktop=None, size=None):
	return ePoint(*parseValuePair(s, scale, object, desktop, size))

def parseSize(s, scale, object=None, desktop=None):
	return eSize(*parseValuePair(s, scale, object, desktop))

def parseFont(s, scale=((1, 1), (1, 1))):
	if ";" in s:
		name, size = s.split(";")
	else:
		name = s
		size = None
	try:
		f = fonts[name]
		name = f[0]
		size = f[1] if size is None else size
	except KeyError:
		if name not in getFontFaces():
			f = fonts["Body"]
			print "[Skin] Error: Font '%s' (in '%s') is not defined!  Using 'Body' font ('%s') instead." % (name, s, f[0])
			name = f[0]
			size = f[1] if size is None else size
	return gFont(name, int(size) * scale[0][0] / scale[0][1])

def parseColor(s):
	if s[0] != "#":
		try:
			return colorNames[s]
		except KeyError:
			raise SkinError("Color '%s' must be #aarrggbb or valid named color" % s)
	return gRGB(int(s[1:], 0x10))

def parseParameter(s):
	"""This function is responsible for parsing parameters in the skin, it can parse integers, floats, hex colors, hex integers, named colors and strings."""
	if s[0] == "*":
		return s[1:]
	elif s[0] == "#":
		return int(s[1:], 16)
	elif s[:2] == "0x":
		return int(s, 16)
	elif "." in s:
		return float(s)
	elif s in colorNames:
		return colorNames[s].argb()
	else:
		return int(s)

def collectAttributes(skinAttributes, node, context, skinPath=None, ignore=(), filenames=frozenset(("pixmap", "pointer", "seek_pointer", "backgroundPixmap", "selectionPixmap", "sliderPixmap", "scrollbarSliderPicture", "scrollbarbackgroundPixmap", "scrollbarBackgroundPicture"))):
	# Walk all attributes.
	size = None
	pos = None
	font = None
	for attrib, value in node.items():
		if attrib not in ignore:
			if attrib in filenames:
				value = resolveFilename(SCOPE_CURRENT_SKIN, value, path_prefix=skinPath)
			# Bit of a hack this, really.  When a window has a flag (e.g. wfNoBorder)
			# it needs to be set at least before the size is set, in order for the
			# window dimensions to be calculated correctly in all situations.
			# If wfNoBorder is applied after the size has been set, the window will
			# fail to clear the title area.  Similar situation for a scrollbar in a
			# listbox; when the scrollbar setting is applied after the size, a scrollbar
			# will not be shown until the selection moves for the first time.
			if attrib == "size":
				size = value.encode("utf-8")
			elif attrib == "position":
				pos = value.encode("utf-8")
			elif attrib == "font":
				font = value.encode("utf-8")
				skinAttributes.append((attrib, font))
			else:
				skinAttributes.append((attrib, value.encode("utf-8")))
	if pos is not None:
		pos, size = context.parse(pos, size, font)
		skinAttributes.append(("position", pos))
	if size is not None:
		skinAttributes.append(("size", size))

def morphRcImagePath(value):
	if rc_model.rcIsDefault() is False:
		if value in ("/usr/share/enigma2/skin_default/rc.png", "/usr/share/enigma2/skin_default/rcold.png"):  # OpenPLi version.
			value = rc_model.getRcImg()
		# if ("rc.png" or "oldrc.png") in value:  # OpenViX version.
		# 	value = "%src.png" % rc_model.getRcLocation()
	return value

def loadPixmap(path, desktop):
	option = path.find("#")
	if option != -1:
		path = path[:option]
	ptr = LoadPixmap(morphRcImagePath(path), desktop)
	if ptr is None:
		raise SkinError("Pixmap file '%s' not found" % path)
	return ptr

class AttributeParser:
	def __init__(self, guiObject, desktop, scale=((1, 1), (1, 1))):
		self.guiObject = guiObject
		self.desktop = desktop
		self.scaleTuple = scale

	def applyOne(self, attrib, value):
		try:
			getattr(self, attrib)(value)
		except AttributeError:
			print "[Skin] Attribute '%s' (with value of '%s') not implemented!" % (attrib, value)
		except SkinError, ex:
			print "[Skin] Error:", ex

	def applyAll(self, attrs):
		for attrib, value in attrs:
			self.applyOne(attrib, value)

	def conditional(self, value):
		pass

	def objectTypes(self, value):
		pass

	def position(self, value):
		if isinstance(value, tuple):
			self.guiObject.move(ePoint(*value))
		else:
			self.guiObject.move(parsePosition(value, self.scaleTuple, self.guiObject, self.desktop, self.guiObject.csize()))

	def size(self, value):
		if isinstance(value, tuple):
			self.guiObject.resize(eSize(*value))
		else:
			self.guiObject.resize(parseSize(value, self.scaleTuple, self.guiObject, self.desktop))

	def animationPaused(self, value):
		pass

# OpenPLi is missing the C++ code to support this animation method.
#
# 	def animationMode(self, value):
# 		try:
# 			self.guiObject.setAnimationMode({
# 				"disable": 0x00,
# 				"off": 0x00,
# 				"offshow": 0x10,
# 				"offhide": 0x01,
# 				"onshow": 0x01,
# 				"onhide": 0x10,
# 			}[value])
# 		except KeyError:
#			print "[Skin] Error: Invalid animationMode '%s'!  Must be one of 'disable', 'off', 'offshow', 'offhide', 'onshow' or 'onhide'." % value

	def title(self, value):
		self.guiObject.setTitle(_(value))

	def text(self, value):
		self.guiObject.setText(_(value))

	def font(self, value):
		self.guiObject.setFont(parseFont(value, self.scaleTuple))

	def secondfont(self, value):
		self.guiObject.setSecondFont(parseFont(value, self.scaleTuple))

	def zPosition(self, value):
		self.guiObject.setZPosition(int(value))

	def itemHeight(self, value):
		self.guiObject.setItemHeight(int(value))

	def pixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setPixmap(ptr)

	def backgroundPixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setBackgroundPicture(ptr)

	def selectionPixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setSelectionPicture(ptr)

	def sliderPixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setSliderPicture(ptr)

	def scrollbarbackgroundPixmap(self, value):
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setScrollbarBackgroundPicture(ptr)

	def scrollbarSliderPicture(self, value):  # For compatibility same as sliderPixmap.
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setSliderPicture(ptr)

	def scrollbarBackgroundPicture(self, value):  # For compatibility same as scrollbarbackgroundPixmap.
		ptr = loadPixmap(value, self.desktop)
		self.guiObject.setScrollbarBackgroundPicture(ptr)

	def alphatest(self, value):
		try:
			self.guiObject.setAlphatest({
				"on": 1,
				"off": 0,
				"blend": 2,
			}[value])
		except KeyError:
			print "[Skin] Error: Invalid alphatest '%s'!  Must be one of 'on', 'off' or 'blend'." % value

	def scale(self, value):
		value = 1 if value.lower() in ("1", "enabled", "on", "scale", "true", "yes") else 0
		self.guiObject.setScale(value)

	def orientation(self, value):  # used by eSlider
		try:
			self.guiObject.setOrientation(*{
				"orVertical": (self.guiObject.orVertical, False),
				"orTopToBottom": (self.guiObject.orVertical, False),
				"orBottomToTop": (self.guiObject.orVertical, True),
				"orHorizontal": (self.guiObject.orHorizontal, False),
				"orLeftToRight": (self.guiObject.orHorizontal, False),
				"orRightToLeft": (self.guiObject.orHorizontal, True),
			}[value])
		except KeyError:
			print "[Skin] Error: Invalid orientation '%s'!  Must be one of 'orVertical', 'orTopToBottom', 'orBottomToTop', 'orHorizontal', 'orLeftToRight' or 'orRightToLeft'." % value

	def valign(self, value):
		try:
			self.guiObject.setVAlign({
				"top": self.guiObject.alignTop,
				"center": self.guiObject.alignCenter,
				"bottom": self.guiObject.alignBottom
			}[value])
		except KeyError:
			print "[Skin] Error: Invalid valign '%s'!  Must be one of 'top', 'center' or 'bottom'." % value

	def halign(self, value):
		try:
			self.guiObject.setHAlign({
				"left": self.guiObject.alignLeft,
				"center": self.guiObject.alignCenter,
				"right": self.guiObject.alignRight,
				"block": self.guiObject.alignBlock
			}[value])
		except KeyError:
			print "[Skin] Error: Invalid halign '%s'!  Must be one of 'left', 'center', 'right' or 'block'." % value

	def textOffset(self, value):
		x, y = value.split(",")
		self.guiObject.setTextOffset(ePoint(int(x) * self.scaleTuple[0][0] / self.scaleTuple[0][1], int(y) * self.scaleTuple[1][0] / self.scaleTuple[1][1]))

	def flags(self, value):
		flags = value.split(",")
		for f in flags:
			try:
				fv = eWindow.__dict__[f]
				self.guiObject.setFlag(fv)
			except KeyError:
				print "[Skin] Error: Invalid flag '%s'!" % f

	def backgroundColor(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))

	def backgroundColorSelected(self, value):
		self.guiObject.setBackgroundColorSelected(parseColor(value))

	def foregroundColor(self, value):
		self.guiObject.setForegroundColor(parseColor(value))

	def foregroundColorSelected(self, value):
		self.guiObject.setForegroundColorSelected(parseColor(value))

	def foregroundNotCrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value))

	def backgroundNotCrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))

	def foregroundCrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value))

	def backgroundCrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))

	def foregroundEncrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value))

	def backgroundEncrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))

	def shadowColor(self, value):
		self.guiObject.setShadowColor(parseColor(value))

	def selectionDisabled(self, value):
		self.guiObject.setSelectionEnable(0)

	def transparent(self, value):
		self.guiObject.setTransparent(int(value))

	def borderColor(self, value):
		self.guiObject.setBorderColor(parseColor(value))

	def borderWidth(self, value):
		self.guiObject.setBorderWidth(int(value))

	def scrollbarSliderBorderWidth(self, value):
		self.guiObject.setScrollbarSliderBorderWidth(int(value))

	def scrollbarWidth(self, value):
		self.guiObject.setScrollbarWidth(int(value))

	def scrollbarSliderBorderColor(self, value):
		self.guiObject.setSliderBorderColor(parseColor(value))

	def scrollbarSliderForegroundColor(self, value):
		self.guiObject.setSliderForegroundColor(parseColor(value))

	def scrollbarMode(self, value):
		try:
			self.guiObject.setScrollbarMode({
				"showOnDemand": self.guiObject.showOnDemand,
				"showAlways": self.guiObject.showAlways,
				"showNever": self.guiObject.showNever,
				"showLeft": self.guiObject.showLeft
			}[value])
		except KeyError:
			print "[Skin] Error: Invalid scrollbarMode '%s'!  Must be one of 'showOnDemand', 'showAlways', 'showNever' or 'showLeft'." % value

	def enableWrapAround(self, value):
		value = True if value.lower() in ("1", "enabled", "enablewraparound", "on", "true", "yes") else False
		self.guiObject.setWrapAround(value)

	def itemHeight(self, value):
		self.guiObject.setItemHeight(int(value))

	def pointer(self, value):
		(name, pos) = value.split(":")
		pos = parsePosition(pos, self.scaleTuple)
		ptr = loadPixmap(name, self.desktop)
		self.guiObject.setPointer(0, ptr, pos)

	def seek_pointer(self, value):
		(name, pos) = value.split(":")
		pos = parsePosition(pos, self.scaleTuple)
		ptr = loadPixmap(name, self.desktop)
		self.guiObject.setPointer(1, ptr, pos)

	def shadowOffset(self, value):
		self.guiObject.setShadowOffset(parsePosition(value, self.scaleTuple))

	def noWrap(self, value):
		value = 1 if value.lower() in ("1", "enabled", "nowrap", "on", "true", "yes") else 0
		self.guiObject.setNoWrap(value)

def applySingleAttribute(guiObject, desktop, attrib, value, scale=((1, 1), (1, 1))):
	# Is anyone still using applySingleAttribute?
	AttributeParser(guiObject, desktop, scale).applyOne(attrib, value)

def applyAllAttributes(guiObject, desktop, attributes, scale):
	AttributeParser(guiObject, desktop, scale).applyAll(attributes)

def loadSingleSkinData(desktop, domSkin, pathSkin, scope=SCOPE_CURRENT_SKIN):
	"""Loads skin data like colors, windowstyle etc."""
	assert domSkin.tag == "skin", "root element in skin must be 'skin'!"
	global colorNames, fonts, menus, parameters, setups, switchPixmap
	for tag in domSkin.findall("output"):
		id = tag.attrib.get("id")
		if id:
			id = int(id)
		else:
			id = GUI_SKIN_ID
		if id == GUI_SKIN_ID:
			for res in tag.findall("resolution"):
				xres = res.attrib.get("xres")
				xres = int(xres) if xres else 720
				yres = res.attrib.get("yres")
				yres = int(yres) if yres else 576
				bpp = res.attrib.get("bpp")
				bpp = int(bpp) if bpp else 32
				# print "[Skin] Resolution xres=%d, yres=%d, bpp=%d." % (xres, yres, bpp)
				from enigma import gMainDC
				gMainDC.getInstance().setResolution(xres, yres)
				desktop.resize(eSize(xres, yres))
				if bpp != 32:
					# Load palette (Not yet implemented!)
					pass
				if yres >= 1080:
					parameters["AboutHddSplit"] = 1
					parameters["AutotimerListChannels"] = (2, 60, 4, 32)
					parameters["AutotimerListDays"] = (1, 40, 5, 25)
					parameters["AutotimerListHasTimespan"] = (154, 4, 150, 25)
					parameters["AutotimerListIcon"] = (3, -1, 36, 36)
					parameters["AutotimerListRectypeicon"] = (39, 4, 30, 30)
					parameters["AutotimerListTimerName"] = (76, 4, 26, 32)
					parameters["AutotimerListTimespan"] = (2, 40, 5, 25)
					parameters["ChoicelistDash"] = (0, 3, 1000, 30)
					parameters["ChoicelistIcon"] = (7, 0, 52, 38)
					parameters["ChoicelistName"] = (68, 3, 1000, 30)
					parameters["ChoicelistNameSingle"] = (7, 3, 1000, 30)
					parameters["ConfigListSeperator"] = 500
					parameters["DreamexplorerIcon"] = (15, 4, 30, 30)
					parameters["DreamexplorerName"] = (62, 0, 1200, 38)
					parameters["FileListIcon"] = (7, 4, 52, 37)
					parameters["FileListMultiIcon"] = (45, 4, 30, 30)
					parameters["FileListMultiLock"] = (2, 0, 36, 36)
					parameters["FileListMultiName"] = (90, 3, 1000, 32)
					parameters["FileListName"] = (68, 4, 1000, 34)
					parameters["HelpMenuListExtHlp0"] = (0, 0, 900, 39)
					parameters["HelpMenuListExtHlp1"] = (0, 42, 900, 30)
					parameters["HelpMenuListHlp"] = (0, 0, 900, 42)
					parameters["PartnerBoxBouquetListName"] = (0, 0, 45)
					parameters["PartnerBoxChannelListName"] = (0, 0, 45)
					parameters["PartnerBoxChannelListTime"] = (0, 78, 225, 30)
					parameters["PartnerBoxChannelListTitle"] = (0, 42, 30)
					parameters["PartnerBoxE1TimerState"] = (255, 78, 255, 30)
					parameters["PartnerBoxE1TimerTime"] = (0, 78, 255, 30)
					parameters["PartnerBoxE2TimerIcon"] = (1050, 8, 20, 20)
					parameters["PartnerBoxE2TimerIconRepeat"] = (1050, 38, 20, 20)
					parameters["PartnerBoxE2TimerState"] = (225, 78, 225, 30)
					parameters["PartnerBoxE2TimerTime"] = (0, 78, 225, 30)
					parameters["PartnerBoxEntryListIP"] = (180, 2, 225, 38)
					parameters["PartnerBoxEntryListName"] = (8, 2, 225, 38)
					parameters["PartnerBoxEntryListPort"] = (405, 2, 150, 38)
					parameters["PartnerBoxEntryListType"] = (615, 2, 150, 38)
					parameters["PartnerBoxTimerName"] = (0, 42, 30)
					parameters["PartnerBoxTimerServicename"] = (0, 0, 45)
					parameters["PicturePlayerThumb"] = (30, 285, 45, 300, 30, 25)
					parameters["PlayListIcon"] = (7, 7, 24, 24)
					parameters["PlayListName"] = (38, 2, 1000, 34)
					parameters["PluginBrowserDescr"] = (180, 42, 25)
					parameters["PluginBrowserDownloadDescr"] = (120, 42, 25)
					parameters["PluginBrowserDownloadIcon"] = (15, 0, 90, 76)
					parameters["PluginBrowserDownloadName"] = (120, 8, 38)
					parameters["PluginBrowserIcon"] = (15, 8, 150, 60)
					parameters["PluginBrowserName"] = (180, 8, 38)
					parameters["SHOUTcastListItem"] = (30, 27, 35, 96, 35, 33, 60, 32)
					parameters["SelectionListDescr"] = (45, 6, 1000, 45)
					parameters["SelectionListLock"] = (0, 2, 36, 36)
					parameters["ServiceInfoLeft"] = (0, 0, 450, 45)
					parameters["ServiceInfoRight"] = (450, 0, 1000, 45)
					parameters["VirtualKeyBoard"] = (68, 68)
					parameters["VirtualKeyBoardAlignment"] = (0, 0)
					parameters["VirtualKeyBoardPadding"] = (7, 7)
					parameters["VirtualKeyBoardShiftColors"] = (0x00ffffff, 0x00ffffff, 0x0000ffff, 0x00ff00ff)
	for tag in domSkin.findall("include"):
		filename = tag.attrib.get("filename")
		if filename:
			filename = resolveFilename(scope, filename, path_prefix=pathSkin)
			if fileExists(filename):
				print "[Skin] Loading included file '%s'." % filename
				loadSkin(filename, desktop=desktop, scope=scope)
			else:
				print "[Skin] Error: Included file '%s' not found!" % filename
	for tag in domSkin.findall("switchpixmap"):
		for pixmap in tag.findall("pixmap"):
			name = pixmap.attrib.get("name")
			if not name:
				raise SkinError("Pixmap needs name attribute")
			filename = pixmap.attrib.get("filename")
			if not filename:
				raise SkinError("Pixmap needs filename attribute")
			resolved = resolveFilename(scope, filename, path_prefix=pathSkin)
			if fileExists(resolved):
				switchPixmap[name] = LoadPixmap(resolved, cached=True)
			else:
				raise SkinError("The switchpixmap pixmap filename='%s' (%s) not found" % (filename, resolved))
	for tag in domSkin.findall("colors"):
		for color in tag.findall("color"):
			name = color.attrib.get("name")
			color = color.attrib.get("value")
			if name and color:
				colorNames[name] = parseColor(color)
				# print "[Skin] Color name='%s', color='%s'." % (name, color)
			else:
				raise SkinError("Tag 'color' needs a name and color, got name='%s' and color='%s'" % (name, color))
	for tag in domSkin.findall("fonts"):
		for font in tag.findall("font"):
			filename = font.attrib.get("filename", "<NONAME>")
			name = font.attrib.get("name", "Regular")
			scale = font.attrib.get("scale")
			if scale:
				scale = int(scale)
			else:
				scale = 100
			isReplacement = font.attrib.get("replacement") and True or False
			render = font.attrib.get("render")
			if render:
				render = int(render)
			else:
				render = 0
			filename = resolveFilename(SCOPE_FONTS, filename, path_prefix=pathSkin)
			addFont(filename, name, scale, isReplacement, render)
			# print "[Skin] Add font: Font path='%s', name='%s', scale=%d, isReplacement=%s, render=%d." % (filename, name, scale, isReplacement, render)
		fallbackFont = resolveFilename(SCOPE_FONTS, "fallback.font", path_prefix=pathSkin)
		if fileExists(fallbackFont):
			addFont(fallbackFont, "Fallback", 100, -1, 0)
		for alias in tag.findall("alias"):
			try:
				name = alias.attrib.get("name")
				font = alias.attrib.get("font")
				size = int(alias.attrib.get("size"))
				height = int(alias.attrib.get("height", size))  # To be calculated some day.
				width = int(alias.attrib.get("width", size))
				fonts[name] = (font, size, height, width)
				# print "[Skin] Add font alias: name='%s', font='%s', size=%d, height=%s, width=%d." % (name, font, size, height, width)
			except Exception, ex:
				print "[Skin] Error: Bad font alias -", ex
	for tag in domSkin.findall("parameters"):
		for parameter in tag.findall("parameter"):
			try:
				name = parameter.attrib.get("name")
				value = parameter.attrib.get("value")
				parameters[name] = "," in value and map(parseParameter, value.split(",")) or parseParameter(value)
			except Exception, ex:
				print "[Skin] Bad parameter:", ex
	for tag in domSkin.findall("menus"):
		for setup in tag.findall("menu"):
			key = setup.attrib.get("key")
			image = setup.attrib.get("image")
			if key and image:
				menus[key] = image
				# print "[Skin] Menu key='%s', image='%s'." % (key, image)
			else:
				raise SkinError("Tag menu needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("setups"):
		for setup in tag.findall("setup"):
			key = setup.attrib.get("key")
			image = setup.attrib.get("image")
			if key and image:
				setups[key] = image
				# print "[Skin] Setup: '%s' -> '%s'" % (key, image)
			else:
				raise SkinError("Tag setup needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("subtitles"):
		from enigma import eSubtitleWidget
		scale = ((1, 1), (1, 1))
		for substyle in tag.findall("sub"):
			font = parseFont(substyle.attrib.get("font"), scale)
			col = substyle.attrib.get("foregroundColor")
			if col:
				foregroundColor = parseColor(col)
				haveColor = 1
			else:
				foregroundColor = gRGB(0xFFFFFF)
				haveColor = 0
			col = substyle.attrib.get("borderColor")
			if col:
				borderColor = parseColor(col)
			else:
				borderColor = gRGB(0)
			borderwidth = substyle.attrib.get("borderWidth")
			if borderwidth is None:
				# Default: Use a subtitle border.
				borderWidth = 3
			else:
				borderWidth = int(borderwidth)
			face = eSubtitleWidget.__dict__[substyle.attrib.get("name")]
			eSubtitleWidget.setFontStyle(face, font, haveColor, foregroundColor, borderColor, borderWidth)
	for tag in domSkin.findall("windowstyle"):
		style = eWindowStyleSkinned()
		styleId = tag.attrib.get("id")
		if styleId:
			styleId = int(styleId)
		else:
			styleId = GUI_SKIN_ID
		font = gFont("Regular", 20)  # Default
		offset = eSize(20, 5)  # Default
		for title in tag.findall("title"):
			offset = parseSize(title.attrib.get("offset"), ((1, 1), (1, 1)))
			font = parseFont(title.attrib.get("font"), ((1, 1), (1, 1)))
		style.setTitleFont(font)
		style.setTitleOffset(offset)
		# print "[Skin] WindowStyle font, offset:", font, offset
		for borderset in tag.findall("borderset"):
			bsName = str(borderset.attrib.get("name"))
			for pixmap in borderset.findall("pixmap"):
				bpName = pixmap.attrib.get("pos")
				filename = pixmap.attrib.get("filename")
				if filename and bpName:
					png = loadPixmap(resolveFilename(scope, filename, path_prefix=pathSkin), desktop)
					style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png)
				# print "[Skin] WindowStyle borderset name, filename:", bpName, filename
		for color in tag.findall("color"):
			colorType = color.attrib.get("name")
			color = parseColor(color.attrib.get("color"))
			try:
				style.setColor(eWindowStyleSkinned.__dict__["col" + colorType], color)
			except Exception:
				raise SkinError("Unknown color type '%s'" % colorType)
				# pass
			# print "[Skin] WindowStyle color type, color:", type, color
		x = eWindowStyleManager.getInstance()
		x.setStyle(styleId, style)
	for tag in domSkin.findall("margin"):
		styleId = tag.attrib.get("id")
		if styleId:
			styleId = int(styleId)
		else:
			styleId = GUI_SKIN_ID
		r = eRect(0, 0, 0, 0)
		v = tag.attrib.get("left")
		if v:
			r.setLeft(int(v))
		v = tag.attrib.get("top")
		if v:
			r.setTop(int(v))
		v = tag.attrib.get("right")
		if v:
			r.setRight(int(v))
		v = tag.attrib.get("bottom")
		if v:
			r.setBottom(int(v))
		# The "desktop" parameter is hard-coded to the GUI screen, so we must ask
		# for the one that this actually applies to.
		getDesktop(styleId).setMargins(r)

# Now a utility for plugins to add skin data to the screens.
#
def loadSkin(filename, desktop=None, scope=SCOPE_SKIN):
	global domScreens
	filename = resolveFilename(scope, filename)
	try:
		# This open gets around a possible file handle leak in Python's XML parser.
		with open(filename, "r") as fd:
			try:
				domSkin = xml.etree.cElementTree.parse(fd).getroot()
				if desktop is not None:
					loadSingleSkinData(desktop, domSkin, filename, scope=scope)
				for element in domSkin:
					name = evaluateElement(element, DISPLAY_SKIN_ID)
					if name is None:
						element.clear()
					else:
						domScreens[name] = (element, "%s/" % os.path.dirname(filename))
			except xml.etree.cElementTree.ParseError as e:
				fd.seek(0)
				content = fd.readlines()
				line, column = e.position
				print "[Skin] XML Parse Error: '%s' in '%s'!" % (e, filename)
				data = content[line - 1].replace("\t", " ").rstrip()
				print "[Skin] XML Parse Error: '%s'" % data
				print "[Skin] XML Parse Error: '%s^%s'" % ("-" * column, " " * (len(data) - column - 1))
			except Exception as e:
				print "[Skin] Error: Unable to parse skin data in '%s' - '%s'!" % (filename, e)
	except IOError as e:
		if e.errno == errno.ENOENT:  #  No such file or directory
			print "[Skin] Warning: Skin file '%s' does not exist!" % filename
		else:
			print "[Skin] Error %d: Opening skin file '%s'! (%s)" % (e.errno, filename, os.strerror(e.errno))
	except Exception as e:
		print "[Skin] Error: Unexpected error opening skin file '%s'! (%s)" % (filename, e)

# Kinda hackish, but this is called once by mytest.py.
#
def loadSkinData(desktop):
	global domSkins
	skins = domSkins[:]
	skins.reverse()
	for (scope, pathSkin, domSkin) in skins:
		loadSingleSkinData(desktop, domSkin, pathSkin, scope=scope)
		for element in domSkin:
			name = evaluateElement(element, DISPLAY_SKIN_ID)
			if name is None:
				element.clear()
			else:
				domScreens[name] = (element, pathSkin)
	# No longer needed, we know where the screens are now.
	del domSkins

def evaluateElement(element, screenID):
	if element.tag == "screen":  # If non-screen element, no need for it any longer.
		name = element.attrib.get("name", None)
		if name:  # Without a name, it's useless!
			sid = element.attrib.get("id", None)
			if not sid or (sid == screenID):  # If for this display.
				return name
	return None

class additionalWidget:
	def __init__(self):
		pass


# Class that makes a tuple look like something else. Some plugins just assume
# that size is a string and try to parse it. This class makes that work.
class SizeTuple(tuple):
	def split(self, *args):
		return str(self[0]), str(self[1])

	def strip(self, *args):
		return "%s,%s" % self

	def __str__(self):
		return "%s,%s" % self


class SkinContext:
	def __init__(self, parent=None, pos=None, size=None, font=None):
		if parent is not None:
			if pos is not None:
				pos, size = parent.parse(pos, size, font)
				self.x, self.y = pos
				self.w, self.h = size
			else:
				self.x = None
				self.y = None
				self.w = None
				self.h = None

	def __str__(self):
		return "Context (%s,%s)+(%s,%s) " % (self.x, self.y, self.w, self.h)

	def parse(self, pos, size, font):
		if pos == "fill":
			pos = (self.x, self.y)
			size = (self.w, self.h)
			self.w = 0
			self.h = 0
		else:
			w, h = size.split(",")
			w = parseCoordinate(w, self.w, 0, font)
			h = parseCoordinate(h, self.h, 0, font)
			if pos == "bottom":
				pos = (self.x, self.y + self.h - h)
				size = (self.w, h)
				self.h -= h
			elif pos == "top":
				pos = (self.x, self.y)
				size = (self.w, h)
				self.h -= h
				self.y += h
			elif pos == "left":
				pos = (self.x, self.y)
				size = (w, self.h)
				self.x += w
				self.w -= w
			elif pos == "right":
				pos = (self.x + self.w - w, self.y)
				size = (w, self.h)
				self.w -= w
			else:
				size = (w, h)
				pos = pos.split(",")
				pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font), self.y + parseCoordinate(pos[1], self.h, size[1], font))
		return (SizeTuple(pos), SizeTuple(size))


# A context that stacks things instead of aligning them.
#
class SkinContextStack(SkinContext):
	def parse(self, pos, size, font):
		if pos == "fill":
			pos = (self.x, self.y)
			size = (self.w, self.h)
		else:
			w, h = size.split(",")
			w = parseCoordinate(w, self.w, 0, font)
			h = parseCoordinate(h, self.h, 0, font)
			if pos == "bottom":
				pos = (self.x, self.y + self.h - h)
				size = (self.w, h)
			elif pos == "top":
				pos = (self.x, self.y)
				size = (self.w, h)
			elif pos == "left":
				pos = (self.x, self.y)
				size = (w, self.h)
			elif pos == "right":
				pos = (self.x + self.w - w, self.y)
				size = (w, self.h)
			else:
				size = (w, h)
				pos = pos.split(",")
				pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font), self.y + parseCoordinate(pos[1], self.h, size[1], font))
		return (SizeTuple(pos), SizeTuple(size))

def readSkin(screen, skin, names, desktop):
	if not isinstance(names, list):
		names = [names]
	# Try all skins, first existing one has priority.
	for n in names:
		myScreen, path = domScreens.get(n, (None, None))
		if myScreen is not None:
			# Use this name for debug output.
			name = n
			break
	else:
		name = "<embedded-in-%s>" % screen.__class__.__name__
	# Otherwise try embedded skin.
	if myScreen is None:
		myScreen = getattr(screen, "parsedSkin", None)
	# Try uncompiled embedded skin.
	if myScreen is None and getattr(screen, "skin", None):
		skin = screen.skin
		print "[Skin] Parsing embedded skin '%s'." % name
		if isinstance(skin, tuple):
			for s in skin:
				candidate = xml.etree.cElementTree.fromstring(s)
				if candidate.tag == "screen":
					sid = candidate.attrib.get("id", None)
					if (not sid) or (int(sid) == DISPLAY_SKIN_ID):
						myScreen = candidate
						break
			else:
				print "[Skin] No suitable screen found!"
		else:
			myScreen = xml.etree.cElementTree.fromstring(skin)
		if myScreen:
			screen.parsedSkin = myScreen
	if myScreen is None:
		print "[Skin] No skin to read."
		myScreen = screen.parsedSkin = xml.etree.cElementTree.fromstring("<screen></screen>")
	screen.skinAttributes = []
	skinPath = getattr(screen, "skin_path", path)
	context = SkinContextStack()
	s = desktop.bounds()
	context.x = s.left()
	context.y = s.top()
	context.w = s.width()
	context.h = s.height()
	del s
	collectAttributes(screen.skinAttributes, myScreen, context, skinPath, ignore=("name",))
	context = SkinContext(context, myScreen.attrib.get("position"), myScreen.attrib.get("size"))
	screen.additionalWidgets = []
	screen.renderer = []
	usedComponents = set()

	# Now walk all widgets and stuff
	def processNone(widget, context):
		pass

	def processWidget(widget, context):
		# Okay, we either have 1:1-mapped widgets ("old style"), or 1:n-mapped
		# widgets (source->renderer).
		wname = widget.attrib.get("name")
		wsource = widget.attrib.get("source")
		if wname is None and wsource is None:
			print "[Skin] Error: The widget has no name and no source!"
			return
		if wname:
			# print "[Skin] Widget name='%s'" % wname
			usedComponents.add(wname)
			# Get corresponding "gui" object.
			try:
				attributes = screen[wname].skinAttributes = []
			except Exception:
				raise SkinError("Component with name '%s' was not found in skin of screen '%s'!" % (wname, name))
			# assert screen[wname] is not Source
			collectAttributes(attributes, widget, context, skinPath, ignore=("name",))
		elif wsource:
			# print "[Skin] Widget source='%s'" % wsource
			# Get corresponding source.
			while True:  # Until we found a non-obsolete source
				# Parse our current "wsource", which might specify a "related screen" before the dot,
				# for example to reference a parent, global or session-global screen.
				scr = screen
				# Resolve all path components.
				path = wsource.split(".")
				while len(path) > 1:
					scr = screen.getRelatedScreen(path[0])
					if scr is None:
						# print "[Skin] wsource='%s', name='%s'." % (wsource, name)
						raise SkinError("Specified related screen '%s' was not found in screen '%s'!" % (wsource, name))
					path = path[1:]
				# Resolve the source.
				source = scr.get(path[0])
				if isinstance(source, ObsoleteSource):
					# If we found an "obsolete source", issue warning, and resolve the real source.
					print "[Skin] WARNING: SKIN '%s' USES OBSOLETE SOURCE '%s', USE '%s' INSTEAD!" % (name, wsource, source.new_source)
					print "[Skin] OBSOLETE SOURCE WILL BE REMOVED %s, PLEASE UPDATE!" % source.removal_date
					if source.description:
						print "[Skin] %s" % source.description
					wsource = source.new_source
				else:
					# Otherwise, use the source.
					break
			if source is None:
				raise SkinError("The source '%s' was not found in screen '%s'!" % (wsource, name))
			wrender = widget.attrib.get("render")
			if not wrender:
				raise SkinError("For source '%s' a renderer must be defined with a 'render=' attribute" % wsource)
			for converter in widget.findall("convert"):
				ctype = converter.get("type")
				assert ctype, "[Skin] The 'convert' tag needs a 'type' attribute!"
				# print "[Skin] Converter='%s'" % ctype
				try:
					parms = converter.text.strip()
				except Exception:
					parms = ""
				# print "[Skin] Params='%s'" % parms
				converterClass = my_import(".".join(("Components", "Converter", ctype))).__dict__.get(ctype)
				c = None
				for i in source.downstream_elements:
					if isinstance(i, converterClass) and i.converter_arguments == parms:
						c = i
				if c is None:
					c = converterClass(parms)
					c.connect(source)
				source = c
			rendererClass = my_import(".".join(("Components", "Renderer", wrender))).__dict__.get(wrender)
			renderer = rendererClass()  # Instantiate renderer.
			renderer.connect(source)  # Connect to source.
			attributes = renderer.skinAttributes = []
			collectAttributes(attributes, widget, context, skinPath, ignore=("render", "source"))
			screen.renderer.append(renderer)

	def processApplet(widget, context):
		try:
			codeText = widget.text.strip()
			widgetType = widget.attrib.get("type")
			code = compile(codeText, "skin applet", "exec")
		except Exception, ex:
			raise SkinError("Applet failed to compile: '%s'" % str(ex))
		if widgetType == "onLayoutFinish":
			screen.onLayoutFinish.append(code)
		else:
			raise SkinError("Applet type '%s' is unknown!" % widgetType)

	def processLabel(widget, context):
		w = additionalWidget()
		w.widget = eLabel
		w.skinAttributes = []
		collectAttributes(w.skinAttributes, widget, context, skinPath, ignore=("name",))
		screen.additionalWidgets.append(w)

	def processPixmap(widget, context):
		w = additionalWidget()
		w.widget = ePixmap
		w.skinAttributes = []
		collectAttributes(w.skinAttributes, widget, context, skinPath, ignore=("name",))
		screen.additionalWidgets.append(w)

	def processScreen(widget, context):
		for w in widget.getchildren():
			conditional = w.attrib.get("conditional")
			if conditional and not [i for i in conditional.split(",") if i in screen.keys()]:
				continue
			objecttypes = w.attrib.get("objectTypes", "").split(",")
			if len(objecttypes) > 1 and (objecttypes[0] not in screen.keys() or not [i for i in objecttypes[1:] if i == screen[objecttypes[0]].__class__.__name__]):
				continue
			p = processors.get(w.tag, processNone)
			try:
				p(w, context)
			except SkinError, e:
				print "[Skin] Error in screen '%s' widget '%s':" % (name, w.tag), e

	def processPanel(widget, context):
		n = widget.attrib.get("name")
		if n:
			try:
				s = domScreens[n]
			except KeyError:
				print "[Skin] Error: Unable to find screen '%s' referred in screen '%s'!" % (n, name)
			else:
				processScreen(s[0], context)
		layout = widget.attrib.get("layout")
		if layout == "stack":
			cc = SkinContextStack
		else:
			cc = SkinContext
		try:
			c = cc(context, widget.attrib.get("position"), widget.attrib.get("size"), widget.attrib.get("font"))
		except Exception, ex:
			raise SkinError("Failed to create skin context (position='%s', size='%s', font='%s') in context '%s': %s" % (widget.attrib.get("position"), widget.attrib.get("size"), widget.attrib.get("font"), context, ex))
		processScreen(widget, c)

	processors = {
		None: processNone,
		"widget": processWidget,
		"applet": processApplet,
		"eLabel": processLabel,
		"ePixmap": processPixmap,
		"panel": processPanel
	}

	try:
		msg = " from list '%s'" % ", ".join(names) if len(names) > 1 else ""
		posX = "?" if context.x is None else str(context.x)
		posY = "?" if context.y is None else str(context.y)
		sizeW = "?" if context.w is None else str(context.w)
		sizeH = "?" if context.h is None else str(context.h)
		print "[Skin] Processing screen '%s'%s, position=(%s, %s), size=(%s x %s) for module '%s'." % (name, msg, posX, posY, sizeW, sizeH, screen.__class__.__name__)
		# Reset offsets, all components are relative to screen coordinates.
		context.x = 0
		context.y = 0
		processScreen(myScreen, context)
	except Exception, e:
		print "[Skin] Error in screen '%s':" % name, e

	from Components.GUIComponent import GUIComponent
	unusedComponents = [x for x in set(screen.keys()) - usedComponents if isinstance(x, GUIComponent)]
	assert not unusedComponents, "[Skin] The following components in '%s' don't have a skin entry: %s" % (name, ", ".join(unusedComponents))
	# This may look pointless, but it unbinds "screen" from the nested scope. A better
	# solution is to avoid the nested scope above and use the context object to pass
	# things around.
	screen = None
	usedComponents = None

# Search the domScreens dictionary to see if any of the screen names provided
# have a skin based screen.  This will allow coders to know if the named
# screen will be skinned by the skin code.  A return of None implies that the
# code must provide its own skin for the screen to be displayed to the user.
#
def findSkinScreen(names):
	if not isinstance(names, list):
		names = [names]
	# Try all names given, the first one found is the one that will be used by the skin engine.
	for name in names:
		screen, path = domScreens.get(name, (None, None))
		if screen is not None:
			return name
	return None

def dump(x, i=0):
	print " " * i + str(x)
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except Exception:
		None
