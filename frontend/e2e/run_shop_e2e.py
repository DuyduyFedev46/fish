#!/usr/bin/env python3
"""
Bộ e2e toàn luồng Shop Cá Về, chạy bằng MỘT lệnh (SHOP-7-01; thay các kịch bản cũ bám giao diện cũ).

    python3 frontend/e2e/run_shop_e2e.py                 # dựng môi trường + build Shop/ERP + chạy mọi kịch bản
    python3 frontend/e2e/run_shop_e2e.py --skip-build    # dùng sẵn frontend/out và erp-console/out (build USE_MOCK=0, API localhost:8000)
    python3 frontend/e2e/run_shop_e2e.py --suite full_flow --suite general_rules
    python3 frontend/e2e/run_shop_e2e.py --keep          # giữ thư mục DB tạm sau khi chạy (mặc định dọn sạch)

Yêu cầu: chạy từ máy dev; `backend/.venv` có Django, `npm ci` đã chạy ở frontend/ và erp-console/ (không --legacy-peer-deps),
Playwright Python + Chromium. Cổng cố định: BE 8000, Shop 3000, ERP 3100 (bản build gắn cứng API localhost:8000).
Môi trường dựng: SQLite tạm → migrate → seed_demo + seed_qa + shop_seed.py (nhóm, món sắp hết/hết, 2 combo) →
load_shop_content --publish → BE runserver. Cổng thanh toán giả lập qua cửa IPN nội bộ. Không đụng DB thật.

Kịch bản (mỗi cái là một file chạy được riêng, cần SHOP_E2E_WORKDIR do lệnh này đặt):
  payment_choice    SHOP-FIX-01: chọn PTTT ở form, đặt xong vào thẳng cổng, nhánh mở cổng lỗi (ảnh vào shots/qa)
  full_flow         khách đi trọn luồng 360 và 1280, nhánh lỗi, tra đơn từ phiên khác, quét dữ liệu cá nhân
  design_screens    86 màn thiết kế → ảnh 360/1280 cạnh bản thiết kế (ảnh vào thư mục shots/lo7)
  general_rules     AC chung G1–G8 trên toàn Shop (API, HTML, storage, popup, hex, code cũ, axe nếu có)
  erp_flow          ERP: Chủ tạo mã, sửa thông tin món, nạp nội dung, lãi lỗ theo lô có đơn dùng mã
  content_pages     trang CMS, Góc bếp, thẻ món trong bài, link an toàn, trang giới thiệu
  footer_consent    chân trang, ô đồng ý, chính sách đổi (409), shop đóng, quay về từ cổng thanh toán
  formats_timezones tiền/ngày giờ đúng định dạng VN ở 4 múi giờ trình duyệt
Thoát khác 0 nếu có kịch bản nào FAIL.
"""
import argparse
import http.server
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shop_e2e_lib import BACKEND, BE_PORT, ERP, ERP_PORT, FRONTEND, QA_PASSWORD, ROOT, SHOP_PORT  # noqa: E402

SUITES = ["payment_choice", "full_flow", "design_screens", "general_rules", "erp_flow", "content_pages", "footer_consent", "formats_timezones"]
PYTHON = str(BACKEND / ".venv/bin/python")


def be_env(workdir):
    return {
        "DATABASE_URL": f"sqlite:///{workdir}/e2e.sqlite3",
        "DJANGO_DEBUG": "1",
        "QA_PASSWORD": QA_PASSWORD,
        "INTERNAL_SERVICE_TOKEN": "e2e-internal-token",
        "CORS_ALLOWED_ORIGINS": f"http://localhost:{SHOP_PORT},http://localhost:{ERP_PORT}",
        "CSRF_TRUSTED_ORIGINS": f"http://localhost:{SHOP_PORT},http://localhost:{ERP_PORT}",
        # nâng giới hạn tần suất để luồng dài không tự chạm 429; kịch bản 429 dựng BE riêng với giới hạn thấp
        "THROTTLE_SHOP_LOOKUP_IP": "5000/min", "THROTTLE_SHOP_LOOKUP_ORDER": "5000/hour",
        "THROTTLE_SHOP_ORDER_CREATE": "5000/hour", "THROTTLE_SHOP_CHECKOUT": "5000/hour",
        "THROTTLE_SHOP_LOOKUP_TOKEN": "5000/min", "THROTTLE_SHOP_VOUCHER_CHECK": "5000/min",
        "THROTTLE_LOGIN_IP": "5000/min", "THROTTLE_LOGIN_USER": "5000/hour", "THROTTLE_PUBLIC_CONTENT": "50000/min",
        # như staging/production: có ô đồng ý, có thông tin người bán (giả)
        "PRIVACY_CONSENT_REQUIRED": "1",
        "SELLER_NAME": "Cá Về (dữ liệu giả)", "SELLER_BUSINESS_TYPE": "Hộ kinh doanh", "SELLER_REG_NO": "00A-000000",
        "SELLER_TAX_CODE": "0000000000", "SELLER_ADDRESS": "1 Đường Thử, Phan Thiết", "SELLER_PHONE": "0900000999",
        "SELLER_EMAIL": "gia@example.test",
    }


def run(cmd, env=None, cwd=None, stdin=None, label=""):
    print(f"$ {label or ' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, stdin=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-3000:], file=sys.stderr)
        sys.exit(f"Lỗi khi chạy: {label or cmd}")
    return r.stdout


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    """Phục vụ bản build tĩnh; đường không có thì trả 404.html với mã 404 (như Firebase Hosting)."""
    root = "."

    def __init__(self, *a, **k):
        super().__init__(*a, directory=self.root, **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        f = os.path.join(self.root, p.lstrip("/"))
        if os.path.isfile(f) or os.path.isfile(os.path.join(f, "index.html")) or os.path.isfile(f + ".html"):
            return super().do_GET()
        data = Path(self.root, "404.html").read_bytes() if Path(self.root, "404.html").exists() else b"404"
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve_static(root, port):
    handler = type("H", (StaticHandler,), {"root": str(root)})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def wait_http(url, tries=60):
    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=3)
            return
        except urllib.error.HTTPError:
            return
        except Exception:
            time.sleep(1)
    sys.exit(f"Không mở được {url}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--suite", action="append", choices=SUITES)
    ap.add_argument("--workdir")
    args = ap.parse_args()

    workdir = Path(args.workdir or tempfile.mkdtemp(prefix="shop_e2e_")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    env = be_env(workdir)
    api_env = {"NEXT_PUBLIC_API_BASE": f"http://localhost:{BE_PORT}", "NEXT_PUBLIC_USE_MOCK": "0"}

    if not args.skip_build:
        run(["npm", "run", "build"], env=api_env, cwd=FRONTEND, label="Shop: npm run build (USE_MOCK=0)")
        run(["npm", "run", "build"], env=api_env, cwd=ERP, label="ERP: npm run build (USE_MOCK=0)")
    run(["node", "scripts/check-no-mock.mjs"], cwd=FRONTEND, label="Shop: check-no-mock")

    mg = [PYTHON, "manage.py"]
    run(mg + ["migrate", "-v0"], env=env, cwd=BACKEND, label="migrate")
    run(mg + ["seed_demo"], env=env, cwd=BACKEND, label="seed_demo")
    run(mg + ["seed_qa", "--manifest", str(workdir / "qa_ids.json")], env=env, cwd=BACKEND, label="seed_qa")
    run(mg + ["shell"], env=env, cwd=BACKEND, stdin=open(Path(__file__).parent / "shop_seed.py"), label="shop_seed.py")
    run(mg + ["load_shop_content", "--author", "qa_owner", "--publish"], env=env, cwd=BACKEND, label="load_shop_content")
    (workdir / "env.json").write_text(json.dumps({"be_env": env, "internal_token": env["INTERNAL_SERVICE_TOKEN"]}))

    procs = []
    servers = []
    code = 0
    try:
        be = subprocess.Popen(mg + ["runserver", str(BE_PORT), "--noreload"], cwd=BACKEND, env={**os.environ, **env},
                              stdout=open(workdir / "be.log", "w"), stderr=subprocess.STDOUT)
        procs.append(be)
        servers.append(serve_static(FRONTEND / "out", SHOP_PORT))
        servers.append(serve_static(ERP / "out", ERP_PORT))
        wait_http(f"http://localhost:{BE_PORT}/api/shop/catalog/")
        wait_http(f"http://localhost:{SHOP_PORT}/shop/")
        wait_http(f"http://localhost:{ERP_PORT}/login/")

        results = {}
        for name in args.suite or SUITES:
            print(f"\n######## {name}", flush=True)
            r = subprocess.run([sys.executable, str(Path(__file__).parent / f"shop_{name}.py")],
                               env={**os.environ, "SHOP_E2E_WORKDIR": str(workdir)})
            results[name] = r.returncode
        print("\n======== TỔNG KẾT")
        for name, rc in results.items():
            rows = []
            f = workdir / f"result-{name}.json"
            if f.exists():
                rows = json.loads(f.read_text())
            p = sum(1 for x in rows if x["pass"] is True)
            fl = sum(1 for x in rows if x["pass"] is False)
            sk = sum(1 for x in rows if x["pass"] is None)
            print(f"{'PASS' if rc == 0 else 'FAIL'}  {name}: {p} đạt, {fl} lỗi, {sk} bỏ qua")
        code = 1 if any(results.values()) else 0
    finally:
        for p in procs:
            p.send_signal(signal.SIGTERM)
        for s in servers:
            s.shutdown()
        if args.keep:
            print(f"Giữ lại thư mục làm việc: {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
    sys.exit(code)


if __name__ == "__main__":
    main()
