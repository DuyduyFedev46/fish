"""
QA P8 Lô 7 — F12 / job khớp tiền tuyệt đối: job chạy 2 lần, hai giao dịch tranh 1 đơn, cờ bật/tắt,
không Chủ hoạt động nhưng khớp tuyệt đối vẫn ghi tiền. Chỉ dữ liệu giả.
"""
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiPolicyVersion
from apps.sales.models import PaymentTransaction, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments.auto_confirm import process_exact_payment_matches
from apps.delivery.tests.test_confirmation_escalation import ConfirmationL3BaseTestCase

CMD = "sales.paymenttransaction.resolve"


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, SEPAY_ENV="SANDBOX")
class QaF12Tests(ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        AiPolicyVersion.objects.create(
            version=1, global_mode="on",
            red_zone_open={"system.auto_confirm_exact_match": True}, created_by=self.chu,
        )
        self.order = order_services.create_order(
            customer_phone="0900000555", customer_name="Khách Giả Q", delivery_address="2 Đường Giả",
            phone="0900000555", lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )

    def _txn(self, code, amount=None, order=True):
        return PaymentTransaction.objects.create(
            bank_txn_id=code, amount=Decimal(amount if amount is not None else self.order.total_amount),
            match_status="UNMATCHED", resolution_status="OPEN", received_at=timezone.now(),
            raw_payload={"order_code": self.order.code} if order else {},
        )

    def test_qa_f12_khop_tuyet_doi_chay_2_lan_chi_ghi_tien_1_lan(self):
        self._txn("QA-EX-1")
        r1 = process_exact_payment_matches()
        r2 = process_exact_payment_matches()
        self.assertEqual((r1["confirmed"], r2["confirmed"], r2["escalated"]), (1, 0, 0))
        self.assertEqual(PaymentTransaction.objects.filter(sales_order=self.order).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="auto_confirm_exact_match").count(), 1)

    def test_qa_f12_hai_giao_dich_cung_don_giao_dich_sau_bi_chuyen_chu_khong_ghi_tien_lan_2(self):
        self._txn("QA-EX-A")
        self._txn("QA-EX-B")
        r = process_exact_payment_matches()
        self.assertEqual(r["confirmed"], 1)
        self.assertEqual(r["escalated"], 1)
        self.assertEqual(PaymentTransaction.objects.filter(sales_order=self.order).count(), 1)
        act = AiAction.objects.get(command=CMD)
        self.assertEqual(act.status, AiAction.Status.ESCALATED)
        self.assertNotIn("0900000555", str(act.downgrade_reason) + str(act.args))
        # chạy lại lần 2: không tạo thêm việc, không thêm nhật ký
        n = AuditLog.objects.filter(action="escalate_unmatched_payment").count()
        r2 = process_exact_payment_matches()
        self.assertEqual((r2["confirmed"], r2["escalated"]), (0, 0))
        self.assertEqual(AuditLog.objects.filter(action="escalate_unmatched_payment").count(), n)
        self.assertEqual(AiAction.objects.filter(command=CMD).count(), 1)

    def test_qa_f12_khong_co_chu_van_khop_tuyet_doi_ghi_tien_khong_can_chu(self):
        self.chu.is_active = False
        self.chu.save(update_fields=["is_active"])
        self._txn("QA-EX-NOCHU")
        r = process_exact_payment_matches()
        self.assertEqual(r["confirmed"], 1)
        self.assertEqual(AiAction.objects.filter(command=CMD).count(), 0)

    def test_qa_f12_khong_co_chu_ca_lech_khong_tao_viec_va_chay_2_lan_van_bo_qua(self):
        self.chu.is_active = False
        self.chu.save(update_fields=["is_active"])
        self._txn("QA-ORPH", order=False)
        for _ in range(2):
            r = process_exact_payment_matches()
            self.assertEqual((r["escalated"], r["skipped"]), (0, 1))
        self.assertEqual(AiAction.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(action="escalate_unmatched_payment").count(), 0)

    def test_qa_f12_chu_khoi_phuc_hoat_dong_job_sau_do_giao_viec_dung_chu(self):
        self.chu.is_active = False
        self.chu.save(update_fields=["is_active"])
        self._txn("QA-ORPH2", order=False)
        process_exact_payment_matches()
        self.chu.is_active = True
        self.chu.save(update_fields=["is_active"])
        r = process_exact_payment_matches()
        self.assertEqual(r["escalated"], 1)
        self.assertEqual(AiAction.objects.get(command=CMD).owner, self.chu)

    def test_qa_f12_chu_da_tu_xu_ly_viec_dong_job_khong_mo_lai(self):
        self._txn("QA-ORPH3", order=False)
        process_exact_payment_matches()
        AiAction.objects.filter(command=CMD).update(status=AiAction.Status.DONE)
        n = AuditLog.objects.filter(action="escalate_unmatched_payment").count()
        r = process_exact_payment_matches()
        self.assertEqual(r["escalated"], 0)
        self.assertEqual(AiAction.objects.get(command=CMD).status, AiAction.Status.DONE)
        self.assertEqual(AuditLog.objects.filter(action="escalate_unmatched_payment").count(), n)

    def test_qa_f12_co_tat_khong_dong_vao_giao_dich(self):
        self._txn("QA-FLAG")
        with override_settings(AI_ENABLED=False):
            self.assertEqual(process_exact_payment_matches()["reason"], "AI_DISABLED")
        with override_settings(AI_PRODUCTION_READY=False):
            self.assertEqual(process_exact_payment_matches()["reason"], "PRODUCTION_NOT_READY")
        AiPolicyVersion.objects.create(version=2, global_mode="on", red_zone_open={}, created_by=self.chu)
        self.assertEqual(process_exact_payment_matches()["reason"], "SWITCH_CLOSED")
        self.assertEqual(PaymentTransaction.objects.get(bank_txn_id="QA-FLAG").sales_order_id, None)
        self.assertEqual(AiAction.objects.count(), 0)

    def test_qa_f12_don_da_huy_chuyen_chu_ly_do_khong_pii_khong_gia_von(self):
        SalesOrder.objects.filter(pk=self.order.pk).update(status=SalesOrder.Status.CANCELLED)
        self._txn("QA-CANC")
        r = process_exact_payment_matches()
        self.assertEqual((r["confirmed"], r["escalated"]), (0, 1))
        act = AiAction.objects.get(command=CMD)
        blob = str(act.downgrade_reason) + str(act.args) + " ".join(
            f"{a.note}|{a.changes}" for a in AuditLog.objects.filter(action="escalate_unmatched_payment"))
        for bad in ("Khách Giả Q", "0900000555", "Đường Giả", "purchase_rate", "unit_cost", "landed"):
            self.assertNotIn(bad, blob)
