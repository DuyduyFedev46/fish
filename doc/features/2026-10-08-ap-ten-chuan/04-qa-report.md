# 04 — QA: lô áp tên chuẩn

## QA lô áp tên chuẩn (08/10)

Nhánh `feat/ten-chuan-fe`, HEAD b572525 (đã merge BE). Chạy thật: runserver từ worktree, SQLite tạm, `migrate` từ DB trống (có `accounts/0017`), dữ liệu giả
(19 đơn đủ trạng thái, 12 phiếu giao, 4 phiếu hoàn tiền, 16 khoản tiền, 1 hàng hoàn, 5 vai `loc` `ql1` `kho1` `giao1` `cskh1`). ERP và Shop build `USE_MOCK=0` trỏ vào runserver.
Ảnh và log nằm ở scratchpad, không đưa vào repo. Toàn bộ khách, SĐT, địa chỉ đều là dữ liệu giả (`Khách giả N`, `09010000NN`).

## Kết luận: REJECTED — chữ cũ còn sót ở chỗ e2e không quét (ghi chú khoản tiền, modal, toast, thông báo lỗi, API) và 1 câu bị thay chữ máy móc thành câu vô nghĩa

## Tổng: 69 ca · ✅ 64 · ❌ 5 · ⏸ 0

Không có lỗi Critical: không rò giá vốn, không rò dữ liệu cá nhân, không đổi giá trị DB, không đổi quyền. Lỗi chặn đều là chữ hiển thị (Medium), sửa nhỏ.

## Theo yêu cầu của điều phối viên

| # | Việc kiểm | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | e2e `standard_names_all_routes` trên BE thật, mọi vai, mọi route, cộng Shop | ❌ 35/36 | Bản sao kịch bản (đổi mật khẩu, id thật, bỏ `PENDING_ROUTES`, 73 route × 5 vai, 19 đơn Shop). Đỏ 1 ca: `/orders/payments/detail/?id=14` còn "Phiếu hoàn #3 · mã GD hoàn FTREF0001" (B1). `/permissions/` (cả 3 trang chi tiết) sạch với mọi vai |
| 2 | So mẫu bằng mắt, 20 dòng C/T/P | ✅ (kèm B2–B4) | Bảng "So mẫu" bên dưới, ảnh `shots/*.png` |
| 3 | Nhật ký W11 | ✅ | "Giao thất bại → Đang giao" (phiếu giao), "Đang giao → Đã giao", "Chờ hoàn tiền → Hoàn thất bại", "Chờ hoàn tiền → Đã hoàn tiền", "Đang soạn hàng → Chờ lấy hàng" |
| 4 | M1 | ✅ | `/confirmation/detail/?id=5` (WANT_CHANGE) có dòng "Huỷ đơn, hoàn tiền rồi đặt lại đơn mới", lý do "Khách muốn đổi món". Việc 1 và 12 (không phải WANT_CHANGE): 0 dòng gợi ý. API `escalation_label` = "Khách muốn đổi món", có khoá `auto_cancel_blocked_label` = null |
| 5 | Dữ liệu cũ + migration | ✅ | Bên dưới |
| 6 | Không đổi giá trị DB | ✅ | So 28 endpoint giữa main (cổng 8766, cùng DB sao chép) và nhánh: mã trạng thái và tập khoá giống hệt, chỉ khác khoá phụ `auto_cancel_blocked_label`. Shop: `status` giữ `BOOKED`/`CANCELLED`/`AUTO_CANCELLED`/`COMPLETED`/`PROCESSING`, chỉ `status_label` đổi theo bảng |
| 7 | `ed_batch9_returns` | ✅ không có ca mới | Main (bản `git archive main`, build mock=1, cổng 3101): 133/139. Nhánh: 133/139. `diff` danh sách FAIL: giống hệt 6 ca |
| 8 | 360px và 1280px, 2 ca ngoài đường thuận | ✅ / ❌ | Bên dưới |

### 5. Dữ liệu cũ
- Chèn AuditLog `cancel_paid_order` note kiểu cũ: "Lý do: Hư hỏng khi soạn hàng", "Lý do: Bỏ giao sau khi thất bại · Có ghi chú (xem trên chứng từ gốc)", "Lý do: Khác" hiện nguyên văn ở Nhật ký, không bị che.
- Note `resolve_payment` cũ "Hoàn tiền theo phiếu hoàn #3" và mới "…phiếu hoàn tiền #4" đều hiện đúng.
- Đối chứng âm: note có SĐT hoặc tên ("Lý do: Hư hỏng khi soạn hàng 0901234567 Số 5 Đường Giả", "…phiếu hoàn #3 khách Nguyễn Văn A") bị che thành "Có ghi chú". Trang Nhật ký không chứa các chuỗi đó.
- `Permission.name` sau `migrate` từ trống: 9 quyền đều theo tên mới ("Xác nhận đã nhận tiền", "Mở bán lô", "Huỷ lô quá hạn (ghi lỗ)", "Duyệt hàng hoàn", "Chọn người giao", "Soạn hàng", "Xem báo cáo lãi lỗ", "Xem Tổng quan", "Sửa ảnh mặt hàng").
- `migrate accounts 0016` về tên cũ ("Publish lô ra Shop", "Xác nhận thanh toán thủ công"...), `migrate accounts` lại về tên mới. Số quyền gán Group giữ 278 ở cả ba trạng thái. `makemigrations --check --dry-run`: không đổi gì.

### 8. Khung nhìn và ngoài đường thuận
- 1280px: 21 màn của `loc`, 360px: 11 màn của `loc` và 2 màn của `giao1`. Không màn nào tràn ngang, console không có lỗi. Shop 360px và 1280px: không tràn, console sạch.
- **Màn cũ (trạng thái đã đổi):** mở phiếu hoàn tiền #2 (Chờ hoàn tiền), người khác xác nhận hoàn qua API, màn cũ vẫn hiện nút. Bấm nhận thông báo "Phiếu đã hoàn, không đổi trạng thái được." và hộp có câu "Phiếu chuyển sang Đã hoàn" (B2, B4). Không tạo phiếu thứ hai, dữ liệu không sai.
- **Dữ liệu đã có giao dịch:** đơn hoàn tất có phiếu hoàn tiền, đơn huỷ sau khi trả tiền, phiếu giao giao lại sau thất bại (FAILED → DELIVERING), hàng hoàn đã duyệt: màn đơn, Nhật ký, dòng thời gian đều hiện chữ chuẩn.
- Lưu ý 360px: thanh bước của đơn xuống dòng từng chữ ("Đa ng gia o", "Chờ gọi xác nhận" 4 dòng). Nhãn "Đang giao" và "Hoàn tất" đã như vậy từ trước, nhãn "Chờ gọi xác nhận" dài hơn nên xấu hơn (Low).

## So mẫu 20 dòng (chữ thấy trên màn thật)

| Dòng | Màn | Chữ thấy | Khớp |
|---|---|---|---|
| T2 | `/orders/` | chip "Hết giờ giữ chỗ", lý do "Hết giờ giữ chỗ" | ✅ |
| T1 | `/orders/` | BOOKED "Giữ chỗ"; Shop "Chờ thanh toán" | ✅ |
| T4/T6/T7 | `/orders/payments/` | "Chuyển thiếu", "Không khớp đơn", "Chuyển thừa" | ✅ |
| T5 | `/orders/payments/` (lọc) | "Về sau khi đơn đã huỷ" | ✅ |
| T10 | chi tiết khoản tiền | Nguồn "Ngân hàng báo" | ✅ |
| T21/T22/T23 | `/orders/refunds/`, chi tiết | "Chờ hoàn tiền", "Đã hoàn tiền", "Hoàn thất bại" | ✅ |
| C3 | tab, menu | "Phiếu hoàn tiền"; menu "Hoàn tiền chờ chuyển" | ✅ |
| T24–T30 | `/deliveries/`, chi tiết, `/orders/` | "Chờ gọi xác nhận", "Đang soạn hàng", "Chờ lấy hàng", "Đang giao", "Đã giao", "Giao thất bại", "Đã huỷ theo đơn" | ✅ |
| T26/T27/T28 | dòng thời gian đơn | "Phiếu giao …: Chờ lấy hàng → Đang giao", "Đã giao — đơn hoàn tất" | ✅ |
| T25 | dòng thời gian đơn | "Tạo phiếu giao … (Đang soạn hàng)" | ✅ |
| C1 | menu, `/returns/` | menu "Hàng hoàn", "Phiếu hàng hoàn", "Nhập hàng hoàn", "Duyệt hàng hoàn" | ✅ |
| T45 | `/returns/` | "Huỷ hàng, ghi lỗ" | ✅ |
| T44 | `/ledger/` (giao diện) | "Huỷ hàng, ghi lỗ" (API còn chữ cũ, B4) | ✅ giao diện |
| C2/P6 | dòng thời gian đơn huỷ | "Lập phiếu trừ doanh thu DC-…" | ✅ |
| P7 | chi tiết đơn, Tài khoản | "Lập phiếu hoàn tiền" | ✅ |
| P1–P13 | `/permissions/`, `/account/` | "Xác nhận đã nhận tiền", "Mở bán lô", "Duyệt hàng hoàn", "Chọn người giao", "Soạn hàng, in tem", "Đăng bài lên Shop" | ✅ |
| T33/T37 | chi tiết việc gọi, lịch sử gọi | "Khách muốn đổi món" | ✅ |
| T39 | `/confirmation/` | tab "Đến giờ gọi" | ✅ |
| T54–T57 | `/content/` | "Chính sách bảo mật, Điều kiện giao dịch chung, Chính sách đổi trả và hoàn tiền, Thông tin người bán" | ✅ |
| T53 | `/catalog/` | "Đang kinh doanh" (mặt hàng); Ưu đãi không có dữ liệu để xem | ✅ |
| Shop | `/shop/orders/` | 8 trạng thái, "Đang chờ hoàn tiền", không mã thô | ✅ |

## Phân quyền, giá vốn, dữ liệu cá nhân
- Quét 5 vai × 73 route ERP: `kho1`, `giao1`, `cskh1`, `ql1` sạch chữ cấm. Ma trận quyền: hàng "Xác nhận đã nhận tiền", "Xác nhận đã hoàn tiền", "Chốt lô" chỉ Chủ, đúng như trước lô.
- So 28 endpoint main và nhánh: tập khoá giống hệt, chỉ thêm `auto_cancel_blocked_label`; không thêm field nào mang giá vốn hay dữ liệu khách. Quét chữ cấm trên 232 cặp (endpoint × vai): chỉ trúng nhãn sổ nhập xuất (B4) và các mã `BR-…` trong khoá `code` của guidance (khoá cấu trúc, FE ánh xạ, không hiển thị).
- `auto_cancel_blocked_label` là câu cố định ("Lô đã chốt, không tự huỷ được"), không tính ngược ra giá vốn, không có tên/SĐT/địa chỉ.
- Shop tra đơn (360px và 1280px): HTML, `localStorage`, `sessionStorage`, URL không chứa SĐT, tên, địa chỉ; JSON công khai chỉ có mã đơn, trạng thái, hàng, tiền. Console sạch.
- ERP bản build thật: `localStorage` chỉ có `cave_erp_token`, `cave_erp_last_user`, `cave_erp_signed_in_at`; không có dữ liệu khách. `check-no-mock` XANH.
- Note Nhật ký mới không chép dữ liệu cá nhân (đối chứng âm ở mục 5).

## Lỗi

### B1 — Ghi chú xử lý khoản tiền còn "Phiếu hoàn #N" · Medium · lô áp tên chuẩn (C3)
Bước tái hiện: BE thật, lập phiếu hoàn tiền cho khoản tiền về lệch (ORPHAN), xác nhận hoàn (`POST sales/refunds/<id>/confirm/`), mở ERP `/orders/payments/detail/?id=14`.
Mong đợi: "Phiếu hoàn tiền #3 · mã GD hoàn …". Thực tế: "Phiếu hoàn #3 · mã GD hoàn FTREF0001". Nguồn: `backend/apps/sales/payments/services.py:905` (`p.resolution_note = f"Phiếu hoàn #{refund.pk} · …"`); dòng 909 (AuditLog) đã sửa nhưng dòng 905 sót.
Ảnh hưởng: e2e `standard_names_all_routes` trên BE thật đỏ (regex `phiếu hoàn(?! tiền)`), chữ trơn dễ lẫn với phiếu hàng hoàn (C1). Dữ liệu cũ giữ nguyên chữ cũ là chấp nhận được.

### B2 — Chữ trạng thái phiếu hoàn tiền và phiếu giao cũ trong toast, hộp thoại · Medium · T21–T24, T28
Bước tái hiện: ERP bản build thật, `/orders/refunds/detail/?id=2`, bấm "Xác nhận đã hoàn tiền" (hộp hiện cảnh báo vàng). Các chỗ khác đọc từ mã nguồn rồi chạy lại ở những màn mở được.
- `erp-console/features/orders/messages.ts:303` "Phiếu chuyển sang Đã hoàn." (thấy trên ảnh hộp thoại) và `:305`; mong đợi "Đã hoàn tiền".
- `messages.ts:171` "Trạng thái Chờ hoàn.", `:312` và `:314` "Phiếu quay lại Chờ hoàn."; mong đợi "Chờ hoàn tiền".
- `messages.ts:308` và `:310` "Phiếu chuyển sang Thất bại."; mong đợi "Hoàn thất bại".
- `erp-console/features/confirmation/components/UnconfirmModal.tsx:59` "Đơn về Chờ xác nhận"; mong đợi "Chờ gọi xác nhận" (T24).
- `erp-console/features/deliveries/components/DeliveryDetailScreen.tsx:464` "Phiếu chuyển sang Hoàn tất."; phiếu giao hoàn thành là "Đã giao" (T28).
Chữ đọc từ mã nguồn mà chưa bấm tới (toast thất bại, thử lại, giao xong): ⏸ về mặt chạy thật, nhưng cùng một nguồn chữ nên rủi ro thấp.
Ảnh hưởng: ngay cạnh chip "Đã hoàn tiền" người dùng đọc "Đã hoàn"; trái nguyên tắc "một tên cho mỗi chứng từ".

### B3 — Câu bị thay chữ máy móc thành vô nghĩa · Medium · C3, T28
Bước tái hiện: `/deliveries/detail/?id=10` (phiếu Đang giao), bấm "Đã giao xong". Hộp xác nhận hiện "Đã giao tận tay khách? **Phiếu hoàn tiền tất rồi** thì không sửa lại được."
Nguồn: `erp-console/features/deliveries/components/ConfirmCompleteModal.tsx:71` (và comment dòng 3). Câu gốc là "Phiếu hoàn tất rồi…" (phiếu giao hoàn tất); lệnh thay "phiếu hoàn" thành "phiếu hoàn tiền" làm hỏng chữ.
Mong đợi: câu nói về phiếu giao, ví dụ "Phiếu giao đã giao rồi thì không sửa lại được." Ảnh hưởng: người giao hàng đọc câu sai nghĩa ở thao tác không hoàn lại được.
Gợi ý: grep toàn nguồn các cụm "phiếu hoàn tiền (tất|xong|…)" (đã grep, chỉ còn chỗ này).

### B4 — Thông báo lỗi BE và nhãn API còn chữ cũ · Medium (nhóm gộp) · T22, T23, T44, T45, C9
Bằng chứng chạy thật (API trên runserver, vai `loc`):
- `POST sales/refunds/1/retry/` (phiếu đang chờ): `"Chỉ thử lại được khi phiếu đang Thất bại."` (`refunds/services.py:278`); cũng `:253` "…đang Chờ hoàn." Mong đợi "Hoàn thất bại", "Chờ hoàn tiền".
- `POST sales/refunds/3/confirm/` hoặc `mark-failed/` (đã hoàn): `"Phiếu đã hoàn, không đổi trạng thái được."` (`refunds/services.py:41`). Mong đợi "Phiếu đã hoàn tiền…".
- `GET inventory/ledger/`: `type_label` của WRITE_OFF là "Ghi lỗ, huỷ hàng" (`inventory/stock/serializers.py:16`, `LEDGER_TYPE_LABEL_OVERRIDES`). T44 chuẩn "Huỷ hàng, ghi lỗ". Màn `/ledger/` hiện đúng vì dùng `enums.ts`, nên chỉ API (và bất cứ nơi nào dùng khoá này) lệch.
- `inventory/returns/services.py:26`, `returns/api.py:94`: "Phải chọn Tái nhập hoặc **Huỷ bỏ** trước khi duyệt"; T45 là "Huỷ hàng, ghi lỗ".
- `delivery/confirmation/api.py:66`: Http404 "Mục chờ gọi không hợp lệ." (C9 là "Việc gọi xác nhận").
Các bài kiểm BE hiện chỉ khoá `choices`/`verbose_name`, nên không bắt được những chuỗi này.

## Quan sát (Low, không chặn)
- `backend/apps/sales/models/refunds.py:86`: `Permission.name` của `create_refund` vẫn "Tạo phiếu hoàn tiền", còn P7 chuẩn "Lập phiếu hoàn tiền" (Django Admin; ma trận và Tài khoản đã đúng).
- `refunds/next_steps.py:167`: "Phiếu hoàn gần hạn 30 ngày (BR-AI-33)" (gợi ý AI, lô này loại trừ phần AI), có mã BR trong chữ.
- Thanh bước đơn ghi "Soạn hàng" (02b cho phép vì chỉ cấm khi là chip); T25 chuẩn là "Đang soạn hàng". Xem lại có muốn thống nhất không.
- Shop: đơn đã huỷ sau khi trả tiền hiện "Chưa thanh toán." và nút "Thanh toán lại". Không do lô này (Shop chỉ đổi mock) và có sẵn trên main; nên báo PO.
- `ed_batch9_returns` đỏ sẵn trên main (cùng 6 ca): lọc tháng mặc định, phạm vi danh sách (RT-4 tháng trước) và "F2m SĐT không nằm trong storage". Ca cuối do `sessionStorage.cave_erp_mock_orders` (dữ liệu giả của bản mock) chứa chuỗi SĐT giả `0912345678` từ bước trước của chính kịch bản; riêng lẻ, hộp nhập hàng hoàn không lưu SĐT vào storage. Chỉ bản mock, không có trong bản build thật (`check-no-mock` XANH). Không do lô này.

## Lệnh đã chạy (output tóm tắt)
| Lệnh | Kết quả |
|---|---|
| `manage.py test --parallel 4` (worktree) | Ran 3261 tests, OK (skipped=2) |
| `makemigrations --check --dry-run` | No changes detected |
| `migrate` từ DB trống, `migrate accounts 0016`, `migrate accounts` | OK cả ba, tên quyền đổi qua lại đúng |
| `npm ci` (erp-console, frontend) | 0 |
| `tsc --noEmit` (erp-console) | 0 |
| `vitest run` (erp-console) | 97 file, 1182 test xanh |
| `NEXT_PUBLIC_USE_MOCK=0 npm run build` (ERP, Shop, trỏ `127.0.0.1:8765`) | 0 |
| `node scripts/check-no-mock.mjs` / `check-ai-chunks.mjs` | XANH / XANH |
| `python3 scripts/check_naming.py` | OK, không phát sinh mới |
| bản sao `standard_names_all_routes` trên BE thật, 5 vai + 19 đơn Shop | 35/36 (ca đỏ: B1) |
| `ed_batch9_returns` main vs nhánh (mock=1) | 133/139 và 133/139, cùng 6 ca |
| So 28 endpoint main vs nhánh | chỉ khác khoá phụ `auto_cancel_blocked_label` |

Dọn dẹp: đã tắt runserver (8765, 8766) và 2 máy chủ tĩnh theo PID của QA; xoá DB tạm, `out/`, `.next/`, symlink `backend/.env`, `backend/staticfiles`.

## QA lại sau bf0acf6 (lần 2)

Chạy lại trên BE thật (runserver từ worktree, SQLite tạm, `migrate` từ trống, dữ liệu giả; ERP và Shop build `USE_MOCK=0`). Mọi thao tác dưới đây bấm thật trên màn bằng Playwright, vai `loc`.

### Kết luận: APPROVED — B1–B4 và Low B-P7 đã sửa, không lỗi mới
Tổng lần này: 14 ca · ✅ 14 · ❌ 0 · ⏸ 0.

| Lỗi | Kết quả | Bằng chứng |
|---|---|---|
| B1 | ✅ | Hoàn tiền thật phiếu #6 (gắn khoản Chuyển thừa) bằng nút "Xác nhận đã hoàn tiền": chi tiết khoản 16 hiện "Phiếu hoàn tiền #6 · mã GD hoàn FTREFQA6"; khoản 14 (phiếu #2) hiện "Phiếu hoàn tiền #2 · …". Không còn "phiếu hoàn" trơn |
| B2 phiếu hoàn tiền | ✅ | Hộp xác nhận: "Phiếu chuyển sang Đã hoàn tiền…" và toast "Đã xác nhận chuyển khoản hoàn tiền. Phiếu chuyển sang Đã hoàn tiền." (phiếu #1, #6). Báo chuyển thất bại: hộp "Phiếu chuyển sang Hoàn thất bại…", toast "…Phiếu chuyển sang Hoàn thất bại.", chip "Hoàn thất bại" (phiếu #4). Chuyển lại: hộp "Phiếu quay lại Chờ hoàn tiền…", toast "Phiếu quay lại Chờ hoàn tiền.", chip "Chờ hoàn tiền" |
| B2 UnconfirmModal | ✅ | Việc gọi #6, "Huỷ xác nhận đơn": "Sau khi huỷ: Phiếu giao về Chờ gọi xác nhận, gọi lại khách" |
| B2 giao xong | ✅ | Phiếu giao #7, bấm "Đã giao xong": toast "Đã giao xong. Đơn đã hoàn tất.", chip "Đã giao". Câu dự phòng ở `DeliveryDetailScreen.tsx:464` (khi đơn chưa hoàn tất) đã là "Phiếu chuyển sang Đã giao." (đọc mã nguồn, ⏸ về chạy thật vì cần đơn nhiều phiếu giao; cùng nguồn chữ) |
| B3 | ✅ | Hộp "Đã giao xong": "Đã giao tận tay khách? Phiếu giao đã giao xong thì không sửa lại được." |
| B4 lỗi API | ✅ | `retry` phiếu chờ: "Chỉ thử lại được khi phiếu đang Hoàn thất bại."; `confirm`/`mark-failed` phiếu đã hoàn: "Phiếu đã hoàn tiền, không đổi trạng thái được."; `approve` không chọn quyết định: "Phải chọn Tái nhập hoặc Huỷ hàng, ghi lỗ trước khi duyệt"; `confirmation/queue/abc/`: 404 "Việc gọi xác nhận không hợp lệ." |
| B4 ledger | ✅ | `GET inventory/ledger/` `type_label` của WRITE_OFF = "Huỷ hàng, ghi lỗ" |
| B-P7 | ✅ | `Permission.name` của `create_refund` sau `migrate` từ trống = "Lập phiếu hoàn tiền" |
| e2e `standard_names_all_routes` BE thật | ✅ 36/36 | 73 route × 5 vai, nhóm A và B sạch, `/permissions/` sạch, Nhật ký W11, Shop 19/19 đơn (8 trạng thái, không mã thô) |
| Quét API 232 cặp (endpoint × vai) | ✅ | Chỉ còn mã `BR-…` ở khoá `code` của guidance (khoá cấu trúc, không hiển thị) |
| Console trình duyệt | ✅ | Không lỗi ở mọi luồng trên |

Chạy lại: BE `manage.py test --parallel 4` 3267 OK (skipped=2) · `makemigrations --check --dry-run` sạch · `tsc --noEmit` 0 · vitest 97 file, 1183 test xanh · build ERP và Shop `USE_MOCK=0` 0 · `check-no-mock` XANH · `check-ai-chunks` XANH · `check_naming` OK.
Giữ nguyên các quan sát Low cũ không thuộc B1–B4 (thanh bước "Soạn hàng", Shop "Chưa thanh toán" của đơn đã huỷ có sẵn trên main, 6 ca đỏ sẵn của `ed_batch9_returns`). Đã tắt server theo PID của QA, xoá DB tạm, `out/`, `.next/`, symlink.
