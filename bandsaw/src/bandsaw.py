#!/usr/bin/env python
#
# bandsaw.py - A log monitoring and alerting tool for GNOME.
#
# Copyright (C) 2004 Graham Ashton <ashtong@users.sourceforge.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# $Id$



import os
import re
import select
import time

import pygtk; pygtk.require('2.0')
import gconf
import gnome
import gnome.ui
import gobject
import gtk
import gtk.glade


class Config:

    BASE_KEY = '/apps/bandsaw'

    FILTER_ALERTS = 'filter_alerts'
    FILTER_NAMES = 'filter_names'
    FILTER_PATTERNS = 'filter_patterns'
    MESSAGES_KEPT = 'messages_kept'
    NAMED_PIPE = 'named_pipe'
    SUPPRESS_ALERTS = 'suppress_alerts'
    SUPPRESS_MINUTES = 'suppress_minutes'
    
    def __init__(self, client):
        self.client = client

    def make_key(self, key):
        return '/'.join((Config.BASE_KEY, key))

    def _get_named_pipe(self):
        return self.client.get_string(self.make_key(Config.NAMED_PIPE))

    named_pipe = property(_get_named_pipe)
    
    def _get_messages_kept(self):
        return self.client.get_int(self.make_key(Config.MESSAGES_KEPT))

    messages_kept = property(_get_messages_kept)

    def _get_suppress_alerts(self):
        return self.client.get_bool(self.make_key(Config.SUPPRESS_ALERTS))

    suppress_alerts = property(_get_suppress_alerts)

    def _get_suppress_minutes(self):
        return self.client.get_int(self.make_key(Config.SUPPRESS_MINUTES))

    suppress_minutes = property(_get_suppress_minutes)

    def _get_filters(self):
        names = self.client.get_list(
            self.make_key(Config.FILTER_NAMES), gconf.VALUE_STRING)
        patterns = self.client.get_list(
            self.make_key(Config.FILTER_PATTERNS), gconf.VALUE_STRING)
        alerts = self.client.get_list(
            self.make_key(Config.FILTER_ALERTS), gconf.VALUE_BOOL)
        filters = []
        for i in range(len(names)):
            filter = Filter(names[i], patterns[i], alerts[i])
            filters.append(filter)
        return filters

    filters = property(_get_filters)
        

class WidgetWrapper(object):

    def __init__(self, root_widget):
        self._root_widget_name = root_widget
        self._xml = gtk.glade.XML('bandsaw.glade', root_widget)
        self.connect_signals(self)

    def _get_root_widget(self):
        return getattr(self, self._root_widget_name)

    root_widget = property(_get_root_widget)

    def __getattr__(self, name):
        widget = self._xml.get_widget(name)
        if widget is None:
            raise AttributeError, name
        return widget
    
    def connect_signals(self, obj):
        for name in obj.__class__.__dict__.keys():
            if hasattr(obj, name):
                candidate_callback = getattr(obj, name)
                if callable(candidate_callback):
                    self._xml.signal_connect(name, candidate_callback)


class Window(WidgetWrapper):

    def show(self):
        self.root_widget.show()

    def destroy(self):
        self.root_widget.destroy()


class Dialog(Window):

    def run(self):
        self.root_widget.run()


class Filter:

    def __init__(self, name, pattern, alert):
        self.name = name
        self.pattern = re.compile(pattern)
        self.alert = alert

    def matches(self, text):
        return self.pattern.search(text) is not None


class PreferencesDialog(Dialog):

    def __init__(self):
        Dialog.__init__(self, 'preferences_dialog')


class LogMessage:

    def __init__(self, line):
        self._words = line.split(' ')

    def _get_date(self):
        return ' '.join(self._words[:3])

    date = property(_get_date)
    
    def _get_hostname(self):
        return self._words[3]

    hostname = property(_get_hostname)

    def _get_process(self):
        return self._words[4][:-1]

    process = property(_get_process)

    def _get_text(self):
        return ' '.join(self._words[5:]).strip()

    text = property(_get_text)


class AlertDialog(Dialog):

    def __init__(self, filter, message):
        Dialog.__init__(self, 'alert_dialog')
        self.set_text(filter, message)

    def set_text(self, filter, message):
        # TODO: escape text
        self.label1.set_markup('<span weight="bold" size="larger">'
                               '%s from %s</span>\n\n%s' %
                               (filter.name, message.hostname, message.text))

    def on_alert_dialog_delete_event(self, *args):
        self.destroy()

    def on_okbutton1_clicked(self, *args):
        self.destroy()
        

class LogTreeView(gtk.TreeView):

    DATE_COLUMN = 0
    HOSTNAME_COLUMN = 1
    PROCESS_COLUMN = 2
    MESSAGE_COLUMN = 3

    def __init__(self, config):
        gtk.TreeView.__init__(self)
        self.config = config
        self.last_alert_time = 0

    def add_column(self, title, index):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(title, renderer, text=index)
        self.append_column(column)

    def setup(self):
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
                              gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.set_model(model)
        self.add_column('Date', LogTreeView.DATE_COLUMN)
        self.add_column('Hostname', LogTreeView.HOSTNAME_COLUMN)
        self.add_column('Process', LogTreeView.PROCESS_COLUMN)
        self.add_column('Message', LogTreeView.MESSAGE_COLUMN)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.show()

    def select_all(self):
        self.get_selection().select_all()

    def scroll_to_end(self):
        adjustment = self.get_parent().get_vadjustment()
        adjustment.set_value(adjustment.get_property('upper'))

    def is_scrolled_down(self):
        adjustment = self.get_parent().get_vadjustment()
        value = adjustment.get_value()
        page_size = adjustment.get_property('page_size')
        upper = adjustment.get_property('upper')
        return value + page_size >= upper

    def add_message(self, message):
        should_scroll_down = self.is_scrolled_down()
        row = (message.date, message.hostname, message.process, message.text)
        self.get_model().append(row)
        if should_scroll_down:
            self.scroll_to_end()
        
    def should_raise_alert(self, filter, message):
        if not filter.alert:
            return False
        seconds_per_minute = 60
        minutes = (time.time() - self.last_alert_time) / seconds_per_minute
        return minutes >= self.config.suppress_minutes

    def raise_alert(self, filter, message):
        self.last_alert_time = time.time()
        dialog = AlertDialog(filter, message)
        dialog.show()
        
    def process_line(self, line):
        message = LogMessage(line)
        for filter in self.config.filters:
            if filter.matches(message.text):
                self.add_message(message)
                if self.should_raise_alert(filter, message):
                    self.raise_alert(filter, message)
        
    def delete_selected(self):
        selected = []
        def delete(model, path, iter):
            selected.append(iter)
        self.get_selection().selected_foreach(delete)
        for iter in selected:
            self.get_model().remove(iter)
#         self.get_selection().select_iter(selected[-1])
        

class Menu:

    def __init__(self, log_view):
        self.log_view = log_view

    def on_quit1_activate(self, *args):
        gtk.mainquit()

    def on_clear1_activate(self, *args):
        self.log_view.delete_selected()

    def on_select_all1_activate(self, *args):
        self.log_view.select_all()

    def on_preferences1_activate(self, *args):
        dialog = PreferencesDialog()
        dialog.run()
        dialog.destroy()

    def on_about1_activate(self, *args):
        dialog = AboutDialog()
        dialog.run()


class AboutDialog(Dialog):
    
    def __init__(self):
        Dialog.__init__(self, 'about_dialog')
        

class MainWindow(Window):

    def __init__(self, config):
        Window.__init__(self, 'app1')
        self.config = config
        self.monitor_id = None
        self.log_view = LogTreeView(self.config)
        self.log_view.setup()
        self.scrolledwindow1.add(self.log_view)
        self.log_view.show()
        self.setup_menu()
        self.monitor_syslog()

    def setup_menu(self):
        menu = Menu(self.log_view)
        self.connect_signals(menu)

    def on_syslog_readable(self, fifo, condition):
        for line in fifo:
            if line == '':   # fifo closed by syslog
                gtk.input_remove(self.monitor_id)
                self.monitor_syslog()
                return gtk.FALSE
            else:
                self.log_view.process_line(line)
                return gtk.TRUE

    def monitor_syslog(self):
        fifo_path = self.config.named_pipe
        fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        fifo = os.fdopen(fd)
        self.monitor_id = gtk.input_add(
            fifo, gtk.gdk.INPUT_READ, self.on_syslog_readable)
        
    def on_app1_delete_event(self, *args):
        gtk.mainquit()


def main():
    gnome.program_init('Band Saw', '0.1')
    config = Config(gconf.client_get_default())
    window = MainWindow(config)
    window.show()
    gtk.main()


if __name__ == '__main__':
    main()
