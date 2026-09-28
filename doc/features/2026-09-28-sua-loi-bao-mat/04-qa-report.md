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
