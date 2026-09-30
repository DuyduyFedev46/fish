# A4 CSKH — CS-11-AC6: PDF trang in tem phải là 1 trang, khổ 100x150mm (+/-1mm), QR giải mã đúng barcode_value.
# Chạy: cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3203 &)
#       SHOTS=<thư mục ảnh> python3 e2e/ra_soat_cs11_ac6_label_pdf.py     # tắt server sau khi xong
# Cần thư viện Python: pypdf (giải mã QR bằng cách sinh SVG tham chiếu qua đúng lib `qrcode` của erp-console,
# so khớp module data — máy không có bộ giải mã QR ảnh offline).
import os
import re
import subprocess
import sys

from playwright.sync_api import sync_playwright
import pypdf

BASE = os.environ.get("BASE", "http://127.0.0.1:3203")
SHOTS = os.environ.get("SHOTS", "/tmp")
NODE_MODULES_QRCODE = os.environ.get(
    "QRCODE_MODULE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "node_modules", "qrcode"),
)


def extract_qr_path_data(svg_html):
    """Lấy đúng dữ liệu module QR (thuộc tính d của path stroke) — bỏ qua khác biệt tự đóng thẻ khi trình
    duyệt serialize DOM so với chuỗi Node sinh ra."""
    m = re.search(r'stroke="#000000" d="([^"]+)"', svg_html)
    return m.group(1) if m else None


results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/overview/", timeout=10_000)


def gen_reference_svg(value):
    """Sinh SVG QR tham chiếu bằng đúng thư viện + tham số mà app/print/label/page.tsx dùng."""
    node_script = f"""
const QRCode = require({NODE_MODULES_QRCODE!r});
QRCode.toString({value!r}, {{type: 'svg', margin: 1, width: 140, errorCorrectionLevel: 'M'}}).then(svg => process.stdout.write(svg));
"""
    out = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
    return out.stdout


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    login(page, "kho1")

    # Note 31 = PREPARING, chưa in tem, có 2 dòng hàng (Tôm sú + Mực lá), địa chỉ mẫu ngắn.
    page.goto(BASE + "/deliveries/")
    page.wait_for_load_state("networkidle")
    page.get_by_text("GH-HD-0031-PREP").first.click()
    page.wait_for_timeout(500)

    with ctx.expect_page() as popup_info:
        page.get_by_role("button", name="In tem").click()
    label_page = popup_info.value
    label_page.wait_for_load_state("networkidle")
    label_page.wait_for_selector("text=GH-HD-0031-PREP", timeout=10_000)
    label_page.wait_for_timeout(600)  # chờ QR render xong (setQrSvg)

    # 1) Xuất PDF với preferCSSPageSize để tôn trọng @page { size: 100mm 150mm }
    pdf_path = os.path.join(SHOTS, "label-cs31.pdf")
    label_page.pdf(path=pdf_path, prefer_css_page_size=True)

    reader = pypdf.PdfReader(pdf_path)
    ok("CS-11-AC6 PDF đúng 1 trang", len(reader.pages) == 1, f"số trang={len(reader.pages)}")

    page0 = reader.pages[0]
    # MediaBox tính bằng points (1mm = 2.834645669 pt)
    width_pt = float(page0.mediabox.width)
    height_pt = float(page0.mediabox.height)
    width_mm = width_pt / 2.834645669
    height_mm = height_pt / 2.834645669
    ok(
        "CS-11-AC6 khổ 100x150mm (+/-1mm)",
        abs(width_mm - 100) <= 1 and abs(height_mm - 150) <= 1,
        f"width_mm={width_mm:.2f} height_mm={height_mm:.2f}",
    )

    # 2) Giải mã QR: sinh SVG tham chiếu bằng đúng lib+tham số app dùng, so khớp với SVG thật trên trang.
    expected_value = "GH-HD-0031-PREP.1"
    actual_svg = label_page.eval_on_selector(
        "[data-testid='label-qr'], svg", "el => el.closest('svg') ? el.closest('svg').outerHTML : el.outerHTML"
    )
    # Lấy đúng svg trong khối QR (loại icon khác nếu có)
    all_svgs = label_page.eval_on_selector_all("svg", "els => els.map(e => e.outerHTML)")
    qr_svg = None
    for s in all_svgs:
        if "shape-rendering=\"crispEdges\"" in s or "viewBox" in s:
            qr_svg = s
            break
    ok("CS-11-AC6 tìm thấy SVG QR trên trang", qr_svg is not None)

    ref_svg = gen_reference_svg(expected_value)
    actual_path = extract_qr_path_data(qr_svg or "")
    ref_path = extract_qr_path_data(ref_svg)
    ok(
        "CS-11-AC6 QR giải mã đúng barcode_value (khớp module data với SVG tham chiếu)",
        actual_path is not None and actual_path == ref_path,
        f"len_actual={len(actual_path or '')} len_ref={len(ref_path or '')}",
    )

    # QR không được trùng với encode của SĐT/URL/tên (bảo đảm không lộ khi giải mã)
    ref_svg_wrong = gen_reference_svg("0900000123")
    ref_path_wrong = extract_qr_path_data(ref_svg_wrong)
    ok("CS-11-AC6 QR KHÔNG chứa SĐT (không khớp module data của SĐT)", actual_path != ref_path_wrong)

    label_page.screenshot(path=os.path.join(SHOTS, "label-cs31.png"))

    browser.close()

print("\n=== TỔNG KẾT ===")
n_ok = sum(1 for _, c, _ in results if c)
print(f"{n_ok}/{len(results)} PASS")
if n_ok != len(results):
    sys.exit(1)
