# $Id$


import ConfigParser
import os
import re
import select

import pygtk; pygtk.require('2.0')
import gobject
import gtk
import gtk.glade


class Config:

    FILE = '../etc/bandsaw.conf'
    PATTERN_ITEM = 'pattern'
    ALERT_ITEM = 'alert'

    def __init__(self):
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read(Config.FILE)

    def get_filters(self):
        filters = []
        for section in self.parser.sections():
            if section.startswith('Filter '):
                name = section.split(' ', 1)[1]
                pattern = self.parser.get(section, Config.PATTERN_ITEM)
                alert = self.parser.getboolean(section, Config.ALERT_ITEM)
                filters.append(Filter(name, pattern, alert))
        return filters
        

class WidgetWrapper(object):

    def __init__(self, root_widget):
        self._root_widget_name = root_widget
        self._xml = gtk.glade.XML('bandsaw.glade', root_widget)
        self._connect_signals()

    def _get_root_widget(self):
        return getattr(self, self._root_widget_name)

    root_widget = property(_get_root_widget)

    def __getattr__(self, name):
        widget = self._xml.get_widget(name)
        if widget is None:
            raise AttributeError, name
        return widget
    
    def _connect_signals(self):
        for name in self.__class__.__dict__.keys():
            if hasattr(self, name):
                candidate_callback = getattr(self, name)
                if callable(candidate_callback):
                    self._xml.signal_connect(name, candidate_callback)


class Window(WidgetWrapper):

    def show(self):
        self.root_widget.show()

    def destroy(self):
        self.root_widget.destroy()


class Dialog(WidgetWrapper):

    def run(self):
        self.root_widget.run()
    
    def destroy(self):
        self.root_widget.destroy()


class Filter:

    def __init__(self, name, pattern, alert):
        self.name = name
        self.pattern = re.compile(pattern)
        self.alert = alert

    def matches(self, text):
        return self.pattern.search(text) is not None


class PreferencesDialog(Dialog):

    def __init__(self):
        Dialog.__init__(self, 'filter_dialog')


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
        self.label1.set_markup('<span weight="bold" size="larger">'
                               '%s message received from %s</span>\n\n%s' %
                               (filter.name, message.hostname, message.text))
        

class LogTreeView(gtk.TreeView):

    DATE_COLUMN = 0
    HOSTNAME_COLUMN = 1
    PROCESS_COLUMN = 2
    MESSAGE_COLUMN = 3

    def __init__(self, config):
        gtk.TreeView.__init__(self)
        self.config = config

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
        self.show()

    def process_line(self, line):
        msg = LogMessage(line)
        for filter in self.config.get_filters():
            if filter.matches(msg.text):
                row = (msg.date, msg.hostname, msg.process, msg.text)
                self.get_model().append(row)
                if filter.alert:
                    dialog = AlertDialog(filter, msg)
                    dialog.run()
                    dialog.destroy()
                continue

    def clear_all(self):
        self.get_model().clear()


class MainWindow(Window):

    def __init__(self, config):
        Window.__init__(self, 'window1')
        self.monitor_id = None
        self.monitor_syslog()
        self.log_view = LogTreeView(config)
        self.log_view.setup()
        self.scrolledwindow1.add(self.log_view)
        self.log_view.show()

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
        fifo_path = '/var/log/bandsaw.fifo'
        fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        fifo = os.fdopen(fd)
        self.monitor_id = gtk.input_add(
            fifo, gtk.gdk.INPUT_READ, self.on_syslog_readable)
        
    def quit(self):
        gtk.mainquit()

    def on_window1_delete_event(self, *args):
        self.quit()

    def on_quit1_activate(self, *args):
        self.quit()

    def on_clear1_activate(self, *args):
        self.log_view.clear_all()

    def on_preferences1_activate(self, *args):
        dialog = PreferencesDialog()
        dialog.run()


class App:

    def main(self):
        config = Config()
        window = MainWindow(config)
        window.show()
        gtk.main()


if __name__ == '__main__':
    app = App()
    app.main()
