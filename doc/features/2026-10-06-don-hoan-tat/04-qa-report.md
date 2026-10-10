# QA — Đơn hoàn tất (W37) · phần BE của L1 (S2, S1)

## QA L1 BE (08/10)

### Kết luận: APPROVED — mọi AC của S1/S2 phần BE chạy thật qua HTTP đều đúng, không có kết cục lệch cặp đơn/phiếu, không rò giá vốn hay dữ liệu cá nhân mới
### Tổng: 33 ca · ✅ 31 · ❌ 0 · ⏸ 2 (SQLite báo `database is locked` ở vài lượt đua, xem dưới)

Cách chạy: nhánh `feat/w37-l1-be`, `runserver` cổng 8765 trên SQLite tạm (`DATABASE_URL`), `DJANGO_DEBUG=1`, dữ liệu giả
(SĐT 0900000xxx, "Khách Giả n"), token 5 vai (owner, manager, warehouse_staff, delivery_staff x2). Đã gỡ server, DB tạm,
symlink `.env` và `staticfiles`.

### Theo AC
| Mã AC | Kết quả | Bằng chứng (HTTP thật) |
|---|---|---|
| S1-AC1 | ✅ | Đơn PROCESSING, NV giao POST `COMPLETED` → 200, `order_status: COMPLETED`; GET đơn thấy `COMPLETED` |
| S1-AC2 | ✅ | 24 dòng AuditLog `complete_order`, 24 đơn khác nhau (mỗi đơn đúng 1), `actor_kind=system`, `actor` rỗng; `changes` = `{status:{PROCESSING→COMPLETED}, delivery_note, delivery_note_id}`, `note` rỗng; quét SĐT/tên/địa chỉ: 0 dòng chứa |
| S1-AC3 | ✅ | Lãi lỗ kỳ (`/reports/period/`), lãi lỗ lô (`/reports/batches/`) bằng nhau từng khoá trước/sau; `revenue_today` 8640000 = 8640000. Khác biệt duy nhất ở Tổng quan: `kpis.pending_orders` 11→10, `recent_orders`, `as_of` (được phép, đúng ghi chú của helper snapshot). 5 phiếu đảo chỉ ở 5 đơn bị huỷ, 0 Refund |
| S1-AC4 (lặp) | ✅ | Gửi lại đúng yêu cầu → 200 `already: true`, `complete_order` vẫn 1 dòng |
| S1-AC5 (thất bại) | ✅ | Báo FAILED → đơn giữ PROCESSING, 0 AuditLog `complete_order` |
| S1-AC6 (giao lại) | ✅ | FAILED → DELIVERING → COMPLETED → đơn COMPLETED, đúng 1 dòng audit |
| S1-AC7 (nhiều phiếu) | ✅ | P1 xong, P2 FAILED → đơn giữ PROCESSING, 0 audit |
| S1-AC8 (nhiều phiếu) | ✅ | P1 xong, P2 CANCELLED → đơn COMPLETED (phiếu huỷ không tính) |
| S1-AC9 (rollback) | ⏸ | Cần giả lập lỗi lưu đơn, không làm được qua HTTP; test đơn vị của dev xanh (36 test chạy lại, OK, skipped=2) nhưng không tính là bằng chứng HTTP |
| S1-AC10 | ✅ | Chỉ PROCESSING chuyển; đơn COMPLETED sẵn: gửi lại không thêm audit (qua S1-AC4). Đơn PAID không tạo được qua luồng thật, dựa vào test dev (không chấm bằng đọc code) |
| S1-AC11 | ✅ | NV giao khác (chưa được gán) → 404; phiếu/đơn không đổi |
| S1-AC12 | ✅ | PATCH/PUT `{status: COMPLETED}` ở owner, manager, delivery_staff → 405; `POST /sales/orders/{id}/complete/` → 404 (không có endpoint) |
| S1-AC13 | ✅ | Chưa đăng nhập → 401. Lưu ý: NV kho của repo này CÓ `change_deliverynote` nên gọi giao xong được 200 (dev ghi nhận lệch, đúng thực tế seed); kiểm "403" cần người chỉ có `view_deliverynote`, dựa vào test dev |
| S2-AC1 (đua) | ✅ (một phần ⏸) | 16 lượt song song bằng thread qua HTTP, phiếu FAILED, huỷ ∥ (DELIVERING rồi COMPLETED), xen kẽ thứ tự và độ trễ 0–60 ms. Kết cục: 4 lượt huỷ thắng (đơn CANCELLED + phiếu CANCELLED, giao nhận 400 BR-GH-24), 12 lượt giao thắng (đơn COMPLETED + phiếu COMPLETED, huỷ nhận 400 BR-GH-05 hoặc BR-GH-07). **0 cặp lệch.** 2 lượt có 5xx "database is locked" (SQLite) nên ghi ⏸; trạng thái cuối vẫn nhất quán |
| S2-AC2 | ✅ | Đơn + phiếu CANCELLED, giao xong → 400 `BR-GH-24`, "Đơn đã huỷ — mang hàng về kho.", `current_status: CANCELLED`; không đổi, không audit mới |
| S2-AC3 | ✅ | Huỷ đơn COMPLETED bằng manager và owner → 400 `BR-GH-05` "Đơn đã giao hoàn tất — chỉ còn cách lập phiếu hoàn."; đơn/phiếu giữ COMPLETED, không phiếu đảo mới |
| S2-AC4 | ✅ | Báo giao thất bại trên đơn huỷ (kèm lý do hợp lệ) → 400 BR-GH-24; phiếu vẫn CANCELLED |

### Ngoại lệ và biên
| Ca | Kết quả |
|---|---|
| Bắt đầu giao (DELIVERING) trên đơn đã huỷ, có và không có `from_status` | ✅ 400 BR-GH-24 kèm `current_status` |
| Huỷ đơn khi phiếu đang DELIVERING (hiện trạng) | ✅ 400 BR-GH-07, đơn giữ PROCESSING |
| `from_status` sai (stale) | ✅ 400 `STALE_STATE` kèm `current_status` |
| `to_status` không hợp lệ | ✅ 400 |
| Hai request y hệt song song (bấm đúp) | ✅ một 200 `already:false`, `order_status: COMPLETED`, 1 audit. Request thứ hai gặp SQLite locked (500) nên ⏸ cho nhánh `already:true` song song; nhánh lặp tuần tự đã ✅ ở S1-AC4 |
| Giao xong bởi NV kho (có `change_deliverynote`) | ✅ 200, đơn COMPLETED, 1 audit |
| Đơn nhiều phiếu / phiếu huỷ | ✅ xem S1-AC7/8 |

### Phân quyền (HTTP thật)
| Hành động | owner | manager | warehouse_staff | delivery_staff (được gán) | delivery_staff (khác) | chưa đăng nhập |
|---|---|---|---|---|---|---|
| Giao xong phiếu | không thử | không thử | 200 (có `change_deliverynote`) | 200 | 404 | 401 |
| Huỷ đơn `/cancel/` | 200/400 theo luật | 200/400 | 403 | 403 | 403 | 401 |
| Ghi thẳng `status` đơn (PATCH/PUT) | 405 | 405 | không thử | 405 | không thử | không thử |

### Rò giá vốn
✅ Quét 20 response của warehouse_staff và delivery_staff (giao xong, báo thất bại, lỗi 400/404): không có `purchase_rate`, `landed_unit_cost`, `unit_cost`, `rate`, `profit`. AuditLog `complete_order` không có khoá tiền hay kg nên không tính ngược được giá vốn. `order_status` chỉ là một chuỗi trạng thái.

### Rò dữ liệu cá nhân
- ✅ AuditLog `complete_order`: 0/24 dòng chứa SĐT, tên, địa chỉ (chỉ mã phiếu và id phiếu).
- ✅ Lỗi BR-GH-24 / BR-GH-05 không chứa dữ liệu khách.
- Quan sát (không thuộc L1, có sẵn trên main, không do nhánh này sinh ra): body trả về của `POST /api/delivery/notes/{id}/status/` dùng serializer cũ nên có `customer_name`, `address`, `phone`, kể cả khi người gọi là NV kho (`wh1` thấy tên/SĐT/địa chỉ phiếu của NV giao). Diff nhánh chỉ thêm 2 dòng `order_status`. Đề nghị đưa vào việc "Phạm vi dữ liệu" (PV) đang làm, không chặn L1.
- Không kiểm log trình duyệt/localStorage (không có FE trong L1 BE). Log server `server.log` chỉ có traceback SQLite lock, không in dữ liệu khách (không soi sâu từng dòng).

### Hồi quy
✅ `manage.py test` của điều phối viên: 3058 OK (skipped 2). Chạy lại 36 test L1: OK (skipped=2, hai test đua Postgres). Luồng cũ qua HTTP: READY/DELIVERING/FAILED/redeliver, huỷ đơn READY (phiếu đảo, kho hoàn), BR-GH-07 giữ nguyên.

### Lỗi
Không có lỗi chặn.

Ghi nhận (không chặn):
- N1 — Rủi ro T1 vẫn còn nợ: đua hai luồng thật chỉ chứng minh được ở mức "không lệch cặp" trên SQLite (khoá toàn bảng). Chưa có bằng chứng Postgres (hai test `skip`). Thứ tự khoá đơn → phiếu đã được test spy của dev xác nhận. Nên chạy 2 test Postgres ở staging/CI trước khi lên production.
- N2 — Dữ liệu cá nhân trong body phiếu giao cho NV kho (mục trên), có sẵn từ main.

### Lệnh đã chạy
- `manage.py migrate` + seed ORM trên SQLite tạm; `runserver 8765 --noreload`.
- Kịch bản HTTP bằng `urllib` (thư mục scratchpad): A–G, 16 lượt đua, quét rò, kiểm AuditLog/phiếu đảo bằng `manage.py shell`.
- `manage.py test apps.delivery.tests.test_order_completion apps.sales.orders.tests.test_completion_rule apps.delivery.tests.test_completion_race_postgres` → 36 OK, skipped 2.

## QA L1 FE (08/10)

### Kết luận: APPROVED — FE ERP khớp S1/S2/S6/S7 trên bản mock và trên BE thật (L1 BE); S6-AC8 chỉ đạt một nửa, để L3 như review đã ghi
### Tổng: 44 ca · ✅ 43 · ❌ 0 · ⏸ 1 (S6-AC8 phần đồng bộ hai kho mock)

Nhánh `feat/w37-l1-fe` đã merge `feat/w37-l1-be` (chỉ thêm mục QA BE ở trên, không xung đột). Dữ liệu giả (SĐT 0900000xxx, "Khách Giả n").

### Bản mock (NEXT_PUBLIC_USE_MOCK=1, `npm run build` exit 0, phục vụ tĩnh)
| Kịch bản | Kết quả |
|---|---|
| `e2e/order_completion_erp.py` | ✅ 6/6 |
| `e2e/ed_batch3_orders.py` (hồi quy đơn, kỳ vọng thanh bước 5 bước) | ✅ 143/143 (chạy với `BASE=http://127.0.0.1:3201`, mặc định của script là cổng 3101) |
| `e2e/ed_batch4_delivery.py` (hồi quy giao hàng) | ✅ 70/70 |

### BE thật (runserver từ worktree này có BE L1, SQLite tạm; erp-console build `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8766`; Playwright, 30/30)
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| S1 (FE): giao xong phiếu cuối | ✅ | NV giao 360px bấm "Đã giao xong" → toast "Đã giao xong. Đơn đã hoàn tất."; API xác nhận đơn `COMPLETED`. Ảnh `shots2/toast_completed_360.png` |
| S1 ngoài đường thuận: phiếu không phải cuối (đơn 2 phiếu, phiếu kia FAILED) | ✅ | Toast chỉ nói "Đã giao xong", KHÔNG nói "Đơn đã hoàn tất"; đơn vẫn `PROCESSING` |
| S2 (FE): đơn huỷ khi NV giao đang mở hộp xác nhận | ✅ | Mở hộp, rồi phiếu FAILED + quản lý huỷ đơn qua API, bấm giao xong → hộp hiện đúng "Đơn đã huỷ — mang hàng về kho." và nút chính "Tải lại"; đơn và phiếu vẫn `CANCELLED` (không bị ghi đè). Bấm "Tải lại": hộp đóng, thẻ phiếu huỷ biến mất. Cả 360px (`br_gh_24_360.png`) lẫn 1280px (`br_gh_24_1280.png`) |
| S6: bộ lọc | ✅ | Chủ: không còn "Đã thanh toán"; còn "Chưa xong", "Đang xử lý", "Hoàn tất". "Chưa xong" = 6 đơn (Giữ chỗ, Đang xử lý), không có đơn Hoàn tất; lọc "Hoàn tất" ra đúng đơn đã hoàn tất, và thêm đơn vừa giao xong sau thao tác (2 đơn). `list_unfinished_1280.png`, `list_completed_*.png` |
| S6-AC8 | ⏸ | Mock hai kho (Giao hàng và Đơn) chưa nối, theo review thì chuyển L3. Trên BE thật thì đơn đổi đúng (ca S1) |
| S7: thanh bước | ✅ | Chi tiết đơn: 5 bước (Giữ chỗ, Chờ gọi xác nhận, Soạn hàng, Đang giao, Hoàn tất). Đơn đang giao: bước "Đang giao" sáng, Hoàn tất chưa. Đơn `COMPLETED`: bước Hoàn tất sáng, kèm chip Hoàn tất. Đơn vừa giao xong ở bước trên chuyển sang Hoàn tất khi mở lại. `detail_*` |
| 360px / 1280px | ✅ | Không cuộn ngang ở mọi màn đã mở (việc giao của tôi, hộp xác nhận, danh sách đơn, chi tiết đơn) |
| Console | ✅ | Không `console.error` (bỏ qua "Failed to fetch RSC payload" do máy chủ tĩnh, như các e2e có sẵn); 400 BR-GH-24 là chủ ý |
| Dữ liệu cá nhân | ✅ | `localStorage`, `sessionStorage`, URL và console của NV giao không chứa SĐT hay tên khách. Màn "Việc giao của tôi" hiện tên, SĐT, địa chỉ khách của chính phiếu được giao (đúng Tầng 3) |
| Giá vốn | ✅ | Không thấy cột hay chuỗi giá vốn ở các màn đã chụp (NV giao không có quyền; chủ chỉ mở danh sách và chi tiết đơn, không có trường giá vốn) |

### Ghi nhận (không chặn)
- Đường BR-GH-24 trong hộp "Báo giao thất bại" chưa có ca trình duyệt thật (UI không mở được hộp cho phiếu đã huỷ); hộp "Xác nhận đã giao xong" thì đã chụp thật. Phần còn lại do vitest phủ, như review.
- Không chạy lại `tsc`/`vitest` (điều phối viên đã chạy: tsc sạch, vitest 1031 xanh); QA chạy build mock=1 và mock=0 đều exit 0.

### Lệnh đã chạy
- `git merge feat/w37-l1-be`; `npm run build` (mock=1) → 3 kịch bản e2e ở trên.
- Seed ORM 6 đơn + runserver 8766 (CORS 127.0.0.1:3202); `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8766 npm run build` exit 0; script Playwright (scratchpad) 30/30 PASS; kiểm lưu trữ trình duyệt.
- Dọn: dừng server, gỡ `out/`, symlink `node_modules`, `.env`, `staticfiles`, DB tạm.

## QA L2 + L4 BE (08/10)

### Kết luận: APPROVED — S3, S4, S5 và `refund_summary` chạy thật đúng AC; không lệch số báo cáo, không rò giá vốn hay dữ liệu cá nhân
### Tổng: 144 ca · ✅ 142 · ❌ 0 · ⏸ 2 (xem cuối mục "Ngoại lệ")

Cách chạy: nhánh `feat/w37-l2-l4-be`, `runserver` cổng 8791 trên SQLite tạm (`DATABASE_URL`), `DJANGO_DEBUG=1`. Dữ liệu giả (SĐT 0900000xxx, "Khách Giả n"),
5 tài khoản (owner, manager, warehouse_staff, hai delivery_staff). Dựng đơn kiểu cũ bằng sửa DB trực tiếp: đơn `PROCESSING` mà phiếu `COMPLETED`.
Lệnh chạy bằng `manage.py` thật (tiến trình con), API gọi qua HTTP bằng token. Đã tắt server theo PID, gỡ symlink `.env`/`staticfiles`, xoá DB tạm.

### Theo AC
| Mã AC | Kết quả | Bằng chứng (chạy thật) |
|---|---|---|
| S3-AC1 | ✅ | 4 đơn đủ điều kiện (X, X2 và hai đơn kẹt trong lô thử S4) chuyển `COMPLETED`; Y (phiếu FAILED), Z (huỷ), W (`PAID` + phiếu xong), M (P1 xong, P2 đang giao) giữ nguyên. So `id,status` toàn bảng trước/sau: chỉ đúng 4 đơn đổi |
| S3-AC2 | ✅ | Mỗi đơn có 1 dòng audit `backfill: W37`: `actor` rỗng, `actor_kind=system`, `changes` = `{status:{PROCESSING→COMPLETED}, delivery_note, delivery_note_id, backfill}`, `note` rỗng. Quét tên/SĐT/địa chỉ/khoá tiền (`cost`, `rate`, `amount`): 0 |
| S3-AC3 | ✅ | Chạy lần hai: "Đã chuyển 0 đơn", số audit không đổi; `--dry-run` sau đó "Sẽ chuyển 0 đơn" |
| S3-AC4 | ✅ | `--dry-run` in danh sách mã đơn (4 mã), "Chưa ghi gì"; so DB (đơn + số audit) trước/sau: không đổi; output không có SĐT/tên/địa chỉ/số tiền |
| S3-AC5 | ✅ | Hoá đơn của X lùi 40 ngày (kỳ 08). Lãi lỗ kỳ 07..10 (API), lãi lỗ mọi lô (API), `revenue_today`, số dòng và id lớn nhất của hoá đơn/chứng từ đảo/phiếu hoàn/sổ kho: **trùng khớp** trước/sau, cả lượt 1 và lượt 2 (lượt 2 có thêm 3 đơn đã hoàn tiền REFUNDED/FAILED) |
| S3-AC6 | ✅ | Đơn M (P1 `COMPLETED`, P2 `DELIVERING`) giữ `PROCESSING` |
| S3-AC7 | ✅ | Giả lập lỗi ở đơn thứ hai trong shell (mock `complete_order_if_delivered` ném lỗi): đơn đầu đã chuyển, đơn lỗi rollback (không audit), lệnh ném `CommandError` "Lỗi ở đơn <mã>… chạy lại để làm nốt"; chạy lại chuyển nốt đúng 2 đơn còn lại. ⏸ phần "exit khác 0" ở mức tiến trình (xem cuối) |
| S3-AC8 | ✅ | Quét resolver Django: 512 URL, không route nào chứa `backfill`. Owner GET/POST 5 đường dẫn đoán (`orders/backfill/`, `backfill-completed-orders/`, …) và `orders/{id}/complete/` đều 404/405; ẩn danh 401/404 |
| S4-AC1 | ✅ | Lô chỉ có đơn `COMPLETED`: owner chốt 200, audit `close_batch` |
| S4-AC2 | ✅ | Lô có đơn `PROCESSING` + phiếu FAILED: 400 `BR-LO-04` "Còn 1 đơn đang mở…", cả trước lẫn sau khi chạy S3 |
| S4-AC3 | ✅ | Lô có đơn kẹt (phiếu xong, đơn `PROCESSING`): chốt trước S3 → 400 `BR-LO-04`; chạy S3; chốt lại → 200, lô `CLOSED` |
| S4-AC4 | ✅ | Manager, kho, giao → 403 (lô không đổi); ẩn danh 401 |
| S4-AC5 | ✅ | Manager và kho xem lô (chi tiết + danh sách): không có `purchase_rate`, `landed_unit_cost`, `unit_cost`, lãi lỗ. Owner (đối chứng) thấy |
| S5-AC1 | ✅ | Đơn `COMPLETED`, đã thu 540.000: manager lập 200.000 → 201 `PENDING`, đơn giữ `COMPLETED` |
| S5-AC2 | ✅ | Owner xác nhận → `REFUNDED`, đơn giữ `COMPLETED`. Kỳ 07, 08, 09 **không đổi**; kỳ 10 đổi (`refunds` 0 → 200.000, `refund_count` 0 → 1, lợi nhuận −200.000). Không thêm chứng từ đảo, không thêm bút toán kho |
| S5-AC3 | ✅ | Hoàn toàn phần 540.000 (lập + xác nhận): đơn vẫn `COMPLETED` |
| S5-AC4 | ✅ | Đã hoàn 400.000/540.000, lập thêm 200.000 → 400 `BR-HT-04`, không tạo phiếu |
| S5-AC5 | ✅ | Owner và manager huỷ đơn `COMPLETED` → 400 `BR-GH-05`; không chứng từ đảo mới |
| S5-AC6 | ✅ | Kho, giao lập phiếu hoàn → 403, 0 phiếu tạo; ẩn danh 401 |
| S5-AC7 | ✅ | Manager, kho xác nhận hoàn → 403 |
| S5-AC8 | ✅ | Đơn `COMPLETED` còn hoàn được: manager có `create_refund`, không có `cancel`; kho không có `create_refund`; còn hoàn = 0 (đã hoàn hết, kể cả đang chờ): không có `create_refund` và không có `cancel` |
| S7 `refund_summary` | ✅ | Xem bảng dưới |

### `refund_summary` (GET `/api/sales/orders/{id}/`)
| Tổ hợp | Kết quả |
|---|---|
| Không phiếu (đơn `COMPLETED`, `PROCESSING`, `BOOKED` chưa có hoá đơn) | `{"refunded_amount":"0","pending_amount":"0"}`, cả hai là chuỗi |
| Chỉ `PENDING` 200.000 | `refunded "0"`, `pending "200000"` |
| `REFUNDED` 200.000 | `refunded "200000"`, `pending "0"` |
| Chỉ `FAILED` 150.000 | `"0"`/`"0"`; phiếu vẫn nằm trong `refunds[]`; manager vẫn có `create_refund` để lập lại |
| Hỗn hợp REFUNDED 200.000 + PENDING 100.000 + FAILED 50.000 | `refunded "200000"`, `pending "100000"` (FAILED bỏ) |
| Hoàn toàn phần | `refunded "540000"`, `pending "0"` |
| Khoá | luôn đúng 2 khoá tiền, mọi vai (owner, manager, kho, giao); không có trong danh sách đơn (chỉ ở chi tiết) |

### Ngoại lệ & biên (ngoài đường thuận)
- Dữ liệu đã có giao dịch: 3 đơn kiểu cũ đã có phiếu hoàn (REFUNDED một phần, REFUNDED toàn phần, có phiếu FAILED) → chuyển bù xong số lãi lỗ kỳ/lô và `refund_summary` y nguyên.
- Màn hình cũ / trạng thái đã đổi: chốt lại lô đã `CLOSED` → 400 `BR-LO-05`, không 5xx; chạy S3 lần hai → 0 đơn.
- Job chạy 2 lần: S3-AC3. Lỗi giữa chừng rồi chạy lại: S3-AC7.
- Bấm đúp lập hoàn (cùng `request_id`): lần 1 201, lần 2 200 `duplicate`, cùng một phiếu; `pending` chỉ cộng 1 lần.
- Hai tình huống đa phiếu: M ở S3-AC6; hoàn FAILED rồi lập lại.
- ⏸ (1) Mã thoát tiến trình khác 0 khi lỗi: kiểm qua `CommandError` (Django chuyển thành exit 1), chưa kiểm bằng lỗi thật ở tiến trình con. (2) Hai lần chạy lệnh đồng thời: chưa thử (mỗi đơn một giao dịch + khoá dòng theo thiết kế; SQLite không đua tin cậy).
- Ghi chú về kiểm thử: lần đầu 8 kiểm của tôi báo FAIL do tôi đặt sai kỳ vọng (không phải lỗi sản phẩm): lô thử cũng có 2 đơn kẹt nên lệnh chuyển 4 chứ không phải 2; audit của đường giao xong (S1) có sẵn từ lúc dựng dữ liệu; đơn M cũng là ứng viên (lọc thô) nên đơn thứ hai không phải đơn "lỗi" như dự tính. Đã sửa kỳ vọng và kiểm lại, đều khớp hành vi đặc tả.

### Phân quyền
| Hành động | owner | manager | warehouse_staff | delivery_staff | Chưa đăng nhập |
|---|---|---|---|---|---|
| Chốt lô | 200 | 403 | 403 | 403 | 401 |
| Lập phiếu hoàn | 201 | 201 | 403 | 403 | 401 |
| Xác nhận hoàn | 200 | 403 | 403 | (không thử) | — |
| Huỷ đơn `COMPLETED` | 400 BR-GH-05 | 400 BR-GH-05 | — | — | — |
| Xem chi tiết đơn | 200 | 200 | 200 | 200 (đơn mình), 404 (đơn người khác) | 401 |
| Chuyển bù qua HTTP | không có route | không có route | không có route | không có route | 401/404 |

### Rò giá vốn
Chi tiết đơn (manager, kho, giao) không có `purchase_rate`, `landed_unit_cost`, `unit_cost`, lãi lỗ; owner có `unit_cost` ở `allocations` (đối chứng, đúng thiết kế). Chi tiết và danh sách lô cho manager, kho: sạch.
Khoá mới: `refund_summary` chỉ gồm tổng tiền hoàn (không phải giá vốn, không tính ngược được giá vốn); audit chuyển bù chỉ có mã phiếu giao, không có tiền/kg.

### Rò dữ liệu cá nhân
- Output lệnh (dry-run, chạy thật, lỗi): chỉ mã đơn; quét SĐT/tên/địa chỉ: 0.
- Audit chuyển bù (4 dòng ở lượt 1, 11 sau tất cả lượt): 0 dữ liệu cá nhân.
- `refund_summary` chỉ 2 khoá tiền. NV giao với đơn quá cửa sổ (completed_at lùi 40 ngày): `customer` = `{name,phone,address: null}`, `customer_hidden_reason: "expired"`, `refund_summary` vẫn có; quét cả phản hồi: không tên/SĐT/địa chỉ. Trong cửa sổ NV giao thấy khách như cũ (đúng thiết kế); NV giao không được gán → 404.
- Log `runserver` cả phiên: 0 dòng chứa SĐT/tên/địa chỉ giả.

### Hồi quy
`manage.py test apps.sales.orders apps.sales.refunds apps.inventory.batches.tests.test_close_after_completion apps.sales.orders.tests.test_backfill_completed_orders`: 304 test OK. (Điều phối viên đã chạy toàn bộ 3182 test OK.)

### Lỗi
Không có lỗi chặn.

### Lệnh đã chạy
- `migrate` + seed qua `manage.py shell` (SQLite tạm), `runserver 8791 --noreload`.
- Các kịch bản HTTP + `manage.py backfill_completed_orders [--dry-run]` bằng `urllib`/`subprocess` (script trong scratchpad).
- `manage.py test` (4 module trên): `Ran 304 tests ... OK`.

---

## QA L3 (08/10) — S7 chi tiết đơn và dòng thời gian, S8 Shop tra đơn (BE + FE, bản build thật)
### Kết luận: APPROVED — S7 và S8 chạy đúng trên runserver thật; mock không lọt vào bản build thật; không lỗi chặn
### Tổng: 97 ca · ✅ 96 · ❌ 0 · ⏸ 1 (xem dưới) · 1 ghi nhận Low (S6-AC1 lời văn "mặc định")
Dữ liệu 100% giả (SĐT 0900005xxx, "Khách Giả QA"). Môi trường: runserver `127.0.0.1:8792` (worktree này, `DJANGO_DEBUG=1`, SQLite tạm), ERP và Shop build `NEXT_PUBLIC_USE_MOCK=0` trỏ vào runserver, Playwright headless. Đơn dựng bằng service thật: A (id 7) hoàn tất qua giao xong, có phiếu hoàn REFUNDED 200.000 + PENDING 100.000; A2 (id 8) hoàn tất, chỉ PENDING 50.000; B (id 9) kẹt kiểu cũ, không có audit giao; D (id 13) kẹt kiểu cũ, có audit giao cũ; C (id 10) PROCESSING với phiếu FAILED.

### Theo yêu cầu
| Việc | Kết quả | Bằng chứng |
|---|---|---|
| 1. ERP chi tiết đơn Hoàn tất (S7-AC1, AC4, AC5, AC6) | ✅ | Chip "Hoàn tất"; thanh 5 bước (Giữ chỗ, Chờ gọi xác nhận, Soạn hàng, Đang giao, Hoàn tất) bốn bước đầu có dấu tick, bước cuối sáng đặc, không có "Đã thanh toán"; dòng "Đã hoàn 200.000 đ · Chờ hoàn 100.000 đ" đúng; nút chính "Lập phiếu hoàn tiền"; menu "…" không có "Huỷ đơn"; đúng 1 mốc "Đã giao — đơn hoàn tất (GH-INV261007-2A18FF-36C8F)", không còn "Giao hàng thành công". Ảnh `l3_erp_detail_completed_1280.png`, `_360.png` |
| 1b. Phần bằng 0 bị bỏ (S7-AC5 biên) | ✅ | A2 chỉ có PENDING: dòng "Chờ hoàn 50.000 đ", không có "Đã hoàn". `l3_erp_detail_pending_only.png` |
| 2. Chuyển bù (S7-AC7, S3) | ✅ | `backfill_completed_orders --dry-run` in 1 đơn, chưa ghi. Chạy thật: "Đã chuyển 1 đơn" (BF568A). Đơn D có audit giao cũ: mốc "Giao hàng thành công (GH-…)" giữ nguyên và thêm "Hệ thống chuyển đơn sang Hoàn tất (chuyển bù)" (Hệ thống); không lẫn "Đã giao — đơn hoàn tất". Đơn B không có audit cũ: chỉ có mốc chuyển bù, đúng 1. Chạy lần 2: "Đã chuyển 0 đơn", mốc không nhân đôi. `l3_erp_detail_backfilled_1280.png` |
| 3. Shop tra đơn (S8-AC1..AC6) | ✅ | Thật: A → 200 `status_label "Hoàn tất"`, `delivery {COMPLETED, "Đã giao"}`; C → "Đang xử lý" / "Giao chưa thành công, vựa sẽ liên hệ lại"; đúng bộ khoá như đơn khác. UI 390/360/1280px: badge "Hoàn tất", dòng "Đã giao", không mã thô (COMPLETED/PROCESSING/...), không cuộn ngang. Sai 4 số: 404 `Không tìm thấy đơn…`, UI hiện "Không tìm thấy đơn hàng phù hợp", không badge. Quá ngưỡng: tra 40 lần sai liên tiếp → từ lần 2 trả 429 (`throttled`), kể cả với 4 số đúng. Thiếu `phone_last4` → 400. `l3_shop_completed_390.png` |
| 4. Nhật ký | ✅ | Trang Nhật ký hiện "Đơn hoàn tất", không lộ `complete_order` thô. `l3_erp_audit_1280.png` |
| 5. Bản build thật sạch mock | ✅ | `grep -rlE "cave_erp_mock\|Anh Ph\|Anh Lâm\|Anh Kh" erp-console/out` rỗng (exit 1). Shop `out/` quét `cave_erp_mock\|DH-DEMO0`: rỗng. Màn ERP trên bản thật nhận đơn từ API (mã đơn thật SO2610…), không còn dữ liệu seed mock |
| 6. Mock=1 | ✅ | ERP `order_completion_detail` 16/16; `order_completion_erp` 6/6; `ed_batch3_orders` 143/143; `ed_batch4_delivery` 70/70. Shop `order_lookup_completed` 4/4; `order_lookup_no_raw_codes` 19/19 |
| 7. 360px, 1280px, ngoài đường thuận | ✅ | Chi tiết đơn Hoàn tất và đơn chuyển bù 360px không cuộn ngang; Shop 360/390/1280 không cuộn ngang. Ngoài đường thuận: dữ liệu cũ kẹt (B, D), chạy job 2 lần, phần tiền bằng 0, đơn PROCESSING có phiếu FAILED, tra sai 4 số, vượt giới hạn tần suất, phân quyền |

### Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| S7-AC1 | ✅ | Playwright, ảnh |
| S7-AC2 | ✅ | Đơn C: chip "Đang xử lý", không nút "Lập phiếu hoàn tiền", bước không tới Hoàn tất |
| S7-AC3 | ✅ | vitest ERP 95 file, 1070 test xanh (gồm bảng `orderStepKey`) |
| S7-AC4 | ✅ | Manager (có `create_refund`) thấy nút; menu "…" không có "Huỷ đơn" |
| S7-AC5 | ✅ | Hỗn hợp, chỉ PENDING |
| S7-AC6 | ✅ | Đúng 1 mốc, kèm mã phiếu |
| S7-AC7 | ✅ | Đơn B, D |
| S7-AC8 | ✅ | `qa_kho` mở đơn Hoàn tất: không nút hoàn tiền; API `available_actions` rỗng |
| S7-AC9 | ✅ | `GET /api/sales/orders/7/` khoá `timeline` với 4 vai: không SĐT, tên, địa chỉ; không `complete_order`, `delivery_note_id`, `changes` |
| S7-AC10 | ✅ | Manager/kho/giao: không `unit_cost`, `purchase_rate`, `landed_unit_cost`, lãi lỗ; cột giá vốn trên màn hiện "(cột giới hạn quyền xem)" |
| S8-AC1..AC6 | ✅ | Xem hàng 3 |
| S8-AC7 | ✅ | Ẩn danh `GET /api/sales/orders/7/` → 401; ẩn danh `POST /api/delivery/notes/1/status/` → 401/403 |
| S6 (hồi quy trên bản thật) | ✅ | Lọc "Chưa xong" loại cả 4 đơn Hoàn tất, giữ đơn C; lọc "Hoàn tất" ra 4 đơn, chip "Hoàn tất" mỗi dòng; không có "Đã thanh toán" trong lựa chọn; đơn `PAID` cũ do seed vẫn hiện chip "Đã thanh toán" (S6-AC4). S6-AC7: `qa_giao` mở `/orders/detail/` nhận "Bạn không có quyền xem mục này" |

### Phân quyền (đơn Hoàn tất)
| Hành động | owner | manager | warehouse_staff | delivery_staff | Chưa đăng nhập |
|---|---|---|---|---|---|
| Xem chi tiết đơn (API) | 200 | 200 | 200 | 200 (đơn mình giao) | 401 |
| Xem chi tiết trên màn ERP | có | có | có | không (màn "Không có quyền", dùng "Việc giao của tôi") | — |
| `available_actions` có `create_refund` | có | có | không | không | — |
| Nút "Lập phiếu hoàn tiền" | có | có | không | không | — |
| Đổi trạng thái phiếu giao | — | — | — | — | 401/403 |

### Rò giá vốn
Chi tiết đơn Hoàn tất (4 vai): sạch với manager, kho, giao. `refund_summary` chỉ 2 khoá tiền hoàn. Audit `complete_order`: `changes` chỉ có `status {from,to}`, `delivery_note` (mã phiếu), `delivery_note_id`, và `backfill: "W37"` với đơn chuyển bù; `note` rỗng. Không có tiền hay kg nên không tính ngược ra giá vốn được; không tên/SĐT/địa chỉ.

### Rò dữ liệu cá nhân
- Shop tra đơn: phản hồi không có tên, SĐT, địa chỉ, người giao; bộ khoá không đổi so với đơn chưa Hoàn tất (`order_code, status, status_label, total_amount, lines, delivery, booked_expires_at, cancel_notice`). Có giới hạn tần suất (429).
- URL, `localStorage`, `sessionStorage` (Shop và ERP) không chứa SĐT, tên, địa chỉ. ERP chỉ giữ `cave_erp_token`, `cave_erp_last_user`, `cave_erp_signed_in_at`.
- Log runserver cả phiên (312 dòng): 0 dòng chứa SĐT/tên/địa chỉ giả. Output `backfill_completed_orders` (dry-run, thật, lần 2): chỉ mã đơn.
- Console: ERP không lỗi (bỏ qua nhiễu "Failed to fetch RSC payload" của máy chủ tĩnh `http.server`). Shop chỉ có dòng "Failed to load resource 404" của trình duyệt khi cố ý tra sai 4 số.
- Ảnh chụp dùng dữ liệu giả; thư mục `shots/` bị `.gitignore` nên ảnh không vào repo.

### Hồi quy
`manage.py test apps.sales.orders apps.delivery apps.sales.refunds`: 689 test OK (2 skipped). ERP: `tsc --noEmit` exit 0; `npm test` 1070 test xanh. Điều phối viên đã chạy BE toàn bộ 3228 OK và build mock=0.

### Ghi nhận (không chặn)
- **N1 (Low, S6-AC1, lời văn):** ô lọc trạng thái trên `/orders/` mở ra với "Mọi trạng thái" (10 đơn gồm đơn Hoàn tất), không phải "Chưa xong" như S6-AC1 ghi "bộ lọc mặc định". Chọn "Chưa xong" thì kết quả đúng. Mã chưa đổi từ L1 (QA L1 FE đã duyệt theo nghĩa "có lựa chọn"). Đề nghị PO chốt: sửa lời văn AC hoặc đổi mặc định.
- **N2 (dữ liệu seed, không phải lỗi L3):** đơn `DH-2609-115` do `seed_demo` có chip "Hoàn tất" nhưng giao hàng "Chờ xác nhận". Là dữ liệu mẫu cũ, không sinh từ luật hoàn tất.
- ⏸ Không kiểm: hai lần chạy `backfill_completed_orders` đồng thời (SQLite không đua tin cậy; giữ nguyên ghi chú của QA L2).

### Lỗi
Không có lỗi chặn.

### Lệnh đã chạy
- `manage.py migrate`, `seed_demo`, `manage.py shell` (dựng đơn A, A2, B, C, D bằng service thật), `runserver 127.0.0.1:8792`.
- `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8792 NEXT_PUBLIC_USE_MOCK=0 npm run build` ở `erp-console` và `frontend`: exit 0; grep sạch mock.
- Playwright (script trong scratchpad): ERP 3 lượt (owner, manager, kho, giao; 1280 và 360px), Shop 3 độ rộng; `urllib` cho API 4 vai.
- `NEXT_PUBLIC_USE_MOCK=1 npm run build` cả hai; 6 kịch bản e2e mock như hàng 6.
- `manage.py test apps.sales.orders apps.delivery apps.sales.refunds` (689 OK); `tsc --noEmit`; `npm test`.
- Đã dọn: tắt server theo PID, xoá `out/`, `.next`, `db.sqlite3`, symlink `.env`, `staticfiles`, `node_modules`.
