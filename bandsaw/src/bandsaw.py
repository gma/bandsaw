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
import sys
import time

import pygtk; pygtk.require('2.0')
import gconf
import gnome
import gnome.ui
import gobject
import gtk
import gtk.glade


__VERSION__ = '@VERSION@'


class Config(object):

    BASE_KEY = '/apps/bandsaw'

    MESSAGES_KEPT = '/'.join((BASE_KEY, 'messages_kept'))
    NAMED_PIPE = '/'.join((BASE_KEY, 'named_pipe'))

    ALERTS_KEY = '/'.join((BASE_KEY, 'alerts'))
    IGNORE_ALERTS = '/'.join((ALERTS_KEY, 'ignore'))
    IGNORE_TIMEOUT = '/'.join((ALERTS_KEY, 'ignore_timeout'))
    
    FILTERS_KEY = '/'.join((BASE_KEY, 'filters'))
    FILTER_ALERTS = '/'.join((FILTERS_KEY, 'alerts'))
    FILTER_NAMES = '/'.join((FILTERS_KEY, 'names'))
    FILTER_PATTERNS = '/'.join((FILTERS_KEY, 'patterns'))

    def __init__(self, client):
        self.client = client
        self._named_pipe = None
        self._messages_kept = None
        self._ignore_alerts = None
        self._ignore_timeout = None
        self._filters = None

    def _get_named_pipe(self):
        if self._named_pipe is None:
            self._named_pipe = self.client.get_string(Config.NAMED_PIPE)
        return self._named_pipe

    def _set_named_pipe(self, value):
        value = value.strip()
        self.client.set_string(Config.NAMED_PIPE, value)
        self._named_pipe = None

    named_pipe = property(_get_named_pipe, _set_named_pipe)
    
    def _get_messages_kept(self):
        if self._messages_kept is None:
            self._messages_kept = self.client.get_int(Config.MESSAGES_KEPT)
        return self._messages_kept

    def _set_messages_kept(self, value):
        self.client.set_int(Config.MESSAGES_KEPT, int(value))
        self._messages_kept = None

    messages_kept = property(_get_messages_kept, _set_messages_kept)

    def _get_ignore_alerts(self):
        if self._ignore_alerts is None:
            self._ignore_alerts = self.client.get_bool(Config.IGNORE_ALERTS)
        return self._ignore_alerts

    def _set_ignore_alerts(self, value):
        self.client.set_bool(Config.IGNORE_ALERTS, value)
        self._ignore_alerts = None

    ignore_alerts = property(_get_ignore_alerts, _set_ignore_alerts)

    def _get_ignore_timeout(self):
        if self._ignore_timeout is None:
            self._ignore_timeout = self.client.get_int(Config.IGNORE_TIMEOUT)
        return self._ignore_timeout

    def _set_ignore_timeout(self, value):
        self.client.set_int(Config.IGNORE_TIMEOUT, int(value))
        self._ignore_timeout = None

    ignore_timeout = property(_get_ignore_timeout, _set_ignore_timeout)

    def _get_filters(self):
        if self._filters is None:
            names = self.client.get_list(Config.FILTER_NAMES, gconf.VALUE_STRING)
            patterns = self.client.get_list(Config.FILTER_PATTERNS,
                                            gconf.VALUE_STRING)
            alerts = self.client.get_list(Config.FILTER_ALERTS, gconf.VALUE_BOOL)
            self._filters = FilterSet()
            for i in range(len(names)):
                filter = Filter(names[i], patterns[i], alerts[i])
                self._filters.append(filter)
        return self._filters

    def _set_filters(self, value):
        names = [filter.name for filter in value]
        patterns = [filter.pattern for filter in value]
        alerts = [filter.alert for filter in value]
        self.client.set_list(Config.FILTER_NAMES, gconf.VALUE_STRING, names)
        self.client.set_list(
            Config.FILTER_PATTERNS, gconf.VALUE_STRING, patterns)
        self.client.set_list(Config.FILTER_ALERTS, gconf.VALUE_BOOL, alerts)
        self._filters = None

    filters = property(_get_filters, _set_filters)

    def is_first_run(self):
        return self.named_pipe is None
        

class LogMessage:

    regex = r'([^\s]+\s+[^\s]+\s+[^\s]+)\s+([^\s]+)\s+([^\s]+):\s(.*)'
    pattern = re.compile(regex)
    
    def __init__(self, line):
        self.match = LogMessage.pattern.match(line)

    def _get_message_part(self, index):
        try:
            return self.match.groups()[index]
        except AttributeError:
            return ''

    def _get_date(self):
        return self._get_message_part(0)

    date = property(_get_date)
    
    def _get_hostname(self):
        return self._get_message_part(1)

    hostname = property(_get_hostname)

    def _get_process(self):
        return self._get_message_part(2)

    process = property(_get_process)

    def _get_text(self):
        return self._get_message_part(3)

    text = property(_get_text)


class Filter:

    def __init__(self, name='', pattern='', alert=False):
        self.name = name
        self.pattern = pattern
        self.alert = alert

    def matches(self, text):
        return re.search(self.pattern, text) is not None


class FilterSet(list):

    def move_filter(self, index, offset):
        moved_filter = self[index]
        self.pop(index)
        self.insert(index + offset, moved_filter)

    def move_up(self, index):
        self.move_filter(index, -1)

    def move_down(self, index):
        self.move_filter(index, +1)

    def update(self, filter):
        self[self.index(filter)] = filter


class AlertQueue(list):

    def __init__(self, config):
        list.__init__(self)
        self.config = config
        self.alert_displayed = False
        self.last_alert_time = 0
    
    def suppress_timeout_elapsed(self):
        seconds_per_minute = 60
        minutes = (time.time() - self.last_alert_time) / seconds_per_minute
        return minutes >= self.config.ignore_timeout

    def should_raise_alert(self, filter):
        if not filter.alert or self.alert_displayed:
            return False
        else:
            suppressed = self.config.ignore_alerts
            return not (suppressed and not self.suppress_timeout_elapsed())

    def raise_alert(self, filter, message):
        if self.should_raise_alert(filter):
            self.last_alert_time = time.time()
            self.alert_displayed = True
            dialog = AlertDialog(self, self.config, filter, message)
            dialog.show()

    def append(self, filter, message):
        if self.alert_displayed:
            list.append(self, (filter, message))
        else:
            self.raise_alert(filter, message)

    def pop(self):
        self.alert_displayed = False
        try:
            filter, message = list.pop(self, 0)
            self.raise_alert(filter, message)
        except IndexError:
            pass
        

class WidgetWrapper(object):

    def __init__(self, root_widget):
        self._root_widget_name = root_widget
        self._xml = gtk.glade.XML('bandsaw.glade',
                                  root_widget)
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
        self.root_widget.show_all()

    def destroy(self):
        self.root_widget.destroy()


class Dialog(Window):

    def run(self):
        return self.root_widget.run()


class WelcomeDruid(Window):

    def __init__(self, config):
        Window.__init__(self, 'druid_window')
        self.config = config
        self.set_defaults()

    def set_defaults(self):
        try:
            filename = os.path.join(os.environ['HOME'], '.bandsaw.fifo')
            self.filename_entry.set_text(filename)
        except KeyError:
            pass

    def on_druidpage_pipe_next(self, *args):
        filename = self.filename_entry.get_text()
        if len(filename) == 0:
            dialog = ErrorDialog('Please specify a filename')
            dialog.run()
            dialog.destroy()
            return gtk.TRUE
        elif not os.path.exists(filename):
            dialog = ErrorDialog(
                'File not found',
                "'%s' could not be found. Please specify the full path to "
                "a named pipe.\n\nRun 'mkfifo /path/to/fifo' from a "
                "terminal to create a new named pipe." % filename)
            dialog.run()
            dialog.destroy()
            return gtk.TRUE
        self.config.named_pipe = filename

    def on_druidpagefinish1_finish(self, *args):
        self.destroy()
        window = MainWindow(self.config)
        window.show()

    def on_druidpage_cancel(self, *args):
        gtk.mainquit()

    def on_druid_window_delete_event(self, *args):
        gtk.mainquit()
        

class AboutDialog(Dialog):
    
    def __init__(self):
        Dialog.__init__(self, 'about_dialog')
        

class ErrorDialog(Dialog):

    def __init__(self, primary, secondary=''):
        Dialog.__init__(self, 'error_dialog')
        self.label1.set_markup(self.get_markup(primary, secondary))

    def get_markup(self, primary, secondary):
        markup = '<span weight="bold" size="larger">%s</span>' % primary
        if secondary:
            markup += '\n\n%s' % secondary
        return markup


class PreferencesDialog(Dialog):

    NAME_COLUMN = 0
    
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
        column = gtk.TreeViewColumn(None, renderer, text=self.NAME_COLUMN)
        self.treeview1.append_column(column)
        self.treeview1.set_headers_visible(gtk.FALSE)
        selection = self.treeview1.get_selection()
        selection.connect('changed', self.on_filter_selection_changed)

    def first_row_selected(self, selection):
        list_store, iter = selection.get_selected()
        first_iter = list_store.get_iter_first()
        return list_store.get_path(iter) == list_store.get_path(first_iter)

    def last_row_selected(self, selection):
        list_store, iter = selection.get_selected()
        return list_store.iter_next(iter) is None

    def on_filter_selection_changed(self, selection, *args):
        list_store, iter = selection.get_selected()
        if iter is None:
            sensitive = gtk.FALSE
            self.up_button.set_sensitive(sensitive)
            self.down_button.set_sensitive(sensitive)
        else:
            sensitive = not self.first_row_selected(selection)
            self.up_button.set_sensitive(sensitive)
            sensitive = not self.last_row_selected(selection)
            self.down_button.set_sensitive(sensitive)
            sensitive = gtk.TRUE
        self.edit_button.set_sensitive(sensitive)
        self.remove_button.set_sensitive(sensitive)

            
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

    def get_selected_filter_index(self):
        list_store, iter = self.treeview1.get_selection().get_selected()
        return list_store.get_path(iter)[0]

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
        filter = self.config.filters[self.get_selected_filter_index()]
        dialog = FilterDialog(self, 'Edit Filter', filter)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            filters = self.config.filters
            filters.update(dialog.filter)
            self.config.filters = filters
            self.redraw_filters()
        dialog.destroy()

    def on_remove_button_clicked(self, *args):
        filters = self.config.filters
        filters.pop(self.get_selected_filter_index())
        self.config.filters = filters
        self.redraw_filters()

    def on_up_button_clicked(self, *args):
        index = self.get_selected_filter_index()
        filters = self.config.filters
        filters.move_up(index)
        self.config.filters = filters
        list_store, iter = self.treeview1.get_selection().get_selected()
        name = list_store.get_value(iter, self.NAME_COLUMN)
        list_store.remove(iter)
        list_store.insert(index - 1, (name,))
        self.treeview1.get_selection().select_path((index - 1,))
    
    def on_down_button_clicked(self, *args):
        index = self.get_selected_filter_index()
        filters = self.config.filters
        filters.move_down(index)
        self.config.filters = filters
        list_store, iter = self.treeview1.get_selection().get_selected()
        name = list_store.get_value(iter, self.NAME_COLUMN)
        list_store.remove(iter)
        list_store.insert(index + 1, (name,))
        self.treeview1.get_selection().select_path((index + 1,))

    def on_treeview1_row_activated(self, *args):
        list_store, iter = self.treeview1.get_selection().get_selected()
        if iter is not None:
            self.on_edit_button_clicked()


class FilterDialog(Dialog):

    def __init__(self, parent, title, filter=Filter()):
        Dialog.__init__(self, 'filter_dialog')
        self.root_widget.set_transient_for(parent.root_widget)
        self.root_widget.set_title(title)
        self.filter = filter
        self.setup_widgets()

    def setup_widgets(self):
        self.setup_size_group()
        self.name_entry.set_text(self.filter.name)
        self.pattern_entry.set_text(self.filter.pattern)
        self.checkbutton1.set_active(self.filter.alert)

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
        if self.name and self.pattern:
            self.filter.name = self.name
            self.filter.pattern = self.pattern
            self.filter.alert = self.raise_alert
        else:
            if not self.name:
                message = 'Filter has no name'
            else:
                message = 'Filter has no pattern'
            self.root_widget.emit_stop_by_name('response')
            dialog = ErrorDialog(message,
                                 'Please specify a name and a pattern.')
            dialog.run()
            dialog.destroy()


class AlertDialog(Dialog):

    def __init__(self, queue, config, filter, message):
        Dialog.__init__(self, 'alert_dialog')
        self.alert_queue = queue
        self.config = config
        self.setup_widgets(filter, message)

    def setup_widgets(self, filter, message):
        # TODO: escape text
        self.label1.set_markup('<span weight="bold" size="larger">'
                               '%s from %s</span>\n\n%s' %
                               (filter.name, message.hostname, message.text))
        self.checkbutton1.set_active(self.config.ignore_alerts)
        self.spinbutton1.set_value(self.config.ignore_timeout)

    def destroy(self):
        Dialog.destroy(self)
        self.alert_queue.pop()
        
    def on_alert_dialog_delete_event(self, *args):
        self.destroy()

    def on_okbutton1_clicked(self, *args):
        self.config.ignore_alerts = self.checkbutton1.get_active()
        self.config.ignore_timeout = self.spinbutton1.get_value()
        self.destroy()
        

class LogTreeView(gtk.TreeView):

    DATE_COLUMN = 0
    HOSTNAME_COLUMN = 1
    PROCESS_COLUMN = 2
    MESSAGE_COLUMN = 3

    def __init__(self, config):
        gtk.TreeView.__init__(self)
        self.config = config
        self.alert_queue = AlertQueue(config)
        self._observers = []

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
        selection = self.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.on_selection_changed)
        self.show()

    def on_selection_changed(self, selection):
        selected = [False]

        def check_if_selected(model, path, iter):
            selected[0] = True

        selection.selected_foreach(check_if_selected)
        for observer in self._observers:
            observer.selection_changed(selected[0])

    def observe_selection(self, observer):
        self._observers.append(observer)
        
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

    def count_messages(self):
        count = [0]

        def count_rows(model, iter, path):
            count[0] += 1

        self.get_model().foreach(count_rows)
        return count[0]

    def remove_first_row(self):
        list_store = self.get_model()
        iter = list_store.get_iter_first()
        if iter:
            list_store.remove(iter)

    def add_message(self, message):
        if self.count_messages() >= self.config.messages_kept:
            self.remove_first_row()
        row = (message.date, message.hostname, message.process, message.text)
        self.get_model().append(row)
        if self.is_scrolled_down():
            self.scroll_to_end()
        
    def process_line(self, line):
        message = LogMessage(line)
        for filter in self.config.filters:
            if filter.matches(message.text):
                self.add_message(message)
                self.alert_queue.append(filter, message)

    def clear(self):
        self.get_model().clear()
        
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

    def on_delete_selected1_activate(self, *args):
        self.log_view.delete_selected()

    def on_clear1_activate(self, *args):
        self.log_view.clear()

    def on_select_all1_activate(self, *args):
        self.log_view.select_all()

    def on_preferences1_activate(self, *args):
        dialog = PreferencesDialog(self.config)
        dialog.run()
        dialog.destroy()

    def on_about1_activate(self, *args):
        dialog = AboutDialog()
        dialog.run()


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
        self.log_view.observe_selection(self)
        self.monitor_syslog()

    def selection_changed(self, have_selection):
        self.delete_selected1.set_sensitive(have_selection)

    def setup_menu(self):
        menu = Menu(self.config, self.log_view)
        self.delete_selected1.set_sensitive(gtk.FALSE)
        self.connect_signals(menu)

    def on_syslog_readable(self, fifo, condition):
        line = fifo.readline()
        if line == '':   # fifo closed by syslog
            gtk.input_remove(self.monitor_id)
            self.monitor_syslog()
            return gtk.FALSE
        else:
            self.log_view.process_line(line)
            return gtk.TRUE

    def monitor_syslog(self):
        fifo_path = self.config.named_pipe
        try:
            fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError, e:
            dialog = ErrorDialog('Unable to open file',
                                 "The file '%s' cannot be read. Please check "
                                 "the permissions and try again." % fifo_path)
            dialog.run()
            dialog.destroy()
            sys.exit()
        else:
            fifo = os.fdopen(fd)
            self.monitor_id = gtk.input_add(
                fifo, gtk.gdk.INPUT_READ, self.on_syslog_readable)
        
    def on_app1_delete_event(self, *args):
        gtk.mainquit()


def main():
    gnome.program_init('Band Saw', __VERSION__)
    config = Config(gconf.client_get_default())
    if config.is_first_run():
        window = WelcomeDruid(config)
    else:
        window = MainWindow(config)
    window.show()
    gtk.main()


if __name__ == '__main__':
    main()
