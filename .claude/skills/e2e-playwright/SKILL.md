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
