"""
Lô bổ sung A #11 (Duy chốt 02/10): `POST /api/sales/customer-directory/search/` body `{q, ordering?, page?}`.

Cùng quyền và `no-store` với GET, cùng shape với danh sách; từ khoá không nằm trong URL. GET `?q=` vẫn chạy.
Toàn bộ dữ liệu là giả.
"""
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.customers.tests.test_directory_api import (
    FAKE_ADDRESS, FAKE_NAME, FAKE_PHONE, LIST_URL, PERM, DirectoryBase,
)
from apps.sales.models import Customer, SalesOrder

SEARCH_URL = LIST_URL + "search/"


class DirectorySearchPostTests(DirectoryBase):
    def post(self, body, who="owner"):
        return self.clients[who].post(SEARCH_URL, body, format="json")

    def test_search_by_name_without_accent_and_by_phone(self):
        Customer.objects.create(phone="0900000124", name="Trần Văn Khác")
        self.assertEqual(self.post({"q": "khach thu"}).json()["count"], 1)
        self.assertEqual(self.post({"q": "0000123"}).json()["count"], 1)
        self.assertEqual(self.post({"q": "văn khác"}).json()["count"], 1)
        self.assertEqual(self.post({"q": "khong co"}).json()["count"], 0)

    def test_short_digits_do_not_match_phone(self):
        self.assertEqual(self.post({"q": "090"}).json()["count"], 0)

    def test_same_shape_and_rows_as_get(self):
        self.seed_history()
        got = self.get("owner", q="khach thu").json()
        posted = self.post({"q": "khach thu"}).json()
        self.assertEqual(set(posted), {"count", "next", "previous", "results"})
        self.assertEqual(posted["results"], got["results"])
        self.assertEqual(posted["count"], got["count"])

    def test_empty_body_lists_everyone(self):
        self.assertEqual(self.post({}).json()["count"], 1)

    def test_ordering_in_body_and_invalid_ordering_falls_back(self):
        older = Customer.objects.create(phone="0900000124", name="Khách Thử B")
        self.make_order(older, "SO-S1", SalesOrder.Status.COMPLETED, invoice="1000", day=1)
        self.make_order(self.customer, "SO-S2", SalesOrder.Status.COMPLETED, invoice="1000", day=5)
        asc = self.post({"ordering": "last_order_at"}).json()["results"]
        self.assertEqual([r["phone"] for r in asc], ["0900000124", FAKE_PHONE])
        self.assertEqual(self.post({"ordering": "phone; drop"}).status_code, 200)

    def test_page_in_body(self):
        for i in range(25):
            Customer.objects.create(phone=f"09100{i:05d}", name=f"Khách Thử {i}")
        first = self.post({"page": 1}).json()
        self.assertEqual((first["count"], len(first["results"])), (26, 20))
        self.assertTrue(first["next"])
        second = self.post({"page": 2}).json()
        self.assertEqual(len(second["results"]), 6)
        self.assertFalse(second["next"])
        self.assertEqual(self.post({"page": 99}).status_code, 404)

    def test_bad_body_is_400(self):
        for body in ({"q": {"a": 1}}, {"page": 0}, {"page": "x"}, {"ordering": ["a"]}):
            self.assertEqual(self.post(body).status_code, 400, body)

    def test_post_requires_same_permission_as_get(self):
        for who in ("warehouse", "courier", "service"):
            res = self.post({"q": "khach"}, who=who)
            self.assertEqual(res.status_code, 403, who)
            body = res.content.decode()
            for secret in (FAKE_NAME, FAKE_PHONE, FAKE_ADDRESS):
                self.assertNotIn(secret, body)
        self.assertEqual(self.post({"q": "khach"}, who="anonymous").status_code, 401)
        self.assertEqual(self.post({"q": "khach"}, who="manager").status_code, 200)
        extra = make_user("dir_search_extra", perms=(PERM,))
        self.assertEqual(client_for(extra).post(SEARCH_URL, {"q": "khach"}, format="json").status_code, 200)

    def test_response_is_no_store_and_keyword_not_in_url(self):
        res = self.post({"q": "khach thu"})
        self.assertIn("no-store", res.headers["Cache-Control"])
        self.assertNotIn("khach", str(res.json()["next"] or ""))

    def test_get_with_q_still_works(self):
        self.assertEqual(self.get("owner", q="khach thu").json()["count"], 1)

    def test_other_methods_on_search_and_create_on_list_stay_405(self):
        self.assertEqual(self.clients["owner"].get(SEARCH_URL).status_code, 405)
        self.assertEqual(self.clients["owner"].patch(SEARCH_URL, {}, format="json").status_code, 405)
        self.assertEqual(self.clients["owner"].post(LIST_URL, {"phone": "0900000999"}, format="json").status_code, 405)

    def test_no_cost_fields(self):
        raw = self.post({"q": "khach"}).content.decode()
        for word in ("purchase_rate", "landed_unit_cost", "unit_cost", "profit"):
            self.assertNotIn(word, raw)
