AC_INIT(src/bandsaw.py)

dnl AM_CONFIG_HEADER(config.h)
AM_INIT_AUTOMAKE(bandsaw, 0.1.0)

AM_MAINTAINER_MODE

dnl Test for GConf
AC_PATH_PROG(GCONFTOOL, gconftool-2)
AM_GCONF_SOURCE_2

dnl Test for scrollkeeper
AC_PATH_PROG(SK_CONFIG,scrollkeeper-config,no)
if test x$SK_CONFIG = xno; then
  AC_MSG_ERROR(Couldn't find scrollkeeper-config. Please install the scrollkeeper package: http://scrollkeeper.sourceforge.net)
fi
dnl SCROLLKEEPER_BUILD_REQUIRED=0.3.14
dnl AC_SUBST SCROLLKEEPER_BUILD_REQUIRED=0.3.14

AM_PATH_PYTHON(2.3)

PKG_CHECK_MODULES(PYGTK, pygtk-2.0)
AC_SUBST(PYGTK_CFLAGS)
AC_SUBST(PYGTK_LIBS)

AC_SUBST(VERSION)

AC_SUBST(iconfile, gnome-log.png)

AC_OUTPUT(
help/bandsaw/C/Makefile
help/bandsaw/Makefile
help/Makefile
Makefile
bandsaw:src/bandsaw.py
data/bandsaw.desktop
)
