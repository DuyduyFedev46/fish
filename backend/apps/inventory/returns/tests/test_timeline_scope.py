"""R9: provider dòng thời gian `return` dùng CHUNG hàm phạm vi với API (nợ review Lô 2 L1). Dữ liệu giả."""
from apps.common.tests.fixtures import client_for
from apps.inventory.models import ReturnToStock
from apps.inventory.returns.scope import scope_returns_for

from .base import NOTE_WITH_PHONE, PHONE_SENTINEL, ReturnsApiBase

GUIDANCE = "/api/guidance/return/"


class ReturnTimelineScopeTests(ReturnsApiBase):
    def setUp(self):
        super().setUp()
        self.mine = self.post(self.courier, self.payload(delivery_note=self.note, qty="2")).json()
        # API đã chặn ghi chú có SĐT; gài thẳng vào DB để vẫn kiểm timeline không rò dữ liệu cũ.
        ReturnToStock.objects.filter(pk=self.mine["id"]).update(note=NOTE_WITH_PHONE)
        self.theirs = self.post(self.warehouse_staff, self.payload(delivery_note=self.other_note, qty="3")).json()

    def get(self, user, rt_id):
        return client_for(user).get(f"{GUIDANCE}{rt_id}/")

    def test_r2_return_other_courier_timeline_404(self):
        self.assertEqual(self.get(self.courier, self.mine["id"]).status_code, 200)
        resp = self.get(self.courier, self.theirs["id"])
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertEqual(self.get(self.other_courier, self.mine["id"]).status_code, 404)

    def test_r2_full_scope_groups_see_every_timeline(self):
        for user in (self.owner, self.manager, self.warehouse_staff):
            for rt in (self.mine, self.theirs):
                self.assertEqual(self.get(user, rt["id"]).status_code, 200, (user.username, rt["id"]))

    def test_r2_customer_service_403_and_unauthenticated_401(self):
        self.assertEqual(self.get(self.customer_service, self.mine["id"]).status_code, 403)
        self.assertEqual(client_for(None).get(f"{GUIDANCE}{self.mine['id']}/").status_code, 401)

    def test_r2_timeline_has_no_free_note_or_phone(self):
        # `mine` được tạo qua API với ghi chú chứa SĐT giả; dòng thời gian chỉ có nhãn việc, người làm, giờ.
        resp = self.get(self.owner, self.mine["id"])
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()["timeline"]), 1)
        text = resp.content.decode()
        self.assertNotIn(PHONE_SENTINEL, text)
        self.assertNotIn("Nguyễn Thử", text)

    def test_r2_scope_function_filters_by_assigned_courier(self):
        mine_ids = {r.pk for r in scope_returns_for(self.courier, ReturnToStock.objects.all())}
        self.assertEqual(mine_ids, {self.mine["id"]})
        for user in (self.owner, self.manager, self.warehouse_staff):
            self.assertEqual(scope_returns_for(user, ReturnToStock.objects.all()).count(), 2)
