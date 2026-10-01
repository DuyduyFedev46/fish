"""
P8 Lô 8 — SR-25 (BE): câu chữ gửi FE (thông điệp Shop, ngày hạn hoàn, giờ giữ việc) theo `x.xxx ₫` và giờ VN.
Chỉ dữ liệu giả. ISO trong JSON không đổi.
"""
from datetime import datetime, timedelta, timezone as dt_timezone

from django.test import override_settings
from django.utils import timezone

from apps.common.exceptions import ConflictError
from apps.common.tests.fixtures import client_for
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask
from apps.delivery.tests import test_cskh_l3 as l3
from apps.sales.models import Refund

# 17:30Z ngày 30/09 = 00:30 ngày 01/10 giờ VN; +30 ngày => hạn 31/10 (giờ VN), không phải 30/10 (UTC)
LATE_UTC = datetime(2026, 9, 30, 17, 30, tzinfo=dt_timezone.utc)


class Lo8CskhFormatTests(l3.ConfirmationL3BaseTestCase):
    def _auto_cancelled(self):
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="UNREACHABLE", now=t0)
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()
        confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
        task.refresh_from_db()
        order.refresh_from_db()
        return order, note, task

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True, REFUND_DEADLINE_DAYS=30)
    def test_sr25_ac1_cancel_notice_message_tien_vnd_dau_cham(self):
        """Câu báo khách tự huỷ: `Số tiền 300.000 ₫ sẽ được hoàn`; JSON refund.amount vẫn là chuỗi thô."""
        order, _note, _task = self._auto_cancelled()
        resp = client_for(None).get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        self.assertEqual(resp.status_code, 200)
        notice = resp.json()["cancel_notice"]
        self.assertIn("Số tiền 300.000 ₫ sẽ được hoàn", notice["message"])
        self.assertNotIn("300000đ", notice["message"])
        self.assertEqual(notice["refund"]["amount"], "300000")  # contract khoá, không đổi

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True, REFUND_DEADLINE_DAYS=30)
    def test_sr25_ac2_cskh_queue_refund_deadline_theo_ngay_vn(self):
        """Phiếu hoàn tạo 17:30Z (00:30 VN ngày kế) -> hạn = ngày VN + 30 ngày."""
        order, note, task = self._auto_cancelled()
        Refund.objects.filter(pk=task.refund.pk).update(created_at=LATE_UTC)
        resp = client_for(self.cs1).get("/api/cskh/queue/?state=REFUND_CALL")
        self.assertEqual(resp.status_code, 200)
        item = resp.json()["results"][0]
        self.assertEqual(item["refund"]["deadline"], "2026-10-31")

    @override_settings(CONFIRMATION_AUTO_CANCEL_ENABLED=True, REFUND_DEADLINE_DAYS=30)
    def test_sr25_ac2_shop_cancel_notice_deadline_theo_ngay_vn(self):
        order, note, task = self._auto_cancelled()
        Refund.objects.filter(pk=task.refund.pk).update(created_at=LATE_UTC)
        resp = client_for(None).get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        self.assertEqual(resp.json()["cancel_notice"]["refund"]["deadline"], "2026-10-31")

    def test_sr25_ac2_claim_conflict_gio_vn_con_iso_giu_nguyen(self):
        """Thông điệp `tới 00:30` theo giờ VN; `extra.claimed_until` ISO còn nguyên offset UTC."""
        _order, note, task = self._create_order_with_confirmation()
        now = LATE_UTC - timedelta(minutes=1)
        task.claimed_by = self.cs2
        task.claimed_until = LATE_UTC
        task.save()
        with self.assertRaises(ConflictError) as ctx:
            confirmation_services.claim_task(task.pk, self.cs1, now=now)
        self.assertIn("tới 00:30", str(ctx.exception))
        self.assertEqual(ctx.exception.extra["claimed_until"], "2026-09-30T17:30:00+00:00")
