"""
P8 Lô 3 — SR-11: job khớp tiền tuyệt đối (DW-26) chạy nhiều lần không phình Nhật ký,
không mở lại việc Chủ đã đóng (F06). Chuyển từ test tái hiện R4 (repro/review_repro_tests.py). Dữ liệu giả.

- SR-11-AC1: 1 giao dịch UNMATCHED OPEN, chạy 2 lần -> đúng 1 dòng AuditLog escalate_unmatched_payment.
- SR-11-AC2: Chủ đặt việc REJECTED/DONE/CANCELLED/EXPIRED/UNDONE/FAILED, chạy lại -> giữ nguyên, không thêm audit.
- SR-11-AC3: lý do chuyển đổi (số tiền giao dịch cập nhật khác) -> thêm 1 dòng audit, cập nhật downgrade_reason.
- SR-11-AC4: chỉ quét match_status=UNMATCHED; ORPHAN/OVERPAID/UNDERPAID không tạo việc chuyển Chủ.
- Job Hệ thống, không có endpoint mới (ma trận Group: không áp dụng).
"""
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiPolicyVersion
from apps.delivery.tests.test_cskh_l3 import ConfirmationL3BaseTestCase
from apps.sales.models import PaymentTransaction
from apps.sales.orders import services as order_services
from apps.sales.payments.auto_confirm import process_exact_payment_matches

CMD = "sales.paymenttransaction.resolve"
ESCALATE_ACTION = "escalate_unmatched_payment"


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, SEPAY_ENV="SANDBOX")
class SR11AutoConfirmIdempotentTests(ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        AiPolicyVersion.objects.create(
            version=1, global_mode="on",
            red_zone_open={"system.auto_confirm_exact_match": True}, created_by=self.chu,
        )

    # --- helpers -------------------------------------------------------------
    def _txn(self, code="TXN-SR11", amount="1", match_status="UNMATCHED", raw=None):
        return PaymentTransaction.objects.create(
            bank_txn_id=code, amount=Decimal(amount), match_status=match_status,
            resolution_status="OPEN", received_at=timezone.now(), raw_payload=raw or {},
        )

    def _audits(self):
        return AuditLog.objects.filter(action=ESCALATE_ACTION).count()

    def _actions(self):
        return AiAction.objects.filter(command=CMD)

    # --- AC1 (R4) ------------------------------------------------------------
    def test_sr11_ac1_r4_chay_2_lan_chi_1_dong_audit(self):
        self._txn()
        process_exact_payment_matches()
        process_exact_payment_matches()
        self.assertEqual(self._audits(), 1)
        self.assertEqual(self._actions().count(), 1)
        self.assertEqual(self._actions().get().status, AiAction.Status.ESCALATED)

    def test_sr11_ac1_chay_nhieu_lan_thong_ke_van_dung(self):
        self._txn()
        for _ in range(3):
            res = process_exact_payment_matches()
            self.assertEqual(res["confirmed"], 0)
        self.assertEqual(self._audits(), 1)

    # --- AC2 -----------------------------------------------------------------
    def test_sr11_ac2_viec_da_dong_khong_bi_mo_lai_va_khong_them_audit(self):
        terminal = (
            AiAction.Status.REJECTED, AiAction.Status.DONE, AiAction.Status.CANCELLED,
            AiAction.Status.EXPIRED, AiAction.Status.UNDONE, AiAction.Status.FAILED,
        )
        for i, final in enumerate(terminal):
            with self.subTest(status=final):
                self._txn(code=f"TXN-SR11-AC2-{i}")
        process_exact_payment_matches()
        self.assertEqual(self._audits(), len(terminal))
        acts = list(self._actions().order_by("target_id"))
        self.assertEqual(len(acts), len(terminal))
        for act, final in zip(acts, terminal):
            act.status = final  # Chủ / hệ thống đã kết thúc việc (RA-05: đặt trực tiếp)
            act.save(update_fields=["status"])
        before = self._audits()

        process_exact_payment_matches()
        process_exact_payment_matches()

        self.assertEqual(self._audits(), before)
        self.assertEqual(self._actions().count(), len(terminal))
        for act, final in zip(acts, terminal):
            act.refresh_from_db()
            self.assertEqual(act.status, final, f"việc {final} bị mở lại")

    def test_sr11_ac2_r4_rejected_roi_chay_lai(self):
        self._txn()
        process_exact_payment_matches()
        act = self._actions().get()
        act.status = AiAction.Status.REJECTED
        act.save(update_fields=["status"])
        process_exact_payment_matches()
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.REJECTED)
        self.assertEqual(self._audits(), 1)

    # --- AC3 -----------------------------------------------------------------
    def test_sr11_ac3_ly_do_doi_thi_ghi_them_audit_va_cap_nhat_downgrade_reason(self):
        order = order_services.create_order(
            customer_phone="0900000111", customer_name="Khách Giả A", delivery_address="1 Đường Giả",
            phone="0900000111", lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )
        txn = self._txn(code="TXN-SR11-AC3", amount="1000", raw={"order_code": order.code})
        process_exact_payment_matches()
        act = self._actions().get()
        first_text = act.downgrade_reason["text"]
        self.assertEqual(self._audits(), 1)
        self.assertIn("1.000 ₫", first_text)

        process_exact_payment_matches()  # lý do không đổi -> không thêm
        self.assertEqual(self._audits(), 1)

        txn.amount = Decimal("2000")  # số tiền giao dịch cập nhật khác -> lý do đổi
        txn.save(update_fields=["amount"])
        process_exact_payment_matches()
        act.refresh_from_db()
        self.assertEqual(self._audits(), 2)
        self.assertNotEqual(act.downgrade_reason["text"], first_text)
        self.assertIn("2.000 ₫", act.downgrade_reason["text"])
        self.assertEqual(act.status, AiAction.Status.ESCALATED)
        self.assertEqual(self._actions().count(), 1)

        process_exact_payment_matches()  # lý do mới ổn định
        self.assertEqual(self._audits(), 2)

    def test_sr11_ac3_ly_do_doi_nhung_viec_da_dong_thi_khong_mo_lai(self):
        order = order_services.create_order(
            customer_phone="0900000111", customer_name="Khách Giả A", delivery_address="1 Đường Giả",
            phone="0900000111", lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )
        txn = self._txn(code="TXN-SR11-AC3B", amount="1000", raw={"order_code": order.code})
        process_exact_payment_matches()
        act = self._actions().get()
        act.status = AiAction.Status.REJECTED
        act.save(update_fields=["status"])
        txn.amount = Decimal("2000")
        txn.save(update_fields=["amount"])
        process_exact_payment_matches()
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.REJECTED)
        self.assertEqual(self._audits(), 1)

    # --- AC4 -----------------------------------------------------------------
    def test_sr11_ac4_chi_quet_unmatched(self):
        for i, ms in enumerate(("ORPHAN", "OVERPAID", "UNDERPAID")):
            self._txn(code=f"TXN-SR11-AC4-{i}", match_status=ms)
        process_exact_payment_matches()
        process_exact_payment_matches()
        self.assertEqual(self._actions().count(), 0)
        self.assertEqual(self._audits(), 0)

    def test_sr11_ac4_unmatched_van_duoc_chuyen_chu_khi_lan_voi_loai_khac(self):
        self._txn(code="TXN-SR11-AC4-U", match_status="UNMATCHED")
        self._txn(code="TXN-SR11-AC4-O", match_status="ORPHAN")
        process_exact_payment_matches()
        acts = self._actions()
        self.assertEqual(acts.count(), 1)
        self.assertEqual(self._audits(), 1)
        txn_u = PaymentTransaction.objects.get(bank_txn_id="TXN-SR11-AC4-U")
        self.assertEqual(acts.get().target_id, str(txn_u.pk))

    def test_sr11_khong_ghi_pii_vao_audit_va_action(self):
        order = order_services.create_order(
            customer_phone="0900000111", customer_name="Khách Giả A", delivery_address="1 Đường Giả",
            phone="0900000111", lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )
        self._txn(code="TXN-SR11-PII", amount="1000", raw={"order_code": order.code})
        process_exact_payment_matches()
        blob = " ".join(
            f"{a.note} {a.changes}" for a in AuditLog.objects.filter(action=ESCALATE_ACTION)
        ) + str(self._actions().get().downgrade_reason) + str(self._actions().get().args)
        for sentinel in ("0900000111", "Khách Giả A", "1 Đường Giả"):
            self.assertNotIn(sentinel, blob)
