"""
P8 Lô 7 — SR-24 F9: bài mẫu XSS `xss-mau` (chỉ có ở bản build MOCK) hiển thị an toàn ở Shop.
Không có dialog, không <script>/on*= chèn vào, không href javascript:/data:/vbscript:/`//`/`\\`,
link ngoài có target=_blank + rel nofollow noopener noreferrer, ảnh có srcset/sizes.

    cd frontend && NEXT_PUBLIC_USE_MOCK=1 npm run build
    cp -R out/. <scratch>/mock/ ; (cd <scratch>/mock && python3 -m http.server 3107 --bind 127.0.0.1 &)
    QA_BASE=http://127.0.0.1:3107 QA_SHOT_DIR=doc/features/2026-09-30-sua-loi-review/qa-lo7 python3 e2e/qa-lo7-shop-xss.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("QA_BASE", "http://127.0.0.1:3107")
SHOT_DIR = os.environ.get("QA_SHOT_DIR", "/tmp")
failures, total = [], 0


def check(label, cond, detail=""):
    global total
    total += 1
    ok = bool(cond)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f"  <{detail}>" if (detail and not ok) else ""))
    if not ok:
        failures.append(label)


BAD_TEXT = ["LINK-JS", "LINK-JS-HOA", "LINK-JS-TAB", "LINK-DATA", "LINK-VB", "LINK-GIAO-THUC-TUONG-DOI",
            "LINK-GACH-NGUOC", "LINK-GACH-NGUOC-DAU", "LINK-FILE", "MUC-LINK-JS"]


def run(b, width, height, tag):
    ctx = b.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    dialogs, errs = [], []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(f"{BASE}/bai-viet/?slug=xss-mau")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(600)

    art = page.locator("article")
    check(f"F9 [{tag}] bài mẫu hiển thị (có <article>)", art.count() >= 1)
    check(f"F9 [{tag}] không có dialog (alert/confirm/prompt) nào bật lên", not dialogs, str(dialogs))
    check(f"F9 [{tag}] window.__xss không được đặt (không payload nào chạy)", page.evaluate("typeof window.__xss") == "undefined")
    check(f"F9 [{tag}] không pageerror", not errs, str(errs))
    check(f"F9 [{tag}] không có <script> nào trong <article>", page.locator("article script").count() == 0)
    inj = page.evaluate("""() => Array.from(document.querySelectorAll('body *')).filter(el =>
        Array.from(el.attributes).some(a => /^on/i.test(a.name))).length""")
    check(f"F9 [{tag}] không phần tử nào trong body có thuộc tính on*= (onerror/onload...)", inj == 0, str(inj))
    check(f"F9 [{tag}] không có <iframe>/<svg onload>/<img src=x> chèn từ payload",
          page.locator("article iframe").count() == 0 and page.locator('article img[src="x"]').count() == 0 and page.locator("article svg").count() == 0)
    text = page.inner_text("article")
    check(f"F9 [{tag}] payload hiện dưới dạng CHỮ THƯỜNG (escape), không thành thẻ",
          "<script>window.__xss=1</script>" in text and "<iframe" in text)

    hrefs = page.evaluate("Array.from(document.querySelectorAll('article a')).map(a => a.getAttribute('href'))")
    bad = [h for h in hrefs if h is None or h.strip().lower().startswith(("javascript:", "data:", "vbscript:", "file:", "//", "/\\", "\\"))
           or any(ord(c) <= 32 for c in h.strip())]
    check(f"F9 [{tag}] không link nào trong bài là javascript:/data:/vbscript:/file:/`//`/`\\`/có khoảng trắng", not bad, str(bad))
    for label in BAD_TEXT:
        n_link = page.locator("article a", has_text=label).count()
        # "LINK-JS" là tiền tố của "LINK-JS-HOA": so khớp chính xác bằng exact text
        exact = page.evaluate("""(t) => Array.from(document.querySelectorAll('article a')).filter(a => a.textContent.trim() === t).length""", label)
        in_text = label in text
        check(f"F9 [{tag}] {label}: hiện như chữ thường, KHÔNG phải link", in_text and exact == 0, f"link={exact} in_text={in_text}")

    ext = page.evaluate("""() => Array.from(document.querySelectorAll('article a')).filter(a => /^https?:/i.test(a.getAttribute('href')||''))
        .map(a => ({t: a.textContent.trim(), target: a.target, rel: a.rel}))""")
    names = {e["t"] for e in ext}
    check(f"F9 [{tag}] link ngoài hợp lệ (https + http) có mặt", {"LINK-NGOAI-OK", "LINK-NGOAI-HTTP-OK"} <= names, str(ext))
    check(f"F9 [{tag}] MỌI link ngoài có target=_blank và rel nofollow+noopener+noreferrer",
          ext and all(e["target"] == "_blank" and all(k in e["rel"].split() for k in ["nofollow", "noopener", "noreferrer"]) for e in ext), str(ext))
    check(f"F9 [{tag}] link nội bộ /shop/, mailto, tel còn dùng được và KHÔNG mở tab mới",
          all(page.evaluate("""(t) => { const a = Array.from(document.querySelectorAll('article a')).find(x => x.textContent.trim() === t);
              return !!a && a.target !== '_blank'; }""", t) for t in ["LINK-NOI-BO-OK", "LINK-MAIL-OK", "LINK-TEL-OK"]))

    img = page.locator("article img").first
    srcset = img.get_attribute("srcset") or ""
    sizes = img.get_attribute("sizes") or ""
    check(f"F9/F8 [{tag}] ảnh có srcset 480w/960w/1600w và sizes", all(w in srcset for w in ["480w", "960w", "1600w"]) and sizes != "", f"{srcset} | {sizes}")
    check(f"F9 [{tag}] alt/chú thích độc hiện dưới dạng chữ, không thành thẻ", "onerror" in page.inner_text("figcaption") if page.locator("figcaption").count() else True)
    check(f"F9 [{tag}] không cuộn ngang", page.evaluate("document.documentElement.scrollWidth") <= page.evaluate("document.documentElement.clientWidth") + 1)
    page.screenshot(path=f"{SHOT_DIR}/lo7-f9-xss-{width}.png", full_page=True)

    # bấm thử link độc: không điều hướng, không dialog (không phải link nên chỉ là chữ)
    url0 = page.url
    for label in ["LINK-JS", "LINK-DATA", "LINK-GIAO-THUC-TUONG-DOI"]:
        page.locator("article p", has_text=label).first.click()
    page.wait_for_timeout(300)
    check(f"F9 [{tag}] bấm vào chữ các link độc: URL không đổi, không dialog", page.url == url0 and not dialogs, page.url)
    ctx.close()


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        run(b, 390, 844, "390px")
        run(b, 1280, 900, "1280px")
        b.close()
    print(f"\nTổng {total} ca, {len(failures)} FAIL")
    for f in failures:
        print(" -", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
