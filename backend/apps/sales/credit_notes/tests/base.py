"""Dữ liệu nền dùng chung cho test chứng từ đảo doanh thu (P8 Lô 4). Toàn bộ dữ liệu giả."""
import datetime
from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from apps.common.tests.fixtures import make_user
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask
from apps.delivery.tests.test_cskh_l3 import ConfirmationL3BaseTestCase
from apps.accounts import roles

# Sentinel dữ liệu cá nhân giả — không được xuất hiện ở chứng từ/timeline/audit/output lệnh.
SENTINEL_NAME = "Khách Giả Bí Mật"
SENTINEL_PHONE = "0900000123"
SENTINEL_ADDRESS = "Số 1 Đường Thử"


def find_keys(node, keys):
    """Quét đệ quy JSON, trả tập khoá thuộc `keys` tìm thấy."""
    found = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k in keys:
                found.add(k)
            found |= find_keys(v, keys)
    elif isinstance(node, list):
        for v in node:
            found |= find_keys(v, keys)
    return found


class CreditNoteBase(ConfirmationL3BaseTestCase):
    """Lô X 100 kg giá mua 110.000, giá bán 150.000 (fixture ConfirmationL3BaseTestCase)."""

    def setUp(self):
        super().setUp()
        self.giao = make_user("giao1", roles.DELIVERY_STAFF)

    def _paid(self, *, phone=SENTINEL_PHONE, name=SENTINEL_NAME, qty=Decimal("2")):
        order, note, task = self._create_order_with_confirmation(phone=phone, name=name, qty=qty)
        return order, note, task

    @override_settings(CSKH_AUTO_CANCEL_ENABLED=True)
    def _auto_cancel(self, task):
        """Đường job tự huỷ CSKH (`auto_cancel_overdue`) — actor=None."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = t0
        task.save()
        return confirmation_services.auto_cancel_overdue(now=t0 + timedelta(minutes=31))
