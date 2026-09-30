"""
GL-05 / BR-PQ / Bất biến 9: Xem bằng chứng đồng ý xử lý dữ liệu của đơn trên ERP.

- GL-05-AC1: Chủ và Quản lý xem chi tiết đơn có consent -> response có `privacy_consent` đủ 4 khoá
             (accepted_at, policy_entry_id, policy_version, policy_version_id).
- GL-05-AC2: Đơn tạo trước ngày áp dụng (không có consent) -> `privacy_consent` là null.
- GL-05-AC3: NV kho, NV giao xem chi tiết đơn -> response KHÔNG CÓ khoá `privacy_consent` ở mọi độ sâu.
- Phân quyền: Quyền `sales.view_privacy_consent` chỉ gán cho Group `chu` và `quan_ly`.
- Danh sách đơn: `SalesOrderListSerializer` (GET /api/sales/orders/) không chứa khoá `privacy_consent`.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.tests.fixtures import client_for, make_user
from apps.content.models import Entry, EntryVersion
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, SalesOrder, SalesOrderLine
from apps.sales.orders import services as order_services
from apps.accounts import roles


def find_key(data, target_key):
    """Quét đệ quy JSON tìm target_key ở bất kỳ độ sâu nào."""
    if isinstance(data, dict):
        if target_key in data:
            return True
        return any(find_key(v, target_key) for v in data.values())
    if isinstance(data, list):
        return any(find_key(item, target_key) for item in data)
    return False


class PrivacyConsentViewTests(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Hải sản")
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        self.today = timezone.localdate()

        self.item = Item.objects.create(code="CA-HOI-1", name="Cá hồi Nauy", item_group=self.g)
        ItemPrice.objects.create(
            price_list=self.pl, item=self.item, rate=Decimal("300000"),
            valid_from=self.today - datetime.timedelta(days=1), valid_upto=None,
        )
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=self.today,
            qty=Decimal("100"), purchase_rate=Decimal("200000"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)

        self.customer = Customer.objects.create(name="Khách Thử Nghiệm", phone="0912345678")

        # Tạo trang chính sách và đăng bằng publish_entry
        author = make_user("editor_consent", roles.MANAGER)
        self.entry = Entry.objects.create(
            kind="page",
            title="Chính sách bảo mật",
            slug="chinh-sach-bao-mat",
            excerpt="Chính sách bảo mật",
            page_role="privacy",
            body={"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Chính sách v1"}]}]},
            created_by=author,
        )
        from apps.content.entries.services import publish_entry
        publish_entry(
            entry=self.entry,
            actor=author,
            row_version=self.entry.row_version,
            checklist_confirmed=True,
            acknowledge_warnings=True,
        )
        self.entry.refresh_from_db()
        self.version = self.entry.published_version

        # Tạo đơn có consent
        self.order_with_consent = order_services.create_order(
            customer_phone="0912345678",
            customer_name="Khách Thử Nghiệm",
            phone="0912345678",
            delivery_address="123 Đường Thử",
            lines=[{"item_code": self.item.code, "qty": Decimal("1.0")}],
            privacy_consent={"accepted": True, "policy_version_id": self.version.pk},
        )

        # Tạo đơn cũ không có consent
        self.order_without_consent = order_services.create_order(
            customer_phone="0912345678",
            customer_name="Khách Thử Nghiệm",
            phone="0912345678",
            delivery_address="456 Đường Thử",
            lines=[{"item_code": self.item.code, "qty": Decimal("1.0")}],
        )

        # Tạo các users theo nhóm
        self.u_chu = make_user("chu_view_consent", roles.OWNER)
        self.u_quanly = make_user("quanly_view_consent", roles.MANAGER)
        self.u_nvkho = make_user("nvkho_view_consent", roles.WAREHOUSE_STAFF)
        self.u_nvgiao = make_user("nvgiao_view_consent", roles.DELIVERY_STAFF)

        # Thanh toán đơn có consent để tự sinh invoice + delivery note, sau đó gán cho u_nvgiao
        from apps.sales.payments import services as payment_services
        payment_services.confirm_payment(
            order=self.order_with_consent,
            bank_txn_id="FT_CONSENT_01",
            amount=self.order_with_consent.total_amount,
            received_at=timezone.now(),
        )
        self.order_with_consent.refresh_from_db()
        DeliveryNote.objects.filter(sales_invoice=self.order_with_consent.invoice).update(
            assigned_to=self.u_nvgiao
        )

    def test_group_permissions_after_migration(self):
        """Kiểm tra quyền sales.view_privacy_consent được gán đúng cho chu, quan_ly; nv_kho, nv_giao không có."""
        perm = Permission.objects.get(content_type__app_label="sales", codename="view_privacy_consent")
        g_chu = Group.objects.get(name=roles.OWNER)
        g_ql = Group.objects.get(name=roles.MANAGER)
        g_kho = Group.objects.get(name=roles.WAREHOUSE_STAFF)
        g_giao = Group.objects.get(name=roles.DELIVERY_STAFF)

        self.assertIn(perm, g_chu.permissions.all())
        self.assertIn(perm, g_ql.permissions.all())
        self.assertNotIn(perm, g_kho.permissions.all())
        self.assertNotIn(perm, g_giao.permissions.all())

    def test_gl05_ac1_chu_sees_privacy_consent(self):
        """GL-05-AC1: Chủ mở chi tiết đơn có consent -> 200, có đủ 4 khoá consent."""
        c = client_for(self.u_chu)
        resp = c.get(f"/api/sales/orders/{self.order_with_consent.pk}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("privacy_consent", data)
        consent = data["privacy_consent"]
        self.assertIsNotNone(consent)
        self.assertEqual(consent["policy_entry_id"], self.entry.pk)
        self.assertEqual(consent["policy_version"], self.version.version)
        self.assertEqual(consent["policy_version_id"], self.version.pk)
        self.assertIsNotNone(consent["accepted_at"])

    def test_gl05_ac1_quan_ly_sees_privacy_consent(self):
        """GL-05-AC1: Quản lý mở chi tiết đơn có consent -> 200, có đủ 4 khoá consent."""
        c = client_for(self.u_quanly)
        resp = c.get(f"/api/sales/orders/{self.order_with_consent.pk}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("privacy_consent", data)
        consent = data["privacy_consent"]
        self.assertIsNotNone(consent)
        self.assertEqual(consent["policy_entry_id"], self.entry.pk)
        self.assertEqual(consent["policy_version"], self.version.version)
        self.assertEqual(consent["policy_version_id"], self.version.pk)
        self.assertIsNotNone(consent["accepted_at"])

    def test_gl05_ac2_order_without_consent_returns_null(self):
        """GL-05-AC2: Đơn tạo trước ngày áp dụng -> response có `"privacy_consent": null`."""
        c = client_for(self.u_chu)
        resp = c.get(f"/api/sales/orders/{self.order_without_consent.pk}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("privacy_consent", data)
        self.assertIsNone(data["privacy_consent"])

    def test_gl05_ac3_nv_kho_does_not_see_privacy_consent_key(self):
        """GL-05-AC3: NV kho mở chi tiết đơn -> response KHÔNG CÓ khoá privacy_consent ở mọi độ sâu."""
        c = client_for(self.u_nvkho)
        resp = c.get(f"/api/sales/orders/{self.order_with_consent.pk}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(find_key(data, "privacy_consent"), "NV kho không được thấy khoá privacy_consent")

    def test_gl05_ac3_nv_giao_does_not_see_privacy_consent_key(self):
        """GL-05-AC3: NV giao (được gán phiếu) mở chi tiết đơn -> response KHÔNG CÓ khoá privacy_consent ở mọi độ sâu."""
        c = client_for(self.u_nvgiao)
        resp = c.get(f"/api/sales/orders/{self.order_with_consent.pk}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(find_key(data, "privacy_consent"), "NV giao không được thấy khoá privacy_consent")

    def test_order_list_does_not_have_privacy_consent_key(self):
        """Danh sách đơn GET /api/sales/orders/ tuyệt đối không chứa khoá privacy_consent với bất kỳ ai."""
        for u in [self.u_chu, self.u_quanly, self.u_nvkho]:
            c = client_for(u)
            resp = c.get("/api/sales/orders/")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            results = data.get("results", data)
            self.assertFalse(find_key(results, "privacy_consent"), f"Danh sách đơn chứa privacy_consent với {u.username}")
