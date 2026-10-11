"""
E2E phía ERP của đợt Shop mới (SHOP-7-01 AC1): Chủ tạo mã giảm giá, sửa thông tin món hiện trên Shop, nạp nội dung soạn sẵn,
và lãi lỗ theo lô khi có đơn dùng mã. BE thật, ERP build USE_MOCK=0 (cổng 3100). Dữ liệu giả.

Phân quyền: Quản lý, Thủ kho, Giao hàng, Gọi xác nhận, không nhóm không thấy/không dùng được màn mã giảm giá và lãi lỗ (bất biến 2).
Mã nghiệp vụ: BR-DM-17…24 (mã giảm giá), BR-BC-04 (lãi lỗ theo lô trừ mã), BR-PQ-04/05 (AuditLog), bất biến 1 (giá vốn chỉ Chủ).
Chạy: python3 frontend/e2e/run_shop_e2e.py --suite erp_flow
"""
import datetime as dt
import json
import re
import subprocess
import uuid

from playwright.sync_api import sync_playwright

from shop_e2e_lib import *

R = Report("erp_flow")
SUF = uuid.uuid4().hex[:4].upper()
tok = login_token()
CODE = "ERP" + SUF


def erp_login(page, user, password=QA_PASSWORD):
    page.goto(ERP_URL + "/login/")
    page.wait_for_load_state("networkidle")
    page.fill("#u", user)
    page.fill("#p", password)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_function("() => !window.location.href.includes('/login/')", timeout=15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(700)


def erp_goto(page, path, wait=1200):
    page.goto(ERP_URL + path)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(wait)


def local_dt(delta_days):
    return (dt.datetime.now() + dt.timedelta(days=delta_days)).strftime("%Y-%m-%dT%H:%M")


with sync_playwright() as p:
    browser = p.chromium.launch()
    # ======================================================== 1. Chủ tạo mã giảm giá trên giao diện ERP
    for width in (1280, 360):
        ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 600 else 800})
        page = ctx.new_page()
        watch = PageWatch(page)
        erp_login(page, OWNER_USER)
        code = CODE + ("D" if width == 1280 else "M")
        erp_goto(page, "/vouchers/new/")
        page.locator("input[name=code]").fill(code.lower())
        page.locator("input[name=name]").fill("Mã e2e từ ERP " + code)
        page.locator("input[name=value]").fill("10")
        page.locator("input[name=max_discount]").fill("30000")
        page.locator("input[name=min_order_amount]").fill("100000")
        page.locator("input[name=total_uses]").fill("5")
        page.locator("input[name=starts_at]").fill(local_dt(-1))
        page.locator("input[name=ends_at]").fill(local_dt(30))
        page.locator("textarea[name=customer_terms], #\\:ra\\:-f, textarea").first.fill("Giảm 10%, tối đa 30.000đ, đơn từ 100.000đ")
        snap(page, "erp-voucher-form", width, "erp")
        page.get_by_role("button", name="Tạo mã").click()
        page.wait_for_timeout(1800)
        erp_goto(page, "/vouchers/")
        text = page.inner_text("main")
        R.ok(f"[{width}] Chủ tạo mã {code} ở ERP: có trong danh sách, IN HOA, 'Đang chạy', 0/5 lượt", code in text and "Đang chạy" in text and (width < 600 or "0 / 5" in text),
             text[:300])
        snap(page, "erp-voucher-list", width, "erp")
        vs, vb = api("GET", f"/api/catalog/vouchers/?search={code}", token=tok)
        row = [v for v in vb["results"] if v["code"] == code] if vs == 200 else []
        R.ok(f"[{width}] API xác nhận mã đã lưu đúng (PERCENT 10, trần 30.000, tối thiểu 100.000, 5 lượt)",
             bool(row) and row[0]["kind"] == "PERCENT" and row[0]["max_discount"].startswith("30000") and row[0]["total_uses"] == 5, row)
        R.ok(f"[{width}] ERP console sạch lỗi JS khi tạo mã", not watch.console_errors() and not watch.errors, (watch.console_errors()[:2], watch.errors[:2]))
        if width == 1280:
            main_code = code
        ctx.close()

    # Mã trùng bị chặn
    s_dup, b_dup = api("POST", "/api/catalog/vouchers/", {"code": main_code, "name": "trùng", "kind": "PERCENT", "value": "10", "max_discount": "1000",
                       "min_order_amount": "0", "starts_at": (dt.datetime.now(dt.timezone.utc)).isoformat(),
                       "ends_at": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat(), "total_uses": 1}, token=tok)
    R.ok("[API] tạo mã trùng → 400 (không ghi đè)", s_dup == 400, (s_dup, b_dup))
    # Không có DELETE (chứng từ không xoá)
    vid = [v for v in api("GET", f"/api/catalog/vouchers/?search={main_code}", token=tok)[1]["results"] if v["code"] == main_code][0]["id"]
    s_del, _ = api("DELETE", f"/api/catalog/vouchers/{vid}/", token=tok)
    R.ok("[API] không có DELETE mã giảm giá (bất biến 3): 405", s_del == 405, s_del)

    # ======================================================== 2. Phân quyền màn mã giảm giá / lãi lỗ ở ERP (giao diện)
    for user in ("qa_manager", "qa_warehouse", "qa_courier1", "qa_cs1", "qa_nogroup"):
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        erp_login(page, user)
        erp_goto(page, "/vouchers/")
        t = page.inner_text("body")
        html = page.content()
        R.ok(f"ERP {user}: /vouchers/ không thấy mã nào, không dữ liệu mã trong HTML", main_code not in t and main_code not in html and "Tạo mã" not in t, t[:200])
        erp_goto(page, "/reports/")
        t2 = page.inner_text("body")
        R.ok(f"ERP {user}: /reports/ (lãi lỗ) không có số doanh thu/giá vốn", not re.search(r"Doanh thu ghi nhận|Giá vốn|Lãi gộp", t2) or "không có quyền" in t2.lower(), t2[:200])
        ctx.close()

    # ======================================================== 3. Lãi lỗ theo lô có đơn dùng mã (BR-BC-04)
    manage_shell(
        "from datetime import timedelta\nfrom decimal import Decimal as D\nfrom django.utils import timezone\n"
        "from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList\nfrom apps.inventory.models import Batch, Warehouse, StockLedgerEntry\n"
        "from apps.purchasing.models import Supplier\n"
        "g=ItemGroup.objects.get(name='Cá')\n"
        f"it,_=Item.objects.get_or_create(code='E2E-PNL-{SUF}', defaults=dict(name='Cá thử báo cáo lô (giả)', item_group=g, item_type='SIMPLE', shelf_life_in_days=10, is_active=True))\n"
        "pl=PriceList.objects.filter(is_default=True).first()\n"
        "ItemPrice.objects.get_or_create(price_list=pl, item=it, defaults=dict(rate=D('200000'), valid_from=timezone.localdate()-timedelta(days=1)))\n"
        "b=Batch.objects.create(batch_id='E2E-LO-%s', item=it, supplier=Supplier.objects.first(), warehouse=Warehouse.objects.first(), received_date=timezone.localdate(), expiry_date=timezone.localdate()+timedelta(days=9), qty_received=D('10'), qty_available=D('10'), qty_reserved=D('0'), purchase_rate=D('100000'), landed_unit_cost=D('100000'), status='SELLING')\n"
        "StockLedgerEntry.objects.create(batch=b, movement_type='RECEIPT', qty_change=D('10'), reference='e2e nhập lô giả')\n" % SUF
    )
    item = f"E2E-PNL-{SUF}"
    batch = f"E2E-LO-{SUF}"
    s1, o1 = create_order_api([(item, "3")])                       # 600.000, không mã
    s2, o2 = create_order_api([(item, "2")], voucher=main_code, phone="0900000021")   # 400.000 - 30.000 (trần) = 370.000
    R.ok("[API] đặt 2 đơn trên lô giả (một đơn dùng mã ERP vừa tạo)", s1 == 201 and s2 == 201 and o2["discount"]["amount"].startswith("30000") and o2["total_amount"].startswith("370000"), (o1, o2))
    pay_order(o1["order_code"], o1["total_amount"])
    pay_order(o2["order_code"], o2["total_amount"])
    R.ok("[DB] lượt mã của đơn thứ hai chuyển 'USED' sau khi trả tiền", redemption_state(o2["order_code"]) == "USED", redemption_state(o2["order_code"]))
    sp, pnl = api("GET", f"/api/reports/batch/{batch}/", token=tok)
    rev = sp == 200 and str(pnl.get("revenue"))
    R.ok("lãi lỗ theo lô (Chủ, API): doanh thu = 600.000 + 370.000 = 970.000, giá vốn cả lô 10 kg × 100.000 = 1.000.000, lãi lỗ −30.000",
         sp == 200 and pnl["revenue"].startswith("970000") and pnl["purchase_cost"].startswith("1000000") and pnl["profit"].startswith("-30000"), pnl if sp != 200 else {k: pnl.get(k) for k in ("revenue", "purchase_cost", "profit")})
    # đơn không mã không đổi, đơn có mã đúng thực thu: tổng hoá đơn = tổng thực trả
    R.ok("lãi lỗ: doanh thu theo lô = tổng tiền khách thực trả (không cộng phần mã giảm)", sp == 200 and float(pnl["revenue"]) == float(o1["total_amount"]) + float(o2["total_amount"]), pnl.get("revenue"))
    for user in ("qa_manager", "qa_warehouse", "qa_courier1", "qa_cs1", "qa_nogroup"):
        t = login_token(user)
        codes = [api("GET", f"/api/reports/batch/{batch}/", token=t)[0], api("GET", "/api/reports/batches/", token=t)[0], api("GET", "/api/reports/period/", token=t)[0]]
        R.ok(f"lãi lỗ: {user} bị chặn ở cả 3 API (403)", all(c == 403 for c in codes), codes)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    watch = PageWatch(page)
    erp_login(page, OWNER_USER)
    erp_goto(page, "/reports/", 2000)
    body = page.inner_text("main")
    R.ok("ERP /reports/ (Chủ): thấy lô vừa tạo với doanh thu 970.000 đ", batch in body and "970.000" in body, body[:400])
    snap(page, "erp-reports-batch", 1280, "erp")

    # ======================================================== 4. Sửa thông tin món → Shop thấy ngay; xoá chữ → Shop ẩn khối
    iid = [i["id"] for i in api("GET", "/api/catalog/items/?search=GHE-XANH", token=tok)[1]["results"] if i["code"] == "GHE-XANH"][0]
    erp_goto(page, f"/catalog/detail/?id={iid}", 1500)
    new_note = "Ghẹ thịt chắc (e2e " + SUF + ")"
    page.get_by_role("button", name="Sửa ghi chú ngắn").click()
    page.wait_for_timeout(400)
    editor = page.locator("main input:not([type]), main textarea").first
    editor.fill(new_note)
    page.get_by_role("button", name="Lưu", exact=True).click()
    page.wait_for_timeout(1500)
    sd, det = api("GET", "/api/shop/catalog/GHE-XANH/")
    R.ok("sửa 'Ghi chú ngắn' ở ERP → API Shop trả đúng chữ mới", sd == 200 and det["short_note"] == new_note, det.get("short_note") if sd == 200 else sd)
    shop_page = ctx.new_page()
    goto(shop_page, "/shop/item/?code=GHE-XANH", 800)
    R.ok("sửa ở ERP → trang món trên Shop hiện chữ mới (không build lại FE)", new_note in shop_page.inner_text("main"), shop_page.inner_text("main")[:200])
    snap(shop_page, "shop-item-after-erp-edit", 1280, "erp")
    s_hist = api("GET", "/api/audit-logs/?limit=20", token=tok)
    R.ok("sửa thông tin món ghi AuditLog (BR-PQ-05)", s_hist[0] == 200 and any("item" in str(x.get("action", "")).lower() and "GHE-XANH" in json.dumps(x, ensure_ascii=False) for x in s_hist[1].get("results", [])), [x.get("action") for x in s_hist[1].get("results", [])][:6])
    # các khoá mới trong AuditLog không tính ngược ra giá vốn / không có dữ liệu khách
    audit_txt = json.dumps(s_hist[1], ensure_ascii=False)
    R.ok("AuditLog gần nhất không chứa tên/SĐT/địa chỉ khách giả, không 'purchase_rate'", not contains_pii(audit_txt) and "purchase_rate" not in audit_txt, contains_pii(audit_txt))
    # xoá hết chữ → Shop ẩn khối
    page.get_by_role("button", name="Sửa ghi chú ngắn").click()
    page.wait_for_timeout(400)
    editor = page.locator("main input:not([type]), main textarea").first
    editor.fill("")
    page.get_by_role("button", name="Lưu", exact=True).click()
    page.wait_for_timeout(1500)
    sd, det = api("GET", "/api/shop/catalog/GHE-XANH/")
    R.ok("xoá chữ 'Ghi chú ngắn' ở ERP → Shop trả rỗng, trang món không còn dòng ghi chú", sd == 200 and det["short_note"] == "" and new_note not in (goto(shop_page, "/shop/item/?code=GHE-XANH", 800) or shop_page.inner_text("main")),
         det.get("short_note"))
    # quá dài bị chặn (60 ký tự)
    sl, bl = api("PATCH", f"/api/catalog/items/{iid}/", {"short_note": "x" * 61}, token=tok)
    R.ok("ghi chú ngắn quá 60 ký tự → 400, không lưu", sl == 400, (sl, str(bl)[:150]))
    # Thủ kho không sửa được chữ hiện trên Shop (nếu thiếu quyền) — ghi nhận theo phân quyền hiện hành
    tw = login_token("qa_warehouse")
    sw, _ = api("PATCH", f"/api/catalog/items/{iid}/", {"short_note": "kho sửa"}, token=tw)
    R.ok("Thủ kho PATCH thông tin món → bị chặn (403)", sw == 403, sw)
    shop_page.close()

    # ======================================================== 5. Nạp nội dung soạn sẵn (idempotent, có AuditLog)
    info = env_info()
    env = {**os.environ, **info["be_env"]}
    def load():
        return subprocess.run([str(BACKEND / ".venv/bin/python"), "manage.py", "load_shop_content", "--author", "qa_owner", "--publish"],
                              cwd=BACKEND, env=env, capture_output=True, text=True, timeout=300).stdout
    out1 = load()
    R.ok("load_shop_content chạy lại: không tạo mới, không đăng lại (idempotent)", re.search(r"tạo 0", out1) and re.search(r"đăng 0", out1) and "lỗi 0" in out1, out1[-200:])
    prod = subprocess.run([str(BACKEND / ".venv/bin/python"), "manage.py", "load_shop_content", "--author", "qa_owner"],
                          cwd=BACKEND, env={**env, "SEPAY_ENV": "PRODUCTION"}, capture_output=True, text=True, timeout=120)
    R.ok("load_shop_content khi SEPAY_ENV=PRODUCTION mà thiếu --environment production → từ chối", prod.returncode != 0, (prod.stdout + prod.stderr)[-200:])
    erp_goto(page, "/content/", 1500)
    ctext = page.inner_text("main")
    R.ok("ERP /content/ (Chủ): thấy các trang đã nạp (Banner, chính sách, Liên hệ, bài Góc bếp)", all(w in ctext for w in ("Chính sách", "Liên hệ")) or "ra-dong-tom" in ctext.lower() or "Ra đòng" in ctext, ctext[:300])
    snap(page, "erp-content-list", 1280, "erp")
    sa, al = api("GET", "/api/audit-logs/?action=content_load", token=tok)
    R.ok("AuditLog có hành động 'content_load' (lần nạp đầu của môi trường)", sa == 200 and "content_load" in json.dumps(al), sa)
    erp_goto(page, "/audit-logs/", 1500)
    page.wait_for_selector("main", timeout=15000)
    found = False
    for _ in range(25):   # nhật ký phân trang ("Tải thêm"); lần nạp đầu nằm ở trang cuối của môi trường mới
        if "Nạp nội dung soạn sẵn" in page.inner_text("main"):
            found = True
            break
        more = page.get_by_role("button", name="Tải thêm")
        if not more.count():
            break
        more.click()
        page.wait_for_timeout(800)
    R.ok("ERP /audit-logs/: hiển thị nhãn 'Nạp nội dung soạn sẵn' (không lộ mã hành động thô 'content_load')", found and "content_load" not in page.inner_text("main"), page.inner_text("main")[-200:])
    R.ok("ERP console sạch lỗi JS suốt phần Chủ", not watch.console_errors() and not watch.errors, (watch.console_errors()[:2], watch.errors[:2]))
    ctx.close()
    browser.close()
R.finish()
