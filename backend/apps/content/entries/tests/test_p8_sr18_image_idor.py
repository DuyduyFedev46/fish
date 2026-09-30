"""
P8 Lô 6 — SR-18: không dùng ảnh của bài khác khi tạo/sửa bài (F1, BR-ND-07).
Repro gốc: doc/features/2026-09-30-ra-soat-agy/repro/A5-f1-idor-cover-image-on-create.py.
Dữ liệu giả, không có dữ liệu cá nhân.
"""
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.common.tests.fixtures import client_for, make_user
from apps.content.models.categories import Category
from apps.content.models.entries import Entry
from apps.content.models.images import ContentImage

User = get_user_model()

MSG_CREATE = "Tải ảnh sau khi lưu nháp lần đầu."
ALT_A = "Ảnh riêng của bài A KHÔNG được lộ"


def _doc(*image_ids):
    return {"type": "doc", "blocks": [{"type": "image", "image_id": i, "alt": "x", "caption": ""} for i in image_ids]}


class Sr18Base(APITestCase):
    def setUp(self):
        self.chu = make_user("sr18_chu", "chu")
        self.ql = make_user("sr18_ql", "quan_ly")
        self.category = Category.objects.create(
            name="Sr18 danh mục", name_key="sr18 danh muc", slug="sr18-danh-muc", is_active=True
        )
        # Bài A (bài khác) có ảnh riêng
        self.entry_a = Entry.objects.create(
            kind="post", title="Bài A", slug="bai-a", category=self.category,
            row_version=1, created_by=self.ql, updated_by=self.ql,
        )
        self.img_a = ContentImage.objects.create(
            entry=self.entry_a, alt=ALT_A, width=10, height=10, uploaded_by=self.ql
        )
        # Bài B (bài đang sửa) có ảnh riêng
        self.entry_b = Entry.objects.create(
            kind="post", title="Bài B", slug="bai-b", category=self.category,
            row_version=1, created_by=self.ql, updated_by=self.ql,
        )
        self.img_b = ContentImage.objects.create(
            entry=self.entry_b, alt="Ảnh của B", width=10, height=10, uploaded_by=self.ql
        )

    def post(self, payload, user=None):
        return client_for(user or self.ql).post("/api/content/entries/", payload, format="json")

    def patch(self, entry, payload, user=None):
        return client_for(user or self.ql).patch(f"/api/content/entries/{entry.pk}/", payload, format="json")

    def new_payload(self, **extra):
        data = {"kind": "post", "title": "Bài mới SR18", "category": self.category.pk,
                "body": {"type": "doc", "blocks": []}}
        data.update(extra)
        return data

    def assert_br_nd_07(self, resp, message=None):
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-ND-07")
        if message:
            self.assertEqual(resp.json()["detail"], message)
        # Không rò thông tin ảnh của bài khác (alt) qua thông điệp lỗi.
        self.assertNotIn("KHÔNG được lộ", resp.content.decode())


class Sr18CreateTests(Sr18Base):
    def test_sr18_ac1_tao_bai_voi_cover_cua_bai_khac_400(self):
        """SR-18-AC1 (repro F1): POST cover_image của bài A -> 400 BR-ND-07, không tạo bài."""
        before = Entry.objects.count()
        resp = self.post(self.new_payload(cover_image=self.img_a.pk))
        self.assert_br_nd_07(resp, MSG_CREATE)
        self.assertEqual(Entry.objects.count(), before)

    def test_sr18_ac1_tao_bai_voi_khoi_image_cua_bai_khac_400(self):
        """SR-18-AC1: POST khối image trỏ ảnh bài A -> 400 BR-ND-07, không tạo bài."""
        before = Entry.objects.count()
        resp = self.post(self.new_payload(body=_doc(self.img_a.pk)))
        self.assert_br_nd_07(resp, MSG_CREATE)
        self.assertEqual(Entry.objects.count(), before)

    def test_sr18_ac1_khi_tao_moi_moi_anh_deu_bi_chan_ke_ca_id_khong_ton_tai(self):
        """SR-18-AC1: khi tạo mọi ảnh đều bị chặn (id không tồn tại cũng vậy)."""
        before = Entry.objects.count()
        self.assert_br_nd_07(self.post(self.new_payload(cover_image=99999999)), MSG_CREATE)
        self.assert_br_nd_07(self.post(self.new_payload(body=_doc(99999999))), MSG_CREATE)
        self.assertEqual(Entry.objects.count(), before)

    def test_sr18_tao_bai_khong_anh_van_201(self):
        """Đường thuận: tạo bài không ảnh (cover null, body chữ) vẫn 201."""
        r1 = self.post(self.new_payload(cover_image=None, title="Bài không ảnh 1"))
        self.assertEqual(r1.status_code, 201, r1.content)
        self.assertIsNone(r1.json()["cover_image"])
        r2 = self.post(self.new_payload(title="Bài không ảnh 2", body={
            "type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Chữ thôi"}]}]}))
        self.assertEqual(r2.status_code, 201, r2.content)

    def test_sr18_tao_bai_khoi_image_khong_id_hop_le_van_bi_bo_khong_chan(self):
        """Khối image thiếu image_id hợp lệ vẫn bị bỏ như cũ (không phải lỗi quyền sở hữu)."""
        resp = self.post(self.new_payload(title="Khối ảnh hỏng", body={
            "type": "doc", "blocks": [{"type": "image", "image_id": "abc"}]}))
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["body"]["blocks"], [])


class Sr18PatchTests(Sr18Base):
    def test_sr18_ac2_patch_cover_cua_bai_khac_400_bai_khong_doi(self):
        """SR-18-AC2: PATCH bài B với cover là ảnh bài A -> 400; bài B không đổi."""
        resp = self.patch(self.entry_b, self.patch_payload(cover_image=self.img_a.pk))
        self.assert_br_nd_07(resp)
        self.entry_b.refresh_from_db()
        self.assertIsNone(self.entry_b.cover_image_id)
        self.assertEqual(self.entry_b.row_version, 1)

    def patch_payload(self, **extra):
        data = {"row_version": 1}
        data.update(extra)
        return data

    def test_sr18_ac2_patch_cover_cua_chinh_bai_200(self):
        """SR-18-AC2: PATCH bài B với ảnh của chính B -> 200."""
        resp = self.patch(self.entry_b, self.patch_payload(cover_image=self.img_b.pk))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["cover_image"], self.img_b.pk)

    def test_sr18_ac2_patch_khoi_image_cua_bai_khac_400_cua_chinh_bai_200(self):
        """SR-18-AC2: khối image của A -> 400; của B -> 200."""
        resp = self.patch(self.entry_b, self.patch_payload(body=_doc(self.img_a.pk)))
        self.assert_br_nd_07(resp)
        self.entry_b.refresh_from_db()
        self.assertEqual(self.entry_b.body, {})  # default JSON, chưa lưu gì
        resp = self.patch(self.entry_b, self.patch_payload(body=_doc(self.img_b.pk)))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["body"]["blocks"][0]["image_id"], self.img_b.pk)

    def test_sr18_patch_cover_khong_ton_tai_400(self):
        """Ca biên: ảnh không tồn tại (vd bài chứa ảnh đã bị xoá cascade) -> 400 BR-ND-07."""
        self.assert_br_nd_07(self.patch(self.entry_b, self.patch_payload(cover_image=99999999)))

    def test_sr18_patch_cover_kieu_la_400_khong_500(self):
        """Ca biên: cover_image không phải số nguyên dương (chuỗi, bool, số âm, danh sách) -> 400, không 500."""
        for bad in ("abc", True, -1, [1], {"id": 1}):
            with self.subTest(bad=bad):
                self.assert_br_nd_07(self.patch(self.entry_b, self.patch_payload(cover_image=bad)))

    def test_sr18_patch_anh_da_go_khoi_bai_van_dung_lai_duoc(self):
        """Ca biên: ảnh của B đã gỡ khỏi cover/body (ảnh mồ côi vẫn thuộc B) -> dùng lại được, 200."""
        r1 = self.patch(self.entry_b, self.patch_payload(cover_image=self.img_b.pk))
        self.assertEqual(r1.status_code, 200, r1.content)
        r2 = self.patch(self.entry_b, {"row_version": r1.json()["row_version"], "cover_image": None})
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertIsNone(r2.json()["cover_image"])
        r3 = self.patch(self.entry_b, {"row_version": r2.json()["row_version"], "cover_image": self.img_b.pk})
        self.assertEqual(r3.status_code, 200, r3.content)
        self.assertEqual(r3.json()["cover_image"], self.img_b.pk)

    def test_sr18_patch_anh_cua_bai_khac_o_moi_trang_thai_deu_400(self):
        """Ca biên: ảnh thuộc bài nháp / đã đăng / đã gỡ của người khác -> đều 400."""
        for st in ("draft", "pending_review", "published", "unpublished"):
            other = Entry.objects.create(
                kind="post", title=f"Bài {st}", slug=f"bai-{st}", status=st,
                created_by=self.chu, updated_by=self.chu,
            )
            img = ContentImage.objects.create(entry=other, alt="x", uploaded_by=self.chu)
            with self.subTest(status=st):
                self.assert_br_nd_07(self.patch(self.entry_b, self.patch_payload(cover_image=img.pk)))
                self.assert_br_nd_07(self.patch(self.entry_b, self.patch_payload(body=_doc(img.pk))))
        self.entry_b.refresh_from_db()
        self.assertIsNone(self.entry_b.cover_image_id)
        self.assertEqual(self.entry_b.row_version, 1)

    def test_sr18_patch_anh_cua_bai_da_xoa_400(self):
        """Ca biên: bài nháp bị xoá (cascade xoá ảnh) -> id ảnh cũ không dùng lại được."""
        other = Entry.objects.create(kind="post", title="Sắp xoá", slug="sap-xoa",
                                     created_by=self.ql, updated_by=self.ql)
        img = ContentImage.objects.create(entry=other, alt="x", uploaded_by=self.ql)
        stale_id = img.pk
        other.delete()
        self.assert_br_nd_07(self.patch(self.entry_b, self.patch_payload(cover_image=stale_id)))

    def test_sr18_patch_phien_ban_cu_409_khong_doi_du_lieu(self):
        """Ca biên: sửa trên phiên bản cũ (row_version lệch) kèm ảnh bài khác -> 409 STALE_VERSION, không ghi."""
        resp = self.patch(self.entry_b, {"row_version": 99, "cover_image": self.img_a.pk})
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "STALE_VERSION")
        self.entry_b.refresh_from_db()
        self.assertIsNone(self.entry_b.cover_image_id)
        self.assertEqual(self.entry_b.row_version, 1)

    def test_sr18_ac4_gioi_han_20_anh_khong_lach_qua_anh_bai_khac(self):
        """SR-18-AC4: B đã đủ 20 ảnh riêng trong body; thêm ảnh bài A làm cover -> 400, không lách."""
        own = [self.img_b] + [
            ContentImage.objects.create(entry=self.entry_b, alt=f"b{i}", uploaded_by=self.ql) for i in range(19)
        ]
        resp = self.patch(self.entry_b, self.patch_payload(body=_doc(*[i.pk for i in own])))
        self.assertEqual(resp.status_code, 200, resp.content)
        version = resp.json()["row_version"]
        resp = self.patch(self.entry_b, {"row_version": version, "cover_image": self.img_a.pk})
        self.assert_br_nd_07(resp)
        # Ảnh bài A vào thân bài cũng 400
        resp = self.patch(self.entry_b, {"row_version": version, "body": _doc(*([i.pk for i in own[:19]] + [self.img_a.pk]))})
        self.assert_br_nd_07(resp)

    def test_sr18_ac4_gioi_han_toi_da_van_ap_dung_voi_anh_cua_chinh_bai(self):
        """SR-18-AC4: 21 ảnh của chính bài B trong thân bài -> vẫn 400 BR-ND-07 (giới hạn cũ còn hiệu lực)."""
        own = [self.img_b] + [
            ContentImage.objects.create(entry=self.entry_b, alt=f"b{i}", uploaded_by=self.ql) for i in range(20)
        ]
        resp = self.patch(self.entry_b, self.patch_payload(body=_doc(*[i.pk for i in own])))
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "BR-ND-07")


class Sr18GroupMatrixTests(Sr18Base):
    """Ma trận Group cho POST/PATCH entries (chu/quan_ly theo quyền content; còn lại 403; khách 401)."""

    def setUp(self):
        super().setUp()
        self.users = {
            "chu": self.chu,
            "quan_ly": self.ql,
            "nv_kho": make_user("sr18_kho", "nv_kho"),
            "nv_giao": make_user("sr18_giao", "nv_giao"),
            "cskh": make_user("sr18_cskh", "cskh"),
            "khach": None,
        }

    def test_sr18_matran_post_va_patch(self):
        expect_ok = {"chu": (201, 200), "quan_ly": (201, 200)}
        expect_deny = {"nv_kho": 403, "nv_giao": 403, "cskh": 403, "khach": 401}
        for name, user in self.users.items():
            with self.subTest(group=name):
                client = client_for(user)
                before = Entry.objects.count()
                r_post = client.post("/api/content/entries/", self.new_payload(title=f"MT {name}"), format="json")
                b = Entry.objects.create(kind="post", title=f"B {name}", slug=f"b-{name}",
                                         created_by=self.ql, updated_by=self.ql)
                r_patch = client.patch(f"/api/content/entries/{b.pk}/", {"row_version": 1, "title": "Đổi"}, format="json")
                if name in expect_ok:
                    self.assertEqual((r_post.status_code, r_patch.status_code), expect_ok[name],
                                     (r_post.content, r_patch.content))
                else:
                    self.assertEqual(r_post.status_code, expect_deny[name])
                    self.assertEqual(r_patch.status_code, expect_deny[name])
                    self.assertEqual(Entry.objects.count(), before + 1)  # chỉ bài B của test
                    b.refresh_from_db()
                    self.assertEqual(b.title, f"B {name}")

    def test_sr18_chu_cung_bi_chan_anh_bai_khac(self):
        """Chủ cũng không được lách: cover ảnh bài A khi tạo -> 400; khi PATCH bài B -> 400."""
        self.assert_br_nd_07(self.post(self.new_payload(cover_image=self.img_a.pk), user=self.chu), MSG_CREATE)
        self.assert_br_nd_07(self.patch(self.entry_b, {"row_version": 1, "cover_image": self.img_a.pk}, user=self.chu))

    def test_sr18_nhom_khong_quyen_gui_anh_bai_khac_van_403_khong_lo_ly_do(self):
        """nv_kho gửi ảnh bài A: 403 (không phải 400 BR-ND-07), không lộ tồn tại ảnh."""
        r = self.post(self.new_payload(cover_image=self.img_a.pk), user=self.users["nv_kho"])
        self.assertEqual(r.status_code, 403)
        self.assertNotIn("BR-ND-07", r.content.decode())
