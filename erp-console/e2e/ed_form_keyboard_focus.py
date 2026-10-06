# E2E nhóm C/D/E (QA B1 + L1): FormPage khi bàn phím mở (viewport 360x420) và focus về ô lỗi / ô mật khẩu.
#   NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3201 &)
#   BASE=http://127.0.0.1:3201 SHOTS=<thư mục> python3 e2e/ed_form_keyboard_focus.py     # tắt server sau khi xong
# Mock giữ trạng thái trong bộ nhớ trang nên đi bằng bấm menu, không gõ URL ghi.
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3201")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, extra)


def login(page, user="loc", pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", pw)
    page.get_by_role("button", name="Đăng nhập").click()
    return page


def visible_above_bar(page):
    """Ô đang focus có nằm hoàn toàn trên mép trên thanh nút dính đáy không."""
    return page.evaluate("""() => {
      const el = document.activeElement; const bar = document.querySelector('[data-action-bar]');
      if (!el || !bar) return {ok: false, why: 'no el/bar'};
      const r = el.getBoundingClientRect(); const b = bar.getBoundingClientRect();
      return {ok: r.bottom <= b.top + 1 && r.top >= 0, bottom: r.bottom, barTop: b.top, tag: el.tagName};
    }""")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 360, "height": 420}, device_scale_factor=2, is_mobile=True, has_touch=True, reduced_motion="reduce")
        page = login(ctx.new_page())
        page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=10_000)
        page.wait_for_load_state("networkidle")
        page.goto(BASE + "/catalog/new/")
        page.get_by_label(re.compile("^Mã hàng")).wait_for()
        # Tab qua mọi ô: ô nào cũng phải nằm trên thanh nút sau khi focus.
        page.get_by_label(re.compile("^Mã hàng")).focus()
        bad = []
        n = 0
        for _ in range(14):
            page.keyboard.press("Tab")
            page.wait_for_timeout(120)
            tag = page.evaluate("() => document.activeElement && document.activeElement.matches('input,select,textarea') ")
            if not tag:
                continue
            n += 1
            v = visible_above_bar(page)
            if not v.get("ok"):
                bad.append(v)
        ok("360x420 /catalog/new: Tab qua các ô, ô nào cũng nằm trên thanh nút", n >= 3 and not bad, f"ô={n} lỗi={bad[:2]}")
        # Ô cuối: Mô tả (nếu có) hoặc ô cuối cùng của form.
        last = page.locator("form textarea, form input:not([type=checkbox]):not([type=radio])").last
        last.focus()
        page.wait_for_timeout(200)
        v = visible_above_bar(page)
        ok("360x420: focus ô cuối → nằm trên mép thanh nút", v.get("ok"), str(v))
        page.screenshot(path=f"{SHOTS}/form-keyboard-360x420.png")
        # L1: Lưu khi trống → tiêu điểm tới ô lỗi đầu tiên.
        page.get_by_role("button", name="Lưu mặt hàng").click()
        page.wait_for_timeout(400)
        inv = page.evaluate("() => { const a = document.activeElement; return {invalid: a && a.getAttribute('aria-invalid'), name: a && (a.id || a.name)}; }")
        ok("Lưu báo lỗi → tiêu điểm nhảy tới ô lỗi đầu tiên (aria-invalid)", inv["invalid"] == "true", str(inv))
        ctx.close()
        # L1b: đăng nhập sai → tiêu điểm về ô mật khẩu.
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, reduced_motion="reduce")
        page = login(ctx.new_page(), "loc", "sai-mat-khau-1")
        page.wait_for_timeout(1200)
        fid = page.evaluate("() => document.activeElement && document.activeElement.id")
        ok("Đăng nhập sai → tiêu điểm về ô mật khẩu", fid == "p" and "/login" in page.url, f"id={fid}")
        ctx.close()
        browser.close()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
