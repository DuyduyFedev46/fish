"""
P8 Lô 1 — SR-01: Nhật ký không lộ giá vốn qua khoá tiền suy ra được giá vốn
(BM-01, bất biến 1, BR-PQ-13, BR-LO-03, BR-GV-03).

Dữ liệu hoàn toàn giả. Lô 10 kg, giá mua 81234 đ/kg (số giả để loss_amount = 812340).
"""
import datetime
import json
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup
from apps.common.cost_keys import COST_KEYS, redact_cost
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockReconciliation, Warehouse
from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation, Supplier

AUDIT_URL = "/api/audit-logs/"

# SR-01-AC3: các khoá tiền suy ra được giá vốn phải nằm trong COST_KEYS.
SR01_REQUIRED_KEYS = (
    "loss_amount", "loss", "inventory_value", "margin", "gross_profit",
    "expired_cost", "supplier_refund_amount", "supplier_return_cost",
)


def _keys_in(node, found=None):
    """Thu mọi khoá ở mọi độ sâu của JSON."""
    found = set() if found is None else found
    if isinstance(node, dict):
        for k, v in node.items():
            found.add(k)
            _keys_in(v, found)
    elif isinstance(node, list):
        for v in node:
            _keys_in(v, found)
    return found


class P8Sr01CostKeysScanTests(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(
            code="CA01", name="Cá nục giả", item_group=g, shelf_life_in_days=60, is_active=True,
        )
        self.sup = Supplier.objects.create(name="Cảng Giả", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho giả")

        self.chu = make_user("chu_sr01", "chu")
        self.ql = make_user("ql_sr01", "quan_ly")
        self.kho = make_user("kho_sr01", "nv_kho")
        self.giao = make_user("giao_sr01", "nv_giao")
        self.cskh = make_user("cskh_sr01", "cskh")

        # Lô 10 kg, giá mua 81234, EXPIRED.
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.localdate() - datetime.timedelta(days=70),
            qty=Decimal("10"), purchase_rate=Decimal("81234"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED)
        self.batch.refresh_from_db()

    # -- SR-01-AC1/AC2: cancel_expired_batch ---------------------------------

    def _cancel_expired(self):
        batch_services.cancel_expired_batch(
            batch=Batch.objects.get(pk=self.batch.pk), actor=self.chu,
        )

    def test_sr01_ac1_quan_ly_khong_thay_loss_amount(self):
        self._cancel_expired()
        # Bản ghi gốc trong DB vẫn có loss_amount (không đổi dữ liệu, AC4).
        raw = AuditLog.objects.get(action="cancel_expired_batch")
        self.assertIn("loss_amount", raw.changes)

        resp = client_for(self.ql).get(AUDIT_URL, {"action": "cancel_expired_batch"})
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        changes = results[0]["changes"]
        self.assertNotIn("loss_amount", changes)
        # Chỉ tìm sentinel trong changes/note (toàn bộ JSON có timestamp micro giây, có thể trùng ngẫu nhiên).
        self.assertNotIn("812340", json.dumps([[r["changes"], r["note"]] for r in results]))
        # Khoá không nhạy cảm cùng dòng vẫn còn.
        self.assertIn("status", changes)
        self.assertIn("qty", changes)

    def test_sr01_ac2_chu_thay_du_loss_amount(self):
        self._cancel_expired()
        resp = client_for(self.chu).get(AUDIT_URL, {"action": "cancel_expired_batch"})
        self.assertEqual(resp.status_code, 200)
        changes = resp.json()["results"][0]["changes"]
        self.assertIn("loss_amount", changes)
        self.assertEqual(Decimal(str(changes["loss_amount"])), Decimal("812340"))

    # -- SR-01-AC3: quét mọi dòng audit liên quan tiền -----------------------

    def _run_money_services(self):
        """Chạy các service ghi audit có số tiền: recompute -> cancel_expired -> close."""
        batch = Batch.objects.get(pk=self.batch.pk)
        # 1) recompute_landed_cost: thêm chi phí phân bổ 200000 -> giá vốn 101234.
        cost = PurchaseCost.objects.create(
            cost_type=PurchaseCost.CostType.TRANSPORT, amount=Decimal("200000"),
            incurred_date=timezone.localdate(), created_by=self.chu,
        )
        PurchaseCostAllocation.objects.create(
            purchase_cost=cost, batch=batch, allocated_amount=Decimal("200000"),
        )
        batch_services.recompute_landed_cost(batch=batch, actor=self.chu)
        # 2) cancel_expired_batch: loss_amount = 10 * 101234 = 1012340.
        batch_services.cancel_expired_batch(batch=Batch.objects.get(pk=batch.pk), actor=self.chu)
        # 3) close_batch: cần kiểm kê đã duyệt (BR-KK-05).
        rec = StockReconciliation.objects.create(
            count_date=timezone.localdate(), created_by=self.chu, approved_by=self.chu,
            status=StockReconciliation.Status.APPROVED, approved_at=timezone.now(),
        )
        rec.lines.create(batch=batch, system_qty=Decimal("0"), counted_qty=Decimal("0"))
        batch_services.close_batch(batch=Batch.objects.get(pk=batch.pk), actor=self.chu)

    def test_sr01_ac3_quet_khoa_tien_quan_ly_khong_thay_gia_von(self):
        self._run_money_services()

        # Chống test xanh giả: các dòng audit cần quét có thật, và DB thật sự có khoá nhạy cảm.
        expected_actions = {"recompute_landed_cost", "cancel_expired_batch", "close_batch"}
        db_rows = AuditLog.objects.filter(action__in=expected_actions)
        self.assertEqual({r.action for r in db_rows}, expected_actions)
        raw_keys = set()
        for r in db_rows:
            _keys_in(r.changes, raw_keys)
        self.assertTrue(raw_keys & COST_KEYS, "Fixture không có khoá giá vốn nào -> test vô nghĩa")
        self.assertIn("loss_amount", raw_keys)

        client = client_for(self.ql)
        ok_responses = 0
        seen_actions = set()
        leaked_keys = set()
        blob = ""  # chỉ gồm changes + note của từng dòng (không gồm created_at)
        url_params = {}
        while True:
            resp = client.get(AUDIT_URL, url_params)
            if resp.status_code == 200:
                ok_responses += 1
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            blob += json.dumps([[r["changes"], r["note"]] for r in data["results"]])
            for row in data["results"]:
                seen_actions.add(row["action"])
                leaked_keys |= _keys_in(row["changes"]) & COST_KEYS
            if not data.get("next"):
                break
            url_params = {"page": (url_params.get("page") or 1) + 1}
        self.assertGreater(ok_responses, 0)
        self.assertTrue(expected_actions <= seen_actions)
        self.assertEqual(leaked_keys, set(), f"quan_ly thấy khoá giá vốn: {leaked_keys}")
        for sentinel in ("81234", "101234", "1012340", "812340"):
            self.assertNotIn(sentinel, blob)

        # Chủ vẫn thấy đủ (AC2).
        chu_blob = json.dumps(client_for(self.chu).get(AUDIT_URL).json())
        self.assertIn("1012340", chu_blob)

    def test_sr01_ac3_cost_keys_co_du_khoa_tien(self):
        missing = [k for k in SR01_REQUIRED_KEYS if k not in COST_KEYS]
        self.assertEqual(missing, [])

    def test_sr01_ac3_redact_cost_bo_khoa_tien_o_moi_do_sau(self):
        payload = {
            "status": {"from": "EXPIRED", "to": "CANCELLED"},
            "detail": [{k: 1 for k in SR01_REQUIRED_KEYS} | {"qty": 2}],
        }
        out = redact_cost(payload)
        self.assertEqual(out, {"status": {"from": "EXPIRED", "to": "CANCELLED"}, "detail": [{"qty": 2}]})
        # Input không bị sửa.
        self.assertIn("loss_amount", payload["detail"][0])

    # -- Ma trận Group --------------------------------------------------------

    def test_sr01_ma_tran_group(self):
        self._cancel_expired()
        for user in (self.kho, self.giao, self.cskh):
            self.assertEqual(client_for(user).get(AUDIT_URL).status_code, 403)
        self.assertEqual(client_for(None).get(AUDIT_URL).status_code, 401)
        self.assertEqual(client_for(self.chu).get(AUDIT_URL).status_code, 200)
        self.assertEqual(client_for(self.ql).get(AUDIT_URL).status_code, 200)

    # -- AC4: append-only ------------------------------------------------------

    def test_sr01_ac4_khong_sua_auditlog_trong_db(self):
        self._cancel_expired()
        before = AuditLog.objects.get(action="cancel_expired_batch")
        snapshot = json.dumps(before.changes, default=str, sort_keys=True)
        client_for(self.ql).get(AUDIT_URL)
        after = AuditLog.objects.get(pk=before.pk)
        self.assertEqual(json.dumps(after.changes, default=str, sort_keys=True), snapshot)
        self.assertIn("loss_amount", after.changes)
