"""
Sửa theo code review trước deploy 1 — R2: cấu hình an toàn mặc định (config/settings.py).

- DEBUG mặc định TẮT khi không có DJANGO_DEBUG (dev local bật bằng .env: DJANGO_DEBUG=1).
- DEBUG tắt mà DJANGO_SECRET_KEY thiếu / rỗng / là key dev hay placeholder của .env.example
  → ImproperlyConfigured ngay khi nạp settings (khởi động). `manage.py test` được miễn.

Chạy settings trong tiến trình con với môi trường kiểm soát được (không nạp .env của máy dev).
"""
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parents[3]
STRONG_KEY = "k" * 50

PROBE = (
    "import dotenv; dotenv.load_dotenv = lambda *a, **k: None; "  # bỏ qua .env máy dev
    "from django.core.exceptions import ImproperlyConfigured\n"
    "try:\n"
    "    import config.settings as s\n"
    "    print('DEBUG=%s' % s.DEBUG)\n"
    "except ImproperlyConfigured as exc:\n"
    "    print('IMPROPERLY:%s' % exc)\n"
)


def load_settings(env, argv=()):
    clean = {k: v for k, v in os.environ.items()
             if not k.startswith("DJANGO_")}
    clean.update(env)
    out = subprocess.run(
        [sys.executable, "-c", PROBE, *argv], cwd=BACKEND, env=clean,
        capture_output=True, text=True, timeout=60,
    )
    return (out.stdout + out.stderr).strip()


class R2SettingsSecurityTests(SimpleTestCase):
    def test_r2_debug_mac_dinh_tat(self):
        self.assertIn("DEBUG=False", load_settings({"DJANGO_SECRET_KEY": STRONG_KEY}))

    def test_r2_debug_tat_thieu_secret_key_bao_loi_khi_khoi_dong(self):
        for env in ({}, {"DJANGO_SECRET_KEY": ""}, {"DJANGO_SECRET_KEY": "   "},
                    {"DJANGO_SECRET_KEY": "dev-insecure-key-đổi-khi-lên-prod"},
                    {"DJANGO_SECRET_KEY": "đổi-thành-chuỗi-ngẫu-nhiên-dài"}):
            with self.subTest(env=env):
                out = load_settings({"DJANGO_DEBUG": "0", **env})
                self.assertIn("IMPROPERLY:", out)
                self.assertIn("DJANGO_SECRET_KEY", out)

    def test_r2_debug_tat_co_secret_key_that_chay_duoc(self):
        self.assertIn("DEBUG=False", load_settings({"DJANGO_DEBUG": "0",
                                                    "DJANGO_SECRET_KEY": STRONG_KEY}))

    def test_r2_dev_bat_debug_van_chay_voi_key_dev(self):
        self.assertIn("DEBUG=True", load_settings({"DJANGO_DEBUG": "1"}))

    def test_r2_chay_test_duoc_mien(self):
        self.assertIn("DEBUG=False", load_settings({"DJANGO_DEBUG": "0"}, argv=("test",)))
