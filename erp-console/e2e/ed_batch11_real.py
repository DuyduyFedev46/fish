# Smoke trên BE THẬT (Lô 11 Nhà cung cấp): cần BE chạy ở :8000 (DB SQLite tạm đã `migrate` + `seed_demo`, có người dùng loc/ql1/kho1/giao1/cs2
# mật khẩu Songbien2026 và ít nhất 1 phiếu nhập đã ghi nhận cho nhà cung cấp "NK Đại Dương"), console build NEXT_PUBLIC_USE_MOCK=0
# NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 phục vụ ở :3102, BE bật CORS_ALLOWED_ORIGINS=http://127.0.0.1:3102.
# Mỗi lần chạy tạo thêm nhà cung cấp tên có hậu tố thời gian nên chạy lại được.
import os
import re
import sys
import time

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3102")
SHOTS = os.environ.get("SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots"))
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15000)
R = []
SUFFIX = str(int(time.time()))[-6:]


def ok(n, c, e=""):
    R.append((n, bool(c), e))
    print("PASS" if c else "FAIL", n, "" if c else e)


def session(b, user):
    ctx = b.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill("Songbien2026")
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, errs


def go(page, path):
    page.goto(BASE + path)
    page.wait_for_load_state("networkidle")


def table(page):
    t = page.locator("table.lt").first
    expect(t.locator("tbody tr").first).to_be_visible()
    expect(t.locator("tr.lt-skel")).to_have_count(0)
    return t


def heads(t):
    return [re.sub(r"\s+", " ", h).split("lock")[0].strip() for h in t.locator("thead th").all_inner_texts()]


def main():
    name = f"Vựa Thật {SUFFIX}"
    with sync_playwright() as p:
        b = p.chromium.launch()
        # ---- Chủ
        ctx, page, errs = session(b, "loc")
        go(page, "/suppliers/")
        t = table(page)
        h = heads(t)
        ok("BE thật, Chủ: có cột Tổng tiền mua", h[-1] == "Tổng tiền mua", str(h))
        row = [c.strip() for c in t.locator("tbody tr", has_text="NK Đại Dương").first.locator("td").all_inner_texts()]
        ok("BE thật, Chủ: 'NK Đại Dương' có phiếu và tổng tiền VNĐ", int(row[3]) >= 1 and re.search(r"\d\.\d{3}\.\d{3} đ$|\d{3}\.\d{3} đ$", row[-1]), str(row))
        page.screenshot(path=f"{SHOTS}/ed11-real-loc-danh-sach.png")
        page.get_by_role("button", name="Thêm nhà cung cấp").first.click()
        dlg = page.get_by_role("dialog", name="Thêm nhà cung cấp")
        dlg.get_by_label("Tên").fill("nk đại dương")
        dlg.get_by_role("button", name="Lưu nhà cung cấp").click()
        expect(dlg.get_by_role("button", name=re.compile("Thử lại"))).to_be_visible()
        txt = dlg.inner_text()
        ok("BE thật: tên trùng (khác hoa thường) → báo trùng dưới ô tên, hộp còn mở", dlg.is_visible() and re.search(r"trùng|đã có|đã tồn tại", txt, re.I), txt[:200])
        print("   thông báo BE thật:", re.sub(r"\s+", " ", txt)[:200])
        dlg.get_by_label("Tên").fill(name)
        dlg.get_by_label("Số điện thoại").fill("0988777666")
        dlg.get_by_role("button", name=re.compile("Thử lại|Lưu nhà cung cấp")).click()
        dlg.wait_for(state="detached")
        expect(page.get_by_text("Đã thêm nhà cung cấp.")).to_be_visible()
        t = table(page)
        expect(t.locator("tbody tr", has_text=name)).to_have_count(1)
        ok("BE thật: thêm được, hàng mới hiện", True)
        # chi tiết nhà cung cấp có phiếu
        t.locator("tbody tr", has_text="NK Đại Dương").first.locator("a").first.click()
        page.wait_for_selector("#supplier-detail")
        expect(page.locator("section[aria-label='Phiếu nhập'] table.lt tbody tr").first).to_be_visible()
        body = page.locator("body").inner_text()
        ok("BE thật, Chủ: chi tiết có Tổng tiền mua + bảng Phiếu nhập có Tiền mua", "Tổng tiền mua" in body and "Tiền mua" in page.locator("section[aria-label='Phiếu nhập']").inner_text())
        ok("BE thật: dòng thời gian tải được", page.locator("#supplier-timeline").count() == 1 and "Chưa tải được dòng thời gian" not in body)
        page.screenshot(path=f"{SHOTS}/ed11-real-loc-chi-tiet.png")
        # sửa tại chỗ ghi chú + ngừng + bật lại
        page.get_by_role("button", name="Sửa ghi chú").click()
        page.get_by_label("Ghi chú").first.fill("Ghi chú thử trên BE thật.")
        page.get_by_role("button", name="Lưu", exact=True).first.click()
        expect(page.locator("main")).to_contain_text("Ghi chú thử trên BE thật.")
        ok("BE thật: sửa ghi chú tại chỗ (PATCH)", True)
        page.get_by_role("button", name="Thao tác khác").click()
        page.get_by_role("menuitem", name=re.compile("^Ngừng hợp tác")).click()
        d2 = page.get_by_role("dialog", name="Ngừng hợp tác với nhà cung cấp này?")
        d2.get_by_role("button", name="Ngừng hợp tác").click()
        d2.wait_for(state="detached")
        expect(page.get_by_text("Đã ngừng hợp tác.")).to_be_visible()
        page.get_by_role("button", name="Thao tác khác").click()
        ok("BE thật: ngừng hợp tác → menu đổi 'Bật lại hợp tác'", page.get_by_role("menuitem", name=re.compile("^Bật lại hợp tác")).count() == 1)
        page.get_by_role("menuitem", name=re.compile("^Bật lại hợp tác")).click()
        d3 = page.get_by_role("dialog", name="Bật lại hợp tác?")
        d3.get_by_role("button", name="Bật lại hợp tác").click()
        d3.wait_for(state="detached")
        expect(page.get_by_text("Đã bật lại hợp tác.")).to_be_visible()
        ok("BE thật: bật lại hợp tác", True)
        dump = page.evaluate("() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage), location.href])")
        ok("BE thật: không có SĐT/tên nhà cung cấp trong storage hay URL", "0988777666" not in dump and name not in dump and "0988" not in page.url)
        ok("BE thật, Chủ: không console.error", not errs, str(errs[:3]))
        ctx.close()

        # ---- Quản lý
        ctx, page, errs = session(b, "ql1")
        go(page, "/suppliers/")
        t = table(page)
        ok("BE thật, ql1: không có cột Tổng tiền mua trong DOM", "Tổng tiền mua" not in page.content() and "Tổng tiền mua" not in heads(t), str(heads(t)))
        ok("BE thật, ql1: có nút Thêm", page.get_by_role("button", name="Thêm nhà cung cấp").count() >= 1)
        t.locator("tbody tr", has_text="NK Đại Dương").first.locator("a").first.click()
        page.wait_for_selector("#supplier-detail")
        expect(page.locator("section[aria-label='Phiếu nhập'] table.lt tbody tr").first).to_be_visible()
        ok("BE thật, ql1: chi tiết + bảng phiếu không có tiền mua", "Tổng tiền mua" not in page.content() and "Tiền mua" not in page.locator("section[aria-label='Phiếu nhập']").inner_text())
        ok("BE thật, ql1: không console.error", not errs, str(errs[:3]))
        ctx.close()

        # ---- Kho
        ctx, page, errs = session(b, "kho1")
        go(page, "/suppliers/")
        t = table(page)
        ok("BE thật, kho1: xem được, không có nút Thêm, không có cột tiền", page.get_by_role("button", name="Thêm nhà cung cấp").count() == 0 and "Tổng tiền mua" not in page.content())
        t.locator("tbody tr", has_text="NK Đại Dương").first.locator("a").first.click()
        page.wait_for_selector("#supplier-detail")
        ok("BE thật, kho1: không có nút Sửa", page.get_by_role("button", name="Sửa", exact=True).count() == 0)
        ctx.close()

        # ---- Giao hàng / CSKH
        for user in ("giao1", "cs2"):
            ctx, page, errs = session(b, user)
            ok(f"BE thật, {user}: không có menu Nhà cung cấp", page.locator(".nav a", has_text="Nhà cung cấp").count() == 0)
            go(page, "/suppliers/")
            page.wait_for_timeout(800)
            txt = page.locator("body").inner_text()
            ok(f"BE thật, {user}: vào thẳng → không có quyền, không bảng", "quyền" in txt.lower() and page.locator("table.lt").count() == 0 and "NK Đại Dương" not in txt, txt[:100])
            ctx.close()
        b.close()
    bad = [r for r in R if not r[1]]
    print(f"\n{len(R) - len(bad)}/{len(R)} PASS")
    sys.exit(1 if bad else 0)


main()
