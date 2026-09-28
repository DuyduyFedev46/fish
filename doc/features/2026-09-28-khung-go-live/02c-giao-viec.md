# Giao việc — Khung go-live pháp lý trên web
> Claude (Tech Lead) · 2026-09-28 · Trạng thái: **NHÁP — chờ Duy đổi SẴN SÀNG CODE**
> Người hiện thực: Gemini CLI / Antigravity theo `AGENTS.md`, lệnh `/lam-tinh-nang 2026-09-28-khung-go-live`.
> Nhánh làm việc: **`main`** (sau khi hồ sơ `2026-09-28-sua-loi-bao-mat` đã merge vào `main`). Nếu hồ sơ đó **chưa** merge thì làm trên `wip/autosave` và ghi rõ trong `03-dev-notes.md`.

## Điều kiện đầu vào
- `02-stories.md`: ĐÃ DUYỆT (Duy 28/09 — chốt scope qua câu hỏi) · `02b-tech-design.md`: ĐÃ DUYỆT (Duy 28/09 — theo chốt scope)
- **Phải xong trước:**
  - Hồ sơ `2026-09-28-sua-loi-bao-mat` đã merge vào `main`.
  - Hồ sơ `2026-09-28-cms-viet-bai`: **Lô 5 (CMS-15) ☑** trước Lô 1–2 ở đây; **Lô 7 (CMS-11) ☑** trước Lô 3. Mặc định bắt đầu khi CMS **XONG**. Kiểm: `02c-giao-viec.md` của CMS có ☑ + mã commit ở các lô đó; `grep -n "def current_policy_version" backend/apps/content/entries/services.py` có kết quả. Không có → **dừng, báo Duy**.
- Trước Lô 1: `git pull`; chạy lệnh kiểm chứng BE, ghi số test gốc vào `03-dev-notes.md`.
- Câu G1–G4 dùng mặc định PO (🟡, `02b` §8): cờ `PRIVACY_CONSENT_REQUIRED` bật ngoài test/dev; `SHOP_CONFIRM_CALL_NOTICE` tắt; người bán qua env.
- Dữ liệu thử giả ("Vựa Thử Nghiệm", `0900000000`, `lienhe@example.com`). **Không** đặt giá trị người bán thật ở bất kỳ file nào trong repo.

## Lô
| ☐/☑ | Lô | Story | BE / FE | Được sửa (thư mục/file) | Không được đụng | Commit |
|---|---|---|---|---|---|---|
| ☐ | 1 | GL-01, GL-02 | BE ∥ FE | BE: `backend/apps/content/site/**` (mới), `backend/apps/content/apps.py` (**chỉ** đăng ký system check trong `ready()`), `backend/config/settings.py` (khối `SELLER_*`, `PRIVACY_CONSENT_REQUIRED`, `SHOP_CONFIRM_CALL_*`), `backend/config/api_urls.py` (`public/site-info/`), `backend/.env.example` (placeholder), `doc/ops/moi-truong.md` (**chỉ** thêm tên biến + nhắc G1, không giá trị thật). FE: `frontend/features/site/**` (mới), `frontend/app/layout.tsx` (**chỉ** chèn `<SiteLegalFooter />`) | `frontend/components/ShopFooter.tsx`, footer trong `frontend/app/page.tsx`, `frontend/firebase*.json`, `apps/content/entries/**`, `apps/content/public/**` (dùng, không sửa), mọi `migrations/`, `apps/sales/**` | — |
| ☐ | 2 | GL-03 | BE ∥ FE | BE: `backend/apps/sales/models/orders.py` (**chỉ thêm** 2 field), `backend/apps/sales/migrations/0007_salesorder_privacy_consent.py` (mới, số kế tiếp nếu đã dùng), `backend/apps/sales/orders/consent.py` (mới), `backend/apps/sales/orders/services.py` (**chỉ** `create_order`: thêm kw `privacy_consent=None` + gọi `resolve_privacy_consent` + gán 2 field), `backend/apps/sales/orders/shop_api.py` (**chỉ** `ShopOrderCreateView.post`), `backend/apps/sales/admin.py` (**chỉ** readonly 2 field), test mới ở `backend/apps/sales/orders/tests/`. FE: `frontend/features/checkout/components/CheckoutScreen.tsx`, `frontend/features/site/**`, `frontend/lib/api.ts` (**chỉ** gắn `code`/`data` vào `ApiError` + hàm mới), `frontend/lib/types.ts`, `frontend/lib/mock.ts` | Luồng giữ chỗ/FEFO/thanh toán (`allocate_fefo`, `reserve`, `payments/**`), `ShopOrderLookupView`, `apps/content/**` (dùng, không sửa), migration đã có, `firebase*.json` | — |
| ☐ | 3 | GL-05, GL-04 | BE ∥ FE | BE: `backend/apps/sales/models/orders.py` (**chỉ** `Meta.permissions` thêm `view_privacy_consent`), `backend/apps/sales/migrations/0008_…`, `0009_grant_view_privacy_consent.py` (mới), `backend/apps/sales/orders/serializers.py` (**chỉ** `SalesOrderDetailSerializer` thêm `privacy_consent` theo quyền), test mới. FE ERP: `erp-console/features/orders/**` (dòng bằng chứng đồng ý), `erp-console/shared/lib/nav.ts` (**chỉ** thêm `PERM.viewPrivacyConsent`). FE web: `frontend/features/site/components/ConfirmCallNotice.tsx`, `frontend/features/checkout/components/PaymentPanel.tsx`, `frontend/app/shop/orders/OrderLookup.tsx` | `SalesOrderListSerializer`, `features/checkout/storage.ts` (dùng, không sửa), `apps/content/**`, migration đã có | — |

Chung cho mọi lô, **không được đụng**: `doc/decisions.md`, `01-analysis.md`, `02-stories.md`, `02b-tech-design.md`, `02c-giao-viec.md` (trừ ☑ + mã commit), `adapter/`, `backend/apps/ai/**`, test cũ (chỉ thêm; test cũ đỏ → **dừng hỏi**).

## Mỗi lô: điều kiện xong

### Lệnh kiểm chứng (chạy trong lượt, dán output tóm tắt vào `03-dev-notes.md`)
```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd backend && .venv/bin/python manage.py test apps.content apps.sales
cd backend && DJANGO_SECRET_KEY=x DEBUG=0 .venv/bin/python manage.py check 2>&1 | grep -c "content.W001"   # Lô 1: = 1 khi thiếu SELLER_*, output không có giá trị nào
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
cd erp-console && npx tsc --noEmit && npm run build                                  # Lô 3
git grep -n "SELLER_" -- . ':!*.md' ':!*.example'   # chỉ settings.py, content/site/*, test — không giá trị thật
grep -rn "dangerouslySetInnerHTML" frontend/features/site frontend/features/checkout   # phải rỗng
```
Lệnh `manage.py check` chạy trên máy dev, **không** trỏ DB staging/production.

### Test bắt buộc theo lô (chi tiết `02b` §6; mỗi AC có ít nhất 1 test mang mã AC)
- **Lô 1**
  - GL-01-AC1: `override_settings(SELLER_*=giả)` → 200, `seller` 7 field đúng, `seller_complete=true`.
  - GL-01-AC3: đổi `SELLER_PHONE` bằng `override_settings` → response đổi (không cache module).
  - GL-01-AC4: thiếu `SELLER_TAX_CODE` → field `null`, `seller_complete=false`; `check_seller_info()` trả 1 `Warning` id `content.W001`, message chứa `SELLER_TAX_CODE`, **không** chứa giá trị của biến khác.
  - GL-01-AC7: tập khoá đúng `02b` §3.1; đặt `SEPAY_SECRET_KEY="sepay-secret-gia"`, `DATABASE_URL` giả → chuỗi không có trong `resp.content`.
  - GL-01-AC8: POST/PUT/PATCH/DELETE → 405 (khách). `Cache-Control` `max-age ≤ 300`.
  - FE (Playwright, mock + staging build): GL-01-AC2 (footer đủ 7 dòng trên Landing, `/shop/`, `/shop/item/?code=…`, `/shop/checkout/`, `/shop/orders/`, `/bai-viet/`, `/trang/?slug=…`; `tel:`/`mailto:`), AC5 (API lỗi → ẩn khối, trang còn dùng được, console không in dữ liệu), AC6 (render mock "Vựa Thử Nghiệm"); GL-02-AC1…AC6 (4 link đúng thứ tự `/trang/?slug=`; gỡ / bỏ `show_in_footer` → biến mất không build lại; `footer-links` lỗi → khối người bán vẫn hiện; 375×667 không cuộn ngang, link ≥ 44 px; trang Nháp không có trong `footer-links` — test BE của CMS đã có, chạy lại).
- **Lô 2**
  - GL-03-AC1: có chính sách phiên bản X → 201; `privacy_consent_at` = giờ server (dùng `freeze`/so với `timezone.now()` ± 5 s, bỏ qua giờ client), `privacy_policy_version_id == X`.
  - GL-03-AC3: không `privacy_consent` / `accepted:false` / `accepted:"true"` → 400 `BR-BH-17`; số `SalesOrder`, `SalesOrderLine`, `SalesOrderLineBatch`, `Batch.qty_reserved` không đổi.
  - GL-03-AC4: đăng lại chính sách (phiên bản mới) rồi gửi `policy_version_id` cũ → 409 `POLICY_CHANGED`, `current` đúng; không đơn. `policy_version_id` dạng chuỗi → 409.
  - GL-03-AC5: `PRIVACY_CONSENT_REQUIRED=True`, không trang `privacy` Đã đăng → 503 `BR-BH-17`, không đơn.
  - GL-03-AC6: cờ `False`, không payload → 201, 2 field `None`.
  - GL-03-AC7: field của `SalesOrder` sau migration = cũ + đúng 2 field mới; không bảng mới trong `sales`.
  - GL-03-AC8: handler bắt log trong lúc tạo đơn → không tên/SĐT/địa chỉ giả; Playwright: `localStorage`/`sessionStorage` chỉ có `order_code` + 4 số cuối như cũ, URL không có dữ liệu cá nhân.
  - GL-03-AC9: tra đơn `set(resp.json())` bằng đúng tập khoá trước story.
  - GL-03-AC10: `PATCH /api/sales/orders/<id>/` → 405; `EntryVersion` bị tham chiếu `delete()` raise; Admin POST đổi 2 field → không đổi.
  - Settings: không `TESTING`, không `DEBUG` → `PRIVACY_CONSENT_REQUIRED is True` (test bằng hàm đọc env tách riêng, hoặc `importlib.reload` có kiểm soát).
  - Toàn bộ test Shop/đơn cũ xanh **không sửa**.
  - FE: GL-03-AC2 (ô chưa tick, nhãn nêu mục đích, link mở tab mới, nút khoá), AC4 (mock 409 → bỏ tick, link bản mới, form giữ nguyên), AC5 (mock 404 chính sách + cờ bật → "Shop tạm chưa nhận đơn").
- **Lô 3**
  - GL-05-AC1/AC2 (BE): `chu`, `quan_ly` → `privacy_consent` đúng 4 khoá / `null` với đơn cũ.
  - GL-05-AC3: `nv_kho`, `nv_giao` (phiếu giao được gán cho mình) → khoá `privacy_consent` **không có** ở mọi độ sâu; quyền `sales.view_privacy_consent` chỉ ở `chu`, `quan_ly` sau migrate.
  - GL-04-AC1…AC5 (FE, mock): cờ bật → câu có đúng 4 số cuối + khung giờ ở màn thanh toán và `/shop/orders/?code=…&result=success`; DOM và URL không SĐT đầy đủ; cờ tắt hoặc `site-info` lỗi → không câu, luồng không chặn.
  - FE ERP: dòng đồng ý + link tới phiên bản đúng (kể cả khi có phiên bản mới hơn); đơn cũ → câu "Không có dữ liệu đồng ý…".

### QA
- QA APPROVED (`04-qa-report.md`, mục theo lô): kiểm từng AC; token `chu`, `quan_ly`, `nv_kho`, `nv_giao`, khách; quét khoá cấm và dữ liệu cá nhân; giao diện 375×667.
- Commit sau APPROVED: `Lô <n> khung go-live: GL-xx …` → `git push origin <nhánh>`; đánh dấu ☑ + mã commit.
- **Không deploy.** Nhắc Duy trong báo cáo cuối: bật API production khi `PRIVACY_CONSENT_REQUIRED` bật thì phải **đăng trang chính sách bảo mật trước** (D4), và đặt `SELLER_*` thật trên Cloud Run production (D7).

## Điểm dừng hỏi Duy
- Contract/thiết kế không khớp code (vd `current_policy_version` của CMS khác chữ ký, `exception_handler` chưa có `extra`, migration `sales` vướng phụ thuộc vòng) → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô.
- Cần đổi luồng giữ chỗ, thanh toán, tra đơn, hoặc thêm field cá nhân nào ngoài 2 field ở `02b` §2.1.
- Có giá trị người bán thật trong tay (không đưa vào repo — hỏi Duy cách đặt lên Cloud Run).
- Test cũ đỏ.
