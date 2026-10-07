"""
NEW-1 (Lô 17b-BE, dữ liệu cá nhân, bất biến 9): tìm đơn theo SĐT/tên khách đi bằng `POST /api/sales/orders/search/`,
từ khoá nằm trong body nên không lọt vào access log. `GET ?q=` chỉ còn khớp mã đơn.
Toàn bộ dữ liệu là giả.
"""
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.common.tests.fixtures import client_for
from apps.delivery.models import DeliveryNote
from apps.sales.models import SalesOrder

from .test_s10_api import OrderApiBase

LIST_URL = "/api/sales/orders/"
SEARCH_URL = LIST_URL + "search/"


class SearchBase(OrderApiBase):
    def setUp(self):
        super().setUp()
        # Tên tiếng Anh cho các tài khoản của OrderApiBase (tên gốc chưa đổi).
        self.owner = self.chu  # naming: allow - tên thuộc tính của OrderApiBase dùng chung
        self.manager = self.ql  # naming: allow - tên thuộc tính của OrderApiBase dùng chung
        self.warehouse = self.kho  # naming: allow - tên thuộc tính của OrderApiBase dùng chung
        self.courier = self.giao  # naming: allow - tên thuộc tính của OrderApiBase dùng chung


class OrderSearchPostTests(SearchBase):
    def post(self, user, body):
        return client_for(user).post(SEARCH_URL, body, format="json")

    def ids(self, user, body):
        res = self.post(user, body)
        self.assertEqual(res.status_code, 200, res.content)
        return sorted(r["id"] for r in res.json()["results"])

    def test_new1_search_by_phone_name_without_accent_and_code(self):
        hoa = self._order(phone="0901234567", name="Chị Hoa")
        self._order(phone="0987654321", name="Anh Ba")
        self.assertEqual(self.ids(self.manager, {"q": "0901234"}), [hoa.pk])
        self.assertEqual(self.ids(self.manager, {"q": "CHỊ HOA"}), [hoa.pk])
        self.assertEqual(self.ids(self.manager, {"q": "chi hoa"}), [hoa.pk])
        self.assertEqual(self.ids(self.manager, {"q": hoa.code[-6:].lower()}), [hoa.pk])
        self.assertEqual(self.ids(self.manager, {"q": "khong co ai"}), [])

    def test_new1_same_shape_and_rows_as_list_without_q(self):
        self._order()
        got = client_for(self.manager).get(LIST_URL, {"status": "BOOKED"}).json()
        posted = self.post(self.manager, {"status": "BOOKED"}).json()
        self.assertEqual(set(posted), {"count", "next", "previous", "results"})
        self.assertEqual(posted["results"], got["results"])
        self.assertEqual(posted["count"], got["count"])

    def test_new1_filters_in_body_status_list_or_comma_and_dates(self):
        order = self._order()
        paid = self._paid_order(phone="0908888888", txn="FTNEW1A")
        self.assertEqual(self.ids(self.manager, {"status": "BOOKED"}), [order.pk])
        self.assertEqual(self.ids(self.manager, {"status": ["BOOKED"]}), [order.pk])
        self.assertEqual(self.ids(self.manager, {"status": f"BOOKED,{paid.status}"}), sorted([order.pk, paid.pk]))
        self.assertEqual(self.ids(self.manager, {"status": [paid.status]}), [paid.pk])
        self.assertEqual(self.ids(self.manager, {"date_from": "2999-01-01"}), [])
        res = self.post(self.manager, {"date_from": "24-09-2026"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "INVALID_FILTER")

    def test_new1_page_in_body_and_next_link_has_no_keyword(self):
        for i in range(22):
            self._order(phone=f"09100{i:05d}", name="Khách Thử")
        first = self.post(self.manager, {"q": "khach thu"}).json()
        self.assertEqual((first["count"], len(first["results"])), (22, 20))
        self.assertNotIn("khach", str(first["next"] or ""))
        second = self.post(self.manager, {"q": "khach thu", "page": 2}).json()
        self.assertEqual(len(second["results"]), 2)

    def test_new1_bad_body_is_400(self):
        for body in ({"q": {"a": 1}}, {"page": 0}, {"page": "x"}, {"status": 5}, {"batch": "x"}):
            self.assertEqual(self.post(self.manager, body).status_code, 400, body)

    def test_new1_scope_courier_only_sees_own_notes(self):
        mine = self._paid_order(phone="0901234567", txn="FTN1")
        other = self._paid_order(phone="0908888888", txn="FTN2")
        DeliveryNote.objects.filter(sales_invoice=mine.invoice).update(assigned_to=self.courier)
        self.assertEqual(self.ids(self.owner, {"q": "hoa"}), sorted([mine.pk, other.pk]))
        self.assertEqual(self.ids(self.courier, {"q": "hoa"}), [mine.pk])

    def test_new1_permission_403_401_and_no_personal_data_in_error(self):
        order = self._order(phone="0901234567", name="Chị Hoa")
        res = self.post(self.nobody, {"q": "0901234567"})
        self.assertEqual(res.status_code, 403)
        for secret in ("0901234567", "Chị Hoa", order.code):
            self.assertNotIn(secret, res.content.decode())
        self.assertEqual(APIClient().post(SEARCH_URL, {"q": "hoa"}, format="json").status_code, 401)
        self.assertEqual(self.post(self.warehouse, {"q": "hoa"}).status_code, 200)

    def test_new1_customer_filter_needs_customer_permission(self):
        order = self._order()
        self.assertEqual(self.post(self.manager, {"customer": order.customer_id}).status_code, 200)
        self.assertEqual(self.post(self.nobody, {"customer": order.customer_id}).status_code, 403)

    def test_new1_response_is_no_store(self):
        self.assertIn("no-store", self.post(self.manager, {"q": "hoa"}).headers["Cache-Control"])

    def test_new1_search_is_post_only(self):
        self.assertEqual(client_for(self.manager).get(SEARCH_URL).status_code, 405)

    def test_new1_no_cost_price_in_results(self):
        self._paid_order()
        body = self.post(self.owner, {"q": "hoa"}).content.decode()
        for key in ("unit_cost", "purchase_rate", "landed_unit_cost"):
            self.assertNotIn(key, body)

    def test_new1_post_keeps_scope_rules_for_phone_search(self):
        """Giữ luật SR-PII-02/PV-07 của GET cũ: không có quyền xem khách thì SĐT/tên không khớp, mã đơn vẫn khớp."""
        order = self._order(phone="0901234567", name="Chị Hoa")
        cache.clear()
        self.assertEqual(self.ids(self.warehouse, {"q": "0901234"}), [order.pk])


class OrderGetSearchRestrictedTests(SearchBase):
    """GET `?q=` chỉ còn nhận mã đơn: dãy từ 9 chữ số hoặc chuỗi giống tên người thì 400, không lặp lại `q`."""

    def get(self, q, user=None):
        return client_for(user or self.manager).get(LIST_URL, {"q": q})

    def test_new1_get_q_with_nine_digits_is_400_without_echo(self):
        for q in ("0901234567", "SO0901234567", "090123456", "09123456", "0912-345-678", "091.234.5678", "0912.345678", "0912-345678"):
            res = self.get(q)
            self.assertEqual(res.status_code, 400, q)
            self.assertEqual(res.json()["code"], "SEARCH_USE_POST")
            self.assertIn("ô tìm kiếm", res.json()["detail"])
            self.assertNotIn(q, res.content.decode())

    def test_new1_get_q_seven_digits_and_order_code_with_one_hyphen_still_ok(self):
        order = self._order()
        for q in ("0912345", order.code, "SO261007-123456", "SO-T003"):
            self.assertEqual(self.get(q).status_code, 200, q)

    def test_new1_get_q_that_looks_like_a_name_is_400_without_echo(self):
        for q in ("Chị Hoa", "nguyen van a", "Đạt", "Nguyễn"):
            res = self.get(q)
            self.assertEqual(res.status_code, 400, q)
            self.assertEqual(res.json()["code"], "SEARCH_USE_POST")
            self.assertNotIn(q, res.content.decode())

    def test_new1_get_q_matches_order_code_only(self):
        order = self._order(phone="0901234567", name="Chị Hoa")
        other = self._order(phone="0987654321", name="Anh Ba")
        for q in (order.code, order.code[-6:].lower(), order.code[:8]):
            res = self.get(q)
            self.assertEqual(res.status_code, 200, q)
            self.assertIn(order.pk, [r["id"] for r in res.json()["results"]])
        # Tên một từ không dấu (không phân biệt được với đoạn mã) cũng không còn khớp tên khách.
        self.assertEqual(self.get("hoa").json()["count"], 0)
        self.assertEqual(self.get("0901234").json()["count"], 0)
        self.assertNotIn(other.pk, [r["id"] for r in self.get(order.code).json()["results"]])

    def test_new1_get_without_q_unchanged(self):
        self._order()
        self.assertEqual(self.get("").status_code, 200)
        self.assertEqual(client_for(self.manager).get(LIST_URL).json()["count"], 1)

    def test_new1_permission_checked_before_q_rule(self):
        self.assertEqual(self.get("0901234567", user=self.nobody).status_code, 403)
