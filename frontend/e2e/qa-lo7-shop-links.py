"""QA P8 Lô 7 (do QA viết) — Shop bản build THẬT: bài có link `\\evil.example`, `javascript:` ... không thể đưa người đọc ra ngoài origin.
Chạy: QA_BASE=http://127.0.0.1:3108 python3 qa_lo7_shop_links.py
Dữ liệu giả; mọi request tới evil.example bị chặn và đếm."""
import json, os, sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

BASE = os.environ.get("QA_BASE", "http://127.0.0.1:3108")
API = "http://localhost:8199"
CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"}
BAD = ["\\\\evil.example", "\\\\\\\\evil.example/x", "/\\evil.example", "//evil.example", "///evil.example",
       "javascript:window.__x=1", " javascript:window.__x=1", "JaVaScRiPt:window.__x=1", "java\tscript:window.__x=1",
       "data:text/html,<script>window.__x=1</script>", "vbscript:msgbox(1)", "file:///etc/passwd", "\u0001javascript:window.__x=1",
       "/ok path", "x" * 2100]
EXT = ["https://evil.example/\u202egpj.exe", "https:\\\\evil.example"]  # https tuyệt đối: hợp lệ theo thiết kế, KHÔNG bấm
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print(("[PASS] " if cond else "[FAIL] ") + name + ("" if cond else f"  <{extra}>"))

def entry(blocks):
    return {"kind": "post", "slug": "bai-thu", "title": "Bài thử QA", "seo_title": "", "description": "", "excerpt": "",
            "category": None, "cover_image": None, "body": {"type": "doc", "blocks": blocks},
            "published_at": "2026-09-28T00:00:00Z", "updated_at": "2026-09-28T00:00:00Z", "version": 1,
            "effective_from": None, "author": "Cá Về"}

with sync_playwright() as p:
    b = p.chromium.launch()
    for vp in ((1280, 800), (390, 800)):
        ctx = b.new_context(viewport={"width": vp[0], "height": vp[1]})
        page = ctx.new_page()
        evil, dialogs, errs, popups = [], [], [], []
        ctx.route(lambda u: urlparse(u).hostname == "evil.example", lambda r: (evil.append(r.request.url), r.abort()))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.on("pageerror", lambda e: errs.append(str(e)))
        ctx.on("page", lambda pg: popups.append(pg.url))
        blocks = [{"type": "paragraph", "children": [{"text": f"LINK{i}", "href": h}]} for i, h in enumerate(BAD)]
        blocks.append({"type": "paragraph", "children": [{"text": "LINKOK", "href": "https://evil.example/hop-le"}]})
        for j, h in enumerate(EXT):
            blocks.append({"type": "paragraph", "children": [{"text": f"EXT{j}", "href": h}]})
        def api(route):
            path = urlparse(route.request.url).path
            if route.request.method == "OPTIONS":
                return route.fulfill(status=204, headers=CORS)
            if path.startswith("/api/public/content/entries/") and path != "/api/public/content/entries/":
                return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps(entry(blocks)))
            if path == "/api/public/site-info/":
                return route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps({"seller_complete": False}))
            return route.fulfill(status=404, content_type="application/json", headers=CORS, body='{"detail":"Not found."}')
        page.route(f"{API}/**", api)
        page.goto(f"{BASE}/blog/?slug=bai-thu"); page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)
        tag = f"[{vp[0]}px]"
        check(f"{tag} bài hiển thị", page.locator("article").count() == 1)
        origin = urlparse(BASE).netloc
        anchors = page.eval_on_selector_all("article a", "els => els.map(a => ({t: a.textContent, h: a.getAttribute('href'), abs: a.href, tg: a.target, rel: a.rel}))")
        bad_anchors = [a for a in anchors if a["t"].startswith("LINK") and a["t"] != "LINKOK"]
        check(f"{tag} không link độc nào thành <a> (15 payload)", len(bad_anchors) == 0, str(bad_anchors)[:300])
        ext = [a for a in anchors if a["t"].startswith("EXT")]
        check(f"{tag} https tuyệt đối lạ (RTL-override / https:\\\\) nếu là link thì phải target=_blank + rel đủ",
              all(a["tg"] == "_blank" and all(x in a["rel"] for x in ("nofollow", "noopener", "noreferrer")) for a in ext), str(ext))
        okc = [a for a in anchors if a["t"] == "LINKOK"]
        check(f"{tag} link https hợp lệ có mặt với target=_blank + rel nofollow noopener noreferrer",
              len(okc) == 1 and okc[0]["tg"] == "_blank" and all(x in okc[0]["rel"] for x in ("nofollow", "noopener", "noreferrer")), str(okc))
        # bấm từng chữ LINKi
        for i in range(len(BAD)):
            loc = page.get_by_text(f"LINK{i}", exact=True)
            if loc.count():
                loc.first.click(force=True)
        page.wait_for_timeout(300)
        check(f"{tag} sau khi bấm hết: vẫn ở origin gốc", urlparse(page.url).netloc == origin, page.url)
        check(f"{tag} không request nào tới evil.example", not evil, str(evil))
        check(f"{tag} không dialog, không __x, không pageerror, không tab mới",
              not dialogs and page.evaluate("window.__x === undefined") and not errs and not popups, f"{dialogs} {errs} {popups}")
        # bàn phím: Tab qua các link còn lại rồi Enter
        page.keyboard.press("Tab"); page.keyboard.press("Enter")
        page.keyboard.press("Tab"); page.keyboard.press("Enter")
        # Tab/Enter chỉ có thể tới link ngoài HỢP LỆ (mở tab mới, có rel); trang gốc vẫn ở origin, không dialog
        check(f"{tag} Tab/Enter: trang gốc vẫn ở origin, không dialog", urlparse(page.url).netloc == origin and not dialogs)
        ctx.close()
    b.close()
print(f"Tổng {len(results)} ca, {results.count(False)} FAIL"); sys.exit(1 if False in results else 0)
