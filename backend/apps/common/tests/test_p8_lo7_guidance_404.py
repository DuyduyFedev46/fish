"""
P8 Lô 7 — nợ Lô 2 L5: guidance refund/batch/payment trả 404 với thông điệp CỐ ĐỊNH, không lặp lại `doc_id`
người gọi gửi lên (không phản chiếu chuỗi tuỳ ý). Dữ liệu giả.
"""
from django.test import TestCase

from apps.common.tests.fixtures import client_for, make_user

SENTINEL = "KhachGiaB0900000999"


class GuidanceNotFoundFixedMessageTests(TestCase):
    def setUp(self):
        self.chu = client_for(make_user("g404_chu", "chu"))

    def _assert_fixed(self, doc_type):
        for doc_id in (SENTINEL, "999999"):
            with self.subTest(doc_type=doc_type, doc_id=doc_id):
                res = self.chu.get(f"/api/guidance/{doc_type}/{doc_id}/")
                self.assertEqual(res.status_code, 404, res.content)
                self.assertNotIn(SENTINEL, res.content.decode())
                self.assertNotIn("999999", res.content.decode())

    def test_l5_refund_404_khong_lap_lai_doc_id(self):
        self._assert_fixed("refund")

    def test_l5_batch_404_khong_lap_lai_doc_id(self):
        self._assert_fixed("batch")

    def test_l5_payment_404_khong_lap_lai_doc_id(self):
        self._assert_fixed("payment")

    def test_l5_khong_co_quyen_van_403_khong_phai_404(self):
        giao = client_for(make_user("g404_giao", "nv_giao"))
        for doc_type in ("refund", "batch", "payment"):
            with self.subTest(doc_type=doc_type):
                self.assertEqual(giao.get(f"/api/guidance/{doc_type}/{SENTINEL}/").status_code, 403)

    def test_l5_khach_401(self):
        self.assertEqual(client_for(None).get(f"/api/guidance/batch/{SENTINEL}/").status_code, 401)
