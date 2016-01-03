# -*- coding: utf-8 -*-
import unittest
import os

import datetime

from qifparse.parser import QifParser, QifParserInvalidDate


def build_data_path(fn):
    return os.path.join(os.path.dirname(__file__), 'data', fn)
filename = build_data_path('file.qif')
filename2 = build_data_path('transactions_only.qif')


class TestQIFParsing(unittest.TestCase):

    def testParseFile(self):
        qif = QifParser.parse(open(filename), date_format='dmy')
        self.assertTrue(qif)

    def testParseDateFormat(self):
        for file_number in range(1,9):
            with open(build_data_path('date_format_{0:02d}.qif'.format(file_number))) as fh:
                qif = QifParser.parse(fh)
                transaction = qif.get_transactions()[0][0]
                self.assertEqual(transaction.date, datetime.datetime(2016, 1, 2))

    def testParseDateFormatInconsistentDates(self):
        with open(build_data_path('date_format_error_01.qif')) as fh:
            self.assertRaises(QifParserInvalidDate, QifParser.parse, fh)

    def testParseDateFormatUnguessableDateFormat(self):
        with open(build_data_path('date_format_error_02.qif')) as fh:
            self.assertRaises(QifParserInvalidDate, QifParser.parse, fh)

    def testWriteFile(self):
        data = open(filename).read()
        qif = QifParser.parse(open(filename), date_format='dmy')
#        out = open('out.qif', 'w')
#        out.write(str(qif))
#        out.close()
        self.assertEquals(data, str(qif))

    def testParseTransactionsFile(self):
        data = open(filename2).read()
        qif = QifParser.parse(open(filename2))
#        out = open('out.qif', 'w')
#        out.write(str(qif))
#        out.close()
        self.assertEquals(data, str(qif))

if __name__ == "__main__":
    import unittest
    unittest.main()
