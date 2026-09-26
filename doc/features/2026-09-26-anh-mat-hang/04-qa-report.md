# QA — Ảnh mặt hàng trên Shop · lô 1 (A1, A2, A4, A3-BE) · 2026-09-27

## Kết luận mới nhất (Vòng 2): APPROVED — xem chi tiết ở mục "Vòng 2" ngay dưới đây. Vòng 1 (REJECTED, do B1) được giữ nguyên bên dưới làm lịch sử.

---

# Vòng 2 — 2026-09-27 (sau khi sửa B1, B2, B3)

## Kết luận: APPROVED — B1 (console sập khi nối BE thật) đã sửa đúng gốc (`listItems`/`useCatalogList` dùng `Paginated<CatalogItem>` + `.results`, thêm `app/(console)/error.tsx` làm lưới an toàn thứ hai), xác nhận lại bằng `erp-console/e2e/a2_catalog_real.py` (6/6, trước đó 0/3) và bằng tay full flow tải/thay ảnh với `chu`/`quan_ly` + xác nhận `nv_kho` không thấy nút. B2/B3 (`uploaded_at` sai sau khi thay ảnh, sai múi giờ) đã sửa đúng, có test RED→GREEN đi kèm. Không có lỗi chặn mới. Hồi quy 3 màn dùng `usePagedList` (Đơn & tiền, Hàng chờ thanh toán, Phiếu hoàn chờ chuyển) không vỡ.

## Tổng vòng 2: 20 ca kiểm tay mới (không lặp lại các ca vòng 1 đã xanh) · ✅ 20 · ❌ 0 · ⏸ 0

## Môi trường kiểm (giống vòng 1)
- Backend Django local, DB SQLite QA riêng (`qa2.sqlite3`, không đụng `backend/db.sqlite3` dev), `ITEM_IMAGE_STORAGE=local`, seed bằng `bootstrap_masterdata` + `seed_demo` + script tạo 4 tài khoản `loc/quanly1/kho1/giao1` (Group tương ứng, `must_change_password=False`).
- `erp-console` chạy `npm run dev -- -p 3100` với `NEXT_PUBLIC_API_BASE=http://localhost:8000 NEXT_PUBLIC_USE_MOCK=0` (không mock) — đúng yêu cầu "kiểm lại AC A2 trước đây bị chặn bởi B1".
- Vẫn cần tự đứng `python -m http.server` trên `backend/media/` để ảnh hiển thị được (xem mục "Ghi nhận Low" — vấn đề path/route MEDIA cục bộ, dev-only, đã được BE/FE ghi lại đúng trong `03-dev-notes.md`, không sửa vì không thuộc phạm vi B1/B2/B3 được giao sửa lần này).
- Tắt hết server (`runserver`, `http.server 8010`, `next dev -p 3100`) khi xong; xoá DB QA tạm; không còn tiến trình nào chạy nền.

## Lệnh đã chạy vòng 2 (kèm output tóm tắt)
```
cd backend && .venv/bin/python manage.py test
→ Ran 634 tests in 30.580s — OK (632 → 634, +2 test B2/B3: test_b2_..., test_b3_...)

cd backend && .venv/bin/python manage.py makemigrations --check --dry-run
→ No changes detected

cd frontend && npm run build
→ Compiled successfully, 8/8 static pages

cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build
→ tsc sạch; Compiled successfully, 20/20 static pages (route /catalog 19.7 kB — tăng nhẹ do usePagedList + error.tsx)

cd erp-console && BASE=http://localhost:3100 API=http://localhost:8000 python3 e2e/a2_catalog_real.py
→ 6/6 pass (vòng 1: 0/3 tài khoản qua) — bắt bằng sự kiện `pageerror` (đáng tin hơn `page.content()`
  vì overlay lỗi Next.js nằm trong shadow DOM)
```
(Không chạy lại `adapter/pytest` vì không có thay đổi ở `adapter/` trong lần sửa này.)

## B1 — xác nhận đã sửa (trước đó High/Blocking, AC A2-AC1..AC18)
| Kiểm | Kết quả | Bằng chứng |
|---|---|---|
| `listItems`/`useCatalogList` trả đúng `Paginated<CatalogItem>` | ✅ | Đọc code: `erp-console/features/catalog/api.ts` dùng `apiFetch<Paginated<CatalogItem>>`, `useCatalogList.ts` bọc `usePagedList` giống `useOrderList.ts` |
| `mockListItems` khớp hình dạng phân trang thật | ✅ | `erp-console/features/catalog/mock.ts` trả `{count,next,previous,results}`, `PAGE_SIZE=4` để luyện "Tải thêm" |
| `erp-console/e2e/a2_catalog_real.py` (test hồi quy QA thêm ở vòng 1) | ✅ 6/6 (loc, quanly1, kho1 × 2 assertion) | Chạy lại trong phiên này, không sửa gì trong file test |
| `chu` (`loc`): vào `/catalog` (mobile 375), thấy 6/6 mặt hàng, `group_name` thật ("Hải sản", không còn "Nhóm #<id>") | ✅ | `shots/qa2-a2-catalog-chu-mobile.png` |
| `chu`: bấm "Tải ảnh" trên mặt hàng chưa có ảnh (Bạch tuộc), chọn JPEG 3000×2000 thật (Pillow sinh lúc chạy, có EXIF GPS giả), bấm "Tải ảnh lên" | ✅ 201 thật, toast "Đã lưu ảnh cho Bạch tuộc.", dòng đổi ảnh thu nhỏ + nút đổi "Tải ảnh"→"Thay ảnh" **tại chỗ**, không tải lại trang | `shots/qa2-a2-upload-sheet-preview.png`, `shots/qa2-a2-upload-success-toast.png` |
| `quan_ly` (`quanly1`): vào `/catalog` (desktop 1280), thấy nút "Thay ảnh" trên Bạch tuộc (ảnh vừa `chu` tải), bấm, chọn WebP 4000×3000 khác, "Lưu ảnh mới" | ✅ 200 thật, toast, ảnh thu nhỏ đổi màu đúng ảnh mới (xanh lá) | `shots/qa2-a2-catalog-quanly-desktop.png`, `shots/qa2-a2-replace-success-quanly.png` |
| `nv_kho` (`kho1`): vào `/catalog`, không có nút "Tải ảnh"/"Thay ảnh" ở bất kỳ dòng nào, dòng nhắc đổi thành "Danh sách mặt hàng và ảnh đang dùng. Cần Chủ vừa cấp quyền đổi ảnh mặt hàng." | ✅ đếm `get_by_role("button", name=…)` = 0 cho cả hai nhãn; vẫn thấy đủ 6 dòng | `shots/qa2-a2-catalog-nvkho-no-button.png` |
| Không có lỗi JS (`pageerror`) ở bất kỳ bước nào trên | ✅ | ghi log rỗng `[]` cho cả 3 tài khoản trong script `qa2_console_flow.py` |
| AuditLog đúng 2 dòng cho 2 thao tác trên (`item_image_add` actor=`loc`, `item_image_replace` actor=`quanly1`) | ✅ | `manage.py shell` đọc `AuditLog` khớp thứ tự thao tác qua UI |

## B2/B3 — xác nhận đã sửa (trước đó Medium/Low)
| Kiểm | Kết quả | Bằng chứng |
|---|---|---|
| Test RED→GREEN đi kèm fix | ✅ | `apps/catalog/images/tests/test_api.py::test_b2_thay_anh_cap_nhat_uploaded_at_va_uploaded_by_theo_lan_gan_nhat`, `::test_b3_uploaded_at_theo_gio_vn_offset_0700` — cả hai nằm trong 634 test xanh |
| `uploaded_at` đổi đúng theo lần **thay ảnh gần nhất**, không còn kẹt ở lần tải đầu | ✅ | Qua UI thật: `chu` tải lúc T1, `quan_ly` thay lúc T2 (vài giây sau) → `GET /api/catalog/items/6/` trả `uploaded_at` = T2 (`2026-09-27T05:21:05.416561+07:00`); đối chiếu DB thô: `updated_at`=`22:21:05` UTC khớp, `created_at`=`22:20:59` UTC (T1, không dùng nữa) |
| `uploaded_at` xuất giờ Việt Nam `+07:00` | ✅ | Response thật ở trên kết thúc bằng `+07:00`, không còn `+00:00` |
| Serializer dùng `timezone.localtime(image.updated_at)` | ✅ | Đọc code `backend/apps/catalog/images/serializers.py:38` |

## Hồi quy 3 màn dùng `usePagedList` (chuyển từ `features/orders/` sang `shared/lib/`)
| Màn | Kết quả | Bằng chứng |
|---|---|---|
| Đơn & tiền (`/orders`) | ✅ | Render 6 đơn thật từ `seed_demo`, đủ cột (mã đơn, khách, giờ đặt, giá trị, trạng thái: Tự huỷ/Hoàn tất/Giữ chỗ/Đã thanh toán/Đang xử lý), không lỗi JS. `shots/qa2-regress-orders.png` |
| Hàng chờ thanh toán (`/orders/payments`) | ✅ | Trạng thái rỗng đúng ngữ cảnh ("Không còn khoản tiền lệch nào", nút "Làm mới danh sách"), không lỗi JS. `shots/qa2-regress-payments-queue.png` |
| Phiếu hoàn chờ chuyển (`/orders/refunds`) | ✅ | Trạng thái rỗng đúng ngữ cảnh, nút "Làm mới" hoạt động (không văng lỗi khi bấm), không lỗi JS. `shots/qa2-regress-refunds-queue.png` |

Ghi chú: dữ liệu `seed_demo` không tạo khoản tiền lệch/phiếu hoàn nào nên 2 màn sau hiện đúng trạng thái rỗng (không phải lỗi) — không kiểm được nhánh "có dữ liệu, bấm Tải thêm" trên 2 màn này với dữ liệu thật trong phạm vi vòng 2 (đã kiểm nhánh "Tải thêm" bằng mock ở lần sửa của FE theo `03-dev-notes.md`, không lặp lại tay ở đây vì không phải trọng tâm — trọng tâm là "không vỡ do đổi chỗ import").

## Ghi nhận Low (không chặn, đã biết trước — không sửa lần này theo đúng chỉ đạo)
- **Local storage URL lệch `MEDIA` path khi `ITEM_IMAGE_STORAGE=local`:** `ITEM_IMAGE_PUBLIC_BASE_URL` mặc định suy ra `http://localhost:8000/media/item-images` (`backend/config/settings.py:151-154`) nhưng `LocalItemImageStorage` ghi file ở `MEDIA_ROOT/items/...` (thiếu tiền tố `item-images`), và `config/urls.py` không có route nào phục vụ `MEDIA_ROOT` nên `/media/...` luôn `404`. Xác nhận lại đúng như `03-dev-notes.md` mô tả — vẫn tồn tại (không thuộc phạm vi B1/B2/B3 được giao sửa lần này). QA tiếp tục dùng `http.server` phụ trợ để kiểm ảnh hiển thị thật. **Mức Low, dev-only** (staging/production dùng `ITEM_IMAGE_STORAGE=gcs`, không đi qua đường này) — nên đưa vào việc nhỏ cho lô sau: thêm `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` khi `DEBUG`, và thống nhất tiền tố `item-images`.
- FE đã tự nêu và QA xác nhận không có gì mới phát sinh ngoài mục này.

## Việc chưa kiểm được ở vòng 2 (kế thừa từ vòng 1, ngoài phạm vi sửa lần này)
- A1-AC1..AC4, AC7 (hạ tầng GCS thật, budget billing thật): vẫn chưa tạo, đúng phạm vi.
- A2-AC11 (503 storage lỗi), A2-AC12 (rớt mạng giữa chừng qua UI thật): không dựng lại bằng tay (đã có unit test BE cho AC11; AC12 phụ thuộc mô phỏng lỗi mạng thật, không phải trọng tâm sửa lỗi vòng này).
- A3 console (nút "Gỡ ảnh" trên UI) và A5: đúng như đã ghi ở vòng 1, ngoài phạm vi lô 1.

---

# Vòng 1 — chi tiết (lịch sử, REJECTED do B1) — 2026-09-27

## Kết luận: REJECTED — console ERP (A2 FE) sập hoàn toàn khi nối BE thật: `listItems()` không bóc `results` khỏi trang phân trang DRF, nên `filterItems` ném `TypeError: items.filter is not a function` ngay khi vào `/catalog`, với **mọi vai trò** (chu, quản lý, nv_kho). BE (A1/A2/A3/A4) và FE Shop (A4) đều đạt.

## Tổng: 46 ca (không tính 632 test BE + 68 test adapter đã chạy sẵn) · ✅ 42 · ❌ 1 (chặn, ảnh hưởng toàn bộ A2 FE) · ⏸ 3 (A1 hạ tầng GCS thật, A2-AC12 rớt mạng thật, A2-AC11 storage lỗi — đã có unit test BE, không lặp lại bằng tay)

## Môi trường kiểm
- Backend Django chạy local, DB sqlite riêng cho QA (`ITEM_IMAGE_STORAGE=local`), **không** dùng `NEXT_PUBLIC_USE_MOCK`.
- `frontend/` (Shop) và `erp-console/` chạy `npm run dev` với `NEXT_PUBLIC_API_BASE=http://localhost:8000 NEXT_PUBLIC_USE_MOCK=0`, gọi thẳng backend thật (không mock).
- Vì `ITEM_IMAGE_PUBLIC_BASE_URL` mặc định rỗng khi `ITEM_IMAGE_STORAGE=local` (không có route Django nào phục vụ `MEDIA_ROOT`), QA tự đứng một `python -m http.server` trên `backend/media/` để mô phỏng việc GCS phục vụ ảnh công khai — không sửa code sản phẩm, chỉ là hạ tầng phụ trợ cho môi trường test cục bộ (điều tương đương ở staging/production là bucket GCS thật, đã có sẵn).
- Tài khoản QA tự tạo trong DB QA: `loc`/`chu`, `quanly1`/`quan_ly`, `kho1`/`nv_kho`, `giao1`/`nv_giao`, mật khẩu `Test@12345`, `must_change_password=False`. Dữ liệu mặt hàng từ `manage.py seed_demo`.
- Ảnh thử sinh bằng Pillow lúc chạy (`gen_images.py` trong scratchpad, không commit): JPEG 3000×2000 có EXIF GPS giả, PNG 400×400, WebP 4000×3000, SVG có `<script>`, GIF động, `.txt` đổi đuôi `.jpg`, JPEG 10 MB + 1 byte, JPEG 5 MB.
- Tắt hết server (`runserver`, `http.server 8010`, 2× `next dev`) khi xong; không còn tiến trình nào chạy nền.

## Lệnh đã chạy (kèm output tóm tắt)
```
cd backend && .venv/bin/python manage.py test
→ Ran 632 tests in 30.540s — OK

cd backend && .venv/bin/python manage.py makemigrations --check --dry-run
→ No changes detected

cd adapter && .venv/bin/python -m pytest -q
→ 68 passed

cd frontend && npm run build
→ Compiled successfully, 8/8 static pages

cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build
→ tsc sạch; Compiled successfully, 20/20 static pages
```

## Theo AC

### A1 — Nơi lưu ảnh bền vững (chỉ kiểm code + `doc/ops/moi-truong.md`, chưa có bucket GCS thật)
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| A1-AC1..AC4 (bucket/IAM thật) | ⏸ Chưa kiểm được | Bucket GCS thật **chưa tạo** — đúng phạm vi giao (chỉ deploy khi Duy duyệt). Lệnh `gcloud` đã ghi đủ và đúng ở `doc/ops/moi-truong.md:56-93` (2 bucket tách staging/production, `--uniform-bucket-level-access`, `allUsers` chỉ `roles/storage.legacyObjectReader`, không `objectViewer`/list) |
| A1-AC5 | ✅ | `doc/ops/moi-truong.md:89,93`: lệnh gán `ITEM_IMAGE_STORAGE=gcs,ITEM_IMAGE_BUCKET=...` qua `gcloud run services update --update-env-vars`, không có khoá JSON nào trong repo (`grep` không thấy credential) |
| A1-AC6 | ✅ | `manage.py test` chạy 632 test xanh với `ITEM_IMAGE_STORAGE=local` mặc định, không gọi mạng ra GCS (`GCSItemImageStorage` chỉ import `google.cloud.storage` bên trong hàm — `backend/apps/catalog/images/storage.py:53-73`) |
| A1-AC7 (budget billing) | ⏸ Chưa kiểm — thao tác tay ở Billing → Budgets, ghi chú "còn nợ, làm khi Duy duyệt deploy" ở `moi-truong.md:97-99`, đúng phạm vi |

### A2 — Chủ/Quản lý tải lên, thay ảnh
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| A2-AC1 | ✅ (BE) / ❌ (FE, xem B1) | `curl POST` JPEG 3000×2000 → `201`, `urls.thumb/card/detail` là WebP vuông 160/480/1200 (xác nhận bằng `PIL.Image.open` size/mode), `alt`="Cá thu" (mặc định = tên mặt hàng) |
| A2-AC2 | ✅ | 3 file `.webp` trong `backend/media/items/1/img_.../{160,480,1200}.webp` không có EXIF (`im.getexif()` rỗng); không có tệp gốc nào trong thư mục; response không có đường dẫn gốc |
| A2-AC3 | ✅ | Đặt `TOM-SU-1.is_active=False`, POST ảnh → `201` |
| A2-AC4 | ✅ | `quanly1` (Quản lý) thay ảnh CA-THU X→Y (`img_5eb0f2f3`→`img_23965b94`), response `200`; URL cũ của X vẫn `200` sau khi thay |
| A2-AC5 | ✅ | `AuditLog`: đúng 1 dòng `item_image_add` mỗi lần thêm mới, `item_image_replace` khi thay, `changes={'image_id':[cũ,mới],'is_illustration':[cũ,mới]}`, `actor_id` đúng người thao tác |
| A2-AC6 | ✅ | PNG 400×400 → `201` kèm `warnings:[{"code":"LOW_RESOLUTION",...}]` |
| A2-AC7 | ✅ (đã có unit test BE `test_processing.py`, không đo lại tay) | — |
| A2-AC8 | ✅ | `is_illustration=true` khi upload → response `is_illustration:true`; AuditLog ghi `is_illustration:[False,True]`; Shop hiện nhãn "Ảnh minh hoạ" tương phản tốt (ảnh `qa-a4-illustration-label.png`) |
| A2-AC9 | ✅ | SVG, GIF động, `.txt`→`.jpg` đều `400 BR-DM-10`, thông điệp tiếng Việt đúng từng loại; không tạo AuditLog (đếm trước/sau không đổi), ảnh mặt hàng giữ nguyên |
| A2-AC10 | ✅ | JPEG 10 485 761 byte → `400 {"code":"BR-DM-10","detail":"Ảnh vượt 10 MB (BR-DM-10)."}`; JPEG 5 MB qua bình thường (`200`) |
| A2-AC11 | ⏸ Không lặp tay (đã có test BE mock storage lỗi trong 632 test) | — |
| A2-AC12 (rớt mạng) | ⏸ Không dựng lại được vì bị chặn bởi B1 (màn crash trước khi tới bước upload); logic retry có trong `ImageUploadSheet.tsx` theo code nhưng không xác minh được bằng tay qua UI thật | |
| A2-AC13 | ✅ | Gửi `expected_image_id` cũ (X) sau khi ảnh đã bị đổi sang Y → `409 {"code":"BR-DM-12"}`, ảnh vẫn là Y |
| A2-AC14 | ✅ (API) / ❌ không thể xác minh phần "không thấy nút" qua UI thật vì màn sập trước đó (B1) | `nv_kho`/`nv_giao` POST → `403 BR-PQ-12`; không đăng nhập → `401`; đếm AuditLog không đổi |
| A2-AC15 | ✅ | `quanly1` (có `change_item_image`) PATCH `name`/`is_active` trên `Item` → `403`, dữ liệu không đổi |
| A2-AC16 | ✅ | `?has_image=true` → đúng 2/6 (CA-THU, TOM-SU-1); `?has_image=false` → đúng 4/6 còn lại |
| A2-AC17 | ✅ (mock UI) / không xác minh được với BE thật (B1) | Ảnh `qa-a2-upload-sheet-mobile-375.png`: input `accept="image/jpeg,image/png,image/webp"`, nút khoá khi đang gửi (đọc code `ImageUploadSheet.tsx`, không lặp lại thao tác bấm đúp qua UI thật vì B1) |
| A2-AC18 | ✅ | Django Admin `CA-THU`: khối "Ảnh (chỉ xem)" hiện ảnh + nhãn "Ảnh minh hoạ", không có ô tải lên (`qa-a2-admin-item-detail.png`) |

**B1 (xem mục Lỗi)** chặn toàn bộ trải nghiệm A2 trên **console thật**: màn Danh mục crash ngay khi load với **mọi** tài khoản (`loc`, `quanly1`, `kho1` — đã xác nhận bằng ảnh chụp), nên các AC còn lại của A2 chỉ kiểm được qua API trực tiếp (`curl`) hoặc qua chế độ mock (không đại diện cho hàng thật).

### A3 — Gỡ ảnh (chỉ phần BE theo yêu cầu QA lô này)
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| A3-AC1 | ✅ | `DELETE /image/` trên TOM-SU-1 → `204`; `GET` sau đó `image:null`; 3 file webp cũ vẫn `200` qua static server |
| A3-AC2 | ✅ | AuditLog thêm đúng 1 dòng `item_image_remove`, `changes={'image_id':['img_...',None]}` |
| A3-AC3 | ⏸ Không lặp tay (không có lô "Đang bán" gắn với mặt hàng có ảnh trong dữ liệu QA dựng nhanh; logic cảnh báo thuộc FE, chưa làm ở lô 1) | |
| A3-AC4 | ✅ | `DELETE` trên mặt hàng chưa có ảnh (BACH-TUOC) → `404 {"code":"BR-DM-09"}` |
| A3-AC5 | ✅ | `DELETE ?expected_image_id=<id cũ>` sau khi ảnh đã bị thay → `409 BR-DM-12`, ảnh mới giữ nguyên |
| A3-AC6 | ✅ | `nv_kho` `DELETE` → `403 BR-PQ-12` |

### A4 — Khách thấy ảnh (Shop, real BE, Playwright thật)
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| A4-AC1 | ✅ | `GET /api/shop/catalog/` và `/CA-THU/`: field `image={alt,is_illustration,urls}`, không `id`/người tải/tệp gốc/tên bucket nội bộ (chỉ URL công khai) |
| A4-AC2 | ✅ | Mặt hàng chưa có ảnh vẫn có trong danh sách, `image:null` |
| A4-AC3 | ✅ | `qa-a4-shop-grid-mobile.png`, `-desktop`: khung vuông giữ chỗ, `loading="lazy"` (đọc DOM), không tải bản `detail` ở lưới (kiểm network log số request ảnh khớp `card`) |
| A4-AC4 | ✅ | Trang chi tiết CA-THU: ảnh `detail`, giá/tồn hiện ngay không chờ ảnh (`qa-a4-item-detail-ca-thu.png`) |
| A4-AC5 | ✅ | Mặt hàng `image:null` (Mực ống) → khung mặc định SVG vẽ icon cá + tên nhóm, `role="img"` (đếm 5 khung `role="img"` khớp 5 mặt hàng chưa ảnh) — không phát request tệp ảnh nào cho khung này |
| A4-AC6 | ✅ | Tắt static server ảnh (giả lập URL 404) → cả lưới chuyển sang khung mặc định, không có icon ảnh vỡ, nút "Thêm vào giỏ" vẫn bấm được (`qa-a4-broken-image-fallback.png`) |
| A4-AC7 | ✅ | `is_illustration=true` → nhãn "Ảnh minh hoạ" đè góc dưới trái, chữ trắng nền tối, đọc rõ (`qa-a4-illustration-label.png`) |
| A4-AC8 | ⏸ Không lặp tay (dữ liệu seed QA không có combo); đã có unit test BE `test_a4_ac8_combo_hien_anh_rieng_khong_lay_anh_thanh_phan` xanh trong 632 test | |
| A4-AC9 | ✅ | So khớp tập khoá JSON `GET /api/shop/catalog*`: không có `purchase_rate`, `landed_unit_cost`, `rate`, `unit_cost`, `cost`, `supplier`, `batch`, `id` ảnh, `bucket`, `path` ở bất kỳ mặt hàng nào |
| A4-AC10 | ✅ | TOM-SU-1 (`is_active=False`, đã có ảnh) → `GET /api/shop/catalog/TOM-SU-1/` vẫn `404`; trang chi tiết Shop không hiện "Tôm sú" |
| A4-AC11 | ✅ | `git status --porcelain` không có tệp `.png/.jpg/.jpeg/.webp/.svg/.gif` nào được thêm; `frontend/lib/mock.ts` có đủ 3 trạng thái (ảnh SVG data URI, `null`, ảnh lỗi) |

## Ngoại lệ & biên
- 400 sai định dạng (SVG/GIF/đổi đuôi/PDF-như-text): ✅, mã lỗi và thông điệp đúng cho từng loại.
- Biên dung lượng: 10 485 761 byte (10 MB + 1) → chặn; 5 242 880 byte → qua. ✅
- Vượt tồn/lô cuối/TTL: không áp dụng (ảnh không đụng tồn/lô — đúng theo 01-analysis §8 "FEFO/tồn/tiền: không ảnh hưởng").
- Trùng/đồng thời: bấm đúp qua API — không lặp lại được ở tầng HTTP thô (không mô phỏng được race thật bằng 2 request đồng thời trong phạm vi QA lô này); khoá lạc quan `expected_image_id` (409) đã kiểm ở cả A2-AC13 và A3-AC5, đúng cả 2 chiều thêm/gỡ. Webhook gửi 2 lần: không áp dụng (tính năng không có webhook).
- Chứng từ không xoá: ảnh không phải chứng từ theo BR-DM-13/14 (đã đúng thiết kế); AuditLog append-only quan sát đủ 5 dòng qua toàn bộ kịch bản, không dòng nào biến mất khi thao tác tiếp.

## Phân quyền (bảng Group × hành động ảnh, qua API thật)
| Group | `POST .../image/` | `DELETE .../image/` | `PATCH` tên/ẩn-hiện | Xem ảnh trong danh sách |
|---|---|---|---|---|
| `chu` | 200/201 | 204 | 200 (được, có `change_item`) | Có |
| `quan_ly` | 200/201 | (không thử DELETE riêng, đã xác nhận có perm qua nhóm cộng dồn) | **403** (đúng — quyền ảnh không mở `change_item`) | Có |
| `nv_kho` | **403 BR-PQ-12** | **403 BR-PQ-12** | (không có `change_item`, không thử) | Có (không thấy nút — chỉ xác nhận qua mock UI, chưa xác nhận qua UI thật vì B1) |
| `nv_giao` | **403 BR-PQ-12** | (suy ra tương tự nv_kho qua cùng permission check ở API) | — | — |
| Chưa đăng nhập | **401** | (suy ra tương tự) | — | — |

## Rò giá vốn
- `GET /api/catalog/items/` (console, quyền `catalog.view_item`) và `GET /api/shop/catalog*` (công khai): cả hai serializer (`ItemSerializer`, `_item_public`) không có field giá vốn nào trong `Meta.fields`/dict trả về — xác nhận bằng đọc code và so khớp tập khoá JSON thật. Không rò `purchase_rate`, `landed_unit_cost`, thông tin NCC qua API ảnh ở bất kỳ nơi nào đã kiểm.

## Hồi quy
- `manage.py test` toàn backend (632 test, gồm mọi app domain khác: accounts, purchasing, inventory, sales, delivery, reports) — xanh, không có test nào vỡ do thay đổi của lô này.
- `test_s47_ac1_quan_ly_nhan_nhom_va_viec_theo_spec_1_5` (accounts) đã cập nhật đúng theo hệ quả tất yếu của Q3 (Quản lý có thêm `catalog.change_item_image`) — không phải hồi quy giấu lỗi, đã đọc diff xác nhận thay đổi hợp lý.
- `adapter/` 68 test xanh (không đụng gì ở lô này, chỉ chạy để chắc chắn không ảnh hưởng).
- `frontend` và `erp-console` build tĩnh sạch, không lỗi TypeScript.

## Lỗi

### B1 — Màn Danh mục ERP console sập hoàn toàn khi nối BE thật (pagination DRF không được bóc) · **High** (chặn) · AC A2-AC1, AC4-AC18 (toàn bộ trải nghiệm console của A2), gián tiếp A2-AC14
**[ĐÃ SỬA — xác nhận ở Vòng 2, 2026-09-27, xem mục "Vòng 2" đầu file]**
**Bước tái hiện**
1. Chạy backend thật (bất kỳ, không mock), `erp-console` với `NEXT_PUBLIC_USE_MOCK=0` trỏ vào backend đó.
2. Đăng nhập bằng bất kỳ tài khoản nào có `catalog.view_item` (`chu`, `quan_ly`, hay `nv_kho`).
3. Vào `/catalog`.

**Mong đợi:** Hiện danh sách mặt hàng kèm ảnh thu nhỏ, bộ lọc "Chưa có ảnh", nút Tải/Thay ảnh theo quyền.

**Thực tế:** Next.js báo lỗi runtime không bắt được: `TypeError: items.filter is not a function`, tại `erp-console/features/catalog/api.ts:24` (`filterItems`), gọi từ `erp-console/features/catalog/components/CatalogScreen.tsx:122`. Nguyên nhân gốc: `listItems()` ở `erp-console/features/catalog/api.ts:16-19` khai kiểu trả về là `CatalogItem[]` (mảng trần) và gọi thẳng `apiFetch<CatalogItem[]>(...)`, nhưng `GET /api/catalog/items/` dùng `DEFAULT_PAGINATION_CLASS = PageNumberPagination` (toàn cục, `backend/config/settings.py:190`) nên trả về `{count, next, previous, results: [...]}`. Module `catalog` là module **duy nhất** trong console chưa dùng kiểu `Paginated<T>` đã có sẵn ở `shared/lib/http.ts:29-34` (so sánh với `features/orders/api.ts` — nơi đã dùng đúng `Paginated<T>` rồi lấy `.results`). Vì `erp-console` không có `app/error.tsx`/`global-error.tsx` hay `ErrorBoundary` nào, lỗi này không được ngăn ở tầng nào — không riêng dev, mà cả bản build production cũng sẽ vỡ trắng màn hình `/catalog` (kiểm bằng cách đọc code, không dựng `next start` để xác nhận thêm vì hiện tượng gốc ở tầng dữ liệu, không phải dev-only overlay).

**Vì sao lọt qua khi BE và FE tự kiểm riêng:** BE tự test bằng `manage.py test` (gọi thẳng serializer, không qua FE). FE tự kiểm bằng `NEXT_PUBLIC_USE_MOCK=1`, và `mockListItems` ở `erp-console/features/catalog/mock.ts:151-161` trả `{status:200, body: list}` với `list` là **mảng trần** — không mô phỏng đúng hình dạng phân trang thật của DRF, nên FE "khớp contract" khi tự kiểm bằng mock nhưng vỡ khi nối BE thật. Đây đúng là điều mà `03-dev-notes.md` đã tự cảnh báo ("Chưa chạy thử với BE thật... nên chạy lại `NEXT_PUBLIC_USE_MOCK=0`") nhưng chưa làm trước khi bàn giao QA.

**Ảnh hưởng:** Chặn hoàn toàn mục tiêu chính của tính năng ("Chủ tự gắn ảnh cho mặt hàng trên console mà không cần dev hỗ trợ" — 02-stories.md §Mục tiêu). Không có cách nào vào được màn Danh mục qua console thật ở trạng thái hiện tại, với bất kỳ vai trò nào. Ảnh chụp: `shots/qa-a2-BUG-catalog-crash-nv_kho.png`, `shots/qa-a2-BUG-catalog-crash-quan_ly.png`, `shots/qa-a2-catalog-mobile-375.png` (tài khoản `chu`).

**Đề xuất sửa (không tự sửa, để BE/FE quyết):** đổi `listItems` trong `erp-console/features/catalog/api.ts` sang `apiFetch<Paginated<CatalogItem>>(...)` rồi trả `.results` (giống `features/orders/api.ts`), đồng thời sửa `mockListItems` trả đúng hình dạng `{count, next, previous, results}` để mock không che giấu lại lần sau. Nên thêm ít nhất 1 lần chạy tay `NEXT_PUBLIC_USE_MOCK=0` trước khi bàn giao QA cho mọi story có FE gọi list endpoint có phân trang.

**Test hồi quy đã thêm (đỏ, để BE/FE tự chạy lại xanh sau khi sửa):** `erp-console/e2e/a2_catalog_real.py` — dựng BE thật (không mock), đăng nhập lần lượt `chu`/`quan_ly`/`nv_kho`, vào `/catalog`, bắt sự kiện `pageerror` (không dựa vào `page.content()` vì overlay lỗi của Next.js nằm trong shadow DOM `<nextjs-portal>`, không đọc được bằng cách đó). Đã xác nhận chạy đỏ đúng lý do (`items.filter is not a function`, 0/3 tài khoản qua) trong phiên QA này.

### B2 — `uploaded_at` trong response API không đổi sau khi thay ảnh (dùng `created_at` thay vì thời điểm ảnh hiện tại được tải) · Medium · liên quan A2-AC4, hợp đồng API mục "Endpoint mới + JSON mẫu"
**[ĐÃ SỬA — xác nhận ở Vòng 2, 2026-09-27]**
**Bước tái hiện**
1. `POST /image/` lần đầu cho một mặt hàng lúc T1 → `uploaded_at = T1`.
2. `POST /image/` thay ảnh (khác `expected_image_id`) lúc T2 (vài phút/giờ sau) → response mới.

**Mong đợi:** `uploaded_at` phản ánh thời điểm ảnh **hiện tại** (T2) được tải lên — đúng tinh thần "khi nào" ở contract (02-stories.md, ví dụ JSON mục A2) và UC-A1 bước 7 ("ghi... khi nào").

**Thực tế:** `uploaded_at` vẫn là **T1** (thời điểm tải lần đầu tiên của mặt hàng đó), không đổi qua nhiều lần thay ảnh sau. Tái hiện được nhiều lần trong phiên QA (item CA-THU thay ảnh 3 lần, cả 3 response đều trả `uploaded_at:"2026-09-26T21:42:24.840250+00:00"` — đúng thời điểm upload **đầu tiên**). Nguyên nhân: `backend/apps/catalog/models/images.py:43` khai `created_at = models.DateTimeField(..., auto_now_add=True)` — chỉ set một lần khi tạo row `ItemImage` (1-1 với `Item`, tái sử dụng qua các lần thay ảnh theo đúng thiết kế ở 03-dev-notes.md). `backend/apps/catalog/images/serializers.py:38` lấy `image.created_at.isoformat()` làm `uploaded_at`, trong khi `updated_at` (dòng 44, `auto_now=True`) mới là field cập nhật đúng mỗi lần thay — nhưng không được dùng.

**Ảnh hưởng:** Hiện chưa hiện trên UI nào (grep không thấy `uploaded_at` được render ở console/`ItemThumb`/`ImageUploadSheet`), nên chưa gây hiểu lầm trực tiếp cho người dùng ở lô 1. Nhưng là dữ liệu sai trả ra API (không khớp AuditLog cùng sự kiện — AuditLog ghi đúng thời điểm thay, còn field này thì không), có thể gây lệch khi S38 hoặc màn Nhật ký sau này hiển thị "tải lúc" dựa vào field này.

**Đề xuất sửa:** đổi serializer dùng `image.updated_at.isoformat()` thay vì `created_at` cho `uploaded_at` (hoặc đổi tên field cho rõ nghĩa `created_at`/`current_version_at`).

### B3 — `uploaded_at` trả theo UTC (`+00:00`) thay vì giờ Việt Nam (`+07:00`) như ví dụ JSON trong contract · Low · A2 §Contract mục 1
**[ĐÃ SỬA — xác nhận ở Vòng 2, 2026-09-27]**
**Thực tế:** mọi response đều trả dạng `...T21:42:24.840250+00:00`, trong khi ví dụ JSON ở 02-stories.md và 03-dev-notes.md dùng `+07:00`. Nguyên nhân: `serializers.py:38` gọi `.isoformat()` trực tiếp trên datetime UTC lưu trong DB, không qua `django.utils.timezone.localtime()`. Không có AC nào assert offset cụ thể, và trường này chưa được hiển thị ở FE nên không chặn — ghi nhận để BE cân nhắc khi làm màn hiển thị ngày tải ảnh sau này (S38/S43).

## Việc chưa kiểm được (ghi rõ, không suy diễn xanh)
- A1-AC1..AC4, AC7 (bucket GCS thật, IAM, budget billing thật): đúng phạm vi giao (chưa tạo hạ tầng thật), chỉ soát code + `doc/ops/moi-truong.md`.
- A2-AC11 (503 storage lỗi), A2-AC12 (rớt mạng giữa chừng): không dựng lại bằng tay qua UI thật (bị B1 chặn phần console; A2-AC11 đã có unit test BE riêng trong 632 test, đã xem qua code test đó chạy xanh).
- A2-AC17 phần "bấm hai lần không gửi hai lần" qua UI thật: không xác minh được (B1).
- A3-AC3 (cảnh báo khi gỡ ảnh của mặt hàng đang có lô Đang bán): không dựng lại kịch bản do giới hạn thời gian dựng dữ liệu QA; đây là phần FE (console) vốn đã ngoài phạm vi lô 1 theo 03-dev-notes.md.
- A4-AC8 (combo có ảnh riêng): không có combo trong seed QA; dựa vào unit test BE `test_a4_ac8_...` đã xanh.
