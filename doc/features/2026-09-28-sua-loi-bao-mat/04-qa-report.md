# Báo cáo QA — Sửa lỗi bảo mật có sẵn (L-1, L-3, L-5, L-6, robots staging) + L-10, L-11

## Lô 1: S01 (L-3), S02 (L-6), S03 (L-5) · Lần 1 · 2026-09-28
### Kết luận: APPROVED — Lô 1 đạt 100% tiêu chí AC của S01, S02, S03, bảo đảm triệt để Bất biến 1 & Bất biến 9, toàn bộ test xanh.
### Tổng: 67 ca · ✅ 67 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/ảnh/lệnh) |
|---|---|---|
| **S01-AC1** (Chủ thấy đủ giá vốn) | ✅ PASS | `apps/accounts/audit/tests/test_l3_cost_redaction.py::test_s01_ac1_chu_thay_du_gia_von`: `changes.landed_unit_cost` còn nguyên `{"from": "111111.1111", "to": "987654.3210"}`. |
| **S01-AC2** (Quản lý không thấy giá vốn) | ✅ PASS | `apps/accounts/audit/tests/test_l3_cost_redaction.py::test_s01_ac2_quan_ly_khong_thay_gia_von`: duyệt đệ quy không khoá nào thuộc `COST_KEYS`; JSON không chứa số mẫu `987654.3210`, `111111.1111`, `55000`, `65000`; khoá không nhạy cảm `status` vẫn còn. |
| **S01-AC3** (Theo quyền view_costprice) | ✅ PASS | `apps/accounts/audit/tests/test_l3_cost_redaction.py::test_s01_ac3_quan_ly_co_quyen_view_costprice_thay_gia_von`: Quản lý cấp thêm perm hoặc superuser đều thấy khoá giá vốn. |
| **S01-AC4** (Phân quyền & lọc ?action=) | ✅ PASS | `apps/accounts/audit/tests/test_l3_cost_redaction.py::test_s01_ac4_phan_quyen_giu_nguyen_va_loc_action`: `nv_kho` 403, `nv_giao` 403, khách 401; lọc `?action=admin_edit` hoạt động chính xác. |
| **S01-AC5** (Danh sách khoá dùng chung & append-only) | ✅ PASS | `apps/common/tests/test_cost_keys.py` (6 tests unit: flat, dict lồng, list chứa dict, input bất biến) & `test_s01_ac5_du_lieu_auditlog_khong_bi_sua_trong_db`: DB không bị sửa (append-only). |
| **S01-AC6** (Không rò PII) | ✅ PASS | Response giữ nguyên 11 field tiêu chuẩn, không thêm field mới; suite cũ xanh. |
| **S02-AC1** (Bắt buộc đúng 4 chữ số) | ✅ PASS | `apps/sales/orders/tests/test_l6_lookup.py::test_s02_ac1_bat_buoc_dung_4_chu_so`: 5 giá trị sai định dạng `""`, `"8"`, `"678"`, `"05678"`, `"56a8"` × {mã thật, mã giả} đều 400 cùng body `{"detail": "Vui lòng nhập đúng 4 số cuối số điện thoại."}`. |
| **S02-AC2** (Một thông điệp 404) | ✅ PASS | `apps/sales/orders/tests/test_l6_lookup.py::test_s02_ac2_mot_thong_diep_404_cho_ca_hai_truong_hop`: mã không tồn tại và mã có thật sai số đều trả 404 `{"detail": "Không tìm thấy đơn với mã và số điện thoại này."}`. Không dò được mã đơn. |
| **S02-AC3** (Đúng thì xem được, không rò PII) | ✅ PASS | `apps/sales/orders/tests/test_l6_lookup.py::test_s02_ac3_dung_thi_xem_duoc_khong_ro_pii`: đúng 7 khoá `order_code`, `status`, `status_label`, `total_amount`, `lines`, `delivery`, `booked_expires_at`; không có `customer`, `phone`, `name`, `delivery_address`. |
| **S02-AC4** (SĐT có dấu cách/+84) | ✅ PASS | `apps/sales/orders/tests/test_l6_lookup.py::test_s02_ac4_sdt_co_dau_cach_hoac_cong_84`: `0900 000 678` và `+84900000678` tra với `0678` đều 200. |
| **S02-AC5** (Thanh toán Shop 404 chung) | ✅ PASS | `apps/sales/orders/tests/test_l6_lookup.py::test_s02_ac5_checkout_ma_khong_ton_tai_tra_404_chung`: checkout mã không tồn tại trả 404 `LOOKUP_NOT_FOUND`. |
| **S02-AC6** (Phân quyền & user đăng nhập) | ✅ PASS | `apps/sales/orders/tests/test_l6_lookup.py::test_s02_ac6_phan_quyen_endpoint_van_cong_khai_va_user_login_tuan_thu_ac1_ac3`: user mọi Group gọi đều phải qua AC1–AC3, không có đường tắt xem đơn. |
| **S03-AC1** (Throttle tra đơn IP & mã đơn) | ✅ PASS | `apps/common/tests/test_l5_throttle.py::test_s03_ac1_shop_lookup_ip_throttle` & `test_s03_ac1_shop_lookup_order_throttle_across_ips`: lần 6/phút IP trả 429 kèm `Retry-After`; 4 IP tra cùng 1 mã đơn lần 4 trả 429. |
| **S03-AC2** (Throttle đặt đơn, thanh toán, login) | ✅ PASS | `apps/common/tests/test_l5_throttle.py::test_s03_ac2_shop_order_create_throttle_khong_tao_don`, `test_s03_ac2_login_ip_throttle_khong_sinh_token`, `test_s03_ac2_login_user_throttle`: request bị chặn không tạo đơn, không sinh token. |
| **S03-AC3** (Mức cấu hình được qua env) | ✅ PASS | `apps/common/tests/test_l5_throttle.py::test_s03_ac3_tat_scope_khi_muc_la_none_hoac_rong`: gán None/rỗng thì tắt scope. |
| **S03-AC4** (Không vỡ test cũ) | ✅ PASS | `CAVEVE_THROTTLE_RATES` mặc định tắt khi `TESTING=True`. Toàn bộ 692 test xanh. |
| **S03-AC5** (Không đụng back-office) | ✅ PASS | `apps/common/tests/test_l5_throttle.py::test_s03_ac5_backoffice_khong_bi_throttle`: `chu` gọi 50 lần liên tiếp vào `/api/audit-logs/` đều 200, không bị 429. |
| **S03-AC6** (Không giả IP, không rò PII) | ✅ PASS | `apps/common/tests/test_l5_throttle.py::test_s03_ac6_num_proxies_dem_chung_ip_cuoi_xff`: `NUM_PROXIES` đếm chung IP thật cuối `9.9.9.9`; cache key `login_user` băm sha256 không lộ username thô. |

### Ngoại lệ & biên
- **S01 Biên dữ liệu `changes`**: Kiểm tra các cấu trúc phức tạp (dict lồng 3 cấp, mảng các object, giá trị None/chuỗi/số) đều được redact sạch các khoá giá vốn mà không gây exception. Input gốc không bị mutate (`test_redact_cost_immutable_does_not_modify_input`).
- **S02 Biên SĐT & mã đơn**:
  - `phone_last4` chứa ký tự chữ cái, dấu cách, hoặc độ dài khác 4 ký tự đều bị chặn ngay ở tầng validation regex `\d{4}` (HTTP 400) TRƯỚC khi query DB, loại bỏ nguy cơ timing attack dò sự tồn tại của đơn hàng.
  - SĐT định dạng quốc tế (`+84`) hoặc phân tách bằng khoảng trắng được lọc chữ số `re.sub(r"\D", "", phone)` trước khi so sánh 4 số cuối.
- **S03 Biên throttle**:
  - Scope với giá trị env `off`, `none`, `0`, rỗng đều được xử lý tắt mượt mà không crash.
  - Request login thiếu trường `username` không ghi đếm vào `login_user` scope (`ident=None`).

### Phân quyền (bảng vai × hành động)
| Vai | GET /api/audit-logs/ | GET /api/shop/orders/<mã>/ (kèm 4 số cuối) | POST /api/auth/token/ (login) |
|---|---|---|---|
| **Chủ** (`chu`) | 200 (thấy đủ giá vốn) | 200 (đúng 7 khoá an toàn) | 200 (có throttle) |
| **Quản lý** (`quan_ly`) | 200 (đã lọc sạch giá vốn) | 200 (đúng 7 khoá an toàn) | 200 (có throttle) |
| **Quản lý** (`quan_ly` + `view_costprice`) | 200 (thấy đủ giá vốn) | 200 (đúng 7 khoá an toàn) | 200 (có throttle) |
| **Nhân viên kho** (`nv_kho`) | 403 Forbidden | 200 (đúng 7 khoá an toàn) | 200 (có throttle) |
| **Nhân viên giao** (`nv_giao`) | 403 Forbidden | 200 (đúng 7 khoá an toàn) | 200 (có throttle) |
| **Khách** (chưa đăng nhập) | 401 Unauthorized | 200 (đúng 7 khoá an toàn) | 200 (có throttle) |

### Rò giá vốn (Bất biến 1 — BR-PQ-13, BR-GV-03)
- ✅ Đã đối chiếu với danh sách `COST_KEYS` toàn diện: `purchase_rate`, `landed_unit_cost`, `unit_cost`, `rate`, `allocated_amount`, `purchase_cost`, `allocated_cost`, `total_cost`, `shrinkage_cost`, `damage_cost`, `cogs`, `profit`.
- ✅ Quản lý gọi `GET /api/audit-logs/`: JSON response không chứa bất kỳ khoá giá vốn nào ở mọi độ sâu; các con số giá vốn mẫu (`987654.3210`, `111111.1111`, `55000`, `65000`) hoàn toàn không xuất hiện trong payload trả về.
- ✅ Dữ liệu trong database giữ nguyên tính append-only (chỉ lọc tại serializer).

### Rò dữ liệu cá nhân khách (Bất biến 9)
- ✅ API Tra đơn Shop `GET /api/shop/orders/<order_code>/?phone_last4=...` phản hồi đúng tập 7 khoá công khai: `order_code`, `status`, `status_label`, `total_amount`, `lines`, `delivery`, `booked_expires_at`.
- ✅ Tuyệt đối không trả về: `customer`, `phone`, `customer_phone`, `name`, `customer_name`, `delivery_address`, `address`.
- ✅ Hai trường hợp: "Mã đơn không tồn tại" và "Mã đơn tồn tại nhưng sai 4 số cuối SĐT" trả về cùng mã HTTP 404 và cùng thông điệp `LOOKUP_NOT_FOUND` ("Không tìm thấy đơn với mã và số điện thoại này."), ngăn chặn kẻ tấn công dò mã đơn hoặc đoán SĐT.
- ✅ Rate limit `shop_lookup_order` (chặn theo mã đơn trên nhiều IP) ngăn chặn tấn công vét cạn 10.000 khả năng của 4 số cuối SĐT.
- ✅ Throttle `login_user` sử dụng SHA-256 băm username, không lưu trữ PII thô trong cache key.
- ✅ Đã đối chiếu màn Shop tra đơn khi chạy Mock (`NEXT_PUBLIC_USE_MOCK=1`): trả về kết quả nhất quán với backend thật (hiện thông báo "Không tìm thấy đơn hàng phù hợp" khi không khớp mã/SĐT).

### Hồi quy
- ✅ Toàn bộ 667 test cũ của backend chạy hoàn toàn xanh, không có bất kỳ regression nào.
- ✅ Tổng số test backend tăng lên 692 test (thêm 25 test mới cho Lô 1).
- ✅ Không phát sinh migration nào (`makemigrations --check --dry-run` báo `No changes detected`).

### Lỗi
- Không có lỗi nào (0 lỗi).

### Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test apps.accounts.audit apps.common apps.sales`
   - Output: `Ran 337 tests in 23.903s. OK`
2. `grep -rn "throttle" backend/config/settings.py backend/apps/common/throttling.py`
   - Output: Cấu hình `CAVEVE_THROTTLE_RATES`, `NUM_PROXIES` và các lớp throttle được khai báo đầy đủ, chuẩn xác.
3. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`
   - Output: `Ran 692 tests in 63.235s. OK`, `No changes detected`.

## Lô 2: S04 (L-1), S05 (robots staging) · Lần 1 · 2026-09-28
### Kết luận: APPROVED — Lô 2 đạt 100% tiêu chí AC của S04 và S05, bảo đảm chặt chẽ Bất biến 1 (Không rò giá vốn) và Bất biến 9 (Không rò PII khách), an toàn tranh chấp đồng thời, build FE sạch và giữ nguyên cấu hình production.
### Tổng: 54 ca · ✅ 54 · ❌ 0 · ⏸ 0

### Theo AC
| Mã AC | Kết quả | Bằng chứng (test/ảnh/lệnh) |
|---|---|---|
| **S04-AC1** (Còn đơn mở → chặn BR-LO-04) | ✅ PASS | `apps/inventory/batches/tests/test_l1_close_batch.py`: `test_s04_ac1_open_order_booked_blocks_close`, `test_s04_ac1_open_order_paid_blocks_close`, `test_s04_ac1_open_order_processing_blocks_close` trả 400 `code="BR-LO-04"`, `detail="Còn 1 đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04)."`, batch không đổi trạng thái, không ghi AuditLog; `test_s04_ac1_multiple_lines_same_order_distinct_count` đếm distinct đơn mở (1 đơn 2 dòng tính là 1; thêm đơn thứ 2 tính là 2); `test_s04_ac1_closed_order_statuses_do_not_block_close` (`COMPLETED`, `CANCELLED`, `AUTO_CANCELLED`) không chặn chốt lô; `test_s04_ac1_error_message_contains_no_customer_pii` xác nhận SĐT, tên, địa chỉ khách không xuất hiện trong response. |
| **S04-AC2** (Còn giữ chỗ hoặc hàng hoàn chờ duyệt → chặn) | ✅ PASS | `test_s04_ac2_qty_reserved_blocks_close`: `qty_reserved > 0` trả 400 `code="BR-LO-04"`, detail nêu rõ giữ chỗ chưa giải phóng; `test_s04_ac2_draft_return_to_stock_blocks_close`: `ReturnToStock` ở trạng thái `DRAFT` trả 400 `BR-LO-04`; `test_s04_ac2_approved_return_to_stock_does_not_block_close`: phiếu hàng hoàn `APPROVED` cho phép chốt thành công 200. |
| **S04-AC3** (Chưa kiểm kê → chặn BR-KK-05) | ✅ PASS | `test_s04_ac3_no_reconciliation_line_blocks_close`: không có dòng kiểm kê trả 400 `code="BR-KK-05"`, detail `"Lô phải được kiểm kê và duyệt trước khi chốt (BR-KK-05)."`; `test_s04_ac3_draft_reconciliation_line_blocks_close`: chỉ có phiếu `DRAFT` trả 400 `BR-KK-05`; `test_s04_ac3_approved_plus_draft_reconciliation_blocks_close`: có cả phiếu `APPROVED` và phiếu `DRAFT` vẫn bị chặn bởi 400 `BR-KK-05`. |
| **S04-AC4** (Đủ điều kiện → chốt & Chốt lần 2 → 400) | ✅ PASS | `test_s04_ac4_happy_path_close_batch`: đầy đủ điều kiện (tồn 0, không đơn mở, kiểm kê `APPROVED`) trả 200, `status=CLOSED`, `closed_by=chu`, `closed_at` được gán, sinh đúng 1 dòng AuditLog `close_batch`; `test_s04_ac4_close_already_closed_batch_raises_br_lo_05`: chốt lần 2 trả 400 `code="BR-LO-05"`, `detail="Lô đã chốt."`. |
| **S04-AC5** (Khoá đồng thời & loại khỏi FEFO) | ✅ PASS | `test_s04_ac5_closed_batch_not_picked_by_allocate_fefo`: sau khi chốt, `allocate_fefo` loại trừ lô, không lấy lô đã chốt; `test_s04_ac5_select_for_update_and_atomic_execution`: xác minh `Batch.objects.select_for_update()` được gọi bên trong khối `transaction.atomic` trước mọi bước kiểm tra logic. |
| **S04-AC6** (Phân quyền & không rò giá vốn) | ✅ PASS | `test_s04_ac6_forbidden_roles_quan_ly_nv_kho_nv_giao_403`: `quan_ly`, `nv_kho`, `nv_giao` gọi chốt lô đều nhận 403 Forbidden, `batch.status` không đổi; `test_s04_ac6_unauthenticated_returns_401`: khách nhận 401 Unauthorized; `test_s04_ac6_no_cost_leak_in_error_responses`: response 400 không chứa `purchase_rate`, `landed_unit_cost` hay con số giá vốn; `test_s04_ac6_quan_ly_cannot_see_cost_in_close_batch_audit_log`: AuditLog `close_batch` khi được đọc bởi `quan_ly` bị serializer lọc sạch `landed_unit_cost` (tuân thủ S01), trong khi `chu` vẫn đọc được. |
| **S05-AC1** (Shop staging có X-Robots-Tag) | ✅ PASS | `frontend/firebase.staging.json`: khai báo cấu hình `"source": "**"` với header `"X-Robots-Tag": "noindex, nofollow"`. Header `Cache-Control` cho `/_next/static/**` vẫn được giữ nguyên đầy đủ. |
| **S05-AC2** (ERP staging có X-Robots-Tag) | ✅ PASS | `erp-console/firebase.staging.json`: khai báo cấu hình `"source": "**"` với header `"X-Robots-Tag": "noindex, nofollow"`. |
| **S05-AC3** (Production không đổi) | ✅ PASS | `git diff --exit-code frontend/firebase.json erp-console/firebase.json` trả về exit code 0 (hai file production hoàn toàn không bị chỉnh sửa). Không sửa meta trong `app/layout.tsx`. |
| **S05-AC4** (Kiểm trước deploy) | ✅ PASS | Node.js parse thành công cú pháp JSON của cả hai file staging; `npx tsc --noEmit` và `npm run build` thành công trên cả `frontend` (8/8 static pages) và `erp-console` (21/21 static pages). Đã ghi chú hướng dẫn kiểm tra `curl -sI` sau deploy vào `doc/ops/moi-truong.md`. |

### Ngoại lệ & biên
- **Thứ tự kiểm tra điều kiện chốt lô cố định**: 
  1. `is_closed` -> 400 `BR-LO-05` ("Lô đã chốt.")
  2. Tồn `qty_available > 0` và status không phải `EXPIRED`/`CANCELLED` -> 400 `BR-LO-04` (đảm bảo test cũ `test_s3_locked_fields.py:355-361` kiểm lô còn tồn vẫn nhận mã lỗi `BR-LO-04`).
  3. Lượng giữ chỗ `qty_reserved > 0` -> 400 `BR-LO-04`.
  4. Đơn bán hàng đang mở (`BOOKED`, `PAID`, `PROCESSING`) -> 400 `BR-LO-04`.
  5. Phiếu hàng hoàn `ReturnToStock` ở trạng thái `DRAFT` -> 400 `BR-LO-04` (lô chốt không thể nhận hàng hoàn trả về theo BR-LO-05).
  6. Purchase Invoice nếu lô nhập từ PO -> 400 `BR-LO-04`.
  7. Phiếu kiểm kê `StockReconciliation`: bắt buộc có ít nhất 1 dòng thuộc phiếu `APPROVED` và không có bất kỳ dòng nào thuộc phiếu `DRAFT` -> 400 `BR-KK-05`.
- **Trường hợp lô `EXPIRED` còn tồn**: Tạm thời cho phép chốt theo đúng quy định phân tích lỗi L-2 (chờ service huỷ lô ở hồ sơ tiếp theo).
- **Trùng lặp / đồng thời**: 
  - Toàn bộ service `close_batch` được bọc trong `@transaction.atomic` và thực hiện `Batch.objects.select_for_update().get(pk=batch.pk)` trước khi đọc các quan hệ phụ thuộc, triệt tiêu nguy cơ race condition khi hai tiến trình cùng cố gắng chốt lô hoặc vừa tạo đơn vừa chốt lô.
  - Bấm đúp gọi chốt 2 lần liên tiếp: lần đầu 200, lần thứ hai lập tức nhận 400 `BR-LO-05`.
  - Một đơn hàng có nhiều dòng (`SalesOrderLine`) cùng tham chiếu tới 1 lô được khử trùng lặp qua `.values("order_line__order").distinct().count()`, thông điệp báo chính xác số lượng đơn thực tế.

### Phân quyền (bảng vai × hành động)
| Vai | POST /api/inventory/batches/<id>/close/ | Đọc AuditLog `close_batch` qua /api/audit-logs/ |
|---|---|---|
| **Chủ** (`chu`) | 200 OK (có quyền `inventory.close_batch`) | 200 OK (thấy đầy đủ giá vốn `landed_unit_cost`) |
| **Quản lý** (`quan_ly`) | 403 Forbidden | 200 OK (đã bị lọc sạch giá vốn) |
| **Nhân viên kho** (`nv_kho`) | 403 Forbidden | 403 Forbidden |
| **Nhân viên giao** (`nv_giao`) | 403 Forbidden | 403 Forbidden |
| **Khách** (chưa đăng nhập) | 401 Unauthorized | 401 Unauthorized |

### Rò giá vốn (Bất biến 1 — BR-PQ-13, BR-GV-03)
- ✅ Response khi chốt lô thất bại (các lỗi 400 do còn đơn mở, giữ chỗ, kiểm kê) hoàn toàn không chứa các trường giá vốn (`purchase_rate`, `landed_unit_cost`) hay số tiền giá mua.
- ✅ Dòng AuditLog `close_batch` sinh ra có chứa `changes={"landed_unit_cost": {"final": ...}}` cho Chủ kiểm toán, nhưng khi user Quản lý gọi `GET /api/audit-logs/`, serializer `audit_item` (từ S01) đã loại bỏ triệt để khoá `landed_unit_cost` và con số giá vốn khỏi chuỗi JSON trả về.

### Rò dữ liệu cá nhân khách (Bất biến 9)
- ✅ Thông điệp lỗi khi chặn do còn đơn mở chỉ ghi dạng `Còn N đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04).`, tuyệt đối không đưa tên khách hàng, SĐT khách hay địa chỉ nhận hàng vào message hoặc detail lỗi.
- ✅ Test `test_s04_ac1_error_message_contains_no_customer_pii` xác nhận các chuỗi dữ liệu giả của khách hàng (`0900000099`, `Nguyễn Văn Tên Riêng`, `99 Đường Tuyệt Mật`) không xuất hiện trong payload phản hồi.

### Hồi quy & Toàn vẹn hệ thống
- ✅ Toàn bộ 712 test backend chạy hoàn toàn xanh (tăng 20 test từ 692 lên 712 so với Lô 1, tăng 45 test so với baseline).
- ✅ Không phát sinh migration nào (`makemigrations --check --dry-run` báo `No changes detected`).
- ✅ Test cũ duy nhất được cập nhật có chủ đích: `backend/apps/inventory/batches/tests/test_services.py:test_publish_and_close_batch` được bổ sung phiếu kiểm kê `APPROVED` cho lô trước khi chốt theo đúng business rule mới BR-KK-05.
- ✅ Các test phụ thuộc liền kề trong `apps/common/tests/test_s3_locked_fields.py` và `apps/inventory/batches/tests/test_api.py` tiếp tục hoạt động ổn định.
- ✅ Hai file production `frontend/firebase.json` và `erp-console/firebase.json` không có bất kỳ dòng thay đổi nào (`git diff --exit-code` sạch).

### Lỗi
- Không có lỗi nào (0 lỗi).

### Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`
   - Output: `Ran 712 tests in 60.502s. OK`, `No changes detected`.
2. `cd frontend && node -e 'JSON.parse(require("fs").readFileSync("firebase.staging.json","utf8"))' && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build`
   - Output: JSON parse hợp lệ, TypeScript kiểm tra không lỗi, Build Next.js thành công 8/8 static pages.
3. `cd erp-console && node -e 'JSON.parse(require("fs").readFileSync("firebase.staging.json","utf8"))' && npx tsc --noEmit && npm run build`
   - Output: JSON parse hợp lệ, TypeScript kiểm tra không lỗi, Build Next.js thành công 21/21 static pages.
4. `git diff --exit-code frontend/firebase.json erp-console/firebase.json`
   - Output: Exit code 0 (file cấu hình production hoàn toàn không bị đụng tới).
