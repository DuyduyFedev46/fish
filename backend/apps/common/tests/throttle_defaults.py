"""TD-04: đọc bảng tần suất MẶC ĐỊNH trong config/settings.py, không phụ thuộc biến môi trường THROTTLE_* của máy chạy."""
import importlib.util
import os
from pathlib import Path
from unittest import mock

import dotenv

SETTINGS_PATH = Path(__file__).resolve().parents[3] / "config" / "settings.py"


def default_throttle_rates() -> dict:
    """Nạp config/settings.py vào một module riêng (không đụng settings đang chạy) với mọi THROTTLE_* bị gỡ và không đọc .env."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("THROTTLE_")}
    with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(dotenv, "load_dotenv", lambda *a, **k: False):
        spec = importlib.util.spec_from_file_location("_throttle_defaults_settings", SETTINGS_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return dict(module._DEFAULT_THROTTLE_RATES)
