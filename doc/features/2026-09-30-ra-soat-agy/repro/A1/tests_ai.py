import datetime
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.ai.models import AiAction
from apps.ai.models.config import AiConfigVersion
from apps.common.tests.fixtures import make_user


class A1AiTests(APITestCase):
    def setUp(self):
        self.chu = make_user("chu_a1", "chu")
        self.kho = make_user("kho_a1", "nv_kho")

    @override_settings(AI_ENABLED=True)
    def test_nhan_vien_tu_bat_lai_sau_khi_chu_tat(self):
        self.client.force_authenticate(self.chu)
        r = self.client.post(f"/api/ai/policy/users/{self.kho.pk}/kill/", {"killed": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.client.force_authenticate(self.kho)
        r2 = self.client.post("/api/ai/my-config/kill/", {"killed": False}, format="json")
        latest = AiConfigVersion.objects.filter(user=self.kho).order_by("-version").first()
        print("\nkho un-kill status", r2.status_code, "killed now", latest.killed)
        self.assertTrue(latest.killed, "NV tự bật lại được AI Chủ đã tắt")

    @override_settings(AI_ENABLED=True, AI_CONFIRM_MIN_SECONDS=0)
    def test_nonce_khong_duoc_kiem(self):
        act = AiAction.objects.create(
            command="inventory.batch.list", kind=AiAction.Kind.WRITE, level=AiAction.Level.C,
            status=AiAction.Status.PENDING, owner=self.kho, args={},
            expires_at=timezone.now() + datetime.timedelta(minutes=10),
            viewed_at=timezone.now() - datetime.timedelta(seconds=10),
        )
        # Chủ chưa từng mở chi tiết; nonce sai
        self.client.force_authenticate(self.chu)
        r = self.client.post(f"/api/ai/actions/{act.pk}/confirm/", {"confirm_nonce": "sai-hoan-toan"}, format="json")
        print("\nconfirm with wrong nonce ->", r.status_code, r.json())
        self.assertNotEqual(r.status_code, 200, "nonce sai vẫn duyệt được")
