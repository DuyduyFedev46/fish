"""
S2 — Job hằng ngày cập nhật trạng thái lô (BR-LO-01/02/06, BR-PQ-04).

Command `update_batch_status`, actor = None (Hệ thống), idempotent.
"""
import datetime
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier

S = Batch.Status


@override_settings(BATCH_NEAR_EXPIRY_DAYS=14)
class S2JobTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="X", name="Cá X", item_group=g)
        self.sup = Supplier.objects.create(name="A")
        self.wh = Warehouse.objects.create(name="Kho")

    def _batch(self, *, days_left, status=S.SELLING, qty="5", reserved="0"):
        b = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=self.today - datetime.timedelta(days=5),
            qty=Decimal(qty), purchase_rate=Decimal("80000"),
        )
        Batch.objects.filter(pk=b.pk).update(
            expiry_date=self.today + datetime.timedelta(days=days_left),
            status=status, qty_reserved=Decimal(reserved),
        )
        b.refresh_from_db()
        return b

    def _run(self):
        out = StringIO()
        call_command("update_batch_status", stdout=out)
        return out.getvalue()

    def _logs(self, batch, action=None):
        qs = AuditLog.objects.filter(model_name="inventory.Batch", object_id=str(batch.pk))
        return qs.filter(action=action) if action else qs

    def test_s2_ac1_con_14_ngay_chuyen_can_han_va_ghi_audit_he_thong(self):
        b = self._batch(days_left=14)
        far = self._batch(days_left=15)
        self._run()
        b.refresh_from_db()
        far.refresh_from_db()
        self.assertEqual(b.status, S.NEAR_EXPIRY)
        self.assertEqual(far.status, S.SELLING)
        logs = self._logs(b, "batch_near_expiry")
        self.assertEqual(logs.count(), 1)
        self.assertIsNone(logs.first().actor)
        self.assertEqual(logs.first().changes["status"], {"from": "SELLING", "to": "NEAR_EXPIRY"})
        self.assertEqual(self._logs(far).count(), 0)

    @override_settings(BATCH_NEAR_EXPIRY_DAYS=3)
    def test_s2_ac1_nguong_can_han_doc_tu_settings(self):
        b = self._batch(days_left=10)
        self._run()
        b.refresh_from_db()
        self.assertEqual(b.status, S.SELLING)

    def test_s2_ac2_han_hom_qua_chuyen_qua_han(self):
        lots = [self._batch(days_left=-1, status=st) for st in (S.SELLING, S.NEAR_EXPIRY, S.DRAFT)]
        today_lot = self._batch(days_left=0)  # hạn = hôm nay: ngày cuối còn bán (C1)
        self._run()
        for b in lots:
            b.refresh_from_db()
            self.assertEqual(b.status, S.EXPIRED)
            logs = self._logs(b, "batch_expired")
            self.assertEqual(logs.count(), 1)
            self.assertIsNone(logs.first().actor)
        today_lot.refresh_from_db()
        self.assertEqual(today_lot.status, S.NEAR_EXPIRY)

    def test_s2_ac3_het_ton_va_khong_giu_cho_thi_het_hang(self):
        b = self._batch(days_left=30, qty="0")
        reserved_all = self._batch(days_left=30, qty="2", reserved="2")
        self._run()
        b.refresh_from_db()
        reserved_all.refresh_from_db()
        self.assertEqual(b.status, S.SOLD_OUT)
        self.assertEqual(self._logs(b, "batch_sold_out").count(), 1)
        self.assertEqual(reserved_all.status, S.SELLING)  # còn giữ chỗ -> chưa hết hàng

    def test_s2_ac3_draft_ton_0_khong_bi_doi(self):
        b = self._batch(days_left=30, qty="0", status=S.DRAFT)
        self._run()
        b.refresh_from_db()
        self.assertEqual(b.status, S.DRAFT)

    def test_s2_ac4_het_hang_co_hang_hoan_quay_lai_ban(self):
        b = self._batch(days_left=30, qty="3", status=S.SOLD_OUT)
        near = self._batch(days_left=5, qty="3", status=S.SOLD_OUT)
        self._run()
        b.refresh_from_db()
        near.refresh_from_db()
        self.assertEqual(b.status, S.SELLING)
        self.assertEqual(near.status, S.NEAR_EXPIRY)
        self.assertEqual(self._logs(b, "batch_back_in_stock").count(), 1)
        self.assertEqual(self._logs(near, "batch_back_in_stock").count(), 1)

    def test_s2_ac4_het_hang_ton_0_da_qua_han_giu_nguyen(self):
        b = self._batch(days_left=-3, qty="0", status=S.SOLD_OUT)
        self._run()
        b.refresh_from_db()
        self.assertEqual(b.status, S.SOLD_OUT)

    def test_s2_ac5_chay_lan_hai_khong_doi_va_khong_them_audit(self):
        self._batch(days_left=14)
        self._batch(days_left=-1)
        self._batch(days_left=30, qty="0")
        self._batch(days_left=30, qty="3", status=S.SOLD_OUT)
        self._run()
        snapshot = list(Batch.objects.order_by("pk").values_list("pk", "status"))
        n_logs = AuditLog.objects.count()
        out = self._run()
        self.assertEqual(list(Batch.objects.order_by("pk").values_list("pk", "status")), snapshot)
        self.assertEqual(AuditLog.objects.count(), n_logs)
        self.assertIn("Đã cập nhật 0 lô", out)

    def test_s2_ac6_lo_da_chot_hoac_da_huy_khong_doi(self):
        closed = self._batch(days_left=-5, status=S.CLOSED, qty="0")
        cancelled = self._batch(days_left=-5, status=S.CANCELLED, qty="0")
        expired = self._batch(days_left=-5, status=S.EXPIRED)
        self._run()
        for b, st in ((closed, S.CLOSED), (cancelled, S.CANCELLED), (expired, S.EXPIRED)):
            b.refresh_from_db()
            self.assertEqual(b.status, st)
            self.assertEqual(self._logs(b).count(), 0)

    def test_s2_ac6_ket_qua_tra_ve_dem_so_lo_doi(self):
        self._batch(days_left=14)
        self._batch(days_left=-1)
        result = batch_services.update_batch_statuses()
        self.assertEqual(result, {S.NEAR_EXPIRY: 1, S.EXPIRED: 1})


class S2PermissionTests(TestCase):
    """S2-AC7: không có endpoint cho người dùng kích job (phần PATCH status thuộc S3)."""

    def test_s2_ac7_khong_co_endpoint_kich_job(self):
        g = ItemGroup.objects.create(name="Cá")
        item = Item.objects.create(code="X", name="Cá X", item_group=g)
        b = batch_services.create_batch(
            item=item, supplier=Supplier.objects.create(name="A"),
            warehouse=Warehouse.objects.create(name="Kho"),
            received_date=timezone.localdate() - datetime.timedelta(days=30),
            qty=Decimal("5"), purchase_rate=Decimal("80000"),
        )
        Batch.objects.filter(pk=b.pk).update(
            status=S.SELLING, expiry_date=timezone.localdate() - datetime.timedelta(days=1),
        )
        kho = User.objects.create_user("kho1", password="x")
        kho.groups.add(Group.objects.get(name="nv_kho"))
        client = APIClient()
        client.force_authenticate(kho)
        for url in (
            "/api/inventory/batches/update_status/",
            "/api/inventory/batches/update-status/",
            "/api/inventory/update_batch_status/",
            "/api/internal/update_batch_status/",
        ):
            self.assertIn(client.post(url, {}).status_code, (403, 404, 405), url)
        b.refresh_from_db()
        self.assertEqual(b.status, S.SELLING)  # không đường API nào chạy job
        self.assertFalse(AuditLog.objects.filter(action__startswith="batch_").exists())
