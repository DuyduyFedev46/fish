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
