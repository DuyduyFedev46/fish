"""Nghiệp vụ ảnh mặt hàng — thêm/thay (A2, UC-A1), gỡ (A3, UC-A2). BR-DM-09..16."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.accounts.models import AuditLog
from apps.catalog.images import services
from apps.catalog.images.storage import ItemImageStorageError
from apps.catalog.models import Item, ItemGroup

from .factories import make_image_bytes, make_uploaded_bytes, make_uploaded_image


class FakeStorage:
    """Storage giả cho test: ghi nhớ path đã lưu, không đụng đĩa/mạng."""

    def __init__(self, fail=False):
        self.fail = fail
        self.saved = {}

    def save(self, path, data, content_type):
        if self.fail:
            raise ItemImageStorageError()
        self.saved[path] = data
        return f"https://fake.local/{path}"

    def url(self, path):
        return f"https://fake.local/{path}"


class ItemImageServiceTestCase(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user("chu1", password="x")
        group = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA-THU", name="Cá thu cắt khúc", item_group=group)
        self.storage = FakeStorage()


class UploadItemImageTests(ItemImageServiceTestCase):
    def test_a2_ac1_them_anh_lan_dau_tra_3_url_va_alt_mac_dinh(self):
        outcome = services.upload_item_image(
            item=self.item,
            file=make_uploaded_image(size=(3000, 2000), fmt="JPEG"),
            alt_text="",
            actor=self.actor,
            storage=self.storage,
        )
        self.assertTrue(outcome.created)
        self.assertEqual(outcome.image.alt_text, self.item.name)  # trống -> tên mặt hàng
        self.assertEqual(len(self.storage.saved), 3)
        for size_name in ("thumb", "card", "detail"):
            self.assertIn(f"items/{self.item.pk}/{outcome.image.image_id}/{size_name}.webp", self.storage.saved)

    def test_a2_ac3_mat_hang_dang_an_van_tai_anh_duoc(self):
        self.item.is_active = False
        self.item.save(update_fields=["is_active"])
        outcome = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
        )
        self.assertTrue(outcome.created)

    def test_a2_ac4_thay_anh_sinh_id_moi_khong_xoa_object_cu(self):
        first = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
        )
        old_id = first.image.image_id
        second = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
            expected_image_id=old_id,
        )
        self.assertFalse(second.created)
        self.assertNotEqual(second.image.image_id, old_id)
        # object cũ vẫn còn trong storage (BR-DM-14 — không xoá cứng)
        self.assertTrue(any(old_id in p for p in self.storage.saved))
        self.assertTrue(any(second.image.image_id in p for p in self.storage.saved))
        # chỉ 1 bản ghi ItemImage cho mặt hàng (Q2: mỗi mặt hàng 1 ảnh)
        self.item.refresh_from_db()
        self.assertEqual(self.item.image.image_id, second.image.image_id)

    def test_a2_ac5_audit_log_dung_1_dong_add_va_replace(self):
        AuditLog.objects.all().delete()
        first = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
        )
        first_id = first.image.image_id  # chốt giá trị TRƯỚC lần thay (O2O cache dùng chung object)
        self.assertEqual(AuditLog.objects.count(), 1)
        log = AuditLog.objects.get()
        self.assertEqual(log.action, "item_image_add")
        self.assertEqual(log.actor, self.actor)
        self.assertEqual(log.changes["image_id"], [None, first_id])

        second = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
            expected_image_id=first_id,
        )
        self.assertEqual(AuditLog.objects.count(), 2)
        replace_log = AuditLog.objects.order_by("-id").first()
        self.assertEqual(replace_log.action, "item_image_replace")
        self.assertEqual(replace_log.changes["image_id"], [first_id, second.image.image_id])

    def test_a2_ac6_canh_bao_low_resolution(self):
        outcome = services.upload_item_image(
            item=self.item, file=make_uploaded_image(size=(400, 400), fmt="PNG"),
            actor=self.actor, storage=self.storage,
        )
        self.assertEqual(outcome.warnings, [{
            "code": "LOW_RESOLUTION",
            "message": "Ảnh nhỏ hơn 600 px, trên Shop có thể bị mờ.",
        }])

    def test_khong_canh_bao_khi_anh_du_lon(self):
        outcome = services.upload_item_image(
            item=self.item, file=make_uploaded_image(size=(3000, 2000), fmt="JPEG"),
            actor=self.actor, storage=self.storage,
        )
        self.assertEqual(outcome.warnings, [])

    def test_a2_ac8_tick_anh_minh_hoa_luu_dung_gia_tri(self):
        outcome = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), is_illustration=True,
            actor=self.actor, storage=self.storage,
        )
        self.assertTrue(outcome.image.is_illustration)
        log = AuditLog.objects.order_by("-id").first()
        self.assertEqual(log.changes["is_illustration"], [None, True])

    def test_a2_ac9_sai_dinh_dang_tra_loi_business_error_khong_luu_gi(self):
        svg = make_uploaded_bytes("x.svg", b"<svg><script>1</script></svg>", "image/svg+xml")
        with self.assertRaises(Exception) as ctx:
            services.upload_item_image(
                item=self.item, file=svg, actor=self.actor, storage=self.storage,
            )
        self.assertEqual(getattr(ctx.exception, "code", None), "BR-DM-10")
        self.assertIsNone(services._current_image(self.item))
        self.assertEqual(self.storage.saved, {})
        self.assertEqual(AuditLog.objects.count(), 0)

    @override_settings(ITEM_IMAGE_MAX_BYTES=10)
    def test_a2_ac10_vuot_dung_luong_toi_da(self):
        big = make_uploaded_image(size=(50, 50), fmt="PNG")
        with self.assertRaises(Exception) as ctx:
            services.upload_item_image(
                item=self.item, file=big, actor=self.actor, storage=self.storage,
            )
        self.assertEqual(getattr(ctx.exception, "code", None), "BR-DM-10")
        self.assertEqual(self.storage.saved, {})

    def test_a2_ac11_kho_anh_loi_tra_503_khong_doi_gi(self):
        failing_storage = FakeStorage(fail=True)
        with self.assertRaises(ItemImageStorageError) as ctx:
            services.upload_item_image(
                item=self.item, file=make_uploaded_image(), actor=self.actor,
                storage=failing_storage,
            )
        self.assertEqual(ctx.exception.http_status, 503)
        self.assertEqual(ctx.exception.code, "BR-DM-16")
        self.assertIsNone(services._current_image(self.item))
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_a2_ac13_expected_image_id_khong_khop_tra_409(self):
        services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
        )
        with self.assertRaises(services.ItemImageConflict) as ctx:
            services.upload_item_image(
                item=self.item, file=make_uploaded_image(), actor=self.actor,
                storage=self.storage, expected_image_id="id-sai-hoan-toan",
            )
        self.assertEqual(ctx.exception.http_status, 409)
        self.assertEqual(ctx.exception.code, "BR-DM-12")

class AltTextValidationTests(ItemImageServiceTestCase):
    def test_alt_text_qua_dai_tra_loi_br_dm_11(self):
        with self.assertRaises(Exception) as ctx:
            services.upload_item_image(
                item=self.item, file=make_uploaded_image(), alt_text="x" * 126,
                actor=self.actor, storage=self.storage,
            )
        self.assertEqual(getattr(ctx.exception, "code", None), "BR-DM-11")


class RemoveItemImageTests(ItemImageServiceTestCase):
    def test_a3_ac1_go_anh_giu_lai_object_cu(self):
        outcome = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
        )
        services.remove_item_image(item=self.item, actor=self.actor)
        self.item.refresh_from_db()
        self.assertIsNone(services._current_image(self.item))
        self.assertTrue(any(outcome.image.image_id in p for p in self.storage.saved))

    def test_a3_ac2_audit_log_item_image_remove(self):
        outcome = services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
        )
        AuditLog.objects.all().delete()
        services.remove_item_image(item=self.item, actor=self.actor)
        self.assertEqual(AuditLog.objects.count(), 1)
        log = AuditLog.objects.get()
        self.assertEqual(log.action, "item_image_remove")
        self.assertEqual(log.changes["image_id"], [outcome.image.image_id, None])

    def test_a3_ac4_chua_co_anh_tra_404(self):
        with self.assertRaises(services.ItemImageNotFound) as ctx:
            services.remove_item_image(item=self.item, actor=self.actor)
        self.assertEqual(ctx.exception.http_status, 404)
        self.assertEqual(ctx.exception.code, "BR-DM-09")

    def test_a3_ac5_expected_image_id_sai_tra_409_giu_nguyen_anh(self):
        services.upload_item_image(
            item=self.item, file=make_uploaded_image(), actor=self.actor, storage=self.storage,
        )
        with self.assertRaises(services.ItemImageConflict):
            services.remove_item_image(
                item=self.item, expected_image_id="sai", actor=self.actor,
            )
        self.item.refresh_from_db()
        self.assertIsNotNone(services._current_image(self.item))
