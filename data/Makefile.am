SUBDIRS = countries fonts extensions keymaps skin_default skin_fallback_1080 rc_models hw_info

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

if HAVE_TEXTLCD
dist_pkgdata_DATA += skin_text.xml
else
dist_pkgdata_DATA += skin_display.xml
endif

skin_display.xml: $(srcdir)/skin_display_default.xml
	test -f $(srcdir)/skin_display_$(BOXTYPE).xml && cp $(srcdir)/skin_display_$(BOXTYPE).xml skin_display.xml || cp $(srcdir)/skin_display_default.xml skin_display.xml

skin_text.xml: $(srcdir)/skin_text_default.xml
	test -f $(srcdir)/skin_text_$(BOXTYPE).xml && cp $(srcdir)/skin_text_$(BOXTYPE).xml skin_text.xml || cp $(srcdir)/skin_text_$(TEXTSKIN).xml skin_text.xml

iso-639-3.pck: $(srcdir)/iso-639-3.tab
	python $(srcdir)/convert-iso-639-3.py $< $@
