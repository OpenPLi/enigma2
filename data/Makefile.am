SUBDIRS = countries display fonts extensions keymaps skin_default rc_models hw_info

dist_pkgdata_DATA = \
	black.mvi \
	radio.mvi \
	encoding.conf \
	freesat.t1 \
	freesat.t2 \
	groupedservices \
	iso-639-3.pck \
	keymap.xml \
	menu.xml \
	otv_00820000_fbff_16a8.dict \
	otv_011a0000_0002_07d4.dict \
	otv_06180000_1000_0011.dict \
	otv_06400000_00a9_0003.dict \
	rcpositions.xml \
	setup.xml \
	skin_subtitles.xml \
	startwizard.xml \
	timezone.xml \
	unicable.xml

iso-639-3.pck: $(srcdir)/iso-639-3.tab
	python $(srcdir)/convert-iso-639-3.py $< $@
