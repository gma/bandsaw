AC_INIT(src/bandsaw.py)
AM_INIT_AUTOMAKE(bandsaw, 0.3.0, ashtong@users.sf.net)

AM_MAINTAINER_MODE

dnl Test for GConf
AC_PATH_PROG(GCONFTOOL, gconftool-2)
AM_GCONF_SOURCE_2

dnl Test for scrollkeeper
AC_PATH_PROG(SK_CONFIG,scrollkeeper-config,no)
if test x$SK_CONFIG = xno; then
  AC_MSG_ERROR(Couldn't find scrollkeeper-config. Please install the scrollkeeper package: http://scrollkeeper.sourceforge.net)
fi
SCROLLKEEPER_BUILD_REQUIRED=0.3.14

dnl Test for Python
AM_PATH_PYTHON(2.3)

PKG_CHECK_MODULES(PYGTK, pygobject-2.0 pygtk-2.0 gnome-python-2.0 gnome-python-extras-2.0)

AC_SUBST(VERSION)
AC_SUBST(alerticon, bandsaw-alert.png)
AC_SUBST(logicon, bandsaw-log.png)
AC_SUBST(logoicon, bandsaw-logo.png)

AC_OUTPUT(
help/Makefile
help/bandsaw/Makefile
help/bandsaw/C/Makefile
help/bandsaw/C/bandsaw.xml:help/bandsaw/C/bandsaw.xml.in
Makefile
bandsaw:src/bandsaw.py
)
