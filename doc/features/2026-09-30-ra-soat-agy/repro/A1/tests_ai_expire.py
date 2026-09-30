import datetime
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.ai.models import AiAction
from apps.common.tests.fixtures import make_user


class A1AiExpire(APITestCase):
    @override_settings(AI_ENABLED=True, AI_CONFIRM_MIN_SECONDS=0)
    def test_expired_never_persisted_and_escalated(self):
        chu = make_user("chu_e", "chu"); kho = make_user("kho_e", "nv_kho")
        act = AiAction.objects.create(
            command="inventory.batch.list", kind=AiAction.Kind.WRITE, level=AiAction.Level.C,
            status=AiAction.Status.PENDING, owner=kho, args={},
            expires_at=timezone.now() - datetime.timedelta(minutes=1),
            viewed_at=timezone.now() - datetime.timedelta(seconds=10),
        )
        self.client.force_authenticate(kho)
        r = self.client.post(f"/api/ai/actions/{act.pk}/confirm/", {}, format="json")
        act.refresh_from_db()
        print("\nconfirm expired ->", r.status_code, "status in DB:", act.status)
        AiAction.objects.filter(pk=act.pk).update(created_at=timezone.now() - datetime.timedelta(hours=3))
        call_command("run_due_ai_actions")
        act.refresh_from_db()
        print("after job:", act.status, act.assignee_group)
        self.client.force_authenticate(chu)
        r2 = self.client.post(f"/api/ai/actions/{act.pk}/confirm/", {}, format="json")
        print("chu confirm escalated ->", r2.status_code, r2.json().get("code"))
        self.assertEqual(act.status, AiAction.Status.EXPIRED)
