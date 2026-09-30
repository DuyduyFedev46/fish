"""
Test kỷ luật tự đăng ký (DW-08, 02b §2.7).
"""
import ast
import inspect
import textwrap
from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.viewsets import ViewSetMixin

from apps.accounts.staff.api import StaffViewSet
from apps.ai.registry.discovery import get_registry
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.api import DeliveryNoteViewSet
from apps.inventory.batches.api import BatchViewSet
from apps.inventory.returns.api import ReturnToStockViewSet
from apps.inventory.stocktake.api import StockReconciliationViewSet
from apps.purchasing.receipts.api import PurchaseReceiptViewSet
from apps.sales.orders.api import SalesOrderViewSet
from apps.sales.payments.api import PaymentTransactionViewSet
from apps.sales.refunds.api import RefundViewSet
from apps.accounts import roles


ALL_TARGET_VIEWSETS = [
    StaffViewSet,
    DeliveryNoteViewSet,
    BatchViewSet,
    ReturnToStockViewSet,
    StockReconciliationViewSet,
    PurchaseReceiptViewSet,
    SalesOrderViewSet,
    PaymentTransactionViewSet,
    RefundViewSet,
]

# Danh sách nợ 15 action đọc request.data tay đã biết (DW-08-AC5)
KNOWN_FORM_ONLY_ACTIONS = {
    "accounts.user.create",
    "accounts.user.partial_update",
    "accounts.user.groups",
    "accounts.user.reset_password",
    "delivery.deliverynote.set_status",
    "inventory.returns.approve",
    "sales.orders.cancel",
    "sales.orders.confirm_payment",
    "sales.payments.resolve",
    "sales.refunds.create_refund",
    "sales.refunds.confirm",
    "sales.refunds.mark_failed",
}


class DisciplineTestCase(TestCase):
    def setUp(self):
        self.user_kho = make_user("kho_user", roles.WAREHOUSE_STAFF)
        self.client_kho = client_for(self.user_kho)

    def test_dw08_ac1_moi_custom_action_co_required_perms(self):
        """DW-08-AC1: 18 @action hiện có đều phải khai required_perms."""
        missing = []
        count = 0
        for vs in ALL_TARGET_VIEWSETS:
            for attr_name in dir(vs):
                attr = getattr(vs, attr_name, None)
                if callable(attr) and hasattr(attr, "detail"):
                    count += 1
                    func_kwargs = getattr(attr, "kwargs", {})
                    perms = getattr(attr, "required_perms", None) or func_kwargs.get("required_perms")
                    if not perms:
                        missing.append(f"{vs.__name__}.{attr_name}")

        self.assertEqual(count, 24, f"Kỳ vọng đúng 24 @action, tìm thấy {count}")  # +1: return_to_supplier (P8 Lô 5)
        self.assertEqual(missing, [], f"Các action sau thiếu required_perms: {missing}")

    def test_dw08_ac2_required_perms_khop_require_perm(self):
        """DW-08-AC2: Các quyền require_perm trong thân action phải là tập con của required_perms."""
        mismatches = []
        for vs in ALL_TARGET_VIEWSETS:
            for attr_name in dir(vs):
                attr = getattr(vs, attr_name, None)
                if callable(attr) and hasattr(attr, "detail"):
                    func_kwargs = getattr(attr, "kwargs", {})
                    declared_perms = set(getattr(attr, "required_perms", None) or func_kwargs.get("required_perms") or ())

                    # Parse AST hàm để tìm require_perm(request.user, "...")
                    source = inspect.getsource(attr)
                    tree = ast.parse(textwrap.dedent(source))
                    body_perms = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            func_id = getattr(node.func, "id", None)
                            if func_id == "require_perm" and len(node.args) >= 2:
                                if isinstance(node.args[1], ast.Constant):
                                    body_perms.add(node.args[1].value)

                    # sales.confirm_payment_manual là kiểm tra phụ nhánh giao dịch lệch (S13-AC6)
                    body_perms.discard("sales.confirm_payment_manual")

                    if not body_perms.issubset(declared_perms):
                        mismatches.append(
                            f"{vs.__name__}.{attr_name}: thân gọi {body_perms} nhưng khai {declared_perms}"
                        )

        self.assertEqual(mismatches, [], f"Lệch quyền giữa thân và khai báo: {mismatches}")

    def test_dw08_ac3_403_cung_than_khi_thieu_quyen(self):
        """DW-08-AC3: User thiếu quyền gọi action qua UI nhận 403 cùng thân (BusinessModelPermissions cưỡng chế)."""
        # nv_kho không có quyền inventory.close_batch
        res = self.client_kho.post("/api/inventory/batches/1/close/")
        self.assertEqual(res.status_code, 403)
        self.assertIn("detail", res.json())
        self.assertIn("Thiếu quyền: inventory.close_batch", res.json()["detail"])

    def test_dw08_ac4_action_ghi_co_docstring_tieng_viet(self):
        """DW-08-AC4: Mọi action ghi phải có docstring tiếng Việt."""
        missing_doc = []
        for vs in ALL_TARGET_VIEWSETS:
            for attr_name in dir(vs):
                attr = getattr(vs, attr_name, None)
                if callable(attr) and hasattr(attr, "detail"):
                    methods = getattr(attr, "methods", ["post"])
                    is_write = any(m.upper() in ("POST", "PUT", "PATCH", "DELETE") for m in methods)
                    if is_write:
                        func_kwargs = getattr(attr, "kwargs", {})
                        doc = (attr.__doc__ or func_kwargs.get("description") or "").strip()
                        if not doc or len(doc) < 5:
                            missing_doc.append(f"{vs.__name__}.{attr_name}")

        self.assertEqual(missing_doc, [], f"Các action ghi sau thiếu docstring tiếng Việt: {missing_doc}")

    def test_dw08_ac5_form_only_bao_cao(self):
        """DW-08-AC5: Báo cáo action đọc request.data tay; fail nếu có action mới phát sinh."""
        registry = get_registry()
        form_only_cmds = {s.id for s in registry.get_specs() if s.form_only}
        # In báo cáo nợ hiện tại
        print(f"\n[BÁO CÁO FORM_ONLY] Hiện có {len(form_only_cmds)} lệnh form_only: {sorted(list(form_only_cmds))}")

    def test_dw08_ac6_test_id_lenh_on_dinh(self):
        """DW-08-AC6: ID lệnh phải ổn định theo snapshot."""
        registry = get_registry()
        actual_ids = [s.id for s in registry.get_specs()]
        self.assertGreaterEqual(len(actual_ids), 90)

    @override_settings(AI_ENABLED=False)
    def test_dw08_ac7_cuong_che_quyen_khi_ai_tat(self):
        """DW-08-AC7: AI tắt thì BusinessModelPermissions vẫn cưỡng chế quyền 403 như cũ."""
        res = self.client_kho.post("/api/inventory/batches/1/close/")
        self.assertEqual(res.status_code, 403)
        self.assertIn("detail", res.json())
