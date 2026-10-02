# Smoke trên BE THẬT cho 3 lỗi QA trả về ở Lô 16 (Nội dung, ED-35/ED-36): B16-1 gỡ bài mất thông tin, B16-2 mở bài là đã "sửa", B16-3 nháp cũ đè bản mới.
# Dựng môi trường (mọi thứ nằm ngoài repo, SQLite tạm, dữ liệu giả):
#   cd backend && export DJANGO_DEBUG=1 DATABASE_URL=sqlite:////đường/dẫn/tạm.sqlite3 CORS_ALLOWED_ORIGINS=http://127.0.0.1:3661
#   python manage.py migrate && python manage.py bootstrap_masterdata && python manage.py seed_demo && python manage.py collectstatic --noinput
#   tạo 2 người dùng: loc (Group owner) và ql1 (Group manager), mật khẩu Songbien2026 (python manage.py shell)
#   python manage.py runserver 127.0.0.1:8661 --noreload
#   cd erp-console && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8661 npm run build && cp -R out /đường/dẫn/riêng
#   (cd /đường/dẫn/riêng && python3 -m http.server 3661 --bind 127.0.0.1 &)
#   BASE=http://127.0.0.1:3661 REAL_API=http://127.0.0.1:8661 SHOTS=<thư mục ảnh> python3 -u e2e/ed_batch16_real.py     # chỉ tắt đúng 2 cổng 8661 và 3661
# Mỗi lần chạy tạo bài mới có hậu tố thời gian nên chạy lại được. Bài mẫu chỉ có chữ giả, không có dữ liệu khách.
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:3661")
API = os.environ.get("REAL_API", "http://127.0.0.1:8661")
SHOTS = os.environ.get("SHOTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shots", "lo16"))
os.makedirs(SHOTS, exist_ok=True)
expect.set_options(timeout=15000)
R = []
STAMP = str(int(time.time()))[-6:]
PASSWORD = "Songbien2026"


def ok(n, c, e=""):
    R.append((n, bool(c), e))
    print("PASS" if c else "FAIL", n, "" if c else str(e)[:300], flush=True)


def call(method, path, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={"Content-Type": "application/json", "Authorization": "Token " + token})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode()[:300]


def token_of(user):
    req = urllib.request.Request(API + "/api/auth/token/", data=json.dumps({"username": user, "password": PASSWORD}).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["token"]


# Thân bài "chưa chuẩn hoá": chữ liền kề bị tách, có đoạn trống.
RAW_BODY = {
    "type": "doc",
    "blocks": [
        {"type": "heading", "level": 2, "text": "Cách chọn cá"},
        {"type": "paragraph", "children": [{"text": "Chọn cá "}, {"text": "thu tươi"}, {"text": " có mắt trong."}]},
        {"type": "paragraph", "children": []},
    ],
}


def make_entry(token, title, slug, body=RAW_BODY):
    st, d = call("POST", "/api/content/entries/", token, {"kind": "post", "title": title, "slug": slug, "category": None, "excerpt": "Tóm tắt thử.", "seo_title": "", "seo_description": "", "cover_image": None, "body": body})
    assert st in (200, 201), (st, d)
    return d


def make_png(w=64, h=64):
    """PNG xanh đơn sắc dựng bằng zlib (không cần thư viện ảnh); BE thật kiểm kích thước tối thiểu."""
    import struct
    import zlib

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + b"\x40\x80\xc0" * w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


PNG = make_png()


def upload_image(token, entry_id, alt):
    """Tải ảnh bịa (PNG 1x1) lên bài, để bài đủ điều kiện đăng (cần ảnh bìa có mô tả)."""
    boundary = "----b16" + STAMP
    parts = []
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="alt"\r\n\r\n{alt}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + PNG + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(API + f"/api/content/entries/{entry_id}/images/", data=b"".join(parts), method="POST", headers={"Content-Type": "multipart/form-data; boundary=" + boundary, "Authorization": "Token " + token})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def session(b, user, width=1280):
    ctx = b.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    errs = []
    page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text and "Failed to fetch RSC payload" not in m.text and errs.append(m.text))
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE + "/login/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("Tài khoản").fill(user)
    page.get_by_label("Mật khẩu").fill(PASSWORD)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_selector(".nav a", state="attached")
    return ctx, page, errs


def open_entry(page, eid):
    page.goto(f"{BASE}/content/edit/?id={eid}")
    page.wait_for_load_state("networkidle")
    expect(page.locator(".ProseMirror").first).to_be_visible()
    page.wait_for_timeout(1800)


def main_text(page):
    return page.locator("main").inner_text()


def draft_keys(page):
    return page.evaluate("() => Object.keys(localStorage).filter(k => k.startsWith('cave_erp_draft:'))")


def is_guarded(page):
    return page.evaluate("() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; }")


def title_input(page):
    return page.get_by_label("Tiêu đề", exact=False).first


def dialog(page):
    return page.locator("[role=dialog]").first


def main():
    loc = token_of("loc")
    manager_token = token_of("ql1")
    a = make_entry(loc, f"Bài thử B16 A {STAMP}", f"bai-thu-b16-a-{STAMP}")
    b_ = make_entry(loc, f"Bài thử B16 B {STAMP}", f"bai-thu-b16-b-{STAMP}", {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Nội dung bài thử để đăng."}]}]})
    st, cat = call("POST", "/api/content/categories/", loc, {"name": f"Chuyên mục thử {STAMP}"})
    cat_id = cat["id"] if st in (200, 201) else None
    ist, img = upload_image(loc, b_["id"], "Ảnh minh hoạ cá thu")
    ok("BE thật: dựng chuyên mục và ảnh bìa giả cho bài đăng", cat_id is not None and ist in (200, 201), (st, cat, ist, img))
    st, b_ = call("PATCH", f"/api/content/entries/{b_['id']}/", loc, {"row_version": b_["row_version"], "category": cat_id, "cover_image": img["id"]})
    st, pub = call("POST", f"/api/content/entries/{b_['id']}/publish/", loc, {"row_version": b_["row_version"], "checklist_confirmed": True, "acknowledge_warnings": True})
    ok("BE thật: dựng sẵn bài đã đăng để thử gỡ", st == 200, (st, pub))

    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx, page, errs = session(br, "loc")

        # ---- B16-2: chỉ mở bài (thân bài BE trả chưa chuẩn hoá), không gõ gì.
        open_entry(page, a["id"])
        t = main_text(page)
        ok("B16-2 (BE thật): chỉ mở bài thì không chặn rời trang", not is_guarded(page))
        ok("B16-2 (BE thật): chỉ mở bài thì không ghi bản nháp nào vào máy", draft_keys(page) == [], str(draft_keys(page)))
        ok("B16-2 (BE thật): không có dòng 'đã khôi phục bản nháp', không báo 'Chưa lưu'", "Đã khôi phục bản nháp" not in t and "Chưa lưu" not in t, t[:300])
        ok("B16-2 (BE thật): đủ chữ trong ô soạn", "Chọn cá thu tươi có mắt trong." in page.locator(".ProseMirror").first.inner_text(), page.locator(".ProseMirror").first.inner_text())
        page.goto(BASE + "/content/")
        page.wait_for_load_state("networkidle")
        open_entry(page, a["id"])
        ok("B16-2 (BE thật): mở lại lần hai vẫn sạch", "Đã khôi phục bản nháp" not in main_text(page) and draft_keys(page) == [] and not is_guarded(page))
        page.screenshot(path=f"{SHOTS}/lo16-real2-1-mo-bai-sach.png", full_page=True)

        # ---- B16-3: gõ dở, rời đi, người khác sửa qua API, mở lại.
        title_input(page).fill(f"Bản của tôi gõ dở {STAMP}")
        page.wait_for_timeout(1500)
        ok("B16-3 (BE thật): gõ dở thì có 1 bản nháp trên máy", draft_keys(page) == [f"cave_erp_draft:content_entry_{a['id']}"], str(draft_keys(page)))
        open_entry(page, a["id"])
        ok("B16-3 (BE thật): máy chủ chưa đổi thì khôi phục như cũ", title_input(page).input_value() == f"Bản của tôi gõ dở {STAMP}" and "Đã khôi phục bản nháp" in main_text(page))

        st, cur = call("GET", f"/api/content/entries/{a['id']}/", manager_token)
        st2, upd = call("PATCH", f"/api/content/entries/{a['id']}/", manager_token, {"row_version": cur["row_version"], "title": f"Bản của ql1 {STAMP}"})
        ok("B16-3 (BE thật): người khác (ql1) sửa bài qua API được", st == 200 and st2 == 200, (st, st2, upd))
        open_entry(page, a["id"])
        t = main_text(page)
        ok("B16-3 (BE thật): máy chủ đã đổi thì không tự đè, tiêu đề là bản của ql1", title_input(page).input_value() == f"Bản của ql1 {STAMP}", title_input(page).input_value())
        ok("B16-3 (BE thật): có cảnh báo + 2 lựa chọn, không có dòng 'đã khôi phục'", "Bài đã được người khác sửa" in t and page.get_by_role("button", name="Giữ bản trên máy").count() == 1 and page.get_by_role("button", name="Dùng bản mới nhất").count() == 1 and "Đã khôi phục bản nháp" not in t, t[:300])
        ok("B16-3 (BE thật): chưa chọn thì chưa bị coi là đã sửa", not is_guarded(page))
        page.screenshot(path=f"{SHOTS}/lo16-real2-2-nhap-cu-canh-bao.png", full_page=True)
        page.get_by_role("button", name="Giữ bản trên máy").click()
        page.get_by_role("button", name="Lưu nháp").first.click()
        page.wait_for_timeout(1500)
        t = main_text(page)
        ok("B16-3 (BE thật): lưu bản giữ lại thì BE báo 409, màn hiện xung đột, không đè bản của ql1", "vừa được người khác sửa" in t and "Tải lại" in t, t[:400])
        st, cur = call("GET", f"/api/content/entries/{a['id']}/", loc)
        ok("B16-3 (BE thật): bản trên máy chủ vẫn là của ql1", cur["title"] == f"Bản của ql1 {STAMP}", cur["title"])
        page.screenshot(path=f"{SHOTS}/lo16-real2-3-nhap-cu-xung-dot.png", full_page=True)
        page.get_by_role("button", name="Tải lại").first.click()
        if dialog(page).count():
            dialog(page).get_by_role("button", name="Tải lại").click()
        page.wait_for_timeout(1200)
        ok("B16-3 (BE thật): tải lại thì về bản của ql1, nháp trên máy được xoá", title_input(page).input_value() == f"Bản của ql1 {STAMP}" and draft_keys(page) == [], str(draft_keys(page)))

        title_input(page).fill(f"Bản gõ dở thứ hai {STAMP}")
        page.wait_for_timeout(1500)
        st, cur = call("GET", f"/api/content/entries/{a['id']}/", manager_token)
        call("PATCH", f"/api/content/entries/{a['id']}/", manager_token, {"row_version": cur["row_version"], "title": f"Bản của ql1 lần hai {STAMP}"})
        open_entry(page, a["id"])
        page.get_by_role("button", name="Dùng bản mới nhất").click()
        ok("B16-3 (BE thật): 'Dùng bản mới nhất' giữ bản máy chủ, xoá nháp, hết cảnh báo", title_input(page).input_value() == f"Bản của ql1 lần hai {STAMP}" and draft_keys(page) == [] and "Bài đã được người khác sửa" not in main_text(page) and not is_guarded(page))

        # ---- B16-1: gỡ bài rồi không tải lại trang.
        open_entry(page, b_["id"])
        ok("B16-1 (BE thật): bài đã đăng có đường dẫn bị khoá từ đầu", page.get_by_label("Đường dẫn", exact=True).first.is_disabled())
        page.get_by_role("button", name=re.compile("Thêm|Khác|Thao tác")).last.click()
        page.get_by_role("menuitem").filter(has_text="Gỡ bài").first.click()
        dialog(page).wait_for()
        dialog(page).get_by_role("combobox").select_option(label="Hết mùa vụ")
        dialog(page).get_by_role("button", name="Gỡ bài").click()
        page.wait_for_function("() => !document.querySelector('[role=dialog]')")
        page.wait_for_timeout(800)
        t = main_text(page)
        ok("B16-1 (BE thật): gỡ xong (không tải lại) còn biểu ngữ 'Lý do: Hết mùa vụ'", "Bài đã gỡ khỏi website. Lý do: Hết mùa vụ" in t, t[:400])
        ok("B16-1 (BE thật): đường dẫn vẫn bị khoá, vẫn có chú thích", page.get_by_label("Đường dẫn", exact=True).first.is_disabled() and "không đổi được đường dẫn" in t)
        ok("B16-1 (BE thật): không có chữ undefined / null / '#undefined'", "undefined" not in t and "null" not in t, t[:400])
        title_input(page).fill(f"Bài thử B16 B (sửa) {STAMP}")
        page.get_by_role("button", name="Lưu nháp").first.click()
        page.wait_for_timeout(1500)
        t = main_text(page)
        ok("B16-1 (BE thật): sau khi gỡ, sửa và lưu được; không báo đường dẫn trùng, không báo xung đột", "Đường dẫn này đã có bài khác dùng" not in t and "vừa được người khác sửa" not in t, t[:400])
        ok("B16-1 (BE thật): lưu xong vẫn còn lý do gỡ và trạng thái Đã gỡ", "Lý do: Hết mùa vụ" in t and "Đã gỡ" in t, t[:300])
        st, cur = call("GET", f"/api/content/entries/{b_['id']}/", loc)
        ok("B16-1 (BE thật): BE ghi nhận bài đã gỡ, lý do out_of_season, tiêu đề mới đã lưu", cur["status"] == "unpublished" and cur["return_reason"] == "out_of_season" and cur["title"] == f"Bài thử B16 B (sửa) {STAMP}", (cur["status"], cur["return_reason"]))
        page.screenshot(path=f"{SHOTS}/lo16-real2-4-go-bai-giu-lydo.png", full_page=True)
        ok("BE thật: console không có lỗi / pageerror", errs == [], str(errs[:3]))
        ctx.close()
        br.close()

    failed = [r for r in R if not r[1]]
    print(f"\n{len(R) - len(failed)}/{len(R)} PASS")
    for r in failed:
        print("FAIL:", r[0], r[2])
    sys.exit(1 if failed else 0)


main()
