# Copyright (C) 2016 Stefano Zacchiroli <zack@upsilon.cc>
# License: GNU General Public License (GPL), version 2 or above

"""This Beancount plugin validates that each Beancount file that contains 2 or
more transactions is strictly chronologically ordered. I.e., no transaction
that occurs later in a given file (in file order) has a date that occurs
earlier (in calendar order) than a previous transaction in the same file.

While Beancount by default doesn't care about file ordering of directives,
ensuring in-file date ordering on transaction is a useful check to avoid
certain kinds of booking errors, e.g., copy-pasting an old transaction,
forgetting to bump its date.

"""

# TODO this plugin can be easily made configurable to, e.g.:
# - enforce reverse date ordering
# - enforce ordering on arbitrary metadata, not only date

import collections
from ast import literal_eval

from beancount.core.data import filter_txns

__plugins__ = ('file_ordering',)


FileOrderingError = collections.namedtuple(
    'FileOrderingError',
    'source message entry')


def txns_by_file(entries, list_ignore_files):
    """Group a list of transaction by origin file and sort them by line number.

    Args:
      entries: a list of directives. All non-transaction directives are ignored
      list_ignore_files: a list of files to ignore
    Returns:
      a dictionary mapping filenames to entries belonging to that file, sorted
      by line number

    """
    file_entries = {}  # return dict

    for entry in filter_txns(entries):  # group by file
        if 'filename' not in entry.meta:
            continue
        filename = entry.meta['filename']

        for ignore_file in list_ignore_files:
            if ignore_file in filename:
                break
        else:
            if filename not in file_entries:
                file_entries[filename] = []
            file_entries[filename].append(entry)

    for filename in file_entries:  # sort by line number
        file_entries[filename].sort(key=lambda e: e.meta['lineno'])

    return file_entries


def validate_date_ordering(entries):
    """Ensure that a given list of entries is chronologically ordered, from oldest
    to newest

    Args:
      entries: a list of directives
    Returns:
      a list of FileOrderingError errors, if any

    """
    errors = []
    prev_date = None

    for entry in entries:
        if prev_date and entry.date < prev_date:
            errors.append(FileOrderingError(
                entry.meta,
                'Date {} occurs after {}, violating in-file date ordering'
                .format(entry.date, prev_date),
                entry))

        prev_date = entry.date

    return errors


def file_ordering(entries, options_map, config="[]"):
    """Traverse all transactions in file order and ensure that, within the same
    file, their dates are strictly increasing.

    Args:
      entries: a list of directives

      options_map: an options map (unused)

      config: A configuration string, which is intended to be a Python list of files to ignore, e.g.
       "{['ignore.beancount', 'also_ignore.beancount']}"

    Returns:
      a list of new errors, if any

    """
    errors = []
    list_ignore_files = literal_eval(config)

    for file_entries in txns_by_file(entries, list_ignore_files).values():
        errors.extend(validate_date_ordering(file_entries))

    return entries, errors