# QA — Xuất kho FEFO (F1, F2) · lần 1 · 2026-09-26

## Kết luận: **APPROVED** — 8 AC của F1 và F2-AC1 (hiển thị) đều đạt trên backend thật, unit test và e2e mock. Thứ tự xuất luôn theo hạn dùng sớm nhất (FEFO), không phụ thuộc ngày nhập; lô quá hạn không bao giờ được chọn dù thứ tự `status` chưa kịp job cập nhật; giữ chỗ không chọn lại lô lúc thanh toán; hoàn/huỷ trả đúng lô gốc. Không rò giá vốn, không còn chữ "FIFO" trên ERP.

## Tổng: 25 test BE mới (F1) + **26 phép kiểm trực tiếp trên backend thật** (đặt hàng thật qua Shop API, xem phân bổ lô, đối chiếu tồn) + hồi quy đầy đủ · ✅ tất cả · ⏸ 1 (F1-AC5 combo: không có mặt hàng combo trong `seed_demo`, không dựng được đơn thật để đặt combo trong lượt QA này — dựa vào unit test)

Môi trường: Django `runserver` 127.0.0.1:8000 trên SQLite tạm trong scratchpad (`migrate` → `bootstrap_masterdata` → `seed_demo`), dùng đúng dữ liệu demo có cặp lô FEFO≠FIFO (`LO-0918` nhập 2026-09-25 hạn 2026-10-04; `LO-0915` nhập 2026-09-21 hạn 2026-10-08 — nhập sau nhưng hạn sớm hơn). Batch bổ sung tạo tay qua `create_batch`/`publish_batch` (không sửa code sản phẩm) để dựng ca AC4 (lô quá hạn), AC6 (lô mới hạn sớm hơn cả `LO-0918`). Cùng phiên với QA lô L8 (xem `doc/features/2026-09-24-erp-console-noi-that/04-qa-report.md`, mục "QA lô L8"), dùng chung backend/adapter thật, dọn sạch khi xong.

## Theo AC

| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| F1-AC1 (lô hạn sớm hơn ra trước dù nhập sau) | ✅ | Đặt 1 kg CA-THU qua `POST /api/shop/orders/` → `allocations` chỉ có `LO-0918` (hạn 10-04), không đụng `LO-0915` (hạn 10-08, nhập sớm hơn 4 ngày). U `test_f1_fefo.py` (cả 2 tầng service + đơn) |
| F1-AC2 (cùng hạn: nhập trước ra trước, rồi tới lô tạo trước) | ✅ (U + đối chiếu danh sách) | Chưa dựng lại ca "hai lô cùng hạn tuyệt đối" bằng đơn thật trong lượt này (khó tạo hai lô cùng `expiry_date` qua `shelf_life_days`); U `test_allocate_fefo_cung_han_thi_lo_nhap_truoc_ra_truoc` + `test_f1_ac2_cung_han_lo_nhap_som_hon_ra_truoc` xanh, kiểm cả tiêu chí phụ "cùng ngày nhập thì lô tạo trước ra trước" |
| F1-AC3 (đơn cần nhiều hơn 1 lô) | ✅ | Đặt 56 kg CA-THU (> 55 kg còn lại của `LO-0918` lúc đó) → `allocations` = 55 kg từ `LO-0918` + 1 kg từ `LO-0915`, đúng thứ tự FEFO |
| F1-AC4 (lô quá hạn không được chọn) | ✅ | Tạo lô CA-THU hạn đã qua 19 ngày (`shelf_life_days=1`, còn `status=SELLING` vì job S2 chưa chạy) — `GET /api/shop/catalog/CA-THU/` **không cộng** 15 kg của lô này vào `sellable_qty`; đặt đúng lượng "sellable thật" (90 kg, loại trừ lô quá hạn) → 201; đặt thêm 1 kg (91 kg) → 400 `BR-BH-02` "thiếu 1kg" — chứng minh lô quá hạn **không hề được đụng tới** dù trạng thái field còn ghi SELLING |
| F1-AC5 (combo, mỗi thành phần tự FEFO) | ⏸ (U only) | `seed_demo` không có mặt hàng COMBO nên không dựng được đơn combo thật trong lượt QA. U `test_f1_fefo.py::…ac5` (mức service) xanh — mỗi dòng combo gọi `allocate_fefo` độc lập, không có code rẽ nhánh riêng cho combo nên rủi ro thấp |
| F1-AC6 (đã giữ chỗ, có lô mới hạn sớm hơn, thanh toán không chọn lại) | ✅ | Đơn 1 kg CA-THU giữ chỗ trên `LO-0918`; sau đó publish thêm lô CA-THU hạn **2026-10-01** (sớm hơn cả `LO-0918`); `confirm-payment` đơn cũ → `allocations` **vẫn** `LO-0918` 1 kg, không đụng lô mới hạn sớm hơn — đúng BR-BH-11 |
| F1-AC7 (hoàn/huỷ về đúng lô gốc) | ✅ | Huỷ đơn PROCESSING (56 kg, phân bổ 55 `LO-0918` + 1 `LO-0915`) → tồn `LO-0918` 1→56 kg, `LO-0915` 24→25 kg — cộng lại **đúng từng lô gốc theo đúng số lượng**, không gộp vào lô khác/lô mới hạn sớm hơn |
| F1-AC8 (Shop/Tổng quan/báo cáo không đổi tồn, không lộ giá vốn) | ✅ | `sellable_qty` Shop đúng bằng tổng các lô còn hạn (không đổi cách tính, chỉ đổi thứ tự nội bộ); `GET /api/inventory/batches/` cho `kho1`/`ql1`: 0 field giá vốn; `loc` thấy đủ `purchase_rate`/`landed_unit_cost` (đối chứng phép quét hoạt động đúng) |
| F2-AC1 (hết chữ "FIFO", phụ đề FEFO, bảng sắp theo hạn) | ✅ | Build `erp-console` thật trỏ BE thật: `grep FIFO` trên `out/` = **0**; trang `/overview/` và `/inventory/` (Playwright, đăng nhập `loc`, 1280 px) đều có chữ "FEFO" trong phụ đề, **không có** chữ "FIFO"; bảng "Kho & lô" hiện `LO-0918` (hạn sớm) **trước** `LO-0915` (hạn muộn hơn), đúng FEFO. M `s8_views.py` +2 kiểm FEFO, 47/47 |

## Ngoại lệ & biên
- Lô quá hạn có `status` còn "SELLING" (job `update_batch_status` — S2 — chưa chạy trong lượt QA này) vẫn bị loại đúng nhờ điều kiện `expiry_date >= hôm nay` chạy song song với `status`, không phụ thuộc job — khớp bất biến #6 và ghi chú dev "Lọc BR-LO-02 chạy trước, sau đó mới sắp".
- Đặt hàng vượt đúng 1 kg so với tồn khả dụng thật (91 kg khi chỉ còn 90 kg sau khi loại lô quá hạn) → 400 `BR-BH-02`, không tạo đơn, không giữ chỗ một phần.
- Đơn giữ chỗ cũ (F1-AC6) không bị "hút" sang lô mới có hạn sớm hơn xuất hiện sau — xác nhận phân bổ **chốt một lần lúc tạo đơn** (BR-BH-11), không tính toán lại lúc thanh toán dù có lô tốt hơn.

## Phân quyền / rò giá vốn
Không có hành động Tầng 2 mới trong F1/F2 (chỉ đổi thứ tự dữ liệu đã có). Qui về bảng phân quyền hiện có của `inventory.view_batch`/`sales.view_salesorder`:

| Endpoint | Chủ | Quản lý | NV kho | NV giao | Chưa đăng nhập |
|---|---|---|---|---|---|
| `GET /api/inventory/batches/` (sắp FEFO) | 200, có giá vốn | 200, 0 giá vốn | 200, 0 giá vốn | 403 (U) | 401 (U) |
| `GET /api/shop/catalog/` | 200 (public) | 200 | 200 | 200 | 200 |

Rò giá vốn: quét đệ quy `GET /api/inventory/batches/` và `GET /api/sales/orders/{id}/` (có `allocations[]`) cho `kho1`, `ql1` → 0 field `unit_cost`/`purchase_rate`/`landed_unit_cost`. Đối chứng `loc` thấy đủ.

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ Ran 512 tests, OK (gồm 25 test F1: 12 `inventory/batches`, 12 `sales/orders`, 1 `accounts/demo`) |
| `makemigrations --check --dry-run` | ✅ No changes detected |
| erp-console `tsc --noEmit` · `npm run build` (thật, mock, trỏ BE thật) | ✅ exit 0 ×3 |
| `frontend npm run build` (Shop) | ✅ exit 0 |
| e2e mock `s8_views.py` (+2 kiểm FEFO) | ✅ 47/47 |
| e2e mock hồi quy `s7_shell` · `s10_s11_orders` · `s12_s13_queue` · `s41_s47_staff` · `s48_password` | ✅ 25/25 · 90/90 · 100/100 · 72/72 · 41/41 |
| e2e BE thật `s41_s47_real` (quy trình liền kề tài khoản) | ✅ 39/39 |
| `shop_e2e` (Shop thật → BE thật) | ✅ 3/3 |
| `grep -rn FIFO backend/` | chỉ còn alias `allocate_fifo` (giữ tương thích, có docstring giải thích), không còn logic/chữ hiển thị nào |

## Lỗi
Không phát hiện lỗi mới. Không có mục Critical/High/Medium.

### Ghi nhận (không chặn)
- F1-AC5 (combo) chỉ được xác nhận ở mức unit test trong lượt QA này vì `seed_demo` chưa có mặt hàng COMBO. Đề xuất: thêm 1 mặt hàng combo vào `seed_demo` ở lô sau để QA/UAT dựng được ca thật qua Shop (không phải sửa trong lượt này vì đây là product code).
- Dev-notes đã tự nêu nợ: mock Tổng quan/Kho (`dashboardSummary.mock.ts`) chưa có ca "nhập trước hạn muộn" — FE vẫn đúng nhờ `fefoOrder()` xử lý phía client, chỉ ảnh hưởng khả năng minh hoạ trên bản mock, không ảnh hưởng hành vi thật (đã kiểm trên backend thật ở F2-AC1).
- Câu SQL đối soát dữ liệu production (chênh giữa FIFO cũ và FEFO mới) trong dev-notes là việc của Duy/ops trước khi triển khai, ngoài phạm vi QA lượt này.

## Lệnh đã chạy (kèm output tóm tắt)
```
backend manage.py test                                       → Ran 512 tests in 27.6s OK
makemigrations --check --dry-run                              → No changes detected
DB scratchpad: migrate → bootstrap_masterdata → seed_demo (7 lô, có cặp FEFO LO-0918/LO-0915)
django runserver 127.0.0.1:8000 (SQLite scratchpad, dùng chung phiên với QA lô L8)
GET /api/inventory/batches/?item=1 (loc)                      → LO-0918 (hạn 10-04) liệt kê trước LO-0915 (hạn 10-08)
POST /api/shop/orders/ {CA-THU, qty:1}  → allocations: LO-0918 1kg                         (F1-AC1)
make_new_earlier_batch.py (shell) → publish lô CA-THU hạn 10-01
POST /api/sales/orders/{id}/confirm-payment                   → allocations vẫn LO-0918 1kg (F1-AC6)
POST /api/shop/orders/ {CA-THU, qty:56} → allocations: 55kg LO-0918 + 1kg LO-0915           (F1-AC3)
POST /api/sales/orders/{id}/confirm-payment; POST .../cancel/ → LO-0918 1→56kg, LO-0915 24→25kg (F1-AC7)
make_expired_batch.py (shell) → publish lô CA-THU hạn 2026-09-07 (quá hạn, status vẫn SELLING)
GET /api/shop/catalog/CA-THU/ → sellable_qty "90.000" (loại 15kg lô quá hạn)                (F1-AC4, F1-AC8)
POST /api/shop/orders/ {qty:91} → 400 BR-BH-02 · {qty:90} → 201, allocations bỏ qua lô quá hạn
erp-console npm run build (NEXT_PUBLIC_API_BASE=:8000) → out/ 0 "FIFO"
http.server 3102 (build BE thật) + Playwright: /overview/, /inventory/ (loc, 1280px)        → 0 "FIFO", có "FEFO", LO-0918 trước LO-0915
http.server 3101 (mock out) → e2e s8_views (+2 FEFO), s7_shell, s10_s11_orders, s12_s13_queue, s41_s47_staff, s48_password → tất cả PASS
DB scratchpad riêng (Songbien2026) → s41_s47_real → 39/39; shop_e2e (:3003) → 3/3
kill mọi PID, lsof 8000/8100/3003/3101/3102 sạch, backend/db.sqlite3 mtime không đổi
```
Script/log/ảnh dùng chung với lượt QA lô L8 ở scratchpad `qafinal/` (xem báo cáo lô L8 để tránh trùng lặp): `qa_money_fefo.py`, `make_new_earlier_batch.py`, `make_expired_batch.py`, `ui_real_check.py`/`ui_real_check2.py`, `shots_real/`. Không sửa code sản phẩm, không thêm test vào repo ngoài phạm vi cho phép.
