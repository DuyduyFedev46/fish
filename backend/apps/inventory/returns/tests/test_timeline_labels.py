"""TLA-L1: guidance "chỉ dòng thời gian" của phiếu hàng hoàn hiểu `cancel_returntostock` (không rơi về "Có thay đổi")."""
from apps.common.tests.fixtures import client_for

from .base import NOTE_WITH_PHONE, PHONE_SENTINEL, URL, ReturnsApiBase

GUIDANCE = "/api/guidance/return/"


class ReturnCancelTimelineLabelTests(ReturnsApiBase):
    def test_tla_l1_cancel_has_vietnamese_label(self):
        rt = self.make_return(self.note, "4", self.courier, NOTE_WITH_PHONE)
        self.assertEqual(client_for(self.manager).post(f"{URL}{rt.pk}/cancel/", {}, format="json").status_code, 200)
        resp = client_for(self.owner).get(f"{GUIDANCE}{rt.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        rows = [r for r in resp.json()["timeline"] if r["kind"] == "cancel_returntostock"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["label"], "Huỷ phiếu hàng hoàn")
        self.assertNotIn("Có thay đổi", [r["label"] for r in resp.json()["timeline"]])
        self.assertNotIn(PHONE_SENTINEL, resp.content.decode())
