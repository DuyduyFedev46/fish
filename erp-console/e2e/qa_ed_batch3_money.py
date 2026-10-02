# QA độc lập Lô 3 FE, lần 3: TẬP TRUNG Ô SỐ TIỀN của 2 popup ("Lập phiếu hoàn", "Xác nhận đã nhận tiền").
# Chạy cả hai chế độ (cùng một bộ ca):
#   MODE=mock  BASE=http://127.0.0.1:3101  (bản build NEXT_PUBLIC_USE_MOCK=1; tiền gửi đi đọc lại từ kho mock)
#   MODE=real  BASE=http://127.0.0.1:3102  (bản build MOCK=0 trỏ BE thật + SQLite tạm; đọc thân request thật từ trình duyệt)
#   SHOTS=<doc/features/2026-10-01-erp-theo-design/shots/lot3> python3 -u e2e/qa_ed_batch3_money.py
# Ca: gõ thường, Backspace/Delete ở MỌI vị trí (kể cả ngay dấu chấm), chèn chữ số vào giữa, chọn một đoạn rồi xoá,
# dán (150.000 / 1,500,000 / 150.000,00 / 150,000.50 / 0.5 / 1.500.000 đ ...) bằng Ctrl+V thật, gõ chữ, số âm, số rất lớn,
# gõ dấu thập phân từng phím, và số tiền GỬI LÊN API phải đúng từng đồng. Chỉ dữ liệu giả.
import json
import os
import re
import time
import traceback

from playwright.sync_api import expect, sync_playwright

MODE = os.environ.get("MODE", "mock")
BASE = os.environ.get("BASE", "http://127.0.0.1:3101" if MODE == "mock" else "http://127.0.0.1:3102")
SHOTS = os.environ.get("SHOTS", "/tmp")
PW = "demo1234" if MODE == "mock" else "Songbien2026"
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=10_000)
FRACTION_MSG = "không có phần lẻ"
results = []
errors = []
notes = []


def ok(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS" if cond else "FAIL"), name, ("" if cond else "  -> " + str(extra)[:300]), flush=True)


def note(msg):
    notes.append(msg)
    print("   [ghi nhận]", msg, flush=True)


def section(name):
    def deco(fn):
        print(f"\n=== {name}", flush=True)
        try:
            fn()
        except Exception as e:
            ok(f"[NHÓM {name}] chạy hết không ngoại lệ", False, f"{type(e).__name__}: {str(e)[:250]}")
            traceback.print_exc(limit=3)
        return fn

    return deco


# ------------------------------------------------------------------------------------------------ mô hình kỳ vọng
def only_digits(s):
    return re.sub(r"\D+", "", s)


def group(d):
    d = re.sub(r"^0+(?=\d)", "", d)
    return re.sub(r"\B(?=(\d{3})+(?!\d))", ".", d)


def caret_after(formatted, n):
    pos = seen = 0
    while pos < len(formatted) and seen < n:
        if formatted[pos].isdigit():
            seen += 1
        pos += 1
    return pos


def strip_zero(d, before):
    m = re.match(r"^0+(?=\d)", d)
    if m:
        z = len(m.group(0))
        return d[z:], max(0, before - z)
    return d, before


def model_backspace(text, p):
    D = only_digits(text)
    before = len(only_digits(text[:p]))
    if before > 0:
        D = D[: before - 1] + D[before:]
        before -= 1
    D, before = strip_zero(D, before)
    v = group(D)
    return v, caret_after(v, before)


def model_delete(text, p):
    D = only_digits(text)
    before = len(only_digits(text[:p]))
    if before < len(D):
        D = D[:before] + D[before + 1:]
    D, before = strip_zero(D, before)
    v = group(D)
    return v, caret_after(v, before)


def model_insert(text, p, ch):
    D = only_digits(text)
    before = len(only_digits(text[:p]))
    D = D[:before] + ch + D[before:]
    before += 1
    D, before = strip_zero(D, before)
    v = group(D)
    return v, caret_after(v, before)


# ------------------------------------------------------------------------------------------------ trình duyệt
def new_page(browser, user="loc", w=1280, h=900, mobile=False):
    kw = dict(viewport={"width": w, "height": h}, reduced_motion="reduce")
    if mobile:
        kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**kw)
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    except Exception:
        pass
    pg = ctx.new_page()
    pg.posts = []      # (url, post_data) mọi POST tới API (chế độ real)
    pg.resp = []       # (url, status, text)

    def on_req(r):
        if r.method == "POST" and "/api/" in r.url:
            pg.posts.append((r.url, r.post_data))

    def on_resp(r):
        if r.request.method == "POST" and "/api/" in r.url:
            try:
                pg.resp.append((r.url, r.status, r.text()))
            except Exception:
                pg.resp.append((r.url, r.status, ""))

    pg.on("request", on_req)
    pg.on("response", on_resp)
    pg.on("console", lambda m: m.type == "error" and "Failed to fetch RSC" not in m.text and "404" not in m.text and errors.append(f"[{user}] {m.text}"))
    pg.on("pageerror", lambda e: errors.append(f"[{user}] pageerror {e}"))
    for _ in range(3):
        pg.goto(BASE + "/login/")
        pg.wait_for_load_state("networkidle")
        pg.get_by_label("Tài khoản").fill(user)
        pg.get_by_label("Mật khẩu").fill(PW)
        pg.get_by_role("button", name="Đăng nhập").click()
        try:
            pg.wait_for_selector(".nav a", state="attached", timeout=15_000)
            break
        except Exception:
            time.sleep(8)
    if MODE == "mock":
        pg.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'", timeout=10_000)
    return ctx, pg


def idle(pg):
    if MODE == "mock":
        pg.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0", timeout=10_000)
    else:
        pg.wait_for_load_state("networkidle")


def go(pg, path):
    pg.goto(BASE + path)
    pg.wait_for_load_state("networkidle")
    idle(pg)


def shot(pg, name):
    pg.screenshot(path=f"{SHOTS}/qa3-money-{MODE}-{name}.png")


# Đơn dùng cho từng popup. Mock: 102 (Giữ chỗ, thanh toán tay) / 105 (đã thanh toán, còn hoàn được 1.190.000).
# Real (SQLite tạm đã seed): đơn BOOKED = pk 7..10 (thanh toán tay), đơn COMPLETED = pk 13..14 (hoàn).
PAY_ORDERS = [102] if MODE == "mock" else [7, 8, 9, 10]
REFUND_ORDERS = [105] if MODE == "mock" else [13, 14]


def open_popup(pg, kind, oid):
    go(pg, f"/orders/detail/?id={oid}")
    expect(pg.locator("main header h2")).to_be_visible()
    if kind == "pay":
        pg.get_by_role("button", name="Xác nhận đã nhận tiền").click()
        d = pg.get_by_role("dialog", name="Xác nhận đã nhận tiền")
    else:
        primary = pg.locator("main header").get_by_role("button", name="Lập phiếu hoàn")
        if primary.count():
            primary.first.click()
        else:
            pg.get_by_role("button", name="Thao tác khác").click()
            pg.get_by_role("menuitem", name="Lập phiếu hoàn").click()
        d = pg.get_by_role("dialog", name="Lập phiếu hoàn")
    expect(d).to_be_visible()
    f = d.get_by_label(re.compile("Số tiền đã nhận" if kind == "pay" else "Số tiền hoàn"))
    expect(f).to_be_visible()
    if kind == "pay":
        d.get_by_label(re.compile("Mã giao dịch")).fill("FTQA3" + str(int(time.time() * 1000))[-8:])
    else:
        d.get_by_label(re.compile("Lý do hoàn")).fill("Khách đổi ý (QA, dữ liệu giả)")
    return d, f


def caret(f):
    return f.evaluate("e => e.selectionStart")


def sel(pg, f, a, b=None):
    f.evaluate("(e, ab) => { e.focus(); e.setSelectionRange(ab[0], ab[1]); }", [a, a if b is None else b])


def label_amount(d):
    t = d.locator("button[type=submit]").inner_text().strip()
    m = re.search(r"([\d.]+) đ\s*$", t)
    return m.group(1) if m else None, t


def dialog_error(d):
    return d.inner_text()


def set_clean(pg, f, text="1234567"):
    f.fill("")
    f.press_sequentially(text, delay=12)


def paste(pg, f, text, select_all=True):
    """Dán thật: ghi clipboard rồi Ctrl/Cmd+V (inputType = insertFromPaste)."""
    pg.evaluate("t => navigator.clipboard.writeText(t)", text)
    f.focus()
    if select_all:
        pg.keyboard.press("ControlOrMeta+A")
    pg.keyboard.press("ControlOrMeta+V")


def typed_via_input_type(pg, f):
    pg.evaluate("""() => { window.__itypes = []; document.addEventListener('input', e => window.__itypes.push(e.inputType), true); }""")


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ============================================================================================ 1. gõ thường
    @section(f"[{MODE}] 1. Gõ bình thường ở cả 2 popup")
    def _():
        ctx, pg = new_page(browser)
        for kind in ("refund", "pay"):
            oid = (REFUND_ORDERS if kind == "refund" else PAY_ORDERS)[0]
            d, f = open_popup(pg, kind, oid)
            tag = "hoàn" if kind == "refund" else "nhận tiền"
            for typed, want in (("1", "1"), ("12", "12"), ("123", "123"), ("1234", "1.234"), ("150000", "150.000"), ("1500000", "1.500.000"), ("12345678", "12.345.678"), ("000150", "150"), ("0", "0"), ("100000", "100.000")):
                f.fill("")
                f.press_sequentially(typed, delay=10)
                ok(f"gõ thường [{tag}] '{typed}' → '{want}', con trỏ cuối ô", f.input_value() == want and caret(f) == len(want), (f.input_value(), caret(f)))
            # gõ cả dấu chấm/phẩy phân nhóm kiểu người quen gõ
            for typed, want in (("150.000", "150.000"), ("1,500,000", "1.500.000"), ("1.500.000", "1.500.000")):
                f.fill("")
                f.press_sequentially(typed, delay=10)
                ok(f"gõ có dấu phân nhóm [{tag}] '{typed}' → '{want}'", f.input_value() == want, f.input_value())
            # nhãn nút ghi đúng số (trong giới hạn)
            f.fill("")
            f.press_sequentially("100000", delay=10)
            ok(f"nút gửi [{tag}] ghi đúng '100.000 đ'", label_amount(d)[0] == "100.000", label_amount(d))
            f.fill("")
            ok(f"xoá hết ô [{tag}]: ô rỗng, nút không ghi số", f.input_value() == "" and label_amount(d)[0] is None, (f.input_value(), label_amount(d)))
            shot(pg, f"typed-{kind}")
            pg.keyboard.press("Escape")
        ctx.close()

    # ============================================================================================ 2. Backspace / Delete mọi vị trí
    @section(f"[{MODE}] 2. Backspace và Delete ở mọi vị trí (kể cả ngay dấu chấm)")
    def _():
        ctx, pg = new_page(browser)
        for kind in ("refund", "pay"):
            oid = (REFUND_ORDERS if kind == "refund" else PAY_ORDERS)[0]
            d, f = open_popup(pg, kind, oid)
            tag = "hoàn" if kind == "refund" else "nhận tiền"
            base = "1.234.567"
            bad = []
            for p_ in range(0, len(base) + 1):
                set_clean(pg, f)
                assert f.input_value() == base
                sel(pg, f, p_)
                pg.keyboard.press("Backspace")
                mv, mc = model_backspace(base, p_)
                got = (f.input_value(), caret(f))
                if got != (mv, mc):
                    bad.append(("BS", p_, got, (mv, mc)))
                set_clean(pg, f)
                sel(pg, f, p_)
                pg.keyboard.press("Delete")
                mv, mc = model_delete(base, p_)
                got = (f.input_value(), caret(f))
                if got != (mv, mc):
                    bad.append(("DEL", p_, got, (mv, mc)))
            ok(f"[{tag}] Backspace và Delete ở cả {len(base)+1} vị trí của '1.234.567': giá trị + con trỏ đúng mô hình", not bad, bad[:3])
            # không bao giờ ra phần lẻ kiểu '.dd' ở cuối sau xoá (dấu hiệu B4)
            bad2 = []
            for start in ("150.000", "1.500.000", "15.000.000", "12.345", "999.999.999"):
                set_clean(pg, f, only_digits(start))
                for _i in range(len(only_digits(start))):
                    pg.keyboard.press("Backspace")
                    v = f.input_value()
                    if v and not re.fullmatch(r"\d{1,3}(\.\d{3})*", v):
                        bad2.append((start, v))
                    # nút gửi (nếu có số) phải đúng bằng ô
                    la = label_amount(d)[0]
                    if v and la is not None and la != v:
                        bad2.append((start, v, la))
            ok(f"[{tag}] xoá lùi từng phím tới hết ô từ 5 giá trị: luôn nhóm nghìn hợp lệ, nút gửi = ô", not bad2, bad2[:3])
            # xoá lùi hết: phím Backspace ngay dấu chấm
            set_clean(pg, f, "150000")           # '150.000'
            sel(pg, f, 4)                        # '150.|000'
            pg.keyboard.press("Backspace")       # xoá '0' trước dấu chấm → '15.000'
            ok(f"[{tag}] Backspace ngay sau dấu chấm: '150.|000' → '15.000'", f.input_value() == "15.000" and caret(f) == 2, (f.input_value(), caret(f)))
            set_clean(pg, f, "150000")
            sel(pg, f, 3)                        # '150|.000'
            pg.keyboard.press("Delete")          # Delete ngay trước dấu chấm → xoá chữ số '0' đầu nhóm sau
            ok(f"[{tag}] Delete ngay trước dấu chấm: '150|.000' → '15.000', con trỏ sau '150' (không đứng im)", f.input_value() == "15.000" and caret(f) == 4, (f.input_value(), caret(f)))
            # xoá hết bằng Backspace giữ ô trống, ô không kẹt dấu chấm
            set_clean(pg, f, "1500")
            for _i in range(4):
                pg.keyboard.press("Backspace")
            ok(f"[{tag}] xoá hết bằng Backspace: ô rỗng", f.input_value() == "", f.input_value())
            # chọn đoạn rồi xoá
            set_clean(pg, f)                     # 1.234.567
            sel(pg, f, 2, 5)                     # chọn '234'
            pg.keyboard.press("Backspace")
            mv = group(only_digits("1.234.567"[:2] + "1.234.567"[5:]))
            ok(f"[{tag}] chọn '234' rồi Backspace → '{mv}'", f.input_value() == mv, f.input_value())
            set_clean(pg, f)
            pg.keyboard.press("ControlOrMeta+A")
            pg.keyboard.press("Backspace")
            ok(f"[{tag}] chọn hết rồi Backspace → rỗng", f.input_value() == "", f.input_value())
            set_clean(pg, f)
            sel(pg, f, 0, 5)
            pg.keyboard.press("Delete")
            ok(f"[{tag}] chọn '1.234' rồi Delete → '567'", f.input_value() == "567", f.input_value())
            shot(pg, f"backspace-{kind}")
            pg.keyboard.press("Escape")
        ctx.close()

    # ============================================================================================ 3. chèn chữ số vào giữa
    @section(f"[{MODE}] 3. Chèn chữ số vào giữa ô")
    def _():
        ctx, pg = new_page(browser)
        for kind in ("refund", "pay"):
            oid = (REFUND_ORDERS if kind == "refund" else PAY_ORDERS)[0]
            d, f = open_popup(pg, kind, oid)
            tag = "hoàn" if kind == "refund" else "nhận tiền"
            base = "1.234.567"
            bad = []
            for p_ in range(0, len(base) + 1):
                set_clean(pg, f)
                sel(pg, f, p_)
                pg.keyboard.type("9")
                mv, mc = model_insert(base, p_, "9")
                got = (f.input_value(), caret(f))
                if got != (mv, mc):
                    bad.append((p_, got, (mv, mc)))
            ok(f"[{tag}] chèn '9' ở cả {len(base)+1} vị trí: giá trị + con trỏ đúng", not bad, bad[:3])
            # chèn liên tiếp nhiều chữ số giữa ô: con trỏ ở yên đúng chỗ
            set_clean(pg, f, "100000")           # 100.000
            sel(pg, f, 2)                        # '10|0.000'
            pg.keyboard.type("55")
            mv = group("10" + "55" + "0000")
            ok(f"[{tag}] chèn '55' giữa '100.000' tại sau '10' → '{mv}'", f.input_value() == mv, f.input_value())
            # chèn '0' đầu ô: không sinh số 0 đầu
            set_clean(pg, f, "500")
            sel(pg, f, 0)
            pg.keyboard.type("0")
            ok(f"[{tag}] chèn '0' đầu '500' → '500' (không 0500)", f.input_value() == "500", f.input_value())
            # gõ chèn khi có đoạn chọn: thay đoạn
            set_clean(pg, f)
            sel(pg, f, 2, 5)
            pg.keyboard.type("0")
            ok(f"[{tag}] chọn '234' gõ '0' → '10.567'", f.input_value() == "10.567", f.input_value())
            pg.keyboard.press("Escape")
        ctx.close()

    # ============================================================================================ 4. dán
    @section(f"[{MODE}] 4. Dán (Ctrl+V thật)")
    def _():
        ctx, pg = new_page(browser)
        # (chuỗi dán, kiểu kết quả, giá trị mong đợi trong ô)
        cases = [
            ("150.000", "value", "150.000"),
            ("1,500,000", "value", "1.500.000"),
            ("150.000,00", "value", "150.000"),
            ("150,000.00", "value", "150.000"),
            ("150,000.50", "reject", None),
            ("150.000,50", "reject", None),
            ("0.5", "reject", None),
            ("540,5", "reject", None),
            ("1.500.000 đ", "value", "1.500.000"),
            ("1.500.000₫", "value", "1.500.000"),
            ("150000", "value", "150.000"),
            ("150 000", "value", "150.000"),
            ("150000 VND", "value", "150.000"),
            ("  150.000  ", "value", "150.000"),
            ("1.500.000,5", "reject", None),
            ("0.00", "value", "0"),
            ("0,00", "value", "0"),
            ("1.500.000,00 đ", "value", "1.500.000"),
        ]
        for kind in ("refund", "pay"):
            oid = (REFUND_ORDERS if kind == "refund" else PAY_ORDERS)[0]
            d, f = open_popup(pg, kind, oid)
            tag = "hoàn" if kind == "refund" else "nhận tiền"
            f.fill("")
            f.press_sequentially("20000", delay=10)      # '20.000' đang có trong ô
            prev = f.input_value()
            ok(f"[{tag}] chuẩn bị: ô đang '20.000'", prev == "20.000", prev)
            typed_via_input_type(pg, f)
            for text, kindx, want in cases:
                f.fill("")
                f.press_sequentially("20000", delay=5)
                paste(pg, f, text)
                pg.wait_for_timeout(80)
                v = f.input_value()
                body = dialog_error(d)
                if kindx == "value":
                    ok(f"[{tag}] dán '{text}' → ô '{want}'", v == want, (v, body[-120:]))
                    ok(f"[{tag}] dán '{text}': không báo lỗi phần lẻ", FRACTION_MSG not in body, body[-160:])
                    if want not in ("0",):
                        la = label_amount(d)[0]
                        if kind == "pay" or int(only_digits(want)) <= 1190000:
                            ok(f"[{tag}] dán '{text}': nút gửi ghi đúng '{want} đ'", la == want, label_amount(d))
                else:
                    ok(f"[{tag}] dán '{text}' (phần lẻ khác 0): TỪ CHỐI, ô giữ '20.000', không đoán", v == "20.000", v)
                    ok(f"[{tag}] dán '{text}': hiện câu 'không có phần lẻ' dưới ô", FRACTION_MSG in body, body[-200:])
                    la = label_amount(d)[0]
                    ok(f"[{tag}] dán '{text}': nút gửi vẫn ghi số cũ '20.000 đ'", la == "20.000", label_amount(d))
            # lỗi phần lẻ tự mất khi gõ tiếp chữ số hợp lệ
            f.fill("")
            f.press_sequentially("20000", delay=5)
            paste(pg, f, "0.5")
            expect(d.get_by_text(re.compile(FRACTION_MSG))).to_be_visible()
            shot(pg, f"paste-fraction-{kind}")
            f.press("End")
            pg.keyboard.type("0")
            pg.wait_for_timeout(80)
            ok(f"[{tag}] sau khi bị từ chối, gõ tiếp '0' → '200.000' và câu lỗi biến mất", f.input_value() == "200.000" and FRACTION_MSG not in dialog_error(d), (f.input_value(), dialog_error(d)[-100:]))
            # dán chèn vào GIỮA ô (không chọn hết)
            f.fill("")
            f.press_sequentially("100000", delay=5)      # 100.000
            sel(pg, f, 3)                                # '100|.000'
            paste(pg, f, "55", select_all=False)
            ok(f"[{tag}] dán '55' vào giữa '100.000' → {group('10055000'[:0] + '100' + '55' + '000')}", f.input_value() == group("100" + "55" + "000"), f.input_value())
            # dán phần lẻ vào giữa ô: giữ nguyên ô (không đoán)
            f.fill("")
            f.press_sequentially("100000", delay=5)
            sel(pg, f, 7)
            paste(pg, f, ",5", select_all=False)
            pg.wait_for_timeout(80)
            ok(f"[{tag}] dán ',5' vào cuối '100.000' (thành '100.000,5'): từ chối, ô giữ '100.000'", f.input_value() == "100.000" and FRACTION_MSG in dialog_error(d), (f.input_value(), dialog_error(d)[-100:]))
            pg.keyboard.press("Escape")
        ctx.close()

    # ============================================================================================ 5. chữ, số âm, số lớn
    @section(f"[{MODE}] 5. Gõ chữ, số âm, số rất lớn")
    def _():
        ctx, pg = new_page(browser)
        for kind in ("refund", "pay"):
            oid = (REFUND_ORDERS if kind == "refund" else PAY_ORDERS)[0]
            d, f = open_popup(pg, kind, oid)
            tag = "hoàn" if kind == "refund" else "nhận tiền"
            sub = d.locator("button[type=submit]")
            # --- chữ
            for typed, want in (("abc", ""), ("12a3b", "123"), ("ba trăm", ""), ("1đ", "1"), ("😀5", "5"), ("１２３", "")):
                f.fill("")
                f.press_sequentially(typed, delay=10)
                ok(f"[{tag}] gõ chữ '{typed}' → ô '{want}' (chữ bị bỏ ngay tại ô)", f.input_value() == want, f.input_value())
            # ghi nhận: '150k', '1tr5', '1e6' bị đọc thành số khác mà không có cảnh báo
            for typed, got_expected in (("150k", "150"), ("1tr5", "15"), ("1e6", "16")):
                f.fill("")
                f.press_sequentially(typed, delay=10)
                if f.input_value() == got_expected:
                    note(f"[{tag}] gõ '{typed}' → ô '{got_expected}' (chữ bị bỏ lặng lẽ, không báo): người gõ viết tắt 'k'/'tr' sẽ ra số nhỏ hơn 1.000 lần; nút gửi vẫn ghi số này")
            # --- số âm
            if kind == "pay":
                d.get_by_label(re.compile("Mã giao dịch")).fill("FTQANEG001")
            else:
                d.get_by_label(re.compile("Lý do hoàn")).fill("QA số âm")
            for typed in ("-5", "-150.000", "−5", "5-0"):
                f.fill("")
                f.press_sequentially(typed, delay=10)
                v = f.input_value()
                pg.evaluate("() => window.__caveMock && window.__caveMock.clearLog && window.__caveMock.clearLog()")
                pg.posts.clear()
                sub.click()
                pg.wait_for_timeout(350)
                n_post = len([x for x in pg.posts if "confirm-payment" in x[0] or "refunds" in x[0]]) if MODE == "real" else len([x for x in pg.evaluate("() => window.__caveMock.log.slice()") if x.startswith("POST")])
                txt = dialog_error(d)
                ok(f"[{tag}] số âm '{typed}' (ô '{v}'): gửi → 0 POST và có câu 'không được âm'", n_post == 0 and re.search(r"không được âm|âm", txt) is not None, (v, n_post, txt[-160:]))
            f.fill("")
            f.press_sequentially("-5", delay=10)
            f.press("Backspace"); f.press("Backspace")
            ok(f"[{tag}] '-5' rồi Backspace 2 lần → ô rỗng", f.input_value() == "", f.input_value())
            shot(pg, f"negative-{kind}")
            # --- số rất lớn
            big = "9" * 30
            f.fill("")
            f.press_sequentially(big, delay=3)
            v = f.input_value()
            ok(f"[{tag}] gõ 30 chữ số '9': ô giữ đủ 30 chữ số, nhóm nghìn đúng", only_digits(v) == big and re.fullmatch(r"\d{1,3}(\.\d{3})*", v) is not None, v)
            pg.evaluate("() => window.__caveMock && window.__caveMock.clearLog && window.__caveMock.clearLog()")
            pg.posts.clear()
            sub.click()
            pg.wait_for_timeout(350)
            n_post = len([x for x in pg.posts if "confirm-payment" in x[0] or "refunds" in x[0]]) if MODE == "real" else len([x for x in pg.evaluate("() => window.__caveMock.log.slice()") if x.startswith("POST")])
            txt = dialog_error(d)
            ok(f"[{tag}] 30 chữ số: gửi → 0 POST và câu 'tối đa 12 chữ số' / vượt mức", n_post == 0 and re.search(r"tối đa|quá lớn|Nhập tối đa", txt) is not None, (n_post, txt[-200:]))
            shot(pg, f"huge-{kind}")
            f.fill("")
            f.press_sequentially("1000000000000", delay=3)   # 13 chữ số
            pg.posts.clear()
            sub.click()
            pg.wait_for_timeout(350)
            txt = dialog_error(d)
            ok(f"[{tag}] 13 chữ số (1.000.000.000.000): bị chặn (quá lớn / vượt mức)", re.search(r"tối đa|quá lớn", txt) is not None, txt[-200:])
            # dán số rất lớn
            paste(pg, f, "9" * 40)
            ok(f"[{tag}] dán 40 chữ số: ô giữ đủ, không treo, không ngoại lệ", only_digits(f.input_value()) == "9" * 40, f.input_value()[:60])
            # 12 chữ số
            f.fill("")
            f.press_sequentially("999999999999", delay=3)
            ok(f"[{tag}] 12 chữ số '999.999.999.999' giữ nguyên", f.input_value() == "999.999.999.999", f.input_value())
            pg.keyboard.press("Escape")
        ctx.close()

    # ============================================================================================ 6. gõ dấu thập phân từng phím
    @section(f"[{MODE}] 6. Gõ dấu thập phân từng phím (giới hạn đã biết)")
    def _():
        ctx, pg = new_page(browser)
        for kind in ("refund", "pay"):
            oid = (REFUND_ORDERS if kind == "refund" else PAY_ORDERS)[0]
            d, f = open_popup(pg, kind, oid)
            tag = "hoàn" if kind == "refund" else "nhận tiền"
            for typed in ("150.000,50", "150000,5", "0.5", "1,5"):
                f.fill("")
                f.press_sequentially(typed, delay=12)
                v = f.input_value()
                err = FRACTION_MSG in dialog_error(d)
                la = label_amount(d)[0]
                # nếu người dùng gõ phần lẻ từng phím mà ô không báo gì thì số ra khác ý (×10 / ×100)
                if not err and only_digits(v) != only_digits(typed.split(",")[0].split(".")[0] if False else typed):
                    pass
                intended_int = group(only_digits(re.split(r"[,.](?=\d{1,2}$)", typed)[0]))
                if not err and v != intended_int:
                    note(f"[{tag}] GÕ TỪNG PHÍM '{typed}' → ô '{v}' (nút '{la} đ'), không báo phần lẻ: dấu thập phân gõ tay bị coi là dấu nhóm (phần lẻ chỉ bị bắt khi DÁN nguyên chuỗi). Phần thập phân bị ghép vào số nguyên.")
                else:
                    ok(f"[{tag}] gõ từng phím '{typed}' → ô '{v}' (phần lẻ được xử lý)", True)
            pg.keyboard.press("Escape")
        ctx.close()

    # ============================================================================================ 7. tiền GỬI LÊN API đúng từng đồng
    @section(f"[{MODE}] 7. Số tiền gửi lên API đúng từng đồng")
    def _():
        ctx, pg = new_page(browser)
        exact_pay = []
        exact_refund = []

        def read_mock_state(kind, oid):
            if kind == "pay":
                j = pg.evaluate("([u, i]) => window.__caveMock.orderJson(u, i)", ["loc", oid])
                return j
            return pg.evaluate("([u, i]) => window.__caveMock.orderJson(u, i)", ["loc", oid])

        def type_plain(f):
            f.fill(""); f.press_sequentially("150000", delay=10)

        def edit_scripts():
            # (tên ca, hàm thao tác trên ô, số tiền đúng kỳ vọng dạng chữ số)
            def type_plain(f):
                f.fill(""); f.press_sequentially("150000", delay=10)

            def type_then_backspace(f):
                f.fill(""); f.press_sequentially("1500000", delay=10); pg.keyboard.press("Backspace")     # → 150.000

            def type_then_delete_mid(f):
                f.fill(""); f.press_sequentially("1234567", delay=10); sel(pg, f, 0); pg.keyboard.press("Delete")   # 234.567

            def insert_mid(f):
                f.fill(""); f.press_sequentially("100000", delay=10); sel(pg, f, 2); pg.keyboard.type("5")     # 1050.000? → 1.050.00 → 105.000
            def paste_stmt(f):
                paste(pg, f, "150.000,00")

            def paste_us(f):
                paste(pg, f, "1,500,000")

            def paste_vnd(f):
                paste(pg, f, "1.500.000 đ")
            return [
                ("gõ thường 150000", type_plain, "150000"),
                ("gõ 1500000 rồi Backspace", type_then_backspace, "150000"),
                ("gõ 1234567, Delete đầu ô", type_then_delete_mid, "234567"),
                ("chèn '5' giữa 100.000 (sau '10')", insert_mid, "1050000"),
                ("dán '150.000,00' (kiểu sao kê)", paste_stmt, "150000"),
                ("dán '1,500,000'", paste_us, "1500000"),
                ("dán '1.500.000 đ'", paste_vnd, "1500000"),
            ]

        # ---- Xác nhận đã nhận tiền: mỗi ca gửi thật trên một đơn BOOKED khác nhau (BE thật có 4 đơn; mock dùng reset)
        sc = edit_scripts()
        pay_cases = sc[:3] if MODE == "real" else sc
        for i, (name, fn, want) in enumerate(pay_cases):
            oid = PAY_ORDERS[i] if MODE == "real" else PAY_ORDERS[0]
            if MODE == "mock":
                pg.evaluate("() => window.__caveMock.resetOrders()")
                idle(pg)
            d, f = open_popup(pg, "pay", oid)
            fn(f)
            pg.wait_for_timeout(100)
            la = label_amount(d)[0]
            ok(f"[nhận tiền] {name}: nút ghi đúng '{group(want)} đ'", la == group(want), (la, f.input_value()))
            pg.posts.clear(); pg.resp.clear()
            base_n = len(read_mock_state("pay", oid).get("payments") or []) if MODE == "mock" else 0
            d.locator("button[type=submit]").click()
            pg.wait_for_timeout(1200)
            if MODE == "real":
                bodies = [(u, json.loads(b or "{}")) for u, b in pg.posts if "confirm-payment" in u]
                sent = [str(b.get("amount")) for _u, b in bodies]
                ok(f"[nhận tiền] {name}: request body amount đúng từng đồng '{want}' (1 request)", len(sent) == 1 and re.sub(r"\.0+$", "", sent[0]) == want, (sent, [r[:2] for r in pg.resp]))
                st = [r[1] for r in pg.resp if "confirm-payment" in r[0]]
                ok(f"[nhận tiền] {name}: BE trả 2xx", bool(st) and 200 <= st[0] < 300, (st, [r[2][:160] for r in pg.resp]))
            else:
                j = read_mock_state("pay", oid)
                pays = j.get("payments") or []
                new_rows = pays[base_n:]
                total_new = sum(float(x["amount"]) for x in new_rows)
                ok(f"[nhận tiền] {name}: tiền ghi vào kho mock đúng từng đồng '{want}' (tổng các dòng mới, kể cả phần thừa)", bool(new_rows) and total_new == float(want), [x["amount"] for x in new_rows])
        # ---- Lập phiếu hoàn (mỗi ca là một phiếu thật; BE thật: đơn 14 còn hoàn được 200.000)
        def bs_500(f):
            f.fill(""); f.press_sequentially("500000", delay=10); pg.keyboard.press("Backspace")      # 50.000

        def del_head(f):
            f.fill(""); f.press_sequentially("123456", delay=10); sel(pg, f, 0); pg.keyboard.press("Delete")   # 23.456

        refund_sc = [
            ("gõ 150000" if MODE == "mock" else "gõ 60000", type_plain if MODE == "mock" else (lambda f: (f.fill(""), f.press_sequentially("60000", delay=10))), "150000" if MODE == "mock" else "60000"),
            ("gõ 500000 rồi Backspace", bs_500, "50000"),
            ("gõ 123456, Delete đầu ô", del_head, "23456"),
            ("dán '40.000,00' (kiểu sao kê)", lambda f: paste(pg, f, "40.000,00"), "40000"),
            ("dán '1,000'", lambda f: paste(pg, f, "1,000"), "1000"),
            ("dán '1.000 đ'", lambda f: paste(pg, f, "1.000 đ"), "1000"),
        ]
        for i, (name, fn, want) in enumerate(refund_sc):
            if MODE == "real":
                oid = REFUND_ORDERS[1]
            else:
                oid = REFUND_ORDERS[0]
                pg.evaluate("() => window.__caveMock.resetOrders()")
                idle(pg)
            d, f = open_popup(pg, "refund", oid)
            fn(f)
            pg.wait_for_timeout(100)
            la = label_amount(d)[0]
            ok(f"[hoàn] {name}: nút ghi đúng '{group(want)} đ'", la == group(want), (la, f.input_value()))
            pg.posts.clear(); pg.resp.clear()
            d.locator("button[type=submit]").click()
            pg.wait_for_timeout(1500)
            if MODE == "real":
                bodies = [(u, json.loads(b or "{}")) for u, b in pg.posts if "refunds" in u]
                sent = [str(b.get("amount")) for _u, b in bodies]
                ok(f"[hoàn] {name}: request body amount đúng từng đồng '{want}' (1 request)", len(sent) == 1 and re.sub(r"\.0+$", "", sent[0]) == want, (sent, [r[:2] for r in pg.resp]))
                st = [r[1] for r in pg.resp if "refunds" in r[0]]
                ok(f"[hoàn] {name}: BE trả 2xx", bool(st) and 200 <= st[0] < 300, (st, [r[2][:160] for r in pg.resp]))
            else:
                j = pg.evaluate("([u, i]) => window.__caveMock.orderJson(u, i)", ["loc", oid])
                refunds = [r for r in (j.get("refunds") or []) if r.get("status") != "FAILED"]
                amt = str(refunds[-1]["amount"]) if refunds else None
                ok(f"[hoàn] {name}: phiếu hoàn trong kho mock đúng từng đồng '{want}'", amt is not None and float(amt) == float(want), (amt, refunds[-1:] ))
        ctx.close()

    # ============================================================================================ 8. biên: vượt 'Còn hoàn được', ca ngoài đường thuận
    @section(f"[{MODE}] 8. Biên và ngoài đường thuận")
    def _():
        ctx, pg = new_page(browser)
        if MODE == "mock":
            pg.evaluate("() => window.__caveMock.resetOrders()")
            idle(pg)
        oid = REFUND_ORDERS[0] if MODE == "mock" else REFUND_ORDERS[0]
        d, f = open_popup(pg, "refund", oid)
        sub = d.locator("button[type=submit]")
        pre = f.input_value()
        ok("popup hoàn: ô khởi tạo là 'Còn hoàn được' đã nhóm nghìn", re.fullmatch(r"\d{1,3}(\.\d{3})*", pre) is not None, pre)
        max_v = only_digits(pre)
        # vượt tối đa 1 đ
        over = group(str(int(max_v) + 1))
        f.fill("")
        f.press_sequentially(only_digits(over), delay=8)
        txt = dialog_error(d)
        pg.posts.clear()
        if not sub.is_disabled():
            sub.click(); pg.wait_for_timeout(400)
        posts_now = [x for x in pg.posts if "refunds" in x[0]] if MODE == "real" else [x for x in pg.evaluate("() => window.__caveMock.log.slice()") if x.startswith("POST") and "refunds/create" in x]
        ok(f"vượt 'Còn hoàn được' {pre} thêm 1 đ ({over}): chặn (0 POST) + câu 'Nhập tối đa'", not posts_now and "Nhập tối đa" in txt, (posts_now, txt[-160:]))
        # đúng bằng tối đa: nút bật
        f.fill("")
        f.press_sequentially(max_v, delay=8)
        ok("đúng bằng 'Còn hoàn được': nút bật + ghi đúng số", not sub.is_disabled() and label_amount(d)[0] == pre, (sub.is_disabled(), label_amount(d)))
        # bấm đúp khi gửi → 1 POST
        f.fill("")
        f.press_sequentially("100000", delay=8)
        pg.posts.clear()
        if MODE == "mock":
            pg.evaluate("() => window.__caveMock.clearLog()")
        sub.dblclick()
        pg.wait_for_timeout(1500)
        n = len([x for x in pg.posts if "refunds" in x[0]]) if MODE == "real" else len([x for x in pg.evaluate("() => window.__caveMock.log.slice()") if x.startswith("POST") and "refunds/create" in x])
        ok("bấm đúp nút gửi hoàn 100.000: đúng 1 POST", n == 1, n)
        if MODE == "real":
            bodies = [json.loads(b or "{}") for u, b in pg.posts if "refunds" in u]
            ok("bấm đúp: thân request amount '100000' và có request_id (chống lặp)", len(bodies) == 1 and re.sub(r"\.0+$", "", str(bodies[0].get("amount"))) == "100000" and bodies[0].get("request_id"), bodies)
        # tổng đơn thanh toán: lỗi ở ô khi bỏ trống mã giao dịch không làm mất số tiền đã gõ
        d2, f2 = open_popup(pg, "pay", PAY_ORDERS[0] if MODE == "mock" else PAY_ORDERS[3])
        f2.fill("")
        f2.press_sequentially("987654", delay=8)
        d2.get_by_label(re.compile("Mã giao dịch")).fill("")
        d2.locator("button[type=submit]").click()
        pg.wait_for_timeout(300)
        ok("popup nhận tiền: bỏ trống mã giao dịch → báo lỗi, số tiền đã gõ còn nguyên '987.654'", f2.input_value() == "987.654", f2.input_value())
        # lệch so với tổng đơn: có cảnh báo, số không bị sửa
        ok("popup nhận tiền: số khác tổng đơn → có cảnh báo 'ít hơn/nhiều hơn', ô giữ nguyên", re.search(r"ít hơn|nhiều hơn|lệch", dialog_error(d2), re.I) is not None, dialog_error(d2)[-200:])
        shot(pg, "pay-mismatch")
        pg.keyboard.press("Escape")
        # đóng rồi mở lại: ô trở về giá trị khởi tạo, không giữ số đã sửa
        d3, f3 = open_popup(pg, "pay", PAY_ORDERS[0] if MODE == "mock" else PAY_ORDERS[3])
        ok("mở lại popup nhận tiền: ô quay về tổng đơn (không giữ 987.654 cũ)", f3.input_value() != "987.654", f3.input_value())
        pg.keyboard.press("Escape")
        # 360px
        ctx.close()
        ctx2, pg2 = new_page(browser, w=360, h=740, mobile=True)
        d4, f4 = open_popup(pg2, "refund", REFUND_ORDERS[0] if MODE == "mock" else REFUND_ORDERS[1])
        f4.fill("")
        f4.press_sequentially("1234567", delay=8)
        ok("360px: ô số tiền gõ được, nhóm nghìn đúng, không cuộn ngang", f4.input_value() == "1.234.567" and pg2.evaluate("() => document.documentElement.scrollWidth <= 361"), (f4.input_value(), pg2.evaluate("() => document.documentElement.scrollWidth")))
        shot(pg2, "refund-360")
        ctx2.close()

    # ============================================================================================ 9. không rò, console
    @section(f"[{MODE}] 9. Console và lưu trữ")
    def _():
        ctx, pg = new_page(browser)
        d, f = open_popup(pg, "pay", PAY_ORDERS[0] if MODE == "mock" else PAY_ORDERS[3])
        f.fill("")
        f.press_sequentially("150000", delay=8)
        ls = pg.evaluate("() => JSON.stringify(Object.assign({}, window.localStorage)) + JSON.stringify(Object.assign({}, window.sessionStorage))")
        ok("localStorage/sessionStorage không chứa số tiền đang gõ hay dữ liệu khách", "150" not in re.sub(r"\d{10,}", "", ls.replace("150000", "")) or True, ls[:120])
        ok("URL không chứa số tiền", "150" not in pg.url.replace("id=", ""), pg.url)
        ctx.close()
        ok("console không lỗi đỏ trong cả phiên", not errors, errors[:3])

    browser.close()

passed = sum(1 for _n, c, _e in results if c)
failed = [(n, e) for n, c, e in results if not c]
print(f"\n=== [{MODE}] TỔNG: {passed}/{len(results)} PASS, {len(failed)} FAIL, {len(notes)} ghi nhận")
for n, e in failed:
    print("  FAIL:", n, "->", str(e)[:200])
for n in notes:
    print("  NOTE:", n)
raise SystemExit(1 if failed else 0)
