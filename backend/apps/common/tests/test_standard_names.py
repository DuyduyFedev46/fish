"""
Lô áp tên chuẩn, Pha A BE (doc/features/2026-10-08-ap-ten-chuan/02b-tech-design.md mục 3.1).

Nguồn chữ: `doc/thuat-ngu-va-trang-thai.md` mục 4 (đã duyệt 07/10). Mỗi dòng bảng là một cặp
(mã dòng, giá trị mong đợi), nên lỗi in đúng mã C/T/P. Chỉ nhãn đổi: giá trị DB, `AuditLog.action`, codename và
khoá JSON giữ nguyên (ngoại lệ: khoá phụ thêm `auto_cancel_blocked_label`, T43).

Chưa có ở đây (Pha B, chờ W37 L3 gộp): dòng thời gian của đơn `sales/orders/timeline.py` (B9).
"""
import importlib
from datetime import timedelta
from decimal import Decimal

from django.apps import apps as django_apps
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.audit.serializers import safe_note
from apps.accounts.auth.services import CAPABILITY_LABELS
from apps.accounts.capabilities import registry
from apps.accounts.data_scopes import catalog as scope_catalog
from apps.accounts.models import AuditLog, StaffProfile
from apps.common.audit import NOTE_PRESENT_LABEL, record_audit
from apps.common.guidance.reasons import get_reason
from apps.common.tests.fixtures import client_for, make_user
from apps.catalog.models import Item, PricingRule
from apps.content.models import Entry
from apps.delivery.confirmation.serializers import AUTO_CANCEL_BLOCKED_LABELS
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.delivery.tests.test_confirmation_escalation import ConfirmationL3BaseTestCase
from apps.inventory.models import ReturnToStock, StockLedgerEntry
from apps.sales.models import PaymentTransaction, Refund, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.shop_labels import SHOP_DELIVERY_STATUS_LABELS, SHOP_ORDER_STATUS_LABELS


# --- B-T1: nhãn của `choices` -------------------------------------------------------------------------------------

CHOICE_LABELS = [
    # (mã dòng, enum, giá trị DB, nhãn chuẩn)
    ("T2", SalesOrder.Status, "AUTO_CANCELLED", "Hết giờ giữ chỗ"),
    ("T3", PaymentTransaction.MatchStatus, "MATCHED", "Khớp đơn"),
    ("T4", PaymentTransaction.MatchStatus, "UNDERPAID", "Chuyển thiếu"),
    ("T5", PaymentTransaction.MatchStatus, "ORPHAN", "Về sau khi đơn đã huỷ"),
    ("T6", PaymentTransaction.MatchStatus, "UNMATCHED", "Không khớp đơn"),
    ("T7", PaymentTransaction.MatchStatus, "OVERPAID", "Chuyển thừa"),
    ("T8", PaymentTransaction.Resolution, "ATTACHED", "Đã gắn vào đơn"),
    ("T9", PaymentTransaction.Resolution, "CONFIRMED", "Đã xác nhận đơn"),
    ("T10", PaymentTransaction.Source, "WEBHOOK", "Ngân hàng báo"),
    ("T11", PaymentTransaction.Source, "MANUAL", "Xác nhận tay"),
    ("T11", PaymentTransaction.Source, "GATEWAY", "Cổng SePay"),
    ("T12", PaymentTransaction.Environment, "SANDBOX", "Chạy thử"),
    ("T13", PaymentTransaction.Environment, "PRODUCTION", "Chạy thật"),
    ("T20", Refund.Method, "GATEWAY", "Qua cổng SePay"),
    ("T21", Refund.Status, "PENDING", "Chờ hoàn tiền"),
    ("T22", Refund.Status, "REFUNDED", "Đã hoàn tiền"),
    ("T23", Refund.Status, "FAILED", "Hoàn thất bại"),
    ("T24", DeliveryNote.Status, "CONFIRMING", "Chờ gọi xác nhận"),
    ("T25", DeliveryNote.Status, "PREPARING", "Đang soạn hàng"),
    ("T26", DeliveryNote.Status, "READY", "Chờ lấy hàng"),
    ("T27", DeliveryNote.Status, "DELIVERING", "Đang giao"),
    ("T28", DeliveryNote.Status, "COMPLETED", "Đã giao"),
    ("T29", DeliveryNote.Status, "FAILED", "Giao thất bại"),
    ("T30", DeliveryNote.Status, "CANCELLED", "Đã huỷ theo đơn"),
    ("T31", CustomerCall.Result, "CONFIRMED_CHANGED", "Đã xác nhận, có đổi thông tin"),
    ("T32", CustomerCall.Result, "WRONG_NUMBER", "Sai số điện thoại"),
    ("T33", CustomerCall.Result, "WANT_CHANGE", "Khách muốn đổi món"),
    ("T34", CustomerCall.Result, "WANT_CANCEL", "Khách muốn huỷ đơn"),
    ("T35", ConfirmationTask.EscalationReason, "WRONG_NUMBER", "Sai số điện thoại"),
    ("T36", ConfirmationTask.EscalationReason, "WANT_CANCEL", "Khách muốn huỷ đơn"),
    ("T37", ConfirmationTask.EscalationReason, "WANT_CHANGE", "Khách muốn đổi món"),
    ("T38", ConfirmationTask.State, "DONE", "Đã xong"),
    ("T44", StockLedgerEntry.MovementType, "WRITE_OFF", "Huỷ hàng, ghi lỗ"),
    ("T45", ReturnToStock.Decision, "WRITE_OFF", "Huỷ hàng, ghi lỗ"),
    ("T46", ReturnToStock.Decision, "RESTOCK", "Tái nhập"),
    ("T46", ReturnToStock.Decision, "PENDING", "Chờ quyết định"),
    ("T48", StaffProfile.Status, "INACTIVE", "Đã nghỉ"),
    ("T49", AuditLog.ActorKind, "user", "Người"),
    ("T50", Item.ItemType, "BUNDLE", "Combo"),
    ("T51", PricingRule.ApplyOn, "ITEM", "Theo mặt hàng"),
    ("T52", PricingRule.ApplyOn, "ORDER", "Theo đơn"),
]

PAGE_ROLE_LABELS = [
    ("T54", "privacy", "Chính sách bảo mật"),
    ("T55", "terms", "Điều kiện giao dịch chung"),
    ("T56", "refund", "Chính sách đổi trả và hoàn tiền"),
    ("T57", "seller_info", "Thông tin người bán"),
]

# Giá trị DB đóng băng: lô này chỉ đổi nhãn, không đổi dữ liệu (B-T2).
FROZEN_VALUES = [
    (SalesOrder.Status, ["BOOKED", "PAID", "PROCESSING", "COMPLETED", "CANCELLED", "AUTO_CANCELLED"]),
    (PaymentTransaction.MatchStatus, ["MATCHED", "UNDERPAID", "ORPHAN", "UNMATCHED", "OVERPAID"]),
    (PaymentTransaction.Resolution, ["ATTACHED", "CONFIRMED", "REFUNDED"]),
    (PaymentTransaction.Source, ["WEBHOOK", "MANUAL", "GATEWAY"]),
    (PaymentTransaction.Environment, ["SANDBOX", "PRODUCTION"]),
    (Refund.Method, ["MANUAL_TRANSFER", "GATEWAY"]),
    (Refund.Status, ["PENDING", "REFUNDED", "FAILED"]),
    (DeliveryNote.Status,
     ["CONFIRMING", "PREPARING", "READY", "DELIVERING", "COMPLETED", "FAILED", "CANCELLED"]),
    (ConfirmationTask.State, ["PENDING", "CALLBACK", "ESCALATED", "REFUND_CALL", "DONE"]),
    (ConfirmationTask.EscalationReason, ["UNREACHABLE", "WRONG_NUMBER", "WANT_CANCEL", "WANT_CHANGE"]),
    (CustomerCall.Result,
     ["CONFIRMED", "CONFIRMED_CHANGED", "UNREACHABLE", "WRONG_NUMBER", "CALLBACK", "WANT_CHANGE", "WANT_CANCEL",
      "NOTIFIED"]),
    (StockLedgerEntry.MovementType,
     ["RECEIPT", "SALE", "RETURN_RESTOCK", "RECONCILE", "WRITE_OFF", "CANCEL_RESTORE", "SUPPLIER_RETURN"]),
    (ReturnToStock.Decision, ["PENDING", "RESTOCK", "WRITE_OFF"]),
    (StaffProfile.Status, ["ACTIVE", "INACTIVE"]),
    (AuditLog.ActorKind, ["user", "system", "ai"]),
    (Item.ItemType, ["SIMPLE", "BUNDLE"]),
    (PricingRule.ApplyOn, ["ITEM", "ORDER"]),
]

# --- B-C: tên chứng từ ---------------------------------------------------------------------------------------------

VERBOSE_NAMES = [
    # (mã dòng, "app_label.Model", tên chuẩn)
    ("C1", "inventory.ReturnToStock", "Hàng hoàn"),
    ("C2", "sales.SalesCreditNote", "Phiếu trừ doanh thu"),
    ("C3", "sales.Refund", "Phiếu hoàn tiền"),
    ("C4", "delivery.DeliveryNote", "Phiếu giao"),
    ("C5", "sales.PaymentTransaction", "Khoản tiền về"),
    ("C6", "purchasing.PurchaseReceipt", "Phiếu nhập"),
    ("C7", "inventory.StockEntry", "Phiếu điều chỉnh tồn"),
    ("C8", "inventory.BatchSupplierReturn", "Trả nhà cung cấp"),
    ("C9", "delivery.ConfirmationTask", "Việc gọi xác nhận"),
]

# --- B-P: quyền Tầng 2 ---------------------------------------------------------------------------------------------

PERMISSION_NAMES = [
    # (mã dòng, app, codename, tên chuẩn)
    ("P1", "sales", "confirm_payment_manual", "Xác nhận đã nhận tiền"),
    ("P2", "inventory", "publish_batch", "Mở bán lô"),
    ("P3", "inventory", "cancel_expired_batch", "Huỷ lô quá hạn (ghi lỗ)"),
    ("P4", "inventory", "approve_returntostock", "Duyệt hàng hoàn"),
    ("P9", "delivery", "assign_deliverynote", "Chọn người giao"),
    ("P10", "delivery", "pack_deliverynote", "Soạn hàng"),
    ("P12", "reports", "view_profitreport", "Xem báo cáo lãi lỗ"),
    ("P12", "reports", "view_dashboard", "Xem Tổng quan"),
    ("P13", "catalog", "change_item_image", "Sửa ảnh mặt hàng"),
]

# Nhãn cũ (trước lô) để kiểm bẫy `auth_permission.name` của DB đã có quyền.
OLD_PERMISSION_NAMES = {
    "confirm_payment_manual": "Xác nhận thanh toán thủ công",
    "publish_batch": "Publish lô ra Shop",
    "cancel_expired_batch": "Huỷ lô quá hạn (hạch toán lỗ)",
    "approve_returntostock": "Duyệt hàng hoàn về kho",
    "assign_deliverynote": "Giao phiếu cho người giao",
    "pack_deliverynote": "Đóng gói phiếu giao",
    "view_profitreport": "Xem báo cáo giá vốn / lãi lỗ",
    "view_dashboard": "Xem Tổng quan vận hành",
    "change_item_image": "Thêm / thay / gỡ ảnh mặt hàng",
}


class ChoiceLabelTests(TestCase):
    def test_bt1_choice_labels_follow_standard_names(self):
        for code, enum, value, label in CHOICE_LABELS:
            with self.subTest(code=code, field=enum.__qualname__, value=value):
                self.assertEqual(enum(value).label, label)

    def test_bt1_page_role_labels(self):
        labels = dict(Entry.PAGE_ROLE_CHOICES)
        for code, value, label in PAGE_ROLE_LABELS:
            with self.subTest(code=code):
                self.assertEqual(labels[value], label)

    def test_bt1_no_old_wording_left_in_labels(self):
        banned = ("TTL", "Webhook", "Sandbox", "Production", "chờ Chủ", "hạch toán", "Publish", "CSKH")
        for enum, _ in FROZEN_VALUES:
            for choice_label in enum.labels:
                for word in banned:
                    with self.subTest(enum=enum.__qualname__, label=str(choice_label), word=word):
                        self.assertNotIn(word, str(choice_label))

    def test_bt1_cancel_reason_labels(self):
        labels = order_services.CANCEL_REASON_LABELS
        self.assertEqual(labels["CUSTOMER_CHANGED_MIND"], "Khách đổi ý")  # T14
        self.assertEqual(labels["DAMAGED_WHEN_PACKING"], "Hàng hư lúc soạn hàng")  # T15
        self.assertEqual(labels["GIVE_UP_AFTER_FAILED"], "Giao thất bại, không giao lại")  # T16
        self.assertEqual(labels["UNREACHABLE"], "Không liên lạc được khách")  # T17
        self.assertEqual(labels["OTHER"], "Lý do khác")  # T18
        self.assertEqual(
            order_services.SYSTEM_CANCEL_REASON_CODES["UNREACHABLE_AUTO"],
            "Hệ thống tự huỷ: không liên lạc được khách",  # T19
        )

    def test_bt1_shop_labels_for_customers(self):
        self.assertEqual(SHOP_ORDER_STATUS_LABELS["BOOKED"], "Chờ thanh toán")  # T1 Shop
        self.assertEqual(SHOP_ORDER_STATUS_LABELS["AUTO_CANCELLED"], "Đã huỷ vì quá giờ thanh toán")  # T2 Shop
        expected = {
            "CONFIRMING": "Chờ vựa gọi xác nhận",
            "PREPARING": "Đang soạn hàng",
            "READY": "Đã soạn xong, chờ giao",
            "DELIVERING": "Đang giao",
            "COMPLETED": "Đã giao",
            "FAILED": "Giao chưa thành công, vựa sẽ liên hệ lại",
            "CANCELLED": "Đã huỷ",
        }
        self.assertEqual(SHOP_DELIVERY_STATUS_LABELS, expected)  # T24-T30 Shop
        for status in DeliveryNote.Status.values:  # khách không bao giờ thấy mã thô
            self.assertNotEqual(SHOP_DELIVERY_STATUS_LABELS[status], status)


class DbValuesUnchangedTests(TestCase):
    def test_bt2_choice_values_are_frozen(self):
        for enum, values in FROZEN_VALUES:
            with self.subTest(enum=enum.__qualname__):
                self.assertEqual(list(enum.values), values)

    def test_bt2_page_role_values_are_frozen(self):
        self.assertEqual([v for v, _ in Entry.PAGE_ROLE_CHOICES], ["privacy", "terms", "refund", "seller_info"])

    def test_bt2_source_choices_untouched(self):
        # Phần AI không thuộc lô này (02b mục 0).
        self.assertEqual(Entry.SOURCE_CHOICES, [("human", "Người dùng"), ("ai", "AI")])
        self.assertEqual(AuditLog.ActorKind.AI.label, "AI (thay người dùng)")


class VerboseNameTests(TestCase):
    def test_bc_document_names(self):
        for code, label, expected in VERBOSE_NAMES:
            model = django_apps.get_model(label)
            with self.subTest(code=code):
                self.assertEqual(str(model._meta.verbose_name), expected)
                self.assertEqual(str(model._meta.verbose_name_plural), expected)

    def test_bc_refund_payment_field_uses_standard_name(self):
        field = Refund._meta.get_field("payment_transaction")
        self.assertEqual(str(field.verbose_name), "Khoản tiền về (không hoá đơn)")


class PermissionNameTests(TestCase):
    def test_bp_meta_permissions(self):
        for code, app_label, codename, expected in PERMISSION_NAMES:
            with self.subTest(code=code, codename=codename):
                model = next(
                    m for m in django_apps.get_app_config(app_label).get_models()
                    if codename in dict(m._meta.permissions or [])
                )
                self.assertEqual(dict(model._meta.permissions)[codename], expected)

    def test_bp_permission_table_has_standard_name_after_migrate(self):
        for code, app_label, codename, expected in PERMISSION_NAMES:
            with self.subTest(code=code, codename=codename):
                perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                self.assertEqual(perm.name, expected)

    def test_bp_data_migration_renames_existing_permission_rows(self):
        """Bẫy: Django không đổi `auth_permission.name` của quyền đã có; migration 0017 phải làm."""
        migration = importlib.import_module("apps.accounts.migrations.0017_rename_permission_labels")
        group_ids_before = {
            codename: set(Permission.objects.get(codename=codename, content_type__app_label=app)
                          .group_set.values_list("pk", flat=True))
            for _, app, codename, _ in PERMISSION_NAMES
        }
        for _, app_label, codename, _ in PERMISSION_NAMES:  # dựng DB "cũ" như staging/production
            Permission.objects.filter(content_type__app_label=app_label, codename=codename).update(
                name=OLD_PERMISSION_NAMES[codename]
            )
        migration.rename_forward(django_apps, None)
        migration.rename_forward(django_apps, None)  # idempotent: chạy hai lần như nhau
        for code, app_label, codename, expected in PERMISSION_NAMES:
            with self.subTest(code=code, codename=codename):
                perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                self.assertEqual(perm.name, expected)
                # Chỉ đổi tên: codename và gán Group giữ nguyên.
                self.assertEqual(set(perm.group_set.values_list("pk", flat=True)), group_ids_before[codename])
        migration.rename_backward(django_apps, None)  # có chiều ngược
        for _, app_label, codename, _ in PERMISSION_NAMES:
            self.assertEqual(
                Permission.objects.get(content_type__app_label=app_label, codename=codename).name,
                OLD_PERMISSION_NAMES[codename],
            )
        migration.rename_forward(django_apps, None)

    def test_bp_matrix_labels(self):
        by_key = registry.BY_KEY
        self.assertEqual(by_key["create_refund"].label, "Lập phiếu hoàn tiền")  # P7
        self.assertEqual(by_key["assign_delivery"].label, "Chọn người giao")  # P9
        self.assertEqual(by_key["create_return"].label, "Ghi hàng hoàn")  # C1
        self.assertEqual(by_key["approve_return"].label, "Duyệt hàng hoàn")  # P4
        self.assertEqual(by_key["confirm_payment"].label, "Xác nhận đã nhận tiền")  # P1
        self.assertEqual(by_key["publish_batch"].label, "Mở bán lô")  # P2
        self.assertEqual(by_key["publish_content"].label, "Đăng bài lên Shop")  # P13

    def test_bp_my_account_capability_labels(self):
        self.assertEqual(CAPABILITY_LABELS["sales.create_refund"], "Lập phiếu hoàn tiền")  # P7
        self.assertEqual(CAPABILITY_LABELS["delivery.pack_deliverynote"], "Soạn hàng")  # P10
        self.assertEqual(CAPABILITY_LABELS["delivery.assign_deliverynote"], "Chọn người giao")  # P9
        self.assertEqual(CAPABILITY_LABELS["content.publish_entry"], "Đăng bài lên Shop")  # P13

    def test_bp_data_scope_label_for_returns(self):
        self.assertEqual(scope_catalog.RETURNS.label, "Hàng hoàn")  # C1

    def test_bp_reason_sentence_uses_full_refund_name(self):
        self.assertIn("phiếu hoàn tiền", get_reason("BR-HT-04"))  # C3
        self.assertTrue(get_reason("BR-HT-08").startswith("Phiếu hoàn tiền"))


class AuditNoteLegacyTests(TestCase):
    """Nhãn lý do huỷ đổi chữ, nhưng AuditLog cũ trong DB vẫn mang chữ cũ và không bị che mất (bất biến 4)."""

    def test_legacy_and_new_cancel_labels_both_pass_through(self):
        for label in ("Hư hỏng khi soạn hàng", "Bỏ giao sau khi thất bại", "Khác", "Lý do khác",
                      "Hàng hư lúc soạn hàng", "Giao thất bại, không giao lại"):
            with self.subTest(label=label):
                note = f"Lý do: {label} · {NOTE_PRESENT_LABEL}"
                self.assertEqual(safe_note("cancel_paid_order", note), note)

    def test_free_text_after_label_is_still_masked(self):
        masked = safe_note("cancel_paid_order", "Lý do: Lý do khác — gọi 0900000999")
        self.assertNotIn("0900000999", masked)


class AutoCancelBlockedLabelTests(ConfirmationL3BaseTestCase):
    """T43: khoá phụ `auto_cancel_blocked_label`; `auto_cancel_blocked` giữ mã thô."""

    def _detail(self, user, note):
        resp = client_for(user).get(f"/api/confirmation/queue/{note.pk}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_bt43_label_when_blocked_by_closed_batch(self):
        _, note, task = self._create_order_with_confirmation()
        task.auto_cancel_blocked_code = "BR-LO-05"
        task.save()
        data = self._detail(make_user("manager_names", roles.MANAGER), note)
        self.assertEqual(data["auto_cancel_blocked"], "BR-LO-05")
        self.assertEqual(data["auto_cancel_blocked_label"], "Lô đã chốt, không tự huỷ được")

    def test_bt43_null_when_not_blocked(self):
        _, note, _ = self._create_order_with_confirmation()
        data = self._detail(make_user("manager_names", roles.MANAGER), note)
        self.assertIsNone(data["auto_cancel_blocked"])
        self.assertIsNone(data["auto_cancel_blocked_label"])

    def test_bt43_label_is_constant_without_customer_data(self):
        for text in AUTO_CANCEL_BLOCKED_LABELS.values():
            self.assertNotRegex(text, r"\d{6,}")  # không SĐT / mã ghép từ dữ liệu khách

    def test_bt37_escalation_label_is_plain_choice_label(self):
        _, note, task = self._create_order_with_confirmation()
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.WANT_CHANGE
        task.save()
        data = self._detail(make_user("manager_names", roles.MANAGER), note)
        self.assertEqual(data["escalation_label"], "Khách muốn đổi món")


class ItemTimelineLabelTests(TestCase):
    """T73 + B22: BE ghi `item_image_add`, bảng nhãn từng dò sai khoá `item_image_upload`."""

    def test_bt73_item_image_add_has_label_not_generic(self):
        from apps.catalog.models import ItemGroup

        owner = make_user("owner_names", roles.OWNER)
        item = Item.objects.create(code="CA-T73", name="Cá thử", item_group=ItemGroup.objects.create(name="Cá"))
        record_audit("item_image_add", actor=owner, obj=item)
        record_audit("admin_edit", actor=owner, obj=item)
        rows = client_for(owner).get(f"/api/guidance/item/{item.pk}/").json()["timeline"]
        labels = [r["label"] for r in rows]
        self.assertIn("Thêm ảnh mặt hàng", labels)
        self.assertIn("Sửa trong trang quản trị kỹ thuật", labels)  # T76
        self.assertNotIn("Có thay đổi", labels)


class PaymentAndRefundTimelineTests(ConfirmationL3BaseTestCase):
    """B10: dòng thời gian khoản tiền và phiếu hoàn tiền (C3, C5, P7); dòng thời gian của ĐƠN để Pha B."""

    def test_b10_payment_and_refund_timeline_wording(self):
        from apps.sales.payments.timeline import build_payment_timeline
        from apps.sales.refunds.timeline import build_refund_timeline

        order, _, _ = self._create_order_with_confirmation()
        refund = Refund.objects.create(
            sales_invoice=order.invoice, amount=Decimal("100000"), created_by=make_user("owner_names_a", roles.OWNER),
        )
        pay_labels = [e.label for e in build_payment_timeline(order.payments.first())]
        refund_labels = [e.label for e in build_refund_timeline(refund)]
        self.assertTrue(pay_labels[0].startswith("Nhận khoản tiền về "), pay_labels)
        self.assertIn("Lập phiếu hoàn tiền 100.000 đ", refund_labels)
        for text in pay_labels + refund_labels:
            for old in ("Nhận giao dịch thanh toán", "Tạo phiếu hoàn ", "chờ Chủ", "Webhook"):
                self.assertNotIn(old, text)

    def test_b10_next_step_labels(self):
        order, _, _ = self._create_order_with_confirmation()
        steps = client_for(make_user("owner_names_b", roles.OWNER)).get(f"/api/guidance/order/{order.pk}/")
        self.assertEqual(steps.status_code, 200, steps.content)
        labels = [s["label"] for s in steps.json().get("next_steps", [])]
        self.assertIn("Lập phiếu hoàn tiền", labels)  # P7
        self.assertNotIn("Tạo phiếu hoàn", labels)


class RefundReturnsLabelTests(TestCase):
    def test_b16_return_decision_label_has_single_source(self):
        from apps.inventory.returns import serializers

        self.assertFalse(hasattr(serializers, "DECISION_LABELS"))
        self.assertEqual(ReturnToStock.Decision.WRITE_OFF.label, "Huỷ hàng, ghi lỗ")

    def test_b13_b16_action_labels(self):
        from apps.delivery.next_steps import ACTION_LABELS as DELIVERY_LABELS
        from apps.inventory.returns.next_steps import ACTION_LABELS as RETURN_LABELS

        self.assertEqual(DELIVERY_LABELS["delivery_confirm_skipped"], "Bỏ qua gọi xác nhận")  # P11
        self.assertEqual(DELIVERY_LABELS["delivery_extended"], "Gia hạn gọi")  # P11
        self.assertEqual(RETURN_LABELS["return_to_warehouse"], "Mang hàng về kho")  # P5
        self.assertEqual(RETURN_LABELS["approve_returntostock"], "Duyệt hàng hoàn")  # P4
        self.assertEqual(RETURN_LABELS["cancel_returntostock"], "Huỷ phiếu hàng hoàn")  # P5


class OrderTimelineWordingTests(OrderApiBase):
    """B9 (Pha B): dòng thời gian của ĐƠN dùng tên chuẩn (P4, P5, P6, P7, T2, T25, C1-C3)."""

    BANNED = ("đảo doanh thu", "phiếu hàng về kho", "hàng về kho:", "Tạo phiếu hoàn ", "Thử chuyển lại phiếu hoàn",
              "hạch toán", "chờ Chủ", "Webhook", "Soạn hàng)", "Tự huỷ vì")

    def setUp(self):
        super().setUp()
        self.owner = make_user("tl_names_owner", roles.OWNER)
        self.courier = make_user("tl_names_courier", roles.DELIVERY_STAFF)

    def _labels(self, order):
        rows = client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()["timeline"]
        return [r["label"] for r in rows]

    def _assert_clean(self, labels):
        for label in labels:
            for old in self.BANNED:
                self.assertNotIn(old, label)

    def test_b9_delivery_return_and_refund_lines(self):
        from apps.delivery import services as delivery_services
        from apps.common.tests.fixtures import confirm_note_for_test
        from apps.inventory.returns import services as return_services
        from apps.sales.refunds import services as refund_services

        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        confirm_note_for_test(note)
        for status in (DeliveryNote.Status.READY, DeliveryNote.Status.DELIVERING):
            delivery_services.advance_status(note=note, to_status=status, actor=self.courier)
        delivery_services.mark_failed(note=note, actor=self.courier)
        rt = delivery_services.return_to_warehouse(
            note=note, batch=self.batch, qty=Decimal("2"), actor=self.courier,
        )
        rt.decision = ReturnToStock.Decision.WRITE_OFF
        rt.save(update_fields=["decision"])
        return_services.apply_return(return_to_stock=rt, approver=self.owner)
        refund, _ = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("100000"), is_partial=True, reason="x", actor=self.owner,
        )
        refund_services.mark_refund_failed(refund=refund, reason="x", actor=self.owner)
        refund_services.retry_refund(refund=refund, actor=self.owner)
        labels = self._labels(order)
        self._assert_clean(labels)
        self.assertTrue(any(l.startswith("Tạo phiếu giao ") and l.endswith("(Đang soạn hàng)") for l in labels), labels)
        self.assertTrue(any(l.startswith("Mang hàng về kho ") for l in labels), labels)  # giữ nguyên (C1)
        self.assertIn("Duyệt hàng hoàn: Huỷ hàng, ghi lỗ", labels)  # P4, T45
        self.assertIn("Lập phiếu hoàn tiền 100.000 đ", labels)  # P7
        self.assertIn("Phiếu hoàn tiền 100.000 đ chuyển thất bại", labels)  # C3
        self.assertIn("Thử hoàn tiền lại 100.000 đ", labels)  # P7

    def test_b9_cancel_return_credit_note_and_auto_cancel(self):
        order = self._paid_order()
        order_services.cancel_paid_order(order=order, actor=self.owner, reason="x", reason_code="CUSTOMER_CHANGED_MIND")
        labels = self._labels(order)
        self._assert_clean(labels)
        self.assertTrue(any(l.startswith("Lập phiếu trừ doanh thu ") for l in labels), labels)  # P6

        expired = self._order(phone="0901234999")
        expired.booked_expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=["booked_expires_at"])
        order_services.cancel_unpaid_expired()
        labels = self._labels(expired)
        self._assert_clean(labels)
        self.assertIn("Hết giờ giữ chỗ, đã nhả hàng giữ", labels)  # T2


class CancelAndResolveNoteTests(TestCase):
    """Low 1 và Low 2: ghi chú AuditLog không lặp chữ, và nhận cả mẫu cũ lẫn mới."""

    def test_new_cancel_note_has_no_repeated_wording(self):
        text = order_services._cancel_audit_note("OTHER", "")
        self.assertEqual(text, "Huỷ đơn: Lý do khác")
        self.assertNotIn("Lý do: Lý do", text)

    def test_cancel_note_old_and_new_prefix_both_pass(self):
        for note in ("Huỷ đơn: Lý do khác", f"Huỷ đơn: Lý do khác · {NOTE_PRESENT_LABEL}",
                     "Lý do: Khác", "Lý do: Lý do khác"):
            self.assertEqual(safe_note("cancel_paid_order", note), note)

    def test_resolve_payment_note_old_and_new_pattern(self):
        for note in ("Hoàn tiền theo phiếu hoàn tiền #12", "Hoàn tiền theo phiếu hoàn #12"):
            self.assertEqual(safe_note("resolve_payment", note), note)
        masked = safe_note("resolve_payment", "Hoàn tiền theo phiếu hoàn tiền #12\n0900000999")
        self.assertNotIn("0900000999", masked)
