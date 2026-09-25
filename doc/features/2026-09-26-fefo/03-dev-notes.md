# Xuất kho FEFO: dev notes

## F1 (BE): chọn lô theo FEFO
> BE · 2026-09-26 · Nguồn: 01-analysis.md, 02-stories.md (ĐÃ DUYỆT), decisions 2026-09-26.

### Rule đã cài
- **BR-BH-05 (sửa):** thứ tự xuất = `expiry_date` tăng dần → `received_date` → `id` (lô tạo trước).
  Khoá này là hằng `FEFO_ORDER` trong `apps/inventory/batches/services.py`. `sellable_batches` là nguồn
  duy nhất "lô bán được + thứ tự xuất". Lọc BR-LO-02 (SELLING/NEAR_EXPIRY và hạn ≥ hôm nay) chạy trước, sau đó mới sắp.
- **BR-BH-11 (mới, ghi thành luật cho hành vi có sẵn):** phân bổ lô chỉ chạy lúc `create_order`.
  `issue_invoice` (payments) trừ đúng các lô trong `SalesOrderLineBatch`. Không sửa code payments, chỉ thêm test (AC6).
- BR-HV-01 / BR-HT-05: `apply_return` và `cancel_paid_order` cộng về đúng lô gốc, hạn lô không đổi. Không sửa code, chỉ thêm test (AC7).
- Q1: áp dụng cho toàn bộ mặt hàng, kể cả từng thành phần combo. Không có cấu hình theo mặt hàng. Q2: không cho chọn tay lô.

### File đã sửa
| File | Thay đổi |
|---|---|
| `backend/apps/inventory/batches/services.py` | Thêm `FEFO_ORDER`. `sellable_batches` sắp theo FEFO. Đổi `allocate_fifo` → `allocate_fefo` và giữ alias `allocate_fifo = allocate_fefo` (hành vi FEFO). Sửa docstring |
| `backend/apps/sales/orders/services.py` | `create_order` gọi `allocate_fefo`; sửa docstring/comment |
| `backend/apps/reports/dashboard_api.py` | Bảng "Tồn theo lô" (≤20 lô) sắp theo `FEFO_ORDER` thay cho `received_date, id` |
| `backend/apps/inventory/batches/api.py` | `GET /api/inventory/batches/` sắp theo `FEFO_ORDER` (UC-6: Kho & lô theo thứ tự xuất) |
| `backend/apps/inventory/models/batches.py` | Chỉ sửa comment: `Meta.ordering` giữ `received_date, id` và **không** phải thứ tự xuất. Không đổi giá trị nên không cần migration |
| `backend/apps/accounts/management/commands/seed_demo.py` | Thêm lô demo `LO-0915` (CA-THU, nhập 5 ngày trước, còn 12 ngày hạn), nhập trước `LO-0918` (nhập 1 ngày trước, còn 8 ngày hạn), để QA thấy FEFO khác FIFO. Đơn demo cá thu vẫn giữ chỗ trên `LO-0918`. Sửa comment |
| README/docstring: `apps/inventory/README.md`, `apps/inventory/batches/README.md`, `apps/inventory/models/__init__.py`, `apps/sales/README.md`, `apps/sales/orders/README.md` | Thay chữ FIFO bằng FEFO. Grep `FIFO` trong `backend/` chỉ còn tên alias `allocate_fifo` |

Mọi chỗ khác đã grep (`received_date`, `order_by`) không sắp lô cho mục đích xuất hàng. Chi tiết:
- `catalog/items/services.py::sellable_qty` (Shop) chỉ cộng tổng qua `sellable_batches`, không phụ thuộc thứ tự.
- Pricing và combo không sắp lô. Combo đi qua `create_order` → `allocate_fefo` cho từng thành phần.
- Cảnh báo cận hạn trên dashboard vốn đã sắp theo `expiry_date`.
- Admin (`date_hierarchy`, `list_display`) dùng `Meta.ordering` mặc định. Chấp nhận vì đây là màn quản trị, không phải thứ tự xuất.

### Endpoint / contract
Không thêm endpoint, không đổi field JSON. Chỉ đổi **thứ tự phần tử**:
- `GET /api/dashboard/summary/` → `batches[]` sắp FEFO. Khi có hơn 20 lô thì tập 20 lô hiển thị có thể khác trước (Q8 đã chấp nhận).
  Bảng này gồm cả lô Nháp và lô quá hạn mà job chưa kịp chuyển trạng thái (`ACTIVE_BATCH` không đổi). Các lô đó cũng sắp theo hạn.
- `GET /api/inventory/batches/` → `results[]` sắp FEFO.
- Shop `/api/shop/catalog/`: `sellable_qty` không đổi.

Ví dụ `batches[]` (người không có `view_costprice`, không có key `unit_cost`). Lô nhập sau đứng đầu vì hạn sớm hơn:
```json
[{"batch_id": "LO-0918", "item": "Cá thu", "received_date": "2026-09-25", "expiry_date": "2026-10-04", "near_expiry": false, "...": "..."},
 {"batch_id": "LO-0915", "item": "Cá thu", "received_date": "2026-09-21", "expiry_date": "2026-10-08", "near_expiry": false, "...": "..."}]
```

### Migration
Không có. `makemigrations --check --dry-run`: "No changes detected".

### Test
Test mới:
- `backend/apps/inventory/batches/tests/test_f1_fefo.py` (12 test): AC1–AC4 ở tầng service, alias `allocate_fifo`, AC8 danh sách lô theo FEFO, nv_kho không thấy giá vốn, chưa đăng nhập bị 401.
- `backend/apps/sales/orders/tests/test_f1_fefo.py` (12 test): AC1–AC5 qua `create_order`, AC6 (`confirm_payment_manual`), AC7 (huỷ đơn đã thanh toán, giao thất bại tái nhập), AC8 (Shop, dashboard sắp FEFO, nv_kho không có key giá vốn, nv_giao bị 403).
- `backend/apps/accounts/demo/tests/test_d1_seed_demo.py::F1SeedFefoCaseTests` (1 test): demo có ca FEFO khác FIFO.

Test đỏ trước khi sửa: mọi test AC1/AC3/AC4/AC5/AC8 và alias. AC6/AC7 cũng đỏ lúc đầu, vì bước kiểm cuối của chúng ("đơn mới sau đó đi lô hạn sớm hơn") phụ thuộc FEFO. Phần "không chọn lại lô / trả về lô gốc" là hành vi đã có, test đóng vai **test giữ hành vi** (characterization) cho BR-BH-11 / BR-HT-05 / BR-HV-01.
AC2 ở tầng đơn (`test_f1_ac2_cung_han_lo_nhap_som_hon_ra_truoc`) xanh ngay, vì FIFO cũng cho cùng kết quả khi hai lô cùng hạn. Test AC2 ở tầng service thì có kiểm tiêu chí thứ ba (cùng ngày nhập thì lô tạo trước ra trước).

Test cũ đã sửa:
| Test | Sửa gì | Vì sao |
|---|---|---|
| `inventory/batches/tests/test_services.py::test_allocate_fifo_orders_by_received_date` → `test_allocate_fefo_cung_han_thi_lo_nhap_truoc_ra_truoc` | Đổi tên, gọi `allocate_fefo`. Kỳ vọng giữ nguyên | Hai lô trong test có **cùng hạn** (hạn tính từ ngày tạo, sau đó chỉ sửa `received_date`), nên dưới FEFO test này kiểm tiêu chí phụ "cùng hạn thì nhập trước" |
| `test_services.py::test_allocate_fifo_insufficient_raises` → `test_allocate_fefo_insufficient_raises`; `test_draft_batch_not_sellable` | Gọi `allocate_fefo` | Đổi tên hàm |
| `inventory/batches/tests/test_s1_expiry.py` (4 chỗ) | Gọi `allocate_fefo` | Đổi tên hàm, ý test S1 giữ nguyên |
| `sales/orders/tests/test_services.py::test_order_spans_multiple_batches_fifo` → `..._fefo` | Đổi tên và comment. Kỳ vọng giữ nguyên | Lô nhập hôm qua có hạn = hôm qua + 90, sớm hơn lô nhập hôm nay, nên FEFO vẫn chọn nó trước |
| `accounts/demo/tests/test_d1_seed_demo.py` | `DEMO_BATCH_IDS` thêm `LO-0915`. Số lô demo 6 → 7 | Thêm lô demo cho ca FEFO |

Không có test cũ nào có lô nhập trước mà hạn muộn hơn, nên không phải đảo kỳ vọng FIFO → FEFO ở test nào.

Kết quả cuối (2026-09-26):
- `manage.py test`: **Ran 512 tests, OK**. Trong đó: 471 test mốc, 25 test F1, 16 test `sales/payments/tests/test_l8_tien_bosung.py` của nhóm làm song song.
- `makemigrations --check --dry-run`: No changes detected.
- `check`: 0 issues.

Ở một lần chạy giữa chừng, 8 test trong `apps/sales/payments/tests` (`test_l8_*`, `test_b13_*`) bị đỏ do nhóm payments đang sửa dở. Tôi không đụng vào thư mục đó. Ở lần chạy cuối, cả 8 test đã xanh.

### Còn nợ / giả định
1. **Đếm trên DB thật trước khi triển khai** (mục 7 phân tích). Tôi không được đụng DB production. Đây là câu SQL chỉ đọc để Duy/ops chạy: nó đếm các cặp lô cùng mặt hàng, đều đang bán được, mà thứ tự FIFO khác FEFO.
   ```sql
   SELECT a.item_id, a.batch_id AS nhap_truoc_han_muon, b.batch_id AS nhap_sau_han_som
   FROM inventory_batch a JOIN inventory_batch b ON a.item_id = b.item_id
   WHERE a.status IN ('SELLING','NEAR_EXPIRY') AND b.status IN ('SELLING','NEAR_EXPIRY')
     AND a.expiry_date >= CURRENT_DATE AND b.expiry_date >= CURRENT_DATE
     AND (a.received_date, a.id) < (b.received_date, b.id) AND a.expiry_date > b.expiry_date;
   ```
2. **Hạn dùng trên phần phân bổ lô của đơn** (Q9/UC-6, NV kho soạn đúng lô): `allocations[]` ở API đơn hiện chỉ có `batch_id`, chưa có `expiry_date`. Thêm field này là **đổi contract**, và F1/F2 chưa có AC nào yêu cầu, nên tôi chưa làm. Nếu FE cần thì thêm `allocations[].expiry_date` (field này không nhạy cảm).
3. `Batch.Meta.ordering` giữ `received_date, id` để không sinh migration. Thứ tự xuất nằm ở `FEFO_ORDER`.
4. R-5: lô demo mới `LO-0915` có hạn **dài hơn** lô demo sẵn có, nên không làm tăng việc FEFO hút đơn thật vào lô demo. Tuy vậy, trong ca đó các lô demo hạn ngắn (`LO-0912`, `LO-0907`…) vẫn bị FEFO ưu tiên trước lô thật cùng mặt hàng.
5. Alias `allocate_fifo`: trong code không còn chỗ gọi ngoài test alias. Giữ lại cho script/nhánh khác. Có thể xoá ở một đợt dọn sau.

## F2 (FE): hiển thị FEFO trên ERP console · 2026-09-26
> FE · làm kèm lô L8 FE (hồ sơ `2026-09-24-erp-console-noi-that`). Chỉ `erp-console/`. F2-AC2 (tài liệu URD/spec/skill) **không** thuộc phần FE này.

### F2-AC1 — đã làm
- **Tổng quan** (`features/overview/components/OverviewScreen.tsx`): phụ đề bảng "Tồn kho theo lô" = **"Xuất theo hạn dùng sớm nhất (FEFO)"**
  (thay "FIFO theo ngày nhập"); gợi ý khi rỗng đổi thành "…xếp theo hạn dùng sớm nhất (FEFO)".
- **Kho & lô** (`features/inventory/components/InventoryScreen.tsx`): đầu màn "Tồn theo lô, xuất theo hạn dùng sớm nhất (FEFO).", phụ đề
  "N lô đang hoạt động · Xuất theo hạn dùng sớm nhất (FEFO)", gợi ý rỗng như trên. Mô tả menu (`shared/lib/nav.ts`), README module
  overview, comment kiểu `DashboardBatch`, comment mock orders: bỏ chữ FIFO.
- **Thứ tự:** `shared/lib/dashboardSummary.ts` thêm `fefoOrder()` — `expiry_date` tăng → `received_date` tăng → giữ thứ tự BE (BE đã sắp
  theo `FEFO_ORDER`, tiêu chí cuối là `id`, nên FE giữ nguyên thứ tự đó); lô không có hạn xếp cuối. `filterBatches` của overview và
  inventory đi qua hàm này, nên bảng đúng thứ tự xuất cả khi BE cũ còn sắp theo ngày nhập. Chỉ để hiển thị; chọn lô thật do BE (F1).
- `grep -rn FIFO erp-console/{app,features,shared,README.md}` → 0 (chỉ còn trong kiểm e2e khẳng định **không có** chữ này).

### Kiểm
- `tsc` sạch, `npm run build` thật sạch. `e2e/s8_views.py` **47/47** (+2 kiểm: phụ đề FEFO và trang không còn "FIFO"; cột hạn dùng tăng dần).
  Hồi quy `s7_shell` 25/25, `s10_s11_orders` 90/90, `s12_s13_queue` 100/100 (mock build, server có giới hạn thời gian, đã kill, `lsof` sạch).

### Còn nợ
- Mock Tổng quan/Kho (`shared/lib/dashboardSummary.mock.ts`) chưa có ca "nhập trước hạn muộn" để thấy FEFO khác FIFO trên màn mock; FE vẫn
  sắp đúng nhờ `fefoOrder`. Có thể thêm khi làm S25.
- Nếu FE cần hạn dùng trên phân bổ lô của đơn (mục 2 phía BE) thì cần BE thêm `allocations[].expiry_date`.
