SUBDIRS = countries fonts extensions keymaps skin_default skin_fallback_1080 rc_models hw_info

if HAVE_TEXTLCD
DISPLAYTYPE = text
else
DISPLAYTYPE = display
endif

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
	menu.xml \
	prev.png \
	radio.mvi \
	black.mvi \
	rcpositions.xml \
	setup.xml \
	skin_default.xml \
	skin_subtitles.xml \
	skin.xml \
	skin_$(DISPLAYTYPE).xml \
	startwizard.xml \
	freesat.t1 \
	freesat.t2 \
	iso-639-3.pck \
	timezone.xml \
	unicable.xml \
	groupedservices \
	otv_011a0000_0002_07d4.dict \
	otv_00820000_fbff_16a8.dict \
	otv_06180000_1000_0011.dict \
	otv_06400000_00a9_0003.dict

# Use box-specific XML if it exists, otherwise get the default
skin_$(DISPLAYTYPE).xml: $(srcdir)/skin_$(DISPLAYTYPE)_default.xml
	cp $(srcdir)/skin_$(DISPLAYTYPE)_$(BOXTYPE).xml $@ 2>/dev/null || cp $(srcdir)/skin_$(DISPLAYTYPE)_default.xml $@

iso-639-3.pck: $(srcdir)/iso-639-3.tab
	python $(srcdir)/convert-iso-639-3.py $< $@
