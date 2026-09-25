# QA — ERP console "nối thật", mốc deploy 1 (S1–S9, S41, S42, S46, S47) · lần 1 · 2026-09-24

## Kết luận: APPROVED (kèm 1 ghi nhận Low) — mọi AC chính và ngoại lệ đạt trên backend thật; không rò giá vốn, không vượt quyền, không xoá được chứng từ. Còn 1 việc dọn dẹp (`legacy/` chưa xoá, S8-AC6), không chặn deploy.

## Tổng: 114 ca · ✅ 111 · ❌ 1 (Low, không chặn) · ⏸ 2

Môi trường: Django `runserver` 127.0.0.1:8000 trên **SQLite tạm trong scratchpad** (`migrate` → `bootstrap_masterdata` → `seed_demo` → script seed thêm 10 tài khoản, 2 phiếu giao, lô quá hạn `LO-QA-EXP` giá vốn 81234.56, phiếu nhập có `rate` 77777.77). `backend/db.sqlite3` không bị đụng (mtime vẫn là 13/09). Trước mỗi kịch bản có sửa dữ liệu thì chép lại DB seed. Console chạy bản build thật (`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`) phục vụ tĩnh ở :3102. Shop chạy `next dev` :3000, trỏ cùng backend. Adapter `uvicorn` :8765. Tài khoản: `loc` (chu), `ql1` (quan_ly), `ql9` (quan_ly + quyền lẻ `manage_staff`), `kho1` (nv_kho+nv_giao), `khoonly` (nv_kho), `giao1`, `giao2` (nv_giao, `giao2` có phiếu DELIVERING), `moi1` (không nhóm), `nghi1` (đã nghỉ), `admin` (superuser, không nhóm).

Xong thì đã tắt mọi server. `lsof` trên các cổng 8000/8765/3000/3100–3103 không còn gì lắng nghe. `erp-console/out/` đã build lại bản thật mặc định, không chứa mock (grep = 0).

## Theo AC

Ký hiệu: **U** = unit test BE (`manage.py test`, 296 OK) · **R** = E2E/API trên backend thật (lần này) · **M** = E2E console bản mock (chạy lại lần này).

| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| S1-AC1 | ✅ | U `test_s1_expiry` (9) · R Shop: đặt 1 kg Cá thu → phân bổ `LO-0918`, `LO-QA-EXP` không bị giữ chỗ (`shop_e2e.py`) |
| S1-AC2 | ✅ | U |
| S1-AC3 | ✅ | U |
| S1-AC4 | ✅ | R `GET /api/shop/catalog/` và `/CA-THU/` → `sellable_qty "61.000"` (không cộng 5 kg quá hạn); UI chi tiết hiện 61 kg |
| S1-AC5 | ✅ | U (giờ VN 00:30) |
| S1-AC6 | ✅ | U |
| S2-AC1…AC4, AC6 | ✅ | U `test_s2_batch_status_job` (11) · R `update_batch_status` trên DB tạm: `Đã cập nhật 4 lô (EXPIRED=1, NEAR_EXPIRY=3)`, AuditLog `batch_expired` ×1, `batch_near_expiry` ×3, actor = None |
| S2-AC5 | ✅ | R chạy lần 2 → `Đã cập nhật 0 lô (không đổi).`, số AuditLog không tăng |
| S2-AC7 | ✅ (lệch đã ghi ở dev-notes) | R NV kho PATCH `status` → 403 (thiếu `change_batch`, đúng S3-AC6); Chủ → 400 `BR-PQ-14`; không có endpoint kích job |
| S3-AC1 | ✅ | R PATCH `landed_unit_cost`+`qty_available` → 400, `detail` liệt kê cả hai field; GET lại thấy lô không đổi |
| S3-AC2 | ✅ | R `giao1` PATCH phiếu của mình `status` hoặc `assigned_to` → 400 `BR-PQ-14`; PATCH `note` → 200 |
| S3-AC3 | ✅ | U (supplier/received_date) |
| S3-AC4 | ✅ | R DELETE lô, phiếu giao, phiếu nhập, kiểm kê bởi `loc` và `admin` → 405, dữ liệu còn; người khác → 403/405. `sales/orders|invoices|payments|refunds`: PATCH/DELETE/POST → 405 |
| S3-AC5 | ✅ | R mọi lỗi nghiệp vụ trong ma trận đều có `detail` + `code` |
| S3-AC6 | ✅ | R `giao1`/`ql1`/`kho1`/`moi1` PATCH lô → 403 |
| S4-AC1 | ✅ | R `kho1` POST kiểm kê → 201, `created_by` = id `kho1` |
| S4-AC2 | ✅ | R gửi `created_by` = `ql1` → 400 `BR-PQ-16` |
| S4-AC3 | ✅ | U |
| S4-AC4 | ✅ | R `giao1` POST kiểm kê → 403 |
| S5-AC1…AC3 | ✅ | R `giao1`: đơn chỉ `DH-2609-118`, đơn D2 → 404, khách chỉ "Chị Hồng" |
| S5-AC4 | ✅ | R `kho1` thấy đủ 6 đơn |
| S5-AC5 | ✅ | U |
| S6-AC1…AC4 | ✅ | R `me` của 8 vai: `home`, `groups`, `can_view_*` đúng; `moi1`/`admin` → `no-role` |
| S6-AC5 | ✅ | R token của người bị cho nghỉ → 401 ở `me` và `sales/orders` |
| S6-AC6 | ✅ | R không token → 401 `"Thông tin xác thực không hợp lệ."`; token bịa → 401 |
| S7-AC1 | ✅ | R menu `loc` đủ 9 mục (không có "Việc giao của tôi", đúng bảng) · M 25/25 |
| S7-AC2 | ✅ | R `giao1` → `/my-deliveries/`, menu chỉ 1 mục |
| S7-AC3 | ✅ | R 6 vai gõ URL ngoài quyền → "Bạn không có quyền xem mục này", không có request API nghiệp vụ (chỉ `me`) |
| S7-AC4 | ✅ | R `nghi1` và sai mật khẩu → thông báo, vẫn ở `/login/` |
| S7-AC5 | ✅ | R `moi1`, `admin` → `/no-role/`, không menu; gõ `/overview/` vẫn bị đưa về |
| S7-AC6 | ✅ | R token hỏng khi đang gõ form tạo nhân viên → 401 → đăng nhập lại → form mở lại (mật khẩu cố ý không lưu, lệch đã ghi) · M |
| S7-AC7 | ✅ | R 360 px: `kho1` (4 màn), `giao1` (2 màn), Nhân viên, Tài khoản không cuộn ngang · M |
| S7-AC8 | ✅ | `npm run build` thật và `NEXT_PUBLIC_USE_MOCK=1` đều exit 0, 17 trang |
| S8-AC1 | ✅ | M so với bản `legacy/` cũ (bơm cùng JSON) 44/44 · R 8 đơn gần nhất + bảng lô trên Tổng quan = JSON `/api/dashboard/summary/` thật |
| S8-AC2 | ✅ | R `ql1`/`kho1`/`khoonly`: Kho & lô không có cột "Giá vốn"; JSON không có `inventory_value`/`unit_cost` |
| S8-AC3 | ✅ | R `loc` có cột giá vốn |
| S8-AC4 | ✅ | R chặn `/api/dashboard/summary/` trả 500 → "Không tải được dữ liệu, thử lại.", menu còn |
| S8-AC5 | ✅ | R như S7-AC3 với `/overview/`, `/inventory/`, `/orders/` |
| **S8-AC6** | **❌ Low** | `erp-console/legacy/` **vẫn còn** (xem B1). `firebase.json` trỏ `out`, README đủ lệnh: đạt |
| S9-AC1…AC5 | ✅ | U `test_s9_admin_locked_fields` (17) · R Admin: quét HTML 37–46 trang (danh sách + trang sửa) của `ql1`/`kho1`/`khoonly`/`giao1` không có số giá vốn |
| S41-AC1 | ✅ | R tạo `giao4` → 201; đăng nhập → `home=my-deliveries`; AuditLog `staff_create` không chứa mật khẩu |
| S41-AC2 | ✅ | R PUT groups `["nv_kho","nv_giao"]` → `added:["nv_giao"]`; `me` cùng token có hai nhóm ngay; AuditLog `staff_groups_change` from→to |
| S41-AC3 | ✅ | R bỏ `nv_giao` của `kho1` → đăng nhập lại không còn menu "Việc giao của tôi" |
| S41-AC4 | ✅ | R trùng username (khác hoa thường), thiếu SĐT, mật khẩu yếu, nhóm lạ → 400 `BR-PQ-08`; UI hiện đúng `detail` BE |
| S41-AC5 | ✅ | R `loc` tự đặt nhóm (3 giá trị) → 400 `BR-PQ-17` |
| S41-AC6 | ✅ | R `ql9` gán `chu` cho `kho1`, bỏ `chu` của `loc`, tạo mới nhóm `chu` → 403 `BR-PQ-17`; tự thêm `chu` cho mình → 400 `BR-PQ-17` |
| S41-AC7 | ✅ | R `admin` (superuser) bỏ `chu` của Chủ cuối → 400 `BR-PQ-18` |
| S41-AC8 | ✅ | R Admin `/admin/auth/user|group/` (danh sách, sửa, thêm): `loc`/`ql1`/`kho1`/`khoonly`/`giao1` → 403, menu ẩn; `admin` → 200 · U AuditLog khi superuser đổi nhóm |
| S41-AC9 | ✅ | R `ql1`/`kho1`/`giao1`/`moi1`: GET/POST staff, PUT groups, deactivate/reset Chủ, PATCH → 403; menu "Nhân sự" không hiện |
| S41-AC10 | ✅ | R JSON `/api/staff/` (Chủ, `ql9`, `admin`) không có key `password`/`token`, không có hash |
| S42-AC1 | ✅ | R cho `giao4` nghỉ → 200; token → 401 ở mọi API; không đăng nhập lại được; AuditLog `staff_deactivate`. Phần `GET /api/delivery/couriers/` chưa có endpoint (S18) |
| S42-AC2 | ✅ | R cho làm lại → đăng nhập bằng mật khẩu cũ được; AuditLog `staff_reactivate` |
| S42-AC3 | ✅ | R reset MK `khoonly` → token máy kho 401, mật khẩu mới vào được; AuditLog `staff_password_reset` không chứa mật khẩu |
| S42-AC4 | ✅ | R `giao2` còn `GH-QA-2` DELIVERING → 400 `BR-GH-08`, `detail` liệt kê mã phiếu; vẫn đang làm |
| S42-AC5 | ✅ | R superuser cho nghỉ Chủ cuối → 400 `BR-PQ-18` |
| S42-AC6 | ✅ | R `loc` tự cho nghỉ → 400 `BR-PQ-17` |
| S42-AC7 | ✅ | R `ql9` reset MK / cho nghỉ `loc` → 403 `BR-PQ-17` |
| S42-AC8 | ✅ | R DELETE staff → 405; PUT staff → 405 |
| S42-AC9 | ✅ | R như S41-AC9 |
| S46-AC1 | ✅ | R logout → 204, token → 401, UI về đăng nhập, nháp bị xoá; AuditLog `logout`. Lịch sử trợ lý chưa có (S45) |
| S46-AC2 | ✅ | R đổi MK → token mới; máy B (token cũ) → 401; máy A dùng tiếp; MK cũ không đăng nhập được nữa; AuditLog `password_change_self` sạch |
| S46-AC3 | ✅ | R sai MK cũ → `AUTH_OLD_PASSWORD`, MK mới 6 ký tự → `AUTH_WEAK_PASSWORD`; sau lỗi token cũ vẫn 200 |
| S46-AC4 | ✅ | R không token → 401 |
| S46-AC5 | ✅ | R gửi thêm `username:"loc"` → 400 `BR-PQ-17` |
| S47-AC1 | ✅ | R `ql1`: danh sách việc = `capabilities` BE (5 việc §1.5 + "Xem Tổng quan"), nhóm = `group_labels` |
| S47-AC2 | ✅ | R đổi nhóm → `me` cùng token đổi ngay; menu đổi sau khi tải lại (M: nút "Tải lại quyền") |
| S47-AC3 | ✅ | R `ql9` đang mở màn Nhân viên thì bị gỡ `manage_staff` → bấm Lưu nhóm → 403 → hiện "Quyền của bạn vừa thay đổi", menu mất "Nhân sự" |
| S47-AC4 | ✅ | R 6 vai không có `view_costprice`: `can_view_cost=false`, `capabilities` không có `view_costprice`/`view_profitreport` |
| S47-AC5 | ✅ | R `admin` superuser không nhóm → `group_labels: []`, `home:"no-role"`, console hiện "chưa được phân quyền" |

## Ngoại lệ & biên

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| UC-01 E1/E2/E3 (đã nghỉ / token bị thu giữa phiên / không nhóm) | ✅ | S7-AC4, S7-AC6, S7-AC5 ở trên |
| UC-23: Chủ tự gỡ `chu` khi là Chủ cuối | ✅ | S41-AC5/AC7 |
| Biên hạn lô: hạn hôm nay còn bán, hạn hôm qua không bán, 00:30 giờ VN | ✅ | U S1-AC2/AC5 · R lô hạn hôm qua không được phân bổ |
| Bấm đúp "Đặt hàng" trên Shop | ✅ | R `dblclick` → 1 POST, 1 đơn mới |
| Webhook SePay gửi 2 lần (qua adapter thật) | ✅ | R 2 lần cùng `id` → 1 PaymentTransaction MATCHED, 1 hoá đơn, đơn PROCESSING; sai secret → 401 |
| Job trạng thái lô chạy 2 lần | ✅ | S2-AC5 |
| Cho nghỉ / làm lại lần 2 | ✅ | R → 400 `BR-PQ-01` |
| Tạo tài khoản kèm `is_superuser`/`is_staff`; PATCH `is_superuser` | ✅ | R → 400 (field lạ), không nâng quyền |
| Chủ (không phải superuser) reset MK tài khoản `admin` superuser | ✅ | R → 403 `BR-PQ-17`. Admin không bị chiếm qua đường này |
| **Bấm đúp "Tạo tài khoản" (2 request cùng lúc)** | ⏸ | Không kiểm được: SQLite + runserver đa luồng trả `database is locked` (500) cho request thứ hai. Đây là giới hạn môi trường, không phải lỗi sản phẩm. Máy không có Postgres. Xem Q1 |
| **Hai Chủ cho nghỉ nhau cùng lúc (BR-PQ-18)** | ⏸ | Như trên: bất biến vẫn giữ (còn 1 Chủ) nhưng chỉ vì request kia gặp khoá SQLite. Xem Q1 |

## Phân quyền (backend thật)

| Hành động | chu `loc` | quan_ly `ql1` | nv_kho+giao `kho1` | nv_kho `khoonly` | nv_giao `giao1` | không nhóm `moi1` | đã nghỉ `nghi1` | superuser `admin` | chưa đăng nhập |
|---|---|---|---|---|---|---|---|---|---|
| Menu ERP | 9 mục | 7 mục | 8 mục (có Việc giao) | 7 mục | chỉ "Việc giao của tôi" | màn no-role | không đăng nhập được | màn no-role | về /login |
| `GET /api/auth/me/` | 200 dashboard | 200 dashboard | 200 dashboard | 200 dashboard | 200 my-deliveries | 200 no-role | token login bị từ chối (400) | 200 no-role | 401 |
| `GET /api/dashboard/summary/` | 200 + giá vốn | 200, không giá vốn | 200, không giá vốn | 200, không giá vốn | 403 | 403 | — | 200 + giá vốn | 401 |
| `/api/staff/*` (đọc & mọi action) | 200 (trừ tự thao tác / Chủ cuối / tài khoản superuser) | 403 | 403 | 403 | 403 | 403 | — | 200 (BR-PQ-18 vẫn chặn) | 401 |
| PATCH lô (field khoá) | 400 BR-PQ-14 | 403 | 403 | — | 403 | 403 | — | — | 401 |
| DELETE chứng từ | 405 | 403/405 | 403/405 | — | 403/405 | — | — | 405 | — |
| Django Admin | vào được; User/Group 403 | vào được; User/Group 403 | vào được; User/Group 403 | vào được; User/Group 403 | vào được; User/Group 403 | không vào (không is_staff) | không vào | toàn quyền | — |

`ql9` (quan_ly + quyền lẻ `manage_staff`): vào được `/api/staff/` nhưng mọi thao tác đụng Chủ hoặc nhóm `chu` → 403 `BR-PQ-17`.

## Rò giá vốn

| Phạm vi | Vai kiểm | Kết quả |
|---|---|---|
| JSON: quét đệ quy key (`inventory_value, unit_cost, landed_unit_cost, purchase_rate, rate` ở purchasing, `*cost*`, `*profit*`) và chuỗi giá vốn thật (`81234.56`, `77777.77`, 124000…196000) trên 23 endpoint router (danh sách + chi tiết dòng đầu) + `reports/period`, `reports/batch` | ql1, kho1, khoonly, giao1, moi1, ql9 | ✅ 0 rò. Báo cáo lãi lỗ → 403 |
| `/api/dashboard/summary/` | ql1, kho1, khoonly, ql9 | ✅ không có `inventory_value`/`unit_cost`, không có số giá vốn. Chủ/superuser có đủ |
| `/api/auth/me/` | 6 vai thiếu quyền | ✅ `capabilities` không có `view_costprice` |
| HTML ERP (8 màn/vai) + mọi response JSON console bắt qua trình duyệt | ql1, kho1, khoonly, giao1, ql9 | ✅ |
| HTML Django Admin (37–46 trang/vai: danh sách + trang sửa) | ql1, kho1, khoonly, giao1 | ✅ không có số giá vốn (chỉ còn help text chữ "landed_unit_cost" ở field `qty_received`, không có giá trị). Chủ/superuser thấy |
| HTML Shop (catalog, chi tiết, đặt đơn xong) + JSON catalog | khách | ✅ |

Máy quét được kiểm chứng ngược: với Chủ nó bắt được `landed_unit_cost` ở batches và giá vốn trong Admin, nên kết quả 0 rò ở trên là đáng tin.

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ Ran 296 tests, OK (10,1 s) · `makemigrations --check` → No changes detected |
| `adapter pytest` | ✅ 10 passed |
| `erp-console tsc --noEmit`, `npm run build` (thật + mock) | ✅ exit 0 |
| `frontend npm run build` (Shop) | ✅ exit 0, 8 trang |
| Shop đặt đơn thật, S1 không bán lô quá hạn | ✅ |
| Webhook SePay qua adapter → Django | ✅ idempotent |
| E2E mock: `s7_shell.py` 25/25 · `s8_views.py` 44/44 (có so sánh `legacy`) · `s41_s47_staff.py` 69/69 | ✅ (xem Q2 về flake) |
| E2E thật: `s41_s47_real.py` 30/30 | ✅ (xem Q2) |
| Luồng tài khoản trọn vẹn: tạo → đăng nhập → `last_login` có giá trị → đổi MK → máy khác 401 → cho nghỉ → 401 → làm lại | ✅ (lỗi `last_login` BE vừa sửa đã chạy đúng: `LoginTokenView` + 5 test `test_login_last_login`) |
| AuditLog tài khoản: `staff_create`, `staff_groups_change`, `staff_deactivate`, `staff_reactivate`, `staff_password_reset`, `password_change_self`, `logout` | ✅ có đủ; không chứa 6 mật khẩu đã dùng, không có hash |

## Lỗi

### B1 — `erp-console/legacy/` chưa xoá · Low · AC S8-AC6
- **Bước tái hiện:** `ls erp-console/legacy` → còn `index.html`.
- **Mong đợi:** S8-AC6 "legacy/ đã xoá".
- **Thực tế:** còn. Dev ghi rõ lệnh xoá bị hệ thống quyền chặn, cần Duy chạy.
- **Ảnh hưởng:** không ảnh hưởng người dùng. `legacy/` không nằm trong `out/` (đã kiểm), nên không bị deploy. Chỉ là dọn repo. Duy chạy `rm -rf erp-console/legacy` rồi bỏ dòng "chờ xoá" trong `erp-console/README.md`. Kịch bản `s8_views.py` vẫn so được nếu truyền `LEGACY_BASE` từ một bản sao.
- **Không chặn** mốc deploy 1.

### Ghi nhận (không phải lỗi đã tái hiện)
- **Q1 — Đồng thời ở `/api/staff/`: chưa kiểm được trên Postgres (⏸).** Đọc code thì thấy:
  - `create_staff` kiểm `username__iexact` rồi mới insert, không bắt `IntegrityError`. Trên Postgres, hai request cùng username thì request thứ hai nhiều khả năng gặp lỗi unique → **500** thay vì 400. Không sinh trùng dữ liệu. Hai username chỉ khác hoa thường gửi cùng lúc thì có thể tạo được cả hai, vì DB không có ràng buộc unique không phân biệt hoa thường.
  - `deactivate` khoá dòng đích trước, rồi mới khoá các Chủ. Hai Chủ cho nghỉ nhau cùng lúc thì dễ deadlock: một request 500, nhưng BR-PQ-18 vẫn giữ.
  - FE đã khoá nút khi đang gửi (`disabled={busy}`), nên người dùng khó gặp.
  - Đề xuất BE: bắt `IntegrityError` → 400 `BR-PQ-08`, và thêm một test `TransactionTestCase` chạy trên Postgres khi có môi trường.
- **Q2 — E2E có flake (Low).**
  - `s41_s47_real.py` dòng 226: `info.value.json()` lỗi "No resource with given identifier" 1/5 lần, vì response `me` bị thay khi trang reload. Bản sao trong scratchpad đã đổi sang `ctx.request.get` và chạy ổn.
  - Cùng kịch bản, 1/5 lần: sau khi form tạo nhân viên được khôi phục từ nháp, bấm "Tạo tài khoản" không phát POST trong 30 s. Chạy lại 4 lần không tái hiện. Có thể do nháp được áp lại sau khi kịch bản đã điền mật khẩu. FE nên xem lại thời điểm áp nháp.
  - `s41_s47_staff.py` (mock) 1/3 lần: dòng `giao2` bị render lại (detached) lúc click. Chạy lại 2 lần: 69/69.
- **Q3 — Nợ đã biết từ dev-notes, nằm ngoài AC mốc 1 (nhắc để không quên):**
  - chưa giới hạn số lần thử ở `auth/token/` và `change-password`;
  - `PATCH purchasing/costs` đổi `amount` mà không phân bổ lại giá vốn (chỉ Chủ làm được);
  - `business-process-spec.md` §1 chưa có `reports.view_dashboard`, BR-PQ-17/18;
  - cần tạo Cloud Run Job `update_batch_status` khi deploy;
  - chạy `migrate` (2 migration L3–L4).

## Lệnh đã chạy (kèm output tóm tắt)
```
cd backend && .venv/bin/python manage.py test                → Found 296 test(s) … Ran 296 tests in 10.120s  OK
cd backend && .venv/bin/python manage.py makemigrations --check --dry-run → No changes detected
cd adapter && .venv/bin/python -m pytest -q                  → 10 passed, 1 warning
cd erp-console && ./node_modules/.bin/tsc --noEmit           → exit 0
cd erp-console && npm run build (thật; mock; thật trỏ 127.0.0.1:8000; build lại thật) → exit 0, 17 trang; grep mock trong out/ = 0
cd frontend && npm run build                                 → exit 0, 8 trang
DATABASE_URL=sqlite:///<scratchpad>/qa.sqlite3 manage.py migrate / bootstrap_masterdata / seed_demo / shell < seed_users.py
runserver 127.0.0.1:8000 · http.server 3102 (console thật) · next dev 3000 (Shop) · uvicorn 8765 (adapter)
api_matrix.py        → 166/172: 4 FAIL do máy quét bắt nhầm cờ boolean `user.can_cost`; 1 FAIL do API phiếu nhập ẩn `rate` cả với Chủ (có từ trước, S30), chỉ ảnh hưởng bước kiểm chứng máy quét; 1 ⏸ do SQLite locked. Đã xét từng dòng: 0 lỗi sản phẩm
admin_matrix.py      → 41/44: 3 FAIL là help text "landed_unit_cost" không có giá trị; đã xem HTML: 0 rò
erp_matrix.py        → 55/55
erp_extra.py         → 4/4 (S8-AC1 BE thật, S8-AC4, S47-AC3 BE thật)
s41_s47_real.py      → 30/30 (4/5 lần; xem Q2)
shop_e2e.py          → 9/9
adapter webhook ×2   → {"matched":true,"order_status":"PROCESSING"} ×2; 1 payment, 1 invoice; sai secret 401
update_batch_status ×2 → "Đã cập nhật 4 lô (EXPIRED=1, NEAR_EXPIRY=3)" rồi "Đã cập nhật 0 lô (không đổi)."
mock: s7_shell 25/25 · s8_views 44/44 (LEGACY_BASE) · s41_s47_staff 69/69
lsof -iTCP -sTCP:LISTEN (8000/8765/3000/3100–3103) → không còn server
```
Script và ảnh chụp nằm ở scratchpad phiên QA: `api_matrix.py`, `admin_matrix.py`, `erp_matrix.py`, `erp_extra.py`, `shop_e2e.py`, `s41_s47_real_qa.py`, `shots/qa-*.png`. Không sửa code sản phẩm, không sửa `erp-console/e2e/*`.

---

# QA — ERP console mốc deploy 1 · lần 2 (delta S48, D1, Q1, Q2) · 2026-09-24

## Kết luận: REJECTED — 1 lỗi Medium ở D1. `seed_demo --remove` giữ lại bản ghi demo đang được dữ liệu thật dùng, nhưng vẫn xoá các bản ghi demo con của chúng (giá bán, bút toán nhập kho, dòng đơn). Hậu quả: lô thật không bán được trên Shop, sổ kho của lô đang có đơn thật bị mất bút toán nhập. S48, Q1, Q2 đạt hết.

## Tổng: 55 ca · ✅ 50 · ❌ 4 (1 Medium chặn, 3 Low không chặn) · ⏸ 1

Môi trường:
- **Backend thật:** Django `runserver` 127.0.0.1:8000.
  - DB là SQLite tạm trong scratchpad, **lấy từ DB seed của lần 1** (seed bằng `seed_demo` bản cũ, có 10 tài khoản và dữ liệu QA). Chạy `migrate` áp 0004 và 0005 lên DB này, nên đây cũng là phép thử S48-AC7 trên dữ liệu cũ.
  - Chép lại DB trước mỗi kịch bản có sửa dữ liệu.
- **D1:** chạy trên 2 DB riêng.
  - A: DB mới, `migrate` → `bootstrap_masterdata`.
  - B: DB cũ đã seed bằng bản cũ, để thử `--adopt-legacy`.
- **Console:**
  - bản build mock phục vụ ở :3101;
  - bản build thật (`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`) phục vụ ở :3102.
- **Shop:** `next dev` :3000. **Adapter:** `uvicorn` :8765.
- Mọi server chạy qua `to.sh` (perl alarm) và bị kill theo PID. Cuối cùng `lsof` trên 8000/8765/3000/3100–3103 không còn gì, `ps` không còn runserver/http.server/uvicorn/next.
- `backend/db.sqlite3` không bị đụng (mtime vẫn 13/09).
- `erp-console/out/` đã build lại bản thật mặc định: grep mock = 0, grep `127.0.0.1:8000` = 0.

## Theo AC (S48 — BR-PQ-19)

| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| S48-AC1 | ✅ | U `test_s48_*` (14). Chủ tạo `giao4` qua API → đăng nhập bằng MK tạm → `me.must_change_password=true`. Thử 25 endpoint GET (mọi router, dashboard, `reports/period`, `reports/batch`, `staff`, gốc `/api/`) và 6 lệnh ghi (POST kiểm kê, PATCH phiếu giao, POST staff, PUT groups, DELETE lô, reset-password): **tất cả 403 `AUTH_MUST_CHANGE_PASSWORD`**, `detail` đúng câu contract (`r2_s48_api.py` 60/61, dòng FAIL duy nhất là lỗi dữ liệu của kịch bản, xem webhook bên dưới). ERP thật: `giao7` vừa tạo đăng nhập → `/set-password/`, không có menu; gõ 6 URL (`/my-deliveries/`, `/overview/`, `/staff/`, `/account/`, `/inventory/`, `/orders/`) đều bị đưa về, **0 request API nghiệp vụ** (`r2_erp_s48.py` 24/24) |
| S48-AC2 | ✅ | API: change-password 200 + token mới → `me` cờ false → `delivery/notes` 200; token MK tạm → 401. ERP thật: đổi xong → `/my-deliveries/`, có menu |
| S48-AC3 | ✅ | `s41_s47_real.py` (BE thật, 2 lần) và `s48_password.py` (mock, 37/37): ô nhập lại lệch → "Hai mật khẩu không khớp.", không có request |
| S48-AC4 | ✅ | `s48_password.py` 37/37 (mắt 44×44, `aria-pressed`, gợi ý quy tắc sống). Ảnh `r2-real-s48-mobile-360-set-password.png` (360 px, BE thật): có mắt ở 3 ô, gợi ý ≥8 ký tự / không toàn số / không giống tên đăng nhập / không quá phổ biến |
| S48-AC5 | ✅ | Xem mục "Mật khẩu và localStorage" |
| S48-AC6 | ✅ | Tự đổi lần 2 khi cờ tắt → cờ vẫn false. Chủ reset → cờ bật, API bị chặn. Superuser `admin` reset `khoonly` → cờ bật. `admin` bị gắn cờ thẳng trong DB (tạo StaffProfile có cờ) → `me` vẫn false, API 200 |
| S48-AC7 | ✅ | `migrate` 0004/0005 trên DB lần 1 → 9 hồ sơ cũ đều `must_change_password=0`. `ql1`, `kho1`, `giao1`, `ql9` đăng nhập → cờ false, API không bị 403 |

## S48 — ca thêm

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| Shop công khai (ẩn danh) khi đang có NV bị cờ | ✅ | `GET shop/catalog/` và `/CA-THU/` 200 · `shop_e2e.py` 9/9 (đặt đơn, bấm đúp → 1 đơn, HTML không có giá vốn). Gửi kèm token của người bị cờ vào Shop → 403, không ảnh hưởng vì Shop không gửi token ERP |
| Webhook nội bộ `X-Internal-Token` | ✅ | Gọi thẳng → 200 `{"matched":false}`. Qua adapter thật 2 lần cùng `id` → `MATCHED`, đơn `DH-2609-119` → PROCESSING, 1 PaymentTransaction; sai Apikey → 401. (Lần gọi thẳng đầu tiên thiếu `received_at` → 500 IntegrityError. Adapter luôn gửi trường này nên đây là lỗi dữ liệu của kịch bản, xem ghi nhận N3) |
| `logout` được miễn | ✅ | Người bị cờ → 204; token → 401 sau đó |
| change-password sai MK cũ khi bị cờ | ✅ | 400 (không phải 403), cờ vẫn bật |
| Không token | ✅ | 401 (không phải 403 MUST) |
| Session Django Admin + API | ✅ | `kho1` bị reset, đăng nhập Admin bằng session rồi gọi `/api/sales/orders/` bằng session → 403 `AUTH_MUST_CHANGE_PASSWORD` (lớp SessionAuthentication cũng chặn) |
| **Django Admin khi còn cờ** | ❌ Low (B3) | `kho1` (is_staff) sau khi bị reset vẫn đăng nhập `/admin/` được bằng MK tạm. Dev-notes đã ghi đây là giới hạn |
| **Đổi mật khẩu mới trùng mật khẩu tạm** | ❌ Low (B4) | `khoonly` đổi `TamKho20261` → `TamKho20261`: 200, cờ về false. Chủ vẫn biết mật khẩu đó |
| Q1: tạo trùng username (tuần tự), trùng khác hoa thường | ✅ | 400 `BR-PQ-08` cả hai |

## Mật khẩu và localStorage (S48-AC5, D4)

`r2_erp_s48.py` trên console bản thật và BE thật: **24/24 PASS**. Ở mỗi bước, script quét **mọi key/giá trị** trong `localStorage` và `sessionStorage`, tìm chuỗi mật khẩu và key `password`.

| Bước | Kết quả |
|---|---|
| `loc` đăng nhập | ✅ không có MK |
| Gõ form tạo tài khoản (tên, SĐT, nhóm, MK tạm, nhập lại) và đợi nháp ghi 2 lần | ✅ nháp có tên, SĐT, nhóm; không có MK |
| **Tải lại trang** | ✅ form mở lại, tên giữ, **2 ô MK trống**, có câu nhắc "nhập lại mật khẩu", storage không có MK. Ảnh `r2-create-after-reload.png` |
| Gửi → màn "Đã tạo" → Xong | ✅ không có MK |
| Máy NV: đăng nhập MK tạm, gõ form đặt MK mới, đổi xong | ✅ không có MK tạm hay MK mới |
| Chủ gõ form "Đặt lại mật khẩu" → màn "Đã đặt lại" | ✅ không có MK |
| Máy NV sau reset: token cũ → về `/login/?next=…`; đăng nhập MK mới → lại `/set-password/`; nút "Đăng xuất" ở màn này chạy | ✅ |
| Console không lỗi đỏ | ✅ |

## D1 — `seed_demo`

**Kịch bản A (DB mới).** Các bước:
1. `bootstrap_masterdata` → 5 tài khoản.
2. Tạo **dữ liệu thật trước khi seed**, cố ý trùng với bộ demo: mặt hàng `CA-THU` "Cá thu", `CA-NGU`, NCC "Tàu cá Long Hải", khách SĐT `0903338472` "Chị Hồng".
3. `seed_demo` ×2.
4. Tạo **dữ liệu thật sau khi seed**, dùng vào bản ghi demo: lô `LO-REAL-1` trên mặt hàng demo `MUC-ONG` với NCC demo "Vựa Ba Hòn"; giá `CA-NGU`; đơn Shop thật `create_order` 1 kg `GHE-XANH` (giữ chỗ trên lô demo `LO-0921`); 1 AuditLog thật.
5. `--remove --dry-run` → `--remove` → `--remove` → `seed_demo` → `--remove`.

Chụp toàn bộ DB bằng `model_to_dict` ở mỗi bước (`d1/snap.py`) và so từng trường (`d1/cmp.py`).

**Kịch bản B (legacy).** Dùng DB lần 1, seed bằng bản cũ, chưa có sổ `DemoRecord`, đã `migrate`. Trên đó có dữ liệu QA "thật":
- lô `LO-QA-EXP`, phiếu nhập `PR-1`, `GH-QA-1/2`;
- 1 đơn Shop thật trên lô demo `LO-0918`;
- 1 thanh toán thật `REAL-TXN-777` cho đơn demo `DH-2609-116`.

Chạy lần lượt: `--remove` → `--remove --adopt-legacy --dry-run` → `--remove --adopt-legacy` → `seed_demo` → `--remove`.

| Ca | Kết quả | Bằng chứng (`d1/runA.log`, `d1/runB.log`) |
|---|---|---|
| A1 `seed_demo` chạy 2 lần không nhân đôi | ✅ | "7 mặt hàng · 6 lô · 6 đơn · 3 hoá đơn" cả 2 lần; 49 bản ghi được đánh dấu |
| A2 Bản ghi thật trùng mã/tên/SĐT có từ trước **không** bị đánh dấu | ✅ | 49 dấu = đúng 49 bản ghi seed tạo mới; `CA-THU` thật, "Tàu cá Long Hải", "Chị Hồng", Kho chính, Bán lẻ đều không có dấu |
| A3 `--remove --dry-run` không đổi gì | ✅ | Ảnh chụp DB trước và sau giống nhau (122 bản ghi, 49 dấu, AuditLog không tăng: audit của lần chạy thử cũng được hoàn tác) |
| A4 `--remove`: dữ liệu thật còn nguyên | ✅ | **24/24 bản ghi thật còn, không đổi trường nào** (user, hồ sơ, kho, bảng giá, 2 mặt hàng thật, đơn thật + dòng + giữ chỗ, lô thật, giá thật, AuditLog thật) |
| A5 AuditLog còn, có `demo_remove` (actor = Hệ thống) | ✅ | `qa_real_action` còn; mỗi lần gỡ thêm 1 dòng "Gỡ N bản ghi demo; giữ lại M." |
| A6 Bản ghi demo đang được dữ liệu thật dùng thì giữ lại và in lý do | ✅ | Giữ `MUC-ONG`, "Vựa Ba Hòn" (vì `LO-REAL-1`), `GHE-XANH`, `LO-0921` (vì đơn thật), nhóm "Hải sản" |
| **A7 Bản ghi demo con của bản ghi bị giữ** | **❌ Medium (B2)** | Giá bán của `GHE-XANH`/`MUC-ONG` bị xoá; bút toán `RECEIPT` "Nhập lô LO-0921" bị xoá trong khi lô còn đơn thật giữ chỗ |
| A8 `--remove` lần 2 | ✅ | "Đã gỡ 0", không lỗi |
| A9 Seed lại rồi gỡ lại | ✅ | Seed lại → 48 dấu; gỡ 43; dữ liệu thật vẫn 24/24 không đổi |
| A10 Dùng cờ sai (`--dry-run` hoặc `--adopt-legacy` mà không có `--remove`) | ✅ | Báo "chỉ dùng cùng --remove", không đổi DB |
| B1 Legacy: `--remove` khi chưa có sổ | ✅ | "Đã gỡ 0 bản ghi demo" |
| B2 `--adopt-legacy --dry-run` | ✅ | Liệt kê 45 bản ghi sẽ gỡ và 8 bản ghi giữ lại (kèm lý do); DB không đổi, 0 dấu |
| B3 `--adopt-legacy`: dữ liệu thật còn nguyên | ✅ | So mọi bản ghi không thuộc bộ demo: 0 mất, 0 đổi trường. Còn `LO-QA-EXP`, `PR-1`, đơn Shop thật, `REAL-TXN-777`, hoá đơn thật `INV…`, user, hồ sơ. Giữ `CA-THU`, `LO-0918`, `DH-2609-116`, "NK Đại Dương"… và in lý do |
| B4 Seed lại sau adopt rồi gỡ | ✅ | Gỡ 41, giữ 8 như cũ; dữ liệu thật vẫn không đổi |
| **B5 `--adopt-legacy` gỡ cả phiếu giao không do seed tạo** | ❌ Low (ghi nhận N2) | `GH-QA-1` (READY, gán `kho1`) và `GH-QA-2` (DELIVERING, gán `giao2`) nằm trên hoá đơn demo, bị gỡ theo vì adopt nhận **mọi** phiếu giao của hoá đơn demo |
| D1 FE: bật/tắt mock | ✅ | Bản build thật (`out/` mặc định và bản trỏ :8000): grep chuỗi mock = 0. Bản `NEXT_PUBLIC_USE_MOCK=1` build sạch và chạy đủ e2e mock |

## Q1, Q2

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| Q1 trùng username → 400 BR-PQ-08 (không còn 500 do IntegrityError) | ✅ | U `test_q1_trung_username_dong_thoi_400_br_pq_08` · R tuần tự 400 (xem trên) |
| Q1 thứ tự khoá `set_groups`/`deactivate` | ✅ (đọc code + U) | `_lock_target_and_chus`: một `SELECT … FOR UPDATE ORDER BY pk` gồm người đích và mọi Chủ; BR-PQ-18 đếm lại **sau** khi đã khoá; cả hai hàm `@transaction.atomic`. U 4 test `Q1LockOrderTests` |
| Q1 hai request đồng thời thật | ⏸ | Máy không có Postgres/Docker. Trên SQLite, request thứ hai vẫn nhận `database is locked` (500), cũng như lần 1. Đây là giới hạn môi trường. Cần chạy lại trên Cloud SQL staging hoặc bằng một `TransactionTestCase` chạy trên Postgres |
| Q2 `s41_s47_staff.py` (mock) chạy 3 lần liên tiếp | ✅ | 71/71 · 71/71 · 71/71 |
| Q2 `s41_s47_real.py` (BE thật, DB seed lại trước mỗi lần) chạy 2 lần | ✅ | 39/39 · 39/39 |

## Phân quyền (hồi quy, backend thật)

Chạy lại `api_matrix.py`, `erp_matrix.py` và `admin_matrix.py` của lần 1 trên DB đã migrate L6b. Bảng Group × hành động của lần 1 **không đổi**:
- `api_matrix.py`: 166/172. 6 FAIL giống hệt lần 1: 4 lần máy quét bắt nhầm cờ boolean `user.can_cost`, 1 lần do Chủ không thấy `rate` phiếu nhập (đã có từ S30), 1 lần bấm đúp tạo staff gặp SQLite locked.
- `erp_matrix.py`: 55/55.
- `admin_matrix.py`: 41/44. 3 FAIL là help text "landed_unit_cost" không kèm giá trị nào. Đã đếm lại: 0 số giá vốn trên mọi trang.

Hàng thêm cho S48:

| Hành động | NV bị cờ (`giao4`/`kho1` sau reset) | superuser bị gắn cờ | NV cũ sau migrate |
|---|---|---|---|
| `auth/token`, `me`, `logout`, `change-password` | 200/204 | 200 | 200 |
| Mọi API nghiệp vụ khác (đọc và ghi) | 403 `AUTH_MUST_CHANGE_PASSWORD` | không bị chặn | như lần 1 |
| ERP | chỉ mở `/set-password/` | no-role (như lần 1) | như lần 1 |
| Django Admin | **vào được** (B3) | toàn quyền | như lần 1 |

## Rò giá vốn

✅ 0 rò. Đã quét:
- JSON: 23 endpoint router, dashboard, báo cáo, `me` với 6 vai thiếu quyền.
- HTML ERP 8 màn/vai.
- HTML Admin 36–45 trang/vai.
- HTML Shop.

Response 403 `AUTH_MUST_CHANGE_PASSWORD` chỉ có `detail` và `code`, không kèm dữ liệu.

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ Ran 328 tests, OK (12,0 s) · `makemigrations --check --dry-run` → No changes detected |
| `adapter pytest -q` | ✅ 10 passed |
| `erp-console tsc --noEmit` | ✅ exit 0 |
| `erp-console npm run build` (mock / thật trỏ :8000 / thật mặc định) | ✅ exit 0 cả 3; có trang `/set-password` |
| `frontend npm run build` (Shop) | ✅ exit 0 |
| e2e mock: `s48_password.py` 37/37 · `s7_shell.py` 25/25 · `s8_views.py` 36/36 (không truyền `LEGACY_BASE`) | ✅ |
| `shop_e2e.py` (BE thật) 9/9 · webhook qua adapter ×2 | ✅ |

## Lỗi

### B2 — `seed_demo --remove` xoá bản ghi demo con của bản ghi demo đang được giữ lại · Medium · D1 (ngoại lệ "giữ lại khi dữ liệu thật đang dùng")
**Bước tái hiện** (kịch bản A, `d1/runA.sh`):
1. DB mới → `migrate` → `bootstrap_masterdata` → `seed_demo`.
2. Tạo dữ liệu thật trên bản ghi demo: lô thật `LO-REAL-1` trên mặt hàng demo `MUC-ONG`; đơn Shop thật 1 kg `GHE-XANH` (`create_order`, giữ chỗ trên lô demo `LO-0921`).
3. `seed_demo --remove`.

**Mong đợi:** bản ghi demo đang được dữ liệu thật dùng "giữ lại" với trạng thái dùng được. Dữ liệu thật dựa vào chúng vẫn hoạt động như trước.

**Thực tế:** lệnh in đúng là giữ `MUC-ONG`, `GHE-XANH`, `LO-0921`. Nhưng nó vẫn xoá các bản ghi demo con của chúng, vì không bản ghi thật nào trỏ **tới** các bản ghi con đó:
- **Giá bán** (`ItemPrice`) của `MUC-ONG` và `GHE-XANH` → 0 giá.
- **Bút toán nhập kho** `RECEIPT` "Nhập lô LO-0921". Lô vẫn `SELLING`, `qty_received 27`, đang có đơn thật giữ chỗ, nhưng Σ sổ kho của lô = 0 và lô không còn bút toán nào.

Kịch bản B (`--adopt-legacy`, `d1/runB.sh`) cho thấy thêm:
- `CA-THU` được giữ vì có lô thật `LO-QA-EXP` và đơn thật trên `LO-0918`, nhưng mất giá → `GET /api/shop/catalog/` trả `[]`, `/CA-THU/` trả `price: null`. Đặt đơn Shop `CA-THU` → 400 `BR-DM-02` "Không có giá niêm yết hiệu lực".
- `LO-0918` giữ lại nhưng mất bút toán nhập 61 kg.
- Đơn `DH-2609-116` được giữ vì có thanh toán thật `REAL-TXN-777` 2.520.000đ và hoá đơn thật. Đơn vẫn `PROCESSING`, `total_amount` 2.520.000, nhưng **0 dòng đơn**.

**Ảnh hưởng:**
- Khi Lộc đã nhập lô thật trên một mặt hàng demo có tên thật (Cá thu, Mực ống…), gỡ demo sẽ làm **hàng thật ngừng bán trên Shop**. Lộc không được báo, vì `--dry-run` chỉ in số lượng theo model, không nói giá của mặt hàng bị giữ sẽ mất.
- Sổ kho (append-only, bất biến 4) của lô đang có đơn thật bị cắt mất bút toán nhập.
- Đơn đã nhận tiền thật mất dòng hàng.
- Kịch bản dùng lệnh này trên production là `--adopt-legacy`, nên có thể xảy ra ngay ở deploy 1 nếu đã có dữ liệu thật đụng vào bộ demo.

**Gợi ý cho BE:**
- Sau khi tính xong tập "giữ lại", giữ luôn các bản ghi demo có FK trỏ tới bản ghi bị giữ (bao đóng ngược: giá, sổ kho, dòng đơn/HĐ, phiếu giao của HĐ bị giữ), rồi mới xoá.
- Hoặc tối thiểu, không xoá `ItemPrice`/`StockLedgerEntry`/`*Line` của cha bị giữ.
- Muốn lô demo bị giữ không bán tiếp thì đổi trạng thái, không xoá giá.
- Thêm test: lô thật trên mặt hàng demo → sau gỡ, mặt hàng vẫn còn giá và Shop vẫn bán được lô thật.

**Cách tạm nếu PO muốn deploy trước khi sửa:** chạy `seed_demo --remove --adopt-legacy` **trước** khi có bất kỳ dữ liệu thật nào đụng vào bộ demo (ngay sau `migrate`, trước khi mở Shop). Đọc kỹ danh sách "Giữ lại" của `--dry-run`: nếu có dòng nào thì không chạy thật.

### B3 — BR-PQ-19 không phủ Django Admin · Low · S48-AC1 (ghi nhận)
**Bước tái hiện:** Chủ reset MK `kho1` (is_staff) → mở `/admin/login/` → đăng nhập bằng MK tạm.

**Mong đợi:** theo ý BR-PQ-19, người còn MK tạm chưa dùng được hệ thống.

**Thực tế:** vào Admin được và thấy đủ những gì quyền cho phép. Gọi API bằng session thì vẫn bị 403. Dev-notes đã ghi.

**Ảnh hưởng:** nhỏ, vì Admin vẫn ẩn giá vốn theo quyền. Đề xuất middleware cho `/admin/` sau mốc 1.

**Không chặn.**

### B4 — Được "đổi" sang mật khẩu mới trùng mật khẩu tạm · Low · S48-AC2/BR-PQ-19 (ghi nhận)
**Bước tái hiện:** `khoonly` bị reset MK thành `TamKho20261` → `POST /api/auth/change-password/ {"old_password":"TamKho20261","new_password":"TamKho20261"}`.

**Mong đợi:** từ chối, vì màn hình nói "Đặt mật khẩu riêng, chỉ mình bạn biết".

**Thực tế:** 200, cờ về false, và Chủ vẫn biết mật khẩu.

**Ảnh hưởng:** làm mất mục đích của BR-PQ-19 ở trường hợp người dùng cố ý. Không có AC nào yêu cầu mật khẩu mới phải khác mật khẩu cũ. Sửa 1 dòng ở `change_own_password` (mới == cũ → 400 `AUTH_WEAK_PASSWORD`), nên làm cùng lúc sửa B2.

**Không chặn.**

### B1 (lần 1) — `erp-console/legacy/` vẫn còn · Low
Vẫn còn `legacy/index.html`. Theo D2 phải xoá ở mốc deploy 1. Không nằm trong `out/`. **Không chặn.**

### Ghi nhận khác (không chặn)
- **N1:** `business-process-spec.md` §1 vẫn chưa có BR-PQ-17/18/19 (grep = 0).
- **N2:** `--adopt-legacy` gỡ **mọi** phiếu giao của hoá đơn demo, kể cả phiếu người dùng tạo thêm hoặc đang giao (`GH-QA-2` DELIVERING, gán `giao2`). Hợp lý nếu coi mọi thứ trên hoá đơn demo đều là demo. Nên in rõ trong `--dry-run` để người chạy nhìn thấy.
- **N3 (có từ trước, ngoài delta):** `POST /api/internal/payments/sepay-webhook/` thiếu `received_at` trả 500 IntegrityError thay vì 400. Adapter luôn gửi trường này, nên chỉ lộ khi có người gọi thẳng API nội bộ.

## Lệnh đã chạy (kèm output tóm tắt)
```
cd backend && manage.py test                               → Ran 328 tests in 12.041s  OK
cd backend && manage.py makemigrations --check --dry-run   → No changes detected
cd adapter && pytest -q                                    → 10 passed, 1 warning
cd frontend && npm run build                               → exit 0
cd erp-console && tsc --noEmit                             → exit 0
cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build     → exit 0 (có /set-password)
cd erp-console && NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 npm run build → exit 0; grep mock trong out = 0
cd erp-console && npm run build (thật mặc định, để lại trong out/) → exit 0; grep mock = 0; grep 127.0.0.1:8000 = 0
DATABASE_URL=sqlite:///<scratch>/r2_legacy.sqlite3 manage.py migrate → Applying accounts.0004…, 0005… OK; 9 hồ sơ cũ must_change_password=0
e2e/s41_s47_staff.py (mock :3101) ×3                       → 71/71 · 71/71 · 71/71
e2e/s48_password.py · s7_shell.py · s8_views.py (mock)     → 37/37 · 25/25 · 36/36
e2e/s41_s47_real.py (BE thật :8000, console thật :3102) ×2 → 39/39 · 39/39
r2_s48_api.py (BE thật)                                    → 60/61 (1 dòng là webhook thiếu received_at do kịch bản; gửi đủ trường → 200)
r2_erp_s48.py (BE thật + console thật)                     → 24/24
adapter uvicorn :8765 → webhook ×2 cùng id                 → MATCHED ×2, 1 payment; Apikey sai → 401
api_matrix.py 166/172 · erp_matrix.py 55/55 · r2_admin_matrix.py 41/44 (FAIL = như lần 1, 0 lỗi sản phẩm)
shop_e2e.py (next dev :3000 → BE thật)                     → 9/9
d1/runA.sh (DB mới)                                        → seed 49 dấu; dry-run không đổi; gỡ 44, giữ 5; thật 24/24 không đổi; B2
d1/runB.sh (DB seed bản cũ)                                → gỡ 0 khi không adopt; adopt gỡ 45, giữ 8; thật không đổi; Shop catalog [] sau gỡ (B2)
lsof -iTCP -sTCP:LISTEN (8000/8765/3000/3100–3103)         → sạch; ps không còn server
```
Script, ảnh và log nằm trong scratchpad phiên QA: `r2_s48_api.py`, `r2_erp_s48.py`, `r2_admin_flag.py`, `r2_reset_be.sh`, `d1/{runA.sh,runB.sh,snap.py,cmp.py,real_pre.py,real_post.py,pay_real.py}`, `r2shots/`. Không sửa code sản phẩm, không sửa `erp-console/e2e/*`, không thêm test vào repo: test tái hiện B2 để BE viết cùng lúc sửa, tránh để lại test đỏ trong bộ test.

---

# QA — ERP console mốc deploy 1 · lần 3 (xác nhận sửa B2, B3, B4, B5, N3; vòng sửa 1/2) · 2026-09-24

## Kết luận: APPROVED — B2 (Medium) đã sửa. Chạy lại kịch bản A trên DB mới và kịch bản B trên bản sao DB B gốc (có đơn Shop thật trên lô demo). Kết quả: 0 bản ghi thật mất hoặc đổi, chứng từ giữ trọn cụm hoặc gỡ trọn cụm, mặt hàng demo có lô thật vẫn bán được. B3, B4, B5, N3 đạt. Hồi quy xanh. Còn 1 lỗi Low không chặn (B6: thứ tự dòng "Giữ lại" của `--adopt-legacy` không ổn định giữa các lần chạy) và 1 rủi ro vận hành cần đưa vào runbook (lô demo bị giữ vẫn bán tồn demo).

## Tổng: 99 ca · ✅ 96 · ❌ 1 (Low, không chặn) · ⚠ 2 (ghi nhận, không sai contract)

Môi trường:
- Mọi DB là SQLite tạm trong scratchpad, thư mục `d1r3/`. `backend/db.sqlite3` không bị đụng (mtime vẫn 13/09).
- **D1-A:** `runA.sh` xoá rồi tạo lại `a.sqlite3` từ đầu: `migrate` → `bootstrap_masterdata` → tài khoản → dữ liệu thật trước seed → `seed_demo` ×2 → dữ liệu thật sau seed (`LO-REAL-1` trên `MUC-ONG` demo, đơn Shop thật trên lô demo `LO-0921`, AuditLog thật).
- **D1-B:** `runB.sh` lấy `b_orig.sqlite3`, là bản sao `r2.sqlite3`. Đây đúng là DB B gốc của lần 2: sha1 `7033c0f3…` khớp, có đơn Shop thật `SO260924-21242C` giữ chỗ trên lô demo `LO-0918`. BE chỉ chạy được `r2_legacy.sqlite3`, bản này thiếu đơn đó. Thêm thanh toán thật `REAL-TXN-777` cho đơn demo `DH-2609-116`. Trên DB đã có sẵn `LO-QA-EXP`, `PR-1`, `GH-QA-1` (READY, gán `kho1`), `GH-QA-2` (DELIVERING, gán `giao2`) và hoá đơn thật `INV…`.
- **Máy chủ:**
  - BE thật: `runserver` :8000, chạy lần lượt trên `r3.sqlite3` (bản sao `r2_seed`), `r3_realbe.sqlite3` (reset trước mỗi lượt e2e/matrix).
  - Adapter thật: `uvicorn` :8765.
  - Console: mock ở :3101, thật trỏ :8000 ở :3102.
  - Shop: `next dev` :3000.
  - Mọi server có giới hạn thời gian (perl alarm) và bị kill theo PID. Cuối cùng `lsof` trên 8000/8765/3000/3100–3103 không còn gì; `ps` không còn runserver/uvicorn/http.server/next.
- `erp-console/out/` được build lại bản thật mặc định: grep `127.0.0.1:8000` = 0, grep mock = 0.

## D1 — `seed_demo --remove` (B2, B5)

Mỗi bước chụp toàn bộ DB bằng `snap.py`. Có 3 cách đối chiếu:
- `cluster.py`: bản ghi có mặt ở cả hai ảnh chụp phải giống nhau từng trường. Bản ghi bị gỡ không được là con (FK không thuộc danh mục) của bản ghi còn sống. Script viết độc lập, không dùng `REFERENCE_FIELDS` của BE.
- `check.py`: in sổ kho từng lô, giá, đơn + dòng + HĐ + phiếu giao + thanh toán, và Shop catalog.
- `cmp.py`: 24 bản ghi thật của kịch bản A.

| Ca | Kết quả | Bằng chứng (`d1r3/runA.log`, `d1r3/runB.log`) |
|---|---|---|
| A1 `seed_demo` ×2 không nhân đôi | ✅ | "7 mặt hàng · 6 lô · 6 đơn · 3 hoá đơn" cả 2 lần, 49 dấu |
| A2 `--dry-run` không đổi DB | ✅ | `cmp 2_real.json 3_dry.json` → giống từng byte (AuditLog chạy thử cũng hoàn tác) |
| A3 Dry-run khớp lần chạy thật | ✅ | `diff` (bỏ tiền tố "Chạy thử") → **giống hệt**: gỡ 41, giữ 8, cùng lý do, cùng thứ tự |
| A4 Không bản ghi thật nào mất hoặc đổi | ✅ | `cmp.py`: 24/24 còn, 0 trường đổi, cả sau gỡ lẫn sau seed lại + gỡ. `cluster.py` 2_real→4_removed và 6_reseed→7_final: đổi trường = [], con bị gỡ khi cha còn sống = [] |
| A5 (lỗi cũ B2) Giá của mặt hàng bị giữ còn | ✅ | Giữ «Giá niêm yết MUC-ONG 235000» và «GHE-XANH 310000» với lý do "là một phần của Mặt hàng … đang được giữ". `check.py` sau gỡ: `GHE-XANH giá=['310000.00']`, `MUC-ONG giá=['235000.00']` |
| A6 (lỗi cũ B2) Sổ kho lô giữ lại khớp qty | ✅ | `LO-0921 recv=27 ledgerΣ=27 n=1`. Bút toán "Nhập lô LO-0921" được giữ, giống hệt trước khi gỡ |
| A7 Mặt hàng demo có lô thật bán được trên Shop | ✅ | Publish `LO-REAL-1` → `GET /api/shop/catalog/MUC-ONG/` 200, `price 235000`, `sellable_qty 10`. `POST /api/shop/orders/` 201 `SO260924-C02CB0`, phân bổ `LO-REAL-1 × 1` |
| A8 Đơn thật trên lô demo còn đủ | ✅ | `SO260924-AE5C8D` còn 1 dòng, Σ dòng = total 310000, giữ chỗ `LO-0921 × 1` |
| A9 `--remove` lần 2 / seed lại rồi gỡ | ✅ | "Đã gỡ 0". Seed lại → gỡ 41, giữ 8 như lần đầu |
| A10 Dùng cờ sai | ✅ | "--dry-run / --adopt-legacy chỉ dùng cùng --remove.", DB không đổi |
| A11 AuditLog | ✅ | `qa_real_action` còn. Mỗi lần gỡ thêm đúng 1 dòng `demo_remove` (actor Hệ thống) "Gỡ N…; giữ lại M." |
| B1 Legacy chưa có sổ, `--remove` không adopt | ✅ | "Đã gỡ 0 bản ghi demo." |
| B2 `--adopt-legacy --dry-run` không đổi DB | ✅ | `cmp b1.json b2.json` → giống từng byte (0 dấu, không thêm AuditLog) |
| **B3 Dry-run khớp lần chạy thật (adopt)** | ❌ Low (B6) | Cùng số (gỡ 26, giữ 25), cùng tập bản ghi, cùng lý do. **Khác thứ tự** 2 dòng «Nhà cung cấp NK Đại Dương» / «Tàu cá Long Hải». Xem B6 |
| B4 Không bản ghi thật nào mất hoặc đổi (adopt) | ✅ | `cluster.py` b1→b3: đổi trường = []. 26 bản ghi bị gỡ đều thuộc chữ ký demo (đã liệt kê: `BACH-TUOC`, `CA-HOI-NU` + giá, "Vựa Ba Hòn", `LO-0903/0907/0912/0921/0922` + bút toán nhập, khách Chị Mai/Anh Sơn/Chị Lan, `DH-2609-114/115/119` + dòng, `HD-2609-115` + `GH-HD-2609-115-…`) |
| B5 Chứng từ gỡ trọn cụm hoặc giữ trọn cụm | ✅ | `cluster.py` b1→b3, b4→b5: con bị gỡ khi cha còn sống = []. Cụm giữ (`DH-2609-116/117/118` + dòng + HĐ + phiếu giao + khách) còn đủ. Cụm gỡ (`DH-2609-115` + dòng + HĐ + phiếu) đi cùng nhau |
| B6 (lỗi cũ B2) Đơn thật đã thanh toán còn đủ dòng | ✅ | `DH-2609-116 PROCESSING total=2520000 dòng=1 Σdòng=2520000 OK`, HĐ `INV260924-6AFA88` 1 dòng, phiếu giao `GH-INV…`, `tt=['REAL-TXN-777']` (lần 2: 0 dòng) |
| B7 (lỗi cũ B5) Phiếu giao đang giao/đã gán không bị gỡ | ✅ | `GH-QA-1 READY gán 5` và `GH-QA-2 DELIVERING gán 6` còn. HĐ `HD-2609-118/117`, đơn, dòng, khách, phiếu tự sinh của chúng cũng giữ, lý do "đang được dữ liệu thật dùng: Phiếu giao hàng «GH-QA-1/2»" |
| B8 (lỗi cũ B2) Sổ kho lô giữ lại khớp qty | ✅ | `LO-0918 recv=61 ledgerΣ=61 n=1`, giữ chỗ 1 kg của đơn Shop thật còn |
| B9 (lỗi cũ B2) Mặt hàng demo có lô thật bán được trên Shop | ✅ | Sau gỡ, `CA-THU giá=['165000.00']`, catalog có CA-THU (lần 2: `[]`). Tạo lô thật mới `LO-REAL-B` 5 kg, publish → detail `price 165000`, `sellable_qty 65`. Đặt đơn Shop 201 |
| B10 Đơn Shop thật trên lô demo (có trong DB B gốc) | ✅ | `SO260924-21242C` còn dòng + giữ chỗ `LO-0918`, CA-THU và LO-0918 được giữ với lý do nêu đúng đơn này |
| B11 Seed lại sau adopt rồi gỡ | ✅ | Gỡ 26, giữ 25 như trên. `cluster.py` b3→b5: 0 bị gỡ, 0 đổi, chỉ thêm 1 AuditLog |
| B12 Kịch bản B của BE so với DB gốc | ✅ ghi nhận | BE báo "giữ 22". Trên DB gốc là giữ 25: thêm cụm CA-THU/LO-0918/"Tàu cá Long Hải" vì đơn Shop thật. Đúng theo quy tắc bao đóng |

## B4 — đổi sang mật khẩu trùng mật khẩu hiện tại (BR-PQ-19)

`r3_fix.py` (BE thật :8000) **18/18**, cùng `r3_ui_b4.py` (console thật :3102, 390 px) **4/4**.

| Ca | Kết quả |
|---|---|
| Chủ reset `khoonly` → đăng nhập MK tạm → `change-password` old = new = MK tạm | ✅ 400 `{"detail":"Mật khẩu mới phải khác mật khẩu hiện tại.","code":"AUTH_WEAK_PASSWORD"}`, không có `token` |
| Hash MK, cờ `must_change_password`, bảng token trong DB | ✅ không đổi (so trước/sau bằng SQL) |
| Token cũ vẫn sống: `me` 200 và cờ true. API nghiệp vụ vẫn 403 `AUTH_MUST_CHANGE_PASSWORD`. MK tạm vẫn đăng nhập được | ✅ |
| Gửi lại lần 2 (bấm đúp) | ✅ vẫn 400 |
| MK cũ sai + trùng | ✅ 400 `AUTH_OLD_PASSWORD` (kiểm MK cũ trước) |
| Đổi sang MK khác | ✅ 200 + token mới, cờ tắt, token cũ 401 |
| Người không còn cờ đổi trùng MK hiện tại | ✅ 400 `AUTH_WEAK_PASSWORD`, cờ vẫn tắt, token hiện tại vẫn sống |
| UI `/set-password/`: nhập trùng MK tạm | ✅ hộp lỗi hiện nguyên văn detail BE, vẫn ở `/set-password/`. Storage không chứa MK. Đổi sang MK khác → `/my-deliveries/`. Ảnh `r3shots/r3-b4-same-password-390.png` |

## B3 — Django Admin khi còn cờ

`r3_fix.py`: **21/21**.

| Người / trang | Kết quả |
|---|---|
| Ẩn danh `/admin/` | ✅ 302 → `/admin/login/` (middleware không chen vào) |
| `/admin/login/` GET khi chưa đăng nhập; POST bằng MK tạm của `kho1` (is_staff, vừa bị Chủ reset) | ✅ 200; 302 (login vẫn mở) |
| `kho1` còn cờ: `/admin/`, `/admin/sales/salesorder/`, `/admin/inventory/batch/`, `/admin/password_change/`, `/admin/auth/user/`, `/admin/jsi18n/` | ✅ 403 `text/html`, có câu "Bạn cần đặt mật khẩu mới trên ERP console…(BR-PQ-19)" và nút Đăng xuất. Trang < 1,5 KB, không có dữ liệu hay giá vốn |
| `/admin/login/` khi đang có session còn cờ | ✅ mở |
| Nút Đăng xuất trên trang 403 (POST kèm csrf) | ✅ 200. Sau đó `/admin/` → 302 login |
| Superuser `admin` bị gắn cờ thẳng trong DB | ✅ `/admin/` 200, trang con 200 (không bị ép) |
| `ql1` (không cờ) | ✅ `/admin/` 200 |
| `kho1` đổi MK qua API rồi đăng nhập lại Admin | ✅ 200. Session Admin cũ (mở trước khi đổi) → 302 login, do Django xoay session hash |
| `/admin/login` (thiếu `/`) khi còn cờ | ⚪ 403 thay vì redirect sang `/admin/login/`. Không ảnh hưởng, ghi để biết |

## N3 — webhook `received_at`

`r3_fix.py`: 17/19 ✅, 2 ⚠. Gọi trực tiếp với `X-Internal-Token`, rồi qua adapter thật.

| Ca | Kết quả |
|---|---|
| `received_at` thiếu / `""` / `null` / "hôm qua" / `2026-02-30T10:00:00+07:00` / số `1727150000` / `T25:00:00` | ✅ 400 `{"detail":"Thiếu hoặc sai received_at (ISO 8601).","code":"WEBHOOK_INVALID_INPUT"}` |
| Thiếu `received_at` + không khớp đơn (lần 2 là **500**) | ✅ 400 `WEBHOOK_INVALID_INPUT` |
| Thiếu `X-Internal-Token` | ✅ bị chặn trước (401/403) |
| Thiếu `bank_txn_id` / `amount` sai | ✅ 400 JSON cũ, như trước |
| Đủ trường, không khớp đơn | ✅ 200 `matched:false` |
| **Qua adapter thật:** SePay `transactionDate "2026-09-24 15:40:00"`, mã `DH-2609-119` | ✅ 200 `MATCHED`, đơn PROCESSING |
| Gửi lại cùng `id` | ✅ 200, đúng 1 PaymentTransaction `930001` |
| Apikey sai | ✅ 401 |
| Ngày dạng ISO, không có mã đơn | ✅ 200 `matched:false` |
| ⚠ `received_at: "2026-09-24"` (chỉ có ngày) | ⚠ **Được chấp nhận** (200, MATCHED, lưu 00:00 giờ VN). `parse_datetime` nhận ngày ISO. Contract ghi "ISO 8601" và ngày trần cũng là ISO 8601, nên không sai contract. Trước khi sửa, model field cũng nhận giá trị này. Adapter luôn gửi đủ giờ. Hệ quả: ca "không tạo PaymentTransaction" của script đếm thêm 1 giao dịch này (⚠ thứ 2). Đề xuất (không chặn): bắt buộc có phần giờ, vì `received_at` là `issued_at` của hoá đơn (BR-TT-06) |

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ **Ran 345 tests, OK** (11,0 s) |
| `makemigrations --check --dry-run` · `manage.py check` | ✅ No changes detected · 0 issue |
| `adapter pytest -q` | ✅ 10 passed |
| `erp-console tsc --noEmit` | ✅ exit 0 |
| `erp-console npm run build`: mock / thật trỏ :8000 / thật mặc định | ✅ exit 0 cả 3 |
| `frontend npm run build` (Shop) | ✅ exit 0 |
| `e2e/s48_password.py` (mock :3101) | ✅ 37/37 |
| `e2e/s41_s47_staff.py` (mock :3101) | ✅ 71/71 |
| `e2e/s41_s47_real.py` (BE thật :8000 + console thật :3102, reset DB trước mỗi lần) ×2 | ✅ 39/39 · 39/39 |
| `api_matrix.py` (phân quyền + rò giá vốn JSON, 8 vai) | ✅ 166/172. 6 FAIL **giống hệt lần 1 và lần 2** (`diff` rỗng): 4 lần máy quét bắt nhầm cờ `user.can_cost`, 1 lần Chủ không thấy `rate` phiếu nhập (S30), 1 lần SQLite locked khi bấm đúp tạo staff. 0 rò thật |
| `r2_admin_matrix.py` (Admin HTML, có middleware mới) | ✅ 41/44. 3 FAIL giống hệt lần 2 (help text "landed_unit_cost" không kèm giá trị). Lần chạy đầu trên DB đã bị `api_matrix` đổi MK `khoonly` cho ra 1 FAIL do dữ liệu. Chạy lại trên DB sạch thì hết |
| `shop_e2e.py` (Shop :3000 → BE thật) | ✅ 9/9: HTML không có số/chữ giá vốn, bấm đúp → 1 đơn, không phân bổ từ lô quá hạn |

Bảng phân quyền Group × hành động của lần 1 và lần 2 **không đổi**. Hàng S48 thay đổi đúng ở cột Django Admin:

| Hành động | NV còn cờ | superuser bị gắn cờ | NV không cờ |
|---|---|---|---|
| Django Admin (trừ login/logout) | **403 hướng dẫn** (lần 2: vào được) | 200 | 200 |
| `change-password` với MK mới = MK hiện tại | **400 `AUTH_WEAK_PASSWORD`** | — | 400 `AUTH_WEAK_PASSWORD` |

## Rò giá vốn
✅ 0 rò:
- JSON API: `api_matrix` với 6 vai thiếu quyền.
- HTML Admin: `r2_admin_matrix`, 36–46 trang/vai.
- HTML Shop: `shop_e2e`.
- Trang 403 Admin mới và JSON 400 của B4/N3 chỉ có `detail`/`code`.

## Lỗi

### B6 — Thứ tự dòng "Giữ lại" của `--adopt-legacy` không ổn định giữa các lần chạy · Low · D1
**Bước tái hiện:**
1. `cp d1r3/b_orig.sqlite3 x.sqlite3` → `migrate`.
2. `manage.py shell < d1r3/pay_real.py`.
3. `seed_demo --remove --adopt-legacy --dry-run`, rồi `seed_demo --remove --adopt-legacy`.

**Mong đợi:** hai lần in giống hệt, theo dev-notes: "Dry-run đi đúng đường chạy thật rồi rollback → danh sách giống hệt".

**Thực tế:** cùng số, cùng bản ghi, cùng lý do. Nhưng 2 dòng «Nhà cung cấp NK Đại Dương» và «Tàu cá Long Hải» đổi chỗ cho nhau (`runB.log` mục "DIFF dry vs real").

**Nguyên nhân:** `adopt_legacy()` duyệt `for sname in {b[2] for b in BATCHES}`. Thứ tự duyệt một `set` chuỗi đổi theo hash seed của từng tiến trình Python. Vì vậy `DemoRecord` được tạo theo thứ tự khác, và danh sách in theo pk sổ cũng khác. Kịch bản A (không adopt) thì luôn giống hệt.

**Ảnh hưởng:** người chạy so bằng mắt hoặc `diff` sẽ tưởng dry-run khác lần thật. Dữ liệu không sai.

**Gợi ý:** dùng `sorted({…})` hoặc `dict.fromkeys(...)`.

**Không chặn.**

### Còn từ trước (không chặn)
- B1 (lần 1): `erp-console/legacy/index.html` vẫn còn.
- N1: `business-process-spec.md` vẫn chưa có BR-PQ-17/18/19 (grep = 0).

## Ghi nhận — lô demo bị giữ vẫn đang bán tồn demo

Đã tái hiện đúng như dev-notes mô tả:
- **Kịch bản A:** sau khi gỡ, `LO-0921` (demo, 27 kg "ảo") vẫn `SELLING`. Shop hiện `GHE-XANH sellable_qty 26`. Khách mới đặt 1 kg → 201, phân bổ `LO-0921`.
- **Kịch bản B (nặng hơn):** nhập lô thật `LO-REAL-B` 5 kg Cá thu. Shop hiện `sellable_qty 65`, trong đó 60 kg là tồn demo của `LO-0918`. Đơn Shop thật được FIFO phân bổ vào **lô demo `LO-0918`, không vào lô thật**, vì lô demo hết hạn sớm hơn.

**Đánh giá:**
- Mức độ nếu xảy ra là cao, thuộc nhóm "sai tồn kho / mất tiền":
  - khách chuyển tiền cho hàng không có;
  - kho soạn theo lô không tồn tại;
  - lô thật đứng yên đến hết hạn;
  - lãi lỗ ghi theo giá vốn demo.
- Xác suất thấp nếu làm theo quy trình deploy 1: chạy `seed_demo --remove --adopt-legacy` ngay sau `migrate`, **trước** khi mở Shop, lúc chưa có dữ liệu thật nào dùng tới demo. Khi đó tập giữ lại rỗng.
- Hành vi đúng như mô tả trong "Còn nợ" và không có AC nào yêu cầu khác, nên **không chặn**.

**Đề xuất:**
1. **Runbook deploy 1 (bắt buộc):** chạy `--dry-run` trước. Nếu danh sách "Giữ lại" có bất kỳ «Lô hàng …» nào thì dừng, không mở Shop, và báo PO.
2. **BE (nhỏ, nên làm ở vòng sau):** cuối lệnh in cảnh báo riêng cho lô demo bị giữ còn `qty_available − qty_reserved > 0` ở trạng thái đang bán, ví dụ: "LO-0918 còn 60 kg tồn demo đang bán trên Shop — đóng/huỷ phần còn lại trên ERP".
3. **Story riêng (cần PO chốt, BR-LO/BR-KK):** cho phép chuyển lô demo bị giữ sang trạng thái không bán, hoặc hạch toán huỷ phần tồn demo, có AuditLog. Không tự làm trong `--remove`, vì đổi tồn là việc nghiệp vụ.

## Ghi nhận khác (ngoài delta, không chặn)
- **N5:** webhook nhận `received_at` chỉ có ngày (xem N3 ⚠).
- **N6:** giao dịch thứ hai (khác `bank_txn_id`) cho đơn đã PROCESSING được ghi `MATCHED` (`confirm_payment`: "coi như đã khớp"). Khách chuyển khoản 2 lần thì tiền thừa không vào hàng chờ Chủ hoàn. Có từ trước. Đề xuất BA xem lại BR-TT-04/05.
- **N7:** adapter nhận `transactionDate` không parse được → adapter trả **500** (ValueError trong `parse_transaction_date`), SePay sẽ gửi lại mãi. Có từ trước, không nằm trong delta.

## Lệnh đã chạy (kèm output tóm tắt)
```
d1r3/runA.sh (DB mới từ đầu)                    → seed 49 dấu; dry-run == thật (diff rỗng); gỡ 41 giữ 8; cmp 24/24 không đổi;
                                                  cluster 0 vi phạm; giá GHE-XANH/MUC-ONG còn; LO-0921 ledgerΣ 27 = recv
sell_real.py (MUC-ONG/LO-REAL-1, GHE-XANH)      → detail 200 có giá; POST shop/orders 201 ×2
d1r3/runB.sh (bản sao DB B gốc r2.sqlite3)      → gỡ 0 khi không adopt; adopt dry-run DB không đổi; gỡ 26 giữ 25;
                                                  cluster b1→b3, b4→b5, b3→b5: 0 đổi, 0 vi phạm; DH-2609-116 1 dòng;
                                                  GH-QA-1/2 còn; CA-THU có giá, bán được; diff dry/thật: lệch thứ tự 2 dòng (B6)
ord_1..5 (adopt dry-run ×5 trên bản sao mới)    → sort(out) giống nhau: chỉ khác thứ tự
r3_fix.py (BE :8000 + adapter :8765)            → 56/58 (2 ⚠ received_at chỉ có ngày, xem N3)
r3_ui_b4.py (console thật :3102)                → 4/4
cd backend && manage.py test                    → Ran 345 tests in 10.995s  OK
makemigrations --check --dry-run · check        → No changes detected · 0 issues
cd adapter && pytest -q                         → 10 passed
erp-console tsc --noEmit                        → exit 0
erp-console build mock / thật :8000 / mặc định   → exit 0 ×3; out/ mặc định: grep 127.0.0.1:8000 = 0, mock = 0
frontend npm run build                          → exit 0
e2e s48_password.py · s41_s47_staff.py (mock)   → 37/37 · 71/71
e2e s41_s47_real.py (BE thật) ×2                → 39/39 · 39/39
api_matrix.py                                   → 166/172 (6 FAIL = lần 2, diff rỗng)
r2_admin_matrix.py (DB sạch)                    → 41/44 (3 FAIL = lần 2, diff rỗng)
shop_e2e.py                                     → 9/9
kill PID; lsof 8000/8765/3000/3100–3103         → sạch; ps không còn server
```
Script, log, ảnh (trong scratchpad phiên QA):
- `d1r3/{runA.sh,runB.sh,check.py,cluster.py,sell_real.py,real_lot_b.py,removed_list.py,runA.log,runB.log,b_orig.sqlite3}`
- `r3_fix.py`, `r3_fix.out`, `r3_ui_b4.py`, `r3_reset_be.sh`, `r3shots/`

Không sửa code sản phẩm, không thêm test vào repo.

---

# QA — ERP console mốc deploy 1 · lần 4 (sửa theo code review BE R1–R7 + FE 3 mục) · 2026-09-24

## Kết luận: APPROVED cho deploy 1. R1–R7 và 3 mục FE đều đạt trên backend thật. Tiền: 0 bản ghi sai, không nhân đôi. Giá vốn: 0 rò với 6 vai + ẩn danh. Hồi quy xanh. Có 1 lỗi Medium (B7) ở **adapter**: trả 500 thay vì 400 khi `transferAmount` ≤ 0 hoặc là NaN trần. Lỗi này có từ trước, adapter không đổi từ 14/09, không nằm trong deploy 1 (adapter chưa deploy), và không ghi dữ liệu nào. B7 **chặn việc deploy adapter**, không chặn deploy 1. Thêm 2 lỗi Low (B8, B9).

## Tổng: 58 ca (dòng bảng; ~300 phép kiểm tự động bên trong) · ✅ 53 · ❌ 3 (B7 Medium ngoài delta · B8 Low · B9 Low) · ⚪ 2 (lỗi dựng kịch bản của script QA, đã loại/chạy lại đúng)

Môi trường:
- Mọi DB là SQLite tạm trong scratchpad: `r4_web.sqlite3` (DB mới: migrate → bootstrap → tài khoản → `seed_demo`), `d1r4/a.sqlite3` và `ttl.sqlite3`, `d1r4/b.sqlite3` (bản sao DB B gốc của lần 3, `b_orig.sqlite3`), `r4_realbe.sqlite3` (reset mỗi lượt e2e). `backend/db.sqlite3` không bị đụng (mtime vẫn 13/09).
- **Máy chủ:**
  - Django `runserver`: :8000 (có token nội bộ), :8003 (**không** cấu hình token), :8001 (runserver DEBUG=0), :8002 (gunicorn DEBUG=0).
  - Adapter `uvicorn`: :8765.
  - Console: bản mock :3101, bản thật trỏ :8000 ở :3102.
  - Shop: `next dev` :3000.
- Mọi server có giới hạn thời gian (perl alarm) và bị kill theo PID. Cuối cùng `lsof` trên 8000–8003/8765/3000/3100–3103 sạch, `ps` không còn runserver/uvicorn/gunicorn/http.server/next.
- `erp-console/out/` là bản build thật mặc định: 0 chuỗi mock, 0 `127.0.0.1:8000`.

## R1 · R3 · R5 — Webhook SePay (`r4_webhook.py`: 83/86)

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| R1 gọi thẳng, `amount` = `"NaN"`, `"nan"`, `"sNaN"`, `"Infinity"`, `"-Infinity"`, `"inf"`, `-5`, `"-705000"`, `0`, `"0"`, `"0.00"`, `"-0"`, `"abc"`, `""`, `"  "`, `null`, `[..]`, `{..}`, `true`, `"1,000"`, thiếu | ✅ 21/21 | 400 `{"detail":"Số tiền (amount) không hợp lệ — phải là số hữu hạn lớn hơn 0.","code":"WEBHOOK_INVALID_INPUT"}` |
| R1 JSON trần `NaN` / `Infinity` (không có nháy) | ✅ | 400, không 500 |
| R1 NaN ở nhánh không mã đơn (hàng chờ) | ✅ | 400 |
| R1 sau 24 lần gửi sai: số PaymentTransaction, hoá đơn, trạng thái DH-2609-119 (BOOKED), tồn/giữ chỗ mọi lô | ✅ | không đổi. 0 mã `R4-BAD-*` trong hàng chờ |
| Hợp lệ `705000` cho DH-2609-119 | ✅ | 200 `{"matched":true,"order_status":"PROCESSING","match_status":"MATCHED"}`, đúng +1 PT, +1 HĐ |
| Hợp lệ, số thực JSON `12345.5`, không mã đơn | ✅ | 200 `matched:false`, hàng chờ UNMATCHED 12345.50 |
| R5 gửi lại mã GD đã MATCHED: `order_code` đúng / thiếu / rỗng / không tồn tại | ✅ 4/4 | 200 đúng `{"matched":true,"order_status":"PROCESSING","match_status":"MATCHED"}` (lần 3: thiếu mã thì ra `matched:false`) |
| R5 gửi lại cùng mã GD nhưng `amount` khác | ✅ | trả kết quả cũ, amount đã ghi không bị đè |
| R5 gửi lại UNDERPAID thiếu mã · UNMATCHED thiếu mã · ORPHAN sai mã | ✅ 3/3 | `{"matched":false,"order_status":"BOOKED","match_status":"UNDERPAID"}` · `order_status:null` · `{"matched":false,"order_status":"AUTO_CANCELLED","match_status":"ORPHAN"}` |
| R5 UNMATCHED gửi lại **kèm** mã đơn đúng và đủ tiền | ✅ | không tự khớp lại, đơn vẫn BOOKED (khớp tay là việc của Chủ, BR-TT-05) |
| R5 mỗi `bank_txn_id` có đúng 1 bản ghi, không HĐ mới do gửi lại | ✅ | `max(count group by bank_txn_id) = 1` |
| **R5 gửi lại mã GD đã MATCHED nhưng `order_code` là một đơn khác đang BOOKED** | ❌ Low (B8) | 200 `{"matched":true,"order_status":"BOOKED",…}`: trạng thái trả về là của đơn khác. Dữ liệu không đổi |
| R5 `bank_txn_id` 101 ký tự · 101 ký tự Unicode · 5000 ký tự kèm mã đơn đúng | ✅ 3/3 | 400 `WEBHOOK_INVALID_INPUT`, không PT mới, đơn vẫn BOOKED |
| R5 biên: đúng 100 ký tự · 100 ký tự + khoảng trắng hai đầu · id kiểu số · thiếu id | ✅ 4/4 | 200 · 200 (strip) · 200 · 400 `WEBHOOK_INVALID_INPUT` |
| R3 token: sai, rỗng, thiếu, UTF-8 không ASCII, latin-1, byte rác `\xff\xfe\x80`, đúng + ký tự thừa, chỉ tiền tố đúng, dài 6000 | ✅ 9/9 | 401 `{"detail":"Sai service token."}`, không 500 (log Django 0 traceback) |
| R3 server **chưa cấu hình** token (:8003): header rỗng / thiếu / bất kỳ | ✅ 3/3 | 401 |
| R3 sau các lần gửi token sai | ✅ | không PT mới, DH-2609-116 vẫn BOOKED |
| **Adapter**: `transferAmount` = `"NaN"`, `"Infinity"`, `"-Infinity"`, `"abc"`, `""`, `null`, `[1]`, thiếu | ✅ 8/8 | 400 (pydantic) |
| **Adapter**: `transferAmount` = `-5`, `0`, NaN trần | ❌ Medium (B7) | **500 Internal Server Error**. Không ghi PT/HĐ, đơn không đổi |
| Adapter Apikey sai · thiếu `Authorization` · Apikey không ASCII | ✅ 3/3 | 401 |
| Adapter hợp lệ → gửi lại cùng `id` → gửi lại cùng `id` nhưng mất mã đơn | ✅ 3/3 | 200 MATCHED/PROCESSING cả 3 lần (lần 3 bị `matched:false`). Đúng 1 PT `940001`, 1 HĐ, 1 bút toán SALE |

## R2 — Khởi động an toàn (settings)

| Ca (DATABASE_URL = SQLite tạm; `.env` dev chỉ có `DJANGO_DEBUG`, `load_dotenv` không đè biến đã đặt) | Kết quả |
|---|---|
| `DJANGO_DEBUG=0` + key ngẫu nhiên 67 ký tự: `check --deploy`, `migrate`, `cancel_expired_orders` | ✅ chạy được. Chỉ còn 2 cảnh báo HSTS/SSL_REDIRECT (Cloud Run kết thúc TLS, như trước). Không có W009/W018 |
| `runserver` (DEBUG=0 + key) | ✅ `/api/shop/catalog/` 200 · `/api/auth/me/` 401 · `/admin/` 302 · 404 không có trang debug (0 dấu Traceback/URLconf) |
| `gunicorn config.wsgi` 2 worker (như CMD Dockerfile, DEBUG=0 + key) | ✅ giống `runserver`: 200/401/302/404, không có trang debug |
| DEBUG=0 thiếu key · DEBUG rỗng (quên biến) · DEBUG=`false` · key toàn khoảng trắng · key dev · key placeholder của `.env.example` | ✅ 6/6 dừng ngay với `ImproperlyConfigured: DJANGO_SECRET_KEY thiếu hoặc đang là key dev/placeholder…` |
| DEBUG=0 thiếu key với `runserver`, `gunicorn` (master tắt), `migrate`, `cancel_expired_orders`, `shell` | ✅ 5/5 dừng |
| `DJANGO_DEBUG=1` thiếu key (dev) | ✅ chạy (W009/W018 như mong đợi) |
| Dockerfile | ✅ `RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput`: chạy lại y lệnh này (`--dry-run`) không cần key, 154 file. Runtime `CMD gunicorn` không mang `DJANGO_DEBUG=1` của bước build (biến chỉ đặt cho một lệnh `RUN`). `.env` có trong `.dockerignore` và `.gitignore`, nên image không mang DEBUG=1 của máy dev |

Runbook bước 3/4/6 đã ghi rõ các job `cangca-migrate`, `cangca-ttl`, `cangca-batch-status` phải có `DJANGO_SECRET_KEY` + `DJANGO_DEBUG=0`. Ca "cancel_expired_orders thiếu key → dừng" cho thấy job TTL cũ sẽ **dừng** nếu đổi sang image v4 mà thiếu biến. Chưa kiểm env thật của Cloud Run (không đụng production).

## R4 — `seed_demo` mới (`d1r4/runA.sh`, `d1r4/runB.sh`, `d1r4/r4_check.py`)

`r4_check.py` kiểm từng lô, đơn và hoá đơn:
- **Lô:** `qty_reserved` = Σ phân bổ của đơn BOOKED; Σ sổ kho = `qty_available`; Σ RECEIPT = `qty_received`; 0 ≤ giữ chỗ ≤ tồn.
- **Đơn:** Σ dòng = total; Σ phân bổ lô = qty dòng; đơn đã thanh toán có HĐ và PT MATCHED; đơn BOOKED hoặc huỷ không có HĐ.
- **Hoá đơn:** Σ dòng = amount = total đơn; `unit_cost` = landed của lô; bút toán SALE = −qty.
- **Báo cáo:** `period_pnl` và Tổng quan `revenue_today`/`inventory_value` so với tính tay từ hoá đơn và lô.

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| Seed trên DB sạch | ✅ 61/61 | 6 lô, 6 đơn, 3 HĐ. Giữ chỗ: `LO-0903` 6 = DH-2609-116, `LO-0907` 3 = DH-2609-119, các lô khác 0. `LO-0918` recv 67 → sổ 61, `LO-0921` 29 → 27 |
| Doanh thu / giá vốn Tổng quan khớp hoá đơn | ✅ | `revenue_today` 1.610.000 = 660.000 + 620.000 + 330.000 = `period_pnl.revenue`. `cogs` 1.180.000 = Σ qty × unit_cost. `inventory_value` 42.212.000 = Σ tồn × landed. qty tồn/giữ chỗ từng dòng lô trên Tổng quan = DB |
| Seed lần 2 | ✅ 61/61 | số liệu y hệt lần 1, không nhân đôi |
| `cancel_expired_orders` (đẩy hạn 2 đơn BOOKED về quá khứ) | ✅ | "Đã huỷ 2 đơn". `LO-0903` giữ 6 → 0, `LO-0907` 3 → 0, `qty_available` không đổi. 2 AuditLog `cancel_unpaid_expired`. Lần 2: "Đã huỷ 0". Kiểm lại 61/61. Doanh thu/giá vốn không đổi |
| `--remove` kịch bản A (DB mới + dữ liệu thật) | ✅ | Gỡ 49, giữ 18. Dry-run **giống hệt** lần chạy thật. Dry-run không đổi DB (cmp từng byte). `cmp.py` 24 bản ghi thật: thiếu 0, đổi 0. `cluster.py`: con bị gỡ khi cha còn sống = []. Gỡ lần 2 → 0. Seed lại + gỡ → 49/18 |
| `--remove --adopt-legacy` kịch bản B (bản sao DB B gốc) | ✅ | Gỡ **26**, giữ **25**, **khớp lần 3**. Dry-run giống hệt lần chạy thật: nay cả thứ tự dòng cũng giống, vì `sorted(...)` đã sửa B6. `cluster` b1→b3: đổi trường = [], con mồ côi = []. `DH-2609-116` (thanh toán thật `REAL-TXN-777`) còn đủ dòng + HĐ. `GH-QA-1/2` còn. Đơn Shop thật `SO260924-21242C` còn giữ chỗ `LO-0918`. CA-THU có giá và bán được |
| Sau khi thêm dữ liệu thật (kịch bản A) | ⚪ 67/69 | 2 FAIL là của **script QA**: `real_post.py` tạo `LO-REAL-1` thẳng bằng ORM, không có bút toán nhập. Không phải lỗi BE |
| **Seed lại trên DB B đã adopt rồi gỡ** | ❌ Low (B9) | Xem B9: seed mới bán 2 kg từ lô demo bị giữ `LO-0918` để tạo DH-2609-115 + HĐ 330.000đ. Sau đó `--remove` không gỡ được cụm này. Dữ liệu thật không đổi (`cluster` b3→b5: chỉ `LO-0918` demo 61 → 59) |

## R6 — Tổng quan (`r4_r6.py`: 66/66)

Thêm 7 lô CA-THU (giá vốn 91234.56, giá mua 81234.56 để dò rò):
- `LO-R6-EXP`: SELLING, hết hạn hôm qua.
- `LO-R6-NEEXP`: NEAR_EXPIRY, hết hạn 3 ngày trước.
- `LO-R6-DRAFT`: DRAFT, còn 3 ngày.
- `LO-R6-TODAY`: SELLING, hạn = hôm nay.
- `LO-R6-EDGE`: SELLING, hạn = hôm nay + 14.
- `LO-R6-OVER`: SELLING, hạn = hôm nay + 15.
- `LO-R6-CLOSED`: CLOSED, còn 2 ngày.

| Ca | Kết quả |
|---|---|
| `near_expiry_days` = 14 ở **cấp gốc**, không nằm trong `kpis` | ✅ |
| `kpis.near_expiry` = 8 (6 lô demo + TODAY + EDGE) | ✅ |
| EXP, NEEXP, DRAFT, OVER, CLOSED không vào `alerts`. Dòng lô có mặt thì cờ `near_expiry=false` (DRAFT vẫn hiện trong bảng lô, không cờ) | ✅ |
| TODAY, EDGE có cờ `near_expiry=true`. `alerts` ≤ 6, sắp theo hạn, `days_left ≥ 0` | ✅ |
| `BATCH_NEAR_EXPIRY_DAYS=5` (env) | ✅ `near_expiry_days` 5, KPI 4 (hạn 0/1/2/3 ngày) |
| Rò giá vốn: `ql1`, `ql9` (quan_ly), `kho1` (nv_kho+nv_giao), `khoonly` (nv_kho), `giao1` (nv_giao), `moi1` (không nhóm), ẩn danh × summary / `inventory/batches` / `reports/period` / `reports/batch` / Shop catalog / Shop chi tiết | ✅ 42/42. Không có key `landed_unit_cost`/`purchase_rate`/`unit_cost`/`inventory_value`/`cogs`/`profit`/`cost`, không có giá trị `91234(.56)`/`81234(.56)`. Người thiếu quyền: `kpis` đúng 4 key, `can_cost:false` |
| Phân quyền kèm theo: summary 200 cho quan_ly/nv_kho, 403 cho nv_giao và người không nhóm, 401 cho ẩn danh. `reports/*` 403 cho mọi vai không phải Chủ | ✅ không đổi so với lần 1–3 |
| Chủ vẫn thấy `unit_cost` + `inventory_value` | ✅ |

## FE — sửa theo code review (console thật :3102 + BE thật; mock :3101)

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| #1 Gỡ `reports.view_dashboard` khỏi Group `nv_kho` (DB tạm). `khoonly` vẫn có `inventory.view_batch` (xác nhận qua `/me`) | ✅ 19/19 (`r4_fe1.py`), 1280 và 390 | Menu không có Tổng quan / Đơn & tiền / Kho & lô. Home không phải `/overview/`. Gõ `/inventory/`, `/orders/`, `/overview/` → "Bạn không có quyền xem mục này". **0 request `/api/dashboard/summary/`**. `/me` không lặp. Không lỗi console. Ảnh `r4shots/r4-fe1-khoonly-*` |
| #1 Đối chứng: trả lại quyền → `khoonly` thấy Kho & lô, mở được, có gọi summary | ✅ | `CONTROL … True True True` |
| #2 Chủ reset `khoonly` (390 px, về Tổng quan) và `giao1` (1280 px, về Việc giao) → đặt MK mới | ✅ | `.pw-done-notice` hiện đúng câu "Đã đặt mật khẩu mới. Lần sau đăng nhập bằng mật khẩu này.". Đóng được. Storage không chứa MK tạm/mới. Cờ BE tắt. Đăng nhập lại → không còn thông báo. Không lỗi console. Ảnh `r4shots/r4-fe2-*` |
| #3 Ô "Lô cận hạn" với BE thật | ✅ | Ghi "trong 14 ngày tới". Số trên ô = `kpis.near_expiry` của BE. Ảnh `r4shots/r4-fe3-overview-loc-1280.png` |
| e2e mock `s8_views.py` (có ca #1/#3 mới, mode `nodays`) | ✅ 46/46 | |
| e2e mock `s48_password.py` (có ca #2 mới) | ✅ 41/41 | |
| ⚪ Script QA bị loại | — | (a) Tài khoản chỉ có quyền lẻ, không thuộc Group nào: BE trả `home: "no-role"` và console hiện "Tài khoản chưa được phân quyền". Đúng thiết kế S7. Đã làm lại bằng cách gỡ quyền khỏi Group như trên. (b) Ca kho1 goto trước khi đăng nhập xong. (c) Nút đóng 40×40 ở 1280 px là đúng design token: `--tap:40px` từ ≥1024 px, 44 px trên mobile (390 px đo được 44×44) |

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ **Ran 369 tests, OK** (14,2 s) |
| `makemigrations --check --dry-run` · `manage.py check` | ✅ No changes detected · 0 issues |
| `adapter pytest -q` | ✅ 10 passed. Không có test nào cho `transferAmount ≤ 0` đi hết qua endpoint, nên B7 lọt |
| `erp-console tsc --noEmit` | ✅ exit 0 |
| `erp-console npm run build`: mock / thật trỏ :8000 / thật mặc định | ✅ exit 0 ×3. `out/` mặc định: `__caveMock`, `cave_erp_mock`, `demo1234`, `mock-token-`, `mockRequestLog`, `127.0.0.1:8000` = 0 |
| `frontend npm run build` (Shop) | ✅ exit 0 |
| e2e `s41_s47_real.py` (BE thật, reset DB trước mỗi lần) ×2 | ✅ 39/39 · 39/39 |
| `shop_e2e.py` (Shop :3000 → BE thật) | ✅ 9/9: HTML không có số/chữ giá vốn, bấm đúp → 1 đơn, không phân bổ từ lô quá hạn |

## Lỗi

### B7 — Adapter trả 500 khi `transferAmount` ≤ 0 hoặc là NaN trần · Medium · R1 (qua adapter) · có từ trước, ngoài delta
**Bước tái hiện:**
1. `cd adapter && DJANGO_INTERNAL_URL=http://127.0.0.1:8000 INTERNAL_SERVICE_TOKEN=x SEPAY_WEBHOOK_SECRET=s .venv/bin/python -m uvicorn app.main:app --port 8765`
2. `curl -X POST :8765/webhook/sepay -H 'Authorization: Apikey s' -H 'Content-Type: application/json' -d '{"id":1,"gateway":"VCB","transactionDate":"2026-09-24 15:40:00","accountNumber":"1","code":"DH-1","content":"x","transferType":"in","transferAmount":0}'`. Ra 500 giống vậy với `-5`, và với `NaN` viết trần trong JSON.

**Mong đợi:** 400 "Payload SePay không hợp lệ", đúng như khi gửi `"abc"` hoặc `"NaN"` có nháy.

**Thực tế:** 500 Internal Server Error. Log uvicorn:
- Số ≤ 0: `TypeError: Object of type ValueError is not JSON serializable`. `HTTPException(detail={"errors": exc.errors()})` ở `adapter/app/main.py:115` chứa `ctx.error` là một đối tượng `ValueError` do validator `amount_must_be_positive` ném ra.
- NaN trần: `input_value=nan`. Starlette `JSONResponse` không cho NaN nên cũng ra 500.

**Ảnh hưởng:**
- Không mất/sai tiền: request dừng ở adapter, Django không nhận gì, 0 PaymentTransaction.
- SePay nhận 5xx thì có thể gửi lại nhiều lần.
- Log báo lỗi sai bản chất.
- Dev-notes ghi "Adapter không cần đổi: đã chặn `transferAmount ≤ 0` ở schema". Ý chặn thì đúng, nhưng mã trả về là 500 chứ không phải 400.

**Phạm vi:** file adapter không đổi từ 14/09, adapter **chưa deploy** (bộ nhớ deploy), deploy 1 không gồm adapter. **Chặn deploy adapter, không chặn deploy 1.**

**Gợi ý:** trả `exc.errors(include_context=False)` (hoặc `jsonable_encoder`); thêm test adapter cho `transferAmount` 0/−5/NaN đi hết qua endpoint.

### B8 — Gửi lại mã GD đã khớp kèm mã của một đơn khác → trả trạng thái của đơn khác · Low · R5
**Bước tái hiện:**
1. `POST /api/internal/payments/sepay-webhook/ {"bank_txn_id":"R4-OK-119","order_code":"DH-2609-119","amount":"705000","received_at":"…"}` → MATCHED/PROCESSING.
2. Gửi lại cùng `bank_txn_id` nhưng `order_code: "DH-2609-116"` (đơn khác, BOOKED).

**Mong đợi (theo contract R5):** trả kết quả đã ghi: `order_status` = PROCESSING (của DH-2609-119).

**Thực tế:** `{"matched":true,"order_status":"BOOKED","match_status":"MATCHED"}`. Nhánh có đơn gọi `confirm_payment`, hàm này trả PT cũ, nhưng response lại đọc `order.status` của đơn trong request.

**Ảnh hưởng:** chỉ phản hồi sai, dữ liệu không đổi (DH-2609-116 vẫn BOOKED, không PT/HĐ mới). SePay gửi lại cùng payload nên thực tế gần như không xảy ra.

**Gợi ý:** ở nhánh có đơn, nếu `bank_txn_id` đã tồn tại thì dùng `_existing_response(existing)`.

### B9 — Chạy `seed_demo` trên DB có lô demo đang bị giữ → sinh đơn + hoá đơn demo mới trên lô đó, rồi không gỡ được · Low · R4 / D1
**Bước tái hiện:**
1. `cp d1r4/b_orig.sqlite3 x.sqlite3`, `migrate`, `shell < pay_real.py`.
2. `seed_demo --remove --adopt-legacy`: giữ `LO-0918` vì đơn Shop thật `SO260924-21242C`.
3. `seed_demo`.
4. `seed_demo --remove`.

**Thực tế:**
- Bước 3 tạo lại `DH-2609-115` COMPLETED: bán 2 kg từ `LO-0918` (sổ 61 → 59), `HD-2609-115` 330.000đ, `DEMO-DH-2609-115`, phiếu giao.
- Bước 4 giữ cả cụm vì "phụ thuộc bản ghi demo đang được giữ", nên doanh thu và giá vốn demo nằm lại trong báo cáo kỳ.
- Lần 3 (seed cũ không lập HĐ) thì seed lại + gỡ sạch (b3→b5: 0 đổi).
- Dữ liệu thật không đổi.

**Ảnh hưởng:** chỉ xảy ra khi có người chạy `seed_demo` (không cờ) trên DB đã có dữ liệu thật. Runbook deploy 1 chỉ chạy `--remove`. `seed_demo` không có chốt chặn production (không kiểm DEBUG).

**Gợi ý:**
- (1) Runbook: ghi rõ **không chạy `seed_demo` không cờ trên production**.
- (2) BE (vòng sau): bỏ qua đơn demo nếu lô demo đích đang có phân bổ của dữ liệu thật, hoặc từ chối seed khi `DEBUG=0` trừ khi có `--force`.

### Còn từ trước (không chặn)
- B6 (lần 3) **đã sửa**: `sorted({…})`. Dry-run adopt giống hệt lần chạy thật.
- B1 (lần 1): `erp-console/legacy/index.html` vẫn còn. Runbook bước 7 xoá sau deploy.
- N1: `business-process-spec.md` vẫn chưa có BR-PQ-17/18/19 (grep = 0).
- N5/N6/N7 của lần 3 không đổi (N7 cùng loại với B7: adapter 500 khi `transactionDate` hỏng).

## Lệnh đã chạy (kèm output tóm tắt)
```
backend manage.py test                              → Ran 369 tests in 14.202s OK
makemigrations --check --dry-run · check            → No changes detected · 0 issues
adapter pytest -q                                   → 10 passed
r4_webhook.py (BE :8000/:8003 + adapter :8765)      → 83/86 (3 FAIL = B7 ×2 ca + NaN trần; B8 ghi INFO)
R2 ma trận settings (check/migrate/cancel_expired/  → key thật: chạy; thiếu/rỗng/dev/placeholder/DEBUG rỗng|false: ImproperlyConfigured
   shell/runserver :8001/gunicorn :8002)               runserver + gunicorn DEBUG=0: 200/401/302/404, 0 trang debug; collectstatic kiểu Dockerfile: 154 file
d1r4/runA.sh                                        → R4 check 61/61 ×3 (seed1, seed2, sau TTL); TTL "Đã huỷ 2" rồi "0"; gỡ 49 giữ 18;
                                                      dry == thật (GIỐNG HỆT); cmp 24/24 không đổi; cluster 0 vi phạm
d1r4/runB.sh                                        → adopt gỡ 26 giữ 25 (= lần 3); dry == thật; cluster 0 vi phạm; seed lại + gỡ: B9
r4_r6.py                                            → 66/66 (R6 + rò giá vốn 7 vai × 6 endpoint)
BATCH_NEAR_EXPIRY_DAYS=5                            → near_expiry_days 5, KPI 4
erp-console tsc · build mock/thật/mặc định          → exit 0 ×4; out/ mặc định 0 chuỗi mock, 0 127.0.0.1:8000
frontend npm run build                              → exit 0
e2e s8_views.py · s48_password.py (mock :3101)      → 46/46 · 41/41
r4_fe1.py (console thật :3102, nv_kho mất dashboard) → 19/19 + đối chứng dương
r4_fe_real.py (FE2/FE3)                             → FE2/FE3 đạt; 6 FAIL của script đã loại (xem ⚪)
e2e s41_s47_real.py ×2 (BE thật, reset DB)          → 39/39 · 39/39
shop_e2e.py                                         → 9/9
kill PID; lsof 8000–8003/8765/3000/3100–3103; ps     → sạch
```
Script, log, ảnh (scratchpad phiên QA): `r4_webhook.py/.out`, `r4_r6.py/.out`, `r4_fe1.py/.out`, `r4_fe_real.py/.out`, `r4_reset_be.sh`, `d1r4/{runA.sh,runB.sh,r4_check.py,expire.py,post_ttl.py,runA.log,runB.log}`, `r4shots/`.

Không sửa code sản phẩm, không thêm test vào repo.

---

# QA — ERP console mốc deploy 1 · lần 5 (hồi quy sau UI refresh UI1–UI5 + cổng UI) · 2026-09-25

## Kết luận: APPROVED. UI refresh không làm hỏng chức năng. Menu và trang theo quyền của 6 vai giống hệt lần 4. Giá vốn không lộ ở JSON, HTML ERP (gồm dải số liệu, "Cần chú ý", tab Hoạt động), Admin và Shop. Cổng UI đạt, trừ 1 lỗi Low: chữ trên nút chính khi rê chuột ở giao diện tối chỉ đạt 4.02:1 (B10). Thêm 1 lỗi Low: nhãn "Cần chú ý · 6 lô cận hạn" lệch với ô KPI khi có hơn 6 lô (B11). Hai lỗi đều không chặn.

## Tổng: 1.713 phép kiểm tự động (26 dòng bảng) · ✅ 1.711 · ❌ 2 (B10 Low, B11 Low) · ⏸ 0

Môi trường:
- DB là SQLite tạm trong scratchpad `qa5/`:
  - `seed.orig.sqlite3`: migrate → `bootstrap_masterdata` → `seed_demo` → 10 tài khoản (`loc` chu, `ql1`/`ql9` quan_ly, `ql9` có thêm quyền lẻ `manage_staff`, `kho1` nv_kho+nv_giao, `khoonly`, `giao1`, `giao2`, `moi1` không nhóm, `nghi1` đã nghỉ, `admin` superuser). Thêm lô dò rò `LO-QA5-COST`: giá mua 81234.56, giá vốn 91234.56. Gán phiếu giao DELIVERING cho `giao1` và `giao2`.
  - `e2e.orig.sqlite3`: seed 5 tài khoản đúng như `e2e/s41_s47_real.py` ghi.
  - DB được chép lại từ bản gốc trước mỗi kịch bản.
  - `backend/db.sqlite3` không bị đụng (mtime vẫn 13/09).
- Máy chủ:
  - Django `runserver` :8000.
  - Console build thật (`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`, build trong bản sao `qa5/realsrc`, 0 mock) phục vụ ở :3102.
  - Console build mock (`qa5/mocksrc`) ở :3101.
  - Shop `next dev` :3000 trỏ BE thật.
  - Mọi server chạy dưới `perl alarm`. Xong thì kill theo PID. `lsof` trên 8000/3000/3101/3102 sạch, `ps` = 0 tiến trình.
- `erp-console/out/` trong repo là bản build thật mặc định: `__caveMock|demo1234|127.0.0.1:8000` = 0 file.

## Theo AC (UI1–UI5 + AC chức năng phải giữ nguyên)

| Mã | Kết quả | Bằng chứng |
|---|---|---|
| UI1 token/không hex rời | ✅ | Tin dev-notes (grep = 0) · màu đo được ở mọi màn đều khớp token `tokens.css` |
| UI2 shell/login/set-password/no-role · 360 không cuộn ngang · AA light+dark | ✅ (trừ B10) | `ui_gate.py` 316 phép: 90 tổ hợp màn×cỡ×theme |
| UI3 Tổng quan/Đơn/Kho · trạng thái tải/rỗng/lỗi/403 | ✅ (B11 Low) | `ui_gate.py` có state-error (summary 500), state-empty, state403 (giao1 mở Kho), khung chờ (`ui_behave.py`) |
| UI4 Nhân sự, sheet, xác nhận, Tài khoản | ✅ | `ui_gate.py` staff-detail/confirm/create/account-chpw · `acct_flow.py` 17/17 |
| UI5 a11y: focus, ngăn kéo, phím tab, reduced-motion | ✅ | `ui_behave.py` 45/46 (FAIL duy nhất = B10) |
| S7, S8, S41, S42, S46, S47, S48 giữ nguyên | ✅ | e2e mock 184/184 · `s41_s47_real.py` 39/39 ×2 · `erp_matrix.py` 703/703 · `api_matrix.py` 315/315 |

## Phân quyền: menu ERP thật, 360 và 1280 (`erp_matrix.py` 703/703)

Menu đo từ DOM, so với luật `nav.ts` × `/me` và với số mục của lần 1–4. `nav.ts` không đổi từ 24/09 15:52, trước khi UI refresh bắt đầu.

| Vai | Menu (360 = 1280) | Số mục lần 4 | Trang đầu | Gõ URL ngoài quyền |
|---|---|---|---|---|
| chu `loc` | Tổng quan, Đơn & tiền, Giao hàng, Kho & lô, Mua hàng, Kiểm kê, Báo cáo lãi lỗ, Danh mục & giá, Nhân sự | 9 = 9 | /overview/ | — |
| quan_ly `ql1` | như Chủ, bỏ Báo cáo, Nhân sự | 7 = 7 | /overview/ | chặn, 0 API nghiệp vụ |
| quan_ly + manage_staff `ql9` | `ql1` + Nhân sự | 8 = 8 | /overview/ | chặn, 0 API nghiệp vụ |
| nv_kho+nv_giao `kho1` | như `ql1` + Việc giao của tôi | 8 = 8 | /overview/ | chặn, 0 API nghiệp vụ |
| nv_kho `khoonly` | như `ql1` | 7 = 7 | /overview/ | chặn, 0 API nghiệp vụ |
| nv_giao `giao1`, `giao2` | chỉ Việc giao của tôi | 1 = 1 | /my-deliveries/ | chặn, 0 API nghiệp vụ |
| không nhóm `moi1`, superuser `admin` | không menu | — | /no-role/ | gõ /overview/ vẫn về /no-role/ |
| đã nghỉ `nghi1` | không đăng nhập được | — | — | — |

Menu đáy ở 360 (4 mục + "Thêm" khi có hơn 5 mục) luôn là tập con của menu. Mọi trang /account/ mở được với mọi vai có nhóm. 0 trang cuộn ngang.

API thật (`api_matrix.py` 315/315), bảng mã trạng thái **giống lần 1–4**:
- summary: 200 cho chu/quan_ly/nv_kho/superuser; 403 cho nv_giao/không nhóm; 401 cho ẩn danh.
- `reports/period` và `reports/batch`: 200 chỉ cho `loc`/`admin`, còn lại 403.
- `/api/staff/`: 200 cho `loc`/`ql9`/`admin`, còn lại 403. `ql9` đụng Chủ → 403 BR-PQ-17.
- `loc` tự đổi nhóm → 400 BR-PQ-17. Cho `giao2` nghỉ khi đang giao → 400 BR-GH-08.
- PATCH giá vốn lô: 400 với Chủ/superuser (BR-PQ-14), 403 với các vai khác; lô không đổi.
- DELETE lô/đơn/phiếu giao: 403/405 với mọi vai (chứng từ còn nguyên).
- `giao1` chỉ thấy `DH-2609-118`.

Django Admin nhanh (`admin_matrix.py` 15/15): `ql1`/`kho1`/`khoonly`/`giao1` quét 13–41 trang, 0 số giá vốn, `/admin/auth/user/` 403. `moi1` không vào được. Đối chứng: `loc`/`admin` thấy giá vốn.

## Rò giá vốn

| Phạm vi | Vai | Kết quả |
|---|---|---|
| JSON 23 endpoint router (danh sách + chi tiết) + summary + reports + `/me` | ql1, ql9, kho1, khoonly, giao1, giao2, moi1 | ✅ 0 key `*cost*`/`*profit*`/`purchase_rate`/`inventory_value`, 0 giá trị 81234/91234. `capabilities` không có view_costprice/view_profitreport. Đối chứng: `loc`/`admin` có `landed_unit_cost` |
| HTML ERP 11 route/vai × 2 cỡ, gồm **dải số liệu KPI**, **Cần chú ý**, bảng lô | 7 vai thiếu quyền | ✅ 0 số giá vốn (81.235/91.235 và giá vốn demo 124.000…342.000), 0 cột "Vốn/kg". Ô "Giá trị tồn kho" chỉ hiện "— cần quyền xem giá vốn". Đối chứng: Chủ thấy 91.235 và "Giá trị tồn kho 42.850.642 ₫" |
| **Tab Hoạt động / Trợ lý / Ghi chú** ở cột phải (1280 cố định, 360 ngăn kéo) | 7 vai | ✅ 0 số/chữ giá vốn. Người không có Kho & lô → câu chặn |
| JSON console nhận qua trình duyệt khi duyệt các màn trên | 7 vai | ✅ 0 rò |
| Shop: catalog, chi tiết Tôm sú (có `LO-QA5-COST`), màn đặt xong | khách | ✅ (`shop_e2e.py` 6/6) |

## Luồng tài khoản trọn vẹn trên UI mới + BE thật (`acct_flow.py` 17/17)

1. Chủ (1280) tạo `giao7` → 201. Khối mật khẩu tạm hiện tên + MK. MK tạm không nằm trong storage.
2. `giao7` (360) đăng nhập bằng MK tạm:
   - chỉ vào được `/set-password/`, không có menu;
   - API nghiệp vụ trả 403 `AUTH_MUST_CHANGE_PASSWORD`.
3. Đặt MK mới → vào Việc giao, có `.pw-done-notice`. Token MK tạm → 401.
4. Máy B đăng nhập. Máy A tự đổi MK → máy B 401 và UI về /login/. Máy A dùng tiếp được.
5. Chủ cho nghỉ `giao7` → máy A 401, UI về /login/. Đăng nhập lại bị từ chối.
6. AuditLog ghi đủ `staff_create`, `password_change_self` ×2, `staff_deactivate`. Không chứa mật khẩu hay hash.

## Cổng UI

| Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|
| Không cuộn ngang: 23 màn/trạng thái × 360/1280 × light/dark (login, lỗi tại ô, 404, set-password, no-role, Việc giao, 403, Tổng quan, Đơn, Kho, Nhân sự, chi tiết, xác nhận, tạo, Tài khoản, tấm đổi MK, Mua hàng, 3 tab cột phải, ngăn kéo menu, lỗi, rỗng) | ✅ 90/90 | `ui_gate.py`, ảnh `qa5/shots/ui/qa5-*` |
| Vùng bấm ≥44 px ở 360 (mọi button/link/input/tab/checkbox-label hiện) | ✅ 45/45 tổ hợp | `ui_gate.py` |
| Tương phản chữ AA từ computed style (ghép nền rgba, tính opacity, placeholder, icon trạng thái ≥3:1) | ✅ 90/90 trạng thái tĩnh | Thấp nhất theo màu: **dark** warn 7.63 ("Cận hạn"), crit 6.73, ink-3 5.09, accent-text 6.74 · **light** warn 4.63, crit 5.65, ink-3 4.88 |
| Tương phản khi rê chuột (hover) | ❌ **B10** dark | light ✅; dark `.btn.primary:hover` 4.02:1 |
| Focus nhìn thấy khi Tab (login + 4 màn, 30 Tab/màn, 1280 light/dark + 360) | ✅ | Tab đầu = "Bỏ qua menu, tới nội dung"; mọi phần tử nhận focus có vòng 2 px `--focus` hoặc box-shadow |
| Ngăn kéo menu 360: focus vào, Tab/Shift+Tab giữ, Esc và "Đóng menu" trả focus về ☰ | ✅ | `ui_behave.py` |
| Cột phải ngăn kéo (360, 800): focus vào tab đang chọn, giữ Tab, Esc trả về nút mở | ✅ | |
| Tấm chi tiết NV, tạo NV, đổi MK (360 + 1280): focus vào, giữ Tab, đổi bước giữ focus trong tấm, Esc trả đúng nút mở | ✅ | |
| Phím tab cột phải: → ← Home End, vòng quanh, 1 tab trong thứ tự Tab, tablist có tên, panel `aria-labelledby` khớp | ✅ | |
| `prefers-reduced-motion` | ✅ | Đối chứng: không giảm thì có trượt tấm/ngăn kéo/scrim/khung chờ. Giảm thì 0 transition transform/opacity, 0 animation, chỉ còn icon tải quay 1,6 s (thiết kế, DESIGN.md) |

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ Ran 369 tests, OK (16,5 s) · `makemigrations --check` No changes detected |
| `adapter pytest -q` | ✅ 10 passed |
| `erp-console tsc --noEmit` · `npm run build` repo (thật mặc định) · build thật trỏ :8000 · build mock | ✅ exit 0 ×4 · `out/` repo 0 chuỗi mock |
| `frontend npm run build` | ✅ exit 0 |
| e2e mock: `s7_shell` 25/25 · `s8_views` 46/46 · `s41_s47_staff` 72/72 · `s48_password` 41/41 | ✅ 184/184 |
| e2e BE thật: `s41_s47_real.py` ×2 (DB reset) | ✅ 39/39 · 39/39 |
| `shop_e2e.py` | ✅ 6/6: bấm đúp → 1 POST, 1 đơn `SO260924-454E6F` BOOKED, FIFO phân bổ `LO-0918` |

## Lỗi

### B10 — Nút chính khi rê chuột ở giao diện tối chỉ đạt 4.02:1 · Low · UI2/UI5 (cổng AA)
- **Tái hiện:** 1280 px, máy ở chế độ tối (hoặc bấm nút đổi sang tối). Rê chuột lên "Đăng nhập", hoặc "Thêm nhân viên" ở Nhân sự (mọi `.btn.primary`).
- **Mong đợi:** chữ ≥4.5:1 ở mọi trạng thái (chữ 14 px).
- **Thực tế:** chữ trắng `#FFFFFF` trên `--accent-hover` dark `#3D7CE6` = **4.02:1**. Trạng thái thường đạt 4.75:1 (`#2F6FDB`). Light hover đạt 6.83:1.
- **Ảnh hưởng:** chỉ trên máy tính có chuột, giao diện tối, trong lúc rê chuột. Không ảnh hưởng điện thoại, vì hover chỉ bật khi `pointer:fine`. Không chặn.
- **Gợi ý:** giao diện tối cho hover *tối hơn* `--accent`, vd `#285FC4` (5.96:1) hoặc `#2A63C9` (5.64:1). Sửa ở `DESIGN.md` và `tokens.css` (`dark-accent-hover`).

### B11 — "Cần chú ý · N lô cận hạn" đếm theo danh sách đã cắt 6 dòng · Low · UI3
- **Tái hiện:** có 7 lô cận hạn (DB QA: 6 lô demo + `LO-QA5-COST`), mở Tổng quan.
- **Thực tế:** ô KPI ghi "Lô cận hạn **7**", ngay dưới lại ghi "Cần chú ý · **6 lô cận hạn**". `OverviewScreen.tsx:73` dùng `data.alerts.length`, mà BE cắt `alerts` ≤ 6 (contract R6).
- **Mong đợi:** hai con số không mâu thuẫn.
- **Ảnh hưởng:** chỉ xảy ra khi có hơn 6 lô cận hạn. Số đúng có ngay ở ô KPI. Không sai dữ liệu hay tồn kho. Không chặn.
- **Gợi ý:** dùng `kpis.near_expiry` cho nhãn, hoặc ghi "6 lô gần hạn nhất". Kèm link "Xem tất cả" sang Kho & lô.
- Ảnh: `qa5/shots/qa5-home-ql1-1280.png`.

### Ghi nhận (không phải lỗi)
- Console trình duyệt có "Failed to fetch RSC payload … Falling back to browser navigation". Lỗi này chỉ xuất hiện khi kịch bản `goto` cắt ngang prefetch. Tệp `index.txt` phục vụ bình thường (200). E2E trong repo cũng lọc lỗi này.
- Còn từ trước: B1 (`legacy/` chưa xoá, runbook bước 7), B7 (adapter, chặn deploy adapter), B8, B9.

## Ghi nhận: độ nhất quán giữa các màn (không chấm)
- **Đồng đều tốt:**
  - Tổng quan, Đơn, Kho, Nhân sự cùng dùng một kiểu đầu mục (`sect-h` + phụ đề xám), hàng phẳng kẻ mảnh, trạng thái chấm + chữ.
  - Rỗng / lỗi / 403 / "sắp có" cùng một khung icon 40 px + tiêu đề + một câu.
  - Tấm bên, xác nhận nguy hiểm, đổi mật khẩu cùng một ngữ pháp nút.
  - Dark ngang hàng light, màu hổ phách/đỏ chỉ xuất hiện khi có nghĩa.
- **Còn lệch nhẹ:**
  - Nhãn nhóm của Nhân sự là viên có viền, trong khi các màn khác chỉ dùng chấm.
  - Các màn "sắp có" (Việc giao, Mua hàng…) còn trống nhiều. Với NV giao, màn đầu tiên họ thấy là một khung "sắp có".
  - Dòng "Chưa có nhóm" của `admin` và `moi1` trong danh sách Nhân sự dùng chữ xám thường, dễ lẫn với ô trống.

## Lệnh đã chạy (kèm output tóm tắt)
```
backend manage.py test                                   → Ran 369 tests in 16.480s OK
makemigrations --check --dry-run                         → No changes detected
adapter pytest -q                                        → 10 passed
builds.sh: realsrc (API :8000) / mocksrc (MOCK=1) / tsc / repo build / frontend build → exit 0 ×5
DATABASE_URL=sqlite:///qa5/seed.sqlite3 migrate · bootstrap_masterdata · seed_demo · shell<seed_users.py · update_batch_status · shell<seed_dn.py
api_matrix.py (BE :8000)                                 → 315/315 (lượt đầu 310/315: 5 FAIL do script, đã sửa: probe khớp nhầm SĐT, thiếu year/month, tra lô theo id)
erp_matrix.py (console thật :3102, 9 vai × 2 cỡ)         → 703/703 (lượt đầu 689/703: regex chữ bắt "Giá trị tồn kho — cần quyền…", lọc RSC prefetch)
admin_matrix.py                                          → 15/15 (lượt đầu 0 trang vì seed chưa is_staff, đã bật)
acct_flow.py                                             → 17/17 · AuditLog 4 dòng, 0 bí mật
shop_e2e.py (Shop :3000 → BE)                            → 6/6
e2e/s41_s47_real.py ×2 (SEED=e2e, DB reset)              → 39/39 · 39/39 (lượt trên DB 10 tài khoản dừng ở BR-GH-08 vì giao1 có phiếu DELIVERING — dữ liệu, không phải lỗi)
e2e mock s7_shell/s8_views/s41_s47_staff/s48_password    → 25/25 · 46/46 · 72/72 · 41/41
ui_gate.py (23 màn × 360/1280 × light/dark)              → 315/316 (FAIL = B10, bắt được vì chuột còn trên nút)
ui_behave.py (hover, focus, ngăn kéo, tấm, phím tab, reduced-motion) → 45/46 (FAIL = B10)
kill PID · lsof 8000/3000/3101/3102 · ps                 → sạch
```
Script, log, ảnh: scratchpad `qa5/` (`api_matrix.py`, `erp_matrix.py`, `admin_matrix.py`, `acct_flow.py`, `shop_e2e.py`, `ui_gate.py`, `ui_behave.py`, `ui_gate.detail.json`, `*.out`, `shots/`). Không sửa code sản phẩm, không sửa `erp-console/e2e/*`, không thêm test vào repo.

---

# QA lô L7 — S10 (danh sách & chi tiết đơn) + S11 (Chủ xác nhận đã nhận tiền) · lần 1 · 2026-09-25

## Kết luận: REJECTED — mọi AC S10/S11 đạt trên backend thật, không rò giá vốn, không vượt quyền, hồi quy xanh. Nhưng đường tiền còn 2 lỗi chặn: (B12 High) Chủ xác nhận tay bằng mã trên sao kê (FT…), sau đó webhook SePay về, thì cùng một khoản tiền bị ghi thành 2 giao dịch; (B13 Medium) số tiền quá lớn trả 500, số tiền dưới 0,005 bị ghi thành giao dịch 0 ₫.

## Tổng: 392 phép kiểm tự động trên BE + console thật (API 241 + UI 151) · ✅ 386 · ❌ 5 (B12 ×2, B13 ×3) · ⏸ 1 (đồng thời thật, cần Postgres) · hồi quy 424 test BE + 10 adapter + 5 bản build + e2e 342/342

Môi trường:
- DB là SQLite tạm trong scratchpad `qa7/`. `seed.orig.sqlite3` dựng qua migrate → `bootstrap_masterdata` → `seed_demo` → 10 tài khoản (như lần 5) → `seed_orders.py`.
  - `seed_orders.py` gán phiếu giao đơn 118 cho `giao1`, 117 cho `giao2`, rồi tạo thêm 46 đơn: 30 BOOKED (2 đơn đã chuyển thiếu), 10 PROCESSING, 9 AUTO_CANCELLED, 1 CANCELLED (do Lộc huỷ, lý do "Khách đổi ý"), 1 PAID, 1 COMPLETED. Đơn trải trên 10 ngày.
  - Có khách "Chị Hoa" 0901234567 và "Anh Đạt Nguyễn".
  - Có hai đơn dò giá vốn: A (BOOKED) giữ chỗ trên 2 lô, gồm lô `LO-QA5-COST` giá vốn 91234.56; B (PROCESSING) đã bán từ `LO-QA5-COST`.
- DB được chép lại từ bản gốc trước mỗi kịch bản. `backend/db.sqlite3` không bị đụng (mtime vẫn 13/09).
- Máy chủ:
  - Django `runserver` :8000.
  - **Adapter FastAPI thật** (uvicorn) :8100, `DJANGO_INTERNAL_URL=:8000`.
  - Console build thật (`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`, 0 mock) :3102.
  - Console build mock :3101.
  - Shop `next dev` :3000 trỏ BE thật.
  - Mọi server chạy dưới `perl alarm`. Xong thì kill theo PID. `lsof` trên 8000/8100/3000/3101/3102 sạch, `ps` = 0.

## Theo AC

| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| S10-AC1 lọc `status=BOOKED` + ngày, 20 dòng/trang | ✅ | `api_l7.py`: chỉ BOOKED, chỉ ngày hôm nay theo giờ VN, count khớp DB. Trang 1 = 20 dòng, trang 2 không trùng. `page=99`/`abc` → 404. Duyệt hết trang = tổng DB, sắp mới → cũ. UI: lọc "Giữ chỗ" + "Hôm nay" khớp DB. "Tải thêm đơn" tới hết: 58/58 dòng, không trùng, hết nút |
| S10-AC2 `q=0901234` | ✅ | API + UI ra đúng Chị Hoa. Thêm: đuôi mã đơn viết thường; tên không dấu `chi hoa`, `CHỊ HOA`, `dat nguyen`, `ĐẠT`, `Dat`, `thuy`, `quan oc` đều đúng người; `%`, `_` không 500 |
| S10-AC3 Quản lý / NV kho không có key `unit_cost` | ✅ | `ql1`, `ql9`, `kho1`, `khoonly`: đơn A (giữ chỗ 2 lô) và đơn B (đã bán) có `batch_id`/`qty_kg`/`line_no`, **không có key** `unit_cost`. UI: 0 `.alloc-cost` |
| S10-AC4 Chủ có `unit_cost` | ✅ | `loc`: `LO-QA5-COST` `unit_cost="91234.56"` ở cả A (từ giữ chỗ) và B (từ phân bổ đã bán). Superuser cũng thấy. UI hiện "Vốn …/kg" |
| S10-AC5 đếm lùi mm:ss | ✅ | BE trả `reserved_until`. UI hiện `mm:ss` và số đổi sau ≤5 s (`ui_l7.py`) |
| S10-AC6 thiếu `view_salesorder` → 403, không menu | ✅ | `moi1`: list 403, chi tiết 403, UI về /no-role/, gõ /orders/ 0 GET đơn. Ẩn danh: API 401, UI về /login/. `giao1`/`giao2` không có menu, gõ /orders/ thấy "Bạn không có quyền xem mục này", 0 GET `sales/orders` |
| S10-AC7 360: mỗi đơn một khối, chi tiết một cột, không cuộn ngang | ✅ | 360/1280 × sáng/tối: 0 cuộn ngang ở danh sách, chi tiết, bước xác nhận. Vùng bấm ≥44 px ở cả ba màn (360). Danh sách là hàng 2 dòng thay cho thẻ, theo lệch 7 dev đã ghi (DESIGN.md), vẫn đạt ý AC |
| S11-AC1 đủ tiền → PAID | ✅ | Kết quả `PAID`, `duplicate:false`, PROCESSING, `invoice_id`, `delivery_note_code` GH-… DB: 1 giao dịch `MANUAL`/`MATCHED`, 1 hoá đơn, phiếu giao PREPARING. Kho: mỗi lô đã giữ trừ `reserved −q`, `available −q`, thêm 1 dòng SALE tham chiếu mã hoá đơn. AuditLog `confirm_payment_manual`: actor = `loc`, `changes` có mã GD, `source=MANUAL`, `status BOOKED→PROCESSING`. UI: như trên + toast khi đóng tấm |
| S11-AC2 thiếu tiền → UNDERPAID | ✅ | `paid_total`/`missing` đúng. Đơn vẫn BOOKED, kho không đổi, 0 hoá đơn. Giao dịch UNDERPAID/MANUAL, có AuditLog. List `needs_attention=true`, vẫn còn nút. Chuyển bù đủ bằng mã khác thì vẫn UNDERPAID, `missing 0`, đúng giả định dev 3 (chờ S12). UI: "Đã ghi nhận 51.000 ₫, còn thiếu 66.500 ₫" (`qa7-s11-underpaid-1280.png`) |
| S11-AC3 đơn tự huỷ → ORPHAN | ✅ | Đơn tự huỷ bằng job `cancel_expired_orders` thật, sau đó xác nhận tay: kết quả `ORPHAN`, đơn vẫn AUTO_CANCELLED, kho và sổ kho không đổi, 0 hoá đơn, giao dịch ORPHAN/MANUAL. Timeline: `auto_cancelled` = Hệ thống, `payment_received` = Lộc. UI nêu "không khôi phục" (`qa7-s11-orphan-1280.png`) |
| S11-AC4 gửi lại y hệt / bấm đúp | ✅ | API gửi lại (có và không có `/`, kể cả khác số tiền) → `duplicate:true`, vẫn 1 giao dịch, 1 hoá đơn, 1 AuditLog, kho không đổi. **UI bấm đúp → đúng 1 POST** |
| S11-AC5 webhook đã ghi rồi Chủ xác nhận tay cùng mã | ✅ theo chữ AC / ❌ trên đường thật (B12) | Gửi webhook qua **adapter thật** (`Authorization: Apikey`, `id=880001`) → MATCHED, PROCESSING. Xác nhận tay `880001` → `duplicate:true`, 0 AuditLog tay, timeline 1 dòng tiền = Hệ thống. Webhook gửi lại → không ghi thêm. Webhook UNDERPAID rồi xác nhận tay cùng mã → duplicate UNDERPAID. **Nhưng** adapter ghi `bank_txn_id` = `id` của SePay, còn màn hướng dẫn Chủ chép mã FT… trên sao kê → xem B12 |
| S11-AC6 thiếu mã / số tiền ≤0 → 400 | ✅ (biên ❌ B13) | 400 `BR-TT-08` với: thiếu hoặc rỗng mã, mã toàn khoảng trắng, mã `null`, mã 101 ký tự; số tiền `0`, `0.00`, `-5`, `-540000`, `abc`, `NaN`, `±Infinity`, `1e`, `true`, `[]`, `{}`. Số tiền bỏ trống = tổng đơn → PAID. Số tiền kiểu số → PAID. UI: mã trống báo tại ô, 0 POST; số tiền 0 hiện câu BE. Biên số rất lớn / rất nhỏ: xem B13 |
| S11-AC7 Quản lý → 403, không nút | ✅ | 403 với `ql1`, `ql9`, `kho1`, `khoonly`, `giao1` (cả đơn của phiếu mình), `giao2`, `moi1`. `ql1` gọi đơn không tồn tại → 403, tức quyền được kiểm trước khi tra đơn. Ẩn danh 401. Không ghi gì. `available_actions` của 4 vai không có `confirm_payment`, UI Quản lý không có nút |
| S11-AC8 action cũ đã gỡ | ✅ | `POST /api/sales/invoices/{id}/confirm-payment[/]` → 404/405, không ghi |
| BR-TT-03 mã đã dùng cho đơn khác | ✅ | 400 `BR-TT-03`, không trả `result`/`invoice_id` của đơn kia, đơn không đổi. Mã UNMATCHED (webhook không có mã đơn) → 400 `BR-TT-03`, giao dịch không bị gắn. UI hiện nguyên văn câu BE và ở lại form |
| BR-TT-08 trạng thái đơn | ✅ | PROCESSING, CANCELLED, COMPLETED, PAID → 400 "Đơn không ở trạng thái Giữ chỗ/Tự huỷ", không ghi. Đơn không tồn tại → 404 |

## Ngoại lệ & biên

| Ca | Kết quả |
|---|---|
| 4 POST đồng thời cùng mã, cùng đơn | ⏸ Dữ liệu đúng: 1 giao dịch, 1 hoá đơn, 1 AuditLog. Nhưng 3/4 lần gọi trả 500 `database is locked`: SQLite không có `select_for_update`. Không có Postgres trên máy nên không kiểm được tuần tự hoá thật (dev đã ghi ở "Còn nợ"). Không tính là lỗi sản phẩm |
| Xác nhận tay bằng mã FT…, webhook cùng khoản về sau | ❌ **B12** (2 giao dịch MATCHED) |
| Đơn tự huỷ: xác nhận tay ORPHAN, webhook cùng khoản về sau | ❌ **B12** (2 dòng ORPHAN trong hàng chờ) |
| Xác nhận tay bằng mã FT… sau khi webhook đã khớp | ✅ 400 (đơn đã PROCESSING), không ghi |
| Số tiền `1e20` hoặc 15 chữ số (API, UI, webhook) | ❌ **B13** (500 / UI "Lỗi máy chủ (500)" / adapter 502) |
| Số tiền `0.001`, `0.004` (API, webhook) | ❌ **B13** (ghi giao dịch 0 ₫ UNDERPAID) |
| 12 chữ số (999.999.999.999), chuyển dư | ✅ PAID (theo luật cũ BR-TT-04) |
| Lọc: `status` lạ → 0 dòng · ngày sai → 400 `INVALID_FILTER` · khoảng ngày ngược → 0 dòng · 1 ngày trong quá khứ đúng số | ✅ |
| `q` kết hợp `status` (AND) | ✅ |

## Phân quyền (API + UI thật, 360 và 1280)

| Vai | Menu "Đơn & tiền" | List | Chi tiết | `unit_cost` | Nút xác nhận / `available_actions` (BOOKED · AUTO_CANCELLED · PROCESSING · CANCELLED · COMPLETED) | POST confirm |
|---|---|---|---|---|---|---|
| chu `loc` | có | 200, 58 đơn | 200 | có | có · `[confirm_payment]` · `[confirm_payment]` · `[cancel, create_refund]` · `[create_refund]` · `[create_refund]` | 200 |
| quan_ly `ql1`, `ql9` | có | 200, tất cả | 200 | không key | không · `[]` · `[]` · `[cancel, create_refund]` · `[create_refund]` · `[create_refund]` | 403 |
| nv_kho+nv_giao `kho1` / nv_kho `khoonly` | có | 200, tất cả | 200 | không key | không · `[]` ×5 | 403 |
| nv_giao `giao1` / `giao2` | không; gõ URL bị chặn, 0 GET | 200, chỉ đơn của phiếu mình (118 / 117) | 200 đơn mình, 404 đơn khác và đơn chưa giao | không key | `[]` | 403 (kể cả đơn mình) |
| không nhóm `moi1` | /no-role/ | 403 | 403 | — | — | 403 |
| superuser `admin` | /no-role/ (như lần 5) | 200 | 200 | có | như Chủ | 200 |
| chưa đăng nhập | về /login/ | 401 | 401 | — | — | 401 |

NV giao tìm theo tên hoặc SĐT của đơn ngoài phạm vi → 0 dòng.

## Rò giá vốn

| Phạm vi | Vai | Kết quả |
|---|---|---|
| JSON: mọi trang list + chi tiết **mọi** đơn thấy được (gồm `timeline`, `payments`, `delivery`, `refunds`), quét đệ quy key `*cost*`/`*profit*`/`purchase_rate`… và giá trị 81234/91234 | ql1, ql9, kho1, khoonly (58 đơn) · giao1, giao2 (1 đơn) | ✅ 0 hit. `allocations[].unit_cost` không có mặt ở giá trị giá vốn demo nào. Đối chứng: Chủ quét ra `unit_cost` và 91234.56 |
| JSON console nhận qua trình duyệt khi duyệt list + 2 chi tiết | 4 vai × 2 cỡ | ✅ 0 hit |
| HTML ERP chi tiết A và B (1280 + 360) | 4 vai | ✅ 0 `.alloc-cost`, 0 "91.235"/"91234", 0 "Vốn …". Đối chứng: Chủ thấy |
| Timeline | 3 vai | ✅ Chỉ có mã chứng từ, tiền khách trả, tên người, lý do. Không có `changes` thô, `password` hay `"from"` |
| Shop | khách | ✅ `shop_e2e.py` 6/6 |

## Chứng từ & AuditLog

- `DELETE` / `PATCH` đơn, giao dịch, hoá đơn với `loc` và `admin` → 403/405. Chứng từ còn nguyên.
- Xác nhận tay ghi đúng 1 AuditLog `confirm_payment_manual` (actor = người bấm) cho PAID, UNDERPAID, ORPHAN. Lần gọi trùng không ghi thêm. Nhánh webhook không ghi (như thiết kế).
- Timeline ghi đúng người:
  - xác nhận tay = "Lộc";
  - webhook, đặt đơn, hoá đơn, phiếu giao, tự huỷ = "Hệ thống";
  - huỷ đơn = "Lộc — lý do: Khách đổi ý".
  - Ba vai xem cùng một timeline.

## Giao diện (console thật)

| Tiêu chí | Kết quả |
|---|---|
| Không cuộn ngang: danh sách / chi tiết / bước xác nhận × 360/1280 × sáng/tối | ✅ 12/12 |
| Vùng bấm ≥44 px (360) ở danh sách, chi tiết, bước xác nhận × sáng/tối | ✅ 6/6 |
| Focus: mở tấm → focus trong tấm. 25 Tab ở chi tiết và 12–15 Tab ở bước xác nhận không thoát tấm. Esc → focus về đúng dòng đã mở. Huỷ bước → focus về nút "Xác nhận đã nhận tiền". Mở bước → focus vào ô mã GD | ✅ (1280 sáng/tối, 360 sáng/tối) |
| Console trình duyệt không lỗi đỏ (trừ 400/401/403 cố ý) | ✅ |
| Ảnh | `qa7/shots/qa7-{list,detail,confirm}-{360,1280}-{light,dark}.png`, `qa7-s11-{paid,underpaid,orphan,brtt03,bigamount}-1280.png`, `qa7-perm-<vai>-<cỡ>.png` |

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ Ran 424 tests, OK (17,7 s) · `makemigrations --check` No changes detected |
| `adapter pytest -q` | ✅ 10 passed |
| erp-console: `tsc --noEmit` · `npm run build` repo · build thật trỏ :8000 · build mock | ✅ exit 0 ×4. `out/` repo: 0 file chứa `__caveMock/demo1234/Chế độ mock/mockOrdersApi/cave_erp_mock_orders`. Build thật: 0 dấu mock |
| `frontend npm run build` | ✅ exit 0 |
| e2e mock: `s7_shell` · `s8_views` · `s10_s11_orders` · `s41_s47_staff` · `s48_password` | ✅ 25/25 · 45/45 · 75/75 · 72/72 · 41/41 |
| e2e BE thật `s41_s47_real.py` ×2 (DB reset) | ✅ 39/39 · 39/39 |
| `shop_e2e.py` (Shop :3000 → BE thật) | ✅ 6/6: bấm đúp đặt hàng → 1 POST, HTML không giá vốn |
| Webhook cũ (không mã đơn → UNMATCHED; gửi lại → không ghi thêm) | ✅ qua adapter thật |

## Lỗi

### B12 — Xác nhận tay rồi webhook SePay về sau: cùng một khoản tiền bị ghi 2 giao dịch · High · S11-AC4/AC5, BR-TT-03
- **Tái hiện** (BE :8000 + adapter thật :8100):
  1. Shop tạo đơn `SO…` 117.500 ₫ (BOOKED).
  2. Chủ bấm "Xác nhận đã nhận tiền". Theo chữ hướng dẫn trên màn ("Chép từ tin nhắn hoặc sao kê ngân hàng, vd FT2626712345"), Chủ nhập `FT880003`, 117.500 → `PAID`.
  3. SePay gửi webhook muộn cho đúng khoản đó: `POST :8100/webhook/sepay` với `{"id": 880003, "referenceCode": "FT880003", "code": "SO…", "transferAmount": 117500, …}`.
- **Mong đợi:** BR-TT-03 nhận ra là cùng một giao dịch ngân hàng. Không ghi thêm, hoặc ít nhất đưa vào hàng chờ cho Chủ.
- **Thực tế:** adapter gửi `bank_txn_id = str(payload.id)` = `"880003"`, không phải `referenceCode`. Django không thấy trùng, ghi thêm giao dịch thứ hai `('880003', WEBHOOK, MATCHED, 117500)` cạnh `('FT880003', MANUAL, MATCHED, 117500)`.
  - Đơn đã tự huỷ: tay → ORPHAN rồi webhook → **2 dòng ORPHAN** cho cùng một khoản (`FT880004` + `880004`).
  - Hoá đơn và kho **không** bị nhân đôi.
- **Ảnh hưởng:**
  - Sổ giao dịch tiền vào ghi gấp đôi số tiền khách đã trả. `paid_total` và hàng chờ S12 sẽ sai.
  - Với ORPHAN, S12/S13 sẽ cho lập phiếu hoàn cho cả hai dòng, tức hoàn tiền hai lần (tiền rời túi).
  - Đây đúng là tình huống chính của S11 (E-05: webhook không về kịp). S11-AC5 chỉ đạt khi Chủ gõ đúng `id` nội bộ của SePay, mà Chủ không nhìn thấy mã này trên sao kê. Báo cáo lãi lỗ không bị ảnh hưởng (tính theo hoá đơn).
  - Liên quan N-6 (đơn đã PROCESSING nhận tiền lần hai vẫn ghi MATCHED), nhưng nguyên nhân gốc mới: **mã GD của webhook và của Chủ khác hệ**.
- **Gợi ý** (cần Duy/BA chốt): adapter dùng `referenceCode` (mã ngân hàng FT…) làm `bank_txn_id`, lùi về `id` khi trống, giữ `id` trong `raw`. Contract S10/S11 cũng lấy ví dụ `bank_txn_id` = `FT…` cho cả giao dịch WEBHOOK. Kèm theo, chốt N-6: tiền về cho đơn không còn BOOKED thì vào hàng chờ, không ghi MATCHED.

### B13 — Số tiền ngoài miền của cột `amount` (14 chữ số, 2 lẻ): quá lớn → 500, quá nhỏ → giao dịch 0 ₫ · Medium · S11-AC6, BR-TT-08
- **Tái hiện:**
  - (a) `POST /api/sales/orders/{id}/confirm-payment {"bank_txn_id":"X1","amount":"123456789012345"}` (hoặc `"1e20"`, `"99999999999999"`) → **500** `decimal.InvalidOperation`. Trên UI: gõ 15 chữ số vào ô "Số tiền đã nhận" (ô chỉ lọc chữ số, không giới hạn độ dài) → thanh nút báo "Lỗi máy chủ (500). Thử lại sau." (`qa7-s11-bigamount-1280.png`).
  - (a) Qua webhook: adapter `transferAmount: 100000000000000` → Django 500, adapter thử lại 3 lần rồi trả **502**, nên SePay sẽ gửi lại mãi.
  - (b) `{"bank_txn_id":"X2","amount":"0.001"}` (hoặc `0.004`) → 200 `UNDERPAID`. DB có giao dịch **amount = 0**, MANUAL, UNDERPAID, nằm trong hàng chờ. Webhook `transferAmount: 0.001` qua adapter cho kết quả tương tự.
- **Mong đợi:** 400 `BR-TT-08` ("Số tiền phải là số lớn hơn 0" / "quá lớn"). Không bao giờ ghi giao dịch 0 ₫.
- **Thực tế:** như trên. Không có dữ liệu rác ở (a), vì transaction rollback.
- **Ảnh hưởng:**
  - (a) Chủ gõ nhầm thì gặp lỗi 500 khó hiểu. Webhook lỗi thì bị gửi lại liên tục.
  - (b) Có một khoản 0 ₫ "thiếu tiền" treo trong hàng chờ, trái BR-TT-08 (> 0).
  - Không mất tiền, không sai kho.
- **Gợi ý:** `parse_positive_amount` (dùng chung cho tay và webhook) nên quantize về 0,01, sau đó từ chối số ≤ 0 và số vượt `max_digits`. FE nên thêm `maxLength` (vd 12 chữ số).

### Ghi nhận (không chặn)
- S10-AC7 ghi "mỗi đơn là một thẻ"; điện thoại hiện hàng 2 dòng (lệch 7 của FE, theo DESIGN.md). Ý AC đạt: mỗi đơn là một khối bấm được, ≥44 px, không cuộn ngang. PO nên chốt lại câu chữ AC.
- Giả định dev còn chờ PO/BA: nút xác nhận hiện cả ở đơn Tự huỷ (1); mã UNMATCHED → 400 thay vì gắn đơn (2); khớp tiền theo **từng** giao dịch nên hai lần chuyển thiếu cộng đủ vẫn UNDERPAID (3). QA đã kiểm và thấy hành vi đúng như các giả định mô tả.
- Chưa kiểm: đồng thời thật trên Postgres; máy điện thoại thật (bàn phím số, `select` iOS).
- Còn từ trước: B1, B7 (adapter), B8, B9.

## Lệnh đã chạy (kèm output tóm tắt)
```
backend manage.py test                                    → Ran 424 tests in 17.745s OK
makemigrations --check --dry-run                          → No changes detected
adapter pytest -q                                         → 10 passed
builds.sh: realsrc(:8000) / mocksrc / tsc / repo build / frontend build → exit 0 ×5 · grep mock trong out/ repo = 0, realsrc = 0
DATABASE_URL=sqlite:///qa7/seed.orig.sqlite3 migrate · bootstrap_masterdata · seed_demo · shell<qa5/seed_users.py · shell<seed_orders.py
  → 52 đơn: BOOKED 30 · PROCESSING 10 · AUTO_CANCELLED 9 · CANCELLED 1 · PAID 1 · COMPLETED 1 (+ đơn tạo trong kịch bản)
be.sh (reset DB + runserver :8000) · ad.sh (uvicorn adapter :8100) · http.server 3102 (thật) / 3101 (mock)
api_l7.py                                                 → 241 · PASS 236 · FAIL 5 (1 ⏸ SQLite lock, B12 ×2, B13 ×2)
  (lượt đầu 234/241: thêm 2 lỗi kịch bản — kỳ vọng phiếu 118 DELIVERING trong khi seed là PREPARING; so "117500" với "117500.00" — đã sửa, chạy lại trên DB sạch)
api_extra.py (webhook biên qua adapter)                   → 1e14 → 502 (Django 500) · 0.001 → giao dịch 0 ₫ UNDERPAID
ui_l7.py (console thật, 9 vai × 2 cỡ + luồng Chủ + 4 tổ hợp cỡ/theme) → 151 · PASS 150 · FAIL 1 (B13)
  (lượt đầu dừng ở hàm tìm với q rỗng; lượt 2 có 8 FAIL giả do tên khách dò "Cô Dò Vốn A" chứa chữ "Vốn" — đã siết regex, chạy lại trên DB sạch)
tl_check.py                                               → timeline đơn huỷ: cancelled = Lộc + lý do, giống nhau với loc/ql1/khoonly
e2e mock s7/s8/s10_s11/s41_s47_staff/s48 (:3101)           → 25/25 · 45/45 · 75/75 · 72/72 · 41/41
e2e/s41_s47_real.py ×2 (SEED=e2e, DB reset, :3102)        → 39/39 · 39/39
qa5/shop_e2e.py (Shop next dev :3000 → BE)                → 6/6
kill PID + pkill theo lệnh · lsof 8000/8100/3000/3101/3102 → sạch · ps = 0 · backend/db.sqlite3 mtime 13/09 (không đụng)
```
Script, log, ảnh ở scratchpad `qa7/`: `seed_orders.py`, `api_l7.py`, `api_extra.py`, `ui_l7.py`, `tl_check.py`, `be.sh`, `ad.sh`, `builds.sh`, `*.out`, `shots/`. Không sửa code sản phẩm, không sửa `erp-console/e2e/*`, không thêm test vào repo.

---

# QA lô L7 — lần 2 (vòng sửa 1/2) · xác nhận sửa B12 + B13 · 2026-09-25

## Kết luận: APPROVED — đã sửa B12 (High) và B13 (Medium) trên backend thật, adapter thật (uvicorn) và console build thật. Cùng một khoản tiền không còn bị ghi 2 lần. Số tiền ngoài miền bị chặn ở UI (tại ô, 0 POST), API tay (400 `BR-TT-08`), webhook nội bộ và adapter (400, không 502, không ghi giao dịch). Hồi quy xanh, không rò giá vốn. Còn **B7** (có từ trước, ngoài B12/B13): adapter trả 500 khi `transferAmount` ≤ 0. B7 vẫn chặn việc deploy adapter như đã ghi ở lần trước, không chặn lô L7.

## Tổng: 527 phép kiểm tự động (API 344 + UI 170 + token sai 13) · ✅ 521 · ❌ 4 (B7, có từ trước) · ⏸ 1 (4 POST đồng thời, cần Postgres) · 1 phép kiểm do script đếm sai, đã đối chiếu log và tính là ✅ · hồi quy 436 test BE + 15 adapter + 5 bản build + e2e 90/90 · 45/45 · 39/39 · 6/6

Môi trường giống lần 1:
- DB: `seed.orig.sqlite3` (hoặc `e2e.orig.sqlite3` cho `s41_s47_real`), chép lại trước mỗi kịch bản.
- Máy chủ: Django `runserver` :8000, adapter FastAPI thật :8100 (`DJANGO_INTERNAL_URL=:8000`), thêm một adapter :8101 dùng token nội bộ sai.
- Console: build thật lại từ mã hiện tại (`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`, 0 mock) :3102, build mock :3101. Shop `next dev` :3000.
- Mọi server chạy dưới `perl alarm`, kill theo PID. `lsof` trên 8000/8100/8101/3000/3101/3102 sạch, `ps` = 0. `backend/db.sqlite3` không bị đụng (mtime 13/09).

Script lần 1 được sinh lại thành `api_l7b.py` / `ui_l7b.py` (qua `r2/mk.py`, `r2/mkui.py`). Có 3 loại thay đổi:
- Thêm mục B12/B13 (`r2/b12b13.py`).
- Sửa kỳ vọng cũ gắn với hành vi lỗi: webhook giờ lưu `FT…` thay cho `id` SePay. Ca "tay bằng FT… sau webhook → 400" đổi thành "→ duplicate".
- Siết ca biên: trước chỉ yêu cầu "không 500", giờ yêu cầu "400 BR-TT-08".

## B12 — cùng một khoản tiền, mã FT… ở cả hai đường (BR-TT-03 · S11-AC4/AC5)

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| Webhook qua adapter (`id=880001`, `referenceCode=FT880001`) → `bank_txn_id` lưu = `FT880001`, không có dòng `880001`. `id` SePay vẫn nằm trong `raw_payload` | ✅ | `api_l7b.py` S11-AC5 |
| Webhook trước → xác nhận tay cùng mã viết khác: `" ft880001 "`, `"Ft 8800 01"`, `" ft990101 "`, `"fT 9901 11"`, `"\tFT990121\n"` → `duplicate:true` PAID. 1 giao dịch WEBHOOK, 1 hoá đơn, 0 AuditLog tay, timeline 1 dòng tiền = Hệ thống | ✅ | B12-a[0..2], S11-AC5 |
| Webhook UNDERPAID → tay `ft880002` → duplicate UNDERPAID, không ghi | ✅ | |
| Tay trước `" ft 990201 "` → lưu `FT990201`, AuditLog ghi mã dạng chuẩn. Webhook cùng khoản về sau (kể cả gửi lại với `referenceCode=" ft990201 "`) → 200, **vẫn 1 giao dịch, 1 hoá đơn**. Chi tiết đơn có 1 dòng tiền, timeline 1 `payment_received` = Lộc | ✅ | B12-b · ca lần 1 `FT880003` giờ ✅ |
| Đơn tự huỷ: tay ORPHAN → webhook → **chỉ 1 ORPHAN** (`FT880004`, `FT990301`). Chiều ngược lại: webhook ORPHAN → tay `ft 990311` → duplicate ORPHAN, 1 dòng, 0 AuditLog | ✅ | B12-c, B12-c2 · ca lần 1 `FT880004` giờ ✅ |
| `referenceCode` = `""`, `"   "`, `null`, hoặc không có key → lùi về `id` (`990401`/`990403`/`990410`/`990402`). Tay bằng `id` → duplicate | ✅ | B12-d |
| UI thật: Chủ gõ `"  ft 770008 "` → PAID, lưu `FT770008`. Webhook 770008 qua adapter → 200, vẫn 1 giao dịch. Mở lại chi tiết: 1 dòng tiền, 1 `payment_received` | ✅ | `ui_l7b.py`, `qa7r2-b12-detail-1280.png` |
| Tay bằng `id` SePay `880001` sau khi webhook đã lưu `FT880001` → 400 (đơn đã PROCESSING), không ghi | ✅ | Đổi hành vi có chủ ý: Chủ không nhìn thấy `id` SePay |
| BR-TT-03: mã của đơn khác / mã UNMATCHED (`ft880005`, viết thường) → 400 `BR-TT-03`, không gắn | ✅ | |

## B13 — số tiền ngoài miền (BR-TT-08 · S11-AC6)

| Đường | Giá trị | Kết quả |
|---|---|---|
| **UI** console thật 1280 | `123456789012345`, `99999999999999`, `1000000000000` → "Số tiền quá lớn: tối đa 12 chữ số…" · `1e20` → "Chỉ nhập chữ số…" · `0,001`, `0.001`, `0` → "…từ 1 ₫ trở lên…" · `-5`, `-540000` → "…không được âm…" | ✅ 9/9: lỗi tại ô, `aria-invalid=true`, focus về ô, **0 POST**, không có "Lỗi máy chủ", DB không ghi. Sửa ô thì lỗi mất (`qa7r2-b13-toobig-1280.png`) |
| UI 360/1280 × sáng/tối | 15 chữ số | ✅ 4/4: lỗi tại ô, 0 POST, không cuộn ngang (`qa7r2-b13-{360,1280}-{light,dark}.png`) |
| UI số hợp lệ lớn nhất | `999.999.999.999` | ✅ 1 POST → PAID, lưu 999999999999 |
| **API tay** | `123456789012345`, `99999999999999`, `1e20`, `1e999999`, `1000000000000`, `999999999999.995`, số JSON `1e20`, `100000000000000` | ✅ 400 `BR-TT-08` "Số tiền quá lớn (tối đa 999.999.999.999,99 ₫)." |
| API tay | `0.001`, `0.004`, `0,001`, `0`, `0.00`, `-5`, `-540000`, `-0.001`, `1e-30`, số JSON `0.001` | ✅ 400 `BR-TT-08` "Số tiền phải là số lớn hơn 0." Không có giao dịch nào, **0 dòng amount ≤ 0 trong DB** |
| API tay hợp lệ | `999999999999.99` → PAID, lưu đúng · `999999999999` → PAID · `0.005` → làm tròn 0.01, UNDERPAID · `1000.456` → lưu 1000.46 | ✅ |
| **Webhook nội bộ Django** (`X-Internal-Token`), cả khi có mã đơn và khi không có mã đơn | `1e20`, `123456789012345`, `100000000000000`, `1e999999`, `999999999999.995`, `0.001`, `0.004`, số `0.001`, `0`, `-5`, `NaN`, `Infinity` | ✅ 24/24: 400 `WEBHOOK_INVALID_INPUT`, không ghi (nhánh UNMATCHED cũng không ghi). `999999999999.99` → 200 MATCHED |
| **Qua adapter thật** | `transferAmount` = `1e14`, `1e20` (số và chuỗi), `123456789012345`, `999999999999.995`, `0.001`, `0.004`, `"0.001"` | ✅ 8/8: **400** (không 502). Body = lỗi Django, không ghi. Mỗi webhook chỉ 1 lần "Django lỗi" trong log adapter, tức không retry |
| Qua adapter | `999999999999`, `999999999999.99` | ✅ 200 MATCHED |
| Qua adapter | `transferAmount` = `0`, `-5`, `"0"`, `-0.001` | ❌ **500** (không phải 502), không ghi, đơn không đổi. Đây là **B7** (lần trước), ngoài B12/B13 — xem mục Lỗi |

## Chấp nhận có chủ ý: token nội bộ sai → adapter 502 (`badtok_r2.py`)

| Ca | Kết quả |
|---|---|
| Adapter :8101 với `INTERNAL_SERVICE_TOKEN` sai → webhook hợp lệ | ✅ 502 "Gọi Django nội bộ thất bại: Django trả HTTP 401…". Không có giao dịch, đơn vẫn BOOKED |
| Không retry với 401 | ✅ Log adapter có đúng 1 dòng "Django lỗi (lần 1/3)" cho mỗi webhook. Script đếm "2 lần gọi" là sai: nó đếm cả dòng `Unauthorized:` lẫn dòng access log của cùng một request |
| SePay gửi lại sau khi sửa cấu hình (gửi cùng webhook qua adapter đúng token) | ✅ 200 MATCHED, đúng 1 giao dịch. Hành vi đúng như dev-notes mô tả: không mất khoản tiền |
| Sai secret SePay | ✅ 401 |

## Phân quyền · Rò giá vốn · Chứng từ (chạy lại toàn bộ trong `api_l7b.py` / `ui_l7b.py`)
- Phân quyền: kết quả giống hệt bảng lần 1 cho 9 vai + ẩn danh, cả API và UI 360/1280. Riêng S11-AC7 (403 cho `ql1`, `ql9`, `kho1`, `khoonly`, `giao1`, `giao2`, `moi1`; ẩn danh 401): ✅.
- Rò giá vốn: quét đệ quy mọi trang list và chi tiết **81 đơn** (gồm timeline, payments) cho `ql1`, `ql9`, `kho1`, `khoonly`, và 1 đơn cho `giao1`/`giao2` → **0 key/giá trị**. Đối chứng: Chủ thấy `unit_cost` 91234.56. Trên UI: 0 `.alloc-cost`, JSON qua trình duyệt 0 hit. Shop 6/6.
- Chứng từ: DELETE/PATCH → 403/405, chứng từ còn nguyên. AuditLog `confirm_payment_manual` ghi đúng 1 lần mỗi lần xác nhận tay thật, lần duplicate không ghi.

## Hồi quy

| Ca | Kết quả |
|---|---|
| `backend manage.py test` | ✅ Ran 436 tests, OK (16,3 s) · `makemigrations --check --dry-run` No changes detected |
| `adapter pytest -q` | ✅ 15 passed |
| erp-console `tsc --noEmit` · `npm run build` repo · build thật :8000 · build mock · `frontend npm run build` | ✅ exit 0 ×5. `out/` repo + build thật: 0 file chứa dấu mock |
| e2e mock `s10_s11_orders.py` · `s8_views.py` (:3101) | ✅ 90/90 · 45/45 |
| e2e BE thật `s41_s47_real.py` (SEED=e2e, :3102) | ✅ 39/39 |
| `qa5/shop_e2e.py` (Shop :3000 → BE thật) | ✅ 6/6 (bấm đúp → 1 đơn, HTML không giá vốn) |
| Toàn bộ S10/S11 của lần 1 trong `api_l7b.py` / `ui_l7b.py` | ✅ (trừ ⏸ đồng thời trên SQLite, giống lần 1) |

## Lỗi

**B12 và B13 đã đóng.** Không có lỗi mới do lượt sửa này gây ra.

### B7 (còn mở, có từ trước) — Adapter trả 500 khi `transferAmount` ≤ 0 · Medium · chặn deploy adapter, không chặn L7
- **Tái hiện:** chạy `ad.sh` rồi `POST :8100/webhook/sepay` với `Authorization: Apikey qa7-sepay` và payload hợp lệ có `transferAmount` là `0`, `-5`, `"0"` hoặc `-0.001`.
- **Mong đợi:** 400 "Payload SePay không hợp lệ", tức cùng nhóm với các ca B13 khác qua adapter.
- **Thực tế:** 500. Log: `TypeError: Object of type ValueError is not JSON serializable`, tại `HTTPException(detail={"errors": exc.errors()})` ở `adapter/app/main.py`.
- **Ảnh hưởng:** không ghi giao dịch, đơn không đổi, không mất tiền. SePay nhận 5xx nên sẽ gửi lại. Lượt này có sửa `main.py` và nói "adapter không 502" cho B13, nhưng chưa đụng tới B7.
- **Gợi ý:** như lần trước, dùng `exc.errors(include_context=False)` và thêm test adapter đi hết endpoint cho 0 / −5 / NaN trần.

### Ghi nhận (không chặn)
- BE và FE lệch nhau ở số lẻ. BE nhận `0.005` (làm tròn thành 0,01 ₫ → UNDERPAID) và lưu `1000.456` thành 1000,46. FE cắt phần lẻ và đòi ≥ 1 ₫. Không sai BR-TT-08 (> 0 sau khi làm tròn) và không có giao dịch 0 ₫. PO nên chốt có cho phép số lẻ dưới 1 ₫ ở đường tay/webhook hay không.
- Chuẩn hoá mã chỉ bỏ khoảng trắng và đổi sang chữ hoa. Mã gõ kèm dấu gạch (`FT-880003`) vẫn được coi là mã khác. Dev-notes chưa hứa xử lý ca này, nên QA chỉ ghi lại.
- Khi Django trả 400, `detail` của adapter lồng body Django (`{"detail": {"detail": …, "code": …}}`). Cách này đúng contract dev ghi.
- Còn từ trước: B1, B8, B9. N-6 chưa chốt: tiền về cho đơn không còn BOOKED vẫn ghi MATCHED nếu **khác mã**.

## Lệnh đã chạy (kèm output tóm tắt)
```
backend manage.py test                              → Ran 436 tests in 16.277s OK
makemigrations --check --dry-run                    → No changes detected
adapter pytest -q                                   → 15 passed, 1 warning
builds.sh (realsrc :8000 / mocksrc / tsc / repo build / frontend build) → exit 0 ×5 · grep dấu mock trong out/ repo + realsrc = 0
be.sh (reset seed) + ad.sh (adapter :8100)          → api_l7b.py: 344 · PASS 339 · FAIL 5 (⏸ SQLite lock ×1, B7 ×4)
adapter :8101 token sai + badtok_r2.py              → 13 · PASS 12 · 1 script đếm sai (log adapter: 1 lần gọi/webhook) → 502, không ghi; SePay gửi lại qua adapter đúng → 200, 1 giao dịch
be.sh + http.server 3102 (realsrc/out) + ui_l7b.py  → 170 · PASS 170
  (lượt đầu 161/170: 9 FAIL giả do script kiểm "500" not in text trong khi tổng đơn là "117.500 ₫" — đã đổi thành "Lỗi máy chủ", chạy lại trên DB sạch)
http.server 3101 (mocksrc/out): e2e s10_s11_orders · s8_views → 90/90 · 45/45
SEED=e2e be.sh: e2e s41_s47_real.py (:3102)          → 39/39
be.sh + Shop next dev :3000 + qa5/shop_e2e.py       → 6/6
kill PID (be, ad, ad_bad, fe-real, fe-mock, shop) + pkill next dev · lsof 8000/8100/8101/3000/3101/3102 → sạch · ps = 0 · backend/db.sqlite3 mtime 13/09
```
Script, log, ảnh ở scratchpad `qa7/`: `api_l7b.py`, `ui_l7b.py`, `badtok_r2.py`, `r2/{mk.py,mkui.py,b12b13.py}`, `r2/*.out`, `shots/qa7r2-*.png`. Không sửa code sản phẩm, không sửa `erp-console/e2e/*`, không thêm test vào repo.
