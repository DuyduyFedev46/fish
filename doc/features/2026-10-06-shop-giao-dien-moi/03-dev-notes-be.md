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

## Lô 3+4 (BE) — SHOP-3-01, SHOP-3-02, SHOP-4-05 (BR-BH-25, 26, 27, 29, BR-TT-19, BR-HT-12; 02b §3.3, §3.4, §3.5, §3.11, §4)

**File sửa:** `apps/sales/models/orders.py` + migration `sales/0020_salesorder_client_request_id` (`UUIDField` null, unique); `apps/sales/orders/{services,shop_api,consent,customer_notices,shop_labels}.py`; mới `lookup_token.py`, `shop_state.py`, `shop_payload.py`; `apps/sales/payments/shop_api.py` (§3.5, không đụng `checkout.py`); `apps/common/{throttling,formatting}.py` (thêm `ShopLookupTokenThrottle`, `body_dict`, `iso_utc`); `config/api_urls.py` (`shop/orders/lookup/`, gỡ GET `shop/orders/<code>/`); `config/settings.py` (`SHOP_CANCEL_POLICY_URL` mặc định đổi sang `/pages/?slug=doi-tra#xu-ly-tien`); đổi tên `mask_phone_last4` thành `mask_phone_tail` (`common/pii.py`, `delivery/labels/services.py`, test) để `grep phone_last4` sạch.

**Contract thực tế (đúng 02b):**
- `POST /api/shop/orders/` 201 (lần đầu) / 200 (gửi lại cùng `client_request_id`): `order_code, status, subtotal, discount{source,code,amount}, total_amount, booked_expires_at, server_now, hold_minutes, lines[{item_code,name,unit,qty,amount}], lookup_token`. Tiền chuỗi nguyên đồng, giờ UTC `Z`, `Cache-Control: no-store`. `lines[].amount` là thành tiền gộp trước giảm; `discount.amount = subtotal − total_amount`; `discount.source` là `"promo"` khi có giảm, `code` luôn `null` (mã giảm giá là lô 3b).
- Thứ tự lỗi: 503 `SHOP_CLOSED` → 400 `VALIDATION{fields: client_request_id|name|phone|delivery_address|items|consent}` → (đơn cũ 200) → 400 `INVALID_QTY` → 409 `POLICY_CHANGED` → 400 `OUT_OF_STOCK`. Mã `BR-BH-17` đã bỏ. Ô đồng ý chưa tick nay là `VALIDATION.fields.consent`. Khoá `phone` cấp ngoài bị bỏ (chỉ `customer.phone`). SĐT chuẩn hoá `^0\d{9}$` rồi mới lưu.
- `POST /api/shop/orders/lookup/` body `{order_code, phone}` hoặc `{order_code, token}` (token ưu tiên). 200 đủ khoá §3.4: `order_code,status,state,status_label,placed_at,paid_at,delivered_at,booked_expires_at,server_now,hold_minutes,payment_pending_minutes,delivery{step,step_label}|null,lines,subtotal,discount,total_amount,cancel_notice,late_payment,lookup_token`. Mọi ca sai (mã, SĐT, token đơn khác, token hỏng) cùng 404 `ORDER_NOT_FOUND`; token quá hạn 401 `TOKEN_EXPIRED`; thiếu SĐT và token 400 `VALIDATION`. GET cũ trả 404.
- `state` ∈ `awaiting_payment|hold_expired|expired|cancelled|preparing|delivering|delivery_failed|completed` đúng bảng §3.4.2. Ca ngoài bảng: `PROCESSING` + phiếu `COMPLETED` nhưng đơn chưa Hoàn tất (còn phiếu khác) → `delivering`; `PAID`/`PROCESSING` không phiếu → `preparing`.
- `cancel_notice` (§3.4.3): `scope, reason_code, reason_label, cancelled_amount, message, hotline, policy_url`; mã lý do lạ/OTHER/rỗng → `OTHER` + "Cá Về đã huỷ đơn này"; không khoá `refund*`, không chữ "hoàn" trong `message`.
- Checkout (§3.5): 404 `{code:"ORDER_NOT_FOUND", detail:"Không tìm thấy đơn."}`; 400 `{code:"CHECKOUT_UNAVAILABLE", detail:"Chưa mở được trang thanh toán. Thử lại.", reason:<mã BusinessError>}`.
- Throttle: tra bằng SĐT dùng `shop_lookup_ip` 20/phút + `shop_lookup_order` 10/giờ (khoá = mã đơn IN HOA từ body, băm sha256); tra bằng token dùng riêng `shop_lookup_token` 60/phút/IP.

**Giả định / lệch nhỏ:** (1) `client_request_id` là tuỳ chọn (vắng thì không chống trùng) vì nhiều caller cũ chưa gửi; FE lô 3+4 luôn gửi. (2) Thứ tự lỗi theo bảng 02b §3.3: `INVALID_QTY` (#3) đứng TRƯỚC `POLICY_CHANGED` (#4); chỉ `SHOP_CLOSED` được đưa lên đầu (câu "POLICY_CHANGED trước INVALID_QTY" trong phiếu giao khác bảng 02b, em theo bảng). (3) `apps/ai/policy/rules.py` còn khoá `phone_last4` trong danh sách chặn khoá cá nhân của AI (phòng thủ, test AI dùng), nên `grep phone_last4 backend/apps` còn các dòng đó và vài test "needle"; không còn trong code sản phẩm hay endpoint. (4) Test cũ dùng GET 4 số cuối đã chuyển sang POST ở sales/delivery/accounts/common (nội dung `cancel_notice` cũ với `refund`, "Đã hoàn tiền", hạn hoàn đã thay theo BR-HT-12).

**Đề xuất (chưa làm, đổi contract):** fe-dev xin cờ boolean "đang chờ xác nhận" thay vì dò chữ trong `delivery.step_label`. 02b §3.4 không có chỗ cho khoá này. Gợi ý nhỏ nhất: thêm `delivery.awaiting_confirmation: true|false` (true khi phiếu `CONFIRMING`). Cần techlead duyệt rồi sửa 02b; em không tự thêm vì FE đang bám contract.

**Nợ:** test đua Postgres `ShopCreateSameRequestIdRaceTests.test_parallel_same_request_id_one_order` viết xong, SQLite skip, nợ chạy cloud. `scripts/naming_baseline.json` chưa `--update` (1 file giảm vi phạm do đổi tên test; ngoài phạm vi thư mục).

## Lô 3b (BE) — SHOP-3b-01, 3b-03, 3b-04 + nợ review lô 3+4 (BR-DM-17…24, BR-BH-15, 27; 02b §2.2, §3.3, §3.4, §3.8, §3.9, §4)

**File sửa/mới:** mới `apps/catalog/models/vouchers.py`, `apps/catalog/vouchers/{services,api,shop_api,serializers}.py` + `README.md` + `tests/`; migration `catalog/0009_voucher`, `catalog/0010_grant_manage_voucher` (Group `owner`, có chiều ngược), `sales/0021_voucherredemption`, `sales/0022_salesorder_payment_started_at`; mới `apps/sales/models/vouchers.py`, `apps/sales/orders/voucher_redemptions.py`; sửa `apps/sales/orders/{services,shop_api,shop_payload,shop_state,shop_errors,customer_notices}.py`, `apps/sales/payments/{services,shop_api}.py`, `apps/sales/models/orders.py`, `apps/accounts/capabilities/registry.py` (việc `manage_voucher`, không `owner_only`), `apps/accounts/auth/services.py` (nhãn), `apps/common/throttling.py` (`ShopVoucherCheckThrottle`), `config/api_urls.py`. Settings không phải sửa (đã khai ở lô 1). Test cũ chỉnh theo contract mới: bộ khoá tra đơn (+`payment_pending_since`), `delivery` (+`awaiting_confirmation`), `test_privacy_consent` (+model `VoucherRedemption`), allowlist `Voucher.disabled_note` ở `test_auditlog_note_no_free_text`.

**Contract thực tế (đúng 02b §3.3, §3.8, §3.9):**
- `POST /api/shop/vouchers/check/` `{code?, items:[{item_code,qty}]}` → 200 `{code, valid, reason_code, subtotal, auto_discount_amount, discount_amount, missing_amount, applied{source,amount}, total_after, terms|null}`. `code` rỗng/vắng/không phải chuỗi → `code:null, valid:null`. `terms` = `{kind, value, max_discount(AMOUNT→null), min_order_amount("0"=không có), starts_at, ends_at, customer_terms}`, có khi hợp lệ, `MIN_ORDER`, `BETTER_PROMO`; `null` khi `INVALID|EXPIRED|USED_UP`. Không số lượt, không mã khác. Lỗi: 400 `VALIDATION{fields.items}` (rỗng, trùng, qty rác, quá `SHOP_MAX_ORDER_LINES`, món không còn bán), 400 `INVALID_QTY`, 429 `throttled` (20/phút/IP). Kiểm mã KHÔNG kiểm tồn.
- `POST /api/shop/orders/` nhận thêm `voucher_code` (chuỗi, tuỳ chọn; rỗng/null = không mã; kiểu khác chuỗi → 400 `VALIDATION.fields.voucher_code`). Lỗi `400 {code:"VOUCHER_INVALID", detail:"Mã giảm giá không còn dùng được.", reason_code:"INVALID|EXPIRED|MIN_ORDER|USED_UP|BETTER_PROMO", missing_amount?:"44000"}` (chỉ MIN_ORDER có `missing_amount`); thứ tự #5 trước OUT_OF_STOCK; không tạo đơn, không giữ chỗ, không giữ lượt. Thành công: `discount:{source:"voucher",code:"CAVE10",amount:"50000"}`, `lines[].amount` vẫn là gộp, `total_amount` = tổng sau giảm. Tra đơn trả cùng khối `discount` (kể cả sau khi lượt đã nhả, vì giá đóng băng).
- **Hoà hay ưu đãi tự động lớn hơn → `VOUCHER_INVALID BETTER_PROMO`** (không tạo đơn, không tính lượt); FE gửi lại không `voucher_code` thì đơn tính ưu đãi tự động (theo B8/C6 của 02a).
- ERP `/api/catalog/vouchers/` (mọi endpoint `catalog.manage_voucher`, 401/403; DELETE và PUT → 405): `GET ?status=running|scheduled|paused|expired|used_up&page=` (20/trang, `{count,next,previous,results}`), `POST`, `GET <id>/`, `PATCH <id>/`, `POST <id>/disable/ {reason,note}`, `POST <id>/enable/`, `GET <id>/redemptions/` (4 khoá `order_code, discount_amount, at, state(held|used|released)`). Đối tượng mã đúng 18 khoá §3.9 (`status` tính theo thứ tự paused, expired, used_up, scheduled, running). Lỗi: `VALIDATION{fields:{tên_ô:câu}}`, `FIELD_LOCKED{fields:[…]}`, `UNFAVORABLE_CHANGE{fields:[…]}` (câu "Tắt mã này và tạo mã mới."), enable → `EXPIRED`|`USED_UP`. Giờ vào nhận ISO có múi giờ (không múi giờ coi là giờ VN). Số tiền/`value` ra chuỗi nguyên đồng.
- Quyền: chỉ `owner` có sẵn; Quản lý nhận được qua màn Phân quyền (việc "Quản lý mã giảm giá", mục Bán hàng).
- AuditLog: `create_voucher` (mọi trường trước→sau, trừ `customer_terms`), `update_voucher` (từng trường trước→sau; `customer_terms` chỉ `{"changed":true}`), `disable_voucher` (`reason_code`, `note_marker`, KHÔNG chép `note`), `enable_voucher`.

**Nợ lô 3+4 đã xử lý:**
- M1: `delivery.awaiting_confirmation: bool` (true khi phiếu giao mới nhất `CONFIRMING`); khối `delivery` có 3 khoá `step, step_label, awaiting_confirmation`.
- M2: `ShopCreateSameRequestIdWaiterTests` (Postgres): luồng chính mở `atomic` + `create_order` chưa commit, luồng phụ `place_order` chờ unique index, sau 0,5 s commit → `(đơn cũ, False)`, `qty_reserved` +1 một lần; thêm ca người đầu rollback thì người chờ tạo đơn bình thường.
- M3: `shop_state.has_payment_transaction` dùng `customer_notices.late_payment_total` (một nguồn duy nhất, bỏ dòng nghi trùng): tự huỷ mà mọi giao dịch nghi trùng → `state:"expired"`, `late_payment:false`, `cancel_notice:null`.
- L1: log mã đơn qua `_loggable_code` (chỉ `A-Z0-9-`, ≤ 32 ký tự). L2: view dùng `timezone.now()`, bỏ alias `_body`; `parse_lines` thành hàm công khai (dùng cho kiểm mã).
- **Mốc D3 — tên field cuối: `payment_pending_since`** (ISO UTC `Z` hoặc `null`) trong tra đơn. Nguồn: cột mới `SalesOrder.payment_started_at` (nullable, không phải dữ liệu cá nhân, migration `sales/0022`), ghi khi `POST /api/shop/orders/<code>/checkout/` thành công cho đơn còn `BOOKED` (mỗi lần mở cổng ghi đè = lần gần nhất); tra đơn chỉ trả khi `status == BOOKED`, ngược lại `null`. FE đếm "Đã chờ" = `server_now − payment_pending_since` (cùng đồng hồ server); `null` thì chưa mở cổng. Lý do thêm cột: không có nơi nào khác lưu thời điểm này (02b §4 không liệt kê, em ghi để techlead thấy).

**Lệch/giả định (cần techlead xem):**
1. `mark_used` đặt trong `payments.issue_invoice` (cùng giao dịch lập hoá đơn) thay vì riêng nhánh MATCHED của `_record_payment`, vì `_issue_and_close` (Chủ xác nhận từ các khoản thiếu, Q9) cũng lập hoá đơn; đặt riêng nhánh MATCHED thì đơn đó kẹt `held` mãi. Một dòng, idempotent (`UPDATE … WHERE state='HELD'`).
2. Kiểm mã khi tạo đơn có hai lần: kiểm nhanh không khoá (để lỗi #5 đứng trước OUT_OF_STOCK #6) rồi kiểm có thẩm quyền dưới khoá. Lượt thua đua luôn do lần dưới khoá quyết định.
3. `max_discount` và `min_order_amount` bắt buộc nguyên đồng; `total_uses` ≥ 1; sửa mã đang chạy: `customer_terms`, `starts_at`, `code`, `kind` khoá (FIELD_LOCKED), gửi lại đúng giá trị cũ thì coi như không đổi.
4. `disable`/`enable` idempotent: tắt mã đã tắt giữ lý do đầu và không ghi nhật ký thêm; bật mã đang bật trả 200.
5. `compute_discount` luôn chừa ≥ 1 đồng (`subtotal − 1`) kể cả khi `VOUCHER_MAX_PERCENT` bị đặt 100.

**Lãi lỗ (điểm dừng — KHÔNG sửa `reports/services.py`):** lãi lỗ THEO KỲ đúng sẵn: `period_pnl` lấy `SalesInvoice.amount` (= tổng sau giảm) làm doanh thu, giá vốn là ảnh chụp `SalesInvoiceLineBatch.unit_cost` không đổi, kỳ cũ không đổi (5 test ở `apps/reports/tests/test_voucher_period_pnl.py`). Lãi lỗ THEO LÔ (`batch_pnl`) vẫn dùng `qty × rate` gộp nên không trừ mã (đúng 02b §8.1, đã có sẵn với PricingRule); một test ghi lại hiện trạng đó. Story 3b-04 AC9 vế "theo lô" cần Duy quyết riêng nếu muốn sửa.

**Chặn AI:** thêm `/api/catalog/vouchers/` vào `FORBIDDEN_PREFIXES` (`apps/ai/policy/rules.py`): registry lệnh AI tự khám phá router nên nếu không thêm, AI sẽ có 7 lệnh tạo/sửa/tắt mã (tiền rời túi). Snapshot lệnh AI không đổi. Sửa thêm `accounts/audit/tests/test_s03_migration.py` (loại `catalog` khỏi danh sách app giữ nguyên khi lùi `accounts`, vì `catalog/0010` phụ thuộc `accounts/0013`).

**Nợ:** (a) test đua Postgres chưa chạy được ở máy (SQLite skip): `test_voucher_race.py` (4 ca: 5 luồng cuối lượt, 5 luồng/3 lượt không vượt, người chờ khoá mã, job hết giờ song song không deadlock) và `test_shop_create_race.py::ShopCreateSameRequestIdWaiterTests` (2 ca) — điều phối chạy trên DB test cloud. (b) Lưu ý contract: `fields` của `FIELD_LOCKED`/`UNFAVORABLE_CHANGE` là danh sách, của `VALIDATION` là dict (đúng 02b).

## Sửa sau review lô 3b + CI
- **CI:** `.github/workflows/backend-tests.yml` (push mọi nhánh + pull_request, `permissions: contents: read`): job Postgres 16 (service tạm, mật khẩu giả, `DATABASE_URL` tới `cangca_ci`, Python 3.12 theo Dockerfile, `makemigrations --check`, `manage.py test --noinput` tuần tự, tóm tắt dòng `Ran N tests` vào Summary) và job SQLite. Env giả: `SEPAY_ENV=SANDBOX`, `AI_ENABLED=0`, `DJANGO_DEBUG=1`. YAML đã parse bằng python yaml; chưa chạy trên GitHub (chưa push). Cách đọc kết quả: `doc/ops/moi-truong.md` mục "Test PostgreSQL trên GitHub Actions".
- **L1:** `test_voucher_race.py` tìm đúng SĐT `09001…`.
- **L2:** ghi `payment_started_at` chuyển vào `payments/services.py::start_checkout` (gọi `checkout.build_checkout_params` rồi UPDATE); view chỉ gọi service. Không đụng `checkout.py` (02b §7.0 cấm, nên không theo gợi ý đặt trong `checkout.py`).
- **L3:** `apps/ai/registry/tests/test_forbidden_prefixes.py::VoucherForbiddenForAiTests` (4 đường dẫn bị cấm, registry không có lệnh voucher).
- **L5:** PATCH `is_active` → `FIELD_LOCKED` với câu "Dùng nút Tắt mã hoặc Bật lại mã…" ở mọi giai đoạn; test `IsActiveLockedTests`.
- Kiểm chứng: `manage.py test apps.catalog apps.sales apps.ai` (không có app `apps.payments`) → Ran 1534 tests, OK (skipped=9).

## Lãi lỗ theo lô trừ mã (BR-BC-04, Duy chốt 11/10)
- Sửa `backend/apps/reports/services.py`: hàm mới `_net_shares(line)`; `batch_pnl` dùng nó cho doanh thu và cho phần chứng từ đảo (đảo trọn một phân bổ thì đảo đúng phần thực thu). Giá vốn, API, migration: không đổi.
- Quy tắc (đã sửa sau review H1, xem mục dưới): chỉ đơn có mã đã dùng mới tính theo thực thu. Dòng của đơn đó: `SalesInvoiceLine.amount` chia theo kg phân bổ, làm tròn đồng bằng cộng dồn, phân bổ cuối nhận phần dư, nên tổng các lô = `amount`. Combo có giảm chia theo kg thành phần.
- "Từ nay / kỳ đã chốt": không có snapshot hay khoá kỳ; `batch_pnl` và `period_pnl` tính lại từ dữ liệu gốc. Chỉ đơn có `VoucherRedemption` USED (từ lô 3b, mới lên staging) đổi cách tính, nên mọi lô/kỳ có sẵn, kể cả đơn có PricingRule, không đổi số. Lô staging đã chốt mà có đơn dùng mã sẽ đổi số: dữ liệu demo, chấp nhận. Không đổi trạng thái đơn.
- Test: `apps/reports/tests/test_voucher_period_pnl.py` (lô trừ giảm, đơn không mã, dòng ăn 2 lô tổng khớp và tròn đồng, kỳ khớp lô, huỷ sau thanh toán đảo đúng phần thực thu). Quyền xem lãi lỗ lô không đổi (test_api/cost_leak có sẵn).
- Nợ: PricingRule không phải mã và combo không giảm vẫn dùng `qty × rate` như cũ (02b §8.1).

### Sửa sau review lãi lỗ theo lô (review lô 5c: H1, M1, L1, L2)
- H1: lập luận trước ("dòng amount != qty×rate là giảm mã") sai, vì PricingRule cũng ghi giảm vào `amount`. Nay `batch_pnl` lấy một lần tập đơn có `VoucherRedemption.state=USED` và chỉ các đơn đó chia theo thực thu; đơn khác (kể cả PricingRule, lô đã chốt) giữ `qty × rate`. Không thêm field, không migration.
- M1: `_net_shares` ghi nhớ theo `line.pk` trong một lần `batch_pnl`; test đếm truy vấn không tăng theo số phân bổ.
- L1: chứng từ đảo một phần chia theo tỉ lệ `cl.qty / silb.qty` của phần doanh thu đã ghi. L2: docstring test đã sửa. L4 (mkt-brand): không đụng.
- Test mới: PricingRule không mã = 600.000; lô đã chốt có đơn PricingRule không đổi; mã + PricingRule = tiền thực thu của hoá đơn.
- Câu hỏi mở cho Duy: có trừ cả ưu đãi tự động cho đơn từ nay không (cần mốc ngày bằng setting). Chưa có thì giữ như trên.

### Sửa sau QA lô 7
- L11: bỏ khoá `gateway: "SEPAY"` khỏi JSON `POST /api/shop/orders/<mã>/checkout/` (`apps/sales/payments/checkout.py`). Frontend không đọc khoá này (grep chỉ thấy tên file `gateway.ts`). Các khoá còn lại (`checkout_url`, `fields`, `merchant`...) giữ nguyên. Test `test_qa_l11_...`.
- L12: throttle `public_content` nâng 120/min thành 600/min mỗi IP (`config/settings.py`, đổi được bằng env `THROTTLE_PUBLIC_CONTENT`), vì mỗi trang gọi khoảng 3 lần và mạng dùng chung dễ dính 429. Test `test_qa_l12_...`; test throttle cũ vẫn xanh.
