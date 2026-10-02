# Hàm dùng chung cho các kịch bản e2e của Đơn & tiền (s10_s11, s12_s13, s14_s16): chạy trên bản build MOCK phục vụ tĩnh.
# Giao diện theo ERP theo design Lô 3: trang chi tiết riêng (/orders/detail/?id=), hộp thoại (role=dialog), toast, tab theo route.
import os
import re

from playwright.sync_api import expect

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=10_000)
results = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))


def login(page, user, pw="demo1234", wait_mock=True):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    if wait_mock:
        page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)


def idle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)


def log(page):
    return page.evaluate("() => window.__caveMock.log.slice()")


def clear_log(page):
    page.evaluate("() => window.__caveMock.clearLog()")


def posts(page):
    return [x for x in log(page) if x.startswith("POST")]



_RULE_CODE = r"(?:BR|DW|V|E|P)-[A-Z0-9]+(?:-[A-Z0-9]+)*"
_PAREN_CODES = re.compile(r"\s*[(（]\s*" + _RULE_CODE + r"(?:\s*[,;/]\s*" + _RULE_CODE + r")*\s*[)）]")
_BARE_BR = re.compile(r"\s*\bBR-[A-Z]+(?:-\d+)?\b")


def strip_rule_codes(msg):
    """Giống shared/lib/ruleCodes.ts: màn ERP bỏ mã luật (BR-…) khỏi câu lỗi BE trước khi hiển thị."""
    if not isinstance(msg, str) or not re.search(r"\b(?:BR|DW|V|E|P)-[A-Z0-9]", msg):
        return msg
    out = _BARE_BR.sub("", _PAREN_CODES.sub("", msg))
    out = re.sub(r"[ \t]{2,}", " ", out)
    return re.sub(r"\s+([.,;:!?])", r"\1", out).strip()


def be(page, key, params=None):
    return strip_rule_codes(page.evaluate("([k, p]) => window.__caveMock.beDetail(k, p || undefined)", [key, params]))


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    idle(page)


def open_order(page, oid):
    go(page, f"/orders/detail/?id={oid}")
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)


def open_payment(page, pid):
    go(page, f"/orders/payments/detail/?id={pid}")
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)


def open_refund(page, rid):
    go(page, f"/orders/refunds/detail/?id={rid}")
    expect(page.locator("main header h2")).to_be_visible()
    idle(page)


def header_text(page):
    return page.locator("main header").first.inner_text()


def header_buttons(page):
    return [t.strip() for t in page.locator("main header .btn").all_inner_texts() if t.strip()]


def open_more(page):
    page.get_by_role("button", name="Thao tác khác").click()
    expect(page.get_by_role("menu")).to_be_visible()
    return page.get_by_role("menu")


def menu_items(page):
    m = open_more(page)
    items = [t.strip() for t in m.get_by_role("menuitem").all_inner_texts()]
    page.keyboard.press("Escape")
    return items


def dialog(page, name):
    d = page.get_by_role("dialog", name=name)
    expect(d).to_be_visible()
    return d


def submit_btn(dlg):
    return dlg.locator("button[type=submit]")


def toast_text(page):
    return " ".join(page.locator(".toast-item").all_inner_texts())


def nav_labels(page):
    return [t.split("\n")[-1].strip() for t in page.locator(".nav a").all_inner_texts()]


def tab_labels(page):
    return [t.strip() for t in page.get_by_role("tab").all_inner_texts()]


def fonts_ready(page):
    page.wait_for_function("() => document.fonts.status === 'loaded'")


def hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth")


def qjson(page, user="loc", status="OPEN"):
    return page.evaluate("([u, s]) => window.__caveMock.queueJson(u, s)", [user, status])


def make_new_page(browser, errors, width=1280, height=800, dark=False, mobile=False):
    kw = dict(viewport={"width": width, "height": height}, reduced_motion="reduce", color_scheme="dark" if dark else "light")
    if mobile:
        kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**kw)
    pg = ctx.new_page()
    pg.on("console", lambda m: m.type == "error" and "Failed to fetch RSC payload" not in m.text and errors.append(m.text))
    pg.on("pageerror", lambda e: errors.append(str(e)))
    return ctx, pg


def finish(errors):
    relevant = [e for e in errors if "fonts.g" not in e and "net::" not in e and "401" not in e and "403" not in e
                and "500" not in e and "Failed to load resource" not in e and "Failed to fetch RSC payload" not in e]
    ok("Không lỗi console (trừ font/401/403/500 cố ý)", not relevant, str(relevant[:5]))
    fails = 0
    for n, c, e in results:
        print(("PASS " if c else "FAIL ") + n + ("" if c else "  -> " + str(e)))
        fails += 0 if c else 1
    print(f"{len(results) - fails}/{len(results)} PASS")
    raise SystemExit(1 if fails else 0)
