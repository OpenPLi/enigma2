#
# WARNING: If you modify the files installed here, change the version
# number of the enigma2-fonts package in enigma2.bb.
#
installdir = $(datadir)/fonts

dist_install_DATA = *.ttf

if DM900
dist_install_DATA += wqy-microhei.ttc
install-data-hook:
	cd $(DESTDIR)$(datadir)/fonts && \
	$(LN_S) wqy-microhei.ttc fallback.font
endif

if DM920
dist_install_DATA += wqy-microhei.ttc
install-data-hook:
	cd $(DESTDIR)$(datadir)/fonts && \
	$(LN_S) wqy-microhei.ttc fallback.font
endif
