# $Id$


import ConfigParser
import os
import re
import select
import time

import pygtk; pygtk.require('2.0')
import gobject
import gtk
import gtk.glade


class Config:

    FILE = '../etc/bandsaw.conf'
    FILTER_PREFIX = 'Filter '
    GENERAL = 'General'
    MAX_MESSAGES_KEPT = 'keep-messages'
    MIN_ALERT_TIME = 'minimum-alert-time'
    NAMED_PIPE = 'named-pipe'
    PATTERN_ITEM = 'pattern'
    ALERT_ITEM = 'alert'

    def __init__(self):
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read(Config.FILE)

    def get_max_messages_kept(self):
        return self.parser.get(Config.GENERAL, Config.MAX_MESSAGES_KEPT)

    def get_minimum_alert_time(self):
        return self.parser.getboolean(Config.GENERAL, Config.MIN_ALERT_TIME)

    def get_named_pipe(self):
        return self.parser.get(Config.GENERAL, Config.NAMED_PIPE)

    def get_filters(self):
        filters = []
        for section in self.parser.sections():
            if section.startswith(Config.FILTER_PREFIX):
                name = section.split(' ', 1)[1]
                pattern = self.parser.get(section, Config.PATTERN_ITEM)
                alert = self.parser.getboolean(section, Config.ALERT_ITEM)
                filters.append(Filter(name, pattern, alert))
        return filters
        

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
                               '%s message received from %s</span>\n\n%s' %
                               (filter.name, message.hostname, message.text))

    def on_alert_dialog_delete_event(self, *args):
        self.destroy()

    def on_closebutton1_clicked(self, *args):
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
        return minutes >= self.config.get_minimum_alert_time()

    def raise_alert(self, filter, message):
        self.last_alert_time = time.time()
        dialog = AlertDialog(filter, message)
        dialog.show()
        
    def process_line(self, line):
        message = LogMessage(line)
        for filter in self.config.get_filters():
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

    def on_delete1_activate(self, *args):
        self.log_view.delete_selected()

    def on_select_all1_activate(self, *args):
        self.log_view.select_all()

    def on_preferences1_activate(self, *args):
        dialog = PreferencesDialog()
        dialog.run()


class MainWindow(Window):

    def __init__(self, config):
        Window.__init__(self, 'window1')
        self.monitor_id = None
        self.log_view = LogTreeView(config)
        self.log_view.setup()
        self.scrolledwindow1.add(self.log_view)
        self.log_view.show()
        self.setup_menu()
        self.monitor_syslog()

    def setup_menu(self):
        self.copy1.set_sensitive(gtk.FALSE)
        self.about1.set_sensitive(gtk.FALSE)
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
        fifo_path = '/var/log/bandsaw.fifo'
        fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        fifo = os.fdopen(fd)
        self.monitor_id = gtk.input_add(
            fifo, gtk.gdk.INPUT_READ, self.on_syslog_readable)
        
    def on_window1_delete_event(self, *args):
        gtk.mainquit()


class App:

    def main(self):
        config = Config()
        window = MainWindow(config)
        window.show()
        gtk.main()


if __name__ == '__main__':
    app = App()
    app.main()
