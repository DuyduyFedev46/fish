"""
P8b Lô 3: tên mới cho env, lệnh quản trị, logger và khoá JSON công khai của module xác nhận đơn.
- Env: `CONFIRMATION_*` đọc trước, `CSKH_*` là fallback tới Lô 5 (R11).
- Lệnh: `process_confirmation_deadlines` / `check_confirmation_job_health` là lệnh thật; tên cũ chỉ bọc gọi.
- Logger: `cangca.delivery.confirmation`, không ghi dữ liệu khách (bất biến 9).
- site-info: `confirmation_policy` cùng nội dung với `cskh_notice`, không có dữ liệu khách.
Dữ liệu dùng SĐT và địa chỉ giả.
"""
import json
import os
import subprocess
import sys
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.utils import timezone

from apps.common.tests.fixtures import client_for
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.delivery.tests.test_cskh_l2 import ConfirmationL2BaseTestCase  # naming: allow - tên tệp test_cskh_l*.py đổi ở Lô 5 (02c), khi đó sửa import này

BACKEND_DIR = Path(__file__).resolve().parents[3]
FAKE_PHONE = "0906667778"
NEW_LOGGER = "cangca.delivery.confirmation"

# (tên env mới, tên env cũ, giá trị thử, thuộc tính settings, giá trị đã ép kiểu)
ENV_CASES = (
    ("CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS", "CSKH_MAX_UNREACHABLE_ATTEMPTS", "7", "CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS", 7),
    ("CONFIRMATION_UNREACHABLE_WINDOW_MINUTES", "CSKH_UNREACHABLE_WINDOW_MINUTES", "41", "CONFIRMATION_UNREACHABLE_WINDOW_MINUTES", 41),
    ("CONFIRMATION_MIN_RETRY_MINUTES", "CSKH_MIN_RETRY_MINUTES", "11", "CONFIRMATION_MIN_RETRY_MINUTES", 11),
    ("CONFIRMATION_MANAGER_DECISION_MINUTES", "CSKH_MANAGER_DECISION_MINUTES", "42", "CONFIRMATION_MANAGER_DECISION_MINUTES", 42),
    ("CONFIRMATION_PII_RECENT_DAYS", "CSKH_PII_RECENT_DAYS", "9", "CONFIRMATION_PII_RECENT_DAYS", 9),
    ("CONFIRMATION_CLAIM_MINUTES", "CSKH_CLAIM_MINUTES", "6", "CONFIRMATION_CLAIM_MINUTES", 6),
    ("CONFIRMATION_EXTEND_MAX_HOURS", "CSKH_EXTEND_MAX_HOURS", "12", "CONFIRMATION_EXTEND_MAX_HOURS", 12),
    ("CONFIRMATION_WORKING_HOURS", "CSKH_WORKING_HOURS", "08:00-20:00", "CONFIRMATION_WORKING_HOURS", "08:00-20:00"),
    ("CONFIRMATION_QUEUE_ALERT_MINUTES", "CSKH_QUEUE_ALERT_MINUTES", "77", "CONFIRMATION_QUEUE_ALERT_MINUTES", 77),
    ("CONFIRMATION_AUTO_CANCEL_ENABLED", "CSKH_AUTO_CANCEL_ENABLED", "1", "CONFIRMATION_AUTO_CANCEL_ENABLED", True),
    ("CONFIRMATION_NOTICE_ENABLED", "CSKH_NOTICE_ENABLED", "0", "CONFIRMATION_NOTICE_ENABLED", False),
    ("THROTTLE_CUSTOMER_SEARCH", "THROTTLE_CSKH_SEARCH", "5/min", "CAVEVE_THROTTLE_RATES.customer_search", "5/min"),
)
ALL_ENV_NAMES = {name for case in ENV_CASES for name in case[:2]}


def _load_settings(extra_env):
    """Nạp config.settings trong tiến trình con sạch (settings đọc env lúc import, không đổi được tại chỗ)."""
    env = {k: v for k, v in os.environ.items() if k not in ALL_ENV_NAMES and k != "DATABASE_URL"}
    env.update({"DJANGO_DEBUG": "1", "DJANGO_SETTINGS_MODULE": "config.settings"})
    env.update(extra_env)
    attrs = [case[3] for case in ENV_CASES]
    # Thuộc tính dạng `DICT.key` đọc từ dict trong settings (throttle: giá trị thực nằm ở CAVEVE_THROTTLE_RATES).
    code = (
        "import json, config.settings as s\n"
        "def read(a):\n"
        "    name, _, key = a.partition('.')\n"
        "    value = getattr(s, name)\n"
        "    return value[key] if key else value\n"
        f"print(json.dumps({{a: read(a) for a in {attrs!r}}}))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 0, out.stderr[-800:]
    return json.loads(out.stdout.strip().splitlines()[-1])


class ConfirmationEnvNamesTests(ConfirmationL2BaseTestCase):
    def test_env_new_name_is_read(self):
        for new, _old, raw, attr, expected in ENV_CASES:
            with self.subTest(env=new):
                self.assertEqual(_load_settings({new: raw})[attr], expected)

    def test_env_legacy_name_still_works_as_fallback(self):
        for _new, old, raw, attr, expected in ENV_CASES:
            with self.subTest(env=old):
                self.assertEqual(_load_settings({old: raw})[attr], expected)

    def test_env_new_name_wins_over_legacy_when_both_set(self):
        for new, old, raw, attr, expected in ENV_CASES:
            with self.subTest(env=new):
                # Giá trị env cũ phải khác giá trị env mới để chứng minh tên mới thắng.
                if raw in ("0", "1"):
                    legacy_raw = "1" if raw == "0" else "0"
                elif "/" in raw:
                    legacy_raw = "99/min"
                elif ":" in raw:
                    legacy_raw = "09:00-10:00"
                else:
                    legacy_raw = "99"
                got = _load_settings({new: raw, old: legacy_raw})[attr]
                self.assertEqual(got, expected)

    def test_env_defaults_when_nothing_set(self):
        got = _load_settings({})
        self.assertEqual(got["CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS"], 3)
        self.assertEqual(got["CONFIRMATION_UNREACHABLE_WINDOW_MINUTES"], 30)
        self.assertEqual(got["CONFIRMATION_WORKING_HOURS"], "07:00-21:00")
        self.assertIs(got["CONFIRMATION_AUTO_CANCEL_ENABLED"], False)
        self.assertIs(got["CONFIRMATION_NOTICE_ENABLED"], True)
        self.assertEqual(got["CAVEVE_THROTTLE_RATES.customer_search"], "30/min")


class ConfirmationCommandTests(ConfirmationL2BaseTestCase):
    def _make_escalatable_task(self, code="DH-CMD-1"):
        """Một phiếu đã gọi không được, cửa sổ chờ đã hết hạn -> lệnh phải chuyển Quản lý."""
        _, _, note, task = self._create_paid_order(code, FAKE_PHONE)
        past = timezone.now() - timedelta(minutes=90)
        ConfirmationTask.objects.filter(pk=task.pk).update(attempts=1, first_unreachable_at=past)
        return note, task

    def _run(self, name, **kwargs):
        out, err = StringIO(), StringIO()
        call_command(name, stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()

    def test_new_process_command_escalates_and_is_idempotent(self):
        _, task = self._make_escalatable_task()
        out, _ = self._run("process_confirmation_deadlines")
        self.assertIn("Đã chuyển Quản lý 1 phiếu", out)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        out2, _ = self._run("process_confirmation_deadlines")
        self.assertIn("Đã chuyển Quản lý 0 phiếu", out2)

    def test_old_process_command_wraps_new_and_gives_same_effect(self):
        _, task = self._make_escalatable_task("DH-CMD-2")
        out, _ = self._run("process_cskh_deadlines")
        self.assertIn("Đã chuyển Quản lý 1 phiếu", out)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        out2, _ = self._run("process_confirmation_deadlines")
        self.assertIn("Đã chuyển Quản lý 0 phiếu", out2)

    def test_process_commands_leave_no_personal_data_in_output(self):
        self._make_escalatable_task("DH-CMD-3")
        for name in ("process_confirmation_deadlines", "process_cskh_deadlines"):
            out, err = self._run(name)
            self.assertNotIn(FAKE_PHONE, out + err)
            self.assertNotIn("Nguyễn Huệ", out + err)

    def test_health_commands_ok_when_nothing_stale(self):
        for name in ("check_confirmation_job_health", "check_cskh_job_health"):
            out, err = self._run(name)
            self.assertIn("khoẻ", out, name)
            self.assertEqual(err, "", name)

    def test_health_commands_exit_1_and_log_to_new_logger_without_personal_data(self):
        self._make_escalatable_task("DH-CMD-4")
        for name in ("check_confirmation_job_health", "check_cskh_job_health"):
            with self.subTest(command=name):
                with self.assertLogs(NEW_LOGGER, level="ERROR") as logs:
                    with self.assertRaises(SystemExit) as exit_ctx:
                        self._run(name)
                self.assertEqual(exit_ctx.exception.code, 1)
                joined = "\n".join(logs.output)
                self.assertIn("quá hạn", joined)
                self.assertNotIn(FAKE_PHONE, joined)
                self.assertNotIn("Nguyễn Huệ", joined)
                self.assertNotIn("Khách DH-CMD-4", joined)

    def test_old_health_command_passes_grace_minutes_through(self):
        """Với --grace-minutes đủ lớn thì phiếu trễ 60 phút chưa bị coi là quá hạn."""
        self._make_escalatable_task("DH-CMD-5")
        out, _ = self._run("check_cskh_job_health", grace_minutes=10_000)
        self.assertIn("khoẻ", out)

    def test_services_use_new_logger_name(self):
        self.assertEqual(confirmation_services.logger.name, NEW_LOGGER)


class ConfirmationPolicyPublicKeyTests(ConfirmationL2BaseTestCase):
    def test_site_info_has_confirmation_policy_equal_to_legacy_notice(self):
        res = client_for(None).get("/api/public/site-info/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["confirmation_policy"], body["cskh_notice"])
        self.assertEqual(
            set(body["confirmation_policy"]),
            {"enabled", "working_hours", "max_attempts", "window_minutes", "decision_minutes",
             "auto_cancel_enabled", "refund_deadline_days", "hotline"},
        )

    def test_site_info_public_payload_has_no_customer_data_or_cost(self):
        """Có đơn thật trong DB nhưng API công khai không chứa tên, SĐT, địa chỉ khách hay giá vốn."""
        self._create_paid_order("DH-PUB-1", FAKE_PHONE)
        res = client_for(None).get("/api/public/site-info/")
        self.assertEqual(res.status_code, 200)
        text = res.content.decode()
        for forbidden in (FAKE_PHONE, "Nguyễn Huệ", "Khách DH-PUB-1", "valuation_rate", "cost_per_kg", "landed_cost"):
            self.assertNotIn(forbidden, text)

    def test_site_info_policy_follows_overridden_settings(self):
        from django.test import override_settings

        with override_settings(CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS=2, CONFIRMATION_NOTICE_ENABLED=False):
            body = client_for(None).get("/api/public/site-info/").json()
        self.assertEqual(body["confirmation_policy"]["max_attempts"], 2)
        self.assertIs(body["confirmation_policy"]["enabled"], False)
        self.assertEqual(body["confirmation_policy"], body["cskh_notice"])
