"""W37 S1 (BR-BH-18): luật thuần "giao xong phiếu cuối thì đơn Hoàn tất", bảng ca UC-4."""
from django.test import SimpleTestCase

from apps.delivery.models import DeliveryNote
from apps.sales.orders.completion import is_delivery_finished

S = DeliveryNote.Status


class IsDeliveryFinishedTests(SimpleTestCase):
    def test_s1_ac8_single_completed_note_is_finished(self):
        self.assertTrue(is_delivery_finished([S.COMPLETED]))

    def test_s1_ac8_cancelled_notes_are_ignored(self):
        self.assertTrue(is_delivery_finished([S.COMPLETED, S.CANCELLED, S.COMPLETED]))

    def test_s1_ac7_failed_note_blocks(self):
        self.assertFalse(is_delivery_finished([S.COMPLETED, S.FAILED]))

    def test_s1_ac7_any_open_note_blocks(self):
        for open_status in (S.CONFIRMING, S.PREPARING, S.READY, S.DELIVERING, S.FAILED):
            with self.subTest(open_status=open_status):
                self.assertFalse(is_delivery_finished([S.COMPLETED, open_status]))

    def test_all_cancelled_is_not_finished(self):
        self.assertFalse(is_delivery_finished([S.CANCELLED, S.CANCELLED]))

    def test_empty_is_not_finished(self):
        self.assertFalse(is_delivery_finished([]))
