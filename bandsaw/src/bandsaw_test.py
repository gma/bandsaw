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
        

if __name__ == '__main__':
    unittest.main()
    
