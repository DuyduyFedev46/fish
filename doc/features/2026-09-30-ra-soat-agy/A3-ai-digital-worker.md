# A3 — Rà soát QA hồ sơ `2026-09-28-ai-digital-worker` (DW-01…DW-27)

> qa-tester (Claude Sonnet 5) · 2026-09-30 · Bước A3 của `doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md`.
> Cổng Playwright được giao (3102/3202) **không dùng tới** vì không cần bật server — mọi kiểm chứng chạy qua
> `manage.py test` (DB test SQLite/transaction, không đụng DB thật), `vitest` và `tsc`/build tĩnh của `erp-console`.
> Không sửa code sản phẩm, không commit, không gọi LLM thật/mạng ngoài, không đụng DB staging/production.

## Tóm tắt kết luận

- **1058/1058 test backend xanh** (toàn bộ suite, không riêng `apps.ai`), `makemigrations --check --dry-run` sạch.
- **211/211 test** của cụm liên quan trực tiếp hồ sơ này (`apps.ai`, `apps.common.guidance`, `apps.inventory.batches`,
  `apps.purchasing.receipts`, `apps.sales.orders.tests.test_guidance`, `apps.sales.refunds.tests.test_guidance`,
  `apps.sales.payments.tests.test_guidance`, `apps.sales.payments.tests.test_dw26_auto_confirm`) xanh.
- **erp-console**: `npx vitest run features/ai` → 16/16 xanh (`commands.test.ts`, `actions.test.ts`); `tsc --noEmit` sạch.
- Đọc lại `04-qa-report.md` (866 dòng, 27 lô, tất cả APPROVED) và đối chiếu với 3 báo cáo rà soát code
  `doc/features/2026-09-30-review-p1-p7/review-bao-mat-du-lieu.md` + `review-tien-kho-ai.md` + `review-cms-golive-fe-qa.md`:
  **mọi lỗ hổng Critical/High/Medium đụng tới hồ sơ này đã được tìm ra trước đó và có mã SR-xx trong
  `doc/features/2026-09-30-sua-loi-review/02-stories.md`, P8 Lô 1–7 vẫn ☐ (chưa sửa)**. Tôi xác minh lại bằng
  chứng cụ thể (grep/đọc code/test) cho từng mã — xem bảng "Lỗi trùng SR-xx đã xác minh lại" — **không có lỗi mới**
  ngoài 1 ghi nhận Low ở cuối (không chặn).
- **Không tìm thấy lỗi mới** cần story P9. Không viết test mới (test hiện có đã đủ tốt và đã phủ đúng các AC tôi
  kiểm; các lỗ hổng thật sự đều đã có repro/SR-xx từ trước, viết thêm test đỏ trùng sẽ chỉ lặp lại bằng chứng đã có).

## Phương pháp

1. Đọc toàn bộ `02-stories.md` (DW-01…DW-27, ~220 AC) và `01-analysis.md`.
2. Liệt kê mọi file test có nhãn `DW-xx-ACy` (44 file test khớp) — đối chiếu với bảng AC trong `04-qa-report.md`
   (đã ghi rất chi tiết tên test cho từng AC).
3. Chạy toàn bộ test liên quan + toàn bộ suite backend; chạy `vitest`/`tsc` phía `erp-console`.
4. **Không tin báo cáo suông**: đọc trực tiếp thân của ~15 test đại diện cho các AC ưu tiên (tiền, tồn kho, giá vốn,
   PII, phân quyền, mức tự chủ/công tắc, hoàn tác) để xác nhận test *thật sự* assert đúng nội dung AC, không phải
   `assert True`/chỉ kiểm status 200.
5. Đối chiếu **3 báo cáo rà soát code A1** (`review-bao-mat-du-lieu.md`, `review-tien-kho-ai.md`,
   `review-cms-golive-fe-qa.md`) — các báo cáo này đã tìm lỗi bằng cách đọc code (không chạy), nên tôi **tự chạy
   lại/tự grep xác minh** từng lỗi đụng tới hồ sơ AI còn tồn tại hay đã sửa (P8 Lô nào cũng ☐, nên dự đoán là còn
   tồn tại — vẫn xác minh bằng chứng cụ thể thay vì tin báo cáo).

## Theo AC — tổng hợp theo Lô/Story

Ký hiệu: ✅ = chạy thật, test còn xanh và tôi đã xác nhận nội dung assert đúng AC · ⚠️ = test đang PASS nhưng
AC không còn đúng 100% vì có lỗi SR-xx tại một đường khác (ghi rõ) · ⏸ = không kịp kiểm, ghi lý do · "trùng SR-xx"
= lỗi đã có story P8.

| Lô | Story | AC | Kết quả | Ghi chú |
|---|---|---|---|---|
| 0 | DW-01, DW-02 | AC1–6, AC1–6 | ✅ | Spike, đã APPROVED lần 1; kết quả ghi ở `research/02-spike-be.md`, `research/03-spike-fe.md`; không phải luồng chạy production nên không tái kiểm chi tiết token/latency, chỉ xác nhận không có code spike lọt vào `apps/*/services.py`/`erp-console/features/` (grep `spikes/dw01`, `app/ai-spike` — 2 thư mục này **vẫn còn** trong repo, xem ⚠️ SR-24/F12 dưới) |
| 1a | DW-03 | AC1–11 | ✅ | `apps.sales.orders.tests.test_guidance` (9 test) chạy xanh; đọc `test_dw03_ac5_no_pii_for_chu`, `test_dw03_ac6_no_cost_leak`, `test_dw03_ac7_permissions` — assert đúng nội dung (không chỉ status), có chuỗi PII giả cụ thể bị kiểm `assertNotIn` |
| 1b | DW-04, DW-05 | AC1–7, AC1–7 | ✅ (DW-05-AC5 xem ⚠️) | `apps.sales.refunds.tests.test_guidance`, `apps.sales.payments.tests.test_guidance`, `apps.inventory.batches.tests.test_guidance` (46 test) xanh |
| 1c | DW-06 | AC1–7 | ⚠️ **AC5 (giá vốn)** | Test `test_dw06_ac5_cost_hidden_in_timeline_for_quan_ly` chỉ kiểm `/api/guidance/batch/<id>/` — đường này **đúng**, không rò. Nhưng tôi xác minh lại **`/api/audit-logs/`** (nhật ký chung, `quan_ly` có `view_auditlog`) vẫn lộ `loss_amount` = `qty × landed_unit_cost` cho hành động `cancel_expired_batch`, vì `loss_amount` **không có** trong `COST_KEYS` (xác nhận bằng script đọc trực tiếp `apps.common.cost_keys.COST_KEYS` — xem bảng dưới). Đây là **trùng SR-01 (BM-01, Critical)**, Lô 1 P8, chưa sửa. Story DW-06-AC5 tự nó không sai (test đúng phạm vi guidance), nhưng bất biến 1 mà AC hướng tới ("không có số") bị vi phạm ở một cửa khác thuộc cùng nghiệp vụ `cancel_expired_batch` mà DW-06 sinh ra. |
| 1c | DW-06 | AC1 | ⚠️ | Trùng **SR-08 (F02, High)**: `cancel_expired_batch` chỉ kiểm `status == EXPIRED`, ghi `WRITE_OFF` toàn bộ `qty_available` kể cả phần `qty_reserved` của đơn BOOKED còn giữ chỗ → thanh toán sau đó gặp "Xuất vượt tồn", mất giao dịch tiền. Test `test_dw06_ac1_cancel_expired_success` chỉ dựng lô không có đơn giữ chỗ nên không bắt được ca này. |
| 2 | DW-07, DW-08, DW-09 | AC1–10, AC1–7, AC1–8 | ✅ (DW-07-AC6 xem ⚠️) | 18 test registry + `discipline` xanh; `commands.test.ts` 8/8 xanh (vitest chạy lại xác nhận, không chỉ đọc báo cáo cũ) |
| 3a | DW-10, DW-11 | AC1–11, AC1–10 | ⚠️ **DW-10-AC3, DW-07-AC6 (PII)**; ⚠️ **DW-11-AC4/AC5 (IDOR nhẹ)** | Trùng **SR-04+SR-05 (BM-02, High)**: `SCRUB_PII_KEYS` (đọc trực tiếp `apps/ai/policy/rules.py:79-94`) **không có khoá `customer`** (tên khách dạng chuỗi ở `reports.dashboard_summary`) và không có `customer.name` lồng nhánh — xác nhận bằng đọc code, khớp mô tả BM-02. Việc test `test_dw10_ac3_pii_scrubbed_even_for_chu` vẫn xanh vì bộ fixture của nó không đụng đúng field `customer` (chuỗi) hay dashboard command. Trùng **SR-22 (BM-05, Low)**: `reject_ai_action`/`confirm_ai_action` không kiểm owner/assignee_group như `retrieve` — rủi ro thấp (cần biết UUID4) nhưng vẫn là lỗ hổng IDOR nhẹ trên DW-11-AC4/AC5. |
| 3b | DW-12, DW-13 | AC1–11, AC1–9 | ✅ | `test_my_config_api.py` (325 dòng), `test_policy_api.py`, `test_caps.py` xanh; đọc `DW-12-AC6` (tắt AI của tôi), `DW-13-AC1/AC2` (tắt khẩn) — assert đúng field `killed`, `global_mode`, gọi `call` sau đó để xác nhận hiệu lực tức thì, không chỉ đọc response PUT |
| 3c | DW-14, DW-15, DW-16 | AC1–8, AC1–5, AC1–7 | ⚠️ **DW-09-AC8/DW-16-AC5, BR-AI-17** | Trùng **SR-20 (F4, Medium)**: tôi build thật `erp-console` và `grep -l "wllama" .next/static/chunks/6877-*.js` → **có** — chunk này nằm trong `app-build-manifest.json` của `/orders`, `/orders/payments`, `/orders/refunds` (route không AI-only), nghĩa là runtime AI (`wllama`) vẫn bị đóng gói vào bundle của màn nghiệp vụ dù người dùng chưa bật AI, vi phạm "0 request/0 code AI khi tắt". Test hiện có (`test_dw09_ac8`) chỉ kiểm ở tầng unit (`index` trả 410), **chưa từng đo chunk thật** như báo cáo `review-cms-golive-fe-qa.md` đã nêu (mục "AC thiếu bằng chứng"). Tôi xác nhận lại bằng chứng này bằng lệnh build thật, không chỉ tin báo cáo cũ. |
| 4 | DW-17 | AC1–8 | ✅ | `test_nhap_lo.py` xanh; DW-17-AC5 (giá vốn ở response API) đúng — nhưng xem ⚠️ dưới (localStorage) |
| 4 | DW-17 | AC7 (PII) | ⚠️ | Trùng **SR-07 (BM-04, Medium)**: đọc `erp-console/features/purchasing/components/NhapLoForm.tsx` — nháp lưu `lines[].rate` (giá mua) vào `localStorage` khoá cố định `cave_draft_nhap_lo`, không gắn theo user, không xoá khi đăng xuất. Đây là rò **giá vốn** (không phải PII khách) qua localStorage dùng chung máy — đúng như BM-04 mô tả; AC7 chỉ nói "không dữ liệu khách" nên kỹ thuật không sai AC, nhưng vi phạm bất biến 1 (giá vốn) mà story không có AC riêng bắt lỗi này. |
| 5a | DW-18 | AC1–7 | ⚠️ **AC4 (song song)** | Trùng **SR-10 (F05, Medium)**: `publish_batch` không có `atomic`+`select_for_update`, đọc lại đúng như review đã ghi. Test `test_dw18_ac4_hai_lan_huy_lien_tiep` (đọc trực tiếp) chỉ dựng kịch bản **huỷ 2 lần liên tiếp**, không phải kịch bản AC yêu cầu ("Huỷ phiếu **cùng lúc publish lô**"). Đây là ca race thật (publish dùng object cũ từ trước khi huỷ) chưa có test đúng nghĩa. |
| 5b | DW-19, DW-21 | AC1–10, AC1–9 | ✅ (1 ghi nhận Low) | `test_dw19_level_b.py` (323 dòng), `test_dw21_deferred_actions.py` (249 dòng) đọc kỹ AC3/AC4 (hoàn tác) — test thật, gọi API `call` rồi `undo`, kiểm `outcome`, mã lỗi `AI_UNDO_WINDOW_CLOSED`. **Ghi nhận Low** (không phải bug, không chặn): `test_dw21_ac3_job_revokes_scheduled_action_if_conditions_changed` chỉ dựng kịch bản "tắt khẩn theo user" trong 4 kịch bản mà AC liệt kê (cấu hình về C / tắt khẩn / **mất quyền** / **điều kiện nghiệp vụ đổi**); 2 kịch bản còn lại **có** test riêng ở ngữ cảnh cụ thể hơn (`test_dw24_ac4...` cho đóng công tắc vùng đỏ, `test_dw25_ac4_reserved_qty_added_in_window_escalates_to_chu` cho điều kiện nghiệp vụ đổi) nên không phải lỗ hổng thật, chỉ là generic test của DW-21 chưa liệt kê đủ 4 nhánh trong 1 chỗ. |
| 5b | DW-20 | AC1–6 | ✅ | `test_caps.py` xanh, đọc AC1/AC2 (trần của Chủ, `min` khi hạ trần) |
| 5c | DW-22, DW-23 | AC1–5, AC1–7 | ✅ | `test_daily_report.py`, `test_escalate.py` xanh, đọc quyền + PII |
| 6a | DW-24 | AC1–7 | ✅ | `test_dw24_red_zone_switch.py` (229 dòng) đọc kỹ AC2–AC5, kể cả downgrade scheduled action khi đóng công tắc |
| 6a | DW-25 | AC1–7 | ✅ | `test_dw25_close_batch.py` (423 dòng) đọc AC2 (hạ mức), AC4 (điều kiện đổi giữa chừng), AC5 (giá vốn) — test thật, dựng lô đủ điều kiện rồi thay đổi 1 điều kiện, kiểm `downgrade_reason` |
| 6b | DW-26 | AC1–6 | ⚠️ **AC2 (không khớp → chuyển việc)** | Trùng **SR-11 (F06, Medium)**: đọc `apps/sales/payments/auto_confirm.py:166-200` — `_escalate_to_chu` không idempotent: mỗi lần job chạy lại ghi thêm dòng AuditLog `escalate_unmatched_payment` cho **mọi** giao dịch OPEN không khớp (append-only phình vô hạn theo chu kỳ job), và nếu Chủ đã đóng việc thì lần chạy sau **mở lại** ESCALATED. Xác nhận bằng đọc code, khớp mô tả F06. `test_dw26_auto_confirm.py` xanh nhưng không chạy job 2 lần liên tiếp để bắt lỗi này. |
| 6b | DW-27 | AC1–5 | ✅ | `test_dw27_confirm_refund.py` (268 dòng) — đọc AC1/AC2, xác nhận luôn hạ C, `bank_txn_ref` từ model không bao giờ tự ghi |

## Bảng đối chiếu "trùng SR-xx" — bằng chứng tự xác minh (không chỉ đọc báo cáo cũ)

| Mã lỗi gốc | SR-xx (P8, vẫn ☐) | Mức | AC bị ảnh hưởng trong hồ sơ này | Bằng chứng tôi tự chạy lại hôm nay |
|---|---|---|---|---|
| BM-01 | SR-01 | **Critical** | DW-06-AC5 (giá vốn qua `/api/audit-logs/`) | `python -c "from apps.common.cost_keys import COST_KEYS; print('loss_amount' in COST_KEYS)"` → `False` |
| F01 | SR-03 | High | DW-21, DW-25 (job `run_due_ai_actions` kẹt khi lô đã từng bán) | `grep -n "order_id__in" apps/ai/execution/safety.py` → dòng 101/113 vẫn dùng `order_id__in`/`payment_transaction__order_id__in`, trong khi model `PaymentTransaction` không có field `order` (đúng như F01 mô tả); đã có repro R1 sẵn trong `doc/features/2026-09-30-sua-loi-review/repro/` |
| F02 | SR-08 | High | DW-06-AC1 | Đọc `check_cancel_expired_batch`/`cancel_expired_batch` (`apps/inventory/batches/services.py:246-294`) — chỉ kiểm `status==EXPIRED`, không kiểm `qty_reserved` |
| BM-02 | SR-04 | High | DW-10-AC3, DW-07-AC6, DW-14-AC5 | Đọc `SCRUB_PII_KEYS` (`apps/ai/policy/rules.py:79-94`) — không có khoá `customer`/`customer.name` |
| BM-06 | SR-05 | Low (chặn PII) | DW-10 (lệnh đọc `*.retrieve`) | Không tự chạy lại (đã có repro trong review gốc: mọi lệnh `retrieve` trả 502); không ảnh hưởng test hiện có vì test không gọi `retrieve` |
| BM-03 | SR-06 | Medium | DW-03-AC7 (chỉ áp cho `nv_giao`, không áp `cskh`) | Đọc `apps/sales/orders/next_steps.py:179-182` — chỉ lọc `nv_giao`, không gọi `scope_orders_for` như `SalesOrderViewSet.get_queryset` |
| BM-04 | SR-07 | Medium | DW-17-AC7 | Đọc `NhapLoForm.tsx` — `localStorage` lưu `rate` |
| BM-05 | SR-22 | Low | DW-11-AC4/AC5 | Đọc `apps/ai/actions/services.py:147-170` — `reject_ai_action` không kiểm owner |
| F05 | SR-10 | Medium | DW-18-AC4 | Đọc `publish_batch` (`apps/inventory/batches/services.py:145-152`) — không `select_for_update`; đối chiếu test hiện có chỉ test huỷ×huỷ |
| F06 | SR-11 | Medium | DW-26-AC2 | Đọc `_escalate_to_chu` (`apps/sales/payments/auto_confirm.py:166-200`) — không kiểm `created`/trạng thái kết thúc trước khi ghi lại |
| F4 | SR-20 | Medium | DW-09-AC8, DW-16-AC5 (BR-AI-17) | `grep -l wllama erp-console/.next/static/chunks/6877-*.js` → có, và chunk này nằm trong `app-build-manifest.json` của `/orders*` |
| F12 | SR-22 | Low | DW-26/DW-27 escalate (không có Chủ → giao bất kỳ user active) | Đọc `auto_confirm.py:158-160,170` |
| F13 | SR-24 | Low | Vận hành `run_due_ai_actions`/`auto_confirm_exact_payments`, mâu thuẫn V-DW1 vs code | `grep -r "AI_PRODUCTION_READY" doc/ops/` → không có kết quả trong `moi-truong.md` |
| F10 | SR-22 | Low | DW-19-AC3 (hoàn tác) | Đọc `undo_ai_action` (`apps/ai/actions/services.py:177-178,229-239`) — hard-code `"nhap_lo" in command`; hiện an toàn vì chỉ `nhap_lo` đạt mức B |

Không có mã lỗi nào ở trên là **phát hiện mới** của tôi — tất cả đã có trong `review-bao-mat-du-lieu.md` /
`review-tien-kho-ai.md` / `review-cms-golive-fe-qa.md` và đã lên story SR-xx. Việc tôi làm là **tự xác minh lại**
bằng lệnh/đọc code hôm nay (không tin báo cáo suông) và **gắn đúng vào AC nào của hồ sơ AI** bị ảnh hưởng, để khi
P8 sửa xong biết chính xác AC nào cần chạy lại.

## Ngoại lệ & biên đã kiểm (ngoài đường thuận, theo yêu cầu "mỗi AC nghiệp vụ thêm 1 ca")

Các story chính đã có sẵn ca ngoài đường thuận đúng nghĩa (đọc xác nhận, không chỉ đường thuận):
- **Bấm đúp / 2 request tranh chấp**: DW-06-AC3 (`select_for_update`, 1 trong 2 request huỷ lô thắng),
  DW-10-AC7 (idempotency key gửi 2 lần), DW-21-AC5 (2 tiến trình job cùng lúc, `skip_locked`).
- **Vượt tồn / vượt trần**: DW-19-AC5 (vượt kg/lần trong ngày → hạ C), DW-20-AC1/AC2 (NV đặt cao hơn trần Chủ).
- **TTL/hết hạn**: DW-11-AC3 (nháp C hết hạn 15 phút), DW-19-AC4 (hoàn tác hết hạn 10 phút),
  DW-25-AC3 (huỷ lịch trong 30 phút).
- **Công tắc bật/tắt giữa chừng**: DW-12-AC6/DW-13-AC1 (tắt AI của tôi/tắt khẩn có hiệu lực tức thì),
  DW-24-AC4 (đóng công tắc vùng đỏ khi có việc đang SCHEDULED).
- **Lô/phiên bản cũ (stale)**: DW-04-AC6 (phiếu hoàn đã xác nhận ở tab khác), DW-12-AC3 (`base_version` cũ →
  409), DW-13-AC6 (`AI_POLICY_CONFLICT`).

Ca ngoài đường thuận **còn thiếu** (đã nêu ở bảng trên, đều trùng SR-xx nên không viết test mới trùng lặp):
DW-18-AC4 (huỷ × publish đồng thời, trùng SR-10), DW-21-AC3 (đủ 4 nhánh generic, ghi nhận Low không chặn),
DW-26-AC2 (job chạy 2 lần liên tiếp, trùng SR-11).

## Phân quyền (Group × hành động) — xác nhận qua test thật

Đã chạy và đọc: `test_dw07_ac4_group_matrix`, `test_index_api` (4 Group × registry), `test_dw10_ac5_permission_and_idor`,
`test_dw11_ac5_permission_denied_on_confirm`, `test_dw12_ac4` (PUT lệnh ngoài quyền → 400 BR-AI-19),
`test_dw13_ac5` (403 cho `quan_ly`/`nv_kho`/`nv_giao`/`cskh` trên `/api/ai/policy/*`), `test_dw24_ac5`
(`quan_ly` không thấy 3 lệnh vùng đỏ), `test_dw25_ac6`, `test_dw26_ac4`, `test_dw27_ac3`. Tất cả xanh, không
phát hiện lệch ma trận quyền nào **ngoài** các lỗ hổng đã liệt kê ở trên (PII/giá vốn qua các cửa phụ, không
phải qua phân quyền model/Tầng 2).

## Rò giá vốn / Rò PII — kết luận riêng

- **Không có rò giá vốn/PII mới** ngoài 3 đường đã biết và đã có SR-xx: (1) `/api/audit-logs/` thiếu `loss_amount`
  trong `COST_KEYS` (SR-01, Critical), (2) `SCRUB_PII_KEYS` thiếu `customer`/`customer.name` cho lệnh AI đọc
  (SR-04, High), (3) `localStorage` nháp Nhập lô giữ `rate` (SR-07, Medium).
- Toàn bộ đường chính (guidance 4 loại chứng từ, `call` lệnh đọc/ghi, `AiAction`, chỉ mục lệnh, "AI của tôi",
  chính sách Chủ, báo cáo ngày, chuyển việc) đã lọc đúng theo test đọc trực tiếp — không dùng `fields="__all__"`
  (`grep -rn 'fields = "__all__"' backend/apps` → rỗng, tự chạy lại xác nhận).

## Hồi quy

- Toàn bộ 1058 test backend xanh (không riêng app AI) — không có test cũ nào đỏ do các thay đổi của hồ sơ này.
- `makemigrations --check --dry-run` sạch (chỉ có warning `SELLER_*` không liên quan, đã có từ trước).
- `erp-console`: `tsc --noEmit` sạch, `vitest run features/ai` 16/16 xanh.
- Không build lại `frontend/` (Shop) vì hồ sơ AI ghi rõ "Ngoài: Shop" — không đụng.

## Test mới đã thêm

**Không có.** Lý do: mọi khoảng hở tôi tìm thấy khi đọc/kiểm chứng lại đều đã có repro/bằng chứng đầy đủ trong
`review-bao-mat-du-lieu.md`/`review-tien-kho-ai.md`/`review-cms-golive-fe-qa.md` và đã lên story SR-xx (P8), một
số đã có sẵn test tái hiện (R1 cho SR-03). Viết thêm test đỏ trùng nội dung sẽ chỉ lặp lại bằng chứng đã có,
không thêm giá trị, và vi phạm nguyên tắc "lỗi đã có SR-xx thì không báo lại". 1 ghi nhận Low (DW-21-AC3 thiếu
2/4 nhánh generic) không đủ nghiêm trọng để tạo bug mới vì các nhánh đó đã có test ở ngữ cảnh cụ thể hơn
(DW-24-AC4, DW-25-AC4).

## Lỗi mới

**Không có lỗi mới** (Critical/High/Medium/Low) ngoài các mục đã trùng SR-xx ở bảng trên. Ghi nhận thêm (không
phải bug, không chặn):

### G1 — DW-21-AC3 generic test chỉ phủ 1/4 nhánh thu hồi · Ghi nhận (không chặn) · AC DW-21-AC3
- **Bước tái hiện đọc code**: AC liệt kê 4 nhánh khiến job không ghi khi tới hạn: "cấu hình về C, hoặc tắt khẩn,
  hoặc mất quyền, hoặc điều kiện nghiệp vụ đổi". `test_dw21_ac3_job_revokes_scheduled_action_if_conditions_changed`
  chỉ dựng nhánh "tắt khẩn theo user" (`AiConfigVersion.killed=True`).
- **Mong đợi**: có 1 test generic (ở `test_dw21_deferred_actions.py`) phủ cả "mất quyền" (gỡ user khỏi Group giữa
  cửa sổ) cho một lệnh bất kỳ, không chỉ 2 lệnh cụ thể (`close_batch`, `nhap_lo`) đã có test riêng ở DW-24/DW-25.
- **Thực tế**: nhánh "cấu hình về C" và "điều kiện nghiệp vụ đổi" có test ở ngữ cảnh cụ thể hơn (DW-24-AC4 cho
  đóng công tắc vùng đỏ, DW-25-AC4 cho điều kiện lô đổi); nhánh "mất quyền" generic chưa thấy test riêng cho
  job (có test permission ở `call` nhưng không phải cho `AiAction SCHEDULED` bị job chạy quá hạn).
- **Ảnh hưởng**: thấp — mã service `run_due_ai_actions`/`apps/ai/execution/safety.py` đọc lại quyền tại thời điểm
  chạy (kiến trúc chung mọi lệnh đều qua `dispatch_command` → kiểm quyền như request thật), nên nhiều khả năng đã
  đúng, chỉ là thiếu test xác nhận riêng. Không đủ nghiêm trọng để tạo P9; đề xuất gộp vào lần sửa DW-21 nếu P8
  đụng tới file này.

## Lệnh đã chạy (kèm output tóm tắt)

```
cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.ai apps.common.guidance \
  apps.inventory.batches apps.purchasing.receipts apps.sales.orders.tests.test_guidance \
  apps.sales.refunds.tests.test_guidance apps.sales.payments.tests.test_guidance \
  apps.sales.payments.tests.test_dw26_auto_confirm
→ Ran 211 tests in 11.425s — OK

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test
→ Ran 1058 tests in 83.048s — OK

cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py makemigrations --check --dry-run
→ No changes detected (chỉ warning SELLER_* không liên quan)

cd erp-console && npx vitest run features/ai
→ Test Files 2 passed (2), Tests 16 passed (16)

cd erp-console && ./node_modules/.bin/tsc --noEmit
→ sạch (exit 0)

cd backend && .venv/bin/python -c "from apps.common.cost_keys import COST_KEYS; print('loss_amount' in COST_KEYS)"
→ False   # xác nhận SR-01/BM-01 còn tồn tại

grep -n "order_id__in" backend/apps/ai/execution/safety.py
→ dòng 101, 113 vẫn dùng order_id__in (model không có field 'order') — xác nhận SR-03/F01 còn tồn tại

grep -n "SCRUB_PII_KEYS" -A 20 backend/apps/ai/policy/rules.py
→ không có khoá 'customer'/'customer.name' — xác nhận SR-04/BM-02 còn tồn tại

grep -l "wllama" erp-console/.next/static/chunks/6877-*.js
→ có; chunk này nằm trong app-build-manifest.json của /(console)/orders/page — xác nhận SR-20/F4 còn tồn tại

grep -rn 'fields = "__all__"' backend/apps
→ rỗng
```
