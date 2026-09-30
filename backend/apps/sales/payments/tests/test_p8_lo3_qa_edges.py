"""
QA P8 Lô 3 — ca biên/ngoại lệ bổ sung cho SR-11 (job khớp tiền tuyệt đối DW-26 idempotent).
Không sửa code sản phẩm. Dữ liệu giả.

Phủ: mọi đường chuyển Chủ (nghi trùng, sai môi trường, không có đơn, >1 đơn, đơn đã bán/không còn BOOKED,
thiếu/thừa tiền) chạy 2 lần chỉ 1 dòng Nhật ký; đường thuận khớp tuyệt đối chạy 2 lần không ghi tiền/hoá đơn
đôi; lệnh quản trị chạy 2 lần; giao dịch RESOLVED không bị quét; PII trong raw_payload không lọt vào
Nhật ký/AiAction/log.
"""
import logging
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiPolicyVersion
from apps.delivery.tests.test_cskh_l3 import CskhL3BaseTestCase
from apps.sales.models import PaymentTransaction, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments.auto_confirm import process_exact_payment_matches

CMD = "sales.paymenttransaction.resolve"
ESC = "escalate_unmatched_payment"
PII = ("0900000777", "Nguyễn Thử Bê", "Số 9 Đường Thử Nghiệm")


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, SEPAY_ENV="SANDBOX")
class QaSR11Edges(CskhL3BaseTestCase):
    def setUp(self):
        super().setUp()
        AiPolicyVersion.objects.create(
            version=1, global_mode="on",
            red_zone_open={"system.auto_confirm_exact_match": True}, created_by=self.chu,
        )
        self._n = 0

    # --- helpers ---------------------------------------------------------------
    def _order(self, qty="2"):
        return order_services.create_order(
            customer_phone="0900000777", customer_name="Nguyễn Thử Bê", delivery_address="Số 9 Đường Thử Nghiệm",
            phone="0900000777", lines=[{"item_code": self.item.code, "qty": Decimal(qty)}],
        )

    def _txn(self, amount="1", raw=None, env="SANDBOX", dup="", order=None, match="UNMATCHED"):
        self._n += 1
        return PaymentTransaction.objects.create(
            bank_txn_id=f"TXN-QA11-{self._n}", amount=Decimal(amount), match_status=match,
            resolution_status="OPEN", received_at=timezone.now(), raw_payload=raw or {},
            environment=env, duplicate_warning=dup, sales_order=order,
        )

    def _audits(self, action=ESC):
        return AuditLog.objects.filter(action=action).count()

    def _twice(self):
        r1 = process_exact_payment_matches()
        a1 = self._audits()
        r2 = process_exact_payment_matches()
        a2 = self._audits()
        return r1, r2, a1, a2

    # --- mỗi lý do chuyển Chủ: chạy 2 lần => 1 dòng Nhật ký, 1 việc ------------------
    def _assert_stable_single_escalation(self, txn, contains):
        r1, r2, a1, a2 = self._twice()
        self.assertEqual((a1, a2), (1, 1), "Nhật ký phình khi chạy lần 2")
        acts = AiAction.objects.filter(command=CMD, target_id=str(txn.pk))
        self.assertEqual(acts.count(), 1)
        act = acts.get()
        self.assertEqual(act.status, AiAction.Status.ESCALATED)
        self.assertIn(contains, act.downgrade_reason["text"])
        self.assertEqual(r1["confirmed"], 0)
        self.assertEqual(r2["confirmed"], 0)

    def test_qa_ly_do_nghi_trung(self):
        t = self._txn(dup="Trùng với GD khác")
        self._assert_stable_single_escalation(t, "nghi trùng")

    def test_qa_ly_do_sai_moi_truong(self):
        t = self._txn(env="PRODUCTION")
        self._assert_stable_single_escalation(t, "Sai môi trường")

    def test_qa_ly_do_khong_co_don(self):
        t = self._txn()
        self._assert_stable_single_escalation(t, "Không tìm thấy đơn")

    def test_qa_ly_do_ma_don_khong_ton_tai(self):
        t = self._txn(raw={"order_code": "SO-000000-KHONGCO"})
        self._assert_stable_single_escalation(t, "Không tìm thấy đơn")

    def test_qa_ly_do_don_da_ban_khong_con_booked(self):
        """Dữ liệu đã từng bán: đơn đã trả tiền (PROCESSING) -> không tự xác nhận lần 2."""
        o = self._order()
        o.status = SalesOrder.Status.PROCESSING
        o.save(update_fields=["status"])
        t = self._txn(amount=str(o.total_amount), raw={"order_code": o.code})
        self._assert_stable_single_escalation(t, "không thể tự xác nhận")
        self.assertEqual(SalesInvoice.objects.filter(sales_order=o).count(), 0)

    def test_qa_ly_do_don_da_huy(self):
        o = self._order()
        o.status = SalesOrder.Status.CANCELLED
        o.save(update_fields=["status"])
        t = self._txn(amount=str(o.total_amount), raw={"order_code": o.code})
        self._assert_stable_single_escalation(t, "không thể tự xác nhận")

    def test_qa_ly_do_thieu_tien_va_thua_tien(self):
        o1, o2 = self._order(), self._order()
        t1 = self._txn(amount=str(o1.total_amount - Decimal("1")), raw={"order_code": o1.code})
        t2 = self._txn(amount=str(o2.total_amount + Decimal("1")), raw={"order_code": o2.code})
        process_exact_payment_matches()
        process_exact_payment_matches()
        self.assertEqual(self._audits(), 2)
        self.assertIn("Thiếu tiền", AiAction.objects.get(command=CMD, target_id=str(t1.pk)).downgrade_reason["text"])
        self.assertIn("Thừa tiền", AiAction.objects.get(command=CMD, target_id=str(t2.pk)).downgrade_reason["text"])
        for o in (o1, o2):
            o.refresh_from_db()
            self.assertEqual(o.status, SalesOrder.Status.BOOKED)  # không tự đổi trạng thái

    # --- đổi trạng thái đơn giữa 2 lần chạy => lý do đổi => +1 dòng, sau đó ổn định ---
    def test_qa_don_doi_trang_thai_giua_2_lan_chay_them_dung_1_dong(self):
        o = self._order()
        t = self._txn(amount=str(o.total_amount + Decimal("5")), raw={"order_code": o.code})
        process_exact_payment_matches()
        self.assertEqual(self._audits(), 1)
        o.status = SalesOrder.Status.CANCELLED
        o.save(update_fields=["status"])
        process_exact_payment_matches()
        process_exact_payment_matches()
        self.assertEqual(self._audits(), 2)
        act = AiAction.objects.get(command=CMD, target_id=str(t.pk))
        self.assertIn("không thể tự xác nhận", act.downgrade_reason["text"])

    # --- đường thuận: khớp tuyệt đối chạy 2 lần --------------------------------------
    def test_qa_khop_tuyet_doi_chay_2_lan_chi_ghi_tien_1_lan(self):
        o = self._order()
        t = self._txn(amount=str(o.total_amount), raw={"order_code": o.code})
        r1 = process_exact_payment_matches()
        r2 = process_exact_payment_matches()
        self.assertEqual((r1["confirmed"], r2["confirmed"]), (1, 0))
        self.assertEqual(self._audits("auto_confirm_exact_match"), 1)
        self.assertEqual(self._audits(ESC), 0)
        self.assertEqual(SalesInvoice.objects.filter(sales_order=o).count(), 1)
        t.refresh_from_db(); o.refresh_from_db()
        self.assertEqual(t.resolution_status, "RESOLVED")
        self.assertEqual(o.status, SalesOrder.Status.PROCESSING)
        self.assertFalse(AiAction.objects.filter(command=CMD).exists())

    def test_qa_hai_giao_dich_cung_don_cai_thu_hai_chuyen_chu_dung_1_lan(self):
        o = self._order()
        t1 = self._txn(amount=str(o.total_amount), raw={"order_code": o.code})
        t2 = self._txn(amount=str(o.total_amount), raw={"order_code": o.code})
        for _ in range(3):
            process_exact_payment_matches()
        self.assertEqual(SalesInvoice.objects.filter(sales_order=o).count(), 1)
        self.assertEqual(self._audits("auto_confirm_exact_match"), 1)
        self.assertEqual(self._audits(ESC), 1)  # giao dịch thứ hai vì đơn không còn BOOKED
        t1.refresh_from_db(); t2.refresh_from_db()
        self.assertEqual({t1.resolution_status, t2.resolution_status}, {"RESOLVED", "OPEN"})

    def test_qa_giao_dich_da_resolved_khong_bi_quet(self):
        o = self._order()
        t = self._txn(amount=str(o.total_amount + Decimal("3")), raw={"order_code": o.code})
        t.resolution_status = "RESOLVED"
        t.save(update_fields=["resolution_status"])
        process_exact_payment_matches()
        self.assertEqual(self._audits(), 0)
        self.assertFalse(AiAction.objects.filter(command=CMD).exists())

    # --- công tắc/cờ bật tắt ---------------------------------------------------------------
    def test_qa_cong_tac_tat_khong_ghi_gi(self):
        self._txn()
        AiPolicyVersion.objects.create(version=2, global_mode="on", red_zone_open={}, created_by=self.chu)
        r = process_exact_payment_matches()
        self.assertEqual(r["reason"], "SWITCH_CLOSED")
        self.assertEqual(self._audits(), 0)

    @override_settings(AI_ENABLED=False)
    def test_qa_ai_tat_khong_ghi_gi(self):
        self._txn()
        self.assertEqual(process_exact_payment_matches()["reason"], "AI_DISABLED")
        self.assertEqual(self._audits(), 0)

    @override_settings(AI_PRODUCTION_READY=False)
    def test_qa_chua_san_sang_production_khong_ghi_gi(self):
        self._txn()
        self.assertEqual(process_exact_payment_matches()["reason"], "PRODUCTION_NOT_READY")
        self.assertEqual(self._audits(), 0)

    # --- lệnh quản trị chạy 2 lần --------------------------------------------------------
    def test_qa_management_command_chay_2_lan(self):
        self._txn()
        for _ in range(2):
            out = StringIO()
            call_command("auto_confirm_exact_payments", stdout=out)
            self.assertIn("Finished", out.getvalue())
        self.assertEqual(self._audits(), 1)
        self.assertEqual(AiAction.objects.filter(command=CMD).count(), 1)

    # --- rò dữ liệu cá nhân / giá vốn -----------------------------------------------------
    def test_qa_khong_ro_pii_hay_gia_von_trong_nhat_ky_action_va_log(self):
        o = self._order()
        raw = {
            "order_code": o.code, "payer_name": PII[1], "phone": PII[0], "address": PII[2],
            "description": f"{PII[1]} {PII[0]} chuyen khoan {o.code}", "content": f"{PII[1]} {PII[0]}",
        }
        self._txn(amount=str(o.total_amount + Decimal("7")), raw=raw)
        self._txn(amount="1", raw={"description": f"{PII[1]} {PII[0]} {PII[2]}", "content": PII[0]})
        h = _ListHandler()
        root = logging.getLogger()
        old = root.level
        root.addHandler(h)
        root.setLevel(logging.DEBUG)
        try:
            process_exact_payment_matches()
            process_exact_payment_matches()
        finally:
            root.removeHandler(h)
            root.setLevel(old)
        blob = "\n".join(h.lines)
        blob += " ".join(f"{a.note} {a.changes}" for a in AuditLog.objects.all())
        for a in AiAction.objects.filter(command=CMD):
            blob += f" {a.downgrade_reason} {a.args}"
        for s in PII:
            self.assertNotIn(s, blob)
        for k in ("unit_cost", "landed_unit_cost", "purchase_rate", "loss_amount", "gross_profit"):
            self.assertNotIn(k, blob)
        self.assertTrue(h.lines, "job phải có log mã GD/đơn")

    def test_qa_audit_khong_xoa_va_khong_sua_khi_chay_lai(self):
        self._txn()
        process_exact_payment_matches()
        first = AuditLog.objects.filter(action=ESC).get()
        snapshot = (first.pk, first.note, first.created_at)
        process_exact_payment_matches()
        first.refresh_from_db()
        self.assertEqual((first.pk, first.note, first.created_at), snapshot)
