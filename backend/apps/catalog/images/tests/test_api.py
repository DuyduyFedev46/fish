"""
API `/api/catalog/items/{id}/image/` (A2 POST tải/thay, A3 DELETE gỡ) — BR-DM-09..16,
BR-PQ-12 (quyền Tầng 2 `catalog.change_item_image`: chu + quan_ly, KHÔNG nv_kho/nv_giao).
"""
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.catalog.images.storage import ItemImageStorageError
from apps.catalog.models import Item, ItemGroup

from .factories import make_uploaded_bytes, make_uploaded_image
from apps.accounts import roles

URL = "/api/catalog/items/{}/image/"


def client_for(username, *groups):
    user = User.objects.create_user(username, password="x")
    for name in groups:
        user.groups.add(Group.objects.get(name=name))
    client = APIClient()
    client.force_authenticate(User.objects.get(pk=user.pk))  # bỏ cache quyền
    return client, user


class ItemImageApiTestCase(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá")
        self.item = Item.objects.create(code="CA-THU", name="Cá thu cắt khúc", item_group=g)
        self.url = URL.format(self.item.pk)


class UploadItemImageApiTests(ItemImageApiTestCase):
    def test_a2_ac1_chu_tai_anh_lan_dau_tra_201_dung_hinh_dang_contract(self):
        client, _ = client_for("chu1", roles.OWNER)
        resp = client.post(
            self.url,
            {"file": make_uploaded_image(size=(3000, 2000), fmt="JPEG"), "alt_text": ""},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body["item_id"], self.item.pk)
        self.assertEqual(body["item_code"], "CA-THU")
        image = body["image"]
        self.assertEqual(image["alt"], "Cá thu cắt khúc")
        self.assertEqual(image["is_illustration"], False)
        self.assertEqual(set(image["urls"]), {"thumb", "card", "detail"})
        for u in image["urls"].values():
            self.assertTrue(u.startswith("http"))
        self.assertIn("uploaded_at", image)
        self.assertEqual(image["uploaded_by"], "chu1")
        self.assertEqual(body["warnings"], [])

    def test_a2_ac4_quan_ly_thay_anh_tra_200_url_moi(self):
        chu_client, _ = client_for("chu1", roles.OWNER)
        first = chu_client.post(
            self.url, {"file": make_uploaded_image()}, format="multipart",
        ).json()

        ql_client, _ = client_for("ql1", roles.MANAGER)
        resp = ql_client.post(
            self.url,
            {"file": make_uploaded_image(), "expected_image_id": first["image"]["id"]},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        second = resp.json()
        self.assertNotEqual(second["image"]["urls"]["card"], first["image"]["urls"]["card"])
        self.assertNotEqual(second["image"]["urls"]["thumb"], first["image"]["urls"]["thumb"])
        self.assertNotEqual(second["image"]["urls"]["detail"], first["image"]["urls"]["detail"])

    def test_b2_thay_anh_cap_nhat_uploaded_at_va_uploaded_by_theo_lan_gan_nhat(self):
        chu_client, _ = client_for("chu1", roles.OWNER)
        first = chu_client.post(self.url, {"file": make_uploaded_image()}, format="multipart").json()
        first_uploaded_at = first["image"]["uploaded_at"]
        first_uploaded_by = first["image"]["uploaded_by"]
        self.assertEqual(first_uploaded_by, "chu1")

        ql_client, _ = client_for("ql1", roles.MANAGER)
        second = ql_client.post(
            self.url,
            {"file": make_uploaded_image(), "expected_image_id": first["image"]["id"]},
            format="multipart",
        ).json()

        # uploaded_by phải là người THAY gần nhất (Quản lý), không còn là người tạo (Chủ).
        self.assertEqual(second["image"]["uploaded_by"], "ql1")
        self.assertNotEqual(second["image"]["uploaded_by"], first_uploaded_by)
        # uploaded_at phải là thời điểm THAY gần nhất (updated_at), không phải thời điểm tạo
        # lần đầu (created_at không đổi khi thay ảnh) — so sánh NGHIÊM NGẶT để bắt lỗi B2.
        self.assertGreater(second["image"]["uploaded_at"], first_uploaded_at)

        # GET danh sách/chi tiết mặt hàng cũng phải phản ánh lần thay gần nhất.
        detail = chu_client.get(f"/api/catalog/items/{self.item.pk}/").json()
        self.assertEqual(detail["image"]["uploaded_at"], second["image"]["uploaded_at"])

    def test_b3_uploaded_at_theo_gio_vn_offset_0700(self):
        client, _ = client_for("chu1", roles.OWNER)
        resp = client.post(self.url, {"file": make_uploaded_image()}, format="multipart")
        uploaded_at = resp.json()["image"]["uploaded_at"]
        self.assertTrue(uploaded_at.endswith("+07:00"), uploaded_at)

    def test_a2_ac5_audit_log_ghi_nguoi_lam_va_mat_hang(self):
        client, actor = client_for("chu1", roles.OWNER)
        client.post(self.url, {"file": make_uploaded_image()}, format="multipart")
        log = AuditLog.objects.get(action="item_image_add")
        self.assertEqual(log.actor, actor)
        self.assertEqual(log.object_id, str(self.item.pk))

    def test_a2_ac6_canh_bao_low_resolution_tra_ve_trong_response(self):
        client, _ = client_for("chu1", roles.OWNER)
        resp = client.post(
            self.url,
            {"file": make_uploaded_image(size=(400, 400), fmt="PNG")},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["warnings"], [{
            "code": "LOW_RESOLUTION",
            "message": "Ảnh nhỏ hơn 600 px, trên Shop có thể bị mờ.",
        }])

    def test_a2_ac8_tick_anh_minh_hoa(self):
        client, _ = client_for("chu1", roles.OWNER)
        resp = client.post(
            self.url,
            {"file": make_uploaded_image(), "is_illustration": "true"},
            format="multipart",
        )
        self.assertTrue(resp.json()["image"]["is_illustration"])

    def test_a2_ac9_sai_dinh_dang_tra_400_br_dm_10(self):
        client, _ = client_for("chu1", roles.OWNER)
        svg = make_uploaded_bytes("x.svg", b"<svg><script>1</script></svg>", "image/svg+xml")
        resp = client.post(self.url, {"file": svg}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-DM-10")
        self.item.refresh_from_db()
        self.assertFalse(hasattr(self.item, "image") and self.item.image)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_a2_ac10_vuot_dung_luong_tra_400(self):
        client, _ = client_for("chu1", roles.OWNER)
        with self.settings(ITEM_IMAGE_MAX_BYTES=10):
            resp = client.post(
                self.url, {"file": make_uploaded_image(size=(50, 50), fmt="PNG")}, format="multipart",
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-DM-10")

    def test_a2_ac11_kho_anh_loi_tra_503(self):
        client, _ = client_for("chu1", roles.OWNER)
        with patch(
            "apps.catalog.images.storage.LocalItemImageStorage.save",
            side_effect=ItemImageStorageError(),
        ):
            resp = client.post(self.url, {"file": make_uploaded_image()}, format="multipart")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["code"], "BR-DM-16")
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_a2_ac13_expected_image_id_khong_khop_tra_409(self):
        chu_client, _ = client_for("chu1", roles.OWNER)
        first = chu_client.post(self.url, {"file": make_uploaded_image()}, format="multipart").json()

        ql_client, _ = client_for("ql1", roles.MANAGER)
        ql_client.post(
            self.url,
            {"file": make_uploaded_image(), "expected_image_id": first["image"]["id"]},
            format="multipart",
        )

        resp = chu_client.post(
            self.url,
            {"file": make_uploaded_image(), "expected_image_id": first["image"]["id"]},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "BR-DM-12")

    def test_a2_ac14_nv_kho_403_nv_giao_403_chua_dang_nhap_401(self):
        kho_client, _ = client_for("kho1", roles.WAREHOUSE_STAFF)
        resp = kho_client.post(self.url, {"file": make_uploaded_image()}, format="multipart")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["code"], "BR-PQ-12")

        giao_client, _ = client_for("giao1", roles.DELIVERY_STAFF)
        resp = giao_client.post(self.url, {"file": make_uploaded_image()}, format="multipart")
        self.assertEqual(resp.status_code, 403)

        anon = APIClient()
        resp = anon.post(self.url, {"file": make_uploaded_image()}, format="multipart")
        self.assertEqual(resp.status_code, 401)

        self.item.refresh_from_db()
        self.assertFalse(hasattr(self.item, "image") and self.item.image)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_a2_ac15_quan_ly_khong_sua_duoc_ten_hay_an_hien(self):
        client, _ = client_for("ql1", roles.MANAGER)
        resp = client.patch(f"/api/catalog/items/{self.item.pk}/", {"name": "Tên mới"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "Cá thu cắt khúc")

    def test_a2_ac16_bo_loc_has_image(self):
        client, _ = client_for("chu1", roles.OWNER)
        other = Item.objects.create(code="CA-KHAC", name="Cá khác", item_group=self.item.item_group)
        client.post(self.url, {"file": make_uploaded_image()}, format="multipart")

        resp_with = client.get("/api/catalog/items/?has_image=true")
        codes_with = {row["code"] for row in resp_with.json()["results"]}
        self.assertEqual(codes_with, {"CA-THU"})

        resp_without = client.get("/api/catalog/items/?has_image=false")
        codes_without = {row["code"] for row in resp_without.json()["results"]}
        self.assertEqual(codes_without, {"CA-KHAC"})

    def test_khong_ro_gia_von_qua_response_anh(self):
        client, _ = client_for("chu1", roles.OWNER)
        resp = client.post(self.url, {"file": make_uploaded_image()}, format="multipart")
        payload_keys = set(resp.json().keys()) | set(resp.json()["image"].keys())
        self.assertFalse(payload_keys & {"purchase_rate", "landed_unit_cost", "rate", "unit_cost"})


class RemoveItemImageApiTests(ItemImageApiTestCase):
    def _upload(self, client):
        return client.post(self.url, {"file": make_uploaded_image()}, format="multipart").json()

    def test_a3_ac1_go_anh_tra_204_va_null_o_get(self):
        client, _ = client_for("chu1", roles.OWNER)
        self._upload(client)
        resp = client.delete(self.url)
        self.assertEqual(resp.status_code, 204)
        detail = client.get(f"/api/catalog/items/{self.item.pk}/").json()
        self.assertIsNone(detail["image"])

    def test_a3_ac2_audit_log_item_image_remove(self):
        client, actor = client_for("chu1", roles.OWNER)
        self._upload(client)
        AuditLog.objects.all().delete()
        client.delete(self.url)
        log = AuditLog.objects.get()
        self.assertEqual(log.action, "item_image_remove")
        self.assertEqual(log.actor, actor)

    def test_a3_ac4_chua_co_anh_tra_404(self):
        client, _ = client_for("chu1", roles.OWNER)
        resp = client.delete(self.url)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "BR-DM-09")

    def test_a3_ac5_expected_image_id_sai_tra_409(self):
        client, _ = client_for("chu1", roles.OWNER)
        first = self._upload(client)
        resp = client.delete(f"{self.url}?expected_image_id=id-sai")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["code"], "BR-DM-12")
        detail = client.get(f"/api/catalog/items/{self.item.pk}/").json()
        self.assertEqual(detail["image"]["id"], first["image"]["id"])

    def test_a3_ac6_nv_kho_va_nv_giao_403(self):
        self.item2 = self.item
        chu_client, _ = client_for("chu1", roles.OWNER)
        self._upload(chu_client)

        kho_client, _ = client_for("kho1", roles.WAREHOUSE_STAFF)
        resp = kho_client.delete(self.url)
        self.assertEqual(resp.status_code, 403)

        giao_client, _ = client_for("giao1", roles.DELIVERY_STAFF)
        resp = giao_client.delete(self.url)
        self.assertEqual(resp.status_code, 403)

        detail = chu_client.get(f"/api/catalog/items/{self.item.pk}/").json()
        self.assertIsNotNone(detail["image"])
