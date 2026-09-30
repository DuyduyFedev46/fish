"""
Test cho DW-26: Xác nhận thanh toán tay cho ca khớp tuyệt đối bằng job Hệ thống (DW-26-AC1..AC6, V-DW1, BR-TT-03, BR-TT-14, BR-TT-15).
"""
import datetime
import logging
from decimal import Decimal
from django.contrib.auth.models import User, Group, Permission
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.models import AiAction, AiPolicyVersion
from apps.catalog.models.items import Item, ItemGroup
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models.suppliers import Supplier
from apps.sales.models import Customer, PaymentTransaction, SalesInvoice, SalesOrder, SalesOrderLine, SalesOrderLineBatch
from apps.sales.payments.auto_confirm import process_exact_payment_matches


@override_settings(
    AI_ENABLED=True,
    AI_PRODUCTION_READY=True,
    SEPAY_ENV="SANDBOX",
    TESTING=True,
)
class AutoConfirmExactMatchTests(TestCase):
    def setUp(self):
        # 1. Tạo Group
        self.chu_group, _ = Group.objects.get_or_create(name="chu")
        self.quan_ly_group, _ = Group.objects.get_or_create(name="quan_ly")

        for perm in Permission.objects.filter(
            codename__in=["confirm_payment_manual", "manage_ai_policy", "view_salesorder"]
        ):
            self.chu_group.permissions.add(perm)

        for perm in Permission.objects.filter(codename__in=["view_salesorder"]):
            self.quan_ly_group.permissions.add(perm)

        # 2. Users
        self.chu_user = User.objects.create_user(
            username="chu_vua_dw26", password="password", first_name="Duy", last_name="Chủ"
        )
        self.chu_user.groups.add(self.chu_group)

        self.quan_ly = User.objects.create_user(
            username="quan_ly_dw26", password="password", first_name="Linh", last_name="QL"
        )
        self.quan_ly.groups.add(self.quan_ly_group)

        # 3. Chính sách mở công tắc system.auto_confirm_exact_match của Chủ (V-DW1)
        self.policy = AiPolicyVersion.objects.create(
            version=1,
            global_mode="on",
            red_zone_open={"system.auto_confirm_exact_match": True},
            created_by=self.chu_user,
        )

        # 4. Master data & Batch
        self.customer = Customer.objects.create(
            phone="0912345678",
            name="Khách DW26",
            default_address="456 Đường ABC",
        )
        self.item_group, _ = ItemGroup.objects.get_or_create(name="Nhóm cá")
        self.item = Item.objects.create(name="Cá cam test", code="ITM-CAM-26", item_group=self.item_group)
        self.supplier = Supplier.objects.create(name="NCC Cảng 26")
        self.warehouse, _ = Warehouse.objects.get_or_create(name="Kho Lạnh 26")

        today = timezone.localdate()
        self.batch = Batch.objects.create(
            batch_id="LO-DW26-01",
            item=self.item,
            supplier=self.supplier,
            warehouse=self.warehouse,
            received_date=today,
            expiry_date=today + datetime.timedelta(days=30),
            qty_received=Decimal("100"),
            qty_available=Decimal("100"),
            purchase_rate=Decimal("100000"),
            landed_unit_cost=Decimal("100000"),
            status=Batch.Status.SELLING,
        )

        # Đơn BOOKED giữ chỗ
        self.order = SalesOrder.objects.create(
            code="SO-DW26-001",
            customer=self.customer,
            total_amount=Decimal("500000"),
            status=SalesOrder.Status.BOOKED,
        )
        self.order_line = SalesOrderLine.objects.create(
            order=self.order,
            item=self.item,
            qty=Decimal("5"),
            rate=Decimal("100000"),
            amount=Decimal("500000"),
        )
        SalesOrderLineBatch.objects.create(
            order_line=self.order_line,
            batch=self.batch,
            component_item=self.item,
            qty=Decimal("5"),
            unit_cost=Decimal("100000"),
        )

    def test_dw26_ac1_exact_match_confirms_payment_and_creates_invoice(self):
        """
        DW-26-AC1: Giao dịch UNMATCHED/OPEN: số tiền đúng bằng tổng đơn,
        mã đơn khớp đúng 1 đơn BOOKED, mã GD chưa dùng, không cờ nghi trùng, đúng môi trường
        -> đơn PAID qua đúng đường ghi tiền hiện có; giao dịch RESOLVED; AuditLog.
        """
        txn = PaymentTransaction.objects.create(
            bank_txn_id="TXN-DW26-EXACT-01",
            amount=Decimal("500000"),
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            source=PaymentTransaction.Source.GATEWAY,
            environment="SANDBOX",
            raw_payload={"order_code": self.order.code, "content": f"Thanh toan don {self.order.code}"},
            received_at=timezone.now(),
        )

        res = process_exact_payment_matches()
        self.assertEqual(res["confirmed"], 1)
        self.assertEqual(res["escalated"], 0)

        # Đơn chuyển sang PAID / PROCESSING
        self.order.refresh_from_db()
        self.assertIn(self.order.status, [SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING])

        # Hoá đơn được tạo
        invoice = SalesInvoice.objects.filter(sales_order=self.order).first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.amount, Decimal("500000"))

        # Giao dịch RESOLVED
        txn.refresh_from_db()
        self.assertEqual(txn.resolution_status, PaymentTransaction.ResolutionStatus.RESOLVED)
        self.assertEqual(txn.sales_order, self.order)

    def test_dw26_ac2_underpaid_escalates_to_chu(self):
        """DW-26-AC2 (lệch tiền): Thiếu tiền -> không xác nhận, chuyển việc cho chu."""
        txn_underpaid = PaymentTransaction.objects.create(
            bank_txn_id="TXN-DW26-UNDERPAID",
            amount=Decimal("400000"),
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            source=PaymentTransaction.Source.GATEWAY,
            environment="SANDBOX",
            raw_payload={"order_code": self.order.code},
            received_at=timezone.now(),
        )

        res = process_exact_payment_matches()
        self.assertEqual(res["confirmed"], 0)
        self.assertEqual(res["escalated"], 1)

        action = AiAction.objects.filter(
            target_model="paymenttransaction", target_id=str(txn_underpaid.id)
        ).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.status, AiAction.Status.ESCALATED)
        self.assertEqual(action.assignee_group, "chu")
        self.assertIn("Thiếu tiền", action.downgrade_reason.get("text", ""))

    def test_p8_lo8_sr25_ac1_underpaid_reason_tien_vnd_dau_cham(self):
        """P8 Lô 8 SR-25: lý do chuyển Chủ hiện tiền `x.xxx ₫`, không phải `400000.00đ`."""
        from apps.common.formatting import format_vnd

        txn = PaymentTransaction.objects.create(
            bank_txn_id="TXN-LO8-UNDERPAID",
            amount=Decimal("400000"),
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            source=PaymentTransaction.Source.GATEWAY,
            environment="SANDBOX",
            raw_payload={"order_code": self.order.code},
            received_at=timezone.now(),
        )
        process_exact_payment_matches()
        action = AiAction.objects.get(target_model="paymenttransaction", target_id=str(txn.id))
        self.assertIn(
            f"Giao dịch 400.000 ₫ khác tổng đơn {format_vnd(self.order.total_amount)} (BR-TT-04/10)",
            action.downgrade_reason["text"],
        )

    def test_dw26_ac2_cancelled_order_escalates_to_chu(self):
        """DW-26-AC2 (đơn huỷ): Đơn đã tự huỷ -> không xác nhận, chuyển việc cho chu."""
        self.order.status = SalesOrder.Status.AUTO_CANCELLED
        self.order.save(update_fields=["status"])

        txn_cancelled = PaymentTransaction.objects.create(
            bank_txn_id="TXN-DW26-CANCELLED-ORDER",
            amount=Decimal("500000"),
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            source=PaymentTransaction.Source.GATEWAY,
            environment="SANDBOX",
            raw_payload={"order_code": self.order.code},
            received_at=timezone.now(),
        )

        res = process_exact_payment_matches()
        self.assertEqual(res["confirmed"], 0)
        self.assertEqual(res["escalated"], 1)

        action = AiAction.objects.filter(
            target_model="paymenttransaction", target_id=str(txn_cancelled.id)
        ).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.status, AiAction.Status.ESCALATED)
        self.assertIn("không thể tự xác nhận", action.downgrade_reason.get("text", ""))

    def test_dw26_ac2_duplicate_warning_escalates_to_chu(self):
        """DW-26-AC2 (nghi trùng): Có cờ nghi trùng -> không xác nhận, chuyển việc cho chu."""
        order_new = SalesOrder.objects.create(
            code="SO-DW26-NEW",
            customer=self.customer,
            total_amount=Decimal("500000"),
            status=SalesOrder.Status.BOOKED,
        )
        txn_dup = PaymentTransaction.objects.create(
            bank_txn_id="TXN-DW26-DUP-WARNING",
            amount=Decimal("500000"),
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            source=PaymentTransaction.Source.GATEWAY,
            environment="SANDBOX",
            duplicate_warning="Nghi trùng xác nhận tay",
            raw_payload={"order_code": order_new.code},
            received_at=timezone.now(),
        )

        res = process_exact_payment_matches()
        self.assertEqual(res["confirmed"], 0)
        self.assertEqual(res["escalated"], 1)

        action = AiAction.objects.filter(
            target_model="paymenttransaction", target_id=str(txn_dup.id)
        ).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.status, AiAction.Status.ESCALATED)
        self.assertIn("nghi trùng", action.downgrade_reason.get("text", ""))

    def test_dw26_ac3_logs_only_txn_and_order_code_no_pii(self):
        """
        DW-26-AC3 (PII, H2): Khớp bằng code; không có đường nào đưa raw_payload/nội dung CK vào model;
        log chỉ in mã GD + mã đơn.
        """
        PaymentTransaction.objects.create(
            bank_txn_id="TXN-DW26-LOG-TEST",
            amount=Decimal("500000"),
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            source=PaymentTransaction.Source.GATEWAY,
            environment="SANDBOX",
            raw_payload={
                "order_code": self.order.code,
                "customer_name_secret": "Khách Bí Mật",
                "phone": "0999888777",
                "transfer_content": "Chuyen tien don hang 123",
            },
            received_at=timezone.now(),
        )

        with self.assertLogs("apps.sales.payments.auto_confirm", level="INFO") as cm:
            process_exact_payment_matches()

        joined_logs = " ".join(cm.output)
        self.assertIn("TXN-DW26-LOG-TEST", joined_logs)
        self.assertIn(self.order.code, joined_logs)
        # Tuyệt đối không có PII trong log
        self.assertNotIn("Khách Bí Mật", joined_logs)
        self.assertNotIn("0999888777", joined_logs)
        self.assertNotIn("Chuyen tien don hang 123", joined_logs)

    @override_settings(AI_PRODUCTION_READY=False)
    def test_dw26_ac5_production_ready_false_does_not_run(self):
        """
        DW-26-AC5 (production): AI_PRODUCTION_READY=false -> job không chạy.
        """
        PaymentTransaction.objects.create(
            bank_txn_id="TXN-DW26-PROD-TEST",
            amount=Decimal("500000"),
            match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            source=PaymentTransaction.Source.GATEWAY,
            environment="SANDBOX",
            raw_payload={"order_code": self.order.code},
            received_at=timezone.now(),
        )

        res = process_exact_payment_matches()
        self.assertEqual(res.get("reason"), "PRODUCTION_NOT_READY")
        self.assertEqual(res["confirmed"], 0)

        # Đơn vẫn BOOKED
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.BOOKED)

    @override_settings(AI_ENABLED=False)
    def test_dw26_ac6_manual_confirm_works_when_ai_disabled(self):
        """
        DW-26-AC6 (AI tắt): AI_ENABLED=false -> Chủ xác nhận tay trên ERP vẫn chạy bình thường.
        """
        from apps.sales.payments.services import confirm_payment_manual
        payment, dup = confirm_payment_manual(
            order=self.order,
            bank_txn_id="TXN-DW26-MANUAL-01",
            amount=Decimal("500000"),
            actor=self.chu_user,
        )
        self.assertFalse(dup)
        self.assertEqual(payment.match_status, PaymentTransaction.MatchStatus.MATCHED)
        self.order.refresh_from_db()
        self.assertIn(self.order.status, [SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING])
