# QA độc lập Lô 9 (ED-26), UI trên bản build MOCK (cổng 3101). Chỉ dữ liệu giả của mock.
#   SHOTS=<thư mục> python3 e2e/qa_ed_batch9_ui.py
# Bổ sung cho ed_batch9_returns.py của dev: ô chạm >= 44px ở 360px, bảng có bị cắt ở 1280/1440 không, liên kết tới
# đối tượng liên quan, bấm đúp, biến thể SĐT trong ghi chú, định dạng kg biên, nút theo từng Group, F5/Back/Esc, không tiền/giá vốn.
import os
import re
import sys

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3101")
SHOTS = os.environ.get("SHOTS", "/tmp")
os.makedirs(SHOTS, exist_ok=True)
R = []
expect.set_options(timeout=10_000)


def ok(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("PASS" if cond else "FAIL"), name, "" if cond else "  -> " + str(extra)[:600], flush=True)


SKIPPED = []


def skip(name, reason):
    SKIPPED.append((name, reason))
    print("SKIP", name, " -> ", reason, flush=True)


def login(page, user, pw="demo1234"):
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    page.wait_for_function("() => window.__caveMock && typeof window.__caveMock.pending === 'function'")


def settle(page):
    page.wait_for_function("() => window.__caveMock && window.__caveMock.pending() === 0")


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")
    settle(page)


def newp(browser, user, w=1280, h=860, touch=False):
    errors = []
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", **({"is_mobile": True, "has_touch": True} if touch else {}))
    page = ctx.new_page()
    page.on("console", lambda m: m.type in ("error", "warning") and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errors.append(m.type + ": " + m.text))
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    login(page, user)
    page.__errors = errors
    return ctx, page


def hscroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")


def small_targets(page, root="body", minimum=44):
    return page.evaluate("""([root, min]) => {
      const out = [];
      const sel = 'button, a[href], input:not([type=hidden]), select, textarea, [role=button], [role=radio], [role=tab], summary';
      document.querySelectorAll(root + ' ' + sel).forEach(e0 => {
        let e = e0;
        if (e0.matches('input[type=radio], input[type=checkbox]') && e0.closest('label')) e = e0.closest('label');
        if (e0.matches('main table tbody tr a')) e = e0.closest('tr');
        const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
        if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || cs.display === 'none') return;
        if (r.bottom < 0 || r.top > innerHeight * 3) return;
        if (r.width < min || r.height < min) out.push((e.innerText || e.getAttribute('aria-label') || e.name || e.tagName).trim().slice(0, 30) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
      });
      return out;
    }""", [root, minimum])


def table_clip(page):
    # bảng bị cắt: vùng bọc có overflow ẩn mà nội dung rộng hơn vùng nhìn
    return page.evaluate("""() => {
      const t = document.querySelector('main table'); if (!t) return null;
      let p = t.parentElement; const res = [];
      while (p && p !== document.body) {
        const cs = getComputedStyle(p);
        res.push({tag: p.tagName, cls: p.className.toString().slice(0, 40), ox: cs.overflowX, sw: p.scrollWidth, cw: p.clientWidth});
        p = p.parentElement;
      }
      return {tableW: t.getBoundingClientRect().width, chain: res.slice(0, 4)};
    }""")


def dlg(page):
    return page.get_by_role("dialog")


def run_roles(b):
    exp = {  # user: (thấy menu, nút Nhập, nút duyệt ở phiếu Chờ duyệt)
        "loc": (True, True, True), "ql1": (True, False, True), "kho1": (True, True, False),
        "giao1": (True, True, False), "giao2": (True, True, False), "cs2": (True, True, False), "cs1": (False, False, False),
    }
    for u, (menu, add, appr) in exp.items():
        ctx, p = newp(b, u)
        navs = [t.strip() for t in p.locator(".nav a").all_inner_texts()]
        ok(f"R {u}: menu Hàng hoàn {'có' if menu else 'không'}", any("Hàng hoàn" in t for t in navs) == menu, navs)
        go(p, "/returns/")
        if not menu:
            ok(f"R {u}: URL trực tiếp -> Không có quyền, không lộ dữ liệu", p.get_by_role("heading", name="Không có quyền").count() >= 1 and "RT-" not in p.inner_text("main"))
            ok(f"R {u}: chi tiết trực tiếp không lộ ghi chú", (go(p, "/returns/detail/?id=1") or True) and "Khách" not in p.inner_text("main"))
        else:
            ok(f"R {u}: nút Nhập hàng hoàn {'có' if add else 'không có'}", (p.get_by_role("button", name="Nhập hàng hoàn").count() == 1) == add)
            rows = p.locator("main table tbody tr").count()
            go(p, "/returns/detail/?id=1" if u not in ("giao2", "cs2") else "/returns/detail/?id=5")
            has_buttons = p.get_by_role("button", name="Tái nhập vào lô").count() + p.get_by_role("button", name="Huỷ hàng, ghi lỗ").count()
            if u in ("giao2", "cs2"):
                ok(f"R {u}: phiếu của người khác -> Không tìm thấy", p.get_by_role("heading", name="Không tìm thấy").count() >= 1 and has_buttons == 0)
                mine = [c.strip() for c in p.locator("main table tbody tr td:first-child").all_inner_texts()] if False else None
                go(p, "/returns/")
                got = [c.strip() for c in p.locator("main table tbody tr td:first-child").all_inner_texts()]
                ok(f"R {u}: danh sách chỉ phiếu của mình ({'RT-2' if u == 'giao2' else 'rỗng'})", got == (["RT-2"] if u == "giao2" else []), got)
            else:
                ok(f"R {u}: nút duyệt {'có' if appr else 'không có'}", (has_buttons == 2) == appr, has_buttons)
        ok(f"R {u}: không console error/warning", p.__errors == [], p.__errors)
        ctx.close()


def run_columns_and_format(b):
    ctx, p = newp(b, "ql1", w=1440, h=900)
    go(p, "/returns/")
    heads = [h.strip() for h in p.locator("main table thead th").all_inner_texts()]
    ok("AC1 cột: Trạng thái và Quyết định tách riêng, có Ghi chú, không có Lý do", "Trạng thái" in heads and "Quyết định" in heads and "Ghi chú" in heads and "Lý do" not in heads, heads)
    ok("AC1 chip Chờ duyệt / Đã duyệt có mặt", p.locator("main table tbody").inner_text().count("Chờ duyệt") >= 1 and "Đã duyệt" in p.locator("main table tbody").inner_text())
    clip = table_clip(p)
    print("INFO bảng 1440:", clip)
    # ô Ghi chú có nhìn thấy trọn vẹn không
    vis = p.evaluate("""() => {
      const th = [...document.querySelectorAll('main table thead th')].find(e => e.innerText.trim() === 'Ghi chú'); if (!th) return null;
      const r = th.getBoundingClientRect(); const wrap = document.querySelector('main table').closest('div');
      const w = wrap.getBoundingClientRect();
      return {thRight: Math.round(r.right), wrapRight: Math.round(w.right), vw: innerWidth, scrollW: wrap.scrollWidth, clientW: wrap.clientWidth, ox: getComputedStyle(wrap).overflowX};
    }""")
    print("INFO cột Ghi chú:", vis)
    p.screenshot(path=f"{SHOTS}/impl-list-ql1-1440.png")
    ok("B2 1440: khung bảng không cần cuộn ngang (scrollWidth <= clientWidth) và có đủ 10 cột", vis and vis["scrollW"] <= vis["clientW"] + 1 and len(heads) >= 10, (vis, heads))
    p.set_viewport_size({"width": 1280, "height": 860})
    p.wait_for_timeout(400)
    v2 = p.evaluate("""() => { const w = document.querySelector('main table').closest('.lt-scroll') || document.querySelector('main table').closest('div'); const th = [...document.querySelectorAll('main table thead th')].find(e => e.innerText.trim() === 'Ghi chú'); return {scrollW: w.scrollWidth, clientW: w.clientWidth, ghiChu: !!th && th.getBoundingClientRect().right <= w.getBoundingClientRect().right + 1, cols: document.querySelectorAll('main table thead th:not([style*="none"])').length}; }""")
    print("INFO bảng 1280:", v2)
    ok("B2 1280: khung bảng không cần cuộn ngang và cột Ghi chú nằm trọn khung", v2["scrollW"] <= v2["clientW"] + 1 and v2["ghiChu"], v2)
    p.screenshot(path=f"{SHOTS}/impl-list-ql1-1280.png")
    p.set_viewport_size({"width": 1440, "height": 900})
    ok("AC1 cột Ghi chú nằm trọn trong khung ở 1440px (không bị cắt, hoặc khung có cuộn ngang rõ ràng)", vis and (vis["thRight"] <= vis["wrapRight"] + 1 or vis["ox"] in ("auto", "scroll")) , vis)
    ok("AC1 cột Ghi chú không bị cắt ở 1440px khi cuộn khung là dư thừa: thRight<=wrapRight", vis and vis["thRight"] <= vis["wrapRight"] + 1, vis)
    body = p.locator("main").inner_text()
    ok("kg theo mẫu '0,3 kg' / '1 kg' (dấu phẩy, không '.000', không 'kg.')", re.search(r"\b0,3 kg\b", body) and re.search(r"\b1 kg\b", body) and not re.search(r"\d\.\d{3}\b", body) and "0.3" not in body, body[:300])
    ok("không có tiền / giá vốn trong danh sách (đ, VND, ₫, giá, vốn, cost)", not re.search(r"₫|\bđ\b|VND|VNĐ|[Gg]iá vốn|landed|cost", body), body)
    ok("không có mã BR / mã lỗi / undefined / NaN", not re.search(r"BR-[A-Z]{2}|RETURN_|STALE_|undefined|NaN|\[object", body))
    amber = p.evaluate("""() => { const hs = [...document.querySelectorAll('main table thead th')].map(h => h.innerText.trim()); const i = hs.findIndex(h => h.startsWith('Ngoài kho lạnh'));
        return {col: i, rows: [...document.querySelectorAll('main table tbody tr')].map(r => { const td = r.children[i]; return r.children[0].innerText.trim() + ':' + td.innerText.trim().replace(/\\s+/g, ' ') + ':' + getComputedStyle(td.querySelector('.warn-text') || td).color; })}; }""")
    base_color = p.evaluate("() => getComputedStyle(document.querySelector('main table tbody td')).color")
    long_rows = [r for r in amber["rows"] if re.search(r"(\d+) giờ", r) and (int(re.search(r"(\d+) giờ", r).group(1)) > 2 or (int(re.search(r"(\d+) giờ", r).group(1)) == 2 and re.search(r"giờ (\d+) phút", r) and int(re.search(r"giờ (\d+) phút", r).group(1)) > 0))]
    short_rows = [r for r in amber["rows"] if r not in long_rows]
    ok("B3 cột Ngoài kho lạnh tìm thấy và có dòng quá 2 giờ trong dữ liệu mock", amber["col"] >= 0 and len(long_rows) >= 1, amber)
    normal = {r.rsplit(":", 1)[1] for r in short_rows}
    ok("B3 dòng không quá 2 giờ cùng một màu chữ thường", len(normal) == 1, short_rows)
    ok("B3 dòng quá 2 giờ có màu cảnh báo khác màu chữ thường", all(r.rsplit(":", 1)[1] not in normal for r in long_rows), (long_rows, normal))
    ok("B3 dòng quá 2 giờ có chữ '(quá 2 giờ)' cho trình đọc màn hình", all("quá 2 giờ" in r for r in long_rows), long_rows)
    print("INFO cột Ngoài kho lạnh:", amber)
    # chi tiết: liên kết đối tượng liên quan
    go(p, "/returns/detail/?id=1")
    links = p.locator("main a[href]").evaluate_all("els => els.map(e => e.innerText.trim() + ' -> ' + e.getAttribute('href'))")
    print("INFO liên kết ở chi tiết:", links)
    ok("Chi tiết: Phiếu giao là liên kết bấm được (UI-RULES: đối tượng liên quan là link)", any(re.search(r"GH-HD", l) for l in links), links)
    ok("Chi tiết: Đơn là liên kết bấm được", any(re.search(r"DH-2609", l) for l in links), links)
    skip("Chi tiết: Lô là liên kết bấm được", "chờ Lô 7 (Kho & lô) vào main; dev ghi nợ, QA không tính lỗi")
    p.screenshot(path=f"{SHOTS}/impl-detail-ql1-1440.png")
    ok("Chi tiết: không có tiền / giá vốn", not re.search(r"₫|VND|[Gg]iá vốn|landed", p.locator("main").inner_text()))
    ok("không console error/warning", p.__errors == [], p.__errors)
    ctx.close()


def run_create_edges(b):
    ctx, p = newp(b, "giao1")
    go(p, "/returns/")
    p.get_by_role("button", name="Nhập hàng hoàn").click()
    d = dlg(p)
    p.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
    opts = d.get_by_label("Phiếu giao").locator("option").all_inner_texts()
    ok("F2m giao1: chỉ phiếu của mình (0036, 0038), không có phiếu của người khác (0033/0034/0039)", all(not any(x in o for x in ("0033", "0034", "0039")) for o in opts) and any("0038" in o for o in opts), opts)
    d.get_by_label("Phiếu giao").select_option(label=[o for o in opts if "0038" in o][0])
    p.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
    facts = d.locator("[data-qty-facts]").inner_text()
    ok("AC: hiện 'Đã giao 1 kg, đã hoàn 0,5 kg, còn hoàn được 0,5 kg'", "Đã giao 1 kg" in facts and "đã hoàn 0,5 kg" in facts and "còn hoàn được 0,5 kg" in facts, facts)
    qty = d.get_by_label("Số kg hoàn")
    for bad, why in (("-1", "âm"), ("abc", "chữ"), ("0", "0"), ("0.0001", "4 số lẻ"), ("1e1", "ký hiệu mũ"), ("0.501", "vượt 0,001"), ("2", "vượt nhiều")):
        qty.fill(bad)
        d.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
        t = d.inner_text()
        rows_before = None
        ok(f"F2m: số kg {why} ({bad}) bị chặn tại chỗ, hộp vẫn mở, không toast thành công", dlg(p).count() == 1 and "Đã gửi phiếu hàng hoàn" not in p.inner_text("body"), t[:200])
    qty.fill("0,5")  # dấu phẩy kiểu VN
    d.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    p.wait_for_timeout(1200)
    still = dlg(p).count() == 1
    ok("F2m: nhập '0,5' (dấu phẩy VN) = đúng phần còn lại -> được nhận (hộp đóng) hoặc báo lỗi rõ, không treo", (not still) or "Số kg" in dlg(p).inner_text(), dlg(p).inner_text()[:200] if still else "")
    print("INFO '0,5' ->", "hộp còn mở: " + dlg(p).inner_text()[:200].replace("\n", " | ") if still else "đã nhận")
    p.screenshot(path=f"{SHOTS}/impl-f2m-after-comma-1280.png")
    ctx.close()

    # biến thể SĐT trong ghi chú
    ctx, p = newp(b, "kho1")
    go(p, "/returns/")
    variants = [("0912345678", True), ("0912 345 678", True), ("091.234.5678", True), ("+84 912 345 678", True), ("84912345678", True),
                ("0912,345,678", "known_miss"), ("số 0912-345-678", True), ("khách hẹn 10/10/2026 9h", "known_false_positive"), ("Mua 2 kg lúc 14h30", False)]
    p.get_by_role("button", name="Nhập hàng hoàn").click()
    d = dlg(p)
    p.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
    opts = d.get_by_label("Phiếu giao").locator("option").all_inner_texts()
    d.get_by_label("Phiếu giao").select_option(label=[o for o in opts if "0036" in o][0])
    p.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
    d.get_by_label("Số kg hoàn").fill("0.1")
    for text, should_block in variants:
        d.get_by_label(re.compile("Ghi chú")).fill(text)
        d.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
        p.wait_for_timeout(250)
        blocked = dlg(p).count() == 1 and "số điện thoại" in d.inner_text()
        if should_block in ("known_miss", "known_false_positive"):
            # quyết định #4: luật 9 chữ số liền đã được chấp nhận; chỉ xác nhận hành vi đúng như đã ghi, không tính lỗi
            expected_blocked = should_block == "known_false_positive"
            ok(f"PII ghi chú {text!r}: hành vi đúng như đã chấp nhận ở quyết định #4 ({'chặn nhầm' if expected_blocked else 'bỏ sót'})", blocked == expected_blocked, blocked)
            if dlg(p).count() == 0:
                p.get_by_role("button", name="Nhập hàng hoàn").click()
                d = dlg(p)
                p.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
                opts = d.get_by_label("Phiếu giao").locator("option").all_inner_texts()
                d.get_by_label("Phiếu giao").select_option(label=[o for o in opts if "0036" in o][0])
                p.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
                d.get_by_label("Số kg hoàn").fill("0.1")
            continue
        if should_block and not blocked:
            ok(f"PII ghi chú {text!r}: bị chặn", False, "FE không chặn, phiếu đã/đang được gửi; BE cũng không chặn (xem API)")
            p.get_by_role("button", name="Nhập hàng hoàn").count() and None
            if dlg(p).count() == 0:
                p.get_by_role("button", name="Nhập hàng hoàn").click()
                d = dlg(p)
                p.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
                opts = d.get_by_label("Phiếu giao").locator("option").all_inner_texts()
                d.get_by_label("Phiếu giao").select_option(label=[o for o in opts if "0036" in o][0])
                p.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
                d.get_by_label("Số kg hoàn").fill("0.1")
        elif not should_block and blocked:
            ok(f"PII ghi chú {text!r}: KHÔNG bị chặn nhầm", False, "chặn nhầm câu thường (đã ghi ở quyết định #4)")
        else:
            ok(f"PII ghi chú {text!r}: {'bị chặn' if should_block else 'không bị chặn'}", True)
        if dlg(p).count() == 0:
            break
    ok("PII: không lọt vào URL/storage (trừ danh sách người dùng mock và token)", "0912" not in p.url and "0912" not in p.evaluate("() => JSON.stringify(Object.entries(localStorage).filter(([k]) => !k.includes('mock_users') && !k.includes('token')).concat(Object.entries(sessionStorage)))"))
    ctx.close()

    # bấm đúp "Gửi duyệt": chỉ 1 phiếu
    ctx, p = newp(b, "kho1")
    go(p, "/returns/")
    n0 = p.locator("main table tbody tr").count()
    p.get_by_role("button", name="Nhập hàng hoàn").click()
    d = dlg(p)
    p.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
    opts = d.get_by_label("Phiếu giao").locator("option").all_inner_texts()
    d.get_by_label("Phiếu giao").select_option(label=[o for o in opts if "0036" in o][0])
    p.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
    d.get_by_label("Số kg hoàn").fill("0.1")
    btn = d.get_by_role("button", name="Gửi duyệt")
    btn.dblclick()
    p.wait_for_function("() => !document.querySelector('[role=dialog]')")
    settle(p)
    p.wait_for_timeout(500)
    n1 = p.locator("main table tbody tr").count()
    ok("Bấm đúp Gửi duyệt: chỉ tạo 1 phiếu (không trùng)", n1 == n0 + 1, (n0, n1))
    ok("không console error/warning", p.__errors == [], p.__errors)
    ctx.close()


def run_approve_edges(b):
    ctx, p = newp(b, "ql1")
    go(p, "/returns/detail/?id=1")
    p.get_by_role("button", name="Tái nhập vào lô").click()
    d = dlg(p)
    # Esc đóng hộp, không duyệt
    p.keyboard.press("Escape")
    p.wait_for_timeout(300)
    ok("F2n: Esc đóng hộp, phiếu vẫn Chờ duyệt", dlg(p).count() == 0 and p.get_by_role("button", name="Tái nhập vào lô").count() == 1)
    p.get_by_role("button", name="Tái nhập vào lô").click()
    d = dlg(p)
    ok("F2n: focus nằm trong hộp khi mở", p.evaluate("() => !!document.activeElement && !!document.activeElement.closest('[role=dialog]')"))
    ok("F2n: có aria-modal / tên hộp", d.get_attribute("aria-modal") == "true" or d.get_attribute("aria-labelledby") is not None or d.get_attribute("aria-label") is not None, d.evaluate("e => e.outerHTML.slice(0,200)"))
    ok("F2n: tóm tắt không có tiền/giá vốn", not re.search(r"₫|VND|[Gg]iá vốn|landed", d.inner_text()))
    d.get_by_role("button", name="Duyệt", exact=True).dblclick()
    p.wait_for_function("() => !document.querySelector('[role=dialog]')")
    settle(p)
    body = p.inner_text("main")
    ok("Bấm đúp Duyệt: kết quả Đã duyệt, không hiện băng xung đột/lỗi giả", "Đã duyệt" in body and "Tải lại" not in p.inner_text("body") and "đã được duyệt" not in p.inner_text("body"), body[:200])
    # F5 trên chi tiết
    p.reload(); p.wait_for_load_state("networkidle")
    ok("F5 ở chi tiết: không văng, vẫn thấy RT-1 (mock nạp lại dữ liệu gốc nên chỉ kiểm không lỗi)", p.locator("main").inner_text() != "" and p.__errors == [], p.__errors)
    # Back/forward
    go(p, "/returns/")
    p.locator("main table tbody tr", has_text="RT-2").click()
    p.wait_for_url(re.compile(r"id=2"))
    p.go_back()
    p.wait_for_url(re.compile(r"/returns/?$"))
    settle(p)
    p.wait_for_function("() => document.querySelectorAll('main table tbody tr').length > 0")
    ok("Back từ chi tiết về danh sách", "RT-" in p.locator("main").inner_text())
    ctx.close()
    # mở màn cũ: phiếu đã duyệt từ nơi khác -> nút 409 -> tải lại
    ctx, p = newp(b, "loc")
    go(p, "/returns/detail/?id=5")
    p.evaluate("() => window.__caveMock.returnsMarkApproved(5)")
    p.get_by_role("button", name="Huỷ hàng, ghi lỗ").click()
    d = dlg(p)
    d.get_by_role("button", name="Duyệt", exact=True).click()
    p.wait_for_function("() => document.querySelector('[role=dialog]') && document.querySelector('[role=dialog]').innerText.includes('Tải lại')")
    ok("AC4 màn cũ: 409 -> băng xung đột có Tải lại, không lộ mã", "STALE" not in d.inner_text() and d.get_by_role("button", name="Tải lại").count() >= 1)
    ctx.close()


def run_mobile(b):
    ctx, p = newp(b, "giao1", w=360, h=780, touch=True)
    go(p, "/returns/")
    ok("360 danh sách: không cuộn ngang trang", hscroll(p) <= 1, hscroll(p))
    st = small_targets(p, "main")
    print("INFO ô nhỏ <44px danh sách 360:", st)
    ok("360 danh sách: các ô bấm >= 44px", st == [], st)
    p.screenshot(path=f"{SHOTS}/impl-list-giao1-360.png")
    p.get_by_role("button", name="Nhập hàng hoàn").click()
    d = dlg(p)
    p.wait_for_function("() => document.querySelectorAll('[role=dialog] select')[0].options.length > 1")
    ok("360 F2m: không cuộn ngang", hscroll(p) <= 1, hscroll(p))
    st = small_targets(p, "[role=dialog]")
    print("INFO ô nhỏ F2m 360:", st, "| số phần tử trong hộp:", p.locator("[role=dialog] input, [role=dialog] select, [role=dialog] textarea, [role=dialog] button").count())
    ok("360 F2m: các ô/nút >= 44px", st == [], st)
    p.screenshot(path=f"{SHOTS}/impl-f2m-giao1-360.png")
    ctx.close()
    ctx, p = newp(b, "ql1", w=360, h=780, touch=True)
    go(p, "/returns/detail/?id=1")
    ok("360 chi tiết: không cuộn ngang", hscroll(p) <= 1, hscroll(p))
    st = small_targets(p, "main")
    print("INFO ô nhỏ chi tiết 360:", st)
    ok("360 chi tiết: ô bấm >= 44px", st == [], st)
    p.screenshot(path=f"{SHOTS}/impl-detail-ql1-360.png")
    p.get_by_role("button", name="Tái nhập vào lô").click()
    st = small_targets(p, "[role=dialog]")
    ok("360 F2n: ô bấm >= 44px", st == [], st)
    ok("360 F2n: không cuộn ngang", hscroll(p) <= 1)
    p.screenshot(path=f"{SHOTS}/impl-f2n-ql1-360.png")
    ctx.close()
    ctx, p = newp(b, "giao1", w=360, h=780, touch=True)
    go(p, "/my-deliveries/")
    ok("360 Việc giao của tôi: không cuộn ngang", hscroll(p) <= 1)
    card = p.locator("li[data-status=FAILED]").first
    st = small_targets(p, "li[data-status=FAILED]")
    print("INFO ô nhỏ thẻ Giao thất bại 360:", st)
    ok("360 thẻ Giao thất bại: nút >= 44px", st == [], st)
    p.screenshot(path=f"{SHOTS}/impl-mydeliveries-failed-360.png")
    ctx.close()


def run_privacy(b):
    ctx, p = newp(b, "ql1")
    for path in ("/returns/", "/returns/detail/?id=1", "/returns/detail/?id=3"):
        go(p, path)
        txt = p.locator("main").inner_text()
        ok(f"PII {path}: không SĐT, không địa chỉ khách, không tên khách", not re.search(r"0\d{9}|\+84", txt) and not re.search(r"Nguyễn|Trần|Lê Văn|Phạm", txt), txt[:200])
        dump = p.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), document.cookie])")
        dump2 = p.evaluate("() => JSON.stringify(Object.entries(localStorage).filter(([k]) => !k.includes('mock_users') && !k.includes('token')).concat(Object.entries(sessionStorage), [document.cookie]))")
        ok(f"PII {path}: storage (trừ danh sách người dùng mock) không chứa ghi chú/tên/SĐT", not re.search(r"Khách|Sai địa chỉ|Xe hỏng|0\d{9}", dump2), dump2[:300])
        ok(f"PII {path}: URL không chứa chữ tự do", re.fullmatch(r"[^?]*(\?id=\d+)?", p.url.replace(BASE, "")) is not None, p.url)
    ok("không console error/warning", p.__errors == [], p.__errors)
    ctx.close()


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for fn in (run_roles, run_columns_and_format, run_create_edges, run_approve_edges, run_mobile, run_privacy):
            try:
                fn(b)
            except Exception as e:  # noqa: BLE001
                ok(f"{fn.__name__}: chạy hết không lỗi", False, repr(e)[:500])
        b.close()
    bad = [r for r in R if not r[1]]
    print(f"\nTỔNG {len(R) + len(SKIPPED)} ca, {len(R) - len(bad)} đạt, {len(bad)} lỗi, {len(SKIPPED)} bỏ qua (⏸)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
