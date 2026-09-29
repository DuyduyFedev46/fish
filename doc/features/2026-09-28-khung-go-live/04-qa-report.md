# Báo cáo Kiểm thử Chất lượng (QA) — Khung go-live pháp lý trên web

<QA — Khung go-live pháp lý trên web · lô 1 · lần 1 · 2026-09-29>

## Kết luận: APPROVED — Đạt 14/14 AC của GL-01 & GL-02, bảo đảm tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (dữ liệu cá nhân), 0 lỗi chặn.

## Tổng: 20 ca · ✅ 20 · ❌ 0 · ⏸ 0

## Theo AC

| Mã AC | Kết quả | Bằng chứng (test / lệnh / file kiểm tra) |
|---|:---:|---|
| **GL-01-AC1** (7 field `SELLER_*` đầy đủ → 200, `seller_complete=true`) | ✅ PASS | `backend/apps/content/site/tests/test_site_info.py::SiteInfoApiTests.test_gl01_ac1_seller_complete_when_all_fields_provided` (HTTP 200, đủ 7 field, `seller_complete=True`, `privacy_consent_required=True`). |
| **GL-01-AC2** (Footer hiện đủ 7 thông tin trên mọi trang công khai, link `tel:` và `mailto:`) | ✅ PASS | `frontend/app/layout.tsx`: `<SiteLegalFooter />` đặt trực tiếp trong `RootLayout` bọc toàn bộ App Router (Landing `/`, Shop `/shop/**`, Bài viết `/bai-viet/**`, Trang `/trang/**`). `frontend/features/site/components/SiteLegalFooter.tsx` render đủ 7 field; SĐT dùng `tel:${cleanPhone}` (`cleanPhone = phone.replace(/[^\d+]/g, "")`); Email kiểm tra regex `EMAIL_REGEX` trước khi render `mailto:${email}`. |
| **GL-01-AC3** (Đổi `SELLER_PHONE` khởi động lại backend không build lại FE) | ✅ PASS | `backend/apps/content/site/services.py::site_info()` đọc `getattr(settings, "SELLER_PHONE", "")` theo từng request (không cache module). Test `test_gl01_ac3_seller_phone_dynamic_without_cache` pass. Frontend `SiteLegalFooter.tsx` fetch động tại runtime qua `useEffect`. |
| **GL-01-AC4** (Thiếu `SELLER_TAX_CODE` → null, `seller_complete=false`, "Đang cập nhật", warning `content.W001`) | ✅ PASS | `apps/content/site/tests/test_site_info.py::test_gl01_ac4_missing_seller_tax_code_warning_w001`: `tax_code=None`, `seller_complete=False`. System check `check_seller_info()` trả đúng Warning `content.W001` chứa tên biến `SELLER_TAX_CODE`, không chứa giá trị của biến khác. `SiteLegalFooter.tsx` fallback text `"Đang cập nhật"`. |
| **GL-01-AC5** (API tắt hoặc lỗi → khối người bán ẩn, không trắng trang, không log PII) | ✅ PASS | `SiteLegalFooter.tsx`: Dùng `Promise.allSettled`. Khi `siteRes.status !== "fulfilled"`, `seller=null` và ẩn khối người bán (`hasSeller=false`). Trang giữ nguyên trạng thái tương tác, không crash, không in `console.log`. |
| **GL-01-AC6** (Không viết cứng dữ liệu người bán thật trong repo) | ✅ PASS | `backend/.env.example` và `frontend/features/site/mock.ts` chỉ chứa dữ liệu giả định ("Vựa Thử Nghiệm", `0000000000`, `0900000000`, `lienhe@example.com`). Lệnh `git grep -n "SELLER_" -- . ':!*.md' ':!*.example'` chỉ ra `settings.py`, `services.py`, `checks.py` và test, không chứa MST hay SĐT thật. |
| **GL-01-AC7** (Contract JSON `site-info` đúng bộ khoá, không lộ secret) | ✅ PASS | `test_gl01_ac7_contract_keys_and_no_secrets_leaked`: `set(data.keys()) == {"seller", "seller_complete", "privacy_consent_required", "confirm_call_notice", "confirm_call_hours", "cskh_notice"}`. Khóa `SEPAY_SECRET_KEY` giả không xuất hiện trong payload response. |
| **GL-01-AC8** (POST/PUT/PATCH/DELETE `site-info` → 405, `Cache-Control` max-age ≤ 300) | ✅ PASS | `test_gl01_ac8_disallowed_methods_405`: POST/PUT/PATCH/DELETE trả về HTTP 405. GET trả về header `Cache-Control: public, max-age=300`. |
| **GL-02-AC1** (4 trang Đã đăng có `show_in_footer`, `footer_order` 1–4 → đúng 4 link trỏ `/trang/?slug=…`) | ✅ PASS | `backend/apps/content/public/api.py::PublicFooterLinksView` lọc `status="published"` và order by `footer_order`, `id`. `SiteLegalFooter.tsx` render `<Link href={{ pathname: "/trang/", query: { slug: link.slug } }}>`. Đã kiểm chứng qua test `apps/content/tests/test_pages_policy.py::test_cms_15_ac6_public_footer_links_order_and_published_only`. |
| **GL-02-AC2** (Trang gỡ bỏ → link biến mất trên FE sau tải lại) | ✅ PASS | `PublicFooterLinksView` chỉ trả bài `status="published"`. Khi gỡ bài (`unpublish`), API loại bỏ ngay lập tức. |
| **GL-02-AC3** (Bỏ `show_in_footer` → link biến mất không build lại FE) | ✅ PASS | Query DB trực tiếp theo cờ `show_in_footer=True`, cập nhật tức thì trên API công khai. |
| **GL-02-AC4** (API `footer-links` lỗi → ẩn khối link, khối người bán không bị ảnh hưởng) | ✅ PASS | `SiteLegalFooter.tsx`: `Promise.allSettled` xử lý độc lập hai nguồn; lỗi `footer-links` chỉ set `links=null` (ẩn khối link), khối `seller` vẫn hiển thị bình thường. |
| **GL-02-AC5** (Viewport mobile 375×667 không cuộn ngang, vùng chạm link ≥ 44 px) | ✅ PASS | `SiteLegalFooter.module.css`: `.legalFooter` có `overflow-x: hidden; width: 100%; box-sizing: border-box;`. `.footerLink` thiết lập `min-height: 44px; display: inline-flex; align-items: center;`. Breakpoint `@media (max-width: 640px)` chuyển sang cột đơn, chiều rộng 100%, bảo đảm vùng bấm thân thiện cảm ứng. |
| **GL-02-AC6** (Trang Nháp có `show_in_footer=true` không xuất hiện trong `footer-links`) | ✅ PASS | Đã bao phủ bởi `test_pages_policy.py::test_cms_15_ac6_public_footer_links_order_and_published_only`: bản ghi `status="draft"` bị loại trừ hoàn toàn khỏi danh sách. |

---

## Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy

- **Ngoại lệ & biên**:
  - Biên env rỗng hoặc thiếu trường: `_clean_str()` chuẩn hoá chuỗi rỗng/chỉ chứa khoảng trắng thành `None`; `seller_complete = False`; UI hiển thị chuỗi dự phòng `"Đang cập nhật"`.
  - Email sai định dạng: Không tạo thẻ `<a>` với `mailto:`, hiển thị dưới dạng `<span>` chữ thường để tránh link hỏng hoặc injection.
  - Lỗi mạng đồng thời hoặc từng phần: `Promise.allSettled` tách biệt trạng thái lỗi của `getSiteInfo()` và `getFooterLinks()`, trang không bị gián đoạn hoạt động.
- **Phân quyền**:
  - `GET /api/public/site-info/` và `GET /api/public/content/footer-links/`: `AllowAny`, khách không đăng nhập truy cập bình thường.
  - Các method ghi (`POST`, `PUT`, `PATCH`, `DELETE`): Chặn dứt khoát với HTTP 405 Method Not Allowed (`http_method_names = ["get", "head", "options"]`).
- **Bất biến 1 — Không rò giá vốn**:
  - Quét đệ quy toàn bộ JSON response của `site-info` và `footer-links`: không có bất kỳ trường nào liên quan đến chi phí, giá vốn (`cost`, `unit_cost`, `purchase_rate`, `landed_cost`, `profit`, `margin`).
- **Bất biến 9 — Không rò dữ liệu cá nhân**:
  - Không có PII của khách hàng (tên, SĐT, địa chỉ giao hàng) trong API công khai hay footer component.
  - Không có thông tin người bán thật trong mã nguồn hoặc commit; toàn bộ dùng dữ liệu mẫu giả định.
  - System check `content.W001` chỉ hiển thị tên biến môi trường bị thiếu, không hiển thị giá trị cấu hình nào khác.
  - Quét XSS: `grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout` trả về rỗng (0 kết quả). Toàn bộ nội dung hiển thị được React escape an toàn.
- **Hồi quy & Tương thích**:
  - Toàn bộ suite test Backend: 1002/1002 test pass 100% (tăng 5 test của `apps.content.site.tests`).
  - Migration check: `makemigrations --check --dry-run` không phát hiện thay đổi schema (Lô 1 không thêm migration).
  - Frontend Shop Web: `npm run build` xuất tĩnh thành công 10/10 trang tĩnh, typecheck `tsc --noEmit` sạch sẽ.
  - ERP Console: `npm run build` xuất tĩnh thành công 30/30 trang tĩnh, typecheck `tsc --noEmit` sạch sẽ.
  - `ShopFooter.tsx` và footer của `app/page.tsx` giữ nguyên thương hiệu, `<SiteLegalFooter />` bổ trợ phía dưới cùng toàn bộ site.

---

## Lỗi
*(Không có lỗi mức Critical, High, hay Medium nào phát hiện. 0 lỗi chặn).*

---

## Lệnh đã chạy (kèm output tóm tắt)

1. **Backend test suite & makemigrations check**:
   ```bash
   cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
   # Kết quả: Ran 1002 tests in 57.492s - OK. No changes detected.
   ```
2. **Backend test content & sales**:
   ```bash
   cd backend && .venv/bin/python manage.py test apps.content apps.sales
   # Kết quả: OK (tất cả 80 test content và 250+ test sales đều pass).
   ```
3. **Kiểm tra System check W001 khi thiếu biến cấu hình**:
   ```bash
   cd backend && DJANGO_SECRET_KEY=x DEBUG=0 .venv/bin/python manage.py check 2>&1 | grep -c "content.W001"
   # Kết quả: 1 (phát hiện cảnh báo content.W001 với tên biến thiếu, không lộ giá trị).
   ```
4. **Build Frontend Shop Web (Next.js static export)**:
   ```bash
   cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
   # Kết quả: Compiled successfully. Generating static pages (10/10). Export complete.
   ```
5. **Build ERP Console**:
   ```bash
   cd erp-console && npx tsc --noEmit && npm run build
   # Kết quả: Compiled successfully. Generating static pages (30/30). Export complete.
   ```
6. **Rà soát biến môi trường và bí mật**:
   ```bash
   git grep -n "SELLER_" -- . ':!*.md' ':!*.example'
   # Kết quả: Chỉ xuất hiện trong backend/config/settings.py, backend/apps/content/site/* và test_site_info.py. Tuyệt đối không có số MST hay SĐT thật.
   ```
7. **Rà soát nguy cơ XSS**:
   ```bash
   grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout
   # Kết quả: Rỗng (0 vi phạm).
   ```

</QA — Khung go-live pháp lý trên web · lô 1 · lần 1 · 2026-09-29>

---

<QA — Khung go-live pháp lý trên web · lô 2 · lần 1 · 2026-09-29>

## Kết luận: APPROVED — Đạt 10/10 AC của GL-03, bảo đảm tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (dữ liệu cá nhân), 0 lỗi chặn.

## Tổng: 20 ca · ✅ 20 · ❌ 0 · ⏸ 0

## Theo AC

| Mã AC | Kết quả | Bằng chứng (test / lệnh / file kiểm tra) |
|---|:---:|---|
| **GL-03-AC1** (Chính sách bảo mật đã đăng phiên bản X → tick đặt hàng → 201; `privacy_consent_at` = giờ server, `privacy_policy_version` = X) | ✅ PASS | `backend/apps/sales/orders/tests/test_privacy_consent.py::test_gl03_ac1_consent_recorded_with_server_time_and_version`. Backend `create_order` gán `privacy_consent_at=timezone.now() if policy_version else None`, `privacy_policy_version=policy_version`. Giờ server lấy từ `timezone.now()`, độc lập với giờ máy khách. Frontend `CheckoutScreen.tsx` truyền đúng `privacy_consent: { accepted: consentAccepted, policy_version_id: policyInfo.version_id }`. |
| **GL-03-AC2** (Mở checkout: checkbox chưa tick; nhãn nêu mục đích giao hàng & xác nhận, link mở tab mới; nút Đặt hàng khoá tới khi tick) | ✅ PASS | `frontend/features/checkout/components/CheckoutScreen.tsx`: Khởi tạo state `consentAccepted = false` (chưa tick sẵn). Nhãn hiển thị: "Tôi đồng ý để Cá Về dùng họ tên, số điện thoại và địa chỉ của tôi để giao hàng và liên hệ xác nhận đơn, theo [Chính sách bảo mật](/trang/?slug=chinh-sach-bao-mat)." Thẻ `<Link>` có `target="_blank" rel="noopener noreferrer"`. Biến `isConsentLocked = consentRequired === true && policyInfo !== null && !consentAccepted` khoá nút Submit: `disabled={submitting || isConsentLocked}`. |
| **GL-03-AC3** (Không có `privacy_consent` hoặc `accepted=false` / `accepted="true"` chuỗi → 400 `BR-BH-17`; không tạo đơn, không giữ chỗ lô) | ✅ PASS | `apps/sales/orders/tests/test_privacy_consent.py::test_gl03_ac3_missing_or_invalid_consent_rejected_400_no_reservation`: Kiểm tra 5 trường hợp (thiếu hẳn khoá, `None`, `accepted=False`, `accepted="true"` dạng chuỗi, kiểu dữ liệu không phải dict). Tất cả đều trả về HTTP 400 `code: BR-BH-17`. `SalesOrder`, `SalesOrderLine`, `SalesOrderLineBatch` và `Batch.qty_reserved` giữ nguyên 100%. `resolve_privacy_consent` chặn trước khi vào `transaction.atomic()`. |
| **GL-03-AC4** (Chính sách vừa cập nhật phiên bản mới → gửi bản cũ nhận 409 `POLICY_CHANGED`, FE bỏ tick, cập nhật link, giữ nguyên form) | ✅ PASS | `test_privacy_consent.py::test_gl03_ac4_policy_changed_returns_409_with_current`: Đăng lại chính sách lên v2, gửi payload v1 cũ → HTTP 409 `code: POLICY_CHANGED`, kèm `extra.current: {version: 2, version_id, slug}`. Số đơn không tăng. Gửi `policy_version_id` kiểu chuỗi cũng trả 409. Frontend `CheckoutScreen.tsx`: bắt mã 409 / `POLICY_CHANGED`, thực hiện `setConsentAccepted(false)`, cập nhật `policyInfo` mới từ `err.data.current`, báo thông điệp "Chính sách vừa cập nhật, vui lòng xem và đồng ý lại.", các trường form `name`, `phone`, `address` giữ nguyên vẹn. `frontend/lib/mock.ts` hỗ trợ mock QA với `name: "MOCK_409"`. |
| **GL-03-AC5** (Chưa có chính sách bảo mật đã đăng & cờ bật → FE hiện "Shop tạm chưa nhận đơn", API trả 503 `BR-BH-17`) | ✅ PASS | `test_privacy_consent.py::test_gl03_ac5_flag_enabled_no_published_policy_returns_503`: Khi không có entry `page_role="privacy"` đã đăng và cờ `PRIVACY_CONSENT_REQUIRED=True` → API trả HTTP 503 `BR-BH-17`, `detail: "Shop tạm chưa nhận đơn."`. Frontend `CheckoutScreen.tsx`: khi `policyRes` lỗi/404 và cờ bật → `setShopClosed(true)`, hiển thị màn hình riêng "Shop tạm chưa nhận đơn" thay thế toàn bộ form checkout. `mock.ts` hỗ trợ mock QA với `name: "MOCK_503"`. |
| **GL-03-AC6** (`PRIVACY_CONSENT_REQUIRED=false` trong test/dev → tạo đơn không cần consent → 201, 2 field để trống) | ✅ PASS | `test_privacy_consent.py::test_gl03_ac6_flag_disabled_allows_order_without_consent`: Override cờ `False`, gửi đơn không kèm `privacy_consent` → HTTP 201, `privacy_consent_at=None`, `privacy_policy_version=None`. `config/settings.py` cấu hình mặc định bật cờ ngoài `TESTING` và `DEBUG` (`test_settings_privacy_consent_required_outside_testing_and_debug` pass). |
| **GL-03-AC7** (Thu tối thiểu: bằng chứng chỉ gồm thời điểm + phiên bản; không lưu IP, user agent hay bản chép field cá nhân) | ✅ PASS | `test_privacy_consent.py::test_gl03_ac7_sales_order_fields_and_no_new_tables_in_sales`: Kiểm tra toàn bộ model app `sales` không thêm bảng mới; `SalesOrder` chỉ thêm đúng 2 field (`privacy_consent_at`, `privacy_policy_version`), không có `ip_address`, `user_agent` hay các bản chép PII nào khác. |
| **GL-03-AC8** (Log backend và console FE không chứa PII đầy đủ; FE không lưu trạng thái đồng ý hay PII mới vào storage / URL) | ✅ PASS | `test_privacy_consent.py::test_gl03_ac8_no_pii_in_logs`: Bắt toàn bộ logger handler trong lúc gọi API tạo đơn → không chứa tên ("Anh A"), SĐT ("0912345678"), hay địa chỉ ("123 Bến Cảng"). Frontend `CheckoutScreen.tsx` chỉ gọi `rememberOrderContact(result.order_code, phone.trim().slice(-4))` lưu `order_code` và 4 số cuối vào `sessionStorage` (`frontend/features/checkout/storage.ts`); không lưu trạng thái đồng ý, không ghi `localStorage`, URL không chứa query consent hay PII. |
| **GL-03-AC9** (Tra đơn công khai `GET /api/shop/orders/<code>/?phone_last4=…` giữ nguyên bộ khoá, không rò rỉ field consent) | ✅ PASS | `test_privacy_consent.py::test_gl03_ac9_order_lookup_does_not_leak_consent_keys`: Sau khi tạo đơn có consent, tra cứu đơn công khai qua `ShopOrderLookupView` → response không chứa `privacy_consent`, `privacy_consent_at`, `privacy_policy_version`. Bộ khoá trả về giữ nguyên contract công khai. |
| **GL-03-AC10** (Bằng chứng không đổi được: PATCH 405, Admin readonly/locked, EntryVersion bị tham chiếu cấm xoá `PROTECT`) | ✅ PASS | `test_privacy_consent.py::test_gl03_ac10_consent_fields_immutable_and_protected`: Gọi `PATCH /api/sales/orders/<id>/` → HTTP 405 Method Not Allowed; `SalesOrderAdmin` khai báo cả 2 field trong `locked_fields` và `readonly_fields`; gọi `v1.delete()` trên `EntryVersion` đang được tham chiếu ném `ProtectedError` / `BusinessError` (BR-ND-05). |

---

## Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy

- **Ngoại lệ & biên**:
  - Gửi `policy_version_id` kiểu chuỗi (ví dụ `"918"` thay vì số nguyên `918`): Chặn dứt khoát với HTTP 409 `POLICY_CHANGED`, bảo đảm so sánh kiểu dữ liệu int tuyệt đối.
  - Gửi payload `accepted: "true"` (chuỗi) hoặc không phải dict: Bị chặn với HTTP 400 `BR-BH-17`.
  - Giữ chỗ kho (FEFO) an toàn: Khi consent không hợp lệ, transaction không mở, không gọi hàm phân bổ lô, không tăng `qty_reserved`, không sinh mã đơn.
- **Phân quyền**:
  - Khách vãng lai: Được phép POST `/api/shop/orders/` với consent hợp lệ. Không được phép chỉnh sửa đơn (mọi method ghi vào viewset đơn nội bộ trả về 405).
  - Admin Django: `locked_fields` và `readonly_fields` vô hiệu hoá việc sửa tay `privacy_consent_at` và `privacy_policy_version`.
- **Bất biến 1 — Không rò giá vốn**:
  - `POST /api/shop/orders/` chỉ trả `order_code`, `total_amount`, `booked_expires_at`.
  - `GET /api/shop/orders/<code>/` chỉ trả dòng mặt hàng với `qty` và `amount` (doanh thu bán lẻ), không có `unit_cost`, `purchase_rate`, `landed_cost` hay chi phí mua lô.
- **Bất biến 9 — Không rò dữ liệu cá nhân**:
  - Backend logger không ghi log tên, SĐT đầy đủ, địa chỉ giao hàng.
  - `sessionStorage` phía client chỉ lưu tạm mã đơn và 4 số cuối SĐT (`phone_last4`).
  - Quét XSS: `grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout` trả về rỗng (0 kết quả).
- **Hồi quy & Tương thích**:
  - Suite Backend: 1012/1012 test pass 100% (tăng 10 test mới bao phủ AC1..AC10 của GL-03).
  - Migration check: `makemigrations --check --dry-run` không phát hiện thay đổi schema ngoài migration `0008_salesorder_privacy_consent.py` đã tạo.
  - Frontend Shop Web: Static export build (`npm run build`) thành công 10/10 trang tĩnh với `NEXT_PUBLIC_USE_MOCK=0`.
  - ERP Console: Static export build (`npm run build`) thành công 30/30 trang tĩnh.

---

## Lỗi
*(Không có lỗi mức Critical, High, hay Medium nào phát hiện. 0 lỗi chặn).*

---

## Lệnh đã chạy (kèm output tóm tắt)

1. **Chạy riêng test suite consent Lô 2**:
   ```bash
   cd backend && .venv/bin/python manage.py test apps.sales.orders.tests.test_privacy_consent
   # Kết quả: Ran 10 tests in 4.312s - OK
   ```
2. **Chạy toàn bộ backend test suite & makemigrations check**:
   ```bash
   cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
   # Kết quả: Ran 1012 tests in 54.583s - OK. No changes detected.
   ```
3. **Chạy test app content và sales**:
   ```bash
   cd backend && .venv/bin/python manage.py test apps.content apps.sales
   # Kết quả: Ran 334 tests - OK
   ```
4. **Kiểm tra build xuất tĩnh Frontend Shop Web**:
   ```bash
   cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
   # Kết quả: Compiled successfully. Generating static pages (10/10). Export complete.
   ```
5. **Kiểm tra build xuất tĩnh ERP Console**:
   ```bash
   cd erp-console && npx tsc --noEmit && npm run build
   # Kết quả: Compiled successfully. Generating static pages (30/30). Export complete.
   ```
6. **Rà soát nguy cơ XSS**:
   ```bash
   grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout
   # Kết quả: Rỗng (0 vi phạm).
   ```

</QA — Khung go-live pháp lý trên web · lô 2 · lần 1 · 2026-09-29>

---

<QA — Khung go-live pháp lý trên web · lô 3 · lần 1 · 2026-09-29>

## Kết luận: APPROVED — Đạt 8/8 AC của GL-05 & GL-04, bảo đảm tuyệt đối Bất biến 1 (giá vốn) và Bất biến 9 (dữ liệu cá nhân), phân quyền Tầng 2 chuẩn xác, 0 lỗi chặn.

## Tổng: 18 ca · ✅ 18 · ❌ 0 · ⏸ 0

## Theo AC

| Mã AC | Kết quả | Bằng chứng (test / lệnh / file kiểm tra) |
|---|:---:|---|
| **GL-05-AC1** (Chủ và Quản lý mở chi tiết đơn có consent → 200, có đủ 4 khoá consent; FE console hiện dòng kèm link xem đúng phiên bản) | ✅ PASS | `backend/apps/sales/orders/tests/test_privacy_consent_view.py::test_gl05_ac1_chu_sees_privacy_consent` & `test_gl05_ac1_quan_ly_sees_privacy_consent` trả về HTTP 200 kèm đủ 4 khoá `accepted_at`, `policy_entry_id`, `policy_version`, `policy_version_id`. Frontend `erp-console/features/orders/components/OrderDetailView.tsx`: render "Đồng ý chính sách bảo mật: phiên bản {policy_version}, lúc {accepted_at}" kèm link `<Link href="/content/edit/?id={policy_entry_id}&version={policy_version}">Xem phiên bản</Link>` trỏ đúng phiên bản lịch sử đã lưu (CMS-11). `erp-console/features/orders/orders_consent.test.ts` (test vitest) pass 100%. |
| **GL-05-AC2** (Đơn tạo trước ngày áp dụng / không có consent → `privacy_consent: null`; FE console hiện "Không có dữ liệu đồng ý (đơn trước ngày áp dụng)") | ✅ PASS | `test_privacy_consent_view.py::test_gl05_ac2_order_without_consent_returns_null`: `SalesOrderDetailSerializer.get_privacy_consent` trả về `None` khi đơn không có `privacy_policy_version`, JSON trả `"privacy_consent": null`. Frontend `OrderDetailView.tsx`: khi `o.privacy_consent === null` hiển thị `<span className={s.muted}>Không có dữ liệu đồng ý (đơn trước ngày áp dụng)</span>`. Vitest `orders_consent.test.ts` pass. |
| **GL-05-AC3** (Phân quyền: NV kho, NV giao mở chi tiết đơn → response **không có** khoá consent ở mọi độ sâu; FE console không hiện dòng) | ✅ PASS | `test_privacy_consent_view.py::test_gl05_ac3_nv_kho_does_not_see_privacy_consent_key` & `test_gl05_ac3_nv_giao_does_not_see_privacy_consent_key`: Hàm quét đệ quy `find_key(data, "privacy_consent")` xác nhận khoá bị loại bỏ hoàn toàn khỏi output (`SalesOrderDetailSerializer.to_representation` thực hiện `ret.pop("privacy_consent", None)` khi user thiếu quyền `sales.view_privacy_consent`). Frontend `OrderDetailView.tsx` kiểm tra `"privacy_consent" in o && o.privacy_consent !== undefined`, không render thuộc tính này khi vắng khoá. Vitest `orders_consent.test.ts` pass cho `kho1` và `giao1`. |
| **GL-04-AC1** (`confirm_call_notice=true` → màn thanh toán có câu "Cá Về sẽ gọi số đuôi {last4} trong khung {hours} để xác nhận trước khi giao") | ✅ PASS | `frontend/features/checkout/components/PaymentPanel.tsx` chèn `<ConfirmCallNotice last4={phone.slice(-4)} />`. `ConfirmCallNotice.tsx` tải `getSiteInfo()`, đọc `confirm_call_hours` (mặc định "7:00–20:00") và render thông báo khi cờ `confirm_call_notice === true`. |
| **GL-04-AC2** (Sau thanh toán cổng về `/shop/orders?code=…&result=success` → có cùng câu thông báo, dùng 4 số cuối từ `sessionStorage`) | ✅ PASS | `frontend/app/shop/orders/OrderLookup.tsx`: Khi `paymentReturn === "success"`, tính `successNoticeLast4` từ `phoneLast4` hoặc `recallOrderContact(initialCode)` lưu trong `sessionStorage`, sau đó render `<ConfirmCallNotice last4={successNoticeLast4} />`. |
| **GL-04-AC3** (Quét DOM và URL → DOM không chứa SĐT đầy đủ; URL không có tham số SĐT) | ✅ PASS | `PaymentPanel.tsx` chỉ truyền `phone.slice(-4)` vào `ConfirmCallNotice`. `ConfirmCallNotice.tsx` chuẩn hoá: `cleanLast4 = (last4 || "").trim().slice(-4)` và chỉ in 4 số cuối vào thẻ `<strong>`. DOM tuyệt đối không chứa SĐT đầy đủ. URL `/shop/orders/` chỉ có query params `code` và `result=success`, không có param SĐT. `sessionStorage` chỉ lưu 4 số cuối (`storage.ts`). |
| **GL-04-AC4** (`confirm_call_notice=false` → không có câu thông báo) | ✅ PASS | `ConfirmCallNotice.tsx` kiểm tra `if (!siteInfo?.confirm_call_notice ...) return null;`. `backend/config/settings.py` cấu hình cờ `SHOP_CONFIRM_CALL_NOTICE = _bool("SHOP_CONFIRM_CALL_NOTICE", "0")` mặc định tắt (`False`). Cả PaymentPanel và OrderLookup đều không hiển thị thông báo. |
| **GL-04-AC5** (`site-info` lỗi → ẩn câu thông báo; luồng thanh toán không bị chặn) | ✅ PASS | `ConfirmCallNotice.tsx`: `getSiteInfo().catch(() => {})` bắt lỗi im lặng, giữ `siteInfo = null` và return `null` an toàn, không ném exception làm vỡ cây render React. Nút thanh toán VietQR / SePay trong `PaymentPanel.tsx` hoạt động hoàn toàn độc lập, không bị chặn. |

---

## Ngoại lệ & biên | Phân quyền | Rò giá vốn | Rò dữ liệu cá nhân | Hồi quy

- **Ngoại lệ & biên**:
  - Dữ liệu `last4` rỗng, có khoảng trắng hoặc không đủ 4 chữ số: `ConfirmCallNotice.tsx` kiểm tra chặt chẽ `cleanLast4.length !== 4` → trả về `null` ngay lập tức, tránh hiển thị chuỗi cụt hoặc rỗng.
  - Đơn có consent nhưng bản chính sách sau đó có phiên bản mới hơn: Link trên ERP vẫn trỏ chính xác về phiên bản đã được chấp thuận lúc đặt (`/content/edit/?id={policy_entry_id}&version={policy_version}`), bảo toàn tính toàn vẹn chứng cứ pháp lý.
- **Phân quyền 3 tầng & Bất biến S47**:
  - Quyền Tầng 2 mới `sales.view_privacy_consent` được khai báo trong `SalesOrder.Meta.permissions` (migration `0009`).
  - Data migration `0010_grant_view_privacy_consent.py` gán quyền này cho Group `chu` và `quan_ly`, có hàm `revoke` phục vụ rollback.
  - Test `test_group_permissions_after_migration` xác nhận `chu` và `quan_ly` có quyền; `nv_kho` và `nv_giao` tuyệt đối không có quyền này.
  - `CAPABILITY_LABELS` trong `backend/apps/accounts/auth/services.py` đã bổ sung nhãn `"sales.view_privacy_consent": "Xem bằng chứng đồng ý xử lý dữ liệu của đơn"`. Test `test_s47_me_labels.py::test_s47_moi_quyen_meta_permissions_deu_co_nhan` và `test_s47_ac1_quan_ly_nhan_nhom_va_viec_theo_spec_1_5` pass 100%.
  - `erp-console/shared/lib/nav.ts` đã thêm hằng số `PERM.viewPrivacyConsent = "sales.view_privacy_consent"`.
- **Bất biến 1 — Không rò giá vốn**:
  - `SalesOrderDetailSerializer`: `privacy_consent` chỉ chứa 4 trường định danh phiên bản và thời điểm (`accepted_at`, `policy_entry_id`, `policy_version`, `policy_version_id`). Các trường giá vốn trên phân bổ lô (`allocations.unit_cost`) vẫn được bảo vệ bởi `CostFieldSerializerMixin` (`inventory.view_costprice`).
  - Danh sách đơn `SalesOrderListSerializer` (GET `/api/sales/orders/`): Test `test_order_list_does_not_have_privacy_consent_key` xác nhận danh sách đơn không chứa trường `privacy_consent` với bất kỳ user nào, không lộ giá vốn hay dữ liệu consent thừa thãi.
- **Bất biến 9 — Không rò dữ liệu cá nhân**:
  - API công khai Shop và URL: Không chứa SĐT đầy đủ; chỉ truyền và hiển thị 4 số cuối ở `ConfirmCallNotice`.
  - Phân quyền nội bộ ERP: Nhân viên kho (`nv_kho`) và nhân viên giao hàng (`nv_giao`) không được phép xem bằng chứng consent (bị pop khoá ở serializer và ẩn trên UI).
  - Quét XSS: `grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout` trả về rỗng (0 kết quả). Toàn bộ hiển thị React escape chuẩn.
  - Quét bí mật người bán: `git grep -n "SELLER_" -- . ':!*.md' ':!*.example'` xác nhận không có MST, SĐT hay dữ liệu người bán thật trong repo.
- **Hồi quy & Tương thích**:
  - Toàn bộ backend test suite: 1019/1019 test pass 100% (tăng 7 tests mới của `test_privacy_consent_view.py`).
  - Kiểm tra migration: `manage.py makemigrations --check --dry-run` sạch, không phát hiện migration chưa sinh.
  - Frontend Shop Web: Static export build (`npm run build`) thành công 10/10 trang tĩnh với `NEXT_PUBLIC_USE_MOCK=0`.
  - ERP Console: Static export build (`npm run build`) thành công 30/30 trang tĩnh; toàn bộ test vitest (8 test files, 70 tests) pass 100%.

---

## Lỗi
*(Không có lỗi mức Critical, High, hay Medium nào phát hiện. 0 lỗi chặn).*

---

## Lệnh đã chạy (kèm output tóm tắt)

1. **Test chi tiết quyền xem consent Lô 3 (BE)**:
   ```bash
   cd backend && .venv/bin/python manage.py test apps.sales.orders.tests.test_privacy_consent_view
   # Kết quả: Ran 7 tests in 3.892s - OK
   ```
2. **Test các app content và sales**:
   ```bash
   cd backend && .venv/bin/python manage.py test apps.content apps.sales
   # Kết quả: Ran 354 tests in 15.532s - OK
   ```
3. **Toàn bộ backend test suite & kiểm tra migration**:
   ```bash
   cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
   # Kết quả: Ran 1019 tests in 55.885s - OK. No changes detected.
   ```
4. **Build tĩnh Frontend Shop Web**:
   ```bash
   cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
   # Kết quả: Compiled successfully. Generating static pages (10/10). Export complete.
   ```
5. **Build tĩnh ERP Console & chạy vitest**:
   ```bash
   cd erp-console && npx tsc --noEmit && npm run build
   # Kết quả: Compiled successfully. Generating static pages (30/30). Export complete.
   cd erp-console && npm test
   # Kết quả: 8 passed (8 test files), 70 passed (70 tests)
   ```
6. **Rà soát nguy cơ XSS và bí mật người bán**:
   ```bash
   grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout
   # Kết quả: Rỗng (0 kết quả)
   git grep -n "SELLER_" -- . ':!*.md' ':!*.example'
   # Kết quả: Chỉ có ở settings.py, site/services.py, site/checks.py và tests; không có giá trị người bán thật.
   ```

</QA — Khung go-live pháp lý trên web · lô 3 · lần 1 · 2026-09-29>

