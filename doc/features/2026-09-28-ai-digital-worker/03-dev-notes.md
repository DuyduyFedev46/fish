# Ghi chú phát triển — AI của tôi: nhân viên số, lệnh tự sinh từ API, hướng dẫn theo chứng từ

## Mốc trước phase P2 (Baseline)
- Ngày ghi nhận: 2026-09-28 22:24 (ngay sau khi P1 XONG trên main)
- Nhánh: `main`
- Số test backend gốc: **723 test** (`Ran 723 tests in 68.393s. OK. No changes detected.`)
- Bảng First Load JS của `erp-console` (`npm run build`):
  ```
  Route (app)                              Size     First Load JS
  ┌ ○ /                                    2.93 kB        94.7 kB
  ├ ○ /_not-found                          138 B          87.7 kB
  ├ ○ /account                             4.32 kB        99.7 kB
  ├ ○ /audit-logs                          6.57 kB        98.4 kB
  ├ ○ /catalog                             19.7 kB         115 kB
  ├ ○ /deliveries                          2.87 kB        94.7 kB
  ├ ○ /inventory                           3.37 kB         108 kB
  ├ ○ /login                               4.27 kB        96.1 kB
  ├ ○ /my-deliveries                       2.87 kB        94.7 kB
  ├ ○ /no-role                             3.26 kB        95.1 kB
  ├ ○ /orders                              3.12 kB         127 kB
  ├ ○ /orders/payments                     6.38 kB         130 kB
  ├ ○ /orders/refunds                      3.97 kB         120 kB
  ├ ○ /overview                            4.17 kB         108 kB
  ├ ○ /purchasing                          2.87 kB        94.7 kB
  ├ ○ /reports                             2.87 kB        94.7 kB
  ├ ○ /set-password                        4.71 kB        96.5 kB
  ├ ○ /staff                               12.1 kB         116 kB
  └ ○ /stocktake                           2.87 kB        94.7 kB
  + First Load JS shared by all            87.6 kB
    ├ chunks/117-a2fb4074d228e846.js       31.9 kB
    ├ chunks/fd9d1056-e8e54aff6d870cc8.js  53.6 kB
    └ other shared chunks (total)          2.08 kB
  ```

## Lô 0: Spike (DW-01 BE + DW-02 FE)
- Trạng thái: HOÀN THÀNH (ĐẠT tất cả tiêu chí)
- Nhánh thực hiện: `main`

### Kết quả DW-01 (Spike BE):
- Code: `backend/spikes/dw01/` (`discovery.py`, `schema.py`, `dispatch.py`, `spike_test_dw01.py`).
- Báo cáo: `research/02-spike-be.md`
- Chỉ mục: `research/dw01-index.json` (114 lệnh, không có PII/giá vốn).
- Lệnh kiểm chứng:
  1. `cd backend && .venv/bin/python manage.py test spikes.dw01 --pattern="spike_*.py" -v 2`: `Ran 4 tests in 0.420s. OK`
  2. `cd backend && .venv/bin/python manage.py test`: `Ran 723 tests in 85.599s. OK` (giữ nguyên mốc 723 gốc).
  3. `git diff --stat origin/main -- backend/apps backend/config`: Rỗng hoàn toàn.

### Kết quả DW-02 (Spike FE):
- Code: `erp-console/spikes/dw02/` (`recall.mjs`, `Harness.tsx`, `index.json`), `erp-console/app/ai-spike/page.tsx`.
- Dữ liệu thử nghiệm: `research/cau-mau-50.json` (50 câu tiếng Việt chuẩn domain Cá Về).
- Báo cáo: `research/03-spike-fe.md`
- Lệnh kiểm chứng:
  1. `node erp-console/spikes/dw02/recall.mjs`:
     - Recall@1: 86.0% (43/50)
     - Recall@3: 90.0% (45/50)
     - Recall@5: 98.0% (49/50) >= 95% (ĐẠT tiêu chí DW-02-AC3)
     - Margin trung bình: 0.217
  2. `cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build`: Compile sạch, First Load JS shared by all giữ nguyên 87.6 kB, không tăng kích thước các route cũ.
- Máy tham chiếu Android/Windows >= 8GB: Ghi nhận "CHỜ DUY ĐO" trong `03-spike-fe.md` theo chỉ đạo của Duy.

