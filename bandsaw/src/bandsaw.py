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


def make_key(key):
    return '/'.join((Config.BASE_KEY, key))


class Config(object):

    BASE_KEY = '/apps/bandsaw'

    FILTER_ALERTS = '/'.join((BASE_KEY, 'filter_alerts'))
    FILTER_NAMES = '/'.join((BASE_KEY, 'filter_names'))
    FILTER_PATTERNS = '/'.join((BASE_KEY, 'filter_patterns'))
    MESSAGES_KEPT = '/'.join((BASE_KEY, 'messages_kept'))
    NAMED_PIPE = '/'.join((BASE_KEY, 'named_pipe'))
    SUPPRESS_ALERTS = '/'.join((BASE_KEY, 'suppress_alerts'))
    SUPPRESS_MINUTES = '/'.join((BASE_KEY, 'suppress_minutes'))
    
    def __init__(self, client):
        self.client = client

    def _get_named_pipe(self):
        return self.client.get_string(Config.NAMED_PIPE)

    def _set_named_pipe(self, value):
        value = value.strip()
        return self.client.set_string(Config.NAMED_PIPE, value)

    named_pipe = property(_get_named_pipe, _set_named_pipe)
    
    def _get_messages_kept(self):
        return self.client.get_int(Config.MESSAGES_KEPT)

    def _set_messages_kept(self, value):
        self.client.set_int(Config.MESSAGES_KEPT, int(value))

    messages_kept = property(_get_messages_kept, _set_messages_kept)

    def _get_suppress_alerts(self):
        return self.client.get_bool(Config.SUPPRESS_ALERTS)

    def _set_suppress_alerts(self, value):
        self.client.set_bool(Config.SUPPRESS_ALERTS, value)

    suppress_alerts = property(_get_suppress_alerts, _set_suppress_alerts)

    def _get_suppress_minutes(self):
        return self.client.get_int(Config.SUPPRESS_MINUTES)

    def _set_suppress_minutes(self, value):
        self.client.set_int(Config.SUPPRESS_MINUTES, int(value))

    suppress_minutes = property(_get_suppress_minutes, _set_suppress_minutes)

    def _get_filters(self):
        names = self.client.get_list(Config.FILTER_NAMES, gconf.VALUE_STRING)
        patterns = self.client.get_list(Config.FILTER_PATTERNS,
                                        gconf.VALUE_STRING)
        alerts = self.client.get_list(Config.FILTER_ALERTS, gconf.VALUE_BOOL)
        filters = []
        for i in range(len(names)):
            filter = Filter(names[i], patterns[i], alerts[i])
            filters.append(filter)
        return filters

    def _set_filters(self, value):
        names = [filter.name for filter in value]
        patterns = [filter.pattern for filter in value]
        alerts = [filter.alert for filter in value]
        self.client.set_list(Config.FILTER_NAMES, gconf.VALUE_STRING, names)
        self.client.set_list(
            Config.FILTER_PATTERNS, gconf.VALUE_STRING, patterns)
        self.client.set_list(Config.FILTER_ALERTS, gconf.VALUE_BOOL, alerts)

    filters = property(_get_filters, _set_filters)
        

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
        return self.root_widget.run()


class ErrorDialog(Dialog):

    def __init__(self, parent, primary, secondary):
        Dialog.__init__(self, 'error_dialog')
        self.label1.set_markup(self.get_markup(primary, secondary))

    def get_markup(self, primary, secondary):
        return '<span weight="bold" size="larger">%s</span>\n\n%s' % \
               (primary, secondary)


class Filter:

    def __init__(self, name, pattern, alert):
        self.name = name
        self.pattern = pattern
        self.alert = alert

    def matches(self, text):
        return re.search(self.pattern, text) is not None


class FilterSet(list):

    pass


class FilterDialog(Dialog):

    def __init__(self, parent, title):
        Dialog.__init__(self, 'filter_dialog')
        self.root_widget.set_transient_for(parent.root_widget)
        self.root_widget.set_title(title)
        self.filter = None
        self.setup_size_group()

    def setup_size_group(self):
        size_group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        size_group.add_widget(self.name_label)
        size_group.add_widget(self.pattern_label)

    def _get_name(self):
        return self.name_entry.get_text().strip()

    name = property(_get_name)

    def _get_pattern(self):
        return self.pattern_entry.get_text().strip()

    pattern = property(_get_pattern)

    def _get_raise_alert(self):
        return self.checkbutton1.get_active()

    raise_alert = property(_get_raise_alert)

    def user_input_ok(self):
        return self.name and self.pattern

    def on_filter_dialog_response(self, widget, event, *args):
        if event != gtk.RESPONSE_OK:
            return
        if self.user_input_ok():
            self.filter = Filter(self.name, self.pattern, self.raise_alert)
        else:
            self.root_widget.emit_stop_by_name('response')
            dialog = ErrorDialog(self, 'Incomplete details',
                                 'Please specify a name and a pattern.')
            dialog.run()
            dialog.destroy()
        

class PreferencesDialog(Dialog):

    def __init__(self, config):
        Dialog.__init__(self, 'preferences_dialog')
        self.config = config
        self.setup_general()
        self.setup_filters()

    def setup_general(self):
        self.named_pipe_entry.set_text(self.config.named_pipe)
        self.spinbutton1.set_value(self.config.messages_kept)

    def setup_filter_treeview(self):
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.treeview1.set_model(list_store)
        renderer = gtk.CellRendererText()
        NAME_COLUMN = 0
        column = gtk.TreeViewColumn(None, renderer, text=NAME_COLUMN)
        self.treeview1.append_column(column)
        self.treeview1.set_headers_visible(gtk.FALSE)

    def redraw_filters(self):
        self.treeview1.get_model().clear()
        for filter in self.config.filters:
            self.treeview1.get_model().append((filter.name,))
        
    def setup_filters(self):
        self.setup_filter_treeview()
        self.redraw_filters()

    def on_named_pipe_entry_changed(self, *args):
        self.config.named_pipe = self.named_pipe_entry.get_text()

    def on_spinbutton1_changed(self, *args):
        self.config.messages_kept = self.spinbutton1.get_value()

    def on_add_button_clicked(self, *args):
        dialog = FilterDialog(self, 'Add Filter')
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            filters = self.config.filters
            filters.append(dialog.filter)
            self.config.filters = filters
            self.redraw_filters()
        dialog.destroy()

    def on_edit_button_clicked(self, *args):
        pass

    def on_remove_button_clicked(self, *args):
        list_store, iter = self.treeview1.get_selection().get_selected()
        row_index = list_store.get_path(iter)[0]
        filters = self.config.filters
        filters.pop(row_index)
        self.config.filters = filters
        self.redraw_filters()
    
    def on_up_button_clicked(self, *args):
        pass
    
    def on_down_button_clicked(self, *args):
        pass


class LogMessage:

    regex = r'([^\s]+\s+[^\s]+\s+[^\s]+)\s+([^\s]+)\s+([^\s]+):\s(.*)'
    pattern = re.compile(regex)
    
    def __init__(self, line):
        self.match = LogMessage.pattern.match(line)

    def _get_date(self):
        return self.match.groups()[0]

    date = property(_get_date)
    
    def _get_hostname(self):
        return self.match.groups()[1]

    hostname = property(_get_hostname)

    def _get_process(self):
        return self.match.groups()[2]

    process = property(_get_process)

    def _get_text(self):
        return self.match.groups()[3]

    text = property(_get_text)


class AlertDialog(Dialog):

    def __init__(self, config, filter, message):
        Dialog.__init__(self, 'alert_dialog')
        self.config = config
        self.setup_widgets(filter, message)

    def setup_widgets(self, filter, message):
        # TODO: escape text
        self.label1.set_markup('<span weight="bold" size="larger">'
                               '%s from %s</span>\n\n%s' %
                               (filter.name, message.hostname, message.text))
        self.checkbutton1.set_active(self.config.suppress_alerts)
        self.spinbutton1.set_value(self.config.suppress_minutes)

    def on_alert_dialog_delete_event(self, *args):
        self.destroy()

    def on_okbutton1_clicked(self, *args):
        self.config.suppress_alerts = self.checkbutton1.get_active()
        self.config.suppress_minutes = self.spinbutton1.get_value()
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
        elif not self.config.suppress_alerts:
            return True
        else:
            seconds_per_minute = 60
            minutes = (time.time() - self.last_alert_time) / seconds_per_minute
            return minutes >= self.config.suppress_minutes

    def raise_alert(self, filter, message):
        self.last_alert_time = time.time()
        dialog = AlertDialog(self.config, filter, message)
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

    def __init__(self, config, log_view):
        self.config = config
        self.log_view = log_view

    def on_quit1_activate(self, *args):
        gtk.mainquit()

    def on_clear1_activate(self, *args):
        self.log_view.delete_selected()

    def on_select_all1_activate(self, *args):
        self.log_view.select_all()

    def on_preferences1_activate(self, *args):
        dialog = PreferencesDialog(self.config)
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
        menu = Menu(self.config, self.log_view)
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
