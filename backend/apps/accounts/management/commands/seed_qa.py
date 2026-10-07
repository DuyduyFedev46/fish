"""
Dữ liệu giả cố định cho e2e chạy trên backend thật (lô dọn e2e, Duy duyệt 08/10).

    QA_PASSWORD=... manage.py seed_qa                 # dựng (idempotent) + in bảng mã → id + ghi JSON
    manage.py seed_qa --reset                         # xoá đúng bản ghi QA (tiền tố QA- / qa_)
    manage.py seed_qa --manifest /đường/dẫn.json      # đổi nơi ghi bảng mã → id (mặc định: thư mục tạm)

Vì sao là lệnh RIÊNG, không phải `seed_demo --qa`: `seed_demo` được phép chạy trên production và có sổ
`DemoRecord` riêng (`seed_demo --remove` gỡ theo sổ); trộn QA vào đó vừa làm bộ dữ liệu giả lọt vào luồng
production, vừa khiến `--remove` của demo kéo theo dữ liệu QA. `seed_qa` có cổng chặn riêng, KHÔNG BAO GIỜ chạy
trên production (xem apps/accounts/qa_fixture/guard.py) và nhận diện bản ghi bằng tiền tố mã.

Mật khẩu các tài khoản `qa_…` lấy từ biến môi trường `QA_PASSWORD` (không có mặc định, không in ra).
Chi tiết bộ dữ liệu: apps/accounts/qa_fixture/build.py và backend/README.md (mục seed_qa).
"""
import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.qa_fixture import guard
from apps.accounts.qa_fixture.build import QaSeed
from apps.accounts.qa_fixture.reset import reset_qa

DEFAULT_MANIFEST = Path("/tmp/seed_qa_ids.json")


class Command(BaseCommand):
    help = "Dựng (mặc định) hoặc xoá (--reset) bộ dữ liệu giả cố định cho e2e. Không chạy trên production."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Xoá đúng bản ghi QA (tiền tố QA-/qa_).")
        parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST),
                            help="Tệp JSON ghi bảng mã → id (mặc định: %(default)s).")
        parser.add_argument("--allow-non-local", action="store_true",
                            help="Cho chạy khi DEBUG tắt hoặc DB không phải SQLite/staging. "
                                 "Không bao giờ mở được cho DB giống production.")

    def handle(self, *args, **opts):
        guard.check_allowed(allow_non_local=opts["allow_non_local"])
        if opts["reset"]:
            return self._reset(Path(opts["manifest"]))
        password = os.environ.get("QA_PASSWORD", "")
        if not password:
            raise CommandError("Thiếu biến môi trường QA_PASSWORD (mật khẩu các tài khoản qa_…).")
        manifest = QaSeed(password=password).run()
        path = Path(opts["manifest"])
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        self._print_table(manifest)
        for warning in manifest["warnings"]:
            self.stdout.write(self.style.WARNING(warning))
        self.stdout.write(self.style.SUCCESS(f"seed_qa xong. Bảng mã → id: {path}"))

    def _reset(self, path):
        result = reset_qa()
        total = sum(result["deleted"].values())
        detail = ", ".join(f"{k}: {v}" for k, v in sorted(result["deleted"].items()))
        self.stdout.write(self.style.SUCCESS(f"Đã xoá {total} bản ghi QA" + (f" ({detail})." if detail else ".")))
        if result["kept"]:
            self.stdout.write(self.style.WARNING(
                "Còn giữ (dữ liệu khác đang tham chiếu): " + ", ".join(result["kept"])))
        if path.exists():
            path.unlink()

    def _print_table(self, manifest):
        for section in ("users", "orders", "delivery_notes", "payments", "refunds", "batches"):
            self.stdout.write(f"[{section}]")
            for code, value in manifest[section].items():
                ident = value["id"] if isinstance(value, dict) else value
                extra = f" ({value['status']})" if isinstance(value, dict) and "status" in value else ""
                self.stdout.write(f"  {code} -> {ident}{extra}")
