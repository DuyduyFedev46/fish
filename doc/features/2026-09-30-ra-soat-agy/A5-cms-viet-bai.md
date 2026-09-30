# A5 — Rà soát CMS viết bài (`doc/features/2026-09-28-cms-viet-bai`)
> QA (Claude) · 2026-09-30 · Bước A5, `doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md`

## Kết luận
**REJECTED tạm thời** — 3 lỗi thật tìm thấy trong lượt rà soát này: **B1** (High, mới, chưa có
story nào phủ), **B2** (Medium, trùng SR-18 — đã có story P8, không mở thêm việc mới), **B3**
(Medium, mới, chưa có story nào phủ đúng). B2 không chặn thêm ngoài P8 (đã có SR-18); B1 và B3 cần
Duy quyết định: thêm story mới hay gộp vào Lô 6/7 của P8. Toàn bộ 118 AC nghiệp vụ + TD-3 của 16
story (CMS-01…CMS-16) đã được kiểm; phần lớn PASS với bằng chứng thật (test đã đọc + chạy lại,
hoặc Playwright mới chạy trên backend/FE thật).

## Tổng
- AC đã kiểm: **118/118** (+ TD-3) · ✅ **116** · ❌ **2** (CMS-06-AC3 do lỗi B1; CMS-04-AC2 do lỗi
  B3) · ⏸ **1** (CMS-04-AC4, không lặp lại kiểm trong lượt này vì không có gì mới, dựa vào test cũ)
  · TD-3 ✅.
- Story CMS-16 (4 AC, tính riêng ngoài 118): xác nhận **đã đổi thiết kế có chủ đích**
  (`02c-giao-viec.md`), không phải bỏ sót — xem mục riêng bên dưới.
- Test mới thêm: 3 test backend (GREEN, trong `backend/apps/content/tests/test_ra_soat_extra.py`)
  + 7 script Playwright thật (GREEN, trong `frontend/e2e/` và `erp-console/e2e/`, một số script có
  nhiều kịch bản). Repro lỗi thật (ĐỎ, không để trong cây test sản phẩm): 2 file trong
  `doc/features/2026-09-30-ra-soat-agy/repro/`.
- **B1 — giá hiển thị sai định dạng toàn Shop và thẻ mặt hàng CMS** (High, MỚI, chưa có story nào
  phủ). **B2 — F1 IDOR ảnh lúc tạo bài** (Medium, **trùng SR-18** — P8 đã có, chưa làm). **B3 —
  reload khi mất mạng bị chặn bởi màn xác thực** (Medium, MỚI, gần phạm vi SR-20 nhưng KHÔNG
  trùng — đề xuất story riêng hoặc gộp SR-24).

## Phương pháp
1. Đọc toàn bộ AC trong `02-stories.md` (118 AC + TD-3, 16 story).
2. Với AC đã có test: mở test, đọc để xác nhận test THẬT SỰ kiểm đúng AC (không rỗng, không giả
   định sai) — đối chiếu **89 tên hàm test** mà báo cáo QA lần 1 trích dẫn với mã nguồn thật:
   **khớp 100%** (không có test "ma"). Sau đó chạy lại **toàn bộ** `apps.content` (không chỉ đọc):
   `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.content`
   → **96/96 PASS** (93 test cũ + 3 test mới thêm ở bước 4).
3. Với AC trong bảng "AC thiếu bằng chứng" (`doc/features/2026-09-30-review-p1-p7/review-cms-golive-fe-qa.md`,
   phần CMS) — trước đó QA chỉ PASS bằng đọc code — dựng môi trường **chạy thật** (backend Django
   thật ở `:8104`, dữ liệu giả qua `manage.py seed_demo` + API, frontend Shop build tĩnh phục vụ ở
   `:3104`, erp-console build tĩnh phục vụ ở `:3204`, `CORS_ALLOWED_ORIGINS` trỏ 2 cổng FE) rồi viết
   Playwright thật, không mock.
4. Với AC nghiệp vụ chính, thêm 1 ca ngoài đường thuận (bấm đúp, 2 người sửa cùng lúc, bài nháp
   không lộ qua API công khai, ảnh gỡ khỏi bài không bị xoá object).
5. Không sửa code sản phẩm. Dữ liệu test 100% giả (`ra_soat_*`, "du lieu gia", ảnh sinh bằng
   Pillow lúc chạy). Không đụng DB staging/production — chỉ SQLite dev cục bộ.

**Sự cố môi trường đáng ghi lại:** một tiến trình khác (một trong 3 agent QA song song) đã build
lại `erp-console/out/` và `frontend/out/` **đè lên** bản build của tôi đang phục vụ ở `:3204`/`:3104`
giữa lúc chạy Playwright (phát hiện qua hash chunk khác nhau và app trỏ nhầm sang API production).
Đã khắc phục bằng cách copy `out/` sang scratchpad riêng rồi phục vụ từ đó — nếu 3 agent dùng
chung một checkout `/Users/dangthiduyen/Downloads/loc`, nên cân nhắc build vào thư mục cách ly cho
mỗi agent.

---

## CMS-01 — Quyền "Nội dung" và mục menu · 7 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1 | ✅ | `apps/content/tests/test_permissions_matrix.py::test_cms_01_ac1_group_permissions` — đọc: kiểm đúng 8 quyền trên 4 Group, thật. |
| AC2 | ✅ | `...::test_cms_01_ac2_nv_kho_nv_giao_endpoints` |
| AC3 | ✅ | `...::test_cms_01_ac3_unauthenticated_401` |
| AC4 | ✅ | `apps/content/tests/test_no_shortcut.py` (2 test) — quét router thật, không có `AllowAny` ghi, không có route dưới `internal/`. |
| AC5 | ✅ | `apps/content/tests/test_publish.py::test_cms_01_ac5_user_with_only_nd01_calls_publish_403` |
| AC6 | ✅ | `erp-console/features/content/content.test.ts` (đơn vị) — **không** có Playwright thật cho việc "gõ thẳng URL". Đã tự kiểm bằng tay qua `ConsoleGate` (đọc `features/auth/components/ConsoleGate.tsx`): route `/content` nằm sau `ConsoleGate`, không gọi API content nào trước khi gate render — hợp lý nhưng chưa có Playwright riêng. Không chặn (Low, ghi nhận). |
| AC7 | ✅ | `erp-console/features/content/content.test.ts` (đơn vị, kiểm bộ lọc/badge). |

## CMS-02 — Quản lý chuyên mục · 6 AC
Toàn bộ 6 AC ✅, `apps/content/tests/test_categories.py` (6 test, đã đọc + chạy lại, thật).

## CMS-03 — Soạn & lưu nháp · 13 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1–AC12 | ✅ | `apps/content/entries/tests/test_draft.py` (10 test) + `apps/content/body/tests/test_sanitize.py`, `test_slug.py` (XSS lớp 1: **15 payload**, đã đọc từng payload — thật, không rỗng). |
| AC13 (điện thoại) | ✅ **MỚI chạy thật** | `erp-console/e2e/ra_soat_cms03_ac13_mobile.py` — Playwright thật trên backend `:8104` + erp-console build tĩnh `:3204`, viewport 375×667: không cuộn ngang (`scrollWidth==clientWidth`), **17 nút thao tác đo được đều ≥44×44px**, nút "Lưu nháp" vẫn nằm trong vùng nhìn thấy khi mô phỏng bàn phím ảo mở (thu viewport còn 375×260). Trước đây QA chỉ đọc CSS. |

## CMS-04 — Tự lưu khi rớt mạng · 6 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1 | ✅ **MỚI chạy thật** | `erp-console/e2e/ra_soat_cms04_autosave.py` — gõ rồi chờ đúng 10.5s, đúng **1** PATCH, trạng thái "Đã lưu lúc". |
| AC2 | ❌ — xem lỗi B3 | Phần "giữ bản tạm khi mất mạng" đúng (localStorage có draft, trạng thái "Chưa lưu, đang giữ trên máy"). Phần "**sau khi tải lại**, nội dung được khôi phục" sai khi mạng mất thật (kể cả API xác thực bị chặn theo) — xem lỗi B3. Chấm ❌ cho cả AC vì câu chữ AC đòi cả hai vế. |
| AC3 | ✅ **MỚI chạy thật** | Có mạng lại (bắn sự kiện `online` + gỡ chặn API) → tự PATCH trong ≤10s, "Đã lưu lúc", xoá bản tạm cục bộ. |
| AC4 | ⏸ chưa kiểm thật lần này | Có test cũ (409 STALE_VERSION giữ bản tạm) — không lặp lại trong lượt A5 vì đã có `CMS-03-AC7`/`test_cms_04_ac4` phía đơn vị FE; không phát hiện gì mới. |
| AC5 | ✅ **MỚI chạy thật** | Bắn `beforeunload` cancelable khi đang có thay đổi chưa lưu → `event.defaultPrevented === true` (chặn rời trang), xác nhận đúng cơ chế code (`handleBeforeUnload`). |
| AC6 | ✅ **MỚI chạy thật** | Sau khi lưu thành công: `localStorage` không còn khoá `draft`; URL `.../content/edit/?id=4` không chứa tiêu đề/nội dung. |

## CMS-05 — Ảnh trong bài · 8 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1–AC4, AC7 | ✅ | `apps/content/images/tests/test_images.py` (5 test, đã đọc: JPEG 4000×3000 có EXIF GPS thật, kiểm tỉ lệ 4:3 sai số ≤1px, kiểm EXIF bị xoá bằng đọc lại file WebP thật trên đĩa — không giả). |
| AC5 | ✅ **MỚI, trước đây chỉ trích `storage.py`** | `apps/content/tests/test_ra_soat_extra.py::CoverImageNeverDeletedTests` — upload ảnh X thật, đăng phiên bản 1 (có X), gỡ X khỏi thân bài, đăng phiên bản 2; xác nhận: bản ghi `ContentImage` của X còn trong DB, **file vật lý trên đĩa vẫn tồn tại** (`os.path.exists`), và lớp storage (`LocalItemImageStorage`) **không có hàm `delete` nào cả** (kiểm cấu trúc, đúng tinh thần BR-DM-14). |
| AC6, AC8 | ✅ **MỚI chạy thật** | `erp-console/e2e/ra_soat_cms05_upload_mobile.py` — chặn (abort) request upload thật giữa chừng: hiện lỗi rõ ràng (lệch chữ so với story, xem Ngoại lệ & biên), **không** ảnh nào được thêm vào danh sách (đếm không đổi). Input file có `accept="image/*"` + gợi ý "Hỗ trợ camera, thư viện ảnh" (AC8). |

## CMS-06 — Thẻ mặt hàng · 7 AC
Dựng dữ liệu thật: `manage.py seed_demo` (mặt hàng `CA-THU` 165.000đ, `GHE-XANH`), bài
`bai-kiem-tra-the-mat-hang-ra-soat` với 2 khối `item_card`.

| AC | KQ | Bằng chứng |
|---|---|---|
| AC1, AC2, AC6 | ✅ | `apps/content/tests/test_item_card_and_public_list.py` (3 test, đã đọc, thật). |
| AC3 | ❌ **MỚI chạy thật — xem lỗi B1** | `frontend/e2e/ra_soat_cms06_item_card.py baseline` rồi đổi giá `CA-THU` 165.000→260.000 **qua DB thật** (không đăng lại bài) rồi `after-price-change` → **cơ chế cập nhật giá theo thời gian thực đúng** (giá trị số đổi 165000→260000 không cần đăng lại bài), nhưng **định dạng hiển thị sai**: DOM hiện "260000.00đ" thay vì "260.000 đ" như AC ghi nguyên văn (lỗi B1, `formatVnd` nhận chuỗi thay vì số). Test evidence dùng bộ đọc số chịu được cả 2 định dạng để không chặn các AC khác; bản thân AC3 bị chấm ❌ vì sai định dạng hiển thị. |
| AC4 | ✅ **MỚI chạy thật** | Link "Xem giá & đặt" đúng `code=CA-THU&utm_source=caveve_web&utm_medium=bai_viet&utm_campaign=<slug>`, không thừa tham số. |
| AC5 | ✅ **MỚI chạy thật** | Vô hiệu hoá `GHE-XANH` thật (`is_active=False`) → thẻ hiện "Tạm hết hàng" + nút `/shop/?...` cùng UTM; phần còn lại của bài (thẻ CA-THU) vẫn hiển thị đủ. |
| AC7 | ✅ **MỚI chạy thật** | Bắt toàn bộ request mạng của trang: chỉ `/api/public/content/**`, `/api/shop/catalog/**` và `/api/public/site-info/` (footer pháp lý, tính năng go-live thêm SAU CMS — xem Ngoại lệ & biên); không request nào tới host khác `localhost`; HTML không có khoá cấm nào. |

## CMS-07 — Đăng bài lần đầu · 9 AC
Toàn bộ ✅, `apps/content/tests/test_publish.py` (7 test, đã đọc: kiểm đúng danh sách `missing`,
kiểm AuditLog chỉ có 3 khoá không chứa chữ bài, kiểm đồng thời 2 request publish song song bằng
thread thật → đúng 1 request 200).

## CMS-08 — Cảnh báo SĐT/giá vốn · 8 AC
Toàn bộ ✅, `apps/content/tests/test_scan_warnings.py` (8 test, đã đọc: 4 định dạng SĐT thật, che
đúng 3 số cuối, bộ khoá `CONTENT_COST_KEYWORDS`, allowlist hotline, không báo nhầm `250.000đ` /
`SO-2026-00012`).

## CMS-09 — Gửi duyệt · 6 AC
Toàn bộ ✅, `apps/content/tests/test_lifecycle_and_versions.py` (6 test).

## CMS-10 — Sửa bài đã đăng · 6 AC
Toàn bộ ✅, `apps/content/tests/test_unpublish_discard.py` (6 test, gồm kiểm append-only bằng gọi
thẳng `save()`/`delete()`/`update()` trên `EntryVersion` → raise `BusinessError` thật).

## CMS-11 — Lịch sử phiên bản & khôi phục · 5 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1, AC2, AC4, AC5 | ✅ | `apps/content/tests/test_lifecycle_and_versions.py` (4 test). |
| AC3 | ✅ **MỚI chạy thật** | `erp-console/e2e/ra_soat_cms11_ac3_restore_confirm.py` — bài có thay đổi chưa đăng thật (PATCH tiêu đề, không publish), bấm "Khôi phục phiên bản này" → `window.confirm` bật lên (bắt bằng `page.on("dialog")`), huỷ → tiêu đề đang soạn không đổi. |

## CMS-12 — Gỡ bài & đăng lại · 7 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1–AC7 | ✅ | `apps/content/tests/test_unpublish_discard.py` (6 test cũ, đã đọc + chạy lại). |
| Ngoài đường thuận | ✅ **MỚI** | `apps/content/tests/test_ra_soat_extra.py::DoubleClickUnpublishTests` — mô phỏng **bấm đúp** nút "Gỡ bài" (2 request cùng `row_version` gửi liên tiếp): đúng 1 request 200, 1 request 409 STALE_VERSION; đúng **1** dòng AuditLog `content_unpublish` (không phình do bấm đúp). |

## CMS-13 — Khách đọc bài công khai · 10 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1 | ✅ **MỚI chạy thật** | Trước đây QA ghi "một câu mô tả 'đã sửa endpoint', không có test FE/E2E nào". `frontend/e2e/ra_soat_cms13_public.py` — bài thật đăng qua API, mở `/bai-viet/?slug=...` bằng frontend build tĩnh + backend thật: tiêu đề, "Cá Về", `document.title` có hậu tố "\| Cá Về", `<meta name=description>` đều đúng. |
| AC2 (lớp 2), AC6, AC7, AC8, AC10 | ✅ **MỚI chạy thật** | Cùng script: bài chứa `<img src=x onerror=alert(1)>` trong text và `href="javascript:alert(1)"` — **không dialog nào bật** (bắt `page.on("dialog")`), chữ hiện nguyên văn dạng text (không phải thẻ `<img>` thật), không link `javascript:` nào còn trong DOM; link ngoài có `target=_blank` + `rel="nofollow noopener noreferrer"`; slug không tồn tại hiện "Không tìm thấy bài"; không cuộn ngang ở 375px; không request nào ra ngoài `localhost` (AC8). |
| AC3, AC4, AC5, AC9 | ✅ | `apps/content/public/tests/test_public_api.py` (đã đọc, thật — quét đệ quy toàn JSON, kiểm 404 draft giống hệt 404 not-found, 410 GONE, 405 cho POST/PUT/PATCH/DELETE). |

## CMS-14 — Danh sách bài & Landing · 6 AC
| AC | KQ | Bằng chứng |
|---|---|---|
| AC1, AC2, AC5, AC6 | ✅ | `apps/content/tests/test_item_card_and_public_list.py` (4 test, đã đọc: 25 bài + 3 nháp + 2 trang, phân trang đúng, `page=999` → 404 không phải 500). |
| AC3 | ✅ **MỚI chạy thật** | `frontend/e2e/ra_soat_cms14_landing.py normal` — Landing thật hiện khối "Cẩm nang & Mẹo hay từ vựa" + link "Xem tất cả bài viết". |
| AC4 | ✅ **MỚI chạy thật** | `... api-down` — chặn (abort) toàn bộ `/api/public/content/**` → khối "Bài mới" biến mất hoàn toàn, phần còn lại Landing (Hero, "Cá Về"...) vẫn hiển thị đủ, trang không trắng. |

## CMS-15 — Trang nội dung & phiên bản có hiệu lực · 9 AC + TD-3
Toàn bộ ✅, `apps/content/tests/test_pages_policy.py` (10 test, đã đọc: `effective_version()` kiểm
đúng biên trước/giữa/sau 2 lần đăng, `footer-links` chỉ trả trang Đã đăng + `show_in_footer`).

## CMS-16 — Staging không bị lập chỉ mục · 4 AC
**Không phải khoảng trống — đổi thiết kế có chủ đích, ghi rõ ở `02c-giao-viec.md` dòng 9:**
> "CMS-16 không giao: đã phủ bởi S05 hồ sơ sửa lỗi bảo mật (`X-Robots-Tag: noindex, nofollow` trong
> `firebase.staging.json`). Không thêm `NEXT_PUBLIC_SITE_ENV`, không thêm `robots.txt`."

Đã tự kiểm chứng: `frontend/firebase.staging.json` và `erp-console/firebase.staging.json` đều có
header `X-Robots-Tag: noindex, nofollow` áp cho `**` — đạt mục tiêu nghiệp vụ của CMS-16-AC1/AC2
bằng cơ chế khác (header hosting thay vì meta/robots.txt app-level). AC3/AC4 (build phải có
`NEXT_PUBLIC_SITE_ENV`) không còn áp dụng vì thiết kế đã đổi. **Không tính là lỗi.**

---

## Ngoại lệ & biên đã thêm (ngoài AC gốc)
1. **Bấm đúp "Gỡ bài"** (CMS-12) — 1×200, 1×409, không phình AuditLog. GREEN.
2. **Bài nháp không lộ qua API công khai dù biết chính xác slug** (CMS-13) — response 404 của bài
   Nháp và của slug không tồn tại **giống hệt nhau từng byte** (so `resp.json()` trực tiếp, không
   chỉ `assertEqual(status)`). GREEN, mới thêm.
3. **Gỡ ảnh khỏi bài rồi đăng lại không xoá object** (CMS-05-AC5) — GREEN, mới thêm (mục CMS-05).
4. **2 người cùng sửa 1 bài** (CMS-03-AC7, CMS-07-AC6) — đã có sẵn từ trước, xác nhận vẫn chạy
   thật bằng thread song song (không phải giả lập tuần tự).
5. **F1 IDOR ảnh khi tạo bài** — RED thật, xem mục Lỗi B2.

## Phân quyền (bảng Group × hành động, tổng hợp 7 lô cũ + xác nhận lại)
| Group | Xem/soạn (ND-01) | Đăng/gỡ (ND-02) | Chuyên mục (ND-03) | API công khai |
|---|---|---|---|---|
| `chu` | ✅ | ✅ | ✅ | GET/HEAD/OPTIONS |
| `quan_ly` | ✅ | ✅ | ✅ | GET/HEAD/OPTIONS |
| `nv_kho` | 403 | 403 | 403 | GET/HEAD/OPTIONS |
| `nv_giao` | 403 | 403 | 403 | GET/HEAD/OPTIONS |
| User chỉ ND-01 | ✅ soạn | 403 | GET 200 / POST 403 | — |
| Chưa đăng nhập | 401 | 401 | 401 | GET/HEAD/OPTIONS; POST/PUT/PATCH/DELETE → 405/401 |

## Rò giá vốn
Không phát hiện rò rỉ. Mọi serializer công khai (`PublicEntrySerializer`,
`PublicEntryListSerializer`, `PublicCategorySerializer`, `PageByRoleSerializer`,
`FooterLinkSerializer`) khai trường tường minh, không `fields = "__all__"`. Quét đệ quy 15 khoá
cấm trên mọi response công khai đã kiểm trong lượt này — sạch.

## Rò dữ liệu cá nhân
Không phát hiện rò rỉ mới. `author` cố định "Cá Về"; `AuditLog` của các action `content_*` chỉ ghi
`entry_id`/`version`/`kind`/mã enum lý do — không chép tiêu đề hay chữ trong bài; máy quét SĐT che
đúng 3 số cuối; không log dữ liệu cá nhân (đọc `body/scan.py`, `services.py`, không có `logger`/
`print` in nội dung bài). Dữ liệu test dùng 100% giả.

## Hồi quy
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.content`
  → **96/96 PASS** (93 cũ + 3 mới).
- `manage.py makemigrations --check --dry-run` → không sinh gì mới.
- `cd erp-console && npm test -- --run` → **79/79 PASS** (9 test file).
- `cd erp-console && npm run build` (NEXT_PUBLIC_API_BASE=http://localhost:8104) → biên dịch
  thành công, 30 trang tĩnh.
- `cd frontend && npm run build` (NEXT_PUBLIC_USE_MOCK=0, NEXT_PUBLIC_API_BASE=:8104,
  NEXT_PUBLIC_SITE_ENV=staging) → biên dịch thành công, 10 trang tĩnh.
- Không chạy `npm ci` (theo hướng dẫn, dùng `node_modules` sẵn có).

---

## Lỗi

### B1 — Giá tiền hiển thị sai định dạng trên toàn bộ Shop và thẻ mặt hàng CMS · High · CMS-06-AC3/AC4
**Bước tái hiện:**
1. `curl http://localhost:8104/api/shop/catalog/CA-THU/` → `"price": "165000.00"` (chuỗi, đúng
   theo DRF `DecimalField`).
2. `frontend/lib/format.ts::formatVnd(amount)` gọi `amount.toLocaleString("vi-VN") + "đ"` — khi
   `amount` là **chuỗi** (không phải `number`), `String.prototype` không override
   `toLocaleString`, JS dùng `Object.prototype.toLocaleString` (chỉ gọi `toString()`), không format
   theo nghìn.
3. Mở `/shop/` (CatalogGrid), `/shop/item/?code=CA-THU`, hoặc bài viết CMS có `item_card` — giá
   hiện `"165000.00đ"` thay vì `"165.000 đ"`.

Xác nhận bằng Node: `Number("165000.00").toLocaleString("vi-VN")` → `"165.000"` (đúng);
`"165000.00".toLocaleString("vi-VN")` → `"165000.00"` (sai, y hệt bug quan sát được).

**Mong đợi:** CMS-06-AC3/AC4 và mọi nơi hiện giá trong Shop phải hiện đúng "260.000 đ" kiểu Việt.
**Thực tế:** hiện "260000.00đ" — sai định dạng, có thể gây hiểu nhầm giá (thiếu dấu phân cách
nghìn, thừa 2 số thập phân vô nghĩa với VNĐ).
**Ảnh hưởng:** Toàn bộ Shop công khai (`CatalogGrid.tsx`, `app/shop/item/page.tsx`,
`app/shop/orders/OrderLookup.tsx`, `features/checkout/*`) và thẻ mặt hàng CMS
(`features/content/components/ItemCard.tsx`) đều dùng chung `formatVnd`. Đây là bug **tiền-sản-
phẩm có sẵn từ trước CMS** (lộ ra từ commit nền `13e7d51`), không phải do đợt CMS gây ra, nhưng
trực tiếp làm fail AC hiển thị giá của CMS-06 mà QA trước đó không phát hiện (đọc code, không mở
trình duyệt thật với dữ liệu giá thật). **Không phải lỗi tính toán/sai tiền** (giá trị đúng, chỉ
sai cách hiển thị) nên không xếp Critical.
**Đề xuất sửa:** `formatVnd(amount: number | string)` ép `Number(amount)` trước khi
`toLocaleString`. Sửa 1 chỗ (`lib/format.ts`) là khắc phục toàn bộ Shop + CMS.
**Chưa có story P8 nào phủ** — đề xuất thêm 1 story nhỏ (Lô 6 hoặc 7) hoặc báo Duy xử lý riêng vì
ảnh hưởng ra ngoài phạm vi CMS.

### B2 — F1 IDOR ảnh khi TẠO bài mới · Medium · trùng SR-18 (P8, chưa làm)
**Bước tái hiện:** đã xác nhận lại bằng test Django thật (không chỉ đọc code):
`doc/features/2026-09-30-ra-soat-agy/repro/A5-f1-idor-cover-image-on-create.py` — user `quan_ly`
tạo bài A có ảnh id=1, rồi `POST /api/content/entries/` với `cover_image: 1` (ảnh của bài A) khi
tạo bài B mới → **201** (mong 400 `BR-ND-07`). Nguyên nhân: `entries/services.py` dòng ~157,
`if entry and not ContentImage.objects.filter(...)` — `entry is None` lúc tạo mới nên điều kiện
luôn bỏ qua kiểm tra "ảnh cùng bài".
**Trùng SR-18** (`doc/features/2026-09-30-sua-loi-review/02-stories.md`) — không mở lỗi mới, chỉ
xác nhận **vẫn còn tồn tại**, chưa được BE sửa.

### B3 — Tải lại trang khi mất mạng bị chặn bởi màn xác thực, không thấy được bản nháp đã khôi phục · Medium · CMS-04-AC2
**Bước tái hiện:** `doc/features/2026-09-30-ra-soat-agy/repro/A5-cms04-reload-offline-auth-gate.py`
— đăng nhập, mở bài nháp, gõ thêm chữ (lưu cục bộ qua `drafts.ts`), chặn mọi request tới backend
(mô phỏng API/mạng không gọi được, gồm cả `/api/auth/me/`), bắn sự kiện `offline` thật, rồi tải
lại trang.
**Mong đợi (CMS-04-AC2):** "sau khi tải lại, nội dung vừa gõ được khôi phục kèm thông báo".
**Thực tế:** `ConsoleGate` (`erp-console/features/auth/components/ConsoleGate.tsx`) bắt buộc gọi
lại `/api/auth/me/` mỗi lần tải trang; khi gọi lỗi, hiện toàn màn hình "Không kết nối được máy
chủ. Kiểm tra mạng rồi thử lại." + nút "Thử lại" / "Đăng nhập tài khoản khác" — **chặn hẳn** truy
cập màn soạn bài. Bản nháp KHÔNG mất (vẫn nằm nguyên trong `localStorage`), nhưng người dùng không
thấy được nó cho tới khi có mạng trở lại và xác thực lại thành công — đúng lúc họ cần nhất (ở
cảng, sóng yếu, vừa tải lại để kiểm tra bài).
**Ảnh hưởng:** không mất dữ liệu (không Critical), nhưng sai trải nghiệm so với AC ghi rõ trong
story; ảnh hưởng mọi màn ERP khác dùng chung `ConsoleGate`, không riêng CMS.
**Chưa có story P8 nào phủ đúng** (gần SR-20 nhưng SR-20 nói về tách code AI khỏi bundle, khác vấn
đề). Đề xuất: `ConsoleGate` cache phiên đăng nhập gần nhất (vd `sessionStorage`) để không chặn
UI khi chỉ mất mạng tạm thời, hoặc hiện lại nội dung đã cache trước khi gọi lại `/api/auth/me/`.

---

## Test mới đã thêm
**Backend (GREEN, giữ trong repo):**
- `backend/apps/content/tests/test_ra_soat_extra.py`
  - `DoubleClickUnpublishTests::test_double_click_unpublish_only_processed_once`
  - `DraftNotExposedByPublicApiTests::test_draft_slug_and_nonexistent_slug_return_identical_body`
  - `CoverImageNeverDeletedTests::test_removed_image_object_and_row_still_exist_after_republish`

**Frontend/ERP Playwright (GREEN, giữ trong repo, chạy thật trên backend `:8104`):**
- `frontend/e2e/ra_soat_cms13_public.py`
- `frontend/e2e/ra_soat_cms06_item_card.py` (3 kịch bản: baseline / after-price-change / after-deactivate)
- `frontend/e2e/ra_soat_cms14_landing.py` (2 kịch bản: normal / api-down)
- `erp-console/e2e/ra_soat_cms03_ac13_mobile.py`
- `erp-console/e2e/ra_soat_cms05_upload_mobile.py`
- `erp-console/e2e/ra_soat_cms04_autosave.py`
- `erp-console/e2e/ra_soat_cms11_ac3_restore_confirm.py`

**Repro lỗi thật (ĐỎ, KHÔNG trong cây test sản phẩm):**
- `doc/features/2026-09-30-ra-soat-agy/repro/A5-f1-idor-cover-image-on-create.py` (B2, trùng SR-18)
- `doc/features/2026-09-30-ra-soat-agy/repro/A5-cms04-reload-offline-auth-gate.py` (B3, mới)

## Lệnh đã chạy (kèm output tóm tắt)
```
manage.py test apps.content                          → Ran 96 tests ... OK (trước khi thêm: 93 OK)
manage.py test apps.content.tests.test_ra_soat_extra  → Ran 3 tests ... OK
manage.py makemigrations --check --dry-run            → No changes detected
erp-console: npm test -- --run                        → 9 files, 79 tests passed
erp-console: npm run build (API_BASE=:8104)            → 30/30 static pages
frontend: npm run build (USE_MOCK=0, API_BASE=:8104, SITE_ENV=staging) → 10/10 static pages
backend runserver :8104 (dev sqlite, CORS mở :3104/:3204) + manage.py seed_demo
python3 frontend/e2e/ra_soat_cms13_public.py           → PASS (chạy 3 lần liên tiếp, ổn định)
python3 frontend/e2e/ra_soat_cms06_item_card.py {baseline,after-price-change,after-deactivate} → PASS x3
python3 frontend/e2e/ra_soat_cms14_landing.py {normal,api-down}                → PASS x2
python3 erp-console/e2e/ra_soat_cms03_ac13_mobile.py    → PASS
python3 erp-console/e2e/ra_soat_cms05_upload_mobile.py  → PASS
python3 erp-console/e2e/ra_soat_cms04_autosave.py       → PASS
python3 erp-console/e2e/ra_soat_cms11_ac3_restore_confirm.py → PASS
python3 doc/features/2026-09-30-ra-soat-agy/repro/A5-f1-idor-cover-image-on-create.py       → FAIL đúng như kỳ vọng (chứng minh lỗi B2)
python3 doc/features/2026-09-30-ra-soat-agy/repro/A5-cms04-reload-offline-auth-gate.py       → FAIL đúng như kỳ vọng (chứng minh lỗi B3)
```

## Dữ liệu QA để lại trên SQLite dev cục bộ (không phải staging/production)
`backend/db.sqlite3` (máy cục bộ): 2 user `ra_soat_quanly`/`ra_soat_kho` (mật khẩu `RaSoat123!`,
dữ liệu giả), category `Ra soat QA` (id=1), 4 bài Entry test (id 2–4, tiêu đề có ghi rõ "du lieu
gia"/"ra-soat"). Có thể xoá an toàn bất cứ lúc nào (không phải chứng từ nghiệp vụ thật).
