# $Id$


import unittest

import bandsaw


class LogMessageTest(unittest.TestCase):

    def setUp(self):
        self.line = 'Jun 23 14:02:37 hoopoo ldap[29913]: Hello  world'

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
        

if __name__ == '__main__':
    unittest.main()
    
