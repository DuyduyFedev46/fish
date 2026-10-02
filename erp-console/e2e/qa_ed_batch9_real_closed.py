# QA Lô 9 lần 2 (B4): lô bị chốt khi hộp "Nhập hàng hoàn" đang mở -> BE 400 RETURN_BATCH_CLOSED, FE hiện câu tiếng Việt dưới ô Lô.
# Chạy trên BE thật :8000 (DB QA_DB nạp bằng qa_ed_batch9 fixture) + console thật :3102. Dữ liệu giả.
import os, re, sqlite3, sys
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BASE", "http://127.0.0.1:3102")
DB = os.environ["QA_DB"]
SHOTS = os.environ.get("SHOTS", "/tmp")
expect.set_options(timeout=15000)
R = []


def ok(n, c, e=""):
    R.append((n, bool(c)))
    print("PASS" if c else "FAIL", n, "" if c else "  -> " + str(e)[:500], flush=True)


def q(sql, *a):
    c = sqlite3.connect(DB); r = c.execute(sql, a).fetchall(); c.commit(); c.close(); return r


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 360, "height": 780}, reduced_motion="reduce", is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errs, posts = [], []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    page.on("response", lambda r: r.request.method == "POST" and "inventory/returns" in r.url and posts.append(r.status))
    page.goto(BASE + "/login/"); page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill("giao1"); page.get_by_label("Mật khẩu").fill("Songbien2026")
    page.get_by_role("button", name="Đăng nhập").click(); page.wait_for_selector(".nav a", state="attached")
    page.goto(BASE + "/my-deliveries/"); page.wait_for_load_state("networkidle")
    page.locator("li[data-status=FAILED]").first.get_by_role("button", name="Mang hàng về kho").click()
    d = page.get_by_role("dialog")
    page.wait_for_function("() => document.querySelector('[role=dialog] select') && document.querySelector('[role=dialog] select').value !== ''")
    page.wait_for_timeout(800)
    sel = d.get_by_label(re.compile("^Lô"))
    opts = sel.locator("option").all_inner_texts()
    print("INFO lô:", opts)
    sel.select_option(label=[o for o in opts if "TOM01" in o][0])
    page.wait_for_function("() => document.querySelector('[data-qty-facts]') !== null")
    ok("B4 lô TOM01 còn mở lúc chọn: facts hiện đủ", "còn hoàn được" in d.locator("[data-qty-facts]").inner_text())
    q("update inventory_batch set status='CLOSED' where id=2")  # lô bị chốt khi màn hình còn mở (màn cũ)
    d.get_by_label("Số kg hoàn").fill("1")
    d.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    page.wait_for_function("() => document.querySelector('[role=dialog]').innerText.includes('đã chốt')")
    t = d.inner_text()
    ok("B4 màn cũ: BE chặn 400, hộp còn mở, hiện 'đã chốt' bằng tiếng Việt", page.get_by_role("dialog").count() == 1 and "đã chốt" in t and posts == [400], (posts, t[:300]))
    ok("B4 câu lỗi không lộ mã (RETURN_, BR-, 400)", not re.search(r"RETURN_|BR-[A-Z]{2}|\b400\b|undefined", t), t[:300])
    ok("B4 DB: không có phiếu hàng hoàn mới, tồn lô không đổi", q("select count(*) from inventory_returntostock")[0][0] == 0 and q("select count(*) from inventory_stockledgerentry where reference like '%RT-%'")[0][0] == 0)
    page.screenshot(path=f"{SHOTS}/impl-real-batch-closed-360.png")
    ok("B4 360px không cuộn ngang", page.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
    # đổi sang lô còn mở (CA01) -> câu lỗi biến mất, gửi được
    sel.select_option(label=[o for o in opts if "CA01" in o][0])
    page.wait_for_function("() => !document.querySelector('[role=dialog]').innerText.includes('đã chốt')")
    d.get_by_label("Số kg hoàn").fill("1")
    d.get_by_role("button", name=re.compile("Gửi duyệt|Thử lại")).click()
    page.wait_for_function("() => !document.querySelector('[role=dialog]')")
    ok("B4 đổi sang lô còn mở: gửi được 201", posts[-1] == 201 and q("select count(*) from inventory_returntostock")[0][0] == 1, posts)
    ok("B4 không console.error", errs == [], errs)
    b.close()
bad = [r for r in R if not r[1]]
print(f"\nTỔNG {len(R)} ca, {len(R) - len(bad)} đạt, {len(bad)} lỗi")
sys.exit(1 if bad else 0)
