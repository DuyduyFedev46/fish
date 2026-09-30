"""
P8 Lô 7 — nợ Lô 6 L6-1 (BR-ND-07): ảnh của bài KHÁC không quay lại qua khôi phục phiên bản / huỷ thay đổi,
và `publish_entry` kiểm lại ảnh bìa + khối ảnh trước khi đăng. Dữ liệu giả.
Ma trận: chu/quan_ly đăng được; nv_kho/nv_giao/cskh 403; khách 401.
"""
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.tests.fixtures import client_for, make_user
from apps.content.entries.services import calculate_content_hash
from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.images import ContentImage
from apps.accounts import roles

ALT_A = "Ảnh riêng của bài A KHÔNG được lộ"


def _para():
    return {"type": "paragraph", "children": [{"text": "Nội dung giả."}]}


class L61Base(APITestCase):
    def setUp(self):
        self.chu = make_user("l61_chu", roles.OWNER)
        self.ql = make_user("l61_ql", roles.MANAGER)
        self.category = Category.objects.create(
            name="L61 danh mục", name_key="l61 danh muc", slug="l61-danh-muc", is_active=True
        )
        self.entry_a = Entry.objects.create(
            kind="post", title="Bài A", slug="l61-bai-a", category=self.category,
            row_version=1, created_by=self.ql, updated_by=self.ql,
        )
        self.img_a = ContentImage.objects.create(
            entry=self.entry_a, alt=ALT_A, width=10, height=10, uploaded_by=self.ql
        )
        self.entry = Entry.objects.create(
            kind="post", title="Bài B", slug="l61-bai-b", category=self.category,
            excerpt="Mô tả giả", body={"type": "doc", "blocks": [_para()]},
            row_version=1, created_by=self.ql, updated_by=self.ql,
        )
        self.img_b = ContentImage.objects.create(
            entry=self.entry, alt="Ảnh của B", width=10, height=10, uploaded_by=self.ql
        )

    def _hash(self, entry, cover_id):
        return calculate_content_hash(
            kind=entry.kind, title=entry.title, slug=entry.slug, excerpt=entry.excerpt,
            seo_title=entry.seo_title, seo_description=entry.seo_description,
            category_id=entry.category_id, cover_image_id=cover_id, body=entry.body,
        )

    def _legacy_published_version(self, cover, body=None):
        """Phiên bản đã đăng có ảnh bìa (dữ liệu cũ trước SR-18 có thể trỏ ảnh bài khác)."""
        body = body or self.entry.body
        ver = EntryVersion.objects.create(
            entry=self.entry, version=1, kind="post", title=self.entry.title, slug=self.entry.slug,
            excerpt=self.entry.excerpt, description="Mô tả giả", category=self.category,
            cover_image=cover, body=body, content_hash="h-legacy",
            published_at=timezone.now(), published_by=self.chu,
        )
        Entry.objects.filter(pk=self.entry.pk).update(
            status="published", published_version=ver, first_published_at=timezone.now(),
            cover_image=cover, draft_hash=self._hash(self.entry, cover.pk if cover else None),
        )
        self.entry.refresh_from_db()
        return ver

    def _post(self, user, suffix, payload=None):
        return client_for(user).post(f"/api/content/entries/{self.entry.pk}/{suffix}/", payload or {}, format="json")

    def _publish_payload(self):
        return {"row_version": self.entry.row_version, "checklist_confirmed": True, "acknowledge_warnings": True}


class L61RestoreDiscardTests(L61Base):
    def test_l61_restore_version_co_cover_bai_khac_dat_cover_none(self):
        self._legacy_published_version(self.img_a)
        res = self._post(self.chu, "versions/1/restore", {"row_version": self.entry.row_version})
        self.assertEqual(res.status_code, 200, res.content)
        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.cover_image_id)
        self.assertEqual(self.entry.restored_from, 1)
        self.assertEqual(self.entry.draft_hash, self._hash(self.entry, None))
        self.assertNotIn("KHÔNG được lộ", res.content.decode())

    def test_l61_restore_version_cover_cua_chinh_bai_van_giu(self):
        """Đối chứng: cover thuộc chính bài thì khôi phục bình thường (không xoá nhầm)."""
        ver = self._legacy_published_version(self.img_b)
        res = self._post(self.chu, "versions/1/restore", {"row_version": self.entry.row_version})
        self.assertEqual(res.status_code, 200, res.content)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.cover_image_id, self.img_b.pk)
        self.assertEqual(self.entry.draft_hash, ver.content_hash)

    def test_l61_discard_changes_co_cover_bai_khac_dat_cover_none(self):
        self._legacy_published_version(self.img_a)
        res = self._post(self.chu, "discard-changes", {"row_version": self.entry.row_version})
        self.assertEqual(res.status_code, 200, res.content)
        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.cover_image_id)
        self.assertEqual(self.entry.draft_hash, self._hash(self.entry, None))

    def test_l61_discard_changes_cover_cua_chinh_bai_van_giu(self):
        ver = self._legacy_published_version(self.img_b)
        res = self._post(self.chu, "discard-changes", {"row_version": self.entry.row_version})
        self.assertEqual(res.status_code, 200, res.content)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.cover_image_id, self.img_b.pk)
        self.assertEqual(self.entry.draft_hash, ver.content_hash)

    def test_l61_restore_va_discard_phan_quyen(self):
        self._legacy_published_version(self.img_b)
        for user in (make_user("l61_kho", roles.WAREHOUSE_STAFF), make_user("l61_giao", roles.DELIVERY_STAFF), make_user("l61_cs", roles.CUSTOMER_SERVICE)):
            with self.subTest(user=user.username):
                self.assertEqual(
                    self._post(user, "versions/1/restore", {"row_version": self.entry.row_version}).status_code, 403)
                self.assertEqual(
                    self._post(user, "discard-changes", {"row_version": self.entry.row_version}).status_code, 403)
        self.assertEqual(client_for(None).post(
            f"/api/content/entries/{self.entry.pk}/discard-changes/", {}, format="json").status_code, 401)


class L61PublishTests(L61Base):
    def _prepare_valid(self):
        Entry.objects.filter(pk=self.entry.pk).update(cover_image=self.img_b)
        self.entry.refresh_from_db()

    def test_l61_publish_cover_cua_bai_khac_400_br_nd_07_khong_tao_phien_ban(self):
        Entry.objects.filter(pk=self.entry.pk).update(cover_image=self.img_a)
        self.entry.refresh_from_db()
        res = self._post(self.chu, "publish", self._publish_payload())
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["code"], "BR-ND-07")
        self.assertNotIn("KHÔNG được lộ", res.content.decode())
        self.assertEqual(EntryVersion.objects.filter(entry=self.entry).count(), 0)
        self.entry.refresh_from_db()
        self.assertNotEqual(self.entry.status, "published")

    def test_l61_publish_khoi_anh_cua_bai_khac_400_br_nd_07(self):
        self._prepare_valid()
        Entry.objects.filter(pk=self.entry.pk).update(body={"type": "doc", "blocks": [
            _para(), {"type": "image", "image_id": self.img_a.pk, "alt": "x", "caption": ""}]})
        self.entry.refresh_from_db()
        res = self._post(self.chu, "publish", self._publish_payload())
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["code"], "BR-ND-07")
        self.assertEqual(EntryVersion.objects.filter(entry=self.entry).count(), 0)

    def test_l61_publish_anh_cua_chinh_bai_van_dang_duoc(self):
        """Đối chứng: cover + khối ảnh đều thuộc bài -> 200, tạo phiên bản 1."""
        self._prepare_valid()
        Entry.objects.filter(pk=self.entry.pk).update(body={"type": "doc", "blocks": [
            _para(), {"type": "image", "image_id": self.img_b.pk, "alt": "x", "caption": ""}]})
        self.entry.refresh_from_db()
        res = self._post(self.chu, "publish", self._publish_payload())
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(EntryVersion.objects.filter(entry=self.entry).count(), 1)

    def test_l61_publish_phan_quyen(self):
        self._prepare_valid()
        for user in (make_user("l61p_kho", roles.WAREHOUSE_STAFF), make_user("l61p_giao", roles.DELIVERY_STAFF), make_user("l61p_cs", roles.CUSTOMER_SERVICE)):
            with self.subTest(user=user.username):
                self.assertEqual(self._post(user, "publish", self._publish_payload()).status_code, 403)
        self.assertEqual(client_for(None).post(
            f"/api/content/entries/{self.entry.pk}/publish/", self._publish_payload(), format="json").status_code, 401)
        self.assertEqual(EntryVersion.objects.filter(entry=self.entry).count(), 0)
