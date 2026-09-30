from django.db import connection
from django.test.utils import CaptureQueriesContext
from apps.common.tests.fixtures import client_for
from apps.delivery.tests.test_cskh_l2 import CskhL2BaseTestCase


class A1NPlus1(CskhL2BaseTestCase):
    def _count(self, user, url, n):
        c = client_for(user)
        with CaptureQueriesContext(connection) as ctx:
            r = c.get(url)
        return r.status_code, len(ctx.captured_queries)

    def test_counts(self):
        out = {}
        for n in (2, 8):
            for i in range(len(out.get("made", [])), n):
                pass
        made = 0
        res = {}
        for n in (2, 8):
            while made < n:
                self._create_paid_order(f"DH-N{made}", f"09000001{made:02d}", qty="1")
                made += 1
            res[n] = (
                self._count(self.ql, "/api/delivery/notes/", n),
                self._count(self.cs1, "/api/cskh/queue/", n),
            )
        print("\nnotes/queue (status, queries) for 2 vs 8 rows:", res)
