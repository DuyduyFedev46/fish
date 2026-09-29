# Ghi chú phát triển — Khung go-live pháp lý trên web

- **Nhánh làm việc**: `main`
- **Số test gốc BE**: 997 test(s) (chạy lúc bắt đầu Lô 1: `manage.py test` passed 100%, 0 issues).
- **Số test sau Lô 1**: 1002 test(s) (tăng 5 test `apps.content.site.tests.test_site_info`).

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
