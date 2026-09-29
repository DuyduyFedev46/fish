# Ghi chú phát triển — Khung go-live pháp lý trên web

- **Nhánh làm việc**: `main`
- **Số test gốc BE**: 997 test(s) (chạy lúc bắt đầu Lô 1: `manage.py test` passed 100%, 0 issues).
- **Số test sau Lô 1**: 1002 test(s) (tăng 5 test `apps.content.site.tests.test_site_info`).
- **Số test sau Lô 2**: 1012 test(s) (tăng 10 test `apps.sales.orders.tests.test_privacy_consent`).

---

## Lô 1: GL-01 Thông tin người bán & GL-02 Link các trang chính sách

### Kế hoạch & Thực hiện

#### 1. Backend (GL-01)
- **Cấu hình `backend/config/settings.py`**:
  - Khối biến người bán: `SELLER_NAME`, `SELLER_BUSINESS_TYPE`, `SELLER_REG_NO`, `SELLER_TAX_CODE`, `SELLER_ADDRESS`, `SELLER_PHONE`, `SELLER_EMAIL` (mặc định rỗng `""`).
  - Cờ đồng ý bảo mật: `PRIVACY_CONSENT_REQUIRED = _bool("PRIVACY_CONSENT_REQUIRED", "0" if (TESTING or DEBUG) else "1")` (G1).
  - Cờ thông báo gọi xác nhận: `SHOP_CONFIRM_CALL_NOTICE = _bool("SHOP_CONFIRM_CALL_NOTICE", "0")` (G2).
  - Khung giờ gọi: `SHOP_CONFIRM_CALL_HOURS = os.getenv("SHOP_CONFIRM_CALL_HOURS", "7:00–20:00")`.
- **Dịch vụ `backend/apps/content/site/services.py`**:
  - Hàm `site_info()` dựng dict tường minh từ `settings`, strip khoảng trắng, rỗng -> `None`.
  - Tính `seller_complete = all(v is not None for v in seller.values())`.
  - Tuyệt đối không lặp biến hay dùng `settings.__dict__` để tránh lộ bí mật (GL-01-AC7).
- **System check `backend/apps/content/site/checks.py`**:
  - `check_seller_info()` kiểm tra 7 biến `SELLER_*`, trả Warning `content.W001` chỉ chứa **tên biến** bị thiếu, không in giá trị bất kỳ biến nào khác (GL-01-AC4).
  - Đăng ký qua hàm bọc `_seller_check` trong `backend/apps/content/apps.py::ready()`, bỏ qua khi `settings.TESTING` để tránh ồn suite test.
- **API `backend/apps/content/site/api.py`**:
  - `SiteInfoView` kế thừa `APIView`, `AllowAny`, `throttle_classes = [PublicContentThrottle]`.
  - `http_method_names = ["get", "head", "options"]` (POST/PUT/PATCH/DELETE -> 405).
  - Trả về dữ liệu `site_info()` gộp với `cskh_notice` (kết hợp liên hồ sơ CSKH Lô 3, không mở endpoint thứ 2).
  - Header `Cache-Control: public, max-age=300`.
- **Tài liệu & Môi trường**:
  - `backend/.env.example`: thêm placeholder giả định ("Vựa Thử Nghiệm", `0900000000`...).
  - `doc/ops/moi-truong.md`: thêm mục biến môi trường Khung go-live pháp lý kèm lời nhắc quan trọng (G1): phải đăng trang chính sách bảo mật trước khi bật API production.
- **Tests BE**:
  - `backend/apps/content/site/tests/test_site_info.py`: 5 tests pass 100%:
    - `test_gl01_ac1_seller_complete_when_all_fields_provided`: 7 trường hợp lệ -> `seller_complete=True`.
    - `test_gl01_ac3_seller_phone_dynamic_without_cache`: đổi `SELLER_PHONE` qua `override_settings` có hiệu lực ngay không cache.
    - `test_gl01_ac4_missing_seller_tax_code_warning_w001`: thiếu biến -> field `null`, `seller_complete=False`, `check_seller_info()` trả đúng Warning `content.W001` chỉ chứa tên biến.
    - `test_gl01_ac7_contract_keys_and_no_secrets_leaked`: tập khoá đúng contract, bí mật `SEPAY_SECRET_KEY` không bị lộ vào response.
    - `test_gl01_ac8_disallowed_methods_405`: POST/PUT/PATCH/DELETE -> 405, GET có `Cache-Control: public, max-age=300`.

#### 2. Frontend (GL-01, GL-02)
- **Types `frontend/features/site/types.ts`**:
  - Định nghĩa `SellerInfo`, `SiteInfoResponse`, `FooterLinkItem`, `PrivacyPolicyResponse`.
- **Mock `frontend/features/site/mock.ts`**:
  - Dữ liệu mock "Vựa Thử Nghiệm", MST `0000000000`, 4 link chính sách (`chinh-sach-bao-mat`, `chinh-sach-kiem-hang-va-doi-tra`, `chinh-sach-thanh-toan`, `chinh-sach-giao-hang`).
- **API `frontend/features/site/api.ts`**:
  - `getSiteInfo()`, `getFooterLinks()`, `getPrivacyPolicy()` (fallback mock khi `NEXT_PUBLIC_USE_MOCK=1`).
- **Component `SiteLegalFooter`**:
  - `frontend/features/site/components/SiteLegalFooter.tsx` & `SiteLegalFooter.module.css`.
  - `"use client"`, tải song song qua `Promise.allSettled([getSiteInfo(), getFooterLinks()])`.
  - Khối người bán: 7 dòng thông tin, `null` hiển thị "Đang cập nhật", SĐT link `tel:`, email link `mailto:` (chỉ khi đúng định dạng regex), ẩn khối khi API lỗi (GL-01-AC5), không log console.
  - Khối link: các link trỏ `/trang/?slug=…`, vùng chạm chiều cao $\ge 44$ px, không cuộn ngang ở viewport 375 px (GL-02-AC5), ẩn khối khi API lỗi độc lập với khối người bán (GL-02-AC4).
  - Không sử dụng `dangerouslySetInnerHTML`.
- **Chèn layout `frontend/app/layout.tsx`**:
  - Chèn `<SiteLegalFooter />` một lần sau `{children}`, áp dụng cho toàn bộ các trang công khai (Landing, Shop, bài viết, trang nội dung, 404). Giữ nguyên `ShopFooter.tsx` và footer của `app/page.tsx`.

---

### Lệnh kiểm chứng Lô 1

```bash
# 1. Toàn bộ test suite backend + makemigrations check
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Kết quả: Ran 1002 tests in 57.492s - OK - No changes detected

# 2. Test apps.content apps.sales
cd backend && .venv/bin/python manage.py test apps.content apps.sales
# Kết quả: OK

# 3. System check W001
cd backend && DJANGO_SECRET_KEY=x DEBUG=0 .venv/bin/python manage.py check 2>&1 | grep -c "content.W001"
# Kết quả: 1 (chỉ in tên biến bị thiếu, không in giá trị nào)

# 4. Frontend static export build
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
# Kết quả: ✓ Generating static pages (10/10) - Compiled successfully

# 5. ERP Console build
cd erp-console && npx tsc --noEmit && npm run build
# Kết quả: ✓ Generating static pages (30/30) - Compiled successfully

# 6. Rà soát biến và bảo mật
git grep -n "SELLER_" -- . ':!*.md' ':!*.example'
# Kết quả: chỉ settings.py, không có giá trị thật
grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout
# Kết quả: rỗng (0 kết quả)
```

---

## Lô 2: GL-03 Ô đồng ý xử lý dữ liệu cá nhân ở checkout

### Kế hoạch & Thực hiện

#### 1. Backend (GL-03)
- **Model `backend/apps/sales/models/orders.py`**:
  - `SalesOrder` thêm 2 field:
    - `privacy_consent_at`: DateTimeField(null=True, blank=True, editable=False)
    - `privacy_policy_version`: ForeignKey("content.EntryVersion", on_delete=PROTECT, null=True, blank=True, editable=False, related_name="+")
  - Không thêm trường IP, user agent hay bản chép dữ liệu cá nhân nào (GL-03-AC7).
- **Migration `backend/apps/sales/migrations/0008_salesorder_privacy_consent.py`**:
  - Đánh số `0008` (vì `0007_alter_refund_created_by.py` đã dùng trước đó bởi hồ sơ khác).
  - Dependencies gồm `("content", "0002_grant_content_perms")` và `("sales", "0007_alter_refund_created_by")`.
- **Dịch vụ `backend/apps/sales/orders/consent.py`**:
  - Lớp lỗi `PolicyChanged(BusinessError)`: `http_status = 409`.
  - Lớp lỗi `ShopClosed(BusinessError)`: `http_status = 503`.
  - Hàm `resolve_privacy_consent(payload)`:
    - Đọc chính sách hiện hành qua `current_policy_version("privacy")`.
    - Nếu không có chính sách và `PRIVACY_CONSENT_REQUIRED=True` -> raise `ShopClosed("Shop tạm chưa nhận đơn.", code="BR-BH-17")`.
    - Nếu `PRIVACY_CONSENT_REQUIRED=False` và `payload=None` -> trả về `None` (cho phép test cũ chạy).
    - Kiểm tra `payload` là dict có `accepted=True` -> nếu không raise `BusinessError("Vui lòng đồng ý chính sách xử lý dữ liệu cá nhân.", code="BR-BH-17")`.
    - So sánh `policy_version_id` tuyệt đối với `current.pk` (chặn cả dạng chuỗi) -> nếu lệch raise `PolicyChanged` kèm `extra={"current": {"version": current.version, "version_id": current.pk, "slug": current.entry.slug}}`.
- **Dịch vụ `backend/apps/sales/orders/services.py`**:
  - `create_order` thêm keyword `privacy_consent=None`.
  - Gọi `resolve_privacy_consent(privacy_consent)` trước khi mở `transaction.atomic()`.
  - Gán `privacy_consent_at = timezone.now() if policy_version else None` và `privacy_policy_version = policy_version`.
- **API `backend/apps/sales/orders/shop_api.py`**:
  - `ShopOrderCreateView.post`: truyền `privacy_consent=d.get("privacy_consent")`.
  - Bỏ khối `try/except BusinessError` cục bộ để `apps.common.api.exception_handler` tự map và trả đúng `http_status` kèm `extra` (409 trả `current`, 503 trả detail, 400 trả BR-BH-17).
- **Admin `backend/apps/sales/admin.py`**:
  - `SalesOrderAdmin` thêm 2 field vào `locked_fields` và `readonly_fields`.
- **Tests BE `backend/apps/sales/orders/tests/test_privacy_consent.py`**:
  - 10 tests pass 100% bao phủ AC1..AC10 của GL-03:
    - `test_gl03_ac1_consent_recorded_with_server_time_and_version`
    - `test_gl03_ac3_missing_or_invalid_consent_rejected_400_no_reservation`
    - `test_gl03_ac4_policy_changed_returns_409_with_current`
    - `test_gl03_ac5_flag_enabled_no_published_policy_returns_503`
    - `test_gl03_ac6_flag_disabled_allows_order_without_consent`
    - `test_gl03_ac7_sales_order_fields_and_no_new_tables_in_sales`
    - `test_gl03_ac8_no_pii_in_logs`
    - `test_gl03_ac9_order_lookup_does_not_leak_consent_keys`
    - `test_gl03_ac10_consent_fields_immutable_and_protected`
    - `test_settings_privacy_consent_required_outside_testing_and_debug`

#### 2. Frontend (GL-03)
- **Kiểu dữ liệu `frontend/lib/types.ts`**:
  - `CreateOrderPayload`: thêm trường `privacy_consent?: { accepted: boolean; policy_version_id: number; };`.
  - `ApiError`: mở rộng thêm `code?: string` và `data?: any`.
  - `SiteInfo`: thêm `privacy_consent_required?: boolean; confirm_call_notice?: boolean; confirm_call_hours?: string;`.
- **API Client `frontend/lib/api.ts`**:
  - `apiFetch`: gắn thêm `code` và `data` vào đối tượng `ApiError` khi ném lỗi HTTP khác 2xx.
- **Mock `frontend/lib/mock.ts`**:
  - `mockCreateOrder`: hỗ trợ giả lập 409 `POLICY_CHANGED`, 503 `BR-BH-17` và kiểm tra consent cho QA.
- **Màn Checkout `frontend/features/checkout/components/CheckoutScreen.tsx`**:
  - Tải song song `getSiteInfo()` và `getPrivacyPolicy()`.
  - Mặc định checkbox chưa tick, nhãn nêu rõ mục đích xử lý dữ liệu và link tab mới tới `/trang/?slug=...`.
  - Nút "Đặt hàng" bị khoá khi chưa tick đồng ý (GL-03-AC2).
  - Chưa có chính sách đã đăng và cờ bật -> hiển thị màn hình "Shop tạm chưa nhận đơn" (GL-03-AC5).
  - Khi API trả 409 `POLICY_CHANGED` -> bỏ tick, cập nhật phiên bản chính sách mới, báo lỗi "Chính sách vừa cập nhật, vui lòng xem và đồng ý lại", toàn bộ thông tin form được giữ nguyên vẹn (GL-03-AC4).
  - Tuyệt đối không lưu dữ liệu đồng ý vào storage/URL (GL-03-AC8).

---

### Lệnh kiểm chứng Lô 2

```bash
# 1. Toàn bộ test suite backend + makemigrations check
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Kết quả: Ran 1012 tests in 54.583s - OK - No changes detected

# 2. Test apps.sales và apps.content
cd backend && .venv/bin/python manage.py test apps.content apps.sales
# Kết quả: Ran 334 tests - OK

# 3. Frontend static export build
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
# Kết quả: ✓ Generating static pages (10/10) - Compiled successfully

# 4. ERP Console build
cd erp-console && npx tsc --noEmit && npm run build
# Kết quả: ✓ Generating static pages (30/30) - Compiled successfully

# 5. Rà soát bảo mật XSS
grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout
# Kết quả: rỗng (0 kết quả)
```

