"""
Kiểm thử cảnh báo SĐT và giá vốn trước khi đăng (CMS-08-AC1..AC8, §9 02b-tech-design).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog
from apps.content.body.scan import scan_entry_warnings
from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion
from apps.content.models.images import ContentImage

User = get_user_model()


class ScanWarningsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # User quản lý
        self.quan_ly = User.objects.create_user(username="quan_ly", password="password123")
        group_ql, _ = Group.objects.get_or_create(name="quan_ly")
        for perm_code in ("view_entry", "add_entry", "change_entry", "delete_entry", "publish_entry"):
            perm = Permission.objects.get(codename=perm_code, content_type__app_label="content")
            group_ql.permissions.add(perm)
        self.quan_ly.groups.add(group_ql)

        # User NV giao
        self.nv_giao = User.objects.create_user(username="nv_giao", password="password123")
        group_giao, _ = Group.objects.get_or_create(name="nv_giao")
        self.nv_giao.groups.add(group_giao)

        self.category = Category.objects.create(
            name="Cá tươi",
            name_key="ca tuoi",
            slug="ca-tuoi",
            is_active=True,
        )

        self.entry = Entry.objects.create(
            kind="post",
            title="Kinh nghiệm chọn cá tươi ngon",
            slug="kinh-nghiem-chon-ca-tuoi-ngon",
            category=self.category,
            excerpt="Mẹo nhận biết cá tươi đánh bắt trong ngày",
            seo_title="Kinh nghiệm chọn cá tươi",
            seo_description="Bí quyết chọn cá tươi ngon tại cảng",
            body={
                "type": "doc",
                "blocks": [
                    {
                        "type": "paragraph",
                        "children": [{"text": "Xem mắt cá và mang cá thật kỹ."}],
                    }
                ],
            },
            source="human",
            row_version=1,
            created_by=self.quan_ly,
            updated_by=self.quan_ly,
        )

        self.cover_image = ContentImage.objects.create(
            entry=self.entry,
            alt="Đĩa cá tươi",
            width=1600,
            height=1200,
            uploaded_by=self.quan_ly,
        )
        self.entry.cover_image = self.cover_image
        self.entry.save()

    def test_cms_08_ac1_phone_formats_detected_and_masked(self):
        """
        CMS-08-AC1: Thân bài chứa 0912 345 678, 0912.345.678, +84 912345678, 84912345678
        -> 409 CONTENT_WARNINGS, phone_like, snippet đã che (chỉ lộ 3 số cuối).
        """
        phone_cases = [
            "0912 345 678",
            "0912.345.678",
            "+84 912345678",
            "84912345678",
        ]

        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"

        for phone in phone_cases:
            self.entry.body = {
                "type": "doc",
                "blocks": [
                    {
                        "type": "paragraph",
                        "children": [{"text": f"Mọi chi tiết xin vui lòng gọi chị Lan {phone} để hỗ trợ."}],
                    }
                ],
            }
            self.entry.save()

            res = self.client.post(
                url,
                {
                    "row_version": self.entry.row_version,
                    "checklist_confirmed": True,
                    "acknowledge_warnings": False,
                },
            )
            self.assertEqual(res.status_code, status.HTTP_409_CONFLICT, f"Không phát hiện SĐT {phone}")
            self.assertEqual(res.data.get("code"), "CONTENT_WARNINGS")
            warnings = res.data.get("warnings", [])
            phone_warnings = [w for w in warnings if w.get("type") == "phone_like"]
            self.assertTrue(len(phone_warnings) > 0)
            snippet = phone_warnings[0]["snippet"]
            # Không được lộ số điện thoại đầy đủ
            self.assertNotIn("912345678", snippet)
            self.assertNotIn("345 678", snippet)
            # Lộ dạng đã che 09xx xxx 678
            self.assertIn("xx xxx", snippet)
            self.assertIn("678", snippet)

    def test_cms_08_ac2_cost_keyword_detected(self):
        """CMS-08-AC2: Thân bài chứa 'giá mua tại cảng 80k' -> 409 CONTENT_WARNINGS có cost_keyword."""
        self.entry.body = {
            "type": "doc",
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [{"text": "Lô cá này giá mua tại cảng 80k một ký."}],
                }
            ],
        }
        self.entry.save()

        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
                "acknowledge_warnings": False,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res.data.get("code"), "CONTENT_WARNINGS")
        warnings = res.data.get("warnings", [])
        cost_warnings = [w for w in warnings if w.get("type") == "cost_keyword"]
        self.assertTrue(len(cost_warnings) > 0)
        self.assertEqual(cost_warnings[0]["field"], "body")

    def test_cms_08_ac3_false_positives_not_warned(self):
        """
        CMS-08-AC3: Các chuỗi 250.000đ, 1.200 kg, 28/09/2026, SO-2026-00012, 10.000.000 đ
        -> Không có cảnh báo phone_like.
        """
        self.entry.body = {
            "type": "doc",
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [
                        {
                            "text": "Giá cá 250.000đ/kg hoặc 1.200 kg nhập ngày 28/09/2026 theo đơn SO-2026-00012 tổng 10.000.000 đ."
                        }
                    ],
                }
            ],
        }
        self.entry.save()

        warnings = scan_entry_warnings(self.entry)
        phone_warnings = [w for w in warnings if w.get("type") == "phone_like"]
        self.assertEqual(phone_warnings, [])

    @override_settings(CONTENT_PHONE_ALLOWLIST=("0901234567",))
    def test_cms_08_ac4_allowlist_phone_not_warned(self):
        """CMS-08-AC4: Số trong CONTENT_PHONE_ALLOWLIST (hotline vựa) không bị cảnh báo."""
        self.entry.body = {
            "type": "doc",
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [{"text": "Liên hệ hotline vựa: 0901 234 567 để đặt hàng."}],
                }
            ],
        }
        self.entry.save()

        warnings = scan_entry_warnings(self.entry)
        phone_warnings = [w for w in warnings if w.get("type") == "phone_like"]
        self.assertEqual(phone_warnings, [])

    def test_cms_08_ac5_acknowledge_warnings_publishes_and_logs(self):
        """
        CMS-08-AC5: Đã có cảnh báo -> acknowledge_warnings=True -> 200,
        AuditLog content_publish có warnings_acknowledged chỉ chứa loại cảnh báo.
        """
        self.entry.body = {
            "type": "doc",
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "Gọi 0912 345 678 và tham khảo giá mua 80k."}
                    ],
                }
            ],
        }
        self.entry.save()

        self.client.force_authenticate(user=self.quan_ly)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": self.entry.row_version,
                "checklist_confirmed": True,
                "acknowledge_warnings": True,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        log = AuditLog.objects.latest("id")
        self.assertIn("warnings_acknowledged", log.changes)
        warn_types = log.changes["warnings_acknowledged"]
        self.assertIn("phone_like", warn_types)
        self.assertIn("cost_keyword", warn_types)
        # AuditLog không chứa số điện thoại hay chuỗi nhạy cảm
        self.assertNotIn("0912", str(log.changes))
        self.assertNotIn("80k", str(log.changes))

    def test_cms_08_ac6_phone_in_image_alt_warned(self):
        """CMS-08-AC6: Chuỗi giống SĐT nằm ở alt ảnh -> cảnh báo field='image_alt'."""
        self.cover_image.alt = "Ảnh cá thu liên hệ 0912 345 678"
        self.cover_image.save()

        warnings = scan_entry_warnings(self.entry)
        alt_warnings = [w for w in warnings if w.get("field") == "image_alt" and w.get("type") == "phone_like"]
        self.assertTrue(len(alt_warnings) > 0)

    def test_cms_08_ac8_nv_giao_publish_with_acknowledge_403_before_scan(self):
        """CMS-08-AC8: NV giao gọi publish với acknowledge_warnings=True -> 403 (kiểm quyền trước khi quét)."""
        self.client.force_authenticate(user=self.nv_giao)
        url = f"/api/content/entries/{self.entry.pk}/publish/"
        res = self.client.post(
            url,
            {
                "row_version": 1,
                "checklist_confirmed": True,
                "acknowledge_warnings": True,
            },
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
