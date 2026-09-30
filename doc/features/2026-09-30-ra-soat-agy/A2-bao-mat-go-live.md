# A2 — Rà soát AGY: `2026-09-28-sua-loi-bao-mat` + `2026-09-28-khung-go-live`
> qa-tester · 2026-09-30 · Bước A2 của `doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md`.
> Không sửa code sản phẩm. Dữ liệu test 100% giả định.

## Tóm tắt
- **72 AC** rà lại (S01–S07: 40 AC · GL-01–GL-05: 32 AC).
- **71 ✅ chạy thật** (test đã có đọc kỹ + chạy lại xanh, hoặc test mới viết thêm và chạy xanh) · **1 ❌ lỗi thật** (GL-05-AC1,
  **trùng SR-19** đã có trong P8 Lô 6) · **0 ⏸**.
- Toàn bộ test backend liên quan (`apps.sales apps.content apps.common apps.inventory apps.reports apps.accounts`):
  **776/776 xanh** (tăng 2 so với baseline 774, là 2 test mới của A2). `makemigrations --check --dry-run`: *No changes
  detected* (chỉ có warning `content.W001` — đúng hành vi mong đợi khi máy dev không có biến `SELLER_*`, xem GL-01-AC4).
- 2 test mới **xanh** giữ lại trong repo (lấp khoảng trống bằng chứng thật, không phải test giả):
  `backend/apps/sales/payments/tests/test_ra_soat_s03_checkout_throttle.py` (S03-AC2, scope `shop_checkout` trước đây
  **chưa có ca nào gọi thật**).
- 1 script Playwright mới, chạy build FE thật (`NEXT_PUBLIC_USE_MOCK=0`, cổng 3101), chặn network bằng `page.route` để
  dựng đủ nhánh AC (không cần backend thật): `frontend/e2e/ra-soat-a2-golive.py` — **43/43 ca PASS**, đáp ứng đúng danh
  sách "AC thiếu bằng chứng" của SR-21 thuộc hồ sơ này (GL-01-AC2/AC5/AC6, GL-02-AC1…AC5, GL-03-AC2/AC4/AC5/AC8,
  GL-04-AC1…AC5). Ảnh chụp bằng chứng ở scratchpad phiên này (không commit ảnh vào repo theo luật dự án).
- **Không** dùng cổng ngoài quy định (frontend chỉ 3101, không đụng erp-console:3201 vì không cần cho phần thuộc A2 —
  GL-05 đã có vitest thật; xem ghi chú GL-05-AC1 bên dưới cho phần cần kiểm ở erp-console).

Quy ước: file test dạng `.py` (Playwright Python sync) theo đúng convention có sẵn của `frontend/e2e/*.py`
(`qa_sepay_checkout.py`…) — không đổi sang `.spec.ts` vì repo không dùng Playwright Test Runner (TS), chỉ dùng
Playwright Python trực tiếp, khớp skill `e2e-playwright`.

---

## 1) Hồ sơ `2026-09-28-sua-loi-bao-mat` (S01–S07)

### S01 — Nhật ký không lộ giá vốn (L-3)
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Chủ thấy đủ | ✅ | `apps/accounts/audit/tests/test_l3_cost_redaction.py::test_s01_ac1_chu_thay_du_gia_von` — đọc lại: assert đúng giá trị `landed_unit_cost` nguyên văn, không phải chỉ status 200. Chạy lại xanh. |
| AC2 Quản lý không thấy | ✅ | `...::test_s01_ac2_quan_ly_khong_thay_gia_von` — duyệt đệ quy `COST_KEYS` ở mọi độ sâu + `assertNotIn` số tiền mẫu trong chuỗi JSON. Test thật, không giả. |
| AC3 Theo quyền `view_costprice` | ✅ | `...::test_s01_ac3_quan_ly_co_quyen_view_costprice_thay_gia_von` |
| AC4 Phân quyền & lọc `?action=` | ✅ | `...::test_s01_ac4_phan_quyen_giu_nguyen_va_loc_action` (403/403/401 + lọc action) |
| AC5 Danh sách khoá dùng chung, append-only | ✅ | `apps/common/tests/test_cost_keys.py` (6 test đơn vị: dict lồng, list chứa dict) + `test_l3_cost_redaction.py::test_s01_ac5_du_lieu_auditlog_khong_bi_sua_trong_db` (DB không đổi trước/sau khi gọi API). |
| AC6 Không rò PII, response không thêm field | ✅ | Xác minh qua đọc code `apps/accounts/audit/serializers.py::audit_item`: **một** `return` duy nhất, luôn cùng 12 khoá (`id, actor_kind, actor_display, ai_actor, action, model_name, object_id, object_repr, changes, note, proposal_ref, created_at`) bất kể `can_view_cost` — bảo đảm cấu trúc không thể khác nhau theo quyền, chỉ nội dung `changes` đổi. Đối chiếu `apps/accounts/audit/tests/test_s03_auditlog.py::test_s03_contract_du_cac_field` (chạy xanh, đúng 12 khoá với `chu`). |

Off-path đã thêm (không phải test có sẵn): không cần thêm mới — `audit_item` không có allowlist action nào (lọc dựa
100% trên `COST_KEYS` xuất hiện trong `changes`, không quan tâm tên `action`), nên đã tự động đúng AC5 cho **mọi**
action tương lai, kể cả action lạ. Xác minh bằng đọc code (không có `if row.action in (...)`).

### S02 — Tra đơn Shop không dò được mã, không đoán SĐT (L-6)
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Bắt buộc đúng 4 chữ số | ✅ | `apps/sales/orders/tests/test_l6_lookup.py::test_s02_ac1_bat_buoc_dung_4_chu_so` — 5 giá trị sai × {mã thật, mã giả}, so `.json()` bằng nhau tuyệt đối (không chỉ status code). |
| AC2 Một thông điệp 404 | ✅ | `...::test_s02_ac2_mot_thong_diep_404_cho_ca_hai_truong_hop` |
| AC3 Đúng thì xem được, không rò PII | ✅ | `...::test_s02_ac3_dung_thi_xem_duoc_khong_ro_pii` — **lưu ý**: tập khoá thật có 8 khoá (`order_code, status, status_label, total_amount, lines, delivery, booked_expires_at, cancel_notice`), nhiều hơn 7 khoá ghi trong `02-stories.md` gốc. Test hiện tại đã cập nhật đúng theo thực tế (khoá `cancel_notice` do tính năng CSKH thêm sau, hợp lệ, không phải rò PII — đã kiểm không có tên/SĐT/địa chỉ). Đây là lệch tài liệu (story cũ chưa cập nhật), **không phải lỗi bảo mật** — không mở lỗi mới. |
| AC4 SĐT có dấu cách/+84 | ✅ | `...::test_s02_ac4_sdt_co_dau_cach_hoac_cong_84` |
| AC5 Checkout mã không tồn tại → 404 chung | ✅ | `...::test_s02_ac5_checkout_ma_khong_ton_tai_tra_404_chung` |
| AC6 Phân quyền, không có đường tắt | ✅ | `...::test_s02_ac6_phan_quyen_endpoint_van_cong_khai_va_user_login_tuan_thu_ac1_ac3` (4 Group đều phải qua đúng AC1–AC3) |

### S03 — Giới hạn tần suất (L-5)
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Tra đơn (IP + mã đơn) | ✅ | `apps/common/tests/test_l5_throttle.py::test_s03_ac1_shop_lookup_ip_throttle`, `::test_s03_ac1_shop_lookup_order_throttle_across_ips` |
| AC2 Đặt đơn, thanh toán, đăng nhập | ✅ (đặt đơn, đăng nhập đã có; **thanh toán trước đây thiếu**, đã bù) | Đặt đơn: `::test_s03_ac2_shop_order_create_throttle_khong_tao_don`. Đăng nhập: `::test_s03_ac2_login_ip_throttle_khong_sinh_token`, `::test_s03_ac2_login_user_throttle`. **Thanh toán (`POST .../checkout/`, scope `shop_checkout`) trước đây KHÔNG có ca nào gọi thật** dù story yêu cầu rõ — đã viết mới **`apps/sales/payments/tests/test_ra_soat_s03_checkout_throttle.py`** (2 test, xanh): `test_s03_ac2_shop_checkout_throttle_khong_tang_checkout_attempts` (2 request đầu 200, request 3 → 429, `checkout_attempts` không tăng khi bị chặn) và off-path `test_s03_ac2_shop_checkout_throttle_ca_khi_ma_don_khong_ton_tai` (throttle vẫn áp dụng khi mã đơn không tồn tại — chặn kênh dò mã đơn qua endpoint checkout). |
| AC3 Mức cấu hình qua env | ✅ | `::test_s03_ac3_tat_scope_khi_muc_la_none_hoac_rong` |
| AC4 Không vỡ test cũ | ✅ | Suite đầy đủ 776/776 xanh, mặc định throttle tắt khi `TESTING=True`. |
| AC5 Không đụng back-office | ✅ | `::test_s03_ac5_backoffice_khong_bi_throttle` (50 lần liên tiếp `chu` gọi `/api/audit-logs/`, không 429) |
| AC6 Không giả IP, không rò PII | ✅ | `::test_s03_ac6_num_proxies_dem_chung_ip_cuoi_xff` |

### S04 — Chốt lô đủ điều kiện, an toàn đồng thời (L-1)
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Còn đơn mở → chặn | ✅ | `apps/inventory/batches/tests/test_l1_close_batch.py::test_s04_ac1_*` (5 test: BOOKED/PAID/PROCESSING, đếm distinct đơn, trạng thái đóng không chặn, không rò PII trong thông điệp lỗi) |
| AC2 Giữ chỗ / hàng hoàn DRAFT → chặn | ✅ | `::test_s04_ac2_qty_reserved_blocks_close`, `::test_s04_ac2_draft_return_to_stock_blocks_close`, `::test_s04_ac2_approved_return_to_stock_does_not_block_close` |
| AC3 Chưa kiểm kê → chặn | ✅ | `::test_s04_ac3_no_reconciliation_line_blocks_close`, `::test_s04_ac3_draft_reconciliation_line_blocks_close`, `::test_s04_ac3_approved_plus_draft_reconciliation_blocks_close` |
| AC4 Đủ điều kiện → chốt, chốt 2 lần → lỗi | ✅ | `::test_s04_ac4_happy_path_close_batch`, `::test_s04_ac4_close_already_closed_batch_raises_br_lo_05` |
| AC5 Khoá đồng thời | ✅ (có giới hạn — xem ghi chú) | `::test_s04_ac5_closed_batch_not_picked_by_allocate_fefo` (hành vi thật: lô chốt xong `allocate_fefo` raise lỗi) + `::test_s04_ac5_select_for_update_and_atomic_execution` (mock xác nhận `select_for_update` gọi **trong** `transaction.atomic`). **Ghi chú**: đây là test tuần tự + mock cấu trúc, KHÔNG phải test đa luồng thật (race 2 request cùng lúc). Đủ để chứng minh đúng ý AC ("lô chốt xong thì `allocate_fefo` không lấy được nữa"), nhưng chưa chứng minh việc khoá chặn được request thứ 2 *đang chờ* — hạn chế chung của `TestCase` Django (transaction wrap), không phải lỗi mới, chỉ ghi nhận Low. |
| AC6 Phân quyền, không rò giá vốn | ✅ | `::test_s04_ac6_forbidden_roles_quan_ly_nv_kho_nv_giao_403`, `::test_s04_ac6_unauthenticated_returns_401`, `::test_s04_ac6_no_cost_leak_in_error_responses`, `::test_s04_ac6_quan_ly_cannot_see_cost_in_close_batch_audit_log` |

### S05 — Staging không bị index
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Shop staging có `X-Robots-Tag` | ✅ | Đọc lại `frontend/firebase.staging.json`: `"source":"**"` → header `X-Robots-Tag: noindex, nofollow`. Parse JSON thật bằng Python, không chỉ đọc mắt. |
| AC2 ERP staging có `X-Robots-Tag` | ✅ | `erp-console/firebase.staging.json` — cùng cấu trúc. |
| AC3 Production không đổi | ✅ | `git diff --stat -- frontend/firebase.json erp-console/firebase.json` → rỗng (chạy lại lượt này, xác nhận lại). |
| AC4 Kiểm trước deploy (JSON hợp lệ, Cache-Control `/_next/static/**` còn) | ✅ (phần build/JSON) · phần `curl` sau deploy staging là việc của Duy, ngoài phạm vi QA lúc chưa deploy | Parse JSON OK; `Cache-Control: public, max-age=31536000, immutable` cho `/_next/static/**` vẫn còn trong `firebase.staging.json`. |

### S06 — Lãi lỗ theo lô không tính hao hụt/hỏng 2 lần (L-10)
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Ví dụ Duy (hao hụt) | ✅ | `apps/reports/tests/test_services.py::test_batch_pnl_duy_example_shrinkage_not_double_counted` — số đúng từng đồng (`profit=3.500.000`), đọc lại khớp AC. |
| AC2 Hàng hỏng + phân bổ | ✅ | `::test_batch_pnl_damage_shown_not_added_to_total_cost`, `::test_batch_pnl_computes_profit_with_shrinkage_and_damage` (`total_cost=8.200.000`, `profit=-1.000.000`) |
| AC3 Bất biến công thức | ✅ | `::test_batch_pnl_total_cost_invariant_under_losses` |
| AC4 "Tạm tính" | ✅ | `::test_batch_pnl_not_provisional_when_closed` |
| AC5 Đúng 14 khoá | ✅ | `::test_batch_pnl_keys_unchanged` |
| AC6 Phân quyền, không rò | ✅ | `apps/reports/tests/test_api.py::BatchPnlApiTests` (4 test: 200/403×3/401/404, JSON lỗi không chứa khoá giá vốn) |
| AC7 Nơi khác không đổi | ✅ | `period_pnl`, `dashboard_api` không sửa (test cũ liên quan vẫn xanh trong suite 776); `doc/BUILD-PLAN.md:147` đã cập nhật. |

### S07 — Doanh thu lô bỏ hoá đơn huỷ (L-11)
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Một huỷ một hiệu lực | ✅ | `::test_batch_pnl_excludes_cancelled_invoice_revenue` — số đúng (`revenue=4.500.000`, `profit=-5.500.000`) |
| AC2 Chỉ hoá đơn huỷ | ✅ | `::test_batch_pnl_only_cancelled_invoices_zero_revenue` |
| AC3 Huỷ sau khi xem, append-only | ✅ | `::test_batch_pnl_invoice_cancelled_after_issue` |
| AC4 Phần khác không đổi | ✅ | Cùng bộ test S06 (14 khoá, `total_cost` không đổi theo trạng thái hoá đơn) |
| AC5 Phạm vi — nơi khác đã đúng | ✅ | Đọc code `period_pnl` (dòng lọc `status=ISSUED` có sẵn), `dashboard_api.py` — không sửa, test cũ vẫn xanh. |

---

## 2) Hồ sơ `2026-09-28-khung-go-live` (GL-01–GL-05)

### GL-01 — Footer thông tin người bán
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 7 field đầy đủ | ✅ | `apps/content/site/tests/test_site_info.py::test_gl01_ac1_seller_complete_when_all_fields_provided` |
| AC2 Footer hiện đủ 7 thông tin, `tel:`/`mailto:` | ✅ (bù bằng chứng thật, SR-21) | **Mới**: `frontend/e2e/ra-soat-a2-golive.py` — mở 3 route thật (Landing `/`, Shop `/shop/`, Trang `/trang/?slug=...`), assert đủ 7 field + `a[href="tel:..."]`/`a[href="mailto:..."]` tồn tại. Trước đây AC này chỉ PASS bằng đọc code. |
| AC3 Đổi `SELLER_PHONE`, không build lại FE | ✅ | `test_site_info.py::test_gl01_ac3_seller_phone_dynamic_without_cache` (BE, `override_settings`, không cache module) |
| AC4 Thiếu biến → `null`, `seller_complete=false`, warning `content.W001` | ✅ | `test_site_info.py::test_gl01_ac4_missing_seller_tax_code_warning_w001` + xác nhận lại bằng `manage.py makemigrations --check --dry-run` chạy thật ở máy này (in đúng warning `content.W001`, đúng 7 biến `SELLER_*`, không lộ giá trị nào khác). |
| AC5 API lỗi → ẩn khối người bán, không trắng trang | ✅ (bù bằng chứng thật, SR-21) | **Mới**: script Playwright — `page.route(..., abort)` cho `/api/public/site-info/`, xác nhận: khối "Thông tin đơn vị bán hàng" biến mất, nội dung Shop (catalog) vẫn hiển thị, console không log PII. |
| AC6 Không viết cứng dữ liệu thật | ✅ (bù bằng chứng thật, SR-21) | Chạy lại `git grep -n "SELLER_" -- . ':!*.md' ':!*.example'` — chỉ khớp `settings.py`, `apps/content/site/*`, test; không có MST/SĐT thật. |
| AC7 Contract JSON đúng bộ khoá | ✅ | `test_site_info.py::test_gl01_ac7_contract_keys_and_no_secrets_leaked` |
| AC8 405 cho method ghi, `Cache-Control` | ✅ | `test_site_info.py::test_gl01_ac8_disallowed_methods_405` |

### GL-02 — Footer link chính sách
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 4 link đúng thứ tự | ✅ (bù bằng chứng thật, SR-21) | BE: `apps/content/tests/test_pages_policy.py::test_cms_15_ac6_public_footer_links_order_and_published_only` (đọc lại: dùng `footer_order` thật, không phải mock cố định). **Mới** FE: script Playwright dựng 3 link theo thứ tự tuỳ ý, assert đúng thứ tự + href `/trang/?slug=...`. |
| AC2/AC3 Gỡ trang / bỏ `show_in_footer` → biến mất, không build lại | ✅ (bù bằng chứng thật, SR-21) | **Mới**: script Playwright — 2 lần `page.reload()` với 2 response `footer-links` khác nhau (không build lại FE giữa 2 lần), xác nhận link biến mất đúng, 2 link còn lại giữ nguyên thứ tự. |
| AC4 API lỗi → ẩn khối link, khối người bán không ảnh hưởng | ✅ (bù bằng chứng thật, SR-21) | **Mới**: Playwright — abort `footer-links`, giữ `site-info` OK → khối người bán còn, khối link mất. |
| AC5 Mobile 375×667 | ✅ (bù bằng chứng thật, SR-21) | **Mới**: Playwright viewport 375×667 — `scrollWidth == clientWidth` (không cuộn ngang), `bounding_box().height >= 44` cho link footer (đo được 44px). |
| AC6 Trang Nháp không vào footer | ✅ | BE test đã có (`test_cms_15_ac6...`, cùng test AC1, có case `status="draft"` bị loại). |

### GL-03 — Ô đồng ý xử lý dữ liệu cá nhân
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Ghi giờ server + phiên bản | ✅ | `apps/sales/orders/tests/test_privacy_consent.py::test_gl03_ac1_consent_recorded_with_server_time_and_version` |
| AC2 Checkbox chưa tick, nhãn đúng, link mở tab mới, nút khoá | ✅ (bù bằng chứng thật, SR-21) | **Mới**: Playwright — `checkbox.is_checked() == False` khi mở trang; text có "giao hàng" + "xác nhận đơn"; `a[target="_blank"]`; nút Đặt hàng `disabled` tới khi tick, hết khoá sau khi tick. Ảnh `gl03-ac2-checkout-consent.png`. |
| AC3 Thiếu/false consent → 400, không giữ chỗ | ✅ | `test_privacy_consent.py::test_gl03_ac3_missing_or_invalid_consent_rejected_400_no_reservation` (5 case, đếm `SalesOrder`/`Batch.qty_reserved` không đổi) |
| AC4 Chính sách đổi → 409, FE bỏ tick, giữ form | ✅ (bù bằng chứng thật, SR-21) | BE: `test_privacy_consent.py::test_gl03_ac4_policy_changed_returns_409_with_current`. **Mới FE**: Playwright chặn `POST /api/shop/orders/` trả 409 thật (không dùng chuỗi ma thuật `MOCK_409` của `lib/mock.ts` — chặn network thật để kiểm đúng code xử lý lỗi HTTP), xác nhận: thông báo đúng, checkbox bỏ tick, **3 field form** (tên/SĐT/địa chỉ) còn nguyên giá trị đã nhập. |
| AC5 Chưa có chính sách & cờ bật → 503, "Shop tạm chưa nhận đơn" | ✅ (bù bằng chứng thật, SR-21) | BE: `test_privacy_consent.py::test_gl03_ac5_flag_enabled_no_published_policy_returns_503`. **Mới FE**: Playwright chặn `GET /api/public/content/pages/by-role/privacy/` trả 404 thật ngay từ lúc tải trang checkout (không phải chỉ lúc submit) → màn "Shop tạm chưa nhận đơn" hiện thay form (ô "Tên người nhận" biến mất hoàn toàn). |
| AC6 Cờ tắt → không cần consent | ✅ | `test_privacy_consent.py::test_gl03_ac6_flag_disabled_allows_order_without_consent` |
| AC7 Thu tối thiểu | ✅ | `test_privacy_consent.py::test_gl03_ac7_sales_order_fields_and_no_new_tables_in_sales` |
| AC8 Log/storage/URL không PII | ✅ (bù bằng chứng thật, SR-21) | BE: `test_privacy_consent.py::test_gl03_ac8_no_pii_in_logs`. **Mới FE**: Playwright đặt đơn thật (network thật, không mock) với tên/SĐT/địa chỉ giả đặc trưng ("Khách QA Ẩn Danh", "0912345678", "999 Đường Bí Mật QA"), sau đó đọc **toàn bộ** `localStorage`, `sessionStorage`, URL, console log bằng JS thật trong trình duyệt (`page.evaluate`) — không có PII nào lọt; xác nhận `sessionStorage` chỉ giữ `order_code` + 4 số cuối (đúng hành vi cho phép). |
| AC9 Tra đơn không lộ khoá consent | ✅ | `test_privacy_consent.py::test_gl03_ac9_order_lookup_does_not_leak_consent_keys` |
| AC10 Không sửa được, `PROTECT` | ✅ | `test_privacy_consent.py::test_gl03_ac10_consent_fields_immutable_and_protected` |

### GL-04 — Thông báo "vựa sẽ gọi xác nhận"
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Bật cờ → câu thông báo đúng 4 số cuối + khung giờ | ✅ (bù bằng chứng thật, SR-21) | **Mới**: Playwright — đặt đơn thật (network thật), `confirm_call_notice=true` → `[data-testid=confirm-call-notice]` có "5678" và "7:00". Ảnh `gl04-ac1-notice-on.png`. |
| AC2 Quay về từ cổng thanh toán vẫn có thông báo (từ `sessionStorage`) | ✅ (bù bằng chứng thật, SR-21) | **Mới**: Playwright set `sessionStorage` trước, mở thẳng `/shop/orders/?code=...&result=success`, có thông báo đúng 4 số cuối lấy lại từ storage. Ảnh `gl04-ac2-return-success.png`. |
| AC3 DOM/URL không chứa SĐT đầy đủ | ✅ (bù bằng chứng thật, SR-21) | **Mới**: assert `"0912345678" not in page.inner_text("body")` và `not in page.url` ở cả 2 màn (thanh toán, quay về). |
| AC4 Cờ tắt → không có câu | ✅ (bù bằng chứng thật, SR-21) | **Mới**: cùng kịch bản AC1 với `confirm_call_notice=false` → `notice.count() == 0`. |
| AC5 `site-info` lỗi → ẩn, không chặn thanh toán | ✅ (bù bằng chứng thật, SR-21) | **Mới**: Playwright abort `site-info`, xác nhận nút Đặt hàng vẫn bấm được, đơn vẫn tạo thành công ("Đặt hàng thành công" hiện ra), không có thông báo gọi xác nhận. |

### GL-05 — Chủ/Quản lý tra bằng chứng đồng ý trên ERP
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 Dòng consent + **link xem đúng phiên bản** | ❌ **Lỗi thật — trùng SR-19** | BE: `apps/sales/orders/tests/test_privacy_consent_view.py::test_gl05_ac1_*` chỉ kiểm **API** trả đủ 4 khoá — đúng, chạy xanh. FE: `erp-console/features/orders/orders_consent.test.ts` chỉ test **tầng mock API**, KHÔNG test hành vi UI/link. Đọc code thật: `erp-console/features/content/**` và `app/content/**` **không có bất kỳ chỗ nào đọc `searchParams.get("version")`** (`grep -rn "searchParams.get(\"version\")" erp-console/` → rỗng) — nghĩa là link `/content/edit/?id=X&version=N` hiện chỉ mở trang sửa bài mới nhất, **bỏ qua** tham số `version`, không mở đúng phiên bản đã được khách đồng ý lúc đó. Đây đúng là lỗi đã ghi ở `doc/features/2026-09-30-sua-loi-review/02-stories.md` **SR-19** ("Link bằng chứng đồng ý mở sai phiên bản chính sách") — **không mở lỗi mới**, chỉ xác nhận lại bằng đọc code thật (không phải đoán). |
| AC2 Đơn cũ không có consent → `null` | ✅ | `test_privacy_consent_view.py::test_gl05_ac2_order_without_consent_returns_null` + `orders_consent.test.ts` (UI hiện đúng câu "Không có dữ liệu đồng ý…") |
| AC3 `nv_kho`/`nv_giao` không thấy khoá | ✅ | `test_privacy_consent_view.py::test_gl05_ac3_nv_kho_does_not_see_privacy_consent_key`, `::test_gl05_ac3_nv_giao_does_not_see_privacy_consent_key` + `test_order_list_does_not_have_privacy_consent_key` (danh sách đơn không lộ với ai) + `orders_consent.test.ts` (UI không render khi thiếu khoá) |

---

## Test mới đã thêm (xanh, giữ lại trong repo)
- `backend/apps/sales/payments/tests/test_ra_soat_s03_checkout_throttle.py` — 2 test, S03-AC2 scope `shop_checkout`
  (trước đây chưa có ca thật nào gọi endpoint này dưới throttle). Chạy: `cd backend && DJANGO_DEBUG=1 env -u
  DATABASE_URL .venv/bin/python manage.py test apps.sales.payments.tests.test_ra_soat_s03_checkout_throttle` → `OK`.
- `frontend/e2e/ra-soat-a2-golive.py` — script Playwright (không phải framework test runner, theo đúng convention repo),
  43 ca kiểm GL-01/GL-02/GL-03/GL-04 bằng build FE thật + `page.route` chặn network (không cần backend). Chạy:
  `cd frontend && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8199 npx next dev -p 3101 &` rồi
  `python3 e2e/ra-soat-a2-golive.py` → `TẤT CẢ CA PASS` (43/43).

## Lỗi mới
Không có lỗi **mới**. Phát hiện lại 1 lỗi **đã có sẵn trong story P8** (không mở trùng):
- **GL-05-AC1 — Link bằng chứng đồng ý mở sai phiên bản chính sách** · Medium · **trùng SR-19**
  (`doc/features/2026-09-30-sua-loi-review/02-stories.md`, Lô 6). Xác nhận lại bằng đọc code thật (`erp-console/`
  không đọc `version` query param ở trang `/content/edit/`) — khớp mô tả AC1/AC2 của SR-19. Không cần hành động thêm
  ở bước A2, để P8 Lô 6 xử lý.

## Ghi chú không phải lỗi (để điều phối viên biết, không chặn)
- S02-AC3: tập khoá tra đơn công khai hiện có 8 khoá (`+cancel_notice`) thay vì 7 khoá ghi trong `02-stories.md` gốc —
  do tính năng CSKH thêm sau, đã kiểm không rò PII. Đề xuất cập nhật câu chữ AC trong story cũ nếu có dịp, không phải
  việc của A2.
- S04-AC5 "khoá đồng thời": bằng chứng hiện có là tuần tự + mock cấu trúc (`select_for_update` được gọi trong
  `transaction.atomic`), không phải test đa luồng thật race 2 request. Đủ đạt ý AC, ghi nhận Low nếu muốn làm chặt hơn
  sau này (không phải P8).

## Lệnh đã chạy (kèm output tóm tắt)
```bash
cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test \
  apps.content apps.sales apps.accounts apps.common apps.inventory apps.reports -v 1
# Ran 774 tests in 64.955s — OK  (trước khi thêm test mới)

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test \
  apps.sales.orders.tests.test_l6_lookup apps.common.tests.test_l5_throttle \
  apps.inventory.batches.tests.test_l1_close_batch apps.reports.tests.test_services apps.reports.tests.test_api
# Ran 52 tests in 1.048s — OK

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test \
  apps.sales.payments.tests.test_ra_soat_s03_checkout_throttle -v 2
# Ran 2 tests — OK (test mới)

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test \
  apps.sales apps.content apps.common apps.inventory apps.reports apps.accounts -v 1
# Ran 776 tests in 28.876s — OK  (sau khi thêm test mới, +2 đúng như kỳ vọng)

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py makemigrations --check --dry-run
# No changes detected (chỉ có warning content.W001 — đúng, máy dev không có SELLER_*)

cd frontend && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8199 npx next dev -p 3101 &
cd frontend && python3 e2e/ra-soat-a2-golive.py
# [PASS] x43 — TẤT CẢ CA PASS

python3 -c "import json; json.load(open('frontend/firebase.staging.json')); json.load(open('erp-console/firebase.staging.json'))"
git diff --stat -- frontend/firebase.json erp-console/firebase.json   # rỗng

grep -rn "SELLER_" -- . ':!*.md' ':!*.example'   # chỉ settings.py, apps/content/site/*, test
grep -rn "searchParams.get(\"version\")" erp-console/   # rỗng -> xác nhận SR-19 còn tồn tại thật
```

Không dùng `npm ci` (node_modules đã sẵn ở cả `frontend/` và `erp-console/`, không cần cài lại). Không chạy
`--parallel`. Không đụng `db.sqlite3` dùng chung của repo (Playwright chạy trên build FE thật nhưng dùng
`page.route` chặn toàn bộ network — không cần một Django server thật đang chạy, tránh tranh chấp DB với agent khác).
