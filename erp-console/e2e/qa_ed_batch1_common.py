"""Hàm dùng chung cho các kịch bản QA độc lập của ERP theo design, đợt 1 (khung + mẫu danh sách).

Chạy trên bản build MOCK phục vụ tĩnh:
    cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &)
Dữ liệu chỉ là dữ liệu giả của mock. Không dùng wait_for_timeout cố định để chấm đạt; chỉ chờ điều kiện.
"""

import os
import pathlib

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp/qa_ed_batch1")
OUT_404 = pathlib.Path(__file__).resolve().parent.parent / "out" / "404.html"
BOARDS = "file:///Users/dangthiduyen/Downloads/loc/doc/design/erp/screens/"
pathlib.Path(SHOTS).mkdir(parents=True, exist_ok=True)

results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:400]), flush=True)


def summary():
    passed = sum(1 for _, c, _ in results if c)
    print(f"== {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


# Thứ tự đầy đủ của menu trái chép từ UI-RULES §2.1 (nguồn độc lập, không lấy từ nav.ts).
FULL_ORDER = [
    "Tổng quan",
    "Đơn & tiền", "Khách hàng", "Gọi xác nhận", "Giao hàng", "Việc giao của tôi",
    "Mua hàng", "Nhà cung cấp", "Kho & lô", "Hàng hoàn về kho", "Kiểm kê", "Sổ nhập xuất", "Danh mục & giá",
    "Báo cáo lãi lỗ", "Hoá đơn bán", "Hoá đơn mua & chi phí",
    "Nội dung",
    "Nhân sự", "Phân quyền", "Nhật ký hoạt động", "Chính sách AI", "Báo cáo AI",
]
SECTION_ORDER = ["Bán hàng", "Hàng hoá & kho", "Kế toán", "Website", "Quản trị"]
SECTION_OF = {
    **{k: "" for k in ["Tổng quan"]},
    **{k: "Bán hàng" for k in ["Đơn & tiền", "Khách hàng", "Gọi xác nhận", "Giao hàng", "Việc giao của tôi"]},
    **{k: "Hàng hoá & kho" for k in ["Mua hàng", "Nhà cung cấp", "Kho & lô", "Hàng hoàn về kho", "Kiểm kê", "Sổ nhập xuất", "Danh mục & giá"]},
    **{k: "Kế toán" for k in ["Báo cáo lãi lỗ", "Hoá đơn bán", "Hoá đơn mua & chi phí"]},
    "Nội dung": "Website",
    **{k: "Quản trị" for k in ["Nhân sự", "Phân quyền", "Nhật ký hoạt động", "Chính sách AI", "Báo cáo AI"]},
}


def is_subsequence(sub, full):
    it = iter(full)
    return all(x in it for x in sub)


def login(page, user, pw="demo1234", wait_nav=True):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    if wait_nav:
        page.wait_for_selector(".nav a", state="attached")
    page.wait_for_load_state("networkidle")


def nav_labels(page):
    return [t.split("\n")[-1].strip() for t in page.locator("#rail-left .nav a").all_inner_texts()]


def nav_heads(page):
    return [t.strip() for t in page.locator("#rail-left .nav-h").all_inner_texts()]


def fonts_ready(page):
    page.wait_for_function("() => document.fonts.status === 'loaded'")


def relevant_errors(errors):
    return [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e
            and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]


def fulfil_404(page, path_glob):
    body = OUT_404.read_text(encoding="utf-8")
    page.route(path_glob, lambda route: route.fulfill(status=404, content_type="text/html; charset=utf-8", body=body))
