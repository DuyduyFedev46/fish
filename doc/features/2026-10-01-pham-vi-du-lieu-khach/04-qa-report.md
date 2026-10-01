# QA — Phạm vi dữ liệu khách theo vai (SR-PII-01, SR-PII-02) · lần 1 · 2026-10-01

## Kết luận: APPROVED — mọi AC đạt bằng chạy thật (Django runserver + đăng nhập token thật; ERP build mock và build thật trên Playwright), 0 lỗi chặn, 6 ghi nhận mức Low.

Phạm vi: bản chưa commit trên nhánh `main` (BE `apps/delivery/pii_scope.py`, `apps/common/api.py`, `apps/sales/customers|orders`, `accounts/0012`, ERP `features/orders|deliveries`, `shared/lib/personalData.ts`, `shared/ui/PersonalText.tsx`).
Toàn bộ dữ liệu là dữ liệu giả (sentinel `QA Ten …`, `QA Dia Chi …`, SĐT `09xxxxxx77`). Không dùng dữ liệu thật.

## Tổng: 387 ca mới + 2.097 ca hồi quy · ✅ tất cả · ❌ 0 · ⏸ 0

Ca mới (do QA viết/chạy trong scratchpad, DB SQLite giả):
| Nhóm | Số ca | Kết quả |
|---|---|---|
| API: ma trận 6 danh tính + 2 người kiêm nhiệm × 3 endpoint (`courier.py` 108 ca) | 108 | ✅ 108/0 |
| API: chu, quan_ly, nv_kho, cskh, khách, kiêm nhiệm (`others.py`) | 46 | ✅ 46/0 |
| API: POST/PATCH trạng thái trên phiếu hết hạn, phiếu người khác, FAILED (`status.py`, `status2.py`) | 9 | ✅ (không rò PII, đúng mã 400/404/200) |
| Migration `accounts/0012`: migrate → rollback 0011 → migrate → chạy lại, DB SQLite sạch (`snap*.json`) | 5 | ✅ |
| Cờ `DELIVERY_PII_RECENT_DAYS` (3/7/30, giá trị rác), mốc 00:00 VN (`env3.py`, `cskh_check.py`) | 6 | ✅ |
| ERP build **mock** (cổng 3253) đăng nhập `cs2`, `kho1`, `loc`; 1280 px và 360 px; storage/URL/console (`mock_e2e.py`) | ~18 | ✅ |
| ERP build **thật** nối backend thật (cổng 8767), kho/giao/chủ; 1280 px và 360 px (`real_e2e.py`) | ~24 | ✅ |
| Đối chứng đỏ: chạy lại `courier.py` trên backend HEAD (trước thay đổi, `git archive`) | 53 ca đỏ / 55 xanh | ✅ bộ kiểm có nhạy (bắt được hành vi cũ), xanh trên code mới |

Hồi quy (chạy lại trong lượt này): backend `manage.py test` 1746 OK · ERP `npm test` (vitest) 236/236 · e2e `p8_lo7_fe_erp.py` 79/79 · `p8_lo8_fe_erp_tz.py` 71/71 · `makemigrations --check` "No changes detected" · `check_naming.py` OK (không phát sinh vi phạm mới) · `check-no-mock` XANH · `check-ai-chunks` XANH · `npm ci` + `npm run build` (mock và thật) xanh.
(Số ca FE "~" lấy theo số lệnh khẳng định trong script; các bản chạy đầu có 6 ca đỏ do lỗi script QA, không phải lỗi sản phẩm, đã sửa script và chạy lại xanh.)

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| SR-PII-01 AC1 (migration gỡ `sales.view_customer` khỏi `nv_kho`, Group khác không đổi) | ✅ | `snap-at0011.json` vs `snap-after0012.json`: chỉ `nv_kho` mất quyền; `chu/quan_ly/nv_giao/cskh` giữ nguyên |
| SR-PII-01 AC2 (nv_kho 403 trên list/detail/POST/PATCH/DELETE khách; body 403 không chứa PII) | ✅ | `others.py` "kho customers … 403"; chu/quan_ly vẫn 200 đủ 6 trường |
| SR-PII-01 AC3 (nv_kho vẫn thấy tên, SĐT đầy đủ, địa chỉ ở orders/notes; ERP Đơn hàng chạy) | ✅ | `others.py` kho orders/notes đủ cả phiếu quá 7 ngày (Q-2); ảnh `shots/real-kho-order-detail-done8.png`, `real-kho-deliveries.png`; `mock-kho1-orders.png` |
| SR-PII-01 AC4 (idempotent, rollback trả quyền) | ✅ | `snap-rollback.json` (quyền trở lại), `snap-again.json`/`snap-idem.json` (chạy lại không lỗi, không đổi) |
| SR-PII-02 AC1 (`DELIVERY_PII_RECENT_DAYS`, mặc định 7, đọc env) | ✅ | `env3.py` (3/7/30) + mặc định 7 khi không đặt |
| SR-PII-02 AC2 (kết thúc > 7 ngày: tên/SĐT/địa chỉ/ghi chú không trả; mã đơn, mã phiếu, trạng thái, kg vẫn trả) | ✅ | `courier.py`: orders list/detail, notes list/detail → giá trị `null`, khoá JSON giữ, không sentinel trong body thô; ảnh `real-*-order-detail-hidden.png` hiển thị "Đã ẩn (quá 7 ngày)" |
| SR-PII-02 AC3 (đang giao hoặc ≤ 7 ngày: như cũ) | ✅ | `courier.py`: phiếu 6 ngày, đang giao, FAILED cũ, chưa gán: đủ dữ liệu |
| SR-PII-02 AC4 (nv_giao: `customers` chỉ id, phone, name, created_at; không `note`, `default_address`) | ✅ | `courier.py`/`others.py`: đúng 4 khoá, chỉ khách của phiếu mình, khách hết hạn không xuất hiện |
| SR-PII-02 AC5 (phạm vi cũ: ngoài phạm vi 404) | ✅ | `courier.py`/`status2.py`: phiếu/đơn/khách của người khác 404, không rò |
| Chung: ma trận Group 3 endpoint, sentinel, đếm 200 > 0; contract khoá JSON các vai khác không đổi; tên mới tiếng Anh; giờ VN | ✅ | Từng ca đều khẳng định "200 và count > 0" trước khi quét sentinel; chu/quan_ly khoá JSON như cũ; `check_naming.py` OK |

## Ngoại lệ & biên
| Ca | Kết quả |
|---|---|
| Mốc ranh: 6 ngày (thấy) vs 8 ngày (ẩn); phiếu kết thúc 00:01 hôm (today−7) vs 23:59 hôm (today−8) theo nửa đêm VN | ✅ |
| Phiếu CANCELLED dùng `created_at` (không có `completed_at`) | ✅ |
| FAILED không bao giờ hết hạn (luôn thấy) | ✅ |
| Tìm kiếm `?q=` bằng SĐT/tên của đơn đã hết hạn không làm lộ đơn đó (không có dòng nào khớp) | ✅ |
| Đơn hết hạn: dòng vẫn có mã/trạng thái/tiền, PII `null`, khoá JSON còn | ✅ |
| Địa chỉ rỗng (`seed_extra.py`): FE hiển thị trống, không nhầm với "Đã ẩn" ở đơn còn hiệu lực | ✅ (ảnh `real-*-order-detail-empty-address.png`) |
| Phiếu hết hạn bị POST đổi trạng thái (lùi, sai chuyển tiếp): 400 theo BR cũ, body không lộ PII | ✅ |
| Hai Group cùng lúc (nv_kho+nv_giao: phạm vi đầy đủ của nv_kho; cskh+nv_giao: phạm vi hẹp của nv_giao) | ✅ (ghi nhận L2/L3) |
| Giá trị cờ rác / 0 / lớn | ✅ (`env3.py`) |
| Chạy migration hai lần (job chạy 2 lần) | ✅ |
| Màn cũ: mở chi tiết đơn đã hiển thị rồi hết hạn (mock `cs2` mốc cũ) hiển thị "Đã ẩn" thay vì dữ liệu | ✅ |
| Người dùng chưa đăng nhập | ✅ 401 ở cả 3 endpoint |

## Phân quyền (200 > 0 đã kiểm trước khi kết luận "không thấy")
| Group | Customers list/detail | Orders list/detail/`?q=` | Notes list/detail | POST trạng thái |
|---|---|---|---|---|
| chu | 200 đủ 6 trường | 200 đủ PII, kể cả cũ | 200 đủ | 200 |
| quan_ly | 200 đủ 6 trường | 200 đủ | 200 đủ | 200 |
| nv_kho | **403** (list, detail, POST, PATCH, DELETE) | 200 đủ tên + SĐT đầy đủ + địa chỉ, kể cả đơn cũ (Q-2) | 200 đủ | 200 như cũ |
| nv_giao | 200, chỉ 4 trường, chỉ khách của phiếu mình còn hiệu lực | 200, chỉ đơn của phiếu mình; hết hạn thì PII `null` | 200, chỉ phiếu của mình; hết hạn thì PII `null`; phiếu người khác 404 | 200 cho phiếu của mình |
| cskh | như cũ (theo `sees_customer_directory` = chỉ chu/quan_ly nên không thấy) | phạm vi BR-GH-18 (đơn có cuộc gọi của mình) | như cũ | không có |
| khách (không Group) | 403 | 403 | 403 | 403 |
| nv_kho + nv_giao | 403 | phạm vi đầy đủ của nv_kho | đầy đủ | 200 |
| cskh + nv_giao | không thấy danh bạ đầy đủ | phạm vi của cskh/giao, ẩn quá hạn | ẩn quá hạn | 200 (phiếu của mình) |
| Chưa đăng nhập | 401 | 401 | 401 | 401 |

## Rò giá vốn
Không có. Quét JSON thô các endpoint khách/đơn/phiếu của mọi Group thiếu quyền: không có khoá `unit_cost`, `cost`, `avg_cost`, `margin`, `cost_price` hay tương đương. Thay đổi lần này không thêm khoá mới vào API hay `AuditLog` (chỉ đổi giá trị thành `null` và thêm annotate nội bộ `pii_visible`, không xuất ra JSON), nên không có đường tính ngược tiền ÷ kg.

## Rò dữ liệu cá nhân
- Danh bạ khách: nv_kho 403; nv_giao chỉ 4 trường của khách trong phạm vi và còn hiệu lực; khách/cskh/chưa đăng nhập không thấy. Body 403 không chứa sentinel. ✅
- Phiếu/đơn hết hạn của nv_giao: toàn bộ tên, SĐT, địa chỉ, ghi chú là `null`; quét sentinel trên body thô (không chỉ trường đã biết) sạch ở list, detail, POST/PATCH trả về, `?q=`. ✅ Đối chứng: trên HEAD cũ cùng bộ kiểm cho 53 ca đỏ (có rò), nên bộ kiểm phát hiện được.
- FE: trong build mock và build thật, màn Đơn hàng và Giao hàng của người bị giới hạn hiển thị "Đã ẩn (quá 7 ngày)", không có link `tel:` của khách ở chỗ bị ẩn (kiểm DOM), 360 px không tràn ngang. ✅
- `localStorage`, URL, console của trình duyệt: không có tên/SĐT/địa chỉ khách (build thật hoàn toàn sạch). Build mock có `sessionStorage` `cave_erp_mock_orders` chứa đơn giả, chỉ ở chế độ mock (xem L5). ✅
- Log: runserver access log chỉ chứa đường dẫn. Điểm cũ: `?q=<SĐT>` xuất hiện trong dòng access log của runserver (xem L6, có từ trước, không do thay đổi này).
- Ảnh chụp: `scratchpad/qa-pii-scope/shots/`, chỉ dữ liệu giả. Report này không có dữ liệu thật.
- Giới hạn tần suất tra đơn: không đổi trong lô này, không phát sinh.

## Hồi quy
Backend 1746 test OK (khoảng 130 giây, không `--parallel`); `makemigrations --check` không có thay đổi; ERP vitest 236/236; e2e `p8_lo7_fe_erp` 79/79 và `p8_lo8_fe_erp_tz` 71/71 (trong đó phần TZ Asia/Ho_Chi_Minh); `check_naming` không phát sinh vi phạm mới; `check-no-mock` và `check-ai-chunks` XANH; `out/_next` không có `127.0.0.1:87xx`. Chức năng liền kề (CSKH, soạn hàng, giao hàng, khách hàng của chu/quan_ly) vẫn chạy.

## Lỗi
Không có lỗi chặn (0 Critical, 0 High, 0 Medium).

Ghi nhận mức Low (không chặn, để PO/techlead cân nhắc):
- **L1** `PATCH /api/delivery/notes/<id>/` với `note` vẫn ghi được trên phiếu đã bị ẩn PII của nv_giao (phản hồi không lộ dữ liệu). Có từ trước, nằm ngoài AC.
- **L2** Người kiêm nhiệm cskh+nv_giao: endpoint `orders` và `notes` áp phạm vi hơi khác nhau (cách chọn bảo thủ hơn, không rò). Nên chốt một quy tắc ở lô kế.
- **L3** Người kiêm nhiệm nv_kho+nv_giao mất danh bạ khách đầy đủ (đúng thiết kế theo Q-1), nhưng nên ghi vào tài liệu vai.
- **L4** Màn ERP Giao hàng chỉ liệt kê "Hoàn tất (hôm nay)", nên trạng thái "Đã ẩn" thực tế chủ yếu thấy ở Đơn hàng. NV giao thuần (không nv_kho/cskh) không vào được `/orders` và `/deliveries` trong ERP (đường vào của họ là app giao hàng).
- **L5** Chế độ mock lưu đơn giả vào `sessionStorage` (`cave_erp_mock_orders`); chỉ build mock, build thật sạch.
- **L6** Dòng access log của runserver có `?q=<SĐT>` (từ trước). Chuỗi "7 ngày" cứng trong FE (`MSG.personalDataHidden`) lệch nếu đổi `DELIVERY_PII_RECENT_DAYS`. `recipient_name` `null` nhập nhằng giữa "ẩn" và "không có". `03-dev-notes.md` mục 7 (D2) còn lỗi thời và còn cập nhật spec BA chờ (D3 BR-PQ-15). Icon hiện là chữ trong ảnh headless do thiếu font offline (chỉ ảnh, không phải lỗi sản phẩm).

## Lệnh đã chạy (tóm tắt)
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` → Ran 1746 tests, OK.
- `manage.py makemigrations --check --dry-run` → No changes detected.
- `DATABASE_URL=sqlite:///…/qa-pii-scope/clean.sqlite3 manage.py migrate accounts 0011 / 0012 / 0011 / 0012` + snapshot quyền Group → đạt (AC1, AC4).
- Seed `seed.py` (17 ca) trên DB SQLite mới, `runserver 8765`, đăng nhập `POST /api/auth/token/`: `courier.py` 108/0, `others.py` 46/0, `status.py`/`status2.py` đạt.
- `courier.py` trên backend HEAD (`git archive HEAD backend`, cổng 8769): 55 xanh / 53 đỏ (đối chứng).
- ERP: `npm ci`, `npx tsc --noEmit`, `npm run build` (mock, cổng 3253, người dùng `cs2`/`kho1`/`loc`; thật, nối backend 8767), `npm test` 236/236, `mock_e2e.py`, `real_e2e.py`, `p8_lo7_fe_erp.py` 79/79, `p8_lo8_fe_erp_tz.py` 71/71.
- `python3 scripts/check_naming.py` → OK, `node scripts/check-no-mock.mjs` → XANH, `node scripts/check-ai-chunks.mjs` → XANH.
- Cuối lượt: build lại ERP bản thật `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=<API Cloud Run> npm run build` → xanh, không còn tham chiếu `127.0.0.1:87xx`; đã tắt mọi server QA (8765–8769, 3217, 3219, 3253, 3254) và máy chủ tĩnh cũ 3110 còn sót từ phiên trước.

Tệp tạm và ảnh: `/private/tmp/claude-501/-Users-dangthiduyen-Downloads-loc/3e0d9f3d-14ce-4b8b-a1cd-6fbcdc0b2f2d/scratchpad/qa-pii-scope/` (không nằm trong repo).
