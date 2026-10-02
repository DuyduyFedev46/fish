# QA độc lập Lô 11 vòng 2: InfoField dùng chung (bút sửa tại chỗ 44x44) trên màn khác ngoài Nhà cung cấp. MOCK :3101, dữ liệu giả.
#   BASE=http://127.0.0.1:3101 SHOTS=<thư mục> python3 e2e/qa_ed_batch11_mock_infofield.py
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=10000)
R = []


def ok(n, c, e=""):
    R.append((n, bool(c)))
    print("PASS" if c else "FAIL", n, "" if c else "  -> " + str(e)[:400], flush=True)


def login(page, user="loc"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("demo1234")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10000)


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10000)


def pencils(page):
    return page.evaluate("""() => [...document.querySelectorAll('button[aria-label^="Sửa "]')].filter(b => /pencil/.test(b.className)).map(b => { const r = b.getBoundingClientRect(); return {l: b.getAttribute('aria-label'), x: r.x, y: r.y, w: r.width, h: r.height}; })""")


def overlap(a, b):
    return a["x"] < b["x"] + b["w"] - 0.5 and b["x"] < a["x"] + a["w"] - 0.5 and a["y"] < b["y"] + b["h"] - 0.5 and b["y"] < a["y"] + a["h"] - 0.5


with sync_playwright() as p:
    br = p.chromium.launch()
    errs = []
    for w, h, touch in ((360, 800, True), (1280, 860, False)):
        opts = {"viewport": {"width": w, "height": h}, "reduced_motion": "reduce"}
        if touch:
            opts.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = br.new_context(**opts)
        pg = ctx.new_page()
        pg.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and errs.append(m.text))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        login(pg)
        for label, path in (("Khách hàng chi tiết", "/customers/detail/?id=3"), ("Nhà cung cấp chi tiết", None)):
            if path is None:
                go(pg, "/suppliers/")
                pg.locator("table.lt tbody tr").first.locator("a").first.click()
                pg.wait_for_selector("#supplier-detail")
                pg.wait_for_load_state("networkidle")
            else:
                go(pg, path)
            ps = pencils(pg)
            if w == 1280:
                # chuột: bút ẩn tới khi rê, nhưng vẫn có kích thước thật
                pass
            ok(f"{w}px {label}: có bút sửa tại chỗ ({len(ps)})", len(ps) >= 2, ps)
            ok(f"{w}px {label}: mọi bút >= 44x44", all(q["w"] >= 43.5 and q["h"] >= 43.5 for q in ps), ps)
            ok(f"{w}px {label}: các bút không chồng lên nhau", not any(overlap(a, b) for i, a in enumerate(ps) for b in ps[i + 1:]), ps)
            ok(f"{w}px {label}: không cuộn ngang trang", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
            # bút không chồng lên nút/liên kết khác (trừ chính nó)
            clash = pg.evaluate("""() => { const all = [...document.querySelectorAll('main button, main a, header button')].filter(e => !/pencil/.test(e.className)); const out = [];
              for (const b of document.querySelectorAll('button[class*=pencil]')) { const r = b.getBoundingClientRect(); for (const o of all) { const q = o.getBoundingClientRect(); if (q.width && q.height && r.x < q.right - 1 && q.x < r.right - 1 && r.y < q.bottom - 1 && q.y < r.bottom - 1) out.push((b.getAttribute('aria-label')) + ' x ' + (o.innerText || o.getAttribute('aria-label') || o.tagName).slice(0, 20)); } } return out; }""")
            ok(f"{w}px {label}: bút không đè lên nút hay liên kết nào khác", not clash, clash)
            # nhấp được và mở ô sửa; chạm đúng ở mép vùng 44px (ngoài chấm 16px) cũng mở
            if ps:
                q0 = ps[0]
                if touch:
                    pg.touchscreen.tap(q0["x"] + 3, q0["y"] + q0["h"] / 2)
                else:
                    pg.mouse.click(q0["x"] + 3, q0["y"] + q0["h"] / 2)
                pg.wait_for_timeout(300)
                ok(f"{w}px {label}: chạm/bấm mép ngoài của bút (cách biểu tượng ~13px) vẫn mở ô sửa", pg.get_by_role("button", name="Huỷ").count() >= 1 and pg.locator("main input, main textarea").count() >= 1)
                # Customer: trống tên -> câu mặc định giữ nguyên
                if path:
                    inp = pg.locator("main input").first
                    inp.fill("")
                    pg.get_by_role("button", name="Lưu", exact=True).first.click()
                    ok(f"{w}px {label}: tên khách để trống vẫn ra câu chung 'Nhập giá trị cho ô này.' (không đổi ở màn khác)", pg.get_by_text("Nhập giá trị cho ô này.").count() >= 1 and pg.get_by_text("Nhập tên nhà cung cấp.").count() == 0, pg.locator("main").inner_text()[:200])
                else:
                    inp = pg.locator("main input").first
                    inp.fill("")
                    pg.get_by_role("button", name="Lưu", exact=True).first.click()
                    ok(f"{w}px {label}: tên NCC để trống ra 'Nhập tên nhà cung cấp.'", pg.get_by_text("Nhập tên nhà cung cấp.").count() >= 1, pg.locator("main").inner_text()[:200])
                pg.screenshot(path=f"{SHOTS}/impl-mock-infofield-{'cust' if path else 'supp'}-{w}.png")
                pg.get_by_role("button", name="Huỷ").first.click()
        ctx.close()
    br.close()
ok("console không lỗi", not errs, errs[:3])
bad = [n for n, c in R if not c]
print(f"\n{len(R) - len(bad)}/{len(R)} PASS")
if bad:
    print("FAIL:", *bad, sep="\n  ")
sys.exit(1 if bad else 0)
