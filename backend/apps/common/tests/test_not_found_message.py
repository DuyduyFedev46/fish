"""
N-404 (Lô 17a, A1): 404 không lộ chữ tiếng Anh "No <Model> matches the given query." và không lộ tên model.

Câu 404 tiếng Việt riêng của view (vd "Không tìm thấy lô.") giữ nguyên. 401/403 không đổi.
"""
import re

from django.test import TestCase

from apps.common.tests.fixtures import client_for, make_user
from config.api_urls import router

MISSING_ID = 999999999
MISSING_UUID = "00000000-0000-0000-0000-000000000000"  # route có khoá chính UUID
GENERIC_404 = {"detail": "Không tìm thấy."}


class NotFoundMessageTests(TestCase):
    def setUp(self):
        self.superuser = make_user("u_super")
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()
        self.client = client_for(self.superuser)
        self.client.raise_request_exception = False  # id sai kiểu của route UUID có thể 500 (ngoài phạm vi A1)

    def test_n404_every_router_detail_route_has_vietnamese_generic_message(self):
        checked = 0
        for prefix, viewset, _basename in router.registry:
            response = self.client.get(f"/api/{prefix}/{MISSING_ID}/")
            if response.status_code == 500:
                response = self.client.get(f"/api/{prefix}/{MISSING_UUID}/")
            if response.status_code != 404:
                continue  # route không có `retrieve` (405) hoặc view tự xử lý khác
            checked += 1
            body = response.content.decode()
            self.assertNotIn("matches the given query", body, prefix)
            model = getattr(getattr(viewset, "queryset", None), "model", None)
            if model is not None:
                self.assertNotIn(model.__name__, body, prefix)
            self.assertTrue(response.json()["detail"].startswith("Không tìm thấy"), prefix)  # chung hoặc câu riêng
        self.assertGreaterEqual(checked, 15)

    def test_n404_default_django_message_pattern_is_replaced(self):
        # Mọi model của Django đều có câu gốc khớp mẫu này.
        self.assertTrue(re.match(r"^No \w+ matches the given query\.$", "No SalesOrder matches the given query."))
        response = self.client.get(f"/api/sales/orders/{MISSING_ID}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), GENERIC_404)

    def test_n404_does_not_echo_the_requested_id(self):
        response = self.client.get(f"/api/sales/orders/{MISSING_ID}/")
        self.assertNotIn(str(MISSING_ID), response.content.decode())

    def test_n404_views_with_their_own_vietnamese_message_keep_it(self):
        response = self.client.get("/api/reports/batch/KHONG-CO/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Không tìm thấy lô.")

    def test_n404_guidance_unknown_document_keeps_vietnamese_message(self):
        response = self.client.get(f"/api/guidance/stocktake/{MISSING_ID}/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("matches the given query", response.content.decode())

    def test_n404_unauthenticated_and_forbidden_unchanged(self):
        self.assertEqual(client_for(None).get(f"/api/sales/orders/{MISSING_ID}/").status_code, 401)
        courier = make_user("u_courier", "delivery_staff")
        self.assertEqual(client_for(courier).get("/api/purchasing/invoices/").status_code, 403)
