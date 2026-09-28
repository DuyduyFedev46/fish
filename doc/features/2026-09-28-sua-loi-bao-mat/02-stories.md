# Sửa lỗi bảo mật có sẵn (L-1, L-3, L-5, L-6, robots staging) + L-10 lãi lỗ theo lô
> Claude (Tech Lead thay PO, luồng NHANH) · 2026-09-28 · Trạng thái: **ĐÃ DUYỆT (Duy 28/09, luồng NHANH)**
> Nguồn: `doc/features/2026-09-28-ai-digital-worker/02b-tech-design.md` §14 (L-1…L-9, đã đối chiếu code 28/09).
> Duy chốt 28/09: phase này làm **đầu tiên**, trước mọi hồ sơ khác. Lô 2 QA APPROVED → merge `wip/autosave` vào `main`.
> Thiết kế: `02b-tech-design.md` · Giao việc: `02c-giao-viec.md`.
> **S06 (L-10) thêm ngày 28/09, Duy duyệt** (trả lời "ok" cho đề xuất sửa công thức lãi lỗ theo lô). Làm ở Lô 3, trên `main` sau khi Lô 2 merge.

Không có tính năng mới, không đổi schema. Mỗi lỗi một story (S06 sửa công thức nghiệp vụ, không phải lỗi bảo mật, gom vào đây vì cùng đợt sửa lỗi có sẵn). "Group" = 4 Group seed sẵn `chu`, `quan_ly`,
`nv_kho`, `nv_giao`; "khách" = gọi không đăng nhập. Dữ liệu trong test chỉ dùng số giả (vd SĐT `0900000000`).

| Story | Lỗi | Mức | Lô |
|---|---|---|---|
| S01 | L-3 Nhật ký hành động lộ giá vốn cho Quản lý | Critical | 1 |
| S02 | L-6 Tra đơn Shop dò được mã đơn và đoán được SĐT | Cao | 1 |
| S03 | L-5 Không có giới hạn tần suất ở endpoint công khai | Cao | 1 |
| S04 | L-1 Chốt lô thiếu kiểm BR-LO-04/BR-KK-05 và thiếu khoá | Cao | 2 |
| S05 | Trang staging bị máy tìm kiếm index | Trung bình | 2 |
| S06 | L-10 Lãi lỗ theo lô tính hao hụt/hàng hỏng hai lần | Cao (sai con số lời lỗ) | 3 |

L-2 (huỷ lô quá hạn, BR-LO-03) **không làm trong hồ sơ này**, xem mục "Việc sau".

---

## S01 — Nhật ký hành động không lộ giá vốn (L-3, bất biến 1, BR-PQ-13, BR-GV-03)
**Là** Chủ, **tôi muốn** Quản lý xem được nhật ký hành động mà không thấy giá vốn, **để** giữ quy tắc "chỉ Chủ biết giá vốn".

Hiện trạng: `GET /api/audit-logs/` trả nguyên `changes` (`backend/apps/accounts/audit/serializers.py:26`). Quản lý có
`accounts.view_auditlog` nhưng không có `inventory.view_costprice`, nên đọc được `landed_unit_cost` do `close_batch`
(`inventory/batches/services.py:166-169`), `recompute_landed_cost` (`:189-192`) và dòng `admin_edit` khi superuser sửa
`purchase_rate`/`landed_unit_cost` trong Admin (`common/admin.py:47`, khoá ở `inventory/admin.py:58-61`) ghi vào.

- **AC1 (Chủ thấy đủ).** Given có dòng `recompute_landed_cost` với `changes={"landed_unit_cost": {"from": "111111.1111", "to": "987654.3210"}}`,
  When user nhóm `chu` gọi `GET /api/audit-logs/`, Then 200 và `changes.landed_unit_cost` của dòng đó còn nguyên `{"from": "111111.1111", "to": "987654.3210"}`.
- **AC2 (Quản lý không thấy giá vốn).** Given các dòng `close_batch`, `recompute_landed_cost` và `admin_edit` có khoá
  `landed_unit_cost`/`purchase_rate`, When user nhóm `quan_ly` gọi `GET /api/audit-logs/`, Then 200, **không** dòng nào có khoá
  thuộc danh sách khoá giá vốn ở bất kỳ độ sâu nào của `changes`, và chuỗi JSON response không chứa các con số giá vốn đã ghi (vd `987654.3210`).
  Các khoá không nhạy cảm cùng dòng (vd `status`) vẫn còn.
- **AC3 (theo quyền, không theo tên Group).** Given user nhóm `quan_ly` được cấp thêm trực tiếp `inventory.view_costprice`, When gọi
  `GET /api/audit-logs/`, Then thấy khoá giá vốn như AC1. Superuser cũng thấy.
- **AC4 (phân quyền giữ nguyên).** `nv_kho`, `nv_giao` → 403; chưa đăng nhập → 401 (như S03-AC5 cũ). Lọc `?action=` vẫn chạy.
- **AC5 (một danh sách khoá dùng chung).** Danh sách khoá giá vốn nằm ở **một** chỗ trong `apps/common/` và hàm lọc nhận vào
  `changes` bất kỳ; test đơn vị chứng minh lọc được dict lồng và list chứa dict. Dữ liệu trong bảng `AuditLog` **không bị sửa**
  (append-only, bất biến 4), chỉ lọc khi trả ra.
- **AC6 (không rò PII).** Response không thêm field mới nào; test cũ S03 xanh nguyên.

## S02 — Tra đơn Shop không cho dò mã đơn, không đoán SĐT (L-6, §7.1, bất biến 9)
**Là** khách, **tôi muốn** chỉ người biết mã đơn **và** đúng 4 số cuối SĐT mới xem được đơn, **để** người khác không dò ra đơn của tôi.

Hiện trạng `backend/apps/sales/orders/shop_api.py:64-71`: `phone_last4="3"` vẫn khớp nhờ `endswith`; hai thông điệp 404 khác nhau
("Không tìm thấy đơn." / "Sai mã đơn hoặc số điện thoại.") cho biết mã đơn có tồn tại hay không.

- **AC1 (bắt buộc đúng 4 chữ số).** Given đơn có SĐT kết thúc `5678`, When khách gọi `GET /api/shop/orders/<mã>/?phone_last4=` với
  giá trị `""`, `"8"`, `"678"`, `"05678"`, `"56a8"`, Then 400 `{"detail": "Vui lòng nhập đúng 4 số cuối số điện thoại."}`,
  và response giống hệt nhau dù mã đơn có tồn tại hay không.
- **AC2 (một thông điệp 404).** When gọi với mã đơn không tồn tại + `0000`, và với mã đơn có thật + `0000`, Then cả hai 404 với **cùng**
  body `{"detail": "Không tìm thấy đơn với mã và số điện thoại này."}`.
- **AC3 (đúng thì xem được).** When gọi với mã đúng + `5678`, Then 200 và body có đúng các khoá `order_code, status, status_label,
  total_amount, lines, delivery, booked_expires_at` — **không** có tên, SĐT, địa chỉ (so tập khoá bằng `assertEqual(set(...))`).
- **AC4 (SĐT có dấu cách/ký tự).** Given đơn lưu SĐT `0900 000 678` hoặc `+84900000678`, When tra với `0678`, Then 200 (so trên
  chữ số của SĐT, không so chuỗi thô).
- **AC5 (thanh toán Shop).** `POST /api/shop/orders/<mã>/checkout/` với mã không tồn tại trả 404 cùng thông điệp chung của AC2
  (thay "Không tìm thấy đơn."); response 200 vẫn không có tên/SĐT/địa chỉ (P1-AC6 giữ nguyên).
- **AC6 (phân quyền).** Endpoint vẫn công khai; user đã đăng nhập bất kỳ Group nào gọi cũng theo đúng AC1–AC3 (không có đường tắt
  xem đơn không cần 4 số).

## S03 — Giới hạn tần suất endpoint công khai (L-5, bất biến 9)
**Là** Chủ, **tôi muốn** hệ thống chặn người gọi dồn dập vào trang tra đơn, đặt đơn, thanh toán và đăng nhập, **để** không ai dò
mật khẩu hay dò đơn của khách được.

Hiện trạng: `REST_FRAMEWORK` (`backend/config/settings.py:183-197`) không có throttle; grep `throttle` trong backend = 0.

- **AC1 (tra đơn).** Given mức `shop_lookup_ip` = 5/phút (đặt trong test), When cùng một IP gọi `GET /api/shop/orders/<mã>/` lần
  thứ 6 trong 1 phút, Then 429 `{"detail": "Bạn thao tác quá nhanh. Vui lòng thử lại sau <n> giây.", "code": "throttled"}` và có
  header `Retry-After`. Given mức `shop_lookup_order` = 3/giờ, When 4 IP khác nhau cùng tra **một** mã đơn, Then lần thứ 4 trả 429
  (chặn dò 4 số từ nhiều IP).
- **AC2 (đặt đơn, thanh toán, đăng nhập).** Tương tự AC1 cho `POST /api/shop/orders/` (`shop_order_create`),
  `POST /api/shop/orders/<mã>/checkout/` (`shop_checkout`), `POST /api/auth/token/` (`login_ip` theo IP và `login_user` theo tên
  đăng nhập). Request bị chặn **không** tạo đơn, không giữ chỗ, không sinh token (đếm `SalesOrder`/`Token` trước/sau bằng nhau).
- **AC3 (mức cấu hình được).** Mức mỗi scope đọc từ env (bảng ở `02b` §3), có mặc định trong `settings.py`; đổi env không cần sửa code.
  Mức `None`/rỗng = tắt scope đó.
- **AC4 (không làm vỡ test cũ).** Khi chạy `manage.py test`, mọi scope mặc định tắt; chỉ test throttle bật bằng `override_settings`.
  Toàn bộ suite cũ xanh.
- **AC5 (không đụng back-office).** User nhóm `chu`/`quan_ly`/`nv_kho`/`nv_giao` gọi endpoint back-office (vd `GET /api/audit-logs/`,
  `GET /api/inventory/batches/`) 50 lần liên tiếp → không có 429. Endpoint công khai thì throttle **cả** khi đã đăng nhập.
- **AC6 (không giả IP, không rò PII).** Hai request có header `X-Forwarded-For` giả khác nhau ở phần đầu nhưng cùng IP thật ở cuối
  bị đếm chung (theo `NUM_PROXIES`). Không ghi IP, SĐT, tên đăng nhập vào log; khoá cache của `login_user` là băm, không phải tên thô.

## S04 — Chốt lô đủ điều kiện và an toàn khi chạy đồng thời (L-1, BR-LO-04, BR-LO-05, BR-KK-05)
**Là** Chủ, **tôi muốn** chỉ chốt được lô khi không còn đơn mở và đã kiểm kê, **để** lãi lỗ đông cứng là số đúng.

Hiện trạng `backend/apps/inventory/batches/services.py:148-170`: không kiểm đơn mở, không kiểm kiểm kê, không `transaction.atomic`,
không `select_for_update`. BR-KK-05 là giả định *(PA)* trong spec; Duy chốt áp dụng khi duyệt phase này (28/09).

- **AC1 (còn đơn mở → chặn).** Given lô tồn 0 có `SalesOrderLineBatch` thuộc đơn ở trạng thái `BOOKED`, `PAID` hoặc `PROCESSING`,
  When `chu` gọi `POST /api/inventory/batches/<id>/close/`, Then 400 `code="BR-LO-04"`, thông điệp nêu số đơn mở (không nêu tên/SĐT
  khách), lô giữ nguyên trạng thái, không có AuditLog `close_batch`. Đơn `COMPLETED`/`CANCELLED`/`AUTO_CANCELLED` không chặn.
- **AC2 (còn giữ chỗ hoặc hàng hoàn chờ duyệt → chặn).** Given `qty_reserved > 0`, hoặc có `ReturnToStock` trạng thái `DRAFT` trỏ vào
  lô, Then 400 `code="BR-LO-04"` (lô chốt không nhận hàng hoàn về — BR-LO-05).
- **AC3 (chưa kiểm kê → chặn).** Given lô không có dòng kiểm kê nào thuộc phiếu `APPROVED`, hoặc đang có phiếu kiểm kê `DRAFT`
  chứa lô, Then 400 `code="BR-KK-05"` "Lô phải được kiểm kê và duyệt trước khi chốt (BR-KK-05)."
- **AC4 (đủ điều kiện → chốt).** Given tồn 0, không đơn mở, có Purchase Invoice (nếu lô từ phiếu nhập), có phiếu kiểm kê đã duyệt,
  When `chu` chốt, Then 200, `status=CLOSED`, `closed_by`=chu, 1 dòng AuditLog `close_batch`. Chốt lần hai → 400 "Lô đã chốt."
- **AC5 (khoá đồng thời).** Hàm chạy trong `transaction.atomic` và lấy lô bằng `select_for_update()` **trước** mọi phép kiểm; mọi
  phép kiểm đọc trên bản ghi vừa khoá. Test chứng minh: lô được chốt xong thì `allocate_fefo` không lấy được lô đó nữa.
- **AC6 (phân quyền, không rò giá vốn).** `quan_ly`, `nv_kho`, `nv_giao` → 403, lô không đổi; chưa đăng nhập → 401. Response
  400 của các lỗi trên không chứa `landed_unit_cost`/`purchase_rate`; dòng AuditLog `close_batch` đọc bằng `quan_ly` vẫn bị lọc (S01).

## S05 — Staging không bị máy tìm kiếm index, production không đổi
**Là** Duy, **tôi muốn** Google không index hai trang staging, **để** khách không lạc vào Shop thử (thanh toán sandbox, dữ liệu giả).

- **AC1 (Shop staging).** Given deploy bằng `frontend/firebase.staging.json`, When `curl -sI https://cangca-loc-staging.web.app/shop/`,
  Then có header `X-Robots-Tag: noindex, nofollow` (áp cho mọi đường dẫn `**`, kể cả `/robots.txt` và `/_next/static/**`).
- **AC2 (ERP staging).** Như AC1 với `erp-console/firebase.staging.json` và `https://cangca-erp-staging.web.app/`.
- **AC3 (production không bị chặn).** `frontend/firebase.json` và `erp-console/firebase.json` **không đổi** (`git diff` rỗng); Shop
  production không có `X-Robots-Tag` noindex và không có meta `robots` noindex. (ERP đã có sẵn meta noindex ở mọi môi trường —
  `erp-console/app/layout.tsx:33` — giữ nguyên, ERP là trang nội bộ.)
- **AC4 (kiểm trước deploy).** Hai file staging parse được JSON, header `Cache-Control` của `/_next/static/**` ở Shop staging vẫn còn;
  `npm run build` hai app sạch. Kiểm bằng `curl` sau deploy là việc của Duy khi deploy staging (ghi trong `03-dev-notes.md`).

## S06 — Lãi lỗ theo lô không tính hao hụt/hàng hỏng hai lần (L-10, BR-BC-04, BR-BC-05, BR-KK-03, BR-GV-01)
**Là** Chủ, **tôi muốn** lãi lỗ của một lô bằng đúng tiền bán trừ tiền đã bỏ ra cho lô, **để** không đọc nhầm lô có lãi thành lô lỗ.

Hiện trạng `backend/apps/reports/services.py:46-66` (`batch_pnl`): `total_cost = purchase_cost + allocated_cost + shrinkage_cost +
damage_cost`. `purchase_cost = purchase_rate × qty_received` đã gồm cả số kg sau đó hao hụt hoặc hỏng, nên hai khoản này bị trừ hai lần.
Công thức sai nằm trong spec §12.1 và `doc/BUILD-PLAN.md:147`.
**Quyết định Duy 28/09:** Lãi/lỗ theo lô = doanh thu bán từ lô − (giá mua + chi phí phân bổ). Hao hụt và hàng hỏng vẫn trả riêng (số kg
và giá trị = kg × `landed_unit_cost` hiện hành) để Chủ biết mất bao nhiêu, nhưng **không** cộng vào `total_cost`. BR-BC-04 sửa theo.

- **AC1 (ví dụ Duy, hao hụt).** Given lô nhận 100 kg, `purchase_rate` 100.000, không chi phí phân bổ (`landed_unit_cost` 100.000), đã bán
  90 kg giá 150.000, kiểm kê ghi `RECONCILE` −10 kg. When gọi `batch_pnl`, Then `revenue` = 13.500.000, `purchase_cost` = 10.000.000,
  `allocated_cost` = 0, `shrinkage_qty` = 10, `shrinkage_cost` = 1.000.000, `total_cost` = 10.000.000, `profit` = **3.500.000**
  (không phải 2.500.000).
- **AC2 (hàng hỏng + chi phí phân bổ).** Given lô nhận 100 kg × 80.000, chi phí phân bổ 200.000 (`landed_unit_cost` 82.000), bán 60 kg
  giá 120.000, hao hụt −2 kg, hàng hỏng 3 kg (`ReturnToStock` `WRITE_OFF` `APPROVED`). Then `revenue` = 7.200.000, `shrinkage_cost` =
  164.000, `damage_qty` = 3, `damage_cost` = 246.000, `total_cost` = **8.200.000**, `profit` = **−1.000.000** (trước đây 8.610.000 và
  −1.410.000). Phiếu hàng hỏng `DRAFT` hoặc quyết định khác `WRITE_OFF` không vào `damage_qty`.
- **AC3 (bất biến công thức).** Với mọi lô: `total_cost == purchase_cost + allocated_cost` và `profit == revenue − total_cost`; thêm một
  dòng hao hụt hay một phiếu hàng hỏng **không** làm đổi `total_cost`, chỉ đổi `shrinkage_*`/`damage_*` (test so trước/sau trên cùng lô).
- **AC4 ("tạm tính").** Lô chưa `CLOSED` → `provisional: true`; lô `CLOSED` → `false`. Công thức AC1 áp dụng giống nhau cho cả hai
  (không có nhánh công thức riêng cho lô chưa chốt).
- **AC5 (contract không đổi hình dạng).** Response `GET /api/reports/batch/<batch_id>/` giữ **đúng 14 khoá** hiện có (`batch_id`,
  `provisional`, `qty_received`, `qty_sold`, `landed_unit_cost`, `revenue`, `purchase_cost`, `allocated_cost`, `shrinkage_qty`,
  `shrinkage_cost`, `damage_qty`, `damage_cost`, `total_cost`, `profit`), không thêm, không bỏ, không đổi tên. Chỉ đổi ý nghĩa
  `total_cost` (= giá mua + chi phí phân bổ) và `profit`. Các khoá còn lại cùng giá trị như trước với cùng dữ liệu.
- **AC6 (phân quyền, không rò giá vốn).** `chu` → 200 đủ 14 khoá. `quan_ly`, `nv_kho`, `nv_giao` → 403 và body không chứa
  `landed_unit_cost`, `purchase_cost`, `profit`; chưa đăng nhập → 401. Lô không tồn tại với `chu` → 404.
- **AC7 (nơi khác dùng công thức).** `period_pnl` (`/api/reports/period/`) **không đổi** (công thức riêng BR-BC-01..03, không cộng hao hụt/
  hỏng — test cũ giữ nguyên xanh). `/api/dashboard/summary/` không dùng công thức lãi lỗ lô → không đổi. ERP console và Shop hiện **không có
  màn** hiển thị `total_cost`/`profit` theo lô (đã kiểm 28/09: không có `reports/batch` trong `erp-console/`, `frontend/`) → không sửa FE;
  mô tả lệnh AI `bao_cao_lo` ở `erp-console/features/ai/mock.ts` không nêu công thức → không sửa. Tài liệu còn ghi công thức cũ
  (`doc/BUILD-PLAN.md:147`, docstring `batch_pnl`) sửa theo công thức mới.

---

## Việc sau (không làm trong hồ sơ này)
- **L-2 huỷ lô quá hạn (BR-LO-03)**: cần quyết định quyền Tầng 2 (dùng `close_batch` hay perm mới + data migration), API, nút trên ERP
  và dòng "lỗ hàng hết hạn" trong báo cáo → không đơn giản. Để ở Lô 1 của `2026-09-28-ai-digital-worker` như đã định.
  Hệ quả tạm thời: `close_batch` vẫn cho chốt lô `EXPIRED` còn tồn như code cũ (điều kiện "đã huỷ phần còn lại" chưa có service).
- Throttle dùng cache trong bộ nhớ của từng worker (3 worker gunicorn × số instance) → mức thật cao hơn cấu hình. Chuyển sang cache
  dùng chung (Redis/DB) khi bật lại production nhiều instance.
- Throttle `/admin/login/` và `/api-auth/login/` (không đi qua DRF).
- Checkout Shop chưa đòi 4 số cuối SĐT (đổi contract FE, P1-AC6) — cân nhắc khi go-live.
- L-4, L-7, L-8, L-9: theo hồ sơ `2026-09-28-ai-digital-worker`.
- (Tech Lead thấy khi làm S06, **chưa hỏi Duy**) `batch_pnl` cộng doanh thu từ mọi `SalesInvoiceLineBatch` của lô, kể cả hoá đơn
  `CANCELLED`, và không trừ phiếu hoàn. `period_pnl` không phản ánh hao hụt/hàng hỏng (chỉ giá vốn phần bán). Đề xuất ghi L-11, hỏi Duy riêng.
