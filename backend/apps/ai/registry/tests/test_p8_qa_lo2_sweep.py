"""
QA P8 Lô 2 — bù test quét PII (techlead L2): cột nv_giao / cskh phải quét trên dữ liệu CÓ TRONG PHẠM VI,
gồm phiếu giao gán cho nv_giao có tên/SĐT người nhận, cskh có việc gọi trong phạm vi + cuộc gọi, một phiếu hoàn,
khách có địa chỉ mặc định. Toàn dữ liệu giả (bất biến 9).

Chống xanh giả: đếm số response 200 THEO NHÓM và theo lệnh chi tiết; nếu nhóm nào không có 200 nào thì fail.
"""
import json
import re

from django.utils import timezone

from apps.ai.registry.discovery import get_registry
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote
from apps.sales.models import Customer, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.scope import scope_orders_for
from apps.sales.payments import services as payment_services
from apps.sales.refunds import services as refund_services

from .test_p8_pii_sweep import GROUPS, PII_KEYS, PII_NAME, PII_PAYER, PII_PHONE, PII_ADDR, PiiSweepBase, _find_keys
from apps.accounts import roles

RECIP_NAME = "Người Nhận Giả Zeta"
RECIP_PHONE = "0900000777"
NOTE_PII = "Khách Giả Bí Mật dặn giao chiều"
DEFAULT_ADDR = "Số 9 Hẻm Giả Mặc Định"
PII_STRINGS_RICH = (PII_NAME, PII_PHONE, PII_ADDR, PII_PAYER, RECIP_NAME, RECIP_PHONE, NOTE_PII, DEFAULT_ADDR,
                    "Khách Giả B", "0900000456")

# Khoá "trông giống PII" mà KHÔNG nằm trong tập lọc — báo cáo để rà (không tự fail vì có khoá vô hại).
HEURISTIC = re.compile(r"(phone|address|recipient|payer|customer|contact|holder|receiver|sender|email)", re.I)


class RichScopeSweep(PiiSweepBase):
    def setUp(self):
        super().setUp()
        self.note = DeliveryNote.objects.get(sales_invoice__sales_order=self.order)
        self.note.assigned_to = self.users[roles.DELIVERY_STAFF]
        self.note.recipient_name = RECIP_NAME
        self.note.recipient_phone = RECIP_PHONE
        self.note.note = NOTE_PII
        self.note.save()
        Customer.objects.filter(pk=self.order.customer_id).update(default_address=DEFAULT_ADDR, note=NOTE_PII)
        # cskh: phiếu đang CONFIRMING với việc gọi mở -> trong phạm vi; thêm 1 cuộc gọi của chính cskh
        task = getattr(self.note, "confirmation", None)
        self.assertIsNotNone(task, "fixture: phiếu phải có ConfirmationTask")
        CustomerCall.objects.create(
            note=self.note, result=CustomerCall.Result.CALLBACK, note_text=NOTE_PII,
            created_by=self.users[roles.CUSTOMER_SERVICE], callback_at=timezone.now(),
        )
        # Phiếu hoàn (lý do trung tính; chữ tự do do nhân viên gõ là ghi chú riêng của báo cáo QA, mục G1)
        self.invoice = self.order.invoice
        self.refund = refund_services.create_refund(
            invoice=self.invoice, amount=self.invoice.amount / 2, is_partial=True,
            reason="Khách đổi ý, hoàn một phần", actor=self.users[roles.OWNER],
        )
        # Đơn thứ 2 đã thanh toán để có thêm phiếu/giao dịch
        payment_services.confirm_payment(
            order=self.order2, bank_txn_id="FTGIA0002", amount=self.order2.total_amount,
            received_at=timezone.now(), raw_payload={"content": f"{PII_PAYER} 2", "counter_account_name": PII_PAYER},
        )

    def _cands(self):
        c = set(self._target_candidates())
        c |= {str(self.note.pk), self.note.code, str(self.refund.pk), str(self.order2.pk), self.order2.code,
              str(self.order.customer_id)}
        inv2 = getattr(self.order2, "invoice", None)
        if inv2 is not None:
            c |= {str(inv2.pk), inv2.code}
        c |= {str(t) for t in range(1, 6)}
        return sorted(c)

    def test_fixture_that_su_nam_trong_pham_vi(self):
        """Điều kiện tiên quyết: dữ liệu có mặt trong phạm vi của nv_giao và cskh (không phải cột rỗng)."""
        qs = SalesOrder.objects.all()
        self.assertIn(self.order.pk, set(scope_orders_for(self.users[roles.DELIVERY_STAFF], qs).values_list("pk", flat=True)))
        self.assertIn(self.order.pk, set(scope_orders_for(self.users[roles.CUSTOMER_SERVICE], qs).values_list("pk", flat=True)))
        self.assertNotIn(self.order2.pk, set(scope_orders_for(self.users[roles.DELIVERY_STAFF], qs).values_list("pk", flat=True)))
        self.assertEqual(self.note.confirmation.state, ConfirmationTask.State.PENDING)

    def test_quet_5_group_tren_du_lieu_trong_pham_vi(self):
        specs = [s for s in get_registry().get_specs() if s.kind == "read"]
        ok_by_group = {g: 0 for g in GROUPS}
        ok_detail_by_group = {g: 0 for g in GROUPS}
        ok_cmds_by_group = {g: set() for g in GROUPS}
        violations = []
        heuristic_keys = {}
        for spec in specs:
            for group in GROUPS:
                bodies = [{"args": {}, "target_id": t} for t in self._cands()] if spec.detail else [{"args": {}}]
                for body in bodies:
                    res = self._call(group, spec.id, body)
                    self.assertLess(res.status_code, 500, f"{spec.id} {group} {body} -> {res.status_code}")
                    if res.status_code != 200:
                        continue
                    ok_by_group[group] += 1
                    ok_cmds_by_group[group].add(spec.id)
                    if spec.detail:
                        ok_detail_by_group[group] += 1
                    raw = res.content.decode()
                    for s in PII_STRINGS_RICH:
                        if s in raw:
                            violations.append((spec.id, group, s))
                    data = res.json()
                    for key in _find_keys(data, PII_KEYS):
                        violations.append((spec.id, group, f"key:{key}"))
                    for key in _find_keys(data, {k for k in _all_keys(data) if HEURISTIC.search(k)}):
                        heuristic_keys.setdefault(key, set()).add(spec.id)
        if violations:
            self.fail(f"Lệnh AI rò PII: {sorted(set(violations))}")
        for g in GROUPS:
            self.assertGreater(ok_by_group[g], 0, f"nhóm {g} không có response 200 nào (xanh giả)")
        # nv_giao/cskh phải chạm được dữ liệu chi tiết có PII trong phạm vi
        for g in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            self.assertIn("sales.salesorder.retrieve", ok_cmds_by_group[g], f"{g} không retrieve được đơn trong phạm vi")
        for g in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF):
            self.assertIn("delivery.deliverynote.retrieve", ok_cmds_by_group[g], f"{g} không retrieve được phiếu giao")
        for g in (roles.OWNER, roles.MANAGER):
            self.assertIn("sales.refund.retrieve", ok_cmds_by_group[g], f"{g} không retrieve được phiếu hoàn")
        print("QA-LO2 200 theo nhóm:", ok_by_group, "chi tiết:", ok_detail_by_group)
        print("QA-LO2 khoá giống-PII ngoài tập lọc (rà tay):", {k: sorted(v) for k, v in heuristic_keys.items()})

    def test_orders_retrieve_nv_giao_chi_thay_don_cua_minh(self):
        """SR-05-AC3 + SR-06: nv_giao retrieve đơn của phiếu mình = 200; đơn khác = 404 (qua AI), body không có PII."""
        ok = self._call(roles.DELIVERY_STAFF, "sales.salesorder.retrieve", {"args": {}, "target_id": str(self.order.pk)})
        self.assertEqual(ok.status_code, 200, ok.content[:300])
        other = self._call(roles.DELIVERY_STAFF, "sales.salesorder.retrieve", {"args": {}, "target_id": str(self.order2.pk)})
        self.assertEqual(other.status_code, 404, other.content[:300])
        for res in (ok, other):
            raw = res.content.decode()
            for s in PII_STRINGS_RICH:
                self.assertNotIn(s, raw)

    def test_ai_action_va_audit_khong_chua_pii_sau_quet(self):
        from apps.accounts.models import AuditLog
        from apps.ai.models import AiAction
        for spec in get_registry().get_specs():
            if spec.kind == "read" and spec.detail:
                for g in (roles.OWNER, roles.DELIVERY_STAFF):
                    self._call(g, spec.id, {"args": {}, "target_id": str(self.order.pk)})
        blob = json.dumps(list(AiAction.objects.values("args", "result_ref", "downgrade_reason")), ensure_ascii=False, default=str)
        blob += json.dumps(list(AuditLog.objects.values("note", "changes")), ensure_ascii=False, default=str)
        for s in (PII_NAME, PII_PHONE, PII_ADDR, RECIP_NAME, RECIP_PHONE, DEFAULT_ADDR):
            self.assertNotIn(s, blob)


def _all_keys(data):
    keys = set()
    if isinstance(data, dict):
        for k, v in data.items():
            keys.add(str(k))
            keys |= _all_keys(v)
    elif isinstance(data, list):
        for v in data:
            keys |= _all_keys(v)
    return keys
