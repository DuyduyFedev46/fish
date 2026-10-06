"""
PV-01 — Ảnh chụp phạm vi dữ liệu HIỆN TẠI làm mốc (BR-PQ-13, BR-PQ-33, BR-PQ-38; bất biến 9).

Chạy TRƯỚC mọi sửa code phạm vi và phải xanh trên code cũ. PV-02 → PV-07 phải giữ nó xanh: đó là bằng chứng
chuyển sang phạm vi cấu hình không làm ai thấy nhiều hơn hay ít hơn.

Mốc nằm ở `scope_snapshot_baseline.json` (chỉ nhãn fixture và sự kiện có/không giá trị, không có tên, SĐT, địa chỉ).
Cố ý đổi hành vi thì sinh lại mốc rồi đọc diff trước khi commit:

    UPDATE_SCOPE_SNAPSHOT=1 python manage.py test apps.accounts.data_scopes.tests.test_scope_snapshot

Lô 4 (PV-04..06): tài khoản `direct_permissions` (người không nhóm) bị thu hẹp ở phiếu nhập (D6) và khách (D7), 02b §7 D-3.
Mốc vẫn ghi hành vi cũ; các lệch đó nằm ở `PENDING_DUY_DIFFS` (CHỜ Duy D-3), không phải `APPROVED_DIFFS`. Không merge main
khi `PENDING_DUY_DIFFS` còn mục.
"""
import json
import os
from pathlib import Path
from unittest import mock

from django.test import TestCase

from . import fixtures
from .snapshot import (
    APPROVED_DIFFS, PHONE_LIKE, Collector, Diff, diff_snapshots, format_diffs, is_approved, unapproved,
)

BASELINE_PATH = Path(__file__).with_name("scope_snapshot_baseline.json")
UPDATE_ENV = "UPDATE_SCOPE_SNAPSHOT"

# Endpoint tối thiểu của PV-01 (danh sách + chi tiết, hàng chờ, danh bạ, dòng thời gian, AI...). Test độ phủ kiểm mốc có đủ.
REQUIRED_ENDPOINTS = (
    "orders.list", "orders.detail", "orders.search_phone", "orders.search_name", "orders.filter_customer",
    "invoices.list", "invoices.detail", "refunds.list", "refunds.detail",
    "deliveries.list", "deliveries.mine", "deliveries.other", "deliveries.detail",
    "returns.list", "returns.detail", "receipts.list", "receipts.detail",
    "confirmation.queue", "confirmation.detail", "confirmation.search_phone",
    "directory.list", "directory.detail", "directory.search", "customers.list", "customers.detail",
    "guidance.order", "guidance.delivery", "guidance.return", "guidance.customer", "guidance.receipt",
    "dashboard.summary", "ai.orders_list", "ai.orders_detail",
    "actions.confirmation_claim", "actions.confirmation_call", "actions.confirmation_unconfirm",
    "actions.confirmation_recipient", "actions.returns_create", "actions.returns_cancel", "actions.returns_update",
    "actions.receipts_update", "actions.receipts_submit", "actions.receipts_cancel",
    "actions.deliveries_assign", "actions.deliveries_status", "actions.deliveries_label",
    "actions.deliveries_label_print", "actions.deliveries_label_void",
)


def load_baseline():
    if not BASELINE_PATH.exists():
        raise AssertionError(
            f"Chưa có tệp mốc {BASELINE_PATH.name}. Sinh bằng {UPDATE_ENV}=1 trên code TRƯỚC khi đổi phạm vi."
        )
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def write_baseline(snapshot):
    BASELINE_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8",
    )


class ScopeSnapshotTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._now_patch = mock.patch("django.utils.timezone.now", return_value=fixtures.NOW)
        cls._now_patch.start()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._now_patch.stop()

    @classmethod
    def setUpTestData(cls):
        cls.scene = fixtures.build_scene()
        cls.collector = Collector(cls.scene)

    def test_pv01_ac1_snapshot_matches_baseline(self):
        """PV-01-AC1: thu ảnh chụp mọi tài khoản × endpoint rồi so với tệp mốc; không lệch."""
        actual = self.collector.collect()
        if os.environ.get(UPDATE_ENV):
            write_baseline(actual)
            return
        diffs = unapproved(diff_snapshots(load_baseline(), actual))
        self.assertEqual(
            diffs, [], f"Phạm vi dữ liệu lệch so với mốc ({len(diffs)} chỗ):\n{format_diffs(diffs)}",
        )

    def test_pv01_ac1_baseline_covers_every_user_and_required_endpoint(self):
        """PV-01-AC1: mốc có đủ tài khoản mẫu và endpoint tối thiểu, không rỗng."""
        baseline = load_baseline()
        self.assertEqual(sorted(baseline), sorted(fixtures.USER_LABELS))
        for user in fixtures.USER_LABELS:
            for endpoint in REQUIRED_ENDPOINTS:
                self.assertIn(endpoint, baseline[user], f"{user} thiếu endpoint {endpoint}")
                self.assertTrue(baseline[user][endpoint], f"{user} {endpoint} rỗng")

    def test_pv01_ac1_fixture_has_known_scope_facts(self):
        """Kiểm chứng mốc phản ánh đúng hành vi hiện tại ở vài điểm then chốt (không chỉ 'khớp chính nó')."""
        baseline = load_baseline()
        courier = set(baseline["courier"]["orders.list"])
        self.assertIn("visible:order_assigned_courier", courier)
        self.assertNotIn("visible:order_assigned_other", courier)  # NV giao chỉ thấy đơn của phiếu gán cho mình
        self.assertIn("pii:order_ended_3_days:customer_name", courier)  # trong cửa sổ 7 ngày
        self.assertNotIn("pii:order_ended_8_days:customer_name", courier)  # quá cửa sổ: ẩn
        owner = set(baseline["owner"]["orders.list"])
        self.assertIn("visible:order_assigned_other", owner)  # Chủ thấy tất cả
        self.assertIn("pii:order_assigned_other:customer_name", owner)
        warehouse_invoices = set(baseline["warehouse_staff"]["invoices.list"])
        self.assertFalse([f for f in warehouse_invoices if f.endswith(":customer_name")])  # hôm nay NV kho chưa thấy tên
        self.assertEqual(set(baseline["anonymous"]["orders.list"]), {"status=401"})

    def test_pv01_ac2_real_rule_change_turns_red_and_names_user_endpoint_row(self):
        """PV-01-AC2: cố ý cho NV giao thấy mọi phiếu giao -> so với mốc thì đỏ, in tài khoản, endpoint, dòng."""
        baseline = load_baseline()
        with mock.patch("apps.delivery.scope.resolve_data_scope", return_value="all"):
            actual = self.collector.collect(users={"courier"}, only={"deliveries.list"})
        diffs = unapproved(diff_snapshots(baseline, actual, users={"courier"}))
        self.assertTrue(diffs)
        self.assertIn(
            Diff("courier", "deliveries.list", "+", "visible:note_of_order_assigned_other"), diffs,
        )
        message = format_diffs(diffs)
        self.assertIn("[courier] deliveries.list + visible:note_of_order_assigned_other", message)

    def test_pv01_ac2_losing_access_is_also_a_diff(self):
        """PV-01-AC2: thấy bớt cũng là lệch (dấu '-'), vì 'không ai mất quyền ngoài ý muốn' cũng là mục tiêu."""
        baseline = load_baseline()
        actual = json.loads(json.dumps(baseline))
        actual["manager"]["orders.list"].remove("visible:order_assigned_other")
        diffs = unapproved(diff_snapshots(baseline, actual))
        self.assertEqual(diffs, [Diff("manager", "orders.list", "-", "visible:order_assigned_other")])

    def test_pv01_ac3_only_one_approved_exception(self):
        """PV-01-AC3: ngoại lệ duy nhất là Q-4 (danh sách hoá đơn, ô tên khách) cho thành viên nhóm NV kho: `warehouse_staff`
        và người kiêm nhiệm kho + giao `warehouse_courier` (cùng nhóm NV kho, cùng V2). Ghi rõ duyệt 02/10 Q-4.
        Không có ngoại lệ nào cho `direct_permissions` (R9, D-3)."""
        self.assertEqual(
            APPROVED_DIFFS,
            (
                ("warehouse_staff", "invoices.list", "+", "pii:*:customer_name"),
                ("warehouse_courier", "invoices.list", "+", "pii:*:customer_name"),
            ),
        )
        self.assertFalse([diff for diff in APPROVED_DIFFS if diff[0] == "direct_permissions"])
        source = (Path(__file__).with_name("snapshot.py")).read_text(encoding="utf-8")
        self.assertIn("Duy duyệt 02/10 Q-4", source)

    def test_pv01_pending_duy_diffs_are_direct_permissions_and_narrowing_only(self):
        """M1 (review Lô 4): mục CHỜ Duy D-3 chỉ của `direct_permissions` và chỉ thu hẹp (dòng biến mất hoặc 200 thành 404)."""
        from .snapshot import PENDING_DUY_DIFFS

        self.assertTrue(PENDING_DUY_DIFFS)
        for user, _endpoint, sign, glob in PENDING_DUY_DIFFS:
            self.assertEqual(user, "direct_permissions")
            self.assertTrue(sign == "-" or (sign == "+" and glob == "status:*=404"), (sign, glob))
        self.assertFalse([d for d in APPROVED_DIFFS if d[0] == "direct_permissions"])
        # Một dòng thấy THÊM của direct_permissions không được miễn.
        self.assertFalse(is_approved(Diff("direct_permissions", "receipts.list", "+", "visible:receipt_manager_today")))
        self.assertFalse(is_approved(Diff("direct_permissions", "orders.list", "-", "visible:order_assigned_direct")))
        self.assertFalse(is_approved(Diff("manager", "receipts.list", "-", "visible:receipt_manager_today")))

    def test_pv01_ac3_approved_exception_passes_but_other_diffs_fail(self):
        baseline = load_baseline()
        actual = json.loads(json.dumps(baseline))
        invoice = "pii:invoice_of_order_assigned_courier:customer_name"
        actual["warehouse_staff"]["invoices.list"].append(invoice)
        self.assertEqual(unapproved(diff_snapshots(baseline, actual)), [])  # đúng ngoại lệ: được lệch
        self.assertTrue(is_approved(Diff("warehouse_staff", "invoices.list", "+", invoice)))
        # Cùng sự kiện nhưng khác tài khoản / khác endpoint / khác chiều / khác ô -> không được miễn.
        for diff in (
            Diff("manager", "invoices.list", "+", invoice),
            Diff("warehouse_staff", "orders.list", "+", invoice),
            Diff("warehouse_staff", "invoices.list", "-", invoice),
            Diff("warehouse_staff", "invoices.list", "+", "pii:invoice_of_order_assigned_courier:phone"),
            Diff("warehouse_staff", "invoices.list", "+", "visible:invoice_of_order_booked_unpaid"),
        ):
            self.assertFalse(is_approved(diff), diff)

    def test_pv01_ac4_baseline_has_no_personal_data(self):
        """PV-01-AC4: grep tệp mốc theo tên, SĐT, địa chỉ, ghi chú giả của fixture -> không thấy."""
        text = BASELINE_PATH.read_text(encoding="utf-8")
        self.assertTrue(fixtures.FAKE_STRINGS)
        for fake in fixtures.FAKE_STRINGS:
            self.assertNotIn(fake, text)
        self.assertNotIn("Khách Giả", text)
        self.assertNotIn("Đường Giả", text)
        self.assertFalse(PHONE_LIKE.findall(text), "Tệp mốc có chuỗi giống SĐT")

    def test_pv01_actions_are_rolled_back_and_recorded(self):
        """M1: hành động ghi không để lại dấu vết (savepoint rollback) và mốc ghi được mã của cả dòng trong lẫn ngoài phạm vi."""
        from apps.delivery.models import CustomerCall, LabelPrint
        from apps.inventory.models import ReturnToStock
        from apps.purchasing.models import PurchaseReceipt

        counts = (CustomerCall.objects.count(), LabelPrint.objects.count(), ReturnToStock.objects.count(),
                  PurchaseReceipt.objects.filter(status="CANCELLED").count())
        facts = self.collector.collect(users={"owner", "courier"}, only={
            "actions.confirmation_call", "actions.returns_create", "actions.receipts_cancel",
            "actions.deliveries_label_print"})
        after = (CustomerCall.objects.count(), LabelPrint.objects.count(), ReturnToStock.objects.count(),
                 PurchaseReceipt.objects.filter(status="CANCELLED").count())
        self.assertEqual(counts, after)
        owner_returns = set(facts["owner"]["actions.returns_create"])
        self.assertTrue(any(f.startswith("status:no_note=") for f in owner_returns))
        self.assertTrue(any(f.startswith("status:note_of_order_assigned_other=") for f in owner_returns))
        self.assertFalse([f for f in owner_returns if "EXC" in f])

    def test_pv01_snapshot_is_deterministic(self):
        """Hai lần thu liên tiếp cho cùng kết quả (mốc không dao động theo pk hay giờ máy)."""
        subset = {"courier", "customer_service"}
        first = self.collector.collect(users=subset)
        second = self.collector.collect(users=subset)
        self.assertEqual(first, second)
