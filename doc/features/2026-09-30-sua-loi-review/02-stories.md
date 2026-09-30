# P8 — Sửa lỗi review P1–P7 (bảo mật dữ liệu · tiền/kho/AI · CMS/go-live/FE)
> Claude (Tech Lead thay PO, luồng sửa lỗi) · 2026-09-30 · Trạng thái: **ĐÃ DUYỆT (Duy 30/09)**
> Nguồn: `doc/features/2026-09-30-review-p1-p7/` — `review-bao-mat-du-lieu.md` (BM-01…07), `review-tien-kho-ai.md` (F01…F13),
> `review-cms-golive-fe-qa.md` (F1…F14 + bảng "AC thiếu bằng chứng"); thêm lỗi `npm ci` của `erp-console` do điều phối viên tìm.
> Thiết kế: `02b-tech-design.md` · Giao việc: `02c-giao-viec.md`.
> **Ký hiệu mã nguồn:** `F01…F13` (hai chữ số) = báo cáo tiền/kho/AI; `F1…F14` (một chữ số) = báo cáo CMS/go-live/FE.

## Quyết định của Duy (30/09) — ghi nguyên văn

- **F04**, nguyên văn: *"đề xuất làm sao cho sổ cái OK á, hủy luôn sợ ko ghi được lịch sử"* → KHÔNG đổi/xoá hoá đơn gốc. Thiết kế
  **chứng từ đảo doanh thu** (credit note / điều chỉnh giảm, append-only) gắn hoá đơn gốc, có dòng theo lô + kg + đơn giá (từ phân bổ
  lô của hoá đơn), lập khi huỷ đơn đã thanh toán (kể cả job tự huỷ CSKH) và thống nhất với phiếu hoàn (đối chiếu BR-HT-06 và docstring
  `confirm_refund` — Q12 cũ). `batch_pnl`/`period_pnl`/dashboard: doanh thu = hoá đơn hiệu lực − chứng từ đảo; kg bán ròng tương ứng;
  kg hoàn về kho bán lại không bị cộng hai lần. Đề xuất cập nhật BR-BC-04/BR-HT-06 trong `doc/business-process-spec.md` (ghi "Duy duyệt 30/09").
- **F09**, nguyên văn: *"Này cho quy trình alert và xác nhận đã hủy/ trả"* → bỏ ngoại lệ cho chốt thẳng lô EXPIRED còn tồn. Lô quá hạn
  còn tồn: cảnh báo (khối Cần chú ý / Tiếp theo), người có quyền xác nhận xử lý phần tồn là **Đã huỷ** (dùng DW-06 cancel-expired, ghi lỗ)
  hoặc **Đã trả** (trả lại nhà cung cấp — nghiệp vụ mới: ghi số kg + số tiền NCC hoàn nếu có, bút toán đảo phù hợp giá vốn; ghi rõ là giả
  định thiết kế, dự án mua tại cảng trả tiền ngay — decisions 10/09; nếu thấy quá lớn thì đặt MVP chỉ ghi nhận kg trả không tiền, ghi 🟡).
  Chỉ khi hết tồn mới chốt.
- **Dashboard**: NV kho (và mọi nhóm không cần) chỉ thấy mã đơn, không thấy tên khách — nguyên văn *"Không, chỉ hiện mã đơn"*.
- **Các mục còn lại**: theo đề xuất trong báo cáo review.

Tech Lead áp cho các mục "theo đề xuất" (Duy lật được): F02 chọn **chặn** huỷ lô khi còn giữ chỗ (không tự huỷ đơn khách);
"Đã trả NCC" làm **có ô tiền NCC hoàn** (không phải bản MVP chỉ kg — đánh giá: thêm 1 field tiền + 1 phép trừ trong `batch_pnl`, không
quá lớn; các giả định ghi 🟡 ở 02b §5); dashboard bỏ tên khách và 4 số cuối SĐT với **mọi** nhóm (Chủ/Quản lý xem ở chi tiết đơn).

## Quy ước chung cho mọi story
- **TDD bắt buộc**: với mỗi lỗi, viết test tái hiện trước, chạy thấy **đỏ** (dán output đỏ vào `03-dev-notes.md`), rồi mới sửa cho xanh.
  Các ca R1–R6 của báo cáo tiền/kho (file tạm `review_repro/tests.py` ở scratchpad review) được **chuyển thành test chính thức** như ghi
  ở từng story, bỏ `print`, thay bằng `assert`.
- **Ma trận Group**: `chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh` (5 Group seed sẵn) + `khách` (không đăng nhập). Ô "—" = không áp dụng.
- Dữ liệu test chỉ dùng số/tên giả (`0900000xxx`, "Khách Giả A"). Không dữ liệu thật.
- Test cũ không được xoá; chỉ sửa đúng các assert mà story nêu tên.

## Bảng story

| Story | Nguồn | Mức | Lô | BE/FE |
|---|---|---|---|---|
| SR-01 | BM-01 Nhật ký lộ `loss_amount` → suy ra giá vốn | Critical | 1 | BE |
| SR-02 | `erp-console` `npm ci` fail (ERESOLVE `@types/node`) | High (chặn build/CI) | 1 | FE |
| SR-03 | F01 AI chốt lô `FieldError` + job `run_due_ai_actions` chết cứng | High | 1 | BE |
| SR-04 | BM-02 Lớp lọc PII của AI để lọt tên khách | High | 2 | BE |
| SR-05 | BM-06 Lệnh AI `retrieve`/`partial_update` sai `detail` (502/500, bỏ kiểm phạm vi) | Low → đi cùng SR-04 | 2 | BE |
| SR-06 | BM-03 Guidance đơn không lọc phạm vi `cskh` | Medium | 2 | BE |
| SR-07 | BM-04 Nháp "Nhập lô" lưu giá mua vào `localStorage` dùng chung | Medium | 2 | FE |
| SR-08 | F02 Huỷ lô quá hạn xoá cả phần đang giữ chỗ → mất giao dịch tiền | High | 3 | BE |
| SR-09 | F03 CSKH xác nhận đơn đã tự huỷ → kho soạn đơn đã huỷ | High | 3 | BE |
| SR-10 | F05 `publish_batch` không khoá → mở bán lô đã huỷ phiếu | Medium | 3 | BE |
| SR-11 | F06 Job DW-26 không idempotent ở nhánh chuyển Chủ | Medium | 3 | BE |
| SR-12 | F04 Chứng từ đảo doanh thu khi huỷ đơn đã thanh toán | High | 4 | BE |
| SR-13 | F04 Báo cáo lãi lỗ/dashboard dùng chứng từ đảo; thống nhất phiếu hoàn | High | 4 | BE |
| SR-14 | F04 Lập bù chứng từ đảo cho đơn đã huỷ trước P8 | High | 4 | BE |
| SR-15 | F09 Lô quá hạn còn tồn: cảnh báo + chỉ chốt khi hết tồn (+F11 nhãn lỗ hết hạn) | Low → nâng (Duy quyết) | 5 | BE+FE |
| SR-16 | F09 Xác nhận "Đã trả NCC" phần tồn lô quá hạn | mới (Duy quyết) | 5 | BE+FE |
| SR-17 | Dashboard chỉ hiện mã đơn, không tên khách | Medium (bất biến 9) | 5 | BE+FE |
| SR-18 | F1 IDOR ảnh khi tạo bài CMS | Medium | 6 | BE |
| SR-19 | F3 Link bằng chứng đồng ý mở sai phiên bản chính sách | Medium | 6 | FE |
| SR-20 | F4 Code AI nằm trong chunk màn nghiệp vụ (BR-AI-17) + F13 | Medium | 6 | FE |
| SR-21 | Bằng chứng chạy thật cho AC FE go-live/quyền riêng tư đã PASS bằng đọc code | QA | 6 | QA |
| SR-22 | Low BE: BM-05, BM-07, F07, F08, F10, F12, `no-store` đơn/khách | Low | 7 | BE |
| SR-23 | Low FE: F2, F6, F7, F8, F10, F12, F14 | Low | 7 | FE |
| SR-24 | Low test/tài liệu: F5, F9, F13 | Low | 7 | BE+FE+doc |

**Để sau (không làm trong P8, ghi lại để không mất):** F11 phía FE (chuyển `content/edit/page.tsx` 1556 dòng sang `features/content` + bỏ
barrel `features/guidance/index.ts` — refactor lớn, không đổi hành vi, rủi ro xung đột cao); idempotency đồng thời của
`POST /api/ai/commands/<id>/call/` (500 khi hai request cùng khoá); kiểm ACL bucket ảnh CMS của bài nháp (việc vận hành, Duy kiểm trên
GCS); tìm kiếm CSKH bằng SĐT đầy đủ trả dòng ngoài phạm vi (hỏi `legal-vn`); `period_pnl` chưa tính lỗ hết hạn/hỏng/trả NCC theo kỳ;
các AC FE CMS còn thiếu bằng chứng không thuộc go-live (CMS-03-AC13, CMS-05-AC6/AC8, CMS-04 offline, CMS-06, CMS-14, CS-02-AC6,
CS-05-AC8) — QA bù dần khi sửa màn đó.

---

# Lô 1 — chặn deploy

## SR-01 — Nhật ký không lộ giá vốn qua `loss_amount` (BM-01, bất biến 1, BR-PQ-13, BR-LO-03)
**Là** Chủ, **tôi muốn** Quản lý đọc Nhật ký mà không suy ra được giá vốn, **để** giữ "chỉ Chủ biết giá vốn".

- **AC1 (tái hiện, đỏ trước).** Given lô 10 kg, `landed_unit_cost` 81.234 (số giả), trạng thái EXPIRED, Chủ gọi `cancel_expired_batch`,
  When `quan_ly` gọi `GET /api/audit-logs/?action=cancel_expired_batch`, Then 200, `changes` **không** có khoá `loss_amount`, và chuỗi JSON
  response không chứa `812340`. (Trước khi sửa test này đỏ.)
- **AC2 (Chủ thấy đủ).** Cùng dữ liệu, `chu` gọi → `changes.loss_amount` còn nguyên.
- **AC3 (quét mọi khoá tiền).** Test quét: chạy `cancel_expired_batch`, `close_batch`, `recompute_landed_cost`, `return_batch_to_supplier`
  (khi có, Lô 5) rồi với `quan_ly` assert không khoá nào trong `changes` của mọi dòng thuộc danh sách "khoá tiền suy ra giá vốn"
  (`COST_KEYS` mở rộng: `loss_amount`, `loss`, `inventory_value`, `margin`, `gross_profit`, `expired_cost`, `supplier_refund_amount`).
- **AC4 (không đổi dữ liệu).** Bảng `AuditLog` không bị sửa (append-only); chỉ lọc khi trả ra.

| Group | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| `/api/audit-logs/` | 200, thấy `loss_amount` | 200, không có `loss_amount` | 403 | 403 | 403 | 401 |

## SR-02 — `erp-console` cài sạch bằng `npm ci` (điều phối viên)
**Là** người hiện thực, **tôi muốn** `npm ci` chạy sạch ở `erp-console` và `frontend`, **để** build/CI không cần `--legacy-peer-deps`.

- **AC1 (tái hiện).** Given lockfile hiện tại, When `cd erp-console && rm -rf node_modules && npm ci`, Then lỗi `ERESOLVE` (vitest@5.0.2
  peerOptional `@types/node ^22 || >=24`, repo ghim `^20.14.0`) — dán output vào `03-dev-notes.md`.
- **AC2.** Sau sửa: `npm ci` (không cờ) ở `erp-console` **và** `frontend` thoát mã 0, không có `ERESOLVE`/`--legacy-peer-deps`.
- **AC3.** `npx tsc --noEmit && npm run build && npm test` ở `erp-console` xanh; `npx tsc --noEmit && npm run build` ở `frontend` xanh.
- **AC4.** Không thêm/bớt thư viện ngoài `@types/node`; diff `package-lock.json` chỉ do đổi `@types/node` (và phụ thuộc bắc cầu của nó).

Ma trận Group: — (không đụng quyền).

## SR-03 — AI chốt lô với lô đã từng bán, và job AI không chết cứng (F01, DW-25, DW-21)
**Là** Chủ, **tôi muốn** việc AI chốt lô chạy đúng với lô đã bán, và một việc lỗi không chặn các việc khác, **để** job AI không đứng im.

- **AC1 (tái hiện R1a, đỏ trước).** Given lô đủ điều kiện chốt có 1 `SalesOrderLineBatch` thuộc đơn `COMPLETED`, When gọi
  `check_ai_close_batch_conditions(batch)`, Then trả `(True, …)` — không `FieldError`.
- **AC2 (điều kiện sàn thật sự chạy).** Given như AC1 nhưng có (a) phiếu hoàn PENDING của đơn đó, hoặc (b) `PaymentTransaction` OPEN gắn
  `sales_order` của đơn đó, Then trả `(False, {"code": "AI_CLOSE_BATCH_CONDITIONS_NOT_MET", …})`. Ba test riêng.
- **AC3 (tái hiện R1b, poison pill).** Given việc `inventory.batch.close` SCHEDULED tới hạn (lô đã bán) **và** một việc B khác tới hạn xếp
  sau, When `call_command("run_due_ai_actions")`, Then lệnh không văng exception; việc chốt lô chạy đúng (DONE hoặc ESCALATED theo điều
  kiện); việc xếp sau vẫn được xử lý; bước đẩy việc quá hạn 2 giờ vẫn chạy.
- **AC4 (lỗi bất ngờ trong một việc).** Given dispatch của một việc văng exception bất kỳ (mock), When job chạy, Then việc đó chuyển
  `FAILED`, `downgrade_reason={"code": "AI_JOB_ERROR", …}`, log chỉ có id việc + mã lệnh + tên lớp exception (không `str(exc)`, không
  args); các việc sau vẫn chạy; chạy job lần 2 không xử lý lại việc `FAILED` (idempotent).
- **AC5 (API).** `POST /api/ai/commands/inventory.batch.close/call/` với lô đã bán không còn trả 500.

| Group | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| gọi lệnh `inventory.batch.close` | 200 (đề xuất/lịch) | 403 | 403 | 403 | 403 | 401 |

---

# Lô 2 — dữ liệu cá nhân & phạm vi

## SR-04 — Lọc PII của AI không để lọt tên khách (BM-02, bất biến 9, H2 02b AI)
**Là** Duy, **tôi muốn** kết quả lệnh AI không bao giờ chứa tên/SĐT/địa chỉ khách, kể cả với Chủ, **để** đúng H2.

- **AC1 (tái hiện, đỏ trước).** Given `AI_ENABLED=True`, đơn của khách giả tên "Khách Giả Bí Mật" SĐT `0900000123` địa chỉ "Số 1 Đường Giả",
  When `nv_kho` gọi `POST /api/ai/commands/reports.dashboard_summary/call/`, Then chuỗi "Khách Giả Bí Mật" không xuất hiện trong response.
- **AC2 (khoá `customer` lọc cả nhánh).** Unit test `scrub_data`: input có `customer` là chuỗi, và `customer` là dict `{name, phone, address}`
  → cả hai bị bỏ nguyên khoá; `recipient_phone`, `phone_last4`, `phone_masked` cũng bị bỏ.
- **AC3 (quét toàn registry, gồm `retrieve`).** Test quét gọi **mọi** lệnh đọc (list **và** retrieve — retrieve gọi được nhờ SR-05) với 5
  Group, fixture PII giả (tên, SĐT, địa chỉ, tên người chuyển trong `raw_payload`); assert không chuỗi PII nào xuất hiện trong bất kỳ
  response 200 nào; assert **số lệnh retrieve đã gọi thành công > 0** (chống test xanh giả vì 502).

| Lệnh AI đọc | chu | quan_ly | nv_kho | nv_giao | cskh |
|---|---|---|---|---|---|
| mọi lệnh đọc có quyền | 200, 0 chuỗi PII | 200, 0 chuỗi PII | 200, 0 chuỗi PII | 200/403, 0 chuỗi PII | 200/403, 0 chuỗi PII |

## SR-05 — Lệnh AI chi tiết chạy đúng và kiểm phạm vi `target_id` (BM-06)
- **AC1 (tái hiện, đỏ trước).** `chu` gọi `POST /api/ai/commands/inventory.batch.retrieve/call/` `{"target_id": "<pk>"}` → 200 có dữ liệu
  lô (hiện 502 `AI_DISPATCH_FAILED`).
- **AC2.** Registry: mọi lệnh sinh từ action chuẩn `retrieve`/`partial_update` có `detail=True`.
- **AC3 (phạm vi).** `nv_giao` tạo đề xuất mức C `sales.salesorder.partial_update` với `target_id` đơn ngoài phạm vi → 404 `NOT_FOUND`,
  không tạo `AiAction`.
- **AC4.** `reports.batch_pnl` kèm `target_id` (Chủ) → 200 hoặc 400 có thông điệp, **không** 500.
- **AC5.** SR-04 và SR-05 merge **cùng commit**; test quét SR-04-AC3 phải xanh trong cùng commit.

## SR-06 — Guidance đơn dùng đúng phạm vi như danh sách đơn (BM-03, BR-GH-18, Tầng 3)
- **AC1 (tái hiện, đỏ trước).** Given user `cskh` và đơn `DH-OUT-1` ngoài phạm vi, When `GET /api/guidance/order/DH-OUT-1/`, Then **404**
  (hiện 200). `GET /api/sales/orders/<id>/` vẫn 404.
- **AC2.** `POST /api/ai/actions/escalate/` với đơn ngoài phạm vi của `cskh` → 404.
- **AC3.** Đơn trong phạm vi `cskh` → 200 như cũ. `nv_giao`: đơn của phiếu giao gán cho mình 200, đơn khác 404. User có `view_salesorder`
  nhưng không thuộc Group nào (gán quyền trực tiếp) → phạm vi giống `SalesOrderViewSet`.
- **AC4.** Một hàm phạm vi dùng chung (`scope_orders_for(user, qs)`); `SalesOrderViewSet.get_queryset` và guidance cùng gọi hàm này;
  test cũ của danh sách đơn xanh nguyên.

| `/api/guidance/order/<mã>/` | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| đơn trong phạm vi | 200 | 200 | 200 | 200 (phiếu của mình) | 200 (trong phạm vi gọi) | 401 |
| đơn ngoài phạm vi | — | — | — | 404 | 404 | 401 |

## SR-07 — Nháp "Nhập lô" không giữ giá mua giữa các người dùng (BM-04, bất biến 1 phía FE)
- **AC1 (tái hiện, đỏ trước).** Test FE (vitest) cho hàm lưu/nạp nháp: lưu nháp có `rate` → đọc lại nháp **không có** `rate`.
- **AC2.** Khoá nháp gắn `user.id` (`cave_draft_nhap_lo:<userId>`), lưu ở `sessionStorage`; đăng xuất xoá mọi khoá `cave_draft_nhap_lo*`
  ở cả `localStorage` (khoá cũ) và `sessionStorage`.
- **AC3 (chạy thật).** Playwright: Chủ đăng nhập, mở Nhập lô, gõ giá mua `81234`, đăng xuất; `nv_kho` đăng nhập, mở Nhập lô → ô giá mua
  rỗng, `localStorage`/`sessionStorage` không chứa `81234`. Ảnh chụp + bước ghi vào `04-qa-report.md`.
- **AC4.** Idempotency key sinh mới khi nạp nháp của phiên khác / sau khi gửi thành công.

---

# Lô 3 — tiền & kho (có test tái hiện)

## SR-08 — Không huỷ lô quá hạn khi còn giữ chỗ (F02, BR-LO-03, BR-LO-07 mới, C1)
- **AC1 (tái hiện R5, đỏ trước).** Given đơn BOOKED giữ 2 kg lô X, lô X chuyển EXPIRED, When Chủ gọi `cancel_expired_batch`, Then 400
  `BR-LO-07` "Còn 2,000 kg đang giữ chỗ của 1 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ." Lô vẫn EXPIRED, tồn không đổi, không
  có dòng `WRITE_OFF`.
- **AC2 (tiền không mất).** Tiếp AC1, `confirm_payment` cho đơn đó → đơn PAID, có `PaymentTransaction`, hoá đơn xuất bình thường.
- **AC3.** Sau khi giữ chỗ về 0 (đơn huỷ do TTL), huỷ lô → 200, `WRITE_OFF` đúng `qty_available`.
- **AC4 (bước Tiếp theo).** Guidance lô EXPIRED còn giữ chỗ: bước `cancel_expired` `allowed=false`, `missing` có `BR-LO-07`.
- **AC5 (chạy 2 lần).** Gọi huỷ lần 2 trên lô đã CANCELLED → 400 `BR-LO-03`, không ghi thêm ledger.

| `POST …/cancel-expired/` | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| | 200/400 nghiệp vụ | 403 | 403 | 403 | 403 | 401 |

## SR-09 — CSKH không "xác nhận" được đơn hệ thống đã tự huỷ (F03, BR-GH-18, CS-08/CS-09)
- **AC1 (tái hiện R2, đỏ trước).** Given đơn bị `auto_cancel_overdue` (đơn CANCELLED, phiếu CANCELLED, task `REFUND_CALL`), When
  `record_call(result="CONFIRMED")`, Then 409 `STALE_STATE` "Đơn đã bị huỷ — tải lại màn hình.", phiếu vẫn CANCELLED, task vẫn `REFUND_CALL`.
- **AC2.** Task `REFUND_CALL` chỉ nhận `UNREACHABLE`, `NOTIFIED`; mọi kết quả khác (`CONFIRMED`, `CONFIRMED_CHANGED`, `CALLBACK`,
  `WRONG_NUMBER`, `WANT_*`) → 409 `STALE_STATE`. Test tham số hoá từng kết quả.
- **AC3 (tranh chấp hai chiều).** (a) CSKH xác nhận trước, job chạy sau → job bỏ qua (đã có, giữ xanh). (b) Job chạy trước, CSKH bấm sau
  trên màn hình cũ → như AC1.
- **AC4 (API).** `POST /api/cskh/queue/<id>/calls/` trả 409 với body `{"detail", "code": "STALE_STATE"}`; FE hiện thông điệp + nút tải lại
  (Playwright hoặc ảnh chụp: mở màn gọi, chạy job tự huỷ ở backend, bấm "Đã xác nhận").

| `…/cskh/queue/<id>/calls/` trên task REFUND_CALL | user có `delivery.confirm_with_customer` (cskh, và nhóm nào đang được gán quyền này) | user không có quyền | khách |
|---|---|---|---|
| CONFIRMED | 409 `STALE_STATE` | 403 | 401 |
| NOTIFIED / UNREACHABLE | 200 | 403 | 401 |

## SR-10 — Mở bán lô có khoá, không mở bán lô của phiếu đã huỷ (F05, BR-MH-05, DW-18-AC4)
- **AC1 (tái hiện R3, đỏ trước).** Given phiếu nhập tạo lô DRAFT, lấy object lô (cũ), `cancel_receipt` chạy xong, When
  `publish_batch(object cũ)`, Then 400 `BR-MH-05`, lô vẫn CANCELLED (hoặc trạng thái huỷ hiện có), phiếu CANCELLED.
- **AC2.** `publish_batch` chạy trong `atomic` + `select_for_update().get(pk=…)` rồi mới kiểm DRAFT; publish lần 2 → 400.
- **AC3.** Luồng thuận publish DRAFT → SELLING, AuditLog `publish_batch` xanh như cũ.

| `POST …/publish/` | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| | 200/400 | 200/400 | 403 | 403 | 403 | 401 |

## SR-11 — Job khớp tiền tuyệt đối (DW-26) chạy nhiều lần không phình Nhật ký, không mở lại việc đã đóng (F06)
- **AC1 (tái hiện R4, đỏ trước).** Given 1 giao dịch UNMATCHED OPEN, When chạy `process_exact_payment_matches()` 2 lần, Then đúng **1** dòng
  AuditLog `escalate_unmatched_payment`.
- **AC2.** Chủ đặt việc đó `REJECTED` (hoặc DONE/CANCELLED/EXPIRED), chạy job lại → việc giữ nguyên trạng thái kết thúc, không thêm audit.
- **AC3.** Lý do chuyển thay đổi (vd số tiền giao dịch được cập nhật khác) → ghi thêm 1 dòng audit và cập nhật `downgrade_reason`.
- **AC4.** Chỉ quét giao dịch `match_status=UNMATCHED`; ORPHAN/OVERPAID/UNDERPAID không tạo việc chuyển Chủ (đã ở hàng chờ lệch).

Ma trận Group: job Hệ thống, không có endpoint mới.

---

# Lô 4 — chứng từ đảo doanh thu (F04)

## SR-12 — Huỷ đơn đã thanh toán lập chứng từ đảo doanh thu (F04, BR-HT-06 sửa, BR-HT-10 mới, BR-PQ-10/11)
**Là** Chủ, **tôi muốn** mỗi lần huỷ đơn đã thanh toán có một chứng từ đảo doanh thu gắn hoá đơn gốc, **để** sổ cái đúng mà vẫn giữ lịch sử.

- **AC1 (tái hiện R6, đỏ trước).** Given đơn PAID 2 kg × 150.000 từ lô X (100 kg), When job tự huỷ CSKH chạy (`auto_cancel_overdue`), Then
  có đúng 1 `SalesCreditNote` gắn hoá đơn gốc, `amount` = `invoice.amount`, 1 dòng: lô X, 2,000 kg, đơn giá 150.000, thành tiền 300.000;
  hoá đơn gốc **vẫn `ISSUED`**, không đổi field nào.
- **AC2 (huỷ tay).** Chủ/Quản lý huỷ qua `POST /api/sales/orders/<id>/cancel/` → như AC1, `created_by` = người huỷ; job → `created_by=None`.
- **AC3 (combo, nhiều lô).** Đơn có dòng phân bổ 2 lô → chứng từ có 2 dòng, mỗi dòng đúng lô/kg/đơn giá của `SalesInvoiceLineBatch`.
- **AC4 (idempotent).** Gọi huỷ lần 2 (400 như cũ) và chạy job tự huỷ 2 lần → vẫn đúng 1 chứng từ.
- **AC5 (atomic).** Nếu lập chứng từ lỗi (mock raise) → huỷ đơn rollback toàn bộ: đơn giữ trạng thái cũ, không `CANCEL_RESTORE`.
- **AC6 (giao thất bại).** Huỷ khi phiếu giao FAILED (không hoàn kho) → vẫn lập chứng từ, `stock_restored=false`.
- **AC7 (append-only).** Model không có quyền add/change/delete cho ai (chỉ `view`); Admin chỉ đọc; không service nào sửa/xoá chứng từ.
- **AC8 (dòng thời gian, không rò giá vốn).** Timeline đơn thêm sự kiện "Hệ thống lập chứng từ đảo doanh thu DC-… (300.000đ)"; không có
  `unit_cost` ở bất kỳ response nào cho `quan_ly`/`nv_kho`/`nv_giao`/`cskh`; AuditLog `issue_credit_note` không có khoá giá vốn.

| Huỷ đơn đã TT (tạo chứng từ) | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| `POST /api/sales/orders/<id>/cancel/` | 200 | theo quyền `sales.cancel_paid_order` hiện có (không đổi) | 403 | 403 | 403 | 401 |

## SR-13 — Lãi lỗ theo lô / theo kỳ / dashboard trừ chứng từ đảo; phiếu hoàn không trừ hai lần (F04, BR-BC-03/04, BR-HT-06)
- **AC1 (lô, tái hiện R6).** Tiếp SR-12-AC1: `batch_pnl(X)` → `revenue=0`, `qty_sold=0`, `reversed_qty=2`, `reversed_revenue=300000`.
- **AC2 (bán lại không cộng hai lần).** Tiếp AC1, bán lại 2 kg đó cho đơn khác 2 × 150.000 → `batch_pnl` `qty_sold=2`, `revenue=300000`
  (không phải 4 kg/600.000).
- **AC3 (kỳ).** Hoá đơn tháng 9, huỷ tháng 10: `period_pnl(9)` giữ nguyên doanh thu/giá vốn tháng 9 (không sửa kỳ cũ); `period_pnl(10)` có
  `credit_notes=300000`, `cogs_reversed = Σ kg × unit_cost` của dòng chứng từ, `revenue` tháng 10 = hoá đơn tháng 10 − 300.000.
- **AC4 (thống nhất phiếu hoàn).** Tiếp AC3, Chủ xác nhận phiếu hoàn 300.000 của hoá đơn đó trong tháng 10 → `period_pnl(10).refunds` **không**
  cộng 300.000 (đã đảo bằng chứng từ). Phiếu hoàn của hoá đơn **không** có chứng từ đảo (hoàn một phần khi giao thiếu) → vẫn trừ như cũ.
- **AC5 (dashboard).** `revenue_today` = Σ hoá đơn ISSUED hôm nay − Σ chứng từ đảo hôm nay.
- **AC6 (quyền báo cáo không đổi).** `/api/reports/batch/<batch_id>/`, `/api/reports/period/`: `chu` 200; nhóm khác 403; khách 401 (giữ ma trận hiện có).
- **AC7 (docstring/spec).** Docstring `confirm_refund`, `cancel_paid_order`, module `reports/services.py` và BR-HT-06/BR-HT-10/BR-BC-03/BR-BC-04
  trong `doc/business-process-spec.md` cập nhật đúng văn bản ở 02b §4.6, có ghi "Duy duyệt 30/09".

| Báo cáo lãi lỗ | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| batch/period pnl | 200 | 403 | 403 | 403 | 403 | 401 |
| dashboard `revenue_today` | 200 | 200 | 200 | 403 | 403 | 401 |

## SR-14 — Lập bù chứng từ đảo cho đơn đã huỷ trước P8 (F04)
- **AC1.** Lệnh `manage.py backfill_credit_notes` mặc định **chỉ in** (dry-run): số đơn CANCELLED có hoá đơn ISSUED chưa có chứng từ, danh
  sách mã đơn, và danh sách **mã lô đã CLOSED** bị ảnh hưởng (lãi lỗ lô đã chốt sẽ đổi). Không ghi gì.
- **AC2.** `--apply` lập chứng từ với `issued_at` = thời điểm dòng AuditLog `cancel_paid_order` của đơn (không có thì `created_at` của đơn
  cộng cờ `backfilled=true`), `created_by=None`.
- **AC3 (chạy 2 lần).** `--apply` lần 2 → 0 chứng từ mới.
- **AC4.** Output không in tên/SĐT/địa chỉ khách, không in giá vốn — chỉ mã đơn, mã hoá đơn, số tiền bán, mã lô.

Ma trận Group: lệnh quản trị, không endpoint. Duy chạy trên staging rồi production **sau** deploy (xem 02c).

---

# Lô 5 — quy trình lô quá hạn + dashboard (F09, quyết định Duy)

## SR-15 — Lô quá hạn còn tồn: cảnh báo và chỉ chốt khi hết tồn (F09, BR-LO-04 sửa, BR-LO-07 mới; kèm F11)
- **AC1 (tái hiện, đỏ trước).** Given lô EXPIRED còn 3 kg, đủ mọi điều kiện khác, When `check_close_batch`, Then có `Missing("BR-LO-04", …)`;
  `close_batch` → 400; luật sàn AI chốt lô (DW-25) cũng chặn. Test S04 đang cho qua trường hợp này được **sửa đúng assert đó**.
- **AC2.** Lô EXPIRED tồn 0 (sau Đã huỷ một phần + Đã trả phần còn lại, hoặc bán hết trước khi quá hạn) → chốt được; lô CANCELLED (tồn 0) →
  chốt được như cũ.
- **AC3 (Tiếp theo).** Guidance lô EXPIRED còn tồn trả 3 bước: `cancel_expired` ("Xác nhận Đã huỷ phần tồn"), `return_to_supplier`
  ("Xác nhận Đã trả NCC"), `close` (`allowed=false`, `missing` BR-LO-04). Lô EXPIRED tồn 0 → bước `close`.
- **AC4 (Cần chú ý).** `GET /api/dashboard/attention/` với user có `inventory.cancel_expired_batch` có khoá `expired_batches_open` = số lô
  EXPIRED còn tồn > 0; user khác không có khoá này; user chỉ có quyền này (không có 3 quyền delivery) → 200 thay vì 403.
- **AC5 (xác nhận số kg khớp màn hình).** `POST …/cancel-expired/` nhận thêm `confirm_qty` (tuỳ chọn); khác `qty_available` hiện tại → 400
  `BR-LO-07` "Tồn đã đổi (x kg) — tải lại."; không gửi → chạy như cũ (giữ tương thích lệnh AI).
- **AC6 (F11).** `batch_pnl.expired_qty` chỉ đếm `WRITE_OFF` do huỷ lô quá hạn; lô có phiếu nhập bị huỷ (DW-18) → `expired_qty=0`.
- **AC7 (FE chạy thật).** Playwright/ảnh chụp: Chủ thấy thẻ "Lô quá hạn còn tồn: N" ở Cần chú ý, bấm vào mở danh sách lọc EXPIRED; mở lô →
  2 nút xác nhận + nút Chốt bị khoá có lý do; `nv_kho` không thấy thẻ và không thấy nút.

| | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| thẻ `expired_batches_open` | có | không | không | không | không | 401 |
| `…/cancel-expired/`, `…/close/` | 200/400 | 403 | 403 | 403 | 403 | 401 |

## SR-16 — Xác nhận "Đã trả NCC" phần tồn lô quá hạn (F09, BR-MH-08 mới, BR-LO-07, BR-BC-04)
**Là** Chủ, **tôi muốn** ghi nhận số kg lô quá hạn đã trả lại nhà cung cấp và số tiền NCC hoàn (nếu có), **để** kho về 0 và lãi lỗ lô đúng.
🟡 Giả định thiết kế (PA): dự án mua tại cảng trả tiền ngay (decisions 10/09), nên việc NCC nhận lại hàng/hoàn tiền là thoả thuận ngoài hệ
thống; hệ thống chỉ ghi sổ. Duy lật được (bỏ ô tiền → chỉ ghi kg).

- **AC1.** Given lô EXPIRED tồn 5 kg, không giữ chỗ, When Chủ `POST /api/inventory/batches/<id>/return-to-supplier/`
  `{"qty": "3.000", "supplier_refund_amount": "150000", "note": "", "request_id": "<uuid>"}`, Then 200; tồn 2 kg; sổ kho có dòng
  `SUPPLIER_RETURN −3.000`; có bản ghi trả NCC; AuditLog `return_batch_to_supplier`; lô vẫn EXPIRED.
- **AC2 (trả hết → chốt).** Trả nốt 2 kg (tiền 0) → tồn 0 → `close_batch` qua được điều kiện tồn.
- **AC3 (lãi lỗ).** `batch_pnl` có `supplier_return_qty=5`, `supplier_refund_amount=150000`, `total_cost = purchase_cost + allocated_cost − 150000`.
- **AC4 (biên).** `qty` ≤ 0, `qty` > tồn, tiền âm, tiền không phải số, lô không EXPIRED, lô đã CLOSED/CANCELLED, còn giữ chỗ → 400 với
  `BR-MH-08`/`BR-LO-07`/`BR-LO-05`; dữ liệu không đổi.
- **AC5 (bấm đúp).** Gửi lại cùng `request_id` → 200 trả bản ghi cũ, không trừ tồn lần 2.
- **AC6 (không rò giá vốn).** `supplier_refund_amount` thuộc `COST_KEYS`; `quan_ly` đọc Nhật ký không thấy; response của endpoint không trả
  số tiền; `BatchSerializer` cho `nv_kho` không có field mới nào về tiền.
- **AC7 (AI).** Lệnh AI sinh tự động cho action này có trần `C` (chỉ soạn nháp), giống `cancel_expired`.
- **AC8 (FE chạy thật).** Playwright/ảnh: form "Đã trả NCC" (kg, tiền NCC hoàn — tuỳ chọn, ghi chú), chặn bấm đúp, lỗi 400 hiện tiếng Việt;
  sau khi trả hết, nút Chốt lô mở.

| `…/return-to-supplier/` | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| | 200/400 | 403 | 403 | 403 | 403 | 401 |

## SR-17 — Dashboard chỉ hiện mã đơn (quyết định Duy, bất biến 9)
- **AC1 (tái hiện, đỏ trước).** Given đơn của "Khách Giả A" SĐT `0900000456`, When `nv_kho` gọi `GET /api/dashboard/summary/`, Then
  `recent_orders[]` **không** có khoá `customer` và `phone_last4`; chuỗi "Khách Giả A" và `0456` không có trong JSON.
- **AC2.** Áp cho **mọi** nhóm có `view_dashboard` (`chu`, `quan_ly`, `nv_kho`): tập khoá mỗi dòng = `{code, amount, status, status_label,
  expires_at}` (so bằng `assertEqual(set(...))`).
- **AC3 (FE chạy thật).** Màn Tổng quan bỏ cột "Khách", ô tìm chỉ theo mã đơn/trạng thái; Playwright/ảnh ở 1366px và 375px, DOM không chứa tên
  khách mock.
- **AC4.** Lệnh AI `reports.dashboard_summary` tự hết tên khách (kiểm lại bằng test SR-04-AC1).

| `/api/dashboard/summary/` | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| | 200, không tên/SĐT | 200, không tên/SĐT | 200, không tên/SĐT | 403 | 403 | 401 |

---

# Lô 6 — CMS / FE

## SR-18 — Không dùng ảnh của bài khác khi tạo/sửa bài (F1, R5 02b CMS, BR-ND-07)
- **AC1 (tái hiện, đỏ trước).** Given bài A có ảnh id=1, When `quan_ly` `POST /api/content/entries/` với `cover_image: 1` → 400 `BR-ND-07`;
  với khối `{"type":"image","image_id":1}` → 400 `BR-ND-07`. Không tạo bài.
- **AC2.** `PATCH` bài B với `cover_image` là ảnh của bài A → 400; với ảnh của chính B → 200.
- **AC3 (lớp 1b).** Bài đã đăng có (dữ liệu cũ) khối ảnh trỏ ảnh bài khác → API công khai bỏ khối đó, ảnh bìa ngoài bài → `null`.
- **AC4.** Giới hạn 20/100 ảnh mỗi bài không lách được qua ảnh bài khác.

| Tạo/sửa bài | chu | quan_ly | nv_kho | nv_giao | cskh | khách |
|---|---|---|---|---|---|---|
| POST/PATCH entries | theo quyền content hiện có (200/400) | như chu | 403 | 403 | 403 | 401 |

## SR-19 — Link bằng chứng đồng ý mở đúng phiên bản chính sách (F3, GL-05-AC1)
- **AC1 (tái hiện, đỏ trước).** Playwright: đơn có consent v1, chính sách đã lên v2; Chủ mở chi tiết đơn, bấm link → màn hình hiện **nội dung v1**
  (tiêu đề "Phiên bản 1", chỉ đọc), không phải bản nháp/v2.
- **AC2.** `/content/edit/?id=…&version=N` mở thẳng panel lịch sử ở phiên bản N (`GET …/versions/<N>/`), chế độ chỉ đọc; N không tồn tại → thông
  báo "Không tìm thấy phiên bản N" + nút về bài.
- **AC3.** `quan_ly` thấy như Chủ; `nv_kho` không thấy link (không có `privacy_consent`).

## SR-20 — Màn nghiệp vụ không tải code AI khi AI không bật (F4, F13, BR-AI-17, DW-09-AC8)
- **AC1 (tái hiện, đỏ trước).** Script đo sau `npm run build`: manifest của `/orders`, `/orders/payments`, `/orders/refunds`, `/inventory` không
  chứa chunk có `new Worker`, `wllama`, `/call/`. (Hiện chunk `6877-*` có mặt.)
- **AC2.** `GuidancePanel` chỉ giữ phần tất định; phần "Để AI làm/Nhờ" nạp bằng `next/dynamic`, chỉ render khi `ai_enabled` và đã đồng ý.
- **AC3.** AI tắt: mở 4 màn trên → **0** request tới `/api/ai/*` (Playwright bắt network).
- **AC4.** Bảng First Load JS trước/sau của 4 route + layout ghi vào `03-dev-notes.md`; chunk layout không còn chuỗi `wllama` (F13).
- **AC5.** AI bật + đã đồng ý: nút "Để AI làm" vẫn chạy (Playwright với mock).

## SR-21 — Bằng chứng chạy thật cho AC FE go-live/quyền riêng tư (bảng "AC thiếu bằng chứng")
QA bổ sung Playwright (hoặc ảnh chụp trình duyệt + bước) cho các AC đã PASS bằng đọc code, ưu tiên nhóm pháp lý:
- GL-03-AC2, AC4, AC5 (mock 409/404/503 ở checkout), AC8 (`localStorage`/`sessionStorage`/URL không có SĐT đầy đủ, tên, địa chỉ).
- GL-04-AC1…AC5 (bật/tắt `SHOP_CONFIRM_CALL_NOTICE` bằng mock; DOM/URL không có SĐT đầy đủ).
- GL-01-AC2/AC5/AC6, GL-02-AC1…AC5 (footer 7 route, API lỗi, 375×667).
- CS-11-AC6 (`page.pdf` 1 trang 100×150 ±1 mm, giải mã QR), X-AC4 (storage/URL/console của màn CSKH, phiếu giao, in tem).
- Mỗi AC: PASS/FAIL + đường dẫn spec/ảnh trong `04-qa-report.md`. AC FAIL → mở lỗi, sửa trong Lô 6 nếu nhỏ, lớn thì báo Duy.

---

# Lô 7 — Low (rẻ và an toàn)

## SR-22 — Siết BE nhỏ
- **BM-05.** `confirm_ai_action`/`reject_ai_action` dùng chung bộ lọc của `retrieve` (owner, hoặc ESCALATED cùng `assignee_group`, hoặc
  `manage_ai_policy`); ngoài bộ lọc → 404, trạng thái không đổi. Test: `nv_giao` reject việc của Chủ → 404.
- **BM-07.** `_is_cost_authorized` dùng `apps.common.cost_keys.can_view_cost`. Test: user chỉ có `view_profitreport` → khoá giá vốn bị lọc.
- **F07.** Mốc ngày của hạn mức AI = `timezone.localtime().replace(hour=0, …)`. Test lúc 06:30 giờ VN tính vào hôm nay.
- **F08.** `escalate_expired_windows` khoá `DeliveryNote` rồi mới khoá `ConfirmationTask` (thứ tự §1.5).
- **F10.** `undo_ai_action` dispatch đúng action trong `undo="cancel_action:<act>"`; không có đường hoàn tác → 400; cho phép hoàn tác khi
  `AI_ENABLED=false`. Test: action B giả có `cancel_action:foo` → gọi `foo`, không gọi `cancel_receipt`.
- **F12.** Không có user `chu` active → bỏ qua, log cảnh báo (không giao cho user bất kỳ); `downgrade_reason` chỉ ghi `BusinessError.code`.
- **No-store.** `SalesOrderViewSet` và `CustomerViewSet` có `Cache-Control: no-store` (dùng `NoStoreMixin`).

## SR-23 — Siết FE nhỏ
- **F2.** `frontend/features/content/safeHref.ts` dùng đúng luật bản ERP (`//`, `/\`, khoảng trắng/ký tự điều khiển, ≤2000); unit test 15 payload.
- **F6.** Ghi bổ sung "Lệch thiết kế" (apiFetch 404/410) vào `03-dev-notes.md` của **P8**; kiểm các chỗ Shop so chuỗi "Không tìm thấy" vẫn đúng.
- **F7.** `ArticleBody` nạp catalog **một lần**, truyền map xuống `ItemCard`; Playwright đếm 1 request catalog cho bài có 3 thẻ.
- **F8.** Ảnh thân bài có `srcSet` 480w/960w/1600w + `sizes` (nếu API công khai đã trả 3 cỡ; không thì ghi "để sau").
- **F10.** Tách `CskhNotice` dùng chung, một `getSiteInfo`, một nguồn giờ gọi (`CSKH_WORKING_HOURS`); màn thanh toán gọi `site-info` ≤ 1 lần.
- **F12.** Xoá `erp-console/app/ai-spike/` và `erp-console/spikes/dw02/`; build không còn `out/ai-spike`.
- **F14.** Trang in tem render QR bằng `<img src="data:image/svg+xml,…">`; chuyển về đăng nhập giữ nguyên query (`next=/print/label/?note=…`).

## SR-24 — Test và tài liệu
- **F5.** (a) Tách hàm đọc cờ `PRIVACY_CONSENT_REQUIRED(testing, debug, env)` và test hàm đó; (b) GL-03-AC10 POST Admin thật bằng
  `force_login(superuser)`; (c) GL-03-AC9 so **đúng tập khoá** response tra đơn.
- **F9.** Mock `xss-mau` ở `frontend/features/content/mock.ts` + Playwright: không `dialog`, không `<script>`, không `javascript:`, link ngoài có `rel`.
- **F13.** `doc/ops/moi-truong.md` ghi: staging `AI_PRODUCTION_READY=1`, `AI_WRITE_LEVELS_ALLOWED=B`; production giữ `0`/`C`; lịch chạy
  `run_due_ai_actions`, `auto_confirm_exact_payments`, `process_cskh_deadlines`. Đính chính câu V-DW1 ghi ở 02b §8 hồ sơ này.
