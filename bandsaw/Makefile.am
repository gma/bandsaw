# $Id$

AUTOMAKE_OPTIONS = check-news std-options

edit = sed \
	-e 's,@alerticon\@,$(alerticon),g' \
	-e 's,@gladedir\@,$(gladedir),g' \
	-e 's,@logicon\@,$(logicon),g' \
	-e 's,@logoicon\@,$(logoicon),g' \
	-e 's,@pixmapsdir\@,$(pixmapsdir),g' \
	-e 's,@VERSION\@,$(VERSION),g'

# Required to allow editing with sed.
distcheck-hook:
	find $(distdir) -type d -name src -maxdepth 1 -exec chmod ug+w {} \;

DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper
PYTHON = python

# Process the data directory

Desktopdir = $(datadir)/applications
Desktop_files = data/bandsaw.desktop
Desktop_in_files = $(srcdir)/data/bandsaw.desktop.in
Desktop_DATA = $(Desktop_in_files:.desktop.in=.desktop)

$(Desktop_files): Makefile $(Desktop_in_files)
	rm -f $(srcdir)/$(Desktop_files) $(srcdir)/$(Desktop_files).tmp
	$(edit) $(srcdir)/$(Desktop_in_files) >$(srcdir)/$(Desktop_files).tmp
	mv $(srcdir)/$(Desktop_files).tmp $(srcdir)/$(Desktop_files)

schemadir = $(GCONF_SCHEMA_FILE_DIR)
schema_in_files = $(srcdir)/data/bandsaw.schemas
schema_DATA = $(schema_in_files)

if GCONF_SCHEMAS_INSTALL
install-data-local:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
		$(GCONFTOOL) --makefile-install-rule $(schema_DATA)
endif

# Process the help directory

SUBDIRS = help

scrollkeeper_files = COPYING-DOCS xmldocs.make omf.make

# Even though scrollkeeper files aren't uninstalled, don't fail when
# running "make distcheck".
distuninstallcheck_listfiles = find . -type f -print | grep -v scrollkeeper

# Process the pixmaps directory

pixmapsdir = $(datadir)/pixmaps/bandsaw
pixmaps_DATA = \
	$(srcdir)/pixmaps/bandsaw-alert.png \
	$(srcdir)/pixmaps/bandsaw-log.png \
	$(srcdir)/pixmaps/bandsaw-logo.png

# Process the src directory

bin_SCRIPTS = bandsaw
python_files = src/bandsawconfig.py
python_in_files = $(python_files).in
# dist_scripts = src/bandsaw.py src/bandsawconfig.py.in src/bandsaw_test.py
python_PYTHON = $(python_files)

$(python_files): Makefile $(srcdir)/$(python_in_files)
	rm -f $(srcdir)/$(python_files) $(srcdir)/$(python_files).tmp
	$(edit) $(srcdir)/$(python_in_files) >$(srcdir)/$(python_files).tmp
	mv $(srcdir)/$(python_files).tmp $(srcdir)/$(python_files)

gladedir   = $(datadir)/bandsaw/glade
glade_DATA = $(srcdir)/src/bandsaw.glade

dist_scripts = src/bandsaw.py

all: $(python_files) bandsaw

CLEANFILES = bandsaw $(python_files) $(Desktop_data)

# Run unit tests via "make check"
TESTS_ENVIRONMENT = $(PYTHON)
TESTS = $(srcdir)/src/bandsaw_test.py

# General settings

# Extra files to include in package
EXTRA_DIST = \
	$(bin_SCRIPTS) \
	$(dist_scripts) \
	$(glade_DATA) \
	$(python_in_files) \
	$(schema_in_files) \
	$(Desktop_in_files) \
	$(scrollkeeper_files) \
	$(pixmaps_DATA)
