PYTHON = python
GCONFTOOL = gconftool-2

# Python source
main_script = src/bandsaw.py
test_files = src/bandsaw_test.py

bin_SCRIPTS = $(main_script)

# Other files (glade, desktop definitions, etc)
gladedir   = $(datadir)/bandsaw/glade
glade_DATA = src/bandsaw.glade

schemadir = $(GCONF_SCHEMA_FILE_DIR)
schema_in_files = data/bandsaw.schemas
schema_DATA = $(schema_in_files)

install-data-hook:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
		$(GCONFTOOL) --makefile-install-rule $(schema_DATA)

Desktopdir = $(datadir)/applications
Desktop_in_files = data/bandsaw.desktop
Desktop_DATA = $(Desktop_in_files)

# Run unit tests via "make check"
TESTS_ENVIRONMENT = $(PYTHON)
TESTS = $(srcdir)/src/bandsaw_test.py

# Extra files to include in package
EXTRA_DIST = \
	$(main_script) \
	$(test_files) \
	$(glade_DATA) \
	$(schema_in_files) \
	$(Desktop_in_files)