# $Id$


import os
import select

import pygtk; pygtk.require('2.0')
import gobject
import gtk
import gtk.glade


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


class LogTreeView(gtk.TreeView):

    DATE_COLUMN = 0
    HOSTNAME_COLUMN = 1
    PROCESS_COLUMN = 2
    MESSAGE_COLUMN = 3

    FILTERS = ('WARN', 'ERROR')

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

    def _message_matches_filter(self, message):
        for filter in LogTreeView.FILTERS:
            if filter in message.text:
                return True
        return False

    def process_line(self, line):
        message = LogMessage(line)
        if self._message_matches_filter(message):
            row = (message.date, message.hostname, message.process, message.text)
            self.get_model().append(row)


class MainWindow(Window):

    def __init__(self):
        Window.__init__(self, 'window1')
        self.monitor_id = None
        self.monitor_syslog()
        self.log_view = LogTreeView()
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

    def on_clear_all1_activate(self, *args):
        self.log_view.get_model().clear()
        
    def on_window1_delete_event(self, *args):
        self.quit()

    def on_quit1_activate(self, *args):
        self.quit()
        

class App:

    def main(self):
        window = MainWindow()
        window.show()
        gtk.main()


if __name__ == '__main__':
    app = App()
    app.main()
