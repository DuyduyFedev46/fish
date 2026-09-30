"""
P8 Lô 2 — SR-04 (BM-02) + SR-05 (BM-06): quét toàn registry lệnh đọc bằng sentinel PII giả.

- SR-04-AC1: `reports.dashboard_summary` không lộ tên khách, kể cả với nv_kho.
- SR-04-AC3: gọi MỌI lệnh đọc (list và retrieve) x 5 Group; không response 200 nào chứa
  chuỗi PII; đếm response 200 và số retrieve thành công > 0 (chống xanh giả vì 4xx/5xx).
- SR-05-AC1/AC2/AC4: lệnh `*.retrieve` chạy đúng (detail=True), `batch_pnl` kèm target_id không 500.
Bất biến 9 (không rò dữ liệu cá nhân). Sentinel toàn là dữ liệu giả.
"""
import datetime
import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.policy.rules import SCRUB_PII_KEYS
from apps.ai.registry.discovery import get_registry
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import PaymentTransaction
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services

PII_NAME = "Khách Giả Bí Mật"
PII_PHONE = "0900000123"
PII_ADDR = "Số 1 Đường Giả"
PII_PAYER = "NGUYEN VAN GIA"
PII_STRINGS = (PII_NAME, PII_PHONE, PII_ADDR, PII_PAYER)

# Khoá bị coi là PII ở mọi đầu ra AI (02b §2.1): tập lọc hiện hành + nhánh khách/SĐT che.
PII_KEYS = set(SCRUB_PII_KEYS) | {
    "customer", "recipient_phone", "recipient_phone_masked", "phone_last4",
    "phone_masked", "customer_address",
}

GROUPS = ("chu", "quan_ly", "nv_kho", "nv_giao", "cskh")


def _find_keys(data, keys):
    found = set()
    if isinstance(data, dict):
        for k, v in data.items():
            if str(k).lower() in keys:
                found.add(str(k))
            found |= _find_keys(v, keys)
    elif isinstance(data, list):
        for v in data:
            found |= _find_keys(v, keys)
    return found


@override_settings(AI_ENABLED=True)
class PiiSweepBase(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Hải sản")
        self.sup = Supplier.objects.create(name="Đầu mối Giả")
        self.wh = Warehouse.objects.create(name="Kho Giả")
        self.pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        today = timezone.localdate()
        self.item = Item.objects.create(code="CA-GIA-1", name="Cá giả 1", item_group=g)
        ItemPrice.objects.create(
            price_list=self.pl, item=self.item, rate=Decimal("270000"),
            valid_from=today - datetime.timedelta(days=1), valid_upto=None,
        )
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=today,
            qty=Decimal("100"), purchase_rate=Decimal("180000"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)
        self.batch.refresh_from_db()

        self.users = {name: make_user(f"sweep_{name}", name) for name in GROUPS}
        self.clients = {name: client_for(u) for name, u in self.users.items()}

        # Đơn đã thanh toán (có hoá đơn, phiếu giao) + giao dịch mang tên người chuyển giả.
        self.order = order_services.create_order(
            customer_phone=PII_PHONE, customer_name=PII_NAME, delivery_address=PII_ADDR,
            phone=PII_PHONE, lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )
        payment_services.confirm_payment(
            order=self.order, bank_txn_id="FTGIA0001", amount=self.order.total_amount,
            received_at=timezone.now(),
            raw_payload={"content": f"{PII_PAYER} chuyen tien", "counter_account_name": PII_PAYER},
        )
        self.order.refresh_from_db()
        # Đơn thứ hai chưa thanh toán (giữ chỗ) để có dữ liệu ở nhiều trạng thái.
        self.order2 = order_services.create_order(
            customer_phone="0900000456", customer_name="Khách Giả B", delivery_address=PII_ADDR,
            phone="0900000456", lines=[{"item_code": self.item.code, "qty": Decimal("1")}],
        )

    def _call(self, group, command_id, body=None):
        return self.clients[group].post(
            f"/api/ai/commands/{command_id}/call/", body or {"args": {}}, format="json",
        )

    def _target_candidates(self):
        """Mọi khoá tra cứu có thể dùng làm target_id (pk và mã) của dữ liệu fixture."""
        inv = getattr(self.order, "invoice", None)
        cands = {"1", "2", str(self.order.pk), self.order.code, str(self.batch.pk),
                 self.batch.batch_id, str(self.item.pk), self.item.code}
        if inv is not None:
            cands |= {str(inv.pk), inv.code}
        return sorted(cands)


class SR04Dashboard(PiiSweepBase):
    def test_sr04_ac1_nv_kho_dashboard_khong_lo_ten_khach(self):
        """SR-04-AC1: nv_kho gọi reports.dashboard_summary -> không có tên/SĐT/địa chỉ khách."""
        res = self._call("nv_kho", "reports.dashboard_summary")
        self.assertEqual(res.status_code, 200, res.content[:300])
        raw = res.content.decode()
        for s in PII_STRINGS:
            self.assertNotIn(s, raw)
        self.assertEqual(_find_keys(res.json(), PII_KEYS), set())
        # Có dữ liệu thật (đơn gần đây) -> mã đơn vẫn hiện, không phải xanh giả vì rỗng.
        self.assertIn(self.order.code, raw)

    def test_sr04_ac1_chu_dashboard_khong_lo_ten_khach(self):
        res = self._call("chu", "reports.dashboard_summary")
        self.assertEqual(res.status_code, 200, res.content[:300])
        self.assertNotIn(PII_NAME, res.content.decode())
        self.assertEqual(_find_keys(res.json(), PII_KEYS), set())


class SR04SweepRegistry(PiiSweepBase):
    def test_sr04_ac3_quet_moi_lenh_doc_list_va_retrieve_5_group(self):
        """SR-04-AC3: mọi lệnh đọc (list + retrieve) x 5 Group -> 0 PII; retrieve thành công > 0."""
        specs = [s for s in get_registry().get_specs() if s.kind == "read"]
        self.assertGreater(len(specs), 0)
        ok_total = 0
        retrieve_ok = 0
        violations = []
        for spec in specs:
            for group in GROUPS:
                if spec.detail:
                    bodies = [{"args": {}, "target_id": t} for t in self._target_candidates()]
                else:
                    bodies = [{"args": {}}]
                for body in bodies:
                    res = self._call(group, spec.id, body)
                    self.assertLess(res.status_code, 500, f"{spec.id} {group} -> {res.status_code}")
                    if res.status_code != 200:
                        continue
                    ok_total += 1
                    if spec.detail and spec.action == "retrieve":
                        retrieve_ok += 1
                    raw = res.content.decode()
                    for s in PII_STRINGS:
                        if s in raw:
                            violations.append((spec.id, group, s))
                    for key in _find_keys(res.json(), PII_KEYS):
                        violations.append((spec.id, group, f"key:{key}"))
        if violations:
            self.fail(f"Lệnh AI rò PII: {sorted(set(violations))}")
        self.assertGreater(ok_total, 0, "Test quét không gọi được lệnh nào (xanh giả)")
        self.assertGreater(retrieve_ok, 0, "Không lệnh retrieve nào chạy được (xanh giả vì 4xx/5xx)")

    def test_sr04_ac3_retrieve_don_hang_chu_thanh_cong_khong_pii(self):
        """SR-04-AC3 + SR-05-AC1: chu retrieve đơn -> 200 có mã đơn, không PII."""
        res = self._call("chu", "sales.salesorder.retrieve", {"args": {}, "target_id": str(self.order.pk)})
        self.assertEqual(res.status_code, 200, res.content[:300])
        raw = res.content.decode()
        self.assertIn(self.order.code, raw)
        for s in PII_STRINGS:
            self.assertNotIn(s, raw)
        self.assertEqual(_find_keys(res.json(), PII_KEYS), set())

    def test_sr04_ac3_audit_ai_action_khong_chua_pii(self):
        """Sau khi quét: AiAction.args không chứa PII (BR-AI-09)."""
        self._call("chu", "sales.salesorder.retrieve", {"args": {}, "target_id": str(self.order.pk)})
        from apps.ai.models import AiAction
        blob = json.dumps(list(AiAction.objects.values_list("args", flat=True)), ensure_ascii=False)
        for s in PII_STRINGS:
            self.assertNotIn(s, blob)


class SR05Detail(PiiSweepBase):
    def test_sr05_ac1_chu_retrieve_lo_tra_du_lieu(self):
        """SR-05-AC1: chu gọi inventory.batch.retrieve {target_id: pk} -> 200 có dữ liệu lô."""
        res = self._call("chu", "inventory.batch.retrieve", {"args": {}, "target_id": str(self.batch.pk)})
        self.assertEqual(res.status_code, 200, res.content[:300])
        rows = res.json()["result"]["rows"]
        self.assertTrue(rows)
        self.assertIn(self.batch.batch_id, json.dumps(rows, ensure_ascii=False))

    def test_sr05_ac2_moi_lenh_retrieve_va_partial_update_co_detail(self):
        """SR-05-AC2: mọi lệnh sinh từ action chuẩn retrieve/partial_update có detail=True."""
        seen = 0
        for spec in get_registry().get_specs():
            if spec.action in ("retrieve", "partial_update", "update", "destroy"):
                seen += 1
                self.assertTrue(spec.detail, f"{spec.id} phải có detail=True")
                self.assertEqual(spec.target, "detail")
        self.assertGreater(seen, 0)

    def test_sr05_ac4_batch_pnl_kem_target_id_khong_500(self):
        """SR-05-AC4: reports.batch_pnl (APIView) kèm target_id (Chủ) -> 200 hoặc 4xx có thông điệp, không 500."""
        spec = get_registry().get("reports.batch_pnl")
        self.assertIsNotNone(spec)
        res = self._call("chu", "reports.batch_pnl", {"args": {}, "target_id": str(self.batch.pk)})
        self.assertLess(res.status_code, 500, res.content[:300])
        self.assertIn(res.status_code, (200, 400, 404))
        if res.status_code != 200:
            self.assertIn("detail", res.json())

    def test_sr05_ac3_nv_giao_de_xuat_partial_update_ngoai_pham_vi_404_khong_tao_ai_action(self):
        """SR-05-AC3: nv_giao đề xuất partial_update (mức C) với target_id ngoài phạm vi -> 404 NOT_FOUND,
        không tạo AiAction. (`sales.salesorder.partial_update` bị registry cấm hẳn theo H7 nên dùng
        `delivery.deliverynote.partial_update` — cùng cơ chế phạm vi phiếu gán cho mình, BR-PQ-12.)"""
        from apps.ai.models import AiAction
        from apps.delivery.models import DeliveryNote

        note = DeliveryNote.objects.get(sales_invoice__sales_order=self.order)
        self.assertIsNone(note.assigned_to)  # không gán cho nv_giao -> ngoài phạm vi
        spec = get_registry().get("delivery.deliverynote.partial_update")
        self.assertIsNotNone(spec)
        before = AiAction.objects.count()
        res = self._call("nv_giao", "delivery.deliverynote.partial_update",
                         {"args": {}, "target_id": str(note.pk)})
        self.assertEqual(res.status_code, 404, res.content[:300])
        self.assertEqual(res.json()["code"], "NOT_FOUND")
        self.assertEqual(AiAction.objects.count(), before)
        # Đối chứng: phiếu gán cho chính nv_giao -> đề xuất được tạo (không phải luôn 404).
        note.assigned_to = self.users["nv_giao"]
        note.save(update_fields=["assigned_to"])
        res2 = self._call("nv_giao", "delivery.deliverynote.partial_update",
                          {"args": {}, "target_id": str(note.pk)})
        self.assertEqual(res2.status_code, 200, res2.content[:300])
        self.assertEqual(res2.json()["outcome"], "proposal")

    def test_sr05_ac3_salesorder_partial_update_khong_ton_tai_trong_registry(self):
        """H7: sales.salesorder.partial_update vẫn bị cấm hẳn -> mọi Group nhận 404, không AiAction."""
        from apps.ai.models import AiAction
        self.assertIsNone(get_registry().get("sales.salesorder.partial_update"))
        for group in GROUPS:
            res = self._call(group, "sales.salesorder.partial_update",
                             {"args": {}, "target_id": str(self.order.pk)})
            self.assertEqual(res.status_code, 404, group)
        self.assertEqual(AiAction.objects.filter(command="sales.salesorder.partial_update").count(), 0)
