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
import unittest

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

    def get_filters_mock(self):
        name_rval = return_value(['Name 1', 'Name 2'])
        pat_rval = return_value(['Pattern 1', 'Pattern 2'])
        bool_rval = return_value([True, False])

        client = Mock()
        key = bandsaw.Config.FILTER_NAMES
        client.expects(once()).get_list(
            eq(key), eq(gconf.VALUE_STRING)).will(name_rval)
        key = bandsaw.Config.FILTER_PATTERNS
        client.expects(once()).get_list(
            eq(key), eq(gconf.VALUE_STRING)).will(pat_rval)
        key = bandsaw.Config.FILTER_ALERTS
        client.expects(once()).get_list(
            eq(key), eq(gconf.VALUE_BOOL)).will(bool_rval)
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

    def test_read_named_pipe_once(self):
        """Check we only read named_pipe from GConf at start up"""
        client = self.get_named_pipe_mock()
        config = bandsaw.Config(client)
        config.named_pipe
        config.named_pipe
        client.verify()

    def test_read_messages_kept_once(self):
        """Check we only read messages_kept from GConf at start up"""
        client = self.get_messages_kept_mock()
        config = bandsaw.Config(client)
        config.messages_kept
        config.messages_kept
        client.verify()
        
    def test_read_ignore_alerts_once(self):
        """Check we only read ignore_alerts from GConf at start up"""
        client = self.get_ignore_alerts_mock()
        config = bandsaw.Config(client)
        config.ignore_alerts
        config.ignore_alerts
        client.verify()

    def test_read_ignore_timeout_once(self):
        """Check we only read ignore_timeout from GConf at start up"""
        client = self.get_ignore_timeout_mock()
        config = bandsaw.Config(client)
        config.ignore_timeout
        config.ignore_timeout
        client.verify()

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


if __name__ == '__main__':
     if 'srcdir' in os.environ:
         sys.argv.append('-v')
     unittest.main()
