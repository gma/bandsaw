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


import unittest

import bandsaw


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
        """Check date is an empty string for bad input message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.date, '')

    def test_hostname(self):
        """Check hostname is an empty string for bad input message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.hostname, '')

    def test_process(self):
        """Check the process details are an empty string for bad input message"""
        message = bandsaw.LogMessage(self.line)
        self.assertEqual(message.process, '')
        
    def test_message(self):
        """Check the message is an empty string for bad input"""
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
        

class MockGConfModule:

    def __init__(self, client):
        self.client = client
        
    def client_get_default(self):
        return self.client


class Mock:

    class MethodCall:

        def __init__(self, rval):
            self.rval = rval

        def __call__(self, *args):
            return self.rval

    def __init__(self):
        self.methods = []

    def __getattr__(self, name):
        method_name, return_value = self.methods.pop()
        assert name == method_name, \
               "expected call to '%s', not '%s'" % (method_name, name)
        return Mock.MethodCall(return_value)

    def register(self, method, value):
        self.methods.insert(0, (method, value))

    def verify(self):
        assert len(self.methods) == 0
        

class GConfTest(unittest.TestCase):

    def test_get_named_pipe(self):
        """Check we can get the path to the named pipe"""
        client = Mock()
        client.register('get_string', '/var/log/bandsaw.fifo')
        config = bandsaw.Config(client)
        self.assertEqual(config.named_pipe, '/var/log/bandsaw.fifo')
        client.verify()

    def test_get_messages_kept(self):
        """Check we can get the number of messages to keep"""
        client = Mock()
        client.register('get_int', 34)
        config = bandsaw.Config(client)
        self.assertEqual(config.messages_kept, 34)
        client.verify()

    def test_get_suppress_alerts(self):
        """Check we can determine whether we should suppress alerts"""
        client = Mock()
        client.register('get_bool', False)
        config = bandsaw.Config(client)
        self.assertEqual(config.suppress_alerts, False)
        client.verify()

    def test_get_suppress_minutes(self):
        """Check we can determine default minutes to suppress alerts"""
        client = Mock()
        client.register('get_int', 5)
        config = bandsaw.Config(client)
        self.assertEqual(config.suppress_minutes, 5)
        client.verify()

    def test_get_filters(self):
        """Check we can load existing filters"""
        client = Mock()
        client.register('get_list', ['Name 1', 'Name 2'])
        client.register('get_list', ['Pattern 1', 'Pattern 2'])
        client.register('get_list', [True, False])
        config = bandsaw.Config(client)
        filter1, filter2 = config.filters
        client.verify()

        self.assertEqual(filter1.name, 'Name 1')
        self.assert_(filter1.matches('Pattern 1'))
        self.assertEqual(filter1.alert, True)
        
        self.assertEqual(filter2.name, 'Name 2')
        self.assert_(filter2.matches('Pattern 2'))
        self.assertEqual(filter2.alert, False)
        

if __name__ == '__main__':
    unittest.main()
    
