AUTOMAKE_OPTIONS = check-news dist-bzip2 std-options
DISTCHECK_CONFIGURE_FLAGS = --disable-schemas-install
PYTHON = python

# Python source
bin_SCRIPTS = bandsaw
dist_scripts = src/bandsaw.py src/bandsaw_test.py

# Other files (glade, desktop definitions, etc)
gladedir   = $(datadir)/bandsaw/glade
glade_DATA = $(srcdir)/src/bandsaw.glade

pixmapsdir = $(datadir)/pixmaps
pixmaps_DATA = pixmaps/bandsaw.png

install-exec-hook:
	sed -i -e "s|'bandsaw.glade'|'$(gladedir)/bandsaw.glade'|" \
		$(DESTDIR)/$(bindir)/$(bin_SCRIPTS)
	sed -i -e "s|../pixmaps|$(pixmapsdir)|" \
		$(DESTDIR)/$(bindir)/$(bin_SCRIPTS)
	sed -i -e "s|@pixmapsdir@|$(pixmapsdir)|" \
		$(DESTDIR)/$(bindir)/$(bin_SCRIPTS)

schemadir = $(GCONF_SCHEMA_FILE_DIR)
schema_in_files = data/bandsaw.schemas
schema_DATA = $(schema_in_files)

if GCONF_SCHEMAS_INSTALL
install-data-local:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
		$(GCONFTOOL) --makefile-install-rule $(schema_DATA)
endif

Desktopdir = $(datadir)/applications
Desktop_in_files = $(srcdir)/data/bandsaw.desktop.in
Desktop_DATA = $(Desktop_in_files:.desktop.in=.desktop)

# Run unit tests via "make check"
#TESTS_ENVIRONMENT = $(PYTHON)
#TESTS = $(srcdir)/src/bandsaw_test.py

# Use makefiles in sub directories
SUBDIRS = help

# Scrollkeeper
scrollkeeper_files = COPYING-DOCS xmldocs.make omf.make

# Extra files to include in package
EXTRA_DIST = \
	$(bin_SCRIPTS) \
	$(dist_scripts) \
	$(glade_DATA) \
	$(pixmaps_DATA) \
	$(schema_in_files) \
	$(Desktop_in_files) \
	$(scrollkeeper_files)
