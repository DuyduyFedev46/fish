# Ghi chú dev BE — Shop làm lại (be-dev)

## Lô 1-BE · SHOP-2-01, SHOP-2-02 (BR-BH-01, 22, 23, 24, BR-DM-01)

### File đã sửa / thêm
- `backend/config/settings.py`: khối biến §2.3 đủ cả đợt (`SHOP_*`, `VOUCHER_MAX_PERCENT`, `SELLER_*` mới) + throttle `shop_lookup_token`, `shop_voucher_check` (chưa có view dùng, lô 3/3b).
- `backend/apps/common/slugs.py` (mới): `slugify_vi`, `unique_slug`. Dự phòng rỗng -> `group`.
- `backend/apps/catalog/models/items.py`: `ItemGroup.slug` (SlugField 80, unique, blank); `save()` tự sinh khi trống.
- Migration `catalog/0005_itemgroup_slug` (null), `0006_populate_itemgroup_slug` (RunPython, hàm slug chép vào file, idempotent, ngược = null), `0007_alter_itemgroup_slug_unique`.
- `backend/apps/catalog/items/services.py`: `stock_level`, `sale_unit`, `qty_rule`, `validate_line_qty`, `simple_sellable_qty`; `sellable_qty` giữ cho nội bộ.
- `backend/apps/catalog/items/shop_api.py`: `{groups, items}` + chi tiết, 404 `ITEM_NOT_FOUND`.
- `backend/apps/sales/orders/shop_errors.py` (mới): `ShopValidationError`, `InvalidQtyError`, `OutOfStockError`, `validation_error`.
- `backend/apps/sales/orders/services.py`: kiểm số lượng + kiểm tồn theo thành phần trước giữ chỗ; thua đua ở `reserve` -> `OutOfStockError`.
- `backend/apps/sales/orders/shop_api.py`: parse `items` -> 400 `VALIDATION` (`fields.items`) thay câu cũ.
- `backend/apps/inventory/batches/services.py`: câu lỗi `allocate_fefo`/`reserve` không còn mã lô và số kg (vẫn mã `BR-BH-02`).
- Test mới: `catalog/items/tests/{test_shop_catalog,test_itemgroup_slug_migration}.py`, `common/tests/test_slugs.py`, `sales/orders/tests/{test_shop_create,test_shop_create_race}.py`.
- Test cũ đổi theo contract (ngoài danh sách file lô nhưng bắt buộc để xanh): `catalog/items/tests/test_shop_api.py`, `sales/orders/tests/{test_f1_fefo,test_p5_bh15_round_total}.py`, `inventory/batches/tests/test_s1_expiry.py`, `common/tests/test_s3_locked_fields.py`, `accounts/demo/tests/test_d1_seed_demo.py`. `test_p5_*` đổi số lượng 0,125 kg thành 1,5 kg (giá 150.501đ) để vẫn kiểm làm tròn nửa đồng.

### Endpoint thực tế
- `GET /api/shop/catalog/` -> `{"groups":[{"slug","name","item_count"}],"items":[{item_code,name,item_type,unit,price,stock_level,min_qty,qty_step,group{slug,name},short_note,image}]}`; giá `"278000"`; chỉ GET.
- `GET /api/shop/catalog/<code>/` -> như một phần tử + `description,spec,storage,origin` (`""`) + `bundle_components[{item_code,name,qty_per_bundle,unit}]` (chỉ combo); 404 `{"code":"ITEM_NOT_FOUND","detail":"Không tìm thấy món này."}` cho mã lạ, ngưng bán, không giá.
- `POST /api/shop/orders/`: response thành công giữ nguyên (`order_code,total_amount,booked_expires_at`). Lỗi mới: `400 INVALID_QTY` (`lines[{item_code,min_qty,qty_step}]`, liệt kê mọi dòng sai), `400 OUT_OF_STOCK` (`lines[{item_code,stock_level:"out"|"short"}]`), `400 VALIDATION` (`fields.items`) khi qty không phải số hữu hạn.

### Lệch thiết kế / giả định
- Thứ tự lỗi: `INVALID_QTY` kiểm TRƯỚC `resolve_privacy_consent`, nên `SHOP_CLOSED`/`POLICY_CHANGED` (02b §3.3 #1, #4) đứng sau `INVALID_QTY`. Chuẩn hoá cùng `VALIDATION` đầy đủ và đổi mã `BR-BH-17` -> `SHOP_CLOSED` ở lô 3 (`consent.py` ngoài phạm vi lô 1).
- Thua đua lúc `reserve`: `OUT_OF_STOCK.lines` chỉ gồm dòng đang giữ chỗ thì thua (không tính lại mọi dòng).
- Món ngưng bán / không giá / mã lạ lúc đặt nay là `OUT_OF_STOCK` dòng `out` (02b §9); trước đây món ngưng bán vẫn đặt được.
- `description` trả `""` ở lô 1 dù cột có dữ liệu (lô 2b mới mở, có kiểm chữ BR-DM-25).
- Slug để `blank=True` vì `save()` tự sinh; ERP nhập slug thủ công là lô 2b.

### Điều còn nợ
- Chạy test đua Postgres (`test_shop_create_race.py`, 2 ca) trên DB cloud: máy này SQLite nên skip. **Nợ chạy Postgres.**
- `apps.common.tests.test_standard_names::test_no_banned_phrase_in_user_facing_string_literals` đỏ ở lần chạy `apps.common` vì `apps/content/management/commands/load_shop_content.py` (mkt-brand): chữ 'Production' dòng 85, 'TTL' dòng 135. Không thuộc lô BE.
- `check_naming.py` exit 1 hiện chỉ do file frontend của fe-dev; backend không vi phạm.

### Kiểm chứng (chạy tuần tự, lượt này)
Trước: 2243 tests OK (skipped=1) cho `apps.catalog apps.sales apps.inventory apps.accounts apps.reports` (trước khi sửa mô hình).
```
$ cd backend && .venv/bin/python manage.py test apps.catalog apps.sales apps.inventory apps.accounts apps.reports
Ran 2296 tests in 158.408s
OK (skipped=3)

$ .venv/bin/python manage.py makemigrations --check --dry-run
No changes detected

$ python3 scripts/check_naming.py   # backend sạch; còn lỗi ở frontend/ (app/gioi-thieu, components/ui/Button.tsx, features/catalog/groupIcon.ts, lib/mock.ts) thuộc fe-dev/mkt-brand
```

### Sửa sau review lô 1
- M1: `validate_line_qty` bắt `InvalidOperation` và chặn qty > 1.000.000 (`MAX_LINE_QTY`); "1e30", "1e999999999", số 80 chữ số, "-0", "1e-30", nhiều chữ số thập phân đều trả 400 (INVALID_QTY/OUT_OF_STOCK), không 500. Test: `InvalidQtyTests.test_review_m1_huge_or_odd_numbers_never_500`, mở rộng `test_validate_line_qty_rules_ac2_of_story_2_02`.
- Low: README `apps/catalog/items` sửa `sellable_qty` là nội bộ, Shop dùng `stock_level`.

## Lô 2b (BE) — SHOP-2b-01, SHOP-2b-02 (BR-DM-25, BR-PQ-04)

**File sửa:** `backend/apps/catalog/models/items.py`, `migrations/0008_item_shop_info.py` (thêm `short_note`/`spec`/`storage`/`origin`), `items/public_text.py` (mới), `items/serializers.py`, `items/api.py`, `items/shop_api.py`, test mới `items/tests/test_shop_info.py` (27 ca); sửa 2 test cũ: `test_shop_catalog.py` (description nay công khai), `pricing/tests/test_r14_pricing.py` (thêm `slug` vào tập field nhóm).

**Contract ERP (đúng 02b §3.10):**
- `GET/POST/PATCH /api/catalog/items/` thêm `short_note`(≤60) `spec`/`storage`/`origin`(≤500) `description`(≤2000). Chỉ `owner` ghi (manager/warehouse_staff/delivery_staff/customer_service 403). Lỗi 400 theo trường: `{"spec": ["Không ghi giá trong thông tin món. Giá lấy từ bảng giá."]}`, SĐT "Không ghi số điện thoại trong thông tin món.", mã lô "Không ghi mã lô trong thông tin món.", độ dài "Tối đa 60 ký tự.".
- `GET/POST/PATCH /api/catalog/item-groups/` thêm `slug`. Lỗi: "Đường dẫn đã dùng cho nhóm khác." / "Chỉ dùng chữ thường không dấu, số và dấu gạch ngang." / "Không được để trống." (PATCH). POST bỏ trống slug thì tự sinh.
- Shop công khai: `GET /api/shop/catalog/` có `short_note` thật; `GET /api/shop/catalog/<code>/` có `short_note`, `description`, `spec`, `storage`, `origin` thật.
- AuditLog: `update_item` `changes={"fields":[tên trường]}` (không chép chữ; không ghi khi không đổi); `update_itemgroup` `changes={"slug":{"from","to"}}`. FE cần nhãn `update_item`, `update_itemgroup` ở `auditModel.ts`.

**Lệch thiết kế:** (1) thêm kiểm cụm "nhà cung cấp / tên tàu / ngày nhập / nhập lô" (BR-DM-25 cấm, 02b chỉ liệt kê 3 kiểm) với lỗi "Không ghi nhà cung cấp, tên tàu hay ngày nhập lô trong thông tin món."; (2) regex mã lô không phân biệt hoa thường.

**Nợ / rủi ro:** `Item.description` cũ trong DB (kể cả production) nay hiện công khai trên Shop; cần Lộc/Duy rà ghi chú nội bộ trước khi deploy (bản ghi cũ không bị kiểm lại tới khi sửa). 

**Kiểm chứng:** `manage.py test apps.catalog apps.sales apps.accounts` -> Ran 1695 tests OK (skipped=3); `makemigrations --check --dry-run` -> No changes detected; `check_naming.py` OK.

### Lô 2b (BE) — bổ sung allowlist
`apps/common/tests/test_auditlog_note_no_free_text.py::AiScrubCoversFreeTextFieldsTests` đòi mọi field tên `note/reason/description` hoặc chứa các từ đó phải nằm trong danh sách lọc AI hoặc allowlist có lý do. `catalog.Item.short_note` (0008) được thêm vào `ALLOWED_UNSCRUBBED` như `Item.description`: chữ công khai về món, không dữ liệu khách; audit `update_item` chỉ ghi tên trường (đã có test `test_2b01_ac6_audit_update_item_records_field_names_only`).

### Sửa sau review lô 2 (BE)
- H1: `items/shop_api.py` `_safe_text` chạy `public_text_error` LÚC ĐỌC cho `short_note` (list + detail) và `description/spec/storage/origin` (detail); ô vi phạm trả `""`, khoá giữ, ô sạch không bị ảnh hưởng. Test `PublicReadTimeFilterTests` (ghi qua ORM "Giá vốn 180 nghìn, gọi 0901234567", mã lô, tàu, nhà cung cấp; kiểm toàn chuỗi JSON).
- L1: `catalog/admin.py` `ItemAdminForm` kiểm độ dài + `public_text_error` cho 5 ô.
- L2: `public_text.py` thêm số hiệu tàu `XX-12345` (2 chữ hoa + 4-6 số, lỗi nhóm "nhà cung cấp/tàu/ngày nhập") và cụm "giá vốn" (lỗi giá). Chữ "tàu" đứng riêng vẫn được phép (tránh báo nhầm).
- Chưa làm (tuỳ chọn): lệnh `check_public_item_text` để Lộc rà dữ liệu cũ.
