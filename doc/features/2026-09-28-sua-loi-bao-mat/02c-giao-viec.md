# Giao việc — Sửa lỗi bảo mật có sẵn (L-1, L-3, L-5, L-6, robots staging)
> Claude (Tech Lead) · 2026-09-28 · Trạng thái: **SẴN SÀNG CODE (Duy 28/09)**
> Người hiện thực: Gemini CLI / Antigravity theo `AGENTS.md`, lệnh `/lam-tinh-nang 2026-09-28-sua-loi-bao-mat`.
> Nhánh làm việc: `wip/autosave` (sau Lô 2 merge vào `main`, từ đó làm trên `main`).

## Điều kiện đầu vào
- `02-stories.md`: ĐÃ DUYỆT (Duy 28/09, luồng NHANH) · `02b-tech-design.md`: ĐÃ DUYỆT (Duy 28/09)
- **Làm đầu tiên**, trước mọi hồ sơ khác (Duy chốt 28/09). Không cần migration.
- Trước khi bắt đầu: `git pull` nhánh `wip/autosave`; chạy lệnh kiểm chứng BE một lần, ghi số test gốc vào `03-dev-notes.md`.
- Luồng NHANH: không có UI review. QA theo `04-qa-report.md`.

## Lô
| ☐/☑ | Lô | Story | BE / FE | Được sửa (thư mục/file) | Không được đụng | Commit |
|---|---|---|---|---|---|---|
| ☐ | 1 | S01 (L-3), S02 (L-6), S03 (L-5) | BE | `backend/apps/common/cost_keys.py` (mới), `backend/apps/common/throttling.py` (mới), `backend/apps/common/api.py` (chỉ `exception_handler`), `backend/apps/common/audit.py` (chỉ docstring), `backend/apps/accounts/audit/serializers.py`, `backend/apps/accounts/audit/api.py`, `backend/apps/sales/orders/shop_api.py`, `backend/apps/sales/payments/shop_api.py`, `backend/apps/accounts/auth/api.py` (chỉ `LoginTokenView`), `backend/config/settings.py` (khối `REST_FRAMEWORK` + `CAVEVE_THROTTLE_RATES`), test mới ở `backend/apps/common/tests/`, `backend/apps/accounts/audit/tests/`, `backend/apps/sales/orders/tests/`, `backend/apps/sales/payments/tests/`; `03-dev-notes.md` | mọi `migrations/`, `models/`, `record_audit` và dữ liệu `AuditLog`, `frontend/`, `erp-console/`, `adapter/`, `doc/decisions.md`, `02*.md`, test cũ (chỉ thêm, không sửa/xoá) | — |
| ☐ | 2 | S04 (L-1), S05 (robots) | BE + cấu hình hosting | `backend/apps/inventory/batches/services.py` (chỉ `close_batch` + hằng số đi kèm), `backend/apps/inventory/batches/tests/test_l1_close_batch.py` (mới), `backend/apps/inventory/batches/tests/test_services.py` (**chỉ** `test_publish_and_close_batch` thêm phiếu kiểm kê APPROVED), `frontend/firebase.staging.json`, `erp-console/firebase.staging.json`, `doc/ops/moi-truong.md` (1 dòng mục Deploy); `03-dev-notes.md` | `frontend/firebase.json`, `erp-console/firebase.json`, `*/app/layout.tsx`, `batches/api.py`, mọi `migrations/`, `models/`, service huỷ lô (L-2 là việc sau), `doc/decisions.md`, `02*.md` | — |

## Lô 1 — điều kiện xong
- Lệnh kiểm chứng (dán output tóm tắt vào `03-dev-notes.md`):
  ```bash
  cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
  cd backend && .venv/bin/python manage.py test apps.accounts.audit apps.common apps.sales
  grep -rn "throttle" backend/config/settings.py backend/apps/common/throttling.py   # có cấu hình
  ```
- Test bắt buộc (chi tiết ở `02b` §1–§3):
  - S01: `chu` / superuser / `quan_ly`+`view_costprice` thấy khoá giá vốn; `quan_ly` không thấy ở mọi độ sâu và JSON không chứa số giá vốn mẫu; `nv_kho`/`nv_giao` 403; khách 401; unit test `redact_cost` (dict lồng, list, không sửa input).
  - S02: 5 giá trị `phone_last4` sai định dạng → 400 giống nhau với mã có/không tồn tại; hai 404 cùng body; 200 có đúng 7 khoá, không tên/SĐT/địa chỉ; SĐT lưu có dấu cách/`+84`; checkout mã không có → 404 thông điệp chung.
  - S03: mỗi scope N+1 → 429 `{"detail","code":"throttled"}` + `Retry-After`; `shop_lookup_order` chặn từ nhiều IP; request bị chặn không tạo đơn/token; XFF giả đếm chung; back-office 50 lần không 429.
  - Toàn bộ suite cũ xanh, không sửa test cũ.
- QA APPROVED (`04-qa-report.md`, mục Lô 1): kiểm lại AC bằng token từng Group; thử Shop chạy mock (`NEXT_PUBLIC_USE_MOCK=1`) màn tra đơn vẫn hiện "không tìm thấy" khi 404.
- Commit: `Lô 1 sửa lỗi bảo mật: S01 lọc giá vốn nhật ký, S02 tra đơn, S03 throttle` → `git push origin wip/autosave`.

## Lô 2 — điều kiện xong
- Lệnh kiểm chứng:
  ```bash
  cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
  cd frontend && node -e 'JSON.parse(require("fs").readFileSync("firebase.staging.json","utf8"))' && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
  cd erp-console && node -e 'JSON.parse(require("fs").readFileSync("firebase.staging.json","utf8"))' && npx tsc --noEmit && npm run build
  git diff --exit-code frontend/firebase.json erp-console/firebase.json    # production không đổi
  ```
- Test bắt buộc (`02b` §4–§5):
  - S04: đơn `BOOKED`/`PAID`/`PROCESSING` chặn, `COMPLETED`/`CANCELLED`/`AUTO_CANCELLED` không chặn; `qty_reserved>0` và `ReturnToStock` DRAFT chặn; thiếu kiểm kê / chỉ phiếu nháp / có phiếu nháp → `BR-KK-05`; happy path `chu` qua API; chốt lần 2 → 400; lô đã chốt không được `allocate_fefo` chọn; `quan_ly`/`nv_kho`/`nv_giao` 403 và lô không đổi; khách 401; body lỗi không có giá vốn.
  - S05: JSON hợp lệ, header `X-Robots-Tag: noindex, nofollow` với `source: "**"` ở hai file staging, `Cache-Control` của Shop staging còn nguyên, `firebase.json` production không đổi.
  - Sửa test cũ có chủ đích duy nhất: `test_publish_and_close_batch` (ghi lý do BR-KK-05 trong `03-dev-notes.md`).
- QA APPROVED (`04-qa-report.md`, mục Lô 2).
- Commit: `Lô 2 sửa lỗi bảo mật: S04 chốt lô BR-LO-04/BR-KK-05, S05 noindex staging` → `git push origin wip/autosave`.
- **Bước cuối — merge vào `main`** (Duy chốt 28/09), chỉ khi Lô 1 và Lô 2 đều ☑:
  ```bash
  git fetch origin
  git checkout main && git pull --ff-only origin main
  git merge --no-ff wip/autosave -m "Merge wip/autosave: sửa lỗi bảo mật L-1/L-3/L-5/L-6 + noindex staging"
  cd backend && .venv/bin/python manage.py test          # chạy lại trên main sau merge, phải xanh
  git push origin main
  ```
  - Lưu ý (Tech Lead kiểm 28/09): máy hiện chưa có nhánh `main` cục bộ (`git checkout main` sẽ tạo nhánh theo dõi `origin/main`); `origin/main` có **4 commit chưa nằm trong** `wip/autosave` (wip đi trước 29 commit) → merge không fast-forward, có thể xung đột. Trước khi merge chạy `git log --oneline wip/autosave..origin/main` và dán vào `03-dev-notes.md`.
  - **Không** `--force`, không `rebase` lại lịch sử đã push, không xoá nhánh `wip/autosave`.
  - `git pull --ff-only` thất bại, merge có **xung đột**, hoặc test đỏ sau merge → `git merge --abort` (nếu đang merge), **dừng và báo Duy**, không tự giải xung đột.
  - Sau khi push `main` thành công: đánh dấu ☑ hai lô + mã commit ở bảng trên, đổi trạng thái hồ sơ thành **XONG**, báo Duy rằng từ nay làm trên `main`.
- **Không deploy.** Kiểm `curl -sI https://cangca-loc-staging.web.app/shop/ | grep -i x-robots-tag` (và ERP staging) là việc sau khi Duy cho deploy staging — ghi nhắc trong `03-dev-notes.md`.

## Điểm dừng hỏi Duy
- Contract/thiết kế không khớp code (vd vòng import không tránh được, test cũ khác ngoài `test_publish_and_close_batch` bị đỏ vì S04) → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô.
- Bất kỳ việc nào đụng tiền, giá vốn, phân quyền ngoài phạm vi story; cần thêm migration, `CACHES`/Redis, hay sửa FE.
- Xung đột khi merge `wip/autosave` → `main`.
