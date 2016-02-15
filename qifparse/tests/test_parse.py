# -*- coding: utf-8 -*-
import unittest
import os

import datetime

from decimal import Decimal

from qifparse.parser import QifParser, QifParserInvalidDate, QifParserInvalidNumber, QifParserException
from qifparse.qif import Qif, Account, Transaction, AmountSplit


def build_data_path(fn):
    return os.path.join(os.path.dirname(__file__), 'data', fn)

filename = build_data_path('file.qif')
filename2 = build_data_path('file2.qif')

filename3 = build_data_path('transactions_only.qif')


class TestQIFParsing(unittest.TestCase):
    maxDiff = None
    def _check(self, qif):
        self.assertTrue(qif)
        self.assertTrue(isinstance(qif, Qif))
        self.assertEqual(len(qif.get_accounts()), 2)
        cash_account = qif.get_accounts('My Cash')[0]
        self.assertTrue(isinstance(cash_account, Account))
        self.assertEqual(cash_account.name, 'My Cash')
        self.assertEqual(cash_account.account_type, 'Cash')
        cc_account = qif.get_accounts('My Cc')[0]
        self.assertTrue(isinstance(cc_account, Account))
        self.assertEqual(cc_account.name, 'My Cc')
        self.assertEqual(cc_account.account_type, 'Invst')
        cash_transactions = cash_account.get_transactions()
        self.assertEqual(len(cash_transactions), 1)
        self.assertEqual(len(cash_transactions[0]), 3)
        transaction = cash_transactions[0][0]
        self.assertTrue(isinstance(transaction, Transaction))
        self.assertEqual(transaction.date, datetime.datetime(2013, 10, 23))
        self.assertEqual(transaction.amount, Decimal("-6.50"))
        self.assertEqual(transaction.category, 'food:lunch')
        transaction = cash_transactions[0][1]
        self.assertEqual(transaction.to_account, 'My Cc')
        transaction = cash_transactions[0][2]
        self.assertEqual(transaction.date, datetime.datetime(2013, 10, 11))
        self.assertEqual(transaction.address, ['via Roma', '44100, Ferrara', 'Italy'])
        self.assertEqual(len(transaction.splits), 2)
        split = transaction.splits[0]
        self.assertTrue(isinstance(split, AmountSplit))
        self.assertEqual(split.amount, Decimal("-31.00"))
        self.assertEqual(split.to_account, 'My Cc')
        split = transaction.splits[1]
        self.assertEqual(split.category, 'food:lunch')

        cc_transactions = cc_account.get_transactions()
        self.assertEqual(len(cc_transactions), 2)

        all_transactions = qif.get_transactions(recursive=True)
        self.assertEqual(len(all_transactions), 3)

        noaccount_transactions = qif.get_transactions()
        self.assertEqual(len(noaccount_transactions), 0)

    def testParseFile(self):
        with open(filename) as fh:
            qif = QifParser.parse(fh, date_format='dmy')
        self._check(qif)

    def testParseCrLfFile(self):
        with open(filename2) as fh:
            qif = QifParser.parse(fh, date_format='dmy')
        self._check(qif)

    def testParseDateFormat(self):
        for file_number in range(1,9):
            with open(build_data_path('date_format_{0:02d}.qif'.format(file_number))) as fh:
                qif = QifParser.parse(fh, num_sep=('.', ''))
                transaction = qif.get_transactions()[0][0]
                self.assertEqual(transaction.date, datetime.datetime(2016, 1, 2))

    def testParseDateFormatInconsistentDates(self):
        with open(build_data_path('date_format_error_01.qif')) as fh:
            self.assertRaises(QifParserInvalidDate, QifParser.parse, fh, num_sep=('.', ''))

    def testParseDateFormatUnguessableDateFormat(self):
        with open(build_data_path('date_format_error_02.qif')) as fh:
            self.assertRaises(QifParserInvalidDate, QifParser.parse, fh, num_sep=('.', ''))

    def testParseNumberFormat(self):
        for file_number in range(1,4):
            with open(build_data_path('number_format_{0:02d}.qif'.format(file_number))) as fh:
                try:
                    qif = QifParser.parse(fh, date_format='dmy')
                except QifParserInvalidNumber as err:
                    raise QifParserInvalidNumber("%s in file %s" % (err, fh.name))
                transaction = qif.get_transactions()[0][0]
                self.assertEqual(transaction.amount, Decimal('-1234.56'))

    def testWriteFile(self):
        with open(filename) as fh:
            data = fh.read()
        with open(filename) as fh:
            qif = QifParser.parse(fh, date_format='dmy')
#        out = open('out.qif', 'w')
#        out.write(str(qif))
#        out.close()
        self.assertEqual(data, str(qif))

    def testParseTransactionsFile(self):
        with open(filename3) as fh:
            data = fh.read()
        with open(filename3) as fh:
            qif = QifParser.parse(fh)
#        out = open('out.qif', 'w')
#        out.write(str(qif))
#        out.close()
        self.assertEqual(data, str(qif))

    def testParseQifNumber(self):
        self.assertEqual(QifParser.parseQifNumber('1'), Decimal('1'))
        self.assertEqual(QifParser.parseQifNumber('1.2'), Decimal('1.2'))
        self.assertEqual(QifParser.parseQifNumber('1,2', decimal_sep=','), Decimal('1.2'))
        self.assertEqual(QifParser.parseQifNumber('1.234', decimal_sep='.'), Decimal('1.234'))
        self.assertEqual(QifParser.parseQifNumber('1.234', thousands_sep='.', decimal_sep=','), Decimal('1234'))
        self.assertEqual(QifParser.parseQifNumber('1,234', thousands_sep=','), Decimal('1234'))
        self.assertEqual(QifParser.parseQifNumber('1234', decimal_sep='.'), Decimal('1234'))
        self.assertEqual(QifParser.parseQifNumber('-1234.56', decimal_sep='.'), Decimal('-1234.56'))
        self.assertEqual(QifParser.parseQifNumber('-123,45', thousands_sep='.', decimal_sep=','), Decimal('-123.45'))
        self.assertRaises(QifParserException, QifParser.parseQifNumber, '-1234.56', decimal_sep=',')




if __name__ == "__main__":
    import unittest
    unittest.main()
