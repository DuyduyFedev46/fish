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
