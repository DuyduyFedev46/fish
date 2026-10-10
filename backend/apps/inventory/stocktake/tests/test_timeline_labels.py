"""TLA-L1: guidance "chỉ dòng thời gian" của phiếu kiểm kê hiểu Gửi duyệt và Trả về nháp (không rơi về "Có thay đổi")."""
from apps.common.tests.fixtures import client_for

from .base import URL, StocktakeApiBase, line

GUIDANCE = "/api/guidance/stocktake/"


class StocktakeSubmitTimelineLabelTests(StocktakeApiBase):
    def test_tla_l1_submit_and_return_to_draft_have_vietnamese_labels(self):
        rec = self.create_via_api(self.warehouse_staff, [line(self.batch, "49", "hao hụt")])
        api = self.api(self.manager)
        self.assertEqual(api.post(f"{URL}{rec['id']}/submit/", {}, format="json").status_code, 200)
        self.assertEqual(api.post(f"{URL}{rec['id']}/return-to-draft/", {}, format="json").status_code, 200)
        resp = client_for(self.owner).get(f"{GUIDANCE}{rec['id']}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        by_kind = {r["kind"]: r["label"] for r in resp.json()["timeline"]}
        self.assertEqual(by_kind["submit_stockreconciliation"], "Gửi duyệt")
        self.assertEqual(by_kind["return_stockreconciliation_to_draft"], "Trả về nháp để sửa")


class StocktakeEditTimelineLabelTests(StocktakeApiBase):
    def test_tla_kk_edit_lines_and_edit_header_have_vietnamese_labels(self):
        rec = self.create_via_api(self.warehouse_staff, [line(self.batch, "49", "hao hụt")])
        api = self.api(self.manager)
        resp = self.replace_via_api(self.manager, rec, [line(self.batch, "48", "hao hụt")])
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(api.patch(f"{URL}{rec['id']}/", {"note": "Ghi chú mới"}, format="json").status_code, 200)
        resp = client_for(self.owner).get(f"{GUIDANCE}{rec['id']}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        by_kind = {r["kind"]: r["label"] for r in resp.json()["timeline"]}
        self.assertEqual(by_kind["update_reconciliation_lines"], "Sửa số đếm kiểm kê")
        self.assertEqual(by_kind["update_stockreconciliation"], "Sửa phiếu kiểm kê")
        for kind in ("update_reconciliation_lines", "update_stockreconciliation"):
            self.assertNotEqual(by_kind[kind], "Có thay đổi", kind)
