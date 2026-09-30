"""
Repro (ĐỎ — lỗi thật, trùng SR-18) — F1 IDOR ảnh khi TẠO bài (POST /api/content/entries/).
Xem doc/features/2026-09-30-sua-loi-review/02-stories.md#SR-18.

Vị trí lỗi: backend/apps/content/entries/services.py dòng ~157
    if entry and not ContentImage.objects.filter(pk=cov_id, entry=entry).exists():
Khi TẠO bài (entry=None lúc gọi save_draft), điều kiện "entry and ..." luôn sai (short-circuit)
nên kiểm tra "ảnh phải thuộc cùng bài" bị BỎ QUA hoàn toàn ở nhánh tạo mới. Kết quả: bài A tạo
được, gán cover_image = ảnh thuộc bài B (của người khác), API trả 201 thay vì 400 BR-ND-07.

Chạy: cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test \
      --settings=... (copy file này vào apps/content/tests/ tạm thời rồi chạy, hoặc dùng pytest
      trỏ trực tiếp path này) — KHÔNG để lại trong backend/apps/content/tests/ (theo hướng dẫn A5).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase, APIClient

from apps.content.models.categories import Category
from apps.content.models.entries import Entry

User = get_user_model()


class F1IdorCoverImageOnCreateTests(APITestCase):
    def setUp(self):
        self.quan_ly = User.objects.create_user(username="ra_ql_idor", password="x")
        g_ql, _ = Group.objects.get_or_create(name="quan_ly")
        self.quan_ly.groups.add(g_ql)
        self.category = Category.objects.create(
            name="Ra soat idor", name_key="ra soat idor", slug="ra-soat-idor", is_active=True
        )
        # Bài A (của người khác / phiên soạn khác) có ảnh id=<img_a.pk>
        self.entry_a = Entry.objects.create(
            kind="post",
            title="Bai A - co anh rieng",
            slug="bai-a-co-anh-rieng",
            category=self.category,
            row_version=1,
            created_by=self.quan_ly,
            updated_by=self.quan_ly,
        )
        self.img_a = self.entry_a.images.create(alt="anh cua bai A", width=10, height=10, uploaded_by=self.quan_ly)

    def test_create_entry_with_other_entrys_image_as_cover_should_be_rejected(self):
        client = APIClient()
        client.force_authenticate(self.quan_ly)

        resp = client.post(
            "/api/content/entries/",
            {
                "kind": "post",
                "title": "Bai moi dung anh cua bai A (IDOR)",
                "category": self.category.id,
                "cover_image": self.img_a.pk,
                "body": {"type": "doc", "blocks": []},
            },
            format="json",
        )

        # KỲ VỌNG (đúng theo BR-ND-07): 400, không tạo được bài dùng ảnh không thuộc về nó.
        # THỰC TẾ (lỗi F1 hiện còn): 201 — bài mới được tạo, cover_image trỏ ảnh của bài A.
        self.assertEqual(
            resp.status_code,
            400,
            f"F1 IDOR vẫn còn: tạo bài với cover_image thuộc bài khác trả {resp.status_code} "
            f"(mong 400 BR-ND-07). Body: {resp.content}",
        )
