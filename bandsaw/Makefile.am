AUTOMAKE_OPTIONS = check-news dist-bzip2 std-options
DISTCHECK_CONFIGURE_FLAGS = --disable-schemas-install
PYTHON = python

# Python source
bin_SCRIPTS = bandsaw
dist_scripts = src/bandsaw.py src/bandsaw_test.py

# Other files (glade, desktop definitions, etc)
gladedir   = $(datadir)/bandsaw/glade
glade_DATA = $(srcdir)/src/bandsaw.glade

install-exec-hook:
	sed -i -e "s|'bandsaw.glade'|'$(gladedir)/bandsaw.glade'|" \
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
Desktop_in_files = $(srcdir)/data/bandsaw.desktop
Desktop_DATA = $(Desktop_in_files)

# Run unit tests via "make check"
TESTS_ENVIRONMENT = $(PYTHON)
TESTS = $(srcdir)/src/bandsaw_test.py

# Extra files to include in package
EXTRA_DIST = \
	$(bin_SCRIPTS) \
	$(dist_scripts) \
	$(glade_DATA) \
	$(schema_in_files) \
	$(Desktop_in_files)
