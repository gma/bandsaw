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

import pygtk; pygtk.require("2.0")
import egg.trayicon
import gconf
import gnome
import gnome.ui
import gobject
import gtk
import gtk.gdk
import gtk.glade

import bandsawconfig


__VERSION__ = bandsawconfig.VERSION

TESTING = "TESTING"


class Config(object):

    BASE_KEY = "/apps/bandsaw"

    MESSAGES_KEPT = "/".join((BASE_KEY, "messages_kept"))
    NAMED_PIPE = "/".join((BASE_KEY, "named_pipe"))
    ALERTS_KEY = "/".join((BASE_KEY, "alerts"))
    
    FILTERS_KEY = "/".join((BASE_KEY, "filters"))
    FILTER_ALERTS = "/".join((FILTERS_KEY, "alerts"))
    FILTER_NAMES = "/".join((FILTERS_KEY, "names"))
    FILTER_PATTERNS = "/".join((FILTERS_KEY, "patterns"))

    UI_KEY = "/".join((BASE_KEY, "ui"))
    LOG_WINDOW_X = "/".join((UI_KEY, "log_window_x"))
    LOG_WINDOW_Y = "/".join((UI_KEY, "log_window_y"))
    LOG_WINDOW_WIDTH = "/".join((UI_KEY, "log_window_width"))
    LOG_WINDOW_HEIGHT = "/".join((UI_KEY, "log_window_height"))
    
    def __init__(self, client):
        self.client = client
        self._named_pipe = None
        self._messages_kept = None
        self._filters = None
        self._observers = {}

    def add_observer(self, key, observer):
        self._observers.setdefault(key, []).append(observer)

    def _notify_observers(self, key):
        for observer in self._observers.get(key, []):
            observer.update(key)

    def _get_named_pipe(self):
        if self._named_pipe is None:
            self._named_pipe = self.client.get_string(Config.NAMED_PIPE)
        return self._named_pipe

    def _set_named_pipe(self, value):
        value = value.strip()
        self.client.set_string(Config.NAMED_PIPE, value)
        self._named_pipe = None
        self._notify_observers(Config.NAMED_PIPE)

    named_pipe = property(_get_named_pipe, _set_named_pipe)
    
    def _get_messages_kept(self):
        if self._messages_kept is None:
            self._messages_kept = self.client.get_int(Config.MESSAGES_KEPT)
        return self._messages_kept

    def _set_messages_kept(self, value):
        self.client.set_int(Config.MESSAGES_KEPT, int(value))
        self._messages_kept = None
        self._notify_observers(Config.MESSAGES_KEPT)

    messages_kept = property(_get_messages_kept, _set_messages_kept)

    def _get_filters(self):
        if self._filters is None:
            names = self.client.get_list(Config.FILTER_NAMES,
                                         gconf.VALUE_STRING)
            patterns = self.client.get_list(Config.FILTER_PATTERNS,
                                            gconf.VALUE_STRING)
            alerts = self.client.get_list(Config.FILTER_ALERTS,
                                          gconf.VALUE_BOOL)
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
        self._notify_observers(Config.FILTERS_KEY)

    filters = property(_get_filters, _set_filters)

    def is_first_run(self):
        return self.named_pipe is None

    def _get_log_window_coords(self):
        x = self.client.get_int(Config.LOG_WINDOW_X)
        y = self.client.get_int(Config.LOG_WINDOW_Y)
        return x, y

    def _set_log_window_coords(self, coords):
        self.client.set_int(Config.LOG_WINDOW_X, coords[0])
        self.client.set_int(Config.LOG_WINDOW_Y, coords[1])

    log_window_coords = property(_get_log_window_coords,
                                 _set_log_window_coords)

    def _get_log_window_size(self):
        width = self.client.get_int(Config.LOG_WINDOW_WIDTH)
        height = self.client.get_int(Config.LOG_WINDOW_HEIGHT)
        return width, height

    def _set_log_window_size(self, size):
        self.client.set_int(Config.LOG_WINDOW_WIDTH, size[0])
        self.client.set_int(Config.LOG_WINDOW_HEIGHT, size[1])

    log_window_size = property(_get_log_window_size, _set_log_window_size)


class LogMessage(object):

    regex = r"([^\s]+\s+[^\s]+\s+[^\s]+)\s+([^\s]+)\s+([^\s]+):\s(.*)"
    pattern = re.compile(regex)
    
    def __init__(self, line):
        self.match = LogMessage.pattern.match(line)

    def _get_message_part(self, index):
        try:
            return self.match.groups()[index]
        except AttributeError:
            return ""

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


class Filter(object):

    def __init__(self, name="", pattern="", alert=False):
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
        # TODO: find out why necessary, then refactor to explain it
        self[self.index(filter)] = filter  


class WidgetWrapper(object):

    def __init__(self, root_widget, wrapper=None):
        self._root_widget_name = root_widget
        if wrapper is None:
            if self.are_running_tests:
                gladedir = os.path.dirname(__file__)
            else:
                gladedir = bandsawconfig.GLADEDIR
            glade_file = os.path.join(gladedir, "bandsaw.glade")
            self._xml = gtk.glade.XML(glade_file, root_widget)
        else:
            self._xml = wrapper._xml
        self.connect_signals(self)

    def _get_root_widget(self):
        return getattr(self, self._root_widget_name)

    root_widget = property(_get_root_widget)

    def __getattr__(self, name):
        widget = self._xml.get_widget(name)
        if widget is None:
            raise AttributeError, name
        return widget
    
    def _are_running_tests(self):
        return TESTING in os.environ

    are_running_tests = property(_are_running_tests)

    def connect_signals(self, obj):
        for name in obj.__class__.__dict__.keys():
            if hasattr(obj, name):
                candidate_callback = getattr(obj, name)
                if callable(candidate_callback):
                    self._xml.signal_connect(name, candidate_callback)


def img_path(filename):
    return os.path.join(bandsawconfig.PIXMAPSDIR, filename)


def set_icon(window):
    if os.path.exists(img_path(bandsawconfig.LOGOICON)):
        pixbuf = gtk.gdk.pixbuf_new_from_file(img_path(bandsawconfig.LOGOICON))
        window.set_icon(pixbuf)


class PopupMenu(gtk.Menu):

    def __init__(self, config):
        gtk.Menu.__init__(self)
        self.config = config
        self.quit_callback = None
        self.setup_widgets()
        
    def setup_widgets(self):
        item = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        item.connect("activate", self.on_preferences_activate)
        item.show()
        self.append(item)

        item = gtk.ImageMenuItem(gtk.STOCK_HELP)
        item.connect("activate", self.on_help_activate)
        item.show()
        self.append(item)

        item = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        item.connect("activate", self.on_about_activate)
        item.show()
        self.append(item)

        item = gtk.SeparatorMenuItem()
        item.show()
        self.append(item)

        item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        item.connect("activate", self.on_quit_activate)
        item.show()
        self.append(item)

    def on_preferences_activate(self, *args):
        dialog = PreferencesDialog(self.config)
        dialog.run()
        dialog.destroy()

    def on_help_activate(self, *args):
        global program
        gnome.help_display_desktop(program, "bandsaw", "bandsaw.xml", "index")

    def on_about_activate(self, *args):
        copyright = u"Copyright \xa9 2004-2006 Graham Ashton"
        comments = "A log monitoring and alerting tool"
        authors = ["Graham Ashton <ashtong@users.sourceforge.net>"]
        documenters = []
        translators = None
        logo = gtk.gdk.pixbuf_new_from_file(img_path(bandsawconfig.LOGOICON))
        dialog = gnome.ui.About("Band Saw", __VERSION__, copyright, comments,
                                authors, documenters, translators, logo)
        set_icon(dialog)
        dialog.show()
        
    def on_quit_activate(self, *args):
        if self.quit_callback is not None:
            self.quit_callback()
        gtk.main_quit()


class FlashingNotifier(object):

    def __init__(self, name, onicon, officon, interval=500, menu=None):
        self.trayicon = egg.trayicon.TrayIcon(name)
        self.on_icon = onicon
        self.off_icon = officon
        self.interval = interval
        self.menu = menu
        self.timeout = None
        self.is_flashing = False
        self.tips = gtk.Tooltips()
        self.setup_widgets()
        self.left_click_callback = None
        self.stop_flashing()

    def _get_eventbox(self):
        return self.trayicon.get_children()[0]

    eventbox = property(_get_eventbox)

    def _get_image(self):
        return self.eventbox.get_children()[0]

    image = property(_get_image)

    def setup_widgets(self):
        eventbox = gtk.EventBox()
        image = gtk.Image()
        eventbox.add(image)
        eventbox.connect("button-press-event", self.on_button_press_event)
        self.trayicon.add(eventbox)

    def on_button_press_event(self, widget, event):
        left_button = 1
        right_button = 3
        if event.button == left_button and self.left_click_callback:
            self.left_click_callback()
        elif event.button == right_button:
            self.menu.popup(None, None, None, event.button, event.time)

    def set_tool_tip(self, text):
        self.tips.set_tip(self.eventbox, text)

    def _flash_on(self):
        self.image.set_from_file(self.on_icon)
        self.is_flashing = True

    def _flash_off(self):
        self.image.set_from_file(self.off_icon)
        self.is_flashing = False

    def _flash(self, *args):
        if self.is_flashing:
            self._flash_off()
        else:
            self._flash_on()
        return True
        
    def start_flashing(self):
        if self.timeout is None:
            self.timeout = gobject.timeout_add(self.interval, self._flash)

    def stop_flashing(self):
        if self.timeout is not None:
            gobject.source_remove(self.timeout)
        self._flash_off()
        self.timeout = None


class Window(WidgetWrapper):

    def __init__(self, root_widget, parent=None):
        WidgetWrapper.__init__(self, root_widget)
        if parent is not None:
            self.root_widget.set_transient_for(parent)
        set_icon(self.root_widget)

    def set_transient_for_main_window(self):
        for window in gtk.window_list_toplevels():
            if window.name == MainWindow.NAME:
                self.root_widget.set_transient_for(window)
                break

    def show(self):
        if not self.are_running_tests:
            self.root_widget.show_all()

    def destroy(self):
        self.root_widget.destroy()


class Dialog(Window):

    def run(self):
        if not self.are_running_tests:
            return self.root_widget.run()


class WelcomeDruid(Window):

    def __init__(self, config):
        Window.__init__(self, "druid_window")
        self.config = config
        self.set_defaults()

    def set_defaults(self):
        try:
            filename = os.path.join(os.environ["HOME"], ".bandsaw.fifo")
            self.filename_entry.set_text(filename)
        except KeyError:
            pass

    def on_druidpage_pipe_next(self, *args):
        filename = self.filename_entry.get_text()
        if len(filename) == 0:
            dialog = ErrorDialog(self.root_widget, "Please specify a filename")
            dialog.run()
            dialog.destroy()
            return True
        elif not os.path.exists(filename):
            dialog = ErrorDialog(
                self.root_widget, "File not found",
                "'%s' could not be found. Please specify the full path to "
                "a named pipe.\n\nRun 'mkfifo /path/to/fifo' from a "
                "terminal to create a new named pipe." % filename)
            dialog.run()
            dialog.destroy()
            return True
        self.config.named_pipe = filename

    def on_druidpagefinish1_finish(self, *args):
        window = MainWindow(self.config)
        self.destroy()

    def on_druidpage_cancel(self, *args):
        gtk.main_quit()

    def on_druid_window_delete_event(self, *args):
        gtk.main_quit()
        

class ErrorDialog(Dialog):

    def __init__(self, parent, primary, secondary=""):
        Dialog.__init__(self, "error_dialog", parent)
        self.label1.set_markup(self.get_markup(primary, secondary))

    def get_markup(self, primary, secondary):
        markup = '<span weight="bold" size="larger">%s</span>' % primary
        if secondary:
            markup += "\n\n%s" % secondary
        return markup


class PreferencesDialog(Dialog):

    NAME_COLUMN = 0
    
    def __init__(self, config):
        Dialog.__init__(self, "preferences_dialog")
        self.config = config
        self.setup_general()
        self.setup_filters()

    def setup_general(self):
        self.named_pipe_entry.set_text(self.config.named_pipe)
        self.messages_kept.set_value(self.config.messages_kept)

    def setup_filter_treeview(self):
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.treeview1.set_model(list_store)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(None, renderer, text=self.NAME_COLUMN)
        self.treeview1.append_column(column)
        self.treeview1.set_headers_visible(False)
        selection = self.treeview1.get_selection()
        selection.connect("changed", self.on_filter_selection_changed)

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
            sensitive = False
            self.up_button.set_sensitive(sensitive)
            self.down_button.set_sensitive(sensitive)
        else:
            sensitive = not self.first_row_selected(selection)
            self.up_button.set_sensitive(sensitive)
            sensitive = not self.last_row_selected(selection)
            self.down_button.set_sensitive(sensitive)
            sensitive = True
        self.edit_button.set_sensitive(sensitive)
        self.remove_button.set_sensitive(sensitive)
            
    def redraw_filters(self):
        self.treeview1.get_model().clear()
        for filter in self.config.filters:
            self.treeview1.get_model().append((filter.name,))
        
    def setup_filters(self):
        self.setup_filter_treeview()
        self.redraw_filters()

    def on_closebutton1_clicked(self, *args):
        self.config.named_pipe = self.named_pipe_entry.get_text()

    def on_messages_kept_value_changed(self, *args):
        self.config.messages_kept = self.messages_kept.get_value()

    def get_selected_filter_index(self):
        list_store, iter = self.treeview1.get_selection().get_selected()
        return list_store.get_path(iter)[0]

    def on_add_button_clicked(self, *args):
        dialog = FilterDialog(self, "Add Filter")
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            filters = self.config.filters
            filters.append(dialog.filter)
            self.config.filters = filters
            self.redraw_filters()
        dialog.destroy()

    def on_edit_button_clicked(self, *args):
        filter = self.config.filters[self.get_selected_filter_index()]
        dialog = FilterDialog(self, "Edit Filter", filter)
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
        Dialog.__init__(self, "filter_dialog")
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

    def reset(self):
        self.name_entry.set_text("")
        self.name_entry.grab_focus()
        self.pattern_entry.set_text("")
        self.checkbutton1.set_active(False)

    def on_filter_dialog_response(self, widget, event, *args):
        if event != gtk.RESPONSE_OK:
            self.reset()
            return
        if self.user_input_ok():
            self.filter.name = self.name
            self.filter.pattern = self.pattern
            self.filter.alert = self.raise_alert
            self.reset()
        else:
            if not self.name:
                message = "Filter has no name"
            else:
                message = "Filter has no pattern"
            self.root_widget.emit_stop_by_name("response")
            dialog = ErrorDialog(self.root_widget, message,
                                 "Please specify a name and a pattern.")
            dialog.run()
            dialog.destroy()


class FilteredListStore(gtk.ListStore):

    def __init__(self, list_store, text):
        num_cols = list_store.get_n_columns()
        col_types = [list_store.get_column_type(n) for n in range(num_cols)]
        gtk.ListStore.__init__(self, *col_types)
        self.filter_text = text

    def append(self, row):
        if self.filter_text in " ".join(row):
            gtk.ListStore.append(self, row)

    def make(list_store, text):
        new_store = FilteredListStore(list_store, text)
        gtk_iter = list_store.get_iter_first()
        while gtk_iter is not None:
            row = []
            for i in range(list_store.get_n_columns()):
                row.append(list_store.get_value(gtk_iter, i))
            new_store.append(row)
            gtk_iter = list_store.iter_next(gtk_iter)
        return new_store

    make = staticmethod(make)


class SearchTools(WidgetWrapper):

    def __init__(self, main_window, message_view):
        WidgetWrapper.__init__(self, "search_tools", main_window)
        self.message_view = message_view

    def on_search_text_activate(self, *args):
        self.find_button.activate()

    def on_find_button_clicked(self, *args):
        text = self.search_text.get_text()
        if text == "":
            self.message_view.clear_filter()
        else:
            self.message_view.filter_by_text(text)
        self.search_text.grab_focus()
        self.message_view.update_message_count()


class MessageView(gtk.TreeView):

    DATE_COLUMN = 0
    HOST_COLUMN = 1
    PROCESS_COLUMN = 2
    MESSAGE_COLUMN = 3

    def __init__(self, config, notifier, status_bar):
        gtk.TreeView.__init__(self)
        config.add_observer(config.MESSAGES_KEPT, self)
        self.config = config
        self.notifier = notifier
        self.status_bar = status_bar
        self._observers = []
        self._unfiltered_model = None
        self._about_to_scroll_down = False
        self.unseen_alertable_messages = 0
        self.clear_alert()

    def update(self, key):
        if key == self.config.MESSAGES_KEPT:
            self.discard_old_messages()
        
    def get_unfiltered_model(self):
        return self._unfiltered_model

    def add_column(self, title, index):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(title, renderer, text=index)
        self.append_column(column)

    def set_unfiltered_model(self, model):
        self.set_model(model)
        self._unfiltered_model = model

    def setup(self):
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
                              gobject.TYPE_STRING, gobject.TYPE_STRING)
        model.connect("row-inserted", self.auto_scroll_down)
        self.set_unfiltered_model(model)
        self.add_column("Date", MessageView.DATE_COLUMN)
        self.add_column("Host", MessageView.HOST_COLUMN)
        self.add_column("Process", MessageView.PROCESS_COLUMN)
        self.add_column("Message", MessageView.MESSAGE_COLUMN)
        selection = self.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect("changed", self.on_selection_changed)

    def filter_by_text(self, text):
        model = self.get_unfiltered_model()
        filtered_model = FilteredListStore.make(model, text)
        self.set_model(filtered_model)
        self.auto_scroll_down()
        self.update_message_count()

    def clear_filter(self):
        self.set_model(self._unfiltered_model)
        self.auto_scroll_down()

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

    def is_scrolled_down(self):
        adjustment = self.get_parent().get_vadjustment()
        position = adjustment.value + adjustment.page_size
        sticky_range = 10  # pixels
        return int(position) + sticky_range >= int(adjustment.upper)

    def scroll_down(self):
        num_rows = self.get_model().iter_n_children(None)
        if num_rows > 0:
            last_row_path = (num_rows - 1,)
            self.scroll_to_cell(last_row_path)

    def auto_scroll_down(self, *args):
        # This method is connected to the row-inserted signal.
        #
        # TODO: only add idle handler if scroll not already scheduled

        # muntyan_: the point here is: scheduled function may or may
        # not be called before treeview revalidates, but it will be
        # called after all the rows are inserted, and scroll_to_* will
        # install another idle which will do correct thing

        if self.is_scrolled_down():
            gobject.idle_add(self.scroll_down)

    def count_rows_in_model(self, model):
        count = [0]

        def count_rows(model, iter, path):
            count[0] += 1

        model.foreach(count_rows)
        return count[0]

    def count_all_messages(self):
        return self.count_rows_in_model(self.get_unfiltered_model())

    def count_shown_messages(self):
        shown_model = self.get_model()
        total_model = self.get_unfiltered_model()
        if shown_model == total_model:
            return None
        else:
            return self.count_rows_in_model(shown_model)
    
    def remove_first_row(self):
        list_store = self.get_model()
        iter_first = list_store.get_iter_first()
        if iter_first:
            list_store.remove(iter_first)

    def append_message_to_models(self, message):
        row = (message.date, message.hostname, message.process, message.text)
        if self.get_model() != self.get_unfiltered_model():
            self.get_unfiltered_model().append(row)
        self.get_model().append(row)
        
    def update_message_count(self):
        # TODO: our model should automatically update the count, and
        # the view should observe it. Some refactoring required;
        # perhaps we need a subclass of ListStore that we can observe?
        total_messages = self.count_all_messages()
        shown_messages = self.count_shown_messages()
        self.status_bar.set_message_count(total_messages, shown_messages)

    def discard_old_messages(self):
        while self.count_all_messages() > self.config.messages_kept:
            self.remove_first_row()
        self.update_message_count()

    def add_message(self, message):
        self.append_message_to_models(message)
        self.discard_old_messages()

    def toplevel_has_focus(self):
        return self.get_toplevel().has_toplevel_focus()

    def raise_alert(self):
        self.unseen_alertable_messages += 1
        self.notifier.start_flashing()
        if self.unseen_alertable_messages == 1:
            text = "There is 1 new alert"
        else:
            text = "There are %d new alerts" % self.unseen_alertable_messages
        self.notifier.set_tool_tip(text)

    def clear_alert(self):
        self.unseen_alertable_messages = 0
        self.notifier.stop_flashing()
        self.notifier.set_tool_tip("There are no new alerts")
    
    def process_line(self, line):
        message = LogMessage(line)
        for message_filter in self.config.filters:
            if message_filter.matches(message.text):
                self.add_message(message)
                if (not self.toplevel_has_focus()) and message_filter.alert:
                    self.raise_alert()
                break

    def clear(self):
        self.get_model().clear()
        
    def delete_selected(self):
        selected = []

        def delete(model, path, iter):
            selected.append(iter)

        self.get_selection().selected_foreach(delete)
        for iter in selected:
            self.get_model().remove(iter)
        self.update_message_count()
        # TODO: fix next line so it works if last line selected
#         self.get_selection().select_iter(selected[-1])


class StatusBar(WidgetWrapper):

    def __init__(self, main_window):
        WidgetWrapper.__init__(self, "appbar", main_window)
        self.setup()

    def setup(self):
        self.set_message_count(0, None)

    def set_message_count(self, total, shown):
        status = "%s messages" % total
        if shown is not None:
            status += " (%s shown)" % shown
        self.appbar.set_status(status)
        

class MainWindow(Window):

    NAME = "app1"  # must match name of widget in glade file

    def __init__(self, config):
        Window.__init__(self, "app1")
        self.config = config
        status_bar = StatusBar(self)
        self.x_coord = 0
        self.y_coord = 0
        self.notifier = self.create_tray_icon()
        self.message_view = MessageView(self.config, self.notifier, status_bar)
        self.setup_widgets()
        self.monitor_syslog()

    def save_window_location(self):
        if self.root_widget.get_property("visible"):
            self.config.log_window_coords = self.root_widget.get_position()
            self.config.log_window_size = self.root_widget.get_size()

    def restore_window_location(self):
        self.root_widget.move(*self.config.log_window_coords)
        self.root_widget.resize(*self.config.log_window_size)

    def toggle_visibility(self):
        if self.root_widget.has_toplevel_focus():
            self.save_window_location()
            self.root_widget.hide()
        else:
            needs_moving = not self.root_widget.get_property("visible")
            if needs_moving:
                self.restore_window_location()
            self.root_widget.present()
            self.message_view.clear_alert()
        
    def create_tray_icon(self):
        popup_menu = PopupMenu(self.config)
        popup_menu.quit_callback = self.save_window_location
        notifier = FlashingNotifier("BandSawTrayIcon",
                                    img_path(bandsawconfig.ALERTICON),
                                    img_path(bandsawconfig.LOGICON),
                                    menu=popup_menu)
        notifier.trayicon.show_all()
        return notifier

    def setup_widgets(self):
        self.message_view.setup()
        self.scrolledwindow1.add(self.message_view)
        self.message_view.show()
        self.setup_buttons()
        self.message_view.observe_selection(self)
        SearchTools(self, self.message_view)
        self.notifier.left_click_callback = self.toggle_visibility

    def on_select_button_clicked(self, *args):
        self.message_view.select_all()

    def on_delete_button_clicked(self, *args):
        self.message_view.delete_selected()

    def set_transient_for_main_window(self):
        pass

    def selection_changed(self, have_selection):
        self.delete_button.set_sensitive(have_selection)

    def setup_buttons(self):
        self.select_button.connect("clicked", self.on_select_button_clicked)
        self.delete_button.connect("clicked", self.on_delete_button_clicked)
        self.delete_button.set_sensitive(False)

    def read_pipe(self, fd, condition):

        class EndOfFile(RuntimeError):
            pass

        end_of_line = "\n"

        try:
            fifo = os.fdopen(fd)
            buf = fifo.read()
            while True:
                if buf == "":
                    raise EndOfFile
                lines = buf.split(end_of_line)
                if buf.endswith(end_of_line):
                    lines = lines[:-1]
                    buf = lines[-1]
                for line in lines:
                    self.message_view.process_line(line)
                buf += fifo.read()
        except (EndOfFile, IOError), e:
            self.monitor_syslog()
            return False

    def monitor_syslog(self):
        try:
            fd = os.open(self.config.named_pipe, os.O_RDONLY | os.O_NONBLOCK)
        except OSError, e:
            dialog = ErrorDialog(self.root_widget, "Unable to open file",
                                 "The file '%s' cannot be read. Please check "
                                 "the permissions and try again." %
                                 self.config.named_pipe)
            dialog.run()
            dialog.destroy()
            sys.exit()
        else:
            gobject.io_add_watch(fd, gobject.IO_IN, self.read_pipe)
        
    def on_app1_delete_event(self, *args):
        self.toggle_visibility()
        return True


def main():
    config = Config(gconf.client_get_default())
    if config.is_first_run():
        window = WelcomeDruid(config)
        window.show()
    else:
        window = MainWindow(config)
    gtk.main()


if __name__ == "__main__":
    program = gnome.program_init("bandsaw", __VERSION__)
    main()
