"""
Test cho Báo cáo AI cuối ngày cho Chủ (DW-22-AC1..AC5, 02b §6.6, BR-AI-26).
"""
import datetime
from django.contrib.auth.models import User, Group, Permission
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.models import AiAction


class DailyAiReportTests(APITestCase):
    def setUp(self):
        # 1. Tạo nhóm và quyền
        self.chu_group, _ = Group.objects.get_or_create(name="chu")
        self.quan_ly_group, _ = Group.objects.get_or_create(name="quan_ly")
        self.nv_kho_group, _ = Group.objects.get_or_create(name="nv_kho")

        perm_policy = Permission.objects.filter(codename="manage_ai_policy").first()
        if perm_policy:
            self.chu_group.permissions.add(perm_policy)

        # 2. Tạo users
        self.chu_user = User.objects.create_user(
            username="chu_vua", password="password", first_name="Duy", last_name="Chủ"
        )
        self.chu_user.groups.add(self.chu_group)
        if perm_policy:
            self.chu_user.user_permissions.add(perm_policy)

        self.quan_ly = User.objects.create_user(
            username="quan_ly_1", password="password", first_name="Linh", last_name="QL"
        )
        self.quan_ly.groups.add(self.quan_ly_group)

        self.nv_kho = User.objects.create_user(
            username="nv_kho_1", password="password", first_name="Tuấn", last_name="Kho"
        )
        self.nv_kho.groups.add(self.nv_kho_group)

    def test_dw22_ac1_counts_and_items(self):
        """
        DW-22-AC1: Ngày 28/09 có 3 việc B, 1 hoàn tác, 2 nháp C duyệt, 1 nháp hết hạn, 1 chuyển việc
        -> by_user đếm đúng từng cột; items liệt kê đủ (BR-AI-26).
        """
        report_date = datetime.date(2026, 9, 28)
        created_dt = timezone.make_aware(datetime.datetime.combine(report_date, datetime.time(10, 0)))

        # 3 việc B
        for i in range(3):
            AiAction.objects.create(
                command="purchasing.purchasereceipt.nhap_lo",
                kind=AiAction.Kind.WRITE,
                level=AiAction.Level.B,
                status=AiAction.Status.DONE,
                owner=self.nv_kho,
            )

        # 1 việc hoàn tác (status=UNDONE)
        AiAction.objects.create(
            command="purchasing.purchasereceipt.nhap_lo",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.B,
            status=AiAction.Status.UNDONE,
            owner=self.nv_kho,
        )

        # 2 nháp C duyệt (status=CONFIRMED)
        for i in range(2):
            AiAction.objects.create(
                command="sales.refund.create_refund",
                kind=AiAction.Kind.WRITE,
                level=AiAction.Level.C,
                status=AiAction.Status.CONFIRMED,
                owner=self.nv_kho,
            )

        # 1 nháp C hết hạn (status=EXPIRED)
        AiAction.objects.create(
            command="sales.refund.create_refund",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.C,
            status=AiAction.Status.EXPIRED,
            owner=self.nv_kho,
        )

        # 1 chuyển việc (status=ESCALATED)
        AiAction.objects.create(
            command="inventory.batch.close",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.C,
            status=AiAction.Status.ESCALATED,
            owner=self.nv_kho,
        )

        AiAction.objects.all().update(created_at=created_dt)

        self.client.force_authenticate(user=self.chu_user)
        res = self.client.get("/api/ai/report/daily/?date=2026-09-28")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["date"], "2026-09-28")
        self.assertEqual(len(data["by_user"]), 1)

        user_stat = data["by_user"][0]
        self.assertEqual(user_stat["user_id"], self.nv_kho.id)
        # 3 việc B DONE + 1 việc B UNDONE = 4 việc B
        self.assertEqual(user_stat["B"], 4)
        self.assertEqual(user_stat["undone"], 1)
        self.assertEqual(user_stat["C_confirmed"], 2)
        self.assertEqual(user_stat["C_expired"], 1)
        self.assertEqual(user_stat["escalated"], 1)

        # Tổng số items là 8
        self.assertEqual(len(data["items"]), 8)

    def test_dw22_ac2_empty_and_invalid_date(self):
        """
        DW-22-AC2: Ngày không có việc -> 200 danh sách rỗng; ngày sai định dạng -> 400.
        """
        self.client.force_authenticate(user=self.chu_user)

        # Ngày không có việc
        res = self.client.get("/api/ai/report/daily/?date=2020-01-01")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["by_user"], [])
        self.assertEqual(res.data["items"], [])

        # Ngày sai định dạng
        res_bad = self.client.get("/api/ai/report/daily/?date=28-09-2026")
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_bad.data["code"], "INVALID_DATE")

    def test_dw22_ac3_permission_check(self):
        """
        DW-22-AC3: quan_ly, nv_* không có quyền -> 403 BR-PQ-12.
        """
        for user in [self.quan_ly, self.nv_kho]:
            self.client.force_authenticate(user=user)
            res = self.client.get("/api/ai/report/daily/?date=2026-09-28")
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(res.data["code"], "BR-PQ-12")

    def test_dw22_ac4_no_pii_no_costprice(self):
        """
        DW-22-AC4: Việc đụng đơn có PII giả -> chỉ trả mã chứng từ, không rò PII (Bất biến 9) và giá vốn (Bất biến 1).
        """
        report_date = datetime.date(2026, 9, 28)
        created_dt = timezone.make_aware(datetime.datetime.combine(report_date, datetime.time(14, 0)))

        AiAction.objects.create(
            command="delivery.deliverynote.confirm",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.B,
            status=AiAction.Status.DONE,
            owner=self.nv_kho,
            target_model="deliverynote",
            target_id="DN-20260928-001",
            args={
                "customer_name": "Nguyễn Văn A (Dữ liệu giả)",
                "phone": "0987654321",
                "shipping_address": "123 Đường Giả Lập",
                "unit_cost": 150000,
                "profit": 35000,
            },
            result_ref={"model": "deliverynote", "id": 123},
        )
        AiAction.objects.all().update(created_at=created_dt)

        self.client.force_authenticate(user=self.chu_user)
        res = self.client.get("/api/ai/report/daily/?date=2026-09-28")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        item = res.data["items"][0]
        # Target chỉ chứa type + code (DW-22-AC4)
        self.assertEqual(item["target"], {"type": "deliverynote", "code": "DN-20260928-001"})
        self.assertEqual(item["result_ref"], {"model": "deliverynote", "id": 123})

        # Toàn bộ response string không được chứa PII hay giá vốn
        content_str = str(res.data)
        self.assertNotIn("0987654321", content_str)
        self.assertNotIn("Nguyễn Văn A", content_str)
        self.assertNotIn("123 Đường Giả Lập", content_str)
        self.assertNotIn("150000", content_str)
        self.assertNotIn("35000", content_str)

    @override_settings(AI_ENABLED=False)
    def test_dw22_ac5_ai_disabled_still_accessible(self):
        """
        DW-22-AC5: AI_ENABLED=false -> vẫn xem được lịch sử báo cáo (BR-AI-10).
        """
        self.client.force_authenticate(user=self.chu_user)
        res = self.client.get("/api/ai/report/daily/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
