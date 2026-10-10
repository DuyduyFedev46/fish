"""
Ba vai trò trang bắt buộc mới: shipping, payment, complaints (SHOP-5-02 AC1–AC4; 02b §3.7.1; BR-ND-20, BR-ND-16, BR-PQ).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts import roles
from apps.common.exceptions import BusinessError
from apps.content.entries.services import (
    GOLIVE_PAGE_ROLES,
    golive_missing_roles,
    publish_entry,
    save_draft,
)
from apps.content.models.entries import Entry, EntryVersion

User = get_user_model()
NEW_ROLES = {
    "shipping": "Chính sách giao hàng",
    "payment": "Chính sách thanh toán",
    "complaints": "Cơ chế giải quyết khiếu nại",
}


def _body(text):
    return {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": text}]}]}


class RequiredPageRoleTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner_roles", password="x")
        self.owner.groups.add(Group.objects.get(name=roles.OWNER))
        self.owner = User.objects.get(pk=self.owner.pk)
        self.warehouse = User.objects.create_user("warehouse_roles", password="x")
        self.warehouse.groups.add(Group.objects.get(name=roles.WAREHOUSE_STAFF))

    def _page(self, slug, role, *, publish=False):
        entry = save_draft(
            data={"kind": "page", "slug": slug, "title": f"Trang {slug}", "excerpt": "Tóm tắt.",
                  "body": _body("Nội dung mẫu."), "page_role": role, "show_in_footer": True},
            actor=self.owner,
        )
        if publish:
            publish_entry(entry=entry, actor=self.owner, row_version=entry.row_version, checklist_confirmed=True)
            entry.refresh_from_db()
        return entry

    def test_shop_5_02_choices_and_golive_roles_include_new_roles(self):
        """BR-ND-20: model có 3 lựa chọn mới đúng nhãn; GOLIVE_PAGE_ROLES gồm 7 vai trò."""
        choices = dict(Entry.PAGE_ROLE_CHOICES)
        for role, label in NEW_ROLES.items():
            self.assertEqual(choices.get(role), label)
        self.assertEqual(
            set(GOLIVE_PAGE_ROLES),
            {"privacy", "terms", "refund", "seller_info", "shipping", "payment", "complaints"},
        )
        missing = golive_missing_roles()
        for role in NEW_ROLES:
            self.assertIn(role, missing)

    def test_shop_5_02_new_role_accepted_and_unique(self):
        """BR-ND-16/20: gắn được vai trò mới; trang thứ hai cùng vai trò bị từ chối."""
        for role in NEW_ROLES:
            self._page(f"trang-{role}", role)
            with self.assertRaises(BusinessError) as ctx:
                self._page(f"trang-{role}-2", role)
            self.assertEqual(ctx.exception.code, "BR-ND-16")
        self.assertEqual(Entry.objects.filter(page_role__in=NEW_ROLES).count(), 3)

    def test_shop_5_02_ac2_cannot_unpublish_effective_shipping_page(self):
        """AC2 (lỗi): trang shipping đang hiệu lực, Chủ bấm gỡ -> 400 BR-ND-16, trang vẫn Đã đăng."""
        page = self._page("giao-hang", "shipping", publish=True)
        self.client.force_authenticate(self.owner)
        res = self.client.post(f"/api/content/entries/{page.pk}/unpublish/",
                               {"row_version": page.row_version, "reason": "other"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data.get("code"), "BR-ND-16")
        page.refresh_from_db()
        self.assertEqual(page.status, "published")

    def test_shop_5_02_published_role_cannot_be_removed(self):
        """BR-ND-16: trang complaints đang đăng không bỏ/đổi vai trò được."""
        page = self._page("khieu-nai", "complaints", publish=True)
        with self.assertRaises(BusinessError) as ctx:
            save_draft(entry=page, data={"page_role": None}, actor=self.owner)
        self.assertEqual(ctx.exception.code, "BR-ND-16")
        page.refresh_from_db()
        self.assertEqual(page.page_role, "complaints")

    def test_shop_5_02_ac3_payment_page_keeps_version_history(self):
        """AC3: sửa trang payment rồi đăng bản mới -> có 2 phiên bản."""
        page = self._page("thanh-toan", "payment", publish=True)
        page = save_draft(entry=page, data={"body": _body("Nội dung sửa lần hai.")}, actor=self.owner)
        publish_entry(entry=page, actor=self.owner, row_version=page.row_version, checklist_confirmed=True)
        self.assertEqual(
            list(EntryVersion.objects.filter(entry=page).order_by("version").values_list("version", flat=True)), [1, 2]
        )
        res = self.client.get("/api/public/content/pages/by-role/payment/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["version"], 2)

    def test_shop_5_02_ac4_warehouse_staff_cannot_edit_page(self):
        """AC4 (quyền): NV kho gọi API sửa trang -> 403, dữ liệu không đổi."""
        page = self._page("giao-hang", "shipping")
        self.client.force_authenticate(self.warehouse)
        res = self.client.patch(f"/api/content/entries/{page.pk}/",
                                {"row_version": page.row_version, "title": "Đổi"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        page.refresh_from_db()
        self.assertEqual(page.title, "Trang giao-hang")

    def test_shop_5_02_golive_status_lists_missing_new_roles(self):
        """golive-status ERP liệt kê vai trò mới chưa đăng; đăng rồi thì hết."""
        self._page("giao-hang", "shipping", publish=True)
        self.client.force_authenticate(self.owner)
        missing = set(self.client.get("/api/content/golive-status/").data["missing_roles"])
        self.assertNotIn("shipping", missing)
        self.assertTrue({"payment", "complaints"} <= missing)
