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
