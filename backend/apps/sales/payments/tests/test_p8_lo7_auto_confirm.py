"""
P8 Lô 7 — SR-22 / F12 + nợ Lô 3 L1, L2 cho job khớp tiền tuyệt đối (DW-26). Job Hệ thống, không có endpoint.
Dữ liệu giả ("Khách Giả B", 0900000999).
"""
import logging
from decimal import Decimal
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiPolicyVersion
from apps.common.exceptions import BusinessError
from apps.delivery.tests.test_cskh_l3 import ConfirmationL3BaseTestCase
from apps.sales.models import PaymentTransaction
from apps.sales.orders import services as order_services
from apps.sales.payments import auto_confirm
from apps.sales.payments.auto_confirm import process_exact_payment_matches
from apps.accounts import roles

CMD = "sales.paymenttransaction.resolve"
SENTINEL = "Khách Giả B 0900000999"


@override_settings(AI_ENABLED=True, AI_PRODUCTION_READY=True, SEPAY_ENV="SANDBOX")
class P8Lo7AutoConfirmTests(ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        AiPolicyVersion.objects.create(
            version=1, global_mode="on",
            red_zone_open={"system.auto_confirm_exact_match": True}, created_by=self.chu,
        )

    def _txn(self, code="TXN-L7", amount="1", raw=None):
        return PaymentTransaction.objects.create(
            bank_txn_id=code, amount=Decimal(amount), match_status="UNMATCHED",
            resolution_status="OPEN", received_at=timezone.now(), raw_payload=raw or {},
        )

    def _order(self):
        return order_services.create_order(
            customer_phone="0900000999", customer_name="Khách Giả B", delivery_address="1 Đường Giả",
            phone="0900000999", lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )

    # --- F12a: không có Chủ hoạt động ------------------------------------------
    def test_f12_khong_co_chu_hoat_dong_bo_qua_va_log_canh_bao_khong_giao_cho_user_khac(self):
        self.chu.is_active = False
        self.chu.save(update_fields=["is_active"])
        self._txn()
        with self.assertLogs("apps.sales.payments.auto_confirm", level=logging.WARNING) as cm:
            res = process_exact_payment_matches()
        self.assertTrue(any(roles.OWNER in line for line in cm.output))
        self.assertEqual(AiAction.objects.filter(command=CMD).count(), 0)
        self.assertEqual(AuditLog.objects.filter(action="escalate_unmatched_payment").count(), 0)
        self.assertEqual(res["escalated"], 0)
        self.assertEqual(res["skipped"], 1)

    def test_f12_co_chu_hoat_dong_viec_giao_dung_chu(self):
        self._txn()
        process_exact_payment_matches()
        act = AiAction.objects.get(command=CMD)
        self.assertEqual(act.owner, self.chu)
        self.assertEqual(act.assignee_group, roles.OWNER)

    # --- F12b: downgrade_reason chỉ ghi mã lỗi -----------------------------------
    def _exact_match_order_txn(self):
        order = self._order()
        txn = self._txn(code="TXN-L7-EXACT", amount=str(order.total_amount), raw={"order_code": order.code})
        return order, txn

    def test_f12_loi_nghiep_vu_chi_ghi_ma_khong_ghi_thong_diep(self):
        self._exact_match_order_txn()
        err = BusinessError(f"Chi tiết có {SENTINEL}", code="BR-TT-99")
        with mock.patch.object(auto_confirm.payment_services, "resolve_payment", side_effect=err), \
             self.assertLogs("apps.sales.payments.auto_confirm", level=logging.WARNING) as cm:
            res = process_exact_payment_matches()
        self.assertEqual(res["escalated"], 1)
        act = AiAction.objects.get(command=CMD)
        text = act.downgrade_reason["text"]
        self.assertIn("BR-TT-99", text)
        self.assertNotIn(SENTINEL, text)
        self.assertNotIn("0900000999", str(act.args))
        self.assertNotIn(SENTINEL, "\n".join(cm.output))
        for row in AuditLog.objects.filter(action="escalate_unmatched_payment"):
            self.assertNotIn(SENTINEL, f"{row.note} {row.changes}")

    def test_f12_loi_khac_chi_ghi_ten_loai_khong_ghi_thong_diep(self):
        self._exact_match_order_txn()
        with mock.patch.object(auto_confirm.payment_services, "resolve_payment",
                               side_effect=ValueError(f"lỗi {SENTINEL}")):
            process_exact_payment_matches()
        text = AiAction.objects.get(command=CMD).downgrade_reason["text"]
        self.assertIn("ValueError", text)
        self.assertNotIn(SENTINEL, text)

    # --- L2: đếm escalated đúng, cập nhật args.reason ----------------------------
    def test_l2_no_op_khong_tinh_vao_escalated_ma_tinh_vao_skipped(self):
        self._txn()
        first = process_exact_payment_matches()
        second = process_exact_payment_matches()
        self.assertEqual((first["escalated"], first["skipped"]), (1, 0))
        self.assertEqual((second["escalated"], second["skipped"]), (0, 1))

    def test_l2_ly_do_doi_cap_nhat_ca_args_reason(self):
        order = self._order()
        txn = self._txn(code="TXN-L7-REASON", amount="1000", raw={"order_code": order.code})
        process_exact_payment_matches()
        act = AiAction.objects.get(command=CMD)
        old = act.args["reason"]
        txn.amount = Decimal("2000")
        txn.save(update_fields=["amount"])
        res = process_exact_payment_matches()
        act.refresh_from_db()
        self.assertEqual(res["escalated"], 1)
        self.assertNotEqual(act.args["reason"], old)
        self.assertEqual(act.args["reason"], act.downgrade_reason["text"])
        self.assertEqual(act.args["payment_id"], txn.id)

    # --- L1: chỉ còn ATTACH_TO_ORDER ---------------------------------------------
    def test_l1_khop_tuyet_doi_dung_attach_to_order(self):
        order, txn = self._exact_match_order_txn()
        with mock.patch.object(auto_confirm.payment_services, "resolve_payment",
                               wraps=auto_confirm.payment_services.resolve_payment) as spy:
            res = process_exact_payment_matches()
        self.assertEqual(res["confirmed"], 1)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(spy.call_args.kwargs["action"], auto_confirm.payment_services.ResolveAction.ATTACH_TO_ORDER)
        self.assertEqual(spy.call_args.kwargs["order_id"], order.id)
        txn.refresh_from_db()
        self.assertEqual(txn.sales_order_id, order.id)
