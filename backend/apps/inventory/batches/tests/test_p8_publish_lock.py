"""
P8 Lô 3 — SR-10: mở bán lô có khoá, không mở bán lô của phiếu đã huỷ (F05, BR-MH-05, DW-18-AC4).
Chuyển từ test tái hiện R3 (repro/review_repro_tests.py). Dữ liệu giả.

- SR-10-AC1: lô DRAFT do phiếu nhập tạo, object cũ, cancel_receipt chạy xong, publish_batch(object cũ) -> 400 BR-MH-05.
- SR-10-AC2: publish_batch trong atomic + select_for_update().get(pk) rồi mới kiểm DRAFT; publish lần 2 -> 400.
- SR-10-AC3: luồng thuận DRAFT -> SELLING, AuditLog publish_batch.
- Ma trận Group: chu 200/400, quan_ly 200/400, nv_kho/nv_giao/cskh 403, khách 401.
"""
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.cost_keys import COST_KEYS
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.tests.test_cskh_l3 import ConfirmationL3BaseTestCase
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch
from apps.purchasing.models import PurchaseReceipt
from apps.purchasing.receipts import services as receipt_services
from apps.sales.orders.tests.test_s10_api import find_keys
from apps.accounts import roles


class SR10PublishLockTests(ConfirmationL3BaseTestCase):
    def setUp(self):
        super().setUp()
        self.giao = make_user("giao_sr10", roles.DELIVERY_STAFF)
        self.receipt, batches = receipt_services.create_and_submit_receipt(
            supplier=self.sup, warehouse=self.wh, received_date=timezone.localdate(),
            lines=[{"item_code": self.item, "qty": Decimal("5"), "rate": Decimal("1000")}],
            actor=self.kho,
        )
        self.draft_pk = batches[0].pk

    def _publish_audits(self, pk):
        return AuditLog.objects.filter(action="publish_batch", object_id=str(pk)).count()

    # --- AC1 (R3) ------------------------------------------------------------
    def test_sr10_ac1_r3_publish_object_cu_sau_khi_huy_phieu_bi_chan(self):
        stale = Batch.objects.get(pk=self.draft_pk)  # get_object() của request publish
        self.assertEqual(stale.status, Batch.Status.DRAFT)
        receipt_services.cancel_receipt(receipt=self.receipt, actor=self.kho)  # request huỷ xong trước

        with self.assertRaises(BusinessError) as ctx:
            batch_services.publish_batch(batch=stale, actor=self.chu)
        self.assertEqual(ctx.exception.code, "BR-MH-05")

        fresh = Batch.objects.get(pk=self.draft_pk)
        self.assertNotEqual(fresh.status, Batch.Status.SELLING)
        self.assertEqual(fresh.status, Batch.Status.CANCELLED)
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.status, PurchaseReceipt.Status.CANCELLED)
        self.assertEqual(self._publish_audits(self.draft_pk), 0)

    def test_sr10_ac1_api_publish_lo_da_huy_400_br_mh_05(self):
        receipt_services.cancel_receipt(receipt=self.receipt, actor=self.kho)
        resp = client_for(self.chu).post(f"/api/inventory/batches/{self.draft_pk}/publish/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-MH-05")
        self.assertEqual(Batch.objects.get(pk=self.draft_pk).status, Batch.Status.CANCELLED)

    # --- AC2 -----------------------------------------------------------------
    def test_sr10_ac2_doc_lai_co_khoa_dong_roi_moi_kiem_draft(self):
        stale = Batch.objects.get(pk=self.draft_pk)
        real = Batch.objects.select_for_update
        with mock.patch.object(Batch.objects, "select_for_update", wraps=real) as spy:
            batch_services.publish_batch(batch=stale, actor=self.chu)
        spy.assert_called_once_with()
        self.assertEqual(Batch.objects.get(pk=self.draft_pk).status, Batch.Status.SELLING)

    def test_sr10_ac2_publish_lan_2_400(self):
        stale = Batch.objects.get(pk=self.draft_pk)
        batch_services.publish_batch(batch=stale, actor=self.chu)
        with self.assertRaises(BusinessError) as ctx:
            batch_services.publish_batch(batch=stale, actor=self.chu)  # object cũ vẫn DRAFT trong bộ nhớ
        self.assertEqual(ctx.exception.code, "BR-MH-05")
        self.assertEqual(self._publish_audits(self.draft_pk), 1)

    def test_sr10_ac2_object_cu_khong_bi_ghi_de_trang_thai_tren_lo_da_huy(self):
        """Lô đã huỷ, object cũ ghi DRAFT: không được save() đè status cũ hay tồn cũ."""
        stale = Batch.objects.get(pk=self.draft_pk)
        receipt_services.cancel_receipt(receipt=self.receipt, actor=self.kho)
        with self.assertRaises(BusinessError):
            batch_services.publish_batch(batch=stale, actor=self.chu)
        fresh = Batch.objects.get(pk=self.draft_pk)
        self.assertEqual(fresh.qty_available, Decimal("0.000"))
        self.assertEqual(fresh.status, Batch.Status.CANCELLED)

    # --- AC3 -----------------------------------------------------------------
    def test_sr10_ac3_luong_thuan_draft_sang_selling_co_audit(self):
        b = batch_services.publish_batch(batch=Batch.objects.get(pk=self.draft_pk), actor=self.chu)
        self.assertEqual(b.status, Batch.Status.SELLING)
        self.assertEqual(Batch.objects.get(pk=self.draft_pk).status, Batch.Status.SELLING)
        self.assertEqual(self._publish_audits(self.draft_pk), 1)
        audit = AuditLog.objects.get(action="publish_batch", object_id=str(self.draft_pk))
        self.assertEqual(audit.actor, self.chu)

    # --- Ma trận Group -------------------------------------------------------
    def test_sr10_ma_tran_group_publish(self):
        url = f"/api/inventory/batches/{self.draft_pk}/publish/"
        for user in (self.kho, self.giao, self.cs1):
            with self.subTest(user=user.username):
                self.assertEqual(client_for(user).post(url).status_code, 403)
        self.assertEqual(client_for(None).post(url).status_code, 401)
        self.assertEqual(Batch.objects.get(pk=self.draft_pk).status, Batch.Status.DRAFT)

        resp = client_for(self.ql).post(url)  # quan_ly: 200 khi hợp lệ
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], Batch.Status.SELLING)
        # không rò giá vốn cho quan_ly
        self.assertFalse(find_keys(resp.json(), set(COST_KEYS)))
        # publish lại (chu) -> 400 nghiệp vụ
        again = client_for(self.chu).post(url)
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.json()["code"], "BR-MH-05")

    def test_sr10_ma_tran_group_chu_200(self):
        resp = client_for(self.chu).post(f"/api/inventory/batches/{self.draft_pk}/publish/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], Batch.Status.SELLING)
