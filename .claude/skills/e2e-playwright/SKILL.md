---
name: e2e-playwright
description: Kiểm thử end-to-end giao diện Cá Về bằng Playwright Python — tự bật backend Django + frontend Next.js (hoặc mock), đi luồng Shop như khách thật, chụp màn hình, bắt lỗi console. Dùng ở bước QA khi story có thay đổi giao diện, hoặc khi cần xác minh một luồng trên trình duyệt.
---

# E2E với Playwright (QA)

Nguồn tham khảo: `webapp-testing` (anthropics/skills), `playwright` + `qa` agent của
ship-mate (wshobson/agents). Playwright Python đã cài sẵn trên máy.

## Chọn cách chạy

```
Story chỉ đụng FE, API đã có mock?  → chạy FE mock:  NEXT_PUBLIC_USE_MOCK=1 npm run dev (:3000)
Story đụng cả BE                     → chạy thật:     Django :8000 (SQLite dev) + FE trỏ NEXT_PUBLIC_API_BASE=http://localhost:8000
```

Bật server nền, đợi cổng mở, chạy script, **luôn tắt server khi xong**:
```bash
cd backend && .venv/bin/python manage.py runserver 8000 &
cd frontend && NEXT_PUBLIC_API_BASE=http://localhost:8000 NEXT_PUBLIC_USE_MOCK=0 npm run dev -- -p 3000 &
# đợi: until curl -s localhost:3000 >/dev/null; do sleep 1; done
```
Cần dữ liệu → `manage.py seed_demo` (idempotent) trên DB dev. **Không** chạy E2E vào
production (`*.run.app`, `*.web.app`) — trừ smoke test chỉ đọc khi Duy yêu cầu.

## Viết script

Đặt script tạm trong scratchpad; script E2E đáng giữ lại → `frontend/e2e/<tên>.py`.

```python
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})   # mobile-first
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto("http://localhost:3000/shop/")
    page.wait_for_load_state("networkidle")          # BẮT BUỘC trước khi soi DOM
    page.screenshot(path="shot-01-catalog.png", full_page=True)
    page.get_by_role("button", name="Thêm vào giỏ").first.click()
    expect(page.get_by_text("Giỏ hàng")).to_be_visible()
    assert not errors, errors
    browser.close()
```

- **Trinh sát rồi mới hành động**: chụp ảnh / `page.content()` để tìm selector thật.
- Ưu tiên selector theo vai trò & chữ hiển thị (`get_by_role`, `get_by_text`) — đó cũng là
  cách kiểm luôn nhãn tiếng Việt.
- Mỗi AC giao diện ↔ một bước có `expect(...)` + ảnh chụp làm bằng chứng.

## Luôn thử thêm (ngoài AC)

- Màn hình 390px (mobile) và 1280px.
- Trạng thái rỗng / lỗi mạng (tắt backend) / đang tải.
- Bấm đúp nút đặt hàng → chỉ tạo 1 đơn.
- Không có giá vốn, lãi lỗ, hay dữ liệu nội bộ nào trong HTML Shop (`page.content()`).
- Console không có lỗi đỏ.

## Đặt tên (P8b, Duy chốt 01/10)

Định danh trong code (hàm, biến, class, module, thư mục, file, test, script, route API, khoá JSON, biến env, Group,
`data-testid`, id lệnh AI, khoá lưu trình duyệt) là **tiếng Anh chuẩn, không viết tắt tiếng Việt**. Chữ hiển thị cho người
dùng, comment, docstring và tài liệu vẫn tiếng Việt. Viết tắt chỉ dùng khi là chuẩn quốc tế: `VN`, `VND`, `pnl`, `id`, `url`.
Không đưa mã lô giao việc (`lo7`, `l8`, `p8_lo5`) vào tên; mã lô/story ghi trong docstring.

| Khái niệm | Dùng | Không dùng |
|---|---|---|
| Vai (Group) | `owner` `manager` `warehouse_staff` `delivery_staff` `customer_service` | `chu` `quan_ly` `nv_kho` `nv_giao` `cskh` |
| Người giao trên một phiếu | `courier` | `nv_giao` |
| Việc gọi xác nhận đơn | `confirmation` | `cskh` (module, route, khoá JSON, env) |
| Nhập lô | `receive_batches`, `ReceiveBatches*` | `nhap_lo`, `NhapLo*` |
| Lệnh AI: nhóm / mức nhạy cảm | `purchasing` `sales` `customer_service` / `high` `medium` `low` | `thu_mua` `ban_hang` / `cao` `trung_binh` `thap` |
| Giờ Việt Nam | `VN_TIME_ZONE`, `todayInVietnam()`, `today_in_vietnam()` | `VN_TZ`, `todayVn`, `vn_today` |
| Bản rà soát QA / bổ sung | `review_*` / `extra`, `followup` | `ra_soat_*` / `bosung` |

Giữ nguyên (không đổi): migration đã chạy, `AuditLog.action` đã ghi, dòng phiên bản cấu hình AI cũ, URL công khai Shop
`/bai-viet/` `/trang/` `?chuyen-muc=`, dữ liệu demo (username `kho1`, `chu_vua`..., slug, mã hàng), keyword AI có dấu, chuỗi `cangca`.
Bảng đầy đủ: `doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md` mục 1.

**Kiểm bằng máy** (Python 3 stdlib, chạy từ gốc repo, dưới 10 giây, không cần venv):
`python3 scripts/check_naming.py`. Exit 1 khi file MỚI có định danh tiếng Việt, hoặc số vi phạm của một file TĂNG so với
`scripts/naming_baseline.json`; in file, dòng, token. Script không xét chuỗi hiển thị, comment, docstring. Danh sách từ chặn và
allowlist ở `scripts/naming_blocklist.txt`. Chạy lệnh này trước khi báo xong mọi việc có sửa code.

**Kịch bản e2e**: tên file và hàm đặt tiếng Anh theo hành vi (`test_customer_places_order.py`, `check_cash_on_delivery_flow`),
không đặt mã lô (`lo7`, `l8`, `p8_lo5`) vào tên. Bản rà soát QA do kịch bản sinh ra dùng tiền tố `review_*` (không dùng `ra_soat_*`).
Dữ liệu demo (username `kho1`, `chu_vua`...) là dữ liệu, không phải định danh, nên giữ. `data-testid` mà kịch bản bám là tiếng Anh
(vd `confirmation-policy-notice`); đổi `data-testid` thì đổi cùng lúc ở FE và kịch bản. Chạy `python3 scripts/check_naming.py`
sau khi thêm hoặc đổi tên kịch bản; script quét cả thư mục e2e (định danh và tên file).
