#!/usr/bin/env python
#
# Public Domain 2014-2020 MongoDB, Inc.
# Public Domain 2008-2014 WiredTiger, Inc.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from wiredtiger import stat
from wtdataset import SimpleDataSet
from test_rollback_to_stable01 import test_rollback_to_stable_base

def timestamp_str(t):
    return '%x' % t

# test_rollback_to_stable06.py
# Test that rollback to stable removes all keys when the stable timestamp is earlier than
# all commit timestamps.
class test_rollback_to_stable06(test_rollback_to_stable_base):
    conn_config = 'cache_size=50MB,log=(enabled),statistics=(all)'
    session_config = 'isolation=snapshot'

    def test_rollback_to_stable(self):
        nrows = 10000

        # Create a table without logging.
        uri = "table:rollback_to_stable06"
        ds = SimpleDataSet(
            self, uri, 0, key_format="i", value_format="S", config='log=(enabled=false)')
        ds.populate()

        # Pin oldest and stable to timestamp 10.
        self.conn.set_timestamp('oldest_timestamp=' + timestamp_str(10) +
            ',stable_timestamp=' + timestamp_str(10))

        value_a = "aaaaa" * 100
        value_b = "bbbbb" * 100
        value_c = "ccccc" * 100
        value_d = "ddddd" * 100

        # Perform several updates.
        self.large_updates(uri, value_a, ds, nrows, 20)
        self.large_updates(uri, value_b, ds, nrows, 30)
        self.large_updates(uri, value_c, ds, nrows, 40)
        self.large_updates(uri, value_d, ds, nrows, 50)

        # Verify data is visible and correct.
        self.check(value_a, uri, nrows, 20)
        self.check(value_b, uri, nrows, 30)
        self.check(value_c, uri, nrows, 40)
        self.check(value_d, uri, nrows, 50)

        # Checkpoint to ensure the data is flushed, then rollback to the stable timestamp.
        self.session.checkpoint()
        self.conn.rollback_to_stable()

        # Check that all keys are removed.
        self.check(value_a, uri, 0, 20)
        self.check(value_b, uri, 0, 30)
        self.check(value_c, uri, 0, 40)
        self.check(value_d, uri, 0, 50)

        stat_cursor = self.session.open_cursor('statistics:', None, None)
        calls = stat_cursor[stat.conn.txn_rts][2]
        hs_removed = stat_cursor[stat.conn.txn_rts_hs_removed][2]
        keys_removed = stat_cursor[stat.conn.txn_rts_keys_removed][2]
        keys_restored = stat_cursor[stat.conn.txn_rts_keys_restored][2]
        pages_visited = stat_cursor[stat.conn.txn_rts_pages_visited][2]
        upd_aborted = stat_cursor[stat.conn.txn_rts_upd_aborted][2]
        stat_cursor.close()

        self.assertEqual(calls, 1)
        self.assertEqual(keys_restored, 0)
        self.assertEqual(keys_removed, nrows)
        self.assertGreater(pages_visited, 0)
        self.assertGreaterEqual(upd_aborted, 0)
        self.assertGreaterEqual(hs_removed, nrows * 3)

if __name__ == '__main__':
    wttest.run()
