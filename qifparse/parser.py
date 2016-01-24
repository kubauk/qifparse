# -*- coding: utf-8 -*-
import six
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from qifparse.qif import (
    Transaction,
    MemorizedTransaction,
    AmountSplit,
    Account,
    Investment,
    Category,
    Class,
    Qif,
)
import re

logger = logging.getLogger("qifparse")

DEFAULT_DATE_FORMAT = 'dmy'
DEFAULT_DECIMAL_SEP = '.'
DEFAULT_THOUSANDS_SEP = ''

NON_INVST_ACCOUNT_TYPES = [
    '!Type:Cash',
    '!Type:Bank',
    '!Type:Ccard',
    '!Type:CCard',
    '!Type:Oth A',
    '!Type:Oth L',
    '!Type:Invoice',  # Quicken for business only
]


class QifParserException(Exception):
    pass


class QifParserInvalidDate(QifParserException):
    pass


class QifParserInvalidNumber(QifParserException):
    pass


class QifParser(object):

    @classmethod
    def parse(cls_, file_handle, date_format=None, num_sep=None):
        if isinstance(file_handle, type('')):
            raise RuntimeError(
                six.u("parse() takes in a file handle, not a string"))
        data = file_handle.read()
        if len(data) == 0:
            raise QifParserException('Data is empty')
        if not date_format:
            date_format = cls_.guessDateFormat(cls_.getDateSamples(data))
        if num_sep is None:
            decimal_sep, thousands_sep = cls_.guessNumberFormat(cls_.getNumberSamples(data))
        else:
            decimal_sep, thousands_sep = num_sep
        qif_obj = Qif()
        chunks = data.split('\n^\n')
        last_type = None
        last_account = None
        transactions_header = None
        parsers = {
            'category': cls_.parseCategory,
            'account': cls_.parseAccount,
            'transaction': cls_.parseTransaction,
            'investment': cls_.parseInvestment,
            'class': cls_.parseClass,
            'memorized': cls_.parseMemorizedTransaction
        }
        for chunk in chunks:
            if not chunk:
                continue
            first_line = chunk.split('\n')[0]
            if first_line == '!Type:Cat':
                last_type = 'category'
            elif first_line == '!Account':
                last_type = 'account'
            elif first_line in NON_INVST_ACCOUNT_TYPES:
                last_type = 'transaction'
                transactions_header = first_line
            elif first_line == '!Type:Invst':
                last_type = 'investment'
                transactions_header = first_line
            elif first_line == '!Type:Class':
                last_type = 'class'
            elif first_line == '!Type:Memorized':
                last_type = 'memorized'
                transactions_header = first_line
            elif chunk.startswith('!'):
                raise QifParserException('Header not recognized: %s' % chunk)
            # if no header is recognized then
            # we use the previous one
            item = parsers[last_type](chunk, date_format, decimal_sep, thousands_sep)
            if last_type == 'account':
                qif_obj.add_account(item)
                last_account = item
            elif last_type == 'transaction'\
                    or last_type == 'memorized' or last_type == 'investment':
                if last_account:
                    last_account.add_transaction(item,
                                                 header=transactions_header)
                else:
                    qif_obj.add_transaction(item,
                                            header=transactions_header)
            elif last_type == 'category':
                qif_obj.add_category(item)
            elif last_type == 'class':
                qif_obj.add_class(item)
        return qif_obj

    @classmethod
    def parseClass(cls_, chunk,
                   date_format=DEFAULT_DATE_FORMAT,
                   decimal_sep=DEFAULT_DECIMAL_SEP,
                   thousands_sep=DEFAULT_THOUSANDS_SEP):
        curItem = Class()
        lines = chunk.split('\n')
        for line in lines:
            if not len(line) or line[0] == '\n' or \
                    line.startswith('!Type:Class'):
                continue
            elif line[0] == 'N':
                curItem.name = line[1:]
            elif line[0] == 'D':
                curItem.description = line[1:]
        return curItem

    @classmethod
    def parseCategory(cls_, chunk,
                      date_format=DEFAULT_DATE_FORMAT,
                      decimal_sep=DEFAULT_DECIMAL_SEP,
                      thousands_sep=DEFAULT_THOUSANDS_SEP):
        """
        """
        curItem = Category()
        lines = chunk.split('\n')
        for line in lines:
            if not len(line) or line[0] == '\n' or line.startswith('!Type'):
                continue
            elif line[0] == 'E':
                curItem.expense_category = True
            elif line[0] == 'I':
                curItem.income_category = True
                curItem.expense_category = False  # if ommitted is True
            elif line[0] == 'T':
                curItem.tax_related = True
            elif line[0] == 'D':
                curItem.description = line[1:]
            elif line[0] == 'B':
                curItem.budget_amount = line[1:]
            elif line[0] == 'R':
                curItem.tax_schedule_info = line[1:]
            elif line[0] == 'N':
                curItem.name = line[1:]
        return curItem

    @classmethod
    def parseAccount(cls_, chunk,
                     date_format=DEFAULT_DATE_FORMAT,
                     decimal_sep=DEFAULT_DECIMAL_SEP,
                     thousands_sep=DEFAULT_THOUSANDS_SEP):
        """
        """
        curItem = Account()
        lines = chunk.split('\n')
        for line in lines:
            if not len(line) or line[0] == '\n' or line.startswith('!Account'):
                continue
            elif line[0] == 'N':
                curItem.name = line[1:]
            elif line[0] == 'D':
                curItem.description = line[1:]
            elif line[0] == 'T':
                curItem.account_type = line[1:]
            elif line[0] == 'L':
                curItem.credit_limit = line[1:]
            elif line[0] == '/':
                curItem.balance_date = cls_.parseQifDateTime(line[1:], date_format)
            elif line[0] == '$':
                curItem.balance_amount = line[1:]
            else:
                logger.warn('Line not recognized: %s' % line)
        return curItem

    @classmethod
    def parseMemorizedTransaction(cls_, chunk,
                                  date_format=DEFAULT_DATE_FORMAT,
                                  decimal_sep=DEFAULT_DECIMAL_SEP,
                                  thousands_sep=DEFAULT_THOUSANDS_SEP):
        """
        """

        curItem = MemorizedTransaction()
        lines = chunk.split('\n')
        for line in lines:
            if not len(line) or line[0] == '\n' or \
                    line.startswith('!Type:Memorized'):
                continue
            elif line[0] == 'T':
                curItem.amount = cls_.parseQifNumber(line[1:], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            elif line[0] == 'C':
                curItem.cleared = line[1:]
            elif line[0] == 'P':
                curItem.payee = line[1:]
            elif line[0] == 'M':
                curItem.memo = line[1:]
            elif line[0] == 'K':
                curItem.mtype = line[1:]
            elif line[0] == 'A':
                if not curItem.address:
                    curItem.address = []
                curItem.address.append(line[1:])
            elif line[0] == 'L':
                cat = line[1:]
                if cat.startswith('['):
                    curItem.to_account = cat[1:-1]
                else:
                    curItem.category = cat
            elif line[0] == 'S':
                curItem.splits.append(AmountSplit())
                split = curItem.splits[-1]
                cat = line[1:]
                if cat.startswith('['):
                    split.to_account = cat[1:-1]
                else:
                    split.category = cat
            elif line[0] == 'E':
                split = curItem.splits[-1]
                split.memo = line[1:-1]
            elif line[0] == 'A':
                split = curItem.splits[-1]
                if not split.address:
                    split.address = []
                split.address.append(line[1:])
            elif line[0] == '$':
                split = curItem.splits[-1]
                split.amount = cls_.parseQifNumber(line[1:-1], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            else:
                # don't recognise this line; ignore it
                logger.warn("Skipping unknown line:\n" + str(line))
        return curItem

    @classmethod
    def parseTransaction(cls_, chunk,
                         date_format=DEFAULT_DATE_FORMAT,
                         decimal_sep=DEFAULT_DECIMAL_SEP,
                         thousands_sep=DEFAULT_THOUSANDS_SEP):
        """
        """

        curItem = Transaction()

        lines = chunk.split('\n')
        for line in lines:
            if not len(line) or line[0] == '\n' or line.startswith('!Type'):
                continue
            elif line[0] == 'D':
                curItem.date = cls_.parseQifDateTime(line[1:], date_format)
            elif line[0] == 'N':
                curItem.num = line[1:]
            elif line[0] == 'T':
                curItem.amount = cls_.parseQifNumber(line[1:], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            elif line[0] == 'C':
                curItem.cleared = line[1:]
            elif line[0] == 'P':
                curItem.payee = line[1:]
            elif line[0] == 'M':
                curItem.memo = line[1:]
            elif line[0] == '1':
                curItem.first_payment_date = line[1:]
            elif line[0] == '2':
                curItem.years_of_loan = line[1:]
            elif line[0] == '3':
                curItem.num_payments_done = line[1:]
            elif line[0] == '4':
                curItem.periods_per_year = line[1:]
            elif line[0] == '5':
                curItem.interests_rate = line[1:]
            elif line[0] == '6':
                curItem.current_loan_balance = line[1:]
            elif line[0] == '7':
                curItem.original_loan_amount = line[1:]
            elif line[0] == 'A':
                if not curItem.address:
                    curItem.address = []
                curItem.address.append(line[1:])
            elif line[0] == 'L':
                cat = line[1:]
                if cat.startswith('['):
                    curItem.to_account = cat[1:-1]
                else:
                    curItem.category = cat
            elif line[0] == 'S':
                curItem.splits.append(AmountSplit())
                split = curItem.splits[-1]
                cat = line[1:]
                if cat.startswith('['):
                    split.to_account = cat[1:-1]
                else:
                    split.category = cat
            elif line[0] == 'E':
                split = curItem.splits[-1]
                split.memo = line[1:-1]
            elif line[0] == 'A':
                split = curItem.splits[-1]
                if not split.address:
                    split.address = []
                split.address.append(line[1:])
            elif line[0] == '$':
                split = curItem.splits[-1]
                split.amount = cls_.parseQifNumber(line[1:-1], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            else:
                # don't recognise this line; ignore it
                logger.warn("Skipping unknown line:\n" + str(line))
        return curItem

    @classmethod
    def parseInvestment(cls_, chunk,
                        date_format=DEFAULT_DATE_FORMAT,
                        decimal_sep=DEFAULT_DECIMAL_SEP,
                        thousands_sep=DEFAULT_THOUSANDS_SEP):
        """
        """

        curItem = Investment()

        lines = chunk.split('\n')
        for line in lines:
            if not len(line) or line[0] == '\n' or line.startswith('!Type'):
                continue
            elif line[0] == 'D':
                curItem.date = cls_.parseQifDateTime(line[1:], date_format)
            elif line[0] == 'T':
                curItem.amount = cls_.parseQifNumber(line[1:], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            elif line[0] == 'N':
                curItem.action = line[1:]
            elif line[0] == 'Y':
                curItem.security = line[1:]
            elif line[0] == 'I':
                curItem.price = cls_.parseQifNumber(line[1:], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            elif line[0] == 'Q':
                curItem.quantity = cls_.parseQifNumber(line[1:], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            elif line[0] == 'C':
                curItem.cleared = line[1:]
            elif line[0] == 'M':
                curItem.memo = line[1:]
            elif line[0] == 'P':
                curItem.first_line = line[1:]
            elif line[0] == 'L':
                curItem.to_account = line[2:-1]
            elif line[0] == '$':
                curItem.amount_transfer = cls_.parseQifNumber(line[1:], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
            elif line[0] == 'O':
                curItem.commission = cls_.parseQifNumber(line[1:], decimal_sep=decimal_sep, thousands_sep=thousands_sep)
        return curItem

    @classmethod
    def getSamples(cls, data, data_type):
        skip = False
        for line in data.split('\n'):
            if line.startswith('!'):
                skip = False
            if line.startswith('!Account'):
                skip = True
            if line.startswith(data_type) and not skip:
                yield line[1:]

    @classmethod
    def getDateSamples(cls, data):
        return cls.getSamples(data, 'D')

    @classmethod
    def guessDateFormat(cls, samples):
        possible_date_formats = ['dmy', 'mdy', 'ymd']
        for sample in samples:
            for date_format in possible_date_formats[:]:
                try:
                    cls.parseQifDateTime(sample, date_format=date_format)
                except QifParserInvalidDate:
                    possible_date_formats.remove(date_format)
        if len(possible_date_formats) == 0:
            raise QifParserInvalidDate("Inconsistent or invalid date values")
        elif len(possible_date_formats) > 1:
            raise QifParserInvalidDate("It is not possible to guess the date format: please specify")
        return possible_date_formats[0]

    @classmethod
    def parseQifDateTime(cls_, qdate, date_format='dmy'):
        """
        Try to detect date format and parse it to datetime object
        :param qdate: date string
        :return: parsed datetime object
        """
        # manage y2k (e.g. 1/1'3 -> 1/1/2003)
        if qdate[-2] == "'":
            #e.g. 1/1'3
            norm_qdate = qdate.replace("'", "/200")
        elif qdate[-3] == "'":
            # e.g. 1/1'12
            norm_qdate = qdate.replace("'", "/20")
        else:
            # e.g. 1/1'2012
            norm_qdate = qdate.replace("'", "/")

        norm_qdate = norm_qdate.strip()

        try:
            (n1, n2, n3) = re.split(r'\W+', norm_qdate)
        except ValueError as err:
            raise QifParserInvalidDate("Invalid date: %s (normalized to %s): %s" % (qdate, norm_qdate, err))

        try:
            if date_format == 'dmy':
                return datetime(int(n3), int(n2), int(n1))
            elif date_format == 'mdy':
                return datetime(int(n3), int(n1), int(n2))
            elif date_format == 'ymd':
                return datetime(int(n1), int(n2), int(n3))
            else:
                raise QifParserInvalidDate("unsupported date_format: %s" % date_format)
        except ValueError as err:
            raise QifParserInvalidDate("Invalid date: %s (splitted to (%s, %s ,%s), %s): %s" %
                                       (qdate, n1, n2, n3, date_format, err))

    @classmethod
    def getNumberSamples(cls, data):
        return cls.getSamples(data, 'T')

    @classmethod
    def guessNumberFormat(cls, samples):
        possible_num_sep = [('.', ''), ('.', ','), (',', ''), (',', '.')]

        for sample in samples:
            for decimal_sep, thousands_sep in possible_num_sep[:]:
                try:
                    cls.parseQifNumber(sample, decimal_sep=decimal_sep, thousands_sep=thousands_sep)
                except (QifParserInvalidNumber, InvalidOperation):
                    possible_num_sep.remove((decimal_sep, thousands_sep))
        if len(possible_num_sep) == 0:
            raise QifParserInvalidNumber("Inconsistent or invalid number values")
        elif len(possible_num_sep) > 1:
            possible_decimal_seps = set([x[0] for x in possible_num_sep])
            if len(possible_decimal_seps) == 1:
                # There's only one possibility for decimal separator
                possible_thousands_seps = set([x[1] for x in possible_num_sep if x[1] != ''])
                if len(possible_thousands_seps) == 1:
                    # there is only one non empty alternative for thousands separator
                    return iter(possible_decimal_seps).next(), iter(possible_thousands_seps).next()
            raise QifParserInvalidNumber("""It is not possible to guess the number format:\
please specify. (possible formats: %s""" % repr(possible_num_sep))
        return possible_num_sep[0]

    @classmethod
    def parseQifNumber(cls, qnumber,
                       decimal_sep=DEFAULT_DECIMAL_SEP,
                       thousands_sep=DEFAULT_THOUSANDS_SEP):

        """

        :type qnumber: str
        """
        if decimal_sep == thousands_sep:
            raise QifParserException(
                    "Cannot parse number if decimal_sep is the same as thousands_sep (%s)" % decimal_sep)

        if qnumber.find(decimal_sep) != -1:
            try:
                int_p, frac_p = qnumber.split(decimal_sep)
            except ValueError:
                raise QifParserInvalidNumber("Something wrong with decimal separator '%s' in %s" % (decimal_sep, qnumber))
        else:
            int_p = qnumber
            frac_p = '0'

        if thousands_sep:
            thousands = int_p.split(thousands_sep)
            if len(thousands[0]) > 3:
                raise QifParserInvalidNumber("Something wrong with thousands separator '%s' in %s" % (thousands_sep, qnumber))
            for block in thousands[1:]:
                if len(block) != 3:
                    raise QifParserInvalidNumber("Something wrong with thousands separator '%s' in %s" % (thousands_sep, qnumber))
            int_p = int_p.replace(thousands_sep, '')
        else:
            try:
                int_p = int(int_p)
            except ValueError as err:
                raise QifParserInvalidNumber("Invalid integer part: %s: %s" % (int_p, err))

        return Decimal("%s.%s" % (int_p, frac_p))
