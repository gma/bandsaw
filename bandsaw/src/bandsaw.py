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


class SocketDialog(Dialog):

    def __init__(self):
        Dialog.__init__(self, 'socket_dialog')

    def get_path_to_socket(self):
        return self.path_entry.get_text()


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
        return ' '.join(self._words[5:])

    text = property(_get_text)


class LogView(WidgetWrapper):

    DATE_COLUMN = 0
    HOSTNAME_COLUMN = 1
    PROCESS_COLUMN = 2
    MESSAGE_COLUMN = 3

    def __init__(self):
        WidgetWrapper.__init__(self, 'scrolledwindow1')
        self.list_store = self.create_list_store()
        self.setup_treeview()

    def create_list_store(self):
        return gtk.ListStore(gobject.TYPE_STRING,
                             gobject.TYPE_STRING,
                             gobject.TYPE_STRING,
                             gobject.TYPE_STRING)

    def add_column(self, title, index):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(title, renderer, text=index)
        self.treeview1.append_column(column)
        self.treeview1.hide()

    def setup_treeview(self):
        self.treeview1.set_model(self.list_store)
        self.add_column('Date', LogView.DATE_COLUMN)
        self.add_column('Hostname', LogView.HOSTNAME_COLUMN)
        self.add_column('Process', LogView.PROCESS_COLUMN)
        self.add_column('Message', LogView.MESSAGE_COLUMN)

    def print_rows(self):
        def f(model, path, iter):
            print model.get_value(iter, 0)
        self.list_store.foreach(f)

    def process_line(self, line):
        message = LogMessage(line)
        self.list_store.append(
            (message.date, message.hostname, message.process, message.text))
        self.print_rows()


class MainWindow(Window):

    def __init__(self):
        Window.__init__(self, 'window1')
        self.monitor_id = None
        self.monitor_syslog()
        self.log_view = LogView()

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
        fifo_path = '/var/log/conductor/messages.fifo'
        fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        fifo = os.fdopen(fd)
        self.monitor_id = gtk.input_add(
            fifo, gtk.gdk.INPUT_READ, self.on_syslog_readable)
        
    def on_open1_activate(self, *args):
        dialog = SocketDialog()
        response = dialog.run()

    def quit(self):
        gtk.mainquit()
        
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
