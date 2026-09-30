"""
P8 Lô 2 — SR-06 (BM-03, BR-GH-18, BR-PQ-12, Tầng 3): guidance đơn + escalate dùng CHUNG phạm vi
với danh sách/chi tiết đơn (`scope_orders_for`). Dữ liệu chỉ là giả.

Ma trận `GET /api/guidance/order/<mã>/`:
  chu/quan_ly/nv_kho: 200 mọi đơn · nv_giao: 200 đơn của phiếu mình, 404 đơn khác ·
  cskh: 200 đơn trong phạm vi gọi, 404 đơn ngoài · user gán quyền trực tiếp (không Group): như
  SalesOrderViewSet (chỉ đơn của phiếu gán cho mình) · khách: 401.
"""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.models import AiAction
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.scope import scope_orders_for
from apps.sales.payments import services as payment_services


@override_settings(AI_ENABLED=True)
class OrderScopeBase(TestCase):
    def setUp(self):
        grp = ItemGroup.objects.create(name="Hải sản")
        self.sup = Supplier.objects.create(name="Đầu mối Giả")
        self.wh = Warehouse.objects.create(name="Kho Giả")
        pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        today = timezone.localdate()
        self.item = Item.objects.create(code="CA-GIA-2", name="Cá giả 2", item_group=grp)
        ItemPrice.objects.create(
            price_list=pl, item=self.item, rate=Decimal("150000"),
            valid_from=today - datetime.timedelta(days=1),
        )
        batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=today,
            qty=Decimal("100"), purchase_rate=Decimal("110000"),
        )
        batch_services.publish_batch(batch=batch, actor=None)

        self.chu = make_user("sc_chu", "chu")
        self.ql = make_user("sc_ql", "quan_ly")
        self.kho = make_user("sc_kho", "nv_kho")
        self.giao = make_user("sc_giao", "nv_giao")
        self.giao2 = make_user("sc_giao2", "nv_giao")
        self.cskh = make_user("sc_cskh", "cskh")
        # Gán quyền trực tiếp, không thuộc Group nào (AC3)
        self.direct = make_user("sc_direct", perms=("sales.view_salesorder",))

        # Đơn TRONG phạm vi cskh: đã thanh toán -> phiếu CONFIRMING + task PENDING.
        self.in_order = self._paid_order("0900000201")
        # Đơn NGOÀI phạm vi cskh: mới giữ chỗ, chưa có phiếu giao. Mã cố định như story.
        self.out_order = self._order("0900000202")
        SalesOrder.objects.filter(pk=self.out_order.pk).update(code="DH-OUT-1")
        self.out_order.refresh_from_db()

    def _order(self, phone):
        return order_services.create_order(
            customer_phone=phone, customer_name="Khách Giả A", delivery_address="Số 1 Đường Giả",
            phone=phone, lines=[{"item_code": self.item.code, "qty": Decimal("1")}],
        )

    def _paid_order(self, phone):
        order = self._order(phone)
        payment_services.confirm_payment(
            order=order, bank_txn_id=f"FTGIA{order.pk}", amount=order.total_amount,
            received_at=timezone.now(),
        )
        order.refresh_from_db()
        return order

    def _note(self, order):
        return DeliveryNote.objects.get(sales_invoice__sales_order=order)

    def guidance(self, user, order):
        return client_for(user).get(f"/api/guidance/order/{order.code}/")

    def detail(self, user, order):
        return client_for(user).get(f"/api/sales/orders/{order.pk}/")


class GuidanceOrderScopeTests(OrderScopeBase):
    def test_sr06_ac1_cskh_don_ngoai_pham_vi_404(self):
        """SR-06-AC1 (đỏ trước: hiện 200): cskh xem guidance đơn ngoài phạm vi -> 404;
        chi tiết đơn vẫn 404."""
        res = self.guidance(self.cskh, self.out_order)
        self.assertEqual(res.status_code, 404, res.content[:200])
        self.assertEqual(self.detail(self.cskh, self.out_order).status_code, 404)

    def test_sr06_ac1_body_404_khong_lo_thong_tin(self):
        res = self.guidance(self.cskh, self.out_order)
        self.assertEqual(res.status_code, 404)
        self.assertNotIn("DH-OUT-1", res.content.decode())
        self.assertIn("Không tìm thấy đơn hàng", res.json()["detail"])

    def test_sr06_ac3_cskh_don_trong_pham_vi_200(self):
        res = self.guidance(self.cskh, self.in_order)
        self.assertEqual(res.status_code, 200, res.content[:200])
        self.assertEqual(res.json()["doc"]["code"], self.in_order.code)
        self.assertEqual(self.detail(self.cskh, self.in_order).status_code, 200)

    def test_sr06_ac3_cskh_het_pham_vi_khi_task_xong_va_chua_goi(self):
        """Khi phiếu rời hàng chờ (task DONE, phiếu PREPARING) và cskh chưa gọi -> 404 như danh sách đơn."""
        note = self._note(self.in_order)
        note.status = DeliveryNote.Status.PREPARING
        note.save(update_fields=["status"])
        ConfirmationTask.objects.filter(note=note).update(state=ConfirmationTask.State.DONE)
        self.assertEqual(self.guidance(self.cskh, self.in_order).status_code, 404)
        self.assertEqual(self.detail(self.cskh, self.in_order).status_code, 404)

    def test_sr06_ac3_nv_giao_chi_thay_don_cua_phieu_minh(self):
        note = self._note(self.in_order)
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])
        self.assertEqual(self.guidance(self.giao, self.in_order).status_code, 200)
        self.assertEqual(self.guidance(self.giao2, self.in_order).status_code, 404)
        self.assertEqual(self.guidance(self.giao, self.out_order).status_code, 404)

    def test_sr06_ac3_user_gan_quyen_truc_tiep_theo_pham_vi_viewset(self):
        """Không thuộc Group nào nhưng có view_salesorder: chỉ đơn của phiếu gán cho mình,
        y như SalesOrderViewSet (trước đây guidance trả 200 cho mọi đơn)."""
        self.assertEqual(self.guidance(self.direct, self.in_order).status_code, 404)
        self.assertEqual(self.detail(self.direct, self.in_order).status_code, 404)
        note = self._note(self.in_order)
        note.assigned_to = self.direct
        note.save(update_fields=["assigned_to"])
        self.assertEqual(self.guidance(self.direct, self.in_order).status_code, 200)
        self.assertEqual(self.detail(self.direct, self.in_order).status_code, 200)

    def test_sr06_ac3_chu_ql_kho_thay_moi_don(self):
        for user in (self.chu, self.ql, self.kho):
            for order in (self.in_order, self.out_order):
                res = self.guidance(user, order)
                self.assertEqual(res.status_code, 200, f"{user.username} {order.code}")

    def test_sr06_ma_tran_khach_401_va_thieu_quyen_403(self):
        res = client_for(None).get(f"/api/guidance/order/{self.in_order.code}/")
        self.assertEqual(res.status_code, 401)
        nobody = make_user("sc_nobody")
        self.assertEqual(self.guidance(nobody, self.in_order).status_code, 403)

    def test_sr06_ac3_guidance_khong_lo_pii_khach(self):
        """Đơn trong phạm vi: response guidance không chứa tên/SĐT/địa chỉ khách."""
        raw = self.guidance(self.cskh, self.in_order).content.decode()
        for s in ("Khách Giả A", "0900000201", "Số 1 Đường Giả"):
            self.assertNotIn(s, raw)


class EscalateOrderScopeTests(OrderScopeBase):
    def _escalate(self, user, order, step_key="confirm_payment_manual"):
        return client_for(user).post(
            "/api/ai/actions/escalate/",
            {"doc_type": "order", "doc_id": order.code, "step_key": step_key}, format="json",
        )

    def test_sr06_ac2_cskh_escalate_don_ngoai_pham_vi_404(self):
        """SR-06-AC2 (đỏ trước: hiện 400 DOC_NOT_FOUND): đơn ngoài phạm vi -> 404, không AiAction,
        body không in nguyên văn exception."""
        before = AiAction.objects.count()
        res = self._escalate(self.cskh, self.out_order)
        self.assertEqual(res.status_code, 404, res.content[:300])
        self.assertEqual(AiAction.objects.count(), before)
        self.assertNotIn("DH-OUT-1", res.content.decode())
        self.assertNotIn("Không thể nạp", res.content.decode())

    def test_sr06_ac2_nv_giao_escalate_don_khac_404(self):
        res = self._escalate(self.giao, self.out_order)
        self.assertEqual(res.status_code, 404, res.content[:300])

    def test_sr06_ac2_thieu_quyen_xem_don_403(self):
        """Thiếu view_salesorder -> 403 (không bị đổi thành 400)."""
        nobody = make_user("sc_nobody2")
        res = self._escalate(nobody, self.in_order)
        self.assertEqual(res.status_code, 403, res.content[:300])

    def test_sr06_ac2_don_trong_pham_vi_van_di_qua_provider(self):
        """Đơn trong phạm vi: không còn là 404; lỗi bước (nếu có) vẫn là 400 nghiệp vụ, không phải 404/500."""
        res = self._escalate(self.cskh, self.in_order, step_key="khong_ton_tai")
        self.assertEqual(res.status_code, 400, res.content[:300])
        self.assertEqual(res.json()["code"], "STEP_NOT_FOUND")


class ScopeOrdersForTests(OrderScopeBase):
    """SR-06-AC4: hàm dùng chung; SalesOrderViewSet.list cho kết quả y như hàm."""

    def _list_ids(self, user):
        res = client_for(user).get("/api/sales/orders/")
        self.assertEqual(res.status_code, 200)
        return {row["id"] for row in res.json()["results"]}

    def test_sr06_ac4_scope_orders_for_khop_danh_sach_don(self):
        note = self._note(self.in_order)
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])
        for user in (self.chu, self.ql, self.kho, self.giao, self.giao2, self.cskh, self.direct):
            expected = set(scope_orders_for(user, SalesOrder.objects.all()).values_list("pk", flat=True))
            if user.has_perm("sales.view_salesorder"):
                self.assertEqual(self._list_ids(user), expected, user.username)

    def test_sr06_ac4_scope_orders_for_khong_trung_dong(self):
        """Đơn có nhiều phiếu giao cùng gán cho 1 người vẫn chỉ xuất hiện 1 lần (distinct)."""
        qs = scope_orders_for(self.cskh, SalesOrder.objects.all())
        pks = list(qs.values_list("pk", flat=True))
        self.assertEqual(len(pks), len(set(pks)))
