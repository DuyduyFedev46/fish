"""
L8-PATCH (Lô 17a, A7): PATCH phiếu kiểm kê (ngày, ghi chú) nhận `expected_updated_at` TUỲ CHỌN.

Có thì so với `updated_at` hiện tại như `…/lines/` (lệch → 409 `STALE_STATE`, dữ liệu không đổi); không có thì giữ hành vi cũ.
"""
from .base import URL, StocktakeApiBase


class StocktakeUpdateStaleTests(StocktakeApiBase):
    def setUp(self):
        super().setUp()
        self.rec = self.make_draft()
        self.url = f"{URL}{self.rec['id']}/"

    def test_l8_patch_with_current_expected_updated_at_is_200_and_moves_updated_at(self):
        resp = self.api(self.manager).patch(
            self.url, {"note": "Đếm lại", "expected_updated_at": self.rec["updated_at"]}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["note"], "Đếm lại")
        self.assertNotEqual(resp.json()["updated_at"], self.rec["updated_at"])

    def test_l8_patch_with_stale_expected_updated_at_is_409_and_data_unchanged(self):
        first = self.api(self.manager).patch(
            self.url, {"note": "Người A", "expected_updated_at": self.rec["updated_at"]}, format="json",
        )
        self.assertEqual(first.status_code, 200, first.content)
        second = self.api(self.warehouse_staff).patch(
            self.url, {"note": "Người B", "expected_updated_at": self.rec["updated_at"]}, format="json",
        )
        self.assertEqual(second.status_code, 409, second.content)
        body = second.json()
        self.assertEqual(body["code"], "STALE_STATE")
        self.assertEqual(body["updated_at"], first.json()["updated_at"])
        self.assertEqual(self.recon(self.rec["id"]).note, "Người A")

    def test_l8_patch_without_expected_updated_at_keeps_old_behaviour(self):
        resp = self.api(self.manager).patch(self.url, {"note": "Không gửi mốc"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.recon(self.rec["id"]).note, "Không gửi mốc")

    def test_l8_patch_with_malformed_expected_updated_at_is_400(self):
        for raw in ("hôm qua", "2026-10-05T10:00:00", 123):  # sai kiểu, hoặc thiếu múi giờ
            resp = self.api(self.manager).patch(self.url, {"note": "x", "expected_updated_at": raw}, format="json")
            self.assertEqual(resp.status_code, 400, raw)
            self.assertEqual(resp.json()["code"], "EXPECTED_UPDATED_AT_INVALID")
        self.assertEqual(self.recon(self.rec["id"]).note, "Đếm đầu ca")

    def test_l8_expected_updated_at_is_not_saved_as_a_field(self):
        resp = self.api(self.manager).patch(
            self.url, {"count_date": str(self.today), "expected_updated_at": self.rec["updated_at"]}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_l8_without_permission_403_and_unauthenticated_401(self):
        payload = {"note": "x", "expected_updated_at": self.rec["updated_at"]}
        self.assertEqual(self.api(self.delivery_staff).patch(self.url, payload, format="json").status_code, 403)
        self.assertEqual(self.api(None).patch(self.url, payload, format="json").status_code, 401)
        self.assertEqual(self.recon(self.rec["id"]).note, "Đếm đầu ca")
