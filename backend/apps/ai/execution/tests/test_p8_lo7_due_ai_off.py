"""
P8 Lô 7 — nợ Lô 1 L4: `run_due_ai_actions` khi AI_ENABLED=false vẫn cô lập lỗi từng việc
(một việc lỗi không làm dừng cả job, các việc sau vẫn được hạ về C). Dữ liệu giả.
"""
import datetime
import logging
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.models import AiAction
from apps.common.tests.fixtures import make_user
from apps.accounts import roles


@override_settings(AI_ENABLED=False)
class L4AiOffIsolationTests(TestCase):
    def setUp(self):
        self.kho = make_user("l4_kho", roles.WAREHOUSE_STAFF)
        past = timezone.now() - datetime.timedelta(minutes=1)
        self.acts = [
            AiAction.objects.create(
                command="inventory.batch.close", kind=AiAction.Kind.WRITE, level=AiAction.Level.B,
                status=AiAction.Status.SCHEDULED, owner=self.kho, target_model="batch",
                target_id=str(i), args={}, execute_after=past,
            )
            for i in (1, 2, 3)
        ]

    def test_l4_mot_viec_loi_khong_chan_cac_viec_sau(self):
        real_save = AiAction.save
        bad_pk = self.acts[0].pk

        def flaky(instance, *args, **kwargs):
            if instance.pk == bad_pk:
                raise RuntimeError("Khách Giả B 0900000999")
            return real_save(instance, *args, **kwargs)

        out = StringIO()
        with mock.patch.object(AiAction, "save", autospec=True, side_effect=flaky), \
             self.assertLogs("apps.ai.management.commands.run_due_ai_actions", level=logging.WARNING) as cm:
            call_command("run_due_ai_actions", stdout=out)

        statuses = {a.pk: AiAction.objects.get(pk=a.pk).status for a in self.acts}
        self.assertEqual(statuses[bad_pk], AiAction.Status.SCHEDULED)  # rollback, thử lại lần chạy sau
        others = [a.pk for a in self.acts if a.pk != bad_pk]
        for pk in others:
            self.assertEqual(statuses[pk], AiAction.Status.PENDING)
            self.assertEqual(AiAction.objects.get(pk=pk).level, AiAction.Level.C)
        self.assertIn("downgraded 2", out.getvalue())
        log = "\n".join(cm.output)
        self.assertIn("RuntimeError", log)
        self.assertNotIn("0900000999", log)  # không log nội dung exception
