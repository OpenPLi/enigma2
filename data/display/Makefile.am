installdir = $(pkgdatadir)/display/skin_default

if HAVE_TEXTLCD
DISPLAYTYPE = text
else
DISPLAYTYPE = display
endif

dist_install_DATA = skin_display.xml

# Use box-specific XML if it exists, otherwise get the default
# TEXTSKIN is either "default" or "7segment"
# TODO: Missing dependency on optional "skin_$(DISPLAYTYPE)_$(BOXTYPE).xml"
skin_display.xml:
	cp $(srcdir)/skin_$(DISPLAYTYPE)_$(BOXTYPE).xml $@ 2>/dev/null || cp $(srcdir)/skin_$(DISPLAYTYPE)_$(TEXTSKIN).xml $@
