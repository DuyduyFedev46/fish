"""
QA P8 Lô 7 — L6-1: chuỗi khôi phục -> đăng với dữ liệu cũ trỏ ảnh bài khác, đăng 2 lần, sửa nháp bằng ảnh bài khác,
màn hình cũ (row_version cũ). Dữ liệu giả.
"""
from apps.content.entries.tests.test_p8_lo7_cover_scope import L61Base, _para
from apps.common.tests.fixtures import client_for
from apps.content.models.entries import Entry, EntryVersion


class QaL61Chain(L61Base):
    def _ver_with_foreign_block(self):
        body = {"type": "doc", "blocks": [_para(), {"type": "image", "image_id": self.img_a.pk, "alt": "x", "caption": ""}]}
        return self._legacy_published_version(self.img_b, body=body)

    def test_qa_restore_ban_cu_co_khoi_anh_bai_khac_van_nap_nhung_dang_bi_chan(self):
        self._ver_with_foreign_block()
        res = self._post(self.chu, "versions/1/restore", {"row_version": self.entry.row_version})
        self.assertEqual(res.status_code, 200, res.content)
        self.entry.refresh_from_db()
        # dữ liệu cũ nằm trong nháp, nhưng KHÔNG đăng được
        self.entry.draft_hash = "khac"
        self.entry.save(update_fields=["draft_hash"])
        before = EntryVersion.objects.filter(entry=self.entry).count()
        res = self._post(self.chu, "publish", self._publish_payload())
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["code"], "BR-ND-07")
        self.assertEqual(EntryVersion.objects.filter(entry=self.entry).count(), before)
        self.assertNotIn("KHÔNG được lộ", res.content.decode())

    def test_qa_sua_nhap_dat_bia_bai_khac_bi_chan_va_khong_doi_nhap(self):
        rv = self.entry.row_version
        res = client_for(self.ql).patch(
            f"/api/content/entries/{self.entry.pk}/", {"row_version": rv, "cover_image": self.img_a.pk}, format="json")
        self.assertIn(res.status_code, (400, 404), res.content)
        self.entry.refresh_from_db()
        self.assertNotEqual(self.entry.cover_image_id, self.img_a.pk)
        self.assertNotIn("KHÔNG được lộ", res.content.decode())

    def test_qa_sua_nhap_khoi_anh_bai_khac_hoac_id_dang_chuoi_khong_lot(self):
        rv = self.entry.row_version
        for bad_id in (self.img_a.pk, str(self.img_a.pk), True, float(self.img_a.pk)):
            with self.subTest(bad_id=repr(bad_id)):
                body = {"type": "doc", "blocks": [_para(), {"type": "image", "image_id": bad_id, "alt": "x", "caption": ""}]}
                res = client_for(self.ql).patch(
                    f"/api/content/entries/{self.entry.pk}/", {"row_version": rv, "body": body}, format="json")
                self.entry.refresh_from_db()
                blocks = self.entry.body.get("blocks", [])
                ids = [b.get("image_id") for b in blocks if b.get("type") == "image"]
                self.assertNotIn(self.img_a.pk, ids, f"lọt ảnh bài khác vào nháp: {res.status_code} {res.content[:200]}")
                rv = self.entry.row_version

    def test_qa_dang_2_lan_lan_hai_khong_tao_phien_ban_thu_2_va_man_hinh_cu_bi_tu_choi(self):
        Entry.objects.filter(pk=self.entry.pk).update(cover_image=self.img_b)
        self.entry.refresh_from_db()
        payload = self._publish_payload()
        r1 = self._post(self.chu, "publish", payload)
        self.assertEqual(r1.status_code, 200, r1.content)
        r2 = self._post(self.chu, "publish", payload)   # màn hình cũ: row_version cũ, không có thay đổi
        self.assertIn(r2.status_code, (400, 409), r2.content)
        self.assertEqual(EntryVersion.objects.filter(entry=self.entry).count(), 1)

    def test_qa_anh_bai_khac_khong_bi_xoa_khi_khoi_phuc(self):
        self._legacy_published_version(self.img_a)
        self._post(self.chu, "versions/1/restore", {"row_version": self.entry.row_version})
        from apps.content.models.images import ContentImage
        self.assertTrue(ContentImage.objects.filter(pk=self.img_a.pk, entry=self.entry_a).exists())
        self.assertTrue(EntryVersion.objects.filter(entry=self.entry, version=1).exists())
