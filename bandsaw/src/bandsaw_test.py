#!/usr/bin/env python
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
import sys
import time
import unittest

import pygtk; pygtk.require('2.0')
import gtk
import gconf
from pmock import *

import bandsaw


class GConfTest(unittest.TestCase):

    def get_named_pipe_mock(self):
        key = bandsaw.Config.NAMED_PIPE
        fifo_rval = return_value('/var/log/bandsaw.fifo')
        client = Mock()
        client.expects(once()).get_string(eq(key)).will(fifo_rval)
        return client

    def test_get_named_pipe(self):
        """Check we can get the path to the named pipe"""
        client = self.get_named_pipe_mock()
        config = bandsaw.Config(client)
        self.assertEqual(config.named_pipe, '/var/log/bandsaw.fifo')
        client.verify()

    def test_read_named_pipe_once(self):
        """Check we only read named_pipe from GConf at start up"""
        client = self.get_named_pipe_mock()
        config = bandsaw.Config(client)
        config.named_pipe
        config.named_pipe
        client.verify()

    def test_read_write_named_pipe(self):
        """Check changes made to named_pipe are picked up by reader"""
        new_fifo = '/home/user/.bandsaw.fifo'
        client = self.get_named_pipe_mock()
        config = bandsaw.Config(client)
        self.assertEqual(config.named_pipe, '/var/log/bandsaw.fifo')
        client.expects(once()).set_string(eq(bandsaw.Config.NAMED_PIPE),
                                          eq(new_fifo))
        config.named_pipe = new_fifo
        client.expects(once()).get_string(
            eq(bandsaw.Config.NAMED_PIPE)).will(return_value(new_fifo))
        self.assertEqual(config.named_pipe, new_fifo)
        client.verify()

    def get_messages_kept_mock(self):
        key = bandsaw.Config.MESSAGES_KEPT
        client = Mock()
        client.expects(once()).get_int(eq(key)).will(return_value(34))
        return client

    def test_get_messages_kept(self):
        """Check we can get the number of messages to keep"""
        client = self.get_messages_kept_mock()
        config = bandsaw.Config(client)
        self.assertEqual(config.messages_kept, 34)
        client.verify()

    def test_read_messages_kept_once(self):
        """Check we only read messages_kept from GConf at start up"""
        client = self.get_messages_kept_mock()
        config = bandsaw.Config(client)
        config.messages_kept
        config.messages_kept
        client.verify()

    def test_read_write_messages_kept(self):
        """Check changes made to messages_kept are picked up by reader"""
        new_value = 10
        client = self.get_messages_kept_mock()
        config = bandsaw.Config(client)
        self.assertEqual(config.messages_kept, 34)
        client.expects(once()).set_int(eq(bandsaw.Config.MESSAGES_KEPT),
                                       eq(new_value))
        config.messages_kept = new_value
        client.expects(once()).get_int(
            eq(bandsaw.Config.MESSAGES_KEPT)).will(return_value(new_value))
        self.assertEqual(config.messages_kept, new_value)
        client.verify()
        
    def get_ignore_alerts_mock(self):
        key = bandsaw.Config.IGNORE_ALERTS
        client = Mock()
        client.expects(once()).get_bool(eq(key)).will(return_value(False))
        return client

    def test_get_ignore_alerts(self):
        """Check we can determine whether we should ignore alerts"""
        client = self.get_ignore_alerts_mock()
        config = bandsaw.Config(client)
        self.assertEqual(config.ignore_alerts, False)
        client.verify()

    def test_read_ignore_alerts_once(self):
        """Check we only read ignore_alerts from GConf at start up"""
        client = self.get_ignore_alerts_mock()
        config = bandsaw.Config(client)
        config.ignore_alerts
        config.ignore_alerts
        client.verify()

    def get_ignore_timeout_mock(self):
        key = bandsaw.Config.IGNORE_TIMEOUT
        client = Mock()
        client.expects(once()).get_int(eq(key)).will(return_value(5))
        return client
    
    def test_get_ignore_timeout(self):
        """Check we can determine default minutes to ignore alerts"""
        client = self.get_ignore_timeout_mock()
        config = bandsaw.Config(client)
        self.assertEqual(config.ignore_timeout, 5)
        client.verify()

    def test_read_ignore_timeout_once(self):
        """Check we only read ignore_timeout from GConf at start up"""
        client = self.get_ignore_timeout_mock()
        config = bandsaw.Config(client)
        config.ignore_timeout
        config.ignore_timeout
        client.verify()

    def get_filters_mock(self):
        client = Mock()
        key = bandsaw.Config.FILTER_NAMES
        name_rval = return_value(['Name 1', 'Name 2'])
        client.expects(once()).get_list(
            eq(key), eq(gconf.VALUE_STRING)).will(name_rval)
        key = bandsaw.Config.FILTER_PATTERNS
        pattern_rval = return_value(['Pattern 1', 'Pattern 2'])
        client.expects(once()).get_list(
            eq(key), eq(gconf.VALUE_STRING)).will(pattern_rval)
        key = bandsaw.Config.FILTER_ALERTS
        alert_rval = return_value([True, False])
        client.expects(once()).get_list(
            eq(key), eq(gconf.VALUE_BOOL)).will(alert_rval)
        return client

    def test_get_filters(self):
        """Check we can load existing filters"""
        client = self.get_filters_mock()
        config = bandsaw.Config(client)
        filter1, filter2 = config.filters
        client.verify()

        self.assertEqual(filter1.name, 'Name 1')
        self.assert_(filter1.matches('Pattern 1'))
        self.assertEqual(filter1.alert, True)
        
        self.assertEqual(filter2.name, 'Name 2')
        self.assert_(filter2.matches('Pattern 2'))
        self.assertEqual(filter2.alert, False)

    def test_read_filters_once(self):
        """Check we only read filters from GConf at start up"""
        client = self.get_filters_mock()
        config = bandsaw.Config(client)
        config.filters
        config.filters
        client.verify()


class LogMessageTest(unittest.TestCase):

    def setUp(self):
        self.line = 'Jun 23 14:02:37 hoopoo ldap[29913]: Hello  world\n'

    def test_date(self):
        """Check we can extract the date from a log message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.date, 'Jun 23 14:02:37')

    def test_date_single_figure_day(self):
        """Check we can extract the date when the day is a single digit"""
        line = 'Jun  1 14:02:37 hoopoo ldap[29913]: Hello  world\n'
        message = bandsaw.LogMessage(line)
        self.assertEqual(message.date, 'Jun  1 14:02:37')

    def test_hostname(self):
        """Check we can extract the hostname from a log message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.hostname, 'hoopoo')

    def test_process(self):
        """Check we can extract the process details from a log message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.process, 'ldap[29913]')
        
    def test_message(self):
        """Check we can extract the text from a log message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.text, 'Hello  world')


class BadLogMessageTest(unittest.TestCase):

    def setUp(self):
        self.line = 'Jun 23 14:\n'

    def test_date(self):
        """Check date is empty string for bad input message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.date, '')

    def test_hostname(self):
        """Check hostname is empty string for bad input message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.hostname, '')

    def test_process(self):
        """Check the process details are empty string for bad input message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.process, '')
        
    def test_message(self):
        """Check the message is empty string for bad input"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.text, '')


class FilterTest(unittest.TestCase):

    def test_matches_good_string(self):
        """Check filter matches with plain string"""
        filter = bandsaw.Filter('Test', 'ever', False)
        self.assert_(filter.matches('Fever Pitch'))

    def test_matches_bad_string(self):
        """Check filter doesn't match with plain string"""
        filter = bandsaw.Filter('Test', 'ever', False)
        self.failIf(filter.matches('Pitch a tent'))

    def test_matches_good_regex(self):
        """Check filter matches with a regex"""
        filter = bandsaw.Filter('Test', '^\w{3} apple', False)
        self.assert_(filter.matches('red apple'))


class FilterSetTest(unittest.TestCase):

    def setUp(self):
        self.filter1 = bandsaw.Filter('Filter 1', 'Pattern 1', True)
        self.filter2 = bandsaw.Filter('Filter 2', 'Pattern 2', True)
        self.filter3 = bandsaw.Filter('Filter 3', 'Pattern 3', True)

    def test_add_filter(self):
        """Check we can append a filter to a filter set"""
        set = bandsaw.FilterSet()
        set.append(self.filter1)
        self.assertEqual(set, [self.filter1])

    def test_remove_filter(self):
        """Check we can remove a filter from a filter set"""
        set = bandsaw.FilterSet()
        set.append(self.filter1)
        set.append(self.filter2)
        set.append(self.filter3)
        set.pop(1)
        self.assertEqual(set, [self.filter1, self.filter3])

    def test_update_filter(self):
        """Check we can update a filter in a filter set"""
        set = bandsaw.FilterSet()
        set.append(self.filter1)
        set.append(self.filter2)
        set.append(self.filter3)
        self.filter2.name = 'New name'
        set.update(self.filter2)
        self.assertEqual(set, [self.filter1, self.filter2, self.filter3])
        self.assertEqual(set[1].name, 'New name')

    def test_move_filter(self):
        """Check we can move a filter up or down"""
        set = bandsaw.FilterSet()
        set.append(self.filter1)
        set.append(self.filter2)
        set.move_up(1)
        self.assertEqual(set, [self.filter2, self.filter1])
        set.move_down(0)
        self.assertEqual(set, [self.filter1, self.filter2])


class AlertTest(unittest.TestCase):

    def setUp(self):
        self.filter = bandsaw.Filter('Everything', '.', True)
        self.message = bandsaw.LogMessage('Jul 19 08:55:50 host proc[1]: foo')


class AlertQueueTest(AlertTest):
      
    def test_clear(self):
        """Check we can clear the alert queue"""
        config = Mock()
        queue = bandsaw.AlertQueue(config)
        queue.alert_displayed = True
        queue.append(self.filter, self.message)
        queue.append(self.filter, self.message)
        self.assertEqual(len(queue), 2)
        queue.clear()
        self.assertEqual(len(queue), 0)

    def test_pop(self):
        """Check pop removes an alert from the queue"""
        config = Mock()
        queue = bandsaw.AlertQueue(config)
        queue.alert_displayed = True
        queue.append(self.filter, self.message)
        queue.append(self.filter, self.message)
        self.assertEqual(len(queue), 2)
        queue.pop()
        self.assertEqual(len(queue), 1)

    def test_append_dialog_visible_alerts_ignored(self):
        """Check messages appended when dialog visible, alerts ignored"""
        config = Mock()
        config.ignore_alerts = True
        config.ignore_timeout = 5
        queue = bandsaw.AlertQueue(config)
        queue.alert_displayed = True
        queue.last_alert_time = time.time() - 10  # last alert very recent
        self.assertEqual(len(queue), 0)
        queue.append(self.filter, self.message)
        self.assertEqual(len(queue), 1)

    def test_append_dialog_visible_alerts_not_ignored(self):
        """Check messages appended when dialog visible, alerts not ignored"""
        config = Mock()
        config.ignore_alerts = False
        queue = bandsaw.AlertQueue(config)
        queue.alert_displayed = True
        self.assertEqual(len(queue), 0)
        queue.append(self.filter, self.message)
        self.assertEqual(len(queue), 1)

    def test_append_no_dialog_alerts_ignored(self):
        """Check messages not appended when no dialog, alerts ignored"""
        config = Mock()
        config.ignore_alerts = True
        config.ignore_timeout = 5
        queue = bandsaw.AlertQueue(config)
        queue.last_alert_time = time.time() - 10  # last alert very recent
        self.assertEqual(len(queue), 0)
        queue.append(self.filter, self.message)
        self.assertEqual(len(queue), 0)
        self.assertEqual(queue.alert_displayed, False)

    def test_append_no_dialog_alerts_not_ignored(self):
        """Check messages not appended when no dialog, alrets not ignored"""
        config = Mock()
        config.ignore_alerts = False
        config.ignore_timeout = 5
        queue = bandsaw.AlertQueue(config)
        queue.alert_displayed = False
        self.assertEqual(len(queue), 0)
        self.assertEqual(queue.alert_displayed, False)
        queue.append(self.filter, self.message)
        self.assertEqual(len(queue), 0)
        self.assertEqual(queue.alert_displayed, True)


class AlertDialogTest(AlertTest):

    def test_queue_cleared_if_ignored(self):
        """Check that the queue is cleared if alerts are ignored"""
        queue = Mock()
        queue.expects(once()).clear()
        config = Mock()
        config.ignore_alerts = False
        config.ignore_timeout = 5
        dialog = bandsaw.AlertDialog(queue, config, self.filter, self.message)
        dialog.checkbutton1.set_active(gtk.TRUE)
        dialog.on_okbutton1_clicked()
        queue.verify()        

    def test_show_next_alert(self):
        """Check next alert displayed if alerts not ignored"""
        queue = Mock()
        queue.expects(once()).pop()
        config = Mock()
        config.ignore_alerts = False
        config.ignore_timeout = 5
        dialog = bandsaw.AlertDialog(queue, config, self.filter, self.message)
        dialog.checkbutton1.set_active(gtk.FALSE)
        dialog.on_okbutton1_clicked()
        queue.verify()


if __name__ == '__main__':
     if 'srcdir' in os.environ:
         sys.argv.append('-v')
     if bandsaw.TESTING not in os.environ:
         os.environ[bandsaw.TESTING] = '1'
     unittest.main()
