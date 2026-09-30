# Rà soát toàn bộ phần AGY làm (P1–P7) — báo cáo tổng
> Điều phối (Claude Opus 5.5) · 2026-09-30 · phạm vi commit `5d26d95..75e5dd3`
> Chi tiết: `A1-code.md` (techlead), `A2-bao-mat-go-live.md`, `A3-ai-digital-worker.md`, `A4-cskh-in-tem.md`, `A5-cms-viet-bai.md` (qa-tester).

## Kết luận
- **Không có lỗi Critical mới.** Critical/High đã biết đều đã có story P8 (SR-01…SR-24) và được xác nhận lại bằng chạy thật.
- **15 lỗi mới** (RA-15 thêm trong P8 Lô 2): 1 High, 6 Medium, 8 Low. Không tự sửa: cần Duy duyệt story (đề xuất gom thành **P10 — sửa lỗi rà soát**, trước đây ghi là P9; xem cuối file).
- **586 AC kiểm lại**: A2 72, A3 220, A4 175, A5 119. Kết quả: ✅ 553 · ❌ 3 · ⏸ 19 · ⚠️ ~10 (test đúng phạm vi hẹp nhưng AC bị vi phạm ở cửa khác; tất cả trùng SR-xx).
  - ❌: GL-05-AC1 (trùng SR-19); CMS-06-AC3 (RA-01); CMS-04-AC2 (RA-06).
  - ⏸: 18 AC của CS-16…CS-18 (story Could, chưa được xây, đúng phạm vi đã duyệt); CMS-04-AC4 (dựa vào test cũ).
- **Bù 7 test BE + 11 script Playwright**, tất cả xanh, để trong repo (danh sách cuối file).

### Hạn chế của lượt rà soát (ghi thật)
- A3 (AI, 220 AC) **không viết test mới** và không chạy Playwright. AC FE của AI dựa trên vitest (16/16), `tsc`, build và grep chunk. Chưa có bằng chứng trình duyệt cho AC FE của AI; phần này để Lô 6 (SR-20/SR-21) bù.
- A2 và A4 đạt AC nhưng **bỏ sót** A1-01/A1-02 (CSKH/giao hàng), vì đây là lỗi ngoài câu chữ AC. Techlead tìm ra khi đọc code.
- Các agent QA chạy song song dùng chung `erp-console/out/` và `frontend/out/`, nên có lúc build bị ghi đè giữa chừng. A4 và A5 đã chạy lại sạch sau khi phát hiện. Từ Bước B, không cho hai agent build cùng lúc.

## Kiểm chứng điều phối tự chạy (A6, sau khi các agent thêm test)
```
backend: Ran 1065 tests in 70.129s — OK          (gốc trước bước A: 1058 OK; +7 test rà soát)
backend: makemigrations --check --dry-run — No changes detected
frontend: npm ci (sạch, không --legacy-peer-deps) · tsc --noEmit OK · next build OK
erp-console: npm ci → ERESOLVE (peerOptional @types/node "^22 || >=24" từ vitest@5.0.2 vs @types/node@26.6.3) = SR-02, chưa sửa
erp-console: npm ci --legacy-peer-deps · tsc --noEmit OK · next build OK · vitest: 9 files, 79 tests passed
Playwright frontend/e2e/ra-soat-a2-golive.py (next dev :3101): TẤT CẢ CA PASS
```
Ghi chú máy: `~/.npm` có file thuộc root nên `npm ci` báo EACCES. Đã chạy với `--cache <scratchpad>`. Duy nên chạy `sudo chown -R 501:20 ~/.npm`.

## Lỗi mới
| Mã | Mức | Nguồn | Tóm tắt | File | Tái hiện |
|---|---|---|---|---|---|
| RA-01 | **High** | A5 B1 | Giá hiển thị sai trên toàn Shop: API trả `price` dạng chuỗi Decimal, `formatVnd` gọi `.toLocaleString` trên chuỗi nên ra `260000.00đ` thay vì `260.000đ` (CatalogGrid, `/shop/item`, checkout, thẻ mặt hàng CMS). Điều phối đã xác nhận: `node -e` cho `"260000.00".toLocaleString("vi-VN")` → `260000.00`. | `frontend/lib/format.ts:1` | A5 §B1. Sửa: `Number(amount)` trong `formatVnd`, thêm test đơn vị. |
| RA-02 | Medium | A1-01 | Hàng chờ CSKH tra `note_id` lẫn `task.pk`: mở đơn cũ (phiếu chưa có task) có thể trả về và thao tác trên **đơn khác**. | `backend/apps/delivery/cskh/api.py:60-70` | `repro/A1/tests_cskh_lookup.py` |
| RA-03 | Medium | A1-02 | `advance_status`/`mark_failed` không khoá dòng, nên ghi đè `CANCELLED` thành `READY`: đơn đã huỷ và hoàn tiền vẫn đi giao. Cùng mẫu SR-10. | `backend/apps/delivery/services.py:74-150` | `repro/A1/tests_delivery_race.py` |
| RA-04 | Medium | A1-03 | Nhân viên tự bật lại AI mà Chủ đã tắt khẩn (`my-config/kill {"killed":false}` → 200). **🔴 Cần Duy chốt luật.** | `backend/apps/ai/settings/services.py:362-389` | `repro/A1/tests_ai.py` |
| RA-05 | Medium | A1-04 | Việc AI không có trạng thái kết thúc: `EXPIRED` bị rollback nên không bao giờ được lưu; job đẩy cả đề xuất đã hết hạn lên Chủ; việc `ESCALATED` không duyệt và không đóng được (409). **Ảnh hưởng SR-11-AC2 (Lô 3).** | `backend/apps/ai/actions/services.py`, `run_due_ai_actions.py:227-256` | `repro/A1/tests_ai_expire.py` |
| RA-06 | Medium | A5 B3 | Mất mạng thật thì `ConsoleGate` chặn toàn màn hình, người viết bài không thấy bản nháp cục bộ khi tải lại (dữ liệu không mất). | `erp-console` `ConsoleGate` | `repro/A5-cms04-reload-offline-auth-gate.py` |
| RA-07 | Low | A1-05 | `confirm_nonce` không được kiểm ở đâu cả; `viewed_at` dùng chung cho mọi người, nên V5 "xem ≥ 3 giây" không đạt. | `ai/actions/services.py:17,53-64` | `repro/A1/tests_ai.py` |
| RA-08 | Low | A1-06 | `decide CANCEL` không kiểm `sales.cancel_paid_order` (hở khi có vai tuỳ biến). | `delivery/cskh/api.py:277-312` | đọc code |
| RA-09 | Low | A1-07 | Dòng thời gian "Chủ ghi nhận chi phí mua" không bao giờ hiện vì không service nào ghi AuditLog đó; test tự dựng log giả. | `inventory/batches/timeline.py:138-158` | grep |
| RA-10 | Low | A1-08 | Input sai → 500: `print_no=abc`, datetime thiếu múi giờ, body JSON mảng ở lệnh AI. | xem A1-08 | đọc code |
| RA-11 | Low | A1-09 | N+1: hàng chờ CSKH ~2,7 query/dòng; phiếu giao; Việc AI; chỉ mục AI. | xem A1-09 | `repro/A1/tests_nplus1.py` |
| RA-12 | Low | A1-10 | Code chết (`site_info_api.py`, `THROTTLE_CSKH_SEARCH`, `backend/spikes/`); kg tính bằng float, chép 3 nơi; kiểm quyền AI chép 2 nơi. | xem A1-10 | grep |
| RA-13 | Low | A1-11 | Test yếu: `test_dw08_ac5` không assert; ca 403 trên thao tác ghi không kiểm dữ liệu đứng yên; test storage FE không chạy trong node. | xem A1-11 | quét AST |
| RA-14 | Low | A1-12 | Thiếu `Cache-Control: no-store` ở `/api/guidance/order/` và lệnh AI đọc đơn. Có thể gộp SR-22. | `common/guidance/api.py:38-54` | đọc code |
| RA-15 | Medium (chờ PO chốt) | QA P8 Lô 2 G1 | Chữ tự do do nhân viên gõ (lý do phiếu hoàn/huỷ) được nối vào `timeline[].label` nên có thể chứa tên khách; bộ lọc PII AI lọc theo **tên khoá** nên không chặn. Lộ qua `sales.salesorder.retrieve` (AI) và API đơn thường. Có từ trước P8. Nếu PO coi chữ tự do là PII → Medium. Đề xuất bỏ `reason` khỏi timeline khi đi qua AI (P10 cùng allowlist PII, liên quan P9). | `backend/apps/sales/orders/timeline.py:136` | `04-qa-report.md` Lô 2 G1 (sửa lời lý do hoàn thành chuỗi có tên giả) |

Repro đỏ ở `repro/` (không nằm trong suite chính). Cách chạy giống `../2026-09-30-sua-loi-review/repro/README.md`: chép vào gói tạm trong scratchpad rồi chạy `manage.py test <gói>.tests_*`.

## Nghi ngờ trong 3 báo cáo review, đã xác minh (A1 §3)
- Chat AI in tên khách: **sai** ở phần màn hình; tên khách vẫn có trong response mạng, thuộc SR-04.
- Ảnh nháp CMS xem được qua URL: **đúng một phần**. Id ảnh ngẫu nhiên nên không đoán được; **Duy cần kiểm bucket GCS không cho liệt kê công khai.**
- Tìm CSKH bằng SĐT đầy đủ trả dòng ngoài phạm vi: **đúng**, đã ở mục "Để sau" của P8.
- `confirm_nonce`: **đúng, nặng hơn** nhận định cũ (RA-07).
- Job AI chết vì transaction hỏng: đúng về lý thuyết, **chưa có đường kích hoạt**. Người sửa SR-03-AC4 cần đặt `try/except` ngoài `atomic` của từng việc.
- Gọi lệnh AI đồng thời trả 500: **đúng**, đã ở "Để sau" của P8.

## Ghi chú cho người làm P8
- SR-06: `escalate_guidance_step` đổi 404/403 thành 400 và in nguyên văn exception. Phải sửa cùng SR-06-AC2 (đòi 404).
- SR-11-AC2 giả định có đường đóng việc `ESCALATED`, nhưng code chưa có (RA-05). Nếu story vướng, ghi "Lệch thiết kế" và dừng SR-11.
- Dev notes các hồ sơ AI, CSKH và go-live không ghi "Lệch thiết kế"; A1 thấy ít nhất 7 lệch chưa được ghi (A1 §5).

## P10 — sửa lỗi rà soát (chờ Duy duyệt, không tự sửa)
> Đổi tên 30/09: trước đây là "Đề xuất P9". P9 nay là **AI local thật** (`doc/ke-hoach-tong.md`). Danh sách cập nhật sau P8: mục `## Đối chiếu sau P8 (30/09)` cuối file.

| Lô P10 | Lỗi | Lý do gom |
|---|---|---|
| 1 | RA-01 | High, sửa 1 dòng FE, nên làm sớm |
| 2 | RA-02, RA-03, RA-08 | Cùng khu CSKH/giao hàng, cùng mẫu khoá dòng như SR-10 |
| 3 | RA-04 (liên quan P9), RA-05, RA-07, RA-15 (liên quan P9) | Vòng đời AI, **cần Duy chốt luật** (ai bật lại AI; cách đóng việc ESCALATED) |
| 4 | RA-06 | FE CMS/ConsoleGate |
| 5 | RA-09…RA-14 | Dọn nợ Low (có thể gộp RA-14 vào SR-22 Lô 7 nếu Duy đồng ý) |

## Test mới đã thêm (xanh, trong repo)
- BE: `backend/apps/sales/payments/tests/test_ra_soat_s03_checkout_throttle.py` (2), `backend/apps/delivery/tests/test_ra_soat_cskh.py` (2), `backend/apps/content/tests/test_ra_soat_extra.py` (3)
- Playwright Shop: `frontend/e2e/ra-soat-a2-golive.py` (43 ca), `ra_soat_cms13_public.py`, `ra_soat_cms06_item_card.py`, `ra_soat_cms14_landing.py`
- Playwright ERP: `erp-console/e2e/ra_soat_cs11_ac6_label_pdf.py`, `ra_soat_x_ac4_storage.py`, `ra_soat_cs02_cs05_mobile_360.py`, `ra_soat_cms03_ac13_mobile.py`, `ra_soat_cms05_upload_mobile.py`, `ra_soat_cms04_autosave.py`, `ra_soat_cms11_ac3_restore_confirm.py`

Lưu ý: `ra_soat_cms06_item_card.py` cố ý **không** assert định dạng giá (để xanh trong khi RA-01 chưa sửa). Docstring của nó
nhắc repro `A5-format-vnd-string-price.py` nhưng file này không được tạo; bằng chứng RA-01 là lệnh `node -e` ở bảng trên.
Khi sửa RA-01, thêm assert định dạng `x.xxx` vào script này.
Các script Playwright cần server đang chạy (và `seed_demo` trên SQLite dev); cách chạy ghi trong docstring từng file.

## Đối chiếu sau P8 (30/09)
> Tech Lead (Claude Opus) · 2026-09-30 · bước "Cuối" của `../2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md`.
> Phạm vi: mọi mã lỗi trong 3 báo cáo `../2026-09-30-review-p1-p7/`, bảng RA ở trên, mục nợ/Low/⏸ trong `03b-review-techlead.md` và `04-qa-report.md` (Lô 1–7).
> Bằng chứng: commit từng lô trong `02c-giao-viec.md` (`git log 75e5dd3..HEAD`), `03-dev-notes.md`, cộng đọc lại code trên `main` @ `105f4de`
> (grep từng chỗ sửa, ví dụ `COST_KEYS` có `loss_amount`, `safety.py` dùng `sales_order_id__in`, `publish_batch` có `select_for_update`, `NoStoreMixin`
> ở đơn/khách, dashboard không còn `customer`, `erp-console/app/ai-spike/` không còn). Không build, không chạy test (Lô 8 đang sửa `frontend/`, `erp-console/`).
> Ký hiệu: ✅ đã sửa (lô · commit) · ⏸ đã sửa hoặc đã chấp nhận, còn chờ kiểm trên Postgres/staging · ⏳ còn, kèm nơi đề xuất đưa vào.
> Hai báo cáo dùng trùng chữ F: **F01–F13** (hai chữ số) là `review-tien-kho-ai.md`, **F1–F14** (một chữ số) là `review-cms-golive-fe-qa.md`.
> Commit P8: Lô 1 `fa4fc37` · Lô 2 `f6dffb1` · Lô 3 `97ce2f9` · Lô 4 `f2de55c` · Lô 5 `84eafe4` · Lô 6 `2af87b0` · Lô 7 `f95b85d` · Lô 8 chưa commit (đang làm).

### Tổng
| Nguồn | ✅ | ⏸ | ⏳ | Tổng |
|---|---|---|---|---|
| Review bảo mật BM-01…07 + §4 | 8 | 0 | 0 | 8 |
| Review tiền-kho-AI F01…F13 + 3 nghi ngờ | 14 | 1 | 1 | 16 |
| Review CMS/go-live F1…F14 + AC thiếu bằng chứng + "Để sau" P8 | 14 | 1 | 3 | 18 |
| Rà soát RA-01…RA-15 | 0 | 0 | 15 | 15 |
| Nợ techlead `03b` Lô 1–7 | 26 | 1 | 24 | 51 |
| Ghi nhận QA `04` Lô 1–7 | 5 | 6 | 12 | 23 |
| **Cộng** | **67** | **9** | **55** | **131** |

Không còn lỗi Critical nào của sản phẩm đang mở. Mã ⏳ mức cao nhất là **RA-01 (High)**, đang sửa ở Lô 8. Còn 7 mã ⏳ mức Medium: RA-02…RA-06, RA-15 và Lô7-D7-1 (chờ Duy).
Riêng QA3-audit chưa xếp mức: `npm audit` báo 1 critical và 1 high trong gói phụ thuộc của `erp-console`, chưa ai kiểm xem có khai thác được không. Nên xử lý sớm bằng luồng NHANH.
Các ca ⏸ đều là tranh chấp thật trên Postgres hoặc cần backend staging thật. SQLite bỏ qua `select_for_update`, nên máy dev không chứng minh được.

### 1. Review bảo mật dữ liệu (`review-bao-mat-du-lieu.md`)
| Mã | Mức | Mô tả | Trạng thái | Ghi chú |
|---|---|---|---|---|
| BM-01 | Critical | Nhật ký lộ `loss_amount` nên suy ra được giá vốn | ✅ SR-01 · Lô 1 `fa4fc37` | `COST_KEYS` thêm 8 khoá. Admin Nhật ký lọc thêm ở Lô 5 (QA B1) |
| BM-02 | High | Bộ lọc PII của AI để lọt tên khách (`customer`) | ✅ SR-04 · Lô 2 `f6dffb1` | Vẫn là denylist theo tên khoá, xem 03b Lô 2 N1 bên dưới |
| BM-03 | Medium | Guidance đơn không lọc phạm vi `cskh` | ✅ SR-06 · Lô 2 `f6dffb1` | `orders/scope.py::scope_orders_for` |
| BM-04 | Medium | Nháp Nhập lô lưu giá mua vào `localStorage` dùng chung | ✅ SR-07 · Lô 2 `f6dffb1` | Dọn khoá cũ, xem QA Lô 2 N1 |
| BM-05 | Low | IDOR: confirm/reject việc AI của người khác | ✅ SR-22 · Lô 7 `f95b85d` | Còn L7-2, L7-3 |
| BM-06 | Low | Lệnh AI `retrieve`/`partial_update` sai `detail` (502/500) | ✅ SR-05 · Lô 2 `f6dffb1` | `batch_pnl`/guidance qua AI trả 400, việc còn lại là 03b Lô 2 L6 |
| BM-07 | Low | `_is_cost_authorized` nhận `view_profitreport` | ✅ SR-22 · Lô 7 `f95b85d` | |
| §4 | — | Dashboard trả tên + 4 số cuối SĐT; đơn/khách thiếu `no-store` | ✅ SR-17 Lô 5 · SR-22 Lô 7 | |

### 2. Review tiền, kho, AI (`review-tien-kho-ai.md`)
| Mã | Mức | Mô tả | Trạng thái | Ghi chú |
|---|---|---|---|---|
| F01 | High | AI chốt lô đã bán gặp `FieldError`, job AI kẹt | ✅ SR-03 · Lô 1 `fa4fc37` | ⏸ P-1 (2 tiến trình job) |
| F02 | High | Huỷ lô quá hạn xoá cả phần giữ chỗ, mất giao dịch tiền | ✅ SR-08 · Lô 3 `97ce2f9` | ⏸ P-3 |
| F03 | High | CSKH xác nhận đơn đã tự huỷ, kho soạn đơn huỷ | ✅ SR-09 · Lô 3 `97ce2f9` | ⏸ P-4 |
| F04 | High | Huỷ đơn đã trả tiền không đảo doanh thu | ✅ SR-12/13/14 · Lô 4 `f2de55c` | ⏸ P-5. Duy tự chạy `backfill_credit_notes` |
| F05 | Medium | `publish_batch` không khoá, mở bán lô của phiếu đã huỷ | ✅ SR-10 · Lô 3 `97ce2f9` | ⏸ P-2 |
| F06 | Medium | Job DW-26 phình Nhật ký, mở lại việc đã đóng | ✅ SR-11 · Lô 3 `97ce2f9` | Còn 03b Lô 3 N1 |
| F07 | Low | Hạn mức ngày AI tính theo UTC | ✅ SR-22 · Lô 7 `f95b85d` | |
| F08 | Low | Thứ tự khoá task→phiếu ngược, có thể deadlock | ✅ SR-22 · Lô 7 `f95b85d` | ⏸ P-7 |
| F09 | Low→nâng | Chốt được lô EXPIRED còn tồn | ✅ SR-15/16 · Lô 5 `84eafe4` | |
| F10 | Low | Undo AI gán cứng `cancel_receipt` | ✅ SR-22 · Lô 7 `f95b85d` | Còn L7-4 |
| F11 | Low | Huỷ phiếu nhập bị tính là "lỗ hết hạn" | ✅ SR-15-AC6 · Lô 5 `84eafe4` | D5-1 |
| F12 | Low | Không có Chủ thì giao việc cho user bất kỳ; `{exc}` vào log | ✅ SR-22 · Lô 7 `f95b85d` | |
| F13 | Low | Thiếu tài liệu vận hành job, câu V-DW1 ngược | ✅ SR-24 · Lô 7 `f95b85d` | `doc/ops/moi-truong.md`; V-DW1 ở 02c AI đã đính chính |
| NN-1 | — | Nghi ngờ: transaction hỏng thành poison pill | ✅ SR-03 · Lô 1 | `try/except` ngoài `atomic`, `_mark_failed` mở transaction mới |
| NN-2 | Low | `POST /api/ai/commands/<id>/call/` đồng thời trả 500, phát lại việc B ra `proposal` | ⏳ P10 lô 3 (liên quan P9) | "Để sau" của P8 |
| NN-3 | — | `test_dw21_ac5` chỉ chứng minh tuần tự | ⏸ P-1 | |

### 3. Review CMS, go-live, FE, QA (`review-cms-golive-fe-qa.md`)
| Mã | Mức | Mô tả | Trạng thái | Ghi chú |
|---|---|---|---|---|
| F1 | Medium | IDOR ảnh khi tạo bài | ✅ SR-18 · Lô 6 `2af87b0` | Thêm phòng thủ L6-1 ở Lô 7 |
| F2 | Low | `safeHref` Shop nhận `//` và `/\` | ✅ SR-23 · Lô 7 `f95b85d` | 40 payload hai bên |
| F3 | Medium | Link bằng chứng đồng ý mở sai phiên bản | ✅ SR-19 · Lô 6 `2af87b0` | |
| F4 | Medium | Code AI nằm trong chunk màn nghiệp vụ (BR-AI-17) | ✅ SR-20 · Lô 6 `2af87b0` | `check-ai-chunks.mjs` xanh |
| F5 | Low | 3 test consent rỗng hoặc yếu | ✅ SR-24 · Lô 7 `f95b85d` | |
| F6 | Low | `apiFetch` đổi hành vi 404/410 mà không ghi lệch | ✅ SR-23 · Lô 7 `f95b85d` | |
| F7 | Low | ItemCard gọi catalog cho mỗi thẻ | ✅ SR-23 · Lô 7 `f95b85d` | |
| F8 | Low | Ảnh thân bài thiếu `srcSet` | ✅ SR-23 · Lô 7 `f95b85d` | |
| F9 | Low | Không có mock `xss-mau` và Playwright XSS | ✅ SR-24 · Lô 7 `f95b85d` | |
| F10 | Low | Khối CSKH chép 2 nơi, `site-info` gọi 3 lần, 2 giờ gọi | ✅ SR-23 · Lô 7 `f95b85d` | Phần BE (một nguồn giờ) là D7-1 ⏳ |
| F11 | Low | `content/edit/page.tsx` quá dài (nay 1578 dòng), barrel `features/guidance/index.ts` | ⏳ backlog | "Để sau" của P8. Không làm song song với Lô 8, vì Lô 8 đang sửa file này |
| F12 | Low | Spike AI FE còn sót | ✅ SR-23 · Lô 7 `f95b85d` | |
| F13 | Info | Chuỗi `wllama` trong chunk layout | ✅ SR-20 · Lô 6 `2af87b0` | |
| F14 | Info | Tem QR dùng `dangerouslySetInnerHTML`, mất `note` khi chuyển trang đăng nhập | ✅ SR-23 · Lô 7 `f95b85d` | Kéo theo L7-1 |
| AC-FE | QA | Bảng "AC thiếu bằng chứng" | ✅ SR-21 Lô 6 (go-live, CSKH) · SR-20 Lô 6 (DW-09-AC8) · bước A `6c5868e` (CMS) | CMS-06-AC3 thuộc RA-01, CMS-04-AC2 thuộc RA-06 |
| DS-1 | — | "Để sau" P8: bucket GCS ảnh CMS có cho liệt kê công khai không | ⏸ P-10 (Duy kiểm trên GCS) | Việc vận hành |
| DS-2 | — | "Để sau" P8: tìm CSKH bằng SĐT đầy đủ trả dòng ngoài phạm vi (dò được "có phải khách") | ⏳ backlog, hỏi `legal-vn` | Bất biến 9. Có throttle 30/phút |
| DS-3 | — | "Để sau" P8: `period_pnl` chưa tính lỗ hết hạn, hỏng, trả NCC theo kỳ | ⏳ backlog (cần BA/Duy) | Đổi nghiệp vụ báo cáo |

### 4. Rà soát AGY (RA, bảng trên)
| Mã | Mức | Mô tả | Trạng thái | Ghi chú |
|---|---|---|---|---|
| RA-01 | High | Giá Shop hiện `260000.00đ` | ⏳ **đang ở Lô 8** (SR-25) | Working tree đang sửa `frontend/lib/format.ts`. Sau Lô 8 thêm assert giá vào `ra_soat_cms06_item_card.py` |
| RA-02 | Medium | Hàng chờ CSKH tra lẫn `note_id` và `task.pk` | ⏳ P10 lô 2 | Code chưa đổi (`cskh/api.py:67`) |
| RA-03 | Medium | `advance_status`/`mark_failed` không khoá, CANCELLED bị ghi đè thành READY | ⏳ P10 lô 2 | Chưa có `select_for_update` |
| RA-04 | Medium | Nhân viên tự bật lại AI mà Chủ đã tắt | ⏳ P10 lô 3 · **liên quan P9** (bật AI hai tầng) | 🔴 Duy chốt luật. `doc/ke-hoach-tong.md` đã ghi RA-04 trong P9. Nếu P9 làm thì bỏ khỏi P10 |
| RA-05 | Medium | Việc AI không có trạng thái kết thúc (EXPIRED bị rollback, ESCALATED kẹt) | ⏳ P10 lô 3 | `actions/services.py:66-68` vẫn `save` rồi `raise` trong `atomic` |
| RA-06 | Medium | Mất mạng thì `ConsoleGate` che bản nháp CMS | ⏳ P10 lô 4 | |
| RA-07 | Low | `confirm_nonce` không được kiểm, `viewed_at` dùng chung | ⏳ P10 lô 3 | |
| RA-08 | Low | `decide CANCEL` không kiểm `sales.cancel_paid_order` | ⏳ P10 lô 2 | |
| RA-09 | Low | Dòng thời gian "Chủ ghi nhận chi phí mua" không bao giờ hiện | ⏳ P10 lô 5 | Nếu ghi audit, dùng khoá thuộc `COST_KEYS` (03b Lô 1 N1) |
| RA-10 | Low | Input sai trả 500 (`print_no=abc`, datetime thiếu múi giờ, body mảng) | ⏳ P10 lô 5 | Gộp QA L7-Q3 (DELETE khách trả 500) |
| RA-11 | Low | N+1 ở hàng chờ CSKH, phiếu giao, Việc AI, chỉ mục AI | ⏳ P10 lô 5 | Gộp 03b Lô 4 L4 (`period_pnl`) |
| RA-12 | Low | Code chết (`site_info_api.py`, `THROTTLE_CSKH_SEARCH`, `backend/spikes/`), kg float chép 3 nơi | ⏳ P10 lô 5 | Cả ba file và biến vẫn còn |
| RA-13 | Low | Test yếu (`test_dw08_ac5` không assert, 403 không kiểm dữ liệu đứng yên) | ⏳ P10 lô 5 | |
| RA-14 | Low | Thiếu `no-store` ở guidance đơn và lệnh AI đọc | ⏳ P10 lô 5 | SR-22 mới phủ đơn/khách. Gộp QA L7-Q2 |
| RA-15 | Medium (chờ PO) | Lý do hoàn/huỷ (chữ tự do) vào `timeline[].label`, qua AI | ⏳ P10 lô 3 · **liên quan P9** | Làm cùng allowlist PII (03b Lô 2 N1) |

### 5. Nợ và Low trong `03b-review-techlead.md`
| Mã | Mức | Mô tả | Trạng thái | Ghi chú |
|---|---|---|---|---|
| Lô1-L1 | Low | Test SR-03 phải assert đúng 404 | ✅ Lô 1 `fa4fc37` | |
| Lô1-L2 | Low | `select_for_update` khoá cả dòng user | ✅ Lô 1 `fa4fc37` | `of=("self",)` |
| Lô1-L3 | Low | Sentinel giá vốn dễ trùng micro giây | ✅ Lô 1 `fa4fc37` | |
| Lô1-L4 | Low | Nhánh AI tắt của job chưa cô lập lỗi | ✅ Lô 7 `f95b85d` | |
| Lô1-L5 | Low | Việc FAILED chỉ owner thấy, Chủ không có trong hộp việc | ⏳ P10 lô 3 | Trùng QA Lô 1 N2 |
| Lô1-N1 | Low | Timeline đọc khoá `amount` cho chi phí mua | ⏳ gộp RA-09 | |
| Lô2-L1 | Low | Giữ idempotency key trong nháp khi F5 | ✅ Lô 2 `f6dffb1` | |
| Lô2-L2 | Low | Fixture quét PII rỗng với `nv_giao`/`cskh` | ✅ Lô 7 `f95b85d` | `SR24Fixture` |
| Lô2-L3 | Low | Hàm localStorage cũ ở `purchasing/api.ts` | ✅ Lô 7 `f95b85d` | |
| Lô2-L4 | Low | `auth` import ruột `purchasing` | ✅ Lô 7 `f95b85d` | `shared/lib/drafts.ts` |
| Lô2-L5 | Low | Thông điệp 404 guidance lặp `doc_id` | ✅ Lô 7 `f95b85d` | |
| Lô2-L6 | Low | `dispatch_command` chưa ánh xạ tham số URL (`batch_pnl`, guidance qua AI) | ⏳ P10 lô 3 · liên quan P9 | Chạy lại quét PII trước khi mở guidance qua AI |
| Lô2-N1 | Low | Lọc PII vẫn là denylist theo tên khoá | ⏳ P10 lô 3 · liên quan P9 | Chuyển sang allowlist cùng RA-15 |
| Lô2-N2 | Low | APIView ghi có `<pk>` không kiểm phạm vi `target_id` trước khi tạo việc | ⏳ backlog | Chưa có lỗ vì 4 APIView trong registry đều chỉ đọc |
| Lô3-L1 | Low | Nhánh chết `CONFIRM_ORDER` trong `auto_confirm` | ✅ Lô 7 `f95b85d` | |
| Lô3-L2 | Low | Bộ đếm `escalated` đếm cả no-op, `args.reason` cũ | ✅ Lô 7 `f95b85d` | Trùng QA Lô 3 N2 |
| Lô3-L3 | Low | `check_close_batch` chép truy vấn đơn mở | ✅ Lô 5 `84eafe4` | `_open_orders_count` |
| Lô3-L4 | Low | CSKH: 3 thao tác khác thiếu nút Tải lại khi STALE | ✅ Lô 7 `f95b85d` | Trùng QA Lô 3 N4 |
| Lô3-N1 | Low | `_escalate_to_chu` `get_or_create` kéo việc của Chủ sang ESCALATED, có thể `MultipleObjectsReturned` | ⏳ P10 lô 3 (+ ⏸ P-8) | Trùng QA Lô 3 N1, D7-2 |
| Lô3-N2 | — | Tranh chấp thật `cancel_receipt` ∥ `publish_batch`, `cancel_expired_batch` ∥ giữ chỗ | ⏸ P-2, P-3 | |
| Lô4-M1 | Medium | Admin chứng từ đảo lộ `unit_cost` | ✅ Lô 4 `f2de55c` | `get_fields` trong `sales/admin.py` |
| Lô4-T1 | Low | Test `period_pnl` đỏ theo giờ (UTC) | ✅ Lô 4 `f2de55c` | `timezone.localdate()` |
| Lô4-L1 | Low | FE chưa có kind `credit_note_issued` | ✅ Lô 7 `f95b85d` | Trùng QA Lô 4 N4 |
| Lô4-L2 | Low | Dry-run `backfill_credit_notes` chưa in tháng huỷ và tháng hoàn | ⏳ P10 lô 1, **làm trước khi Duy chạy `--apply`** | Chỉ in tháng, không in giá vốn |
| Lô4-L3 | Low | KPI "doanh thu hôm nay" âm vào ngày `--apply` | ✅ ghi hướng dẫn ở 02c | Muốn lọc `backfilled=False` thì Duy quyết |
| Lô4-L4 | Low | `period_pnl` N+1 | ⏳ P10 lô 5 | Trùng QA Lô 4 N3 |
| Lô4-D1 | — | Hoàn một phần rồi huỷ làm đổi số kỳ cũ | ✅ Lô 4 (Duy chọn phương án B) | |
| Lô4-G6 | Low | Combo: `qty × rate` của dòng chứng từ ≠ `amount` | ⏳ backlog | Nợ có sẵn. Trùng QA Lô 4 N2 |
| Lô4-G7 | — | Chưa có màn ERP xem chứng từ đảo (chỉ Admin superuser) | ⏳ backlog (cần story) | Nguyên tắc "làm xong ở ERP" |
| Lô4-G8 | — | FE báo cáo kỳ và dashboard phải hiện được số âm | ⏳ backlog QA | Kiểm cùng Lô 8 nếu kịp |
| Lô5-T5-1 | Low | Thiếu test luật sàn AI chặn lô EXPIRED còn tồn | ✅ Lô 5 `84eafe4` | |
| Lô5-T5-2 | Low | Thiếu test dùng lại `request_id` sang lô khác | ✅ Lô 5 `84eafe4` | |
| Lô5-M5-1 | Medium | Bản build thật ERP chứa mock (`demo1234`) | ✅ Lô 5 `84eafe4` · M5-1b Lô 6 `2af87b0` | `check-no-mock.mjs` |
| Lô5-L5-1 | Low | Danh sách lô EXPIRED chỉ trang 1, lọc ở FE | ✅ Lô 7 `f95b85d` | `has_stock=1` |
| Lô5-L5-2 | Low | `runSimple` chặn bấm đúp bằng state | ⏳ backlog | `BatchDetailSheet.tsx:105`. Bấm lần hai chỉ nhận 400 |
| Lô5-L5-3 | Low | Mock `overview`/`guidance` import ruột `inventory/mock` | ⏳ backlog (hoặc P8b) | |
| Lô5-L5-4 | Low | Sổ chi tiết thiếu nhãn "Trả NCC", docstring `safety.py` cũ | ⏳ P10 lô 5 | Trùng QA Lô 5 L5-4 |
| Lô5-D5-1 | — | F11 đổi số hiển thị "hết hạn" của lô đã chốt | ⏳ chờ Duy xác nhận giữ nguyên | Không đổi lãi lỗ |
| Lô6-F6-1 | High | Nút "Nhờ" mất khi AI tắt | ✅ Lô 6 `2af87b0` | |
| Lô6-F6-2 | Medium | "Để AI làm" chỉ hiện sau khi mở tab Trợ lý | ✅ Lô 6 `2af87b0` | Theo `step.ai` |
| Lô6-L6-1 | Low | Khôi phục hoặc đăng bài không kiểm lại ảnh | ✅ Lô 7 `f95b85d` | |
| Lô6-L6-2 | Low | "Tóm tắt" phụ thuộc việc mở tab Trợ lý; có thể thêm `ai_enabled` vào guidance | ⏳ P9 | Cổng AI và model trên máy |
| Lô6-L6-3 | Low | `check-no-mock.mjs` chưa lấy seed nội tuyến từ `api.ts`, chưa chặn khi seed ít hơn 10, chưa có trong runbook | ⏳ P10 lô 1, **trước lần deploy tới** | Script và `moi-truong.md` chưa đổi |
| Lô7-L7-1 | Medium | Open redirect ở `safeNext` đăng nhập ERP | ✅ Lô 7 `f95b85d` | |
| Lô7-L7-2 | Low | `retrieve` Việc AI chép tay bộ lọc | ⏳ P10 lô 5 | Dùng `visible_actions_for` |
| Lô7-L7-3 | Low | Undo trả 403 (lộ việc có tồn tại) | ⏳ P10 lô 3 | Đổi sang 404 |
| Lô7-L7-4 | Low | `hasattr(view_cls, cancel_act)` nhận cả thuộc tính không phải `@action` | ⏳ P10 lô 3 | Thêm test hoàn tác DONE khi AI tắt |
| Lô7-L7-5 | Low | (a) chú thích `safeHref` cũ; (b) BE bỏ `#neo`, không chặn DEL/C1, `r"/\ "` thừa | ⏳ (b) P10 lô 5 · ✅ (a) Lô 7 | Tính một mã, trạng thái ⏳ |
| Lô7-D7-1 | Medium (câu cho khách) | Hai giờ gọi mặc định lệch nhau (`7:00–20:00` và `07:00-21:00`) | ⏳ chờ Duy + `legal-vn` → P10 lô 5 | `settings.py:340` chưa đổi |
| Lô7-G3 | Low | Việc SCHEDULED lỗi mãi thì bị thử lại mãi, không ai biết | ⏳ P10 lô 3 · liên quan P9 | Đếm số lần thử, quá N lần thì ESCALATED |
| Lô7-P8b | — | Định danh mới của Lô 7 chưa có trong rà soát đặt tên (`cskhSetStatus`, `CallNoticeBox`, `callHours`, 12 file `test_p8_lo7_*`) | ⏳ P8b | Bổ sung vào `2026-09-30-dat-ten-tieng-anh/01-ra-soat-dat-ten.md` |

### 6. Ghi nhận QA trong `04-qa-report.md` (mục chưa trùng bảng trên)
| Mã | Mức | Mô tả | Trạng thái | Ghi chú |
|---|---|---|---|---|
| QA1-N3 / QA3-N5 | Doc | Chữ story/02b lệch code (403 và 404, 200 và 201, PAID và PROCESSING, `code` và `text`, README R2/R3) | ⏳ điều phối nhờ PO sửa chữ | Không sửa code |
| QA2-⏸ | — | SR-05-AC5 "SR-04 và SR-05 cùng commit" | ✅ `f6dffb1` | |
| QA2-N1 | Low | Khoá nháp cũ `cave_draft_nhap_lo` (có giá) chỉ bị dọn khi đăng xuất, đổi người hoặc mở form | ⏳ backlog | Dọn khi đổi user đã có (`AuthProvider.tsx:178`). Chưa dọn ngay lúc khởi động |
| QA2-N2 | Low | Bấm "Nhờ" 2 lần hoặc 2 phiên tạo 2 việc ESCALATED | ⏳ P10 lô 3 | Trùng QA Lô 6 L6-3 |
| QA3-N3 | Low | Thông điệp "0 đơn" khi `qty_reserved > 0` mà không có đơn giữ | ⏳ backlog | Chỉ xảy ra khi sửa DB tay |
| QA3-N6 | Low | "Cá thu 2,000 kg · 2.000 kg" định dạng kg lặp và sai | ⏳ kiểm sau Lô 8. Lô 8 không phủ kg thì đưa vào P10 lô 4 | SR-25 chỉ phủ tiền và giờ |
| QA3-audit | Chưa xếp mức (npm audit: 1 critical, 1 high) | `npm ci` báo 27 lỗ hổng gói ở `erp-console` (1 critical, 1 high) | ⏳ backlog, **nên sớm** (luồng NHANH riêng) | Không đổi `next`/`react` khi Duy chưa duyệt |
| QA5-B1 | Critical (phạm vi hẹp) | Admin Nhật ký lộ `supplier_refund_amount` cho staff không phải Chủ | ✅ Lô 5 `84eafe4` | `redact_cost` trong `accounts/admin.py` |
| QA5-L5-1 | Low | `qty` nhận `"1_0"`, `request_id` nhận số nguyên | ⏳ backlog | |
| QA5-L5-2 | Low | Response trả `qty_available` là số thực JSON | ⏳ P10 lô 5 | Trái quy ước Decimal. Nên trả chuỗi |
| QA5-L5-3 | Low | Không có trần cho `supplier_refund_amount`, lô có thể có `total_cost` âm | ⏳ backlog (cần Duy) | Chỉ Chủ nhập |
| QA5-⏸ E10 | — | Trả NCC song song, cùng `request_id` gửi đồng thời cho 2 lô | ⏸ P-6 | |
| QA6-B1 | Medium | Bản build Shop chứa mock | ✅ Lô 6 `2af87b0` (M5-1b) | |
| QA6-B2 | Low | `recallOrderContact` nhận SĐT đầy đủ | ✅ Lô 6 `2af87b0` | |
| QA6-L6-4 | Low | Fixture `ra-soat-a2-golive.py` cứng giờ hết hạn | ✅ Lô 6 (sửa test) | |
| QA6-⏸ | — | Ô ma trận `cskh` trên backend thật (ERP) | ⏸ P-9 | |
| QA7-L7-Q1 | Low | `cogs_reversed` chưa có trong `COST_KEYS` | ⏳ P10 lô 1 (rẻ, chặn rò giá vốn từ trước) | Hiện chỉ người có quyền thấy |
| QA7-L7-Q2 | Low | API hoàn tiền, thanh toán, hoá đơn thiếu `no-store` | ⏳ P10 lô 5 | Gộp RA-14 |
| QA7-L7-Q3 | Low | `DELETE` khách đã có đơn trả 500 thay vì 409 | ⏳ P10 lô 5 | Gộp RA-10 |
| QA7-⏸ F08 | — | F08 tranh khoá thật giữa 2 tiến trình | ⏸ P-7 | |
| QA7-⏸ N1 | — | `get_or_create` đồng thời | ⏸ P-8 | |
| QA7-⏸ cskh | — | Giao diện `cskh` của L5-1 trên backend thật | ⏸ P-9 | |
| QA1-⏸ N4 | — | 2 tiến trình job AI cùng lúc | ⏸ P-1 | |

### 7. Danh sách ⏳ còn lại, gom theo nơi đưa vào
**Lô 8 (đang làm):** RA-01 (High). Sau Lô 8 kiểm lại QA3-N6 (định dạng kg) và Lô4-G8 (số âm).

**P8b — đặt tên tiếng Anh:** Lô7-P8b (bổ sung định danh Lô 7 vào rà soát). Có thể gộp Lô5-L5-3 (chuyển mock sang `shared/lib/`) và F11 (tách `content/edit/page.tsx`, bỏ barrel), vì đều là di chuyển file, không đổi hành vi.

**P9 — AI local thật:** Lô6-L6-2 (tín hiệu AI bật cho "Tóm tắt"). RA-04 đã nằm trong kế hoạch P9 ở `doc/ke-hoach-tong.md`.

**P10 — sửa lỗi rà soát (chờ Duy duyệt story):**
| Lô P10 | Mã | Lý do gom |
|---|---|---|
| 1 | Lô4-L2, Lô6-L6-3, QA7-L7-Q1 | Rẻ, **làm trước lần deploy tới hoặc trước `--apply`** |
| 2 | RA-02, RA-03, RA-08 | CSKH và giao hàng, cùng mẫu khoá dòng như SR-10 |
| 3 | RA-04 (liên quan P9), RA-05, RA-07, RA-15 (liên quan P9), Lô1-L5, Lô2-L6, Lô2-N1, Lô3-N1, Lô7-L7-3, Lô7-L7-4, Lô7-G3, QA2-N2, NN-2 | Vòng đời và an toàn AI. 🔴 Duy chốt luật: ai được bật lại AI, cách đóng việc ESCALATED, retry quá N lần. Phần nào P9 đã làm thì bỏ khỏi đây |
| 4 | RA-06 (+ QA3-N6 nếu Lô 8 không phủ) | FE CMS, ConsoleGate |
| 5 | RA-09…RA-14, Lô4-L4, Lô5-L5-4, Lô7-L7-2, Lô7-L7-5(b), Lô7-D7-1 (sau khi Duy chốt), QA5-L5-2, QA7-L7-Q2, QA7-L7-Q3 | Dọn nợ Low BE: 500 do input sai, N+1, `no-store`, code chết, test yếu |

**Backlog (chưa xếp lịch):** F11 (nếu không gộp P8b), DS-2 (hỏi `legal-vn`), DS-3 (cần BA), Lô2-N2, Lô4-G6, Lô4-G7 (cần story màn ERP chứng từ đảo),
Lô4-G8, Lô5-L5-2, Lô5-L5-3, Lô5-D5-1 (Duy xác nhận), QA1-N3/QA3-N5 (sửa chữ doc), QA2-N1, QA3-N3, QA3-audit (**nên làm sớm**),
QA5-L5-1, QA5-L5-3.

### 8. Ca ⏸ cần chạy sau khi deploy staging (Postgres thật, dữ liệu giả)
QA chạy bằng hai tiến trình hoặc hai request song song thật (ví dụ hai `manage.py shell` hoặc `curl … & curl …`), mỗi ca chạy cả hai thứ tự A→B và B→A, sau đó so sổ kho, AuditLog và trạng thái:
| Mã | Ca | Kỳ vọng |
|---|---|---|
| P-1 | Hai tiến trình `run_due_ai_actions` chạy cùng lúc trên cùng tập việc SCHEDULED (Lô 1 N4, `test_dw21_ac5`, L2 `of=("self",)`) | Mỗi việc chạy đúng 1 lần. Không bỏ qua việc do khoá dòng `auth_user` |
| P-2 | `cancel_receipt` ∥ `publish_batch` cùng lô (SR-10, F05) | Đúng một thao tác thành công. Lô không bị `SELLING` sau khi phiếu đã `CANCELLED` |
| P-3 | `cancel_expired_batch` ∥ tạo đơn giữ chỗ cùng lô (SR-08, F02) | Không có WRITE_OFF phần đang giữ, hoặc đơn bị từ chối. Tồn không âm |
| P-4 | `record_call(CONFIRMED)` ∥ `auto_cancel_overdue` cùng phiếu (SR-09, F03) | Phiếu không quay về `PREPARING` sau khi đơn đã huỷ. Bên thua nhận 409 `STALE_STATE` |
| P-5 | Hai lần huỷ đồng thời cùng một đơn đã thanh toán (SR-12, F04) | Đúng 1 chứng từ đảo, kho hoàn 1 lần |
| P-6 | Trả NCC song song cùng lô, và cùng `request_id` gửi đồng thời cho 2 lô (SR-16, QA5 E10) | 400 `BR-MH-08`, không 500 (`IntegrityError`). Tồn đúng |
| P-7 | `escalate_expired_windows` ∥ `record_call` cùng phiếu (F08) | Không deadlock, không 500 cho CSKH |
| P-8 | Job `auto_confirm_exact_payments` chạy chồng 2 lần, và trường hợp Chủ đã có việc `resolve` cho cùng giao dịch (Lô 3 N1) | Không `MultipleObjectsReturned`, không nhân đôi audit |
| P-9 | Đăng nhập tài khoản `cskh` giả trên ERP staging: ma trận quyền Lô 6 và màn lô EXPIRED `has_stock=1` (L5-1) | Chỉ thấy đúng phạm vi. Danh sách lô gọi đúng `?status=EXPIRED&has_stock=1` |
| P-10 | Duy kiểm bucket GCS ảnh (DS-1) | Không cho `list` công khai |
Tuỳ chọn: chạy lại CMS-04-AC4 (409 `STALE_VERSION` giữ bản tạm) trên staging, vì A5 chỉ dựa vào test cũ.

Việc Duy trên staging (không phải QA): `backfill_credit_notes` dry-run trước (nên chờ Lô4-L2), rồi mới quyết định `--apply`. Đặt `AI_PRODUCTION_READY=1` và `AI_WRITE_LEVELS_ALLOWED=B` theo `doc/ops/moi-truong.md`.


### Bổ sung sau review P8 Lô 8 (30/09) — đưa vào P10
| Mã | Mức | Mô tả | File |
|---|---|---|---|
| I8-1 | Medium | `auto_confirm` tìm mã đơn theo mẫu `SO-\d{6}` nhưng mã thật là `SO260930-XXXXXX` → nhánh đọc mã đơn trong nội dung CK không bao giờ khớp, luôn chuyển Chủ; test dùng mã giả có gạch nên không bắt được | `backend/apps/sales/payments/auto_confirm.py:~98` |
| I8-2 | Medium (tiềm ẩn, cùng loại M1/B1) | `PurchaseInvoiceAdmin` hiện `amount` (giá mua) không ẩn theo `view_costprice`; lộ nếu bật `is_staff` cho Quản lý | `backend/apps/purchasing/admin.py` |
| L8-Q4 | Medium–High (tiền, chờ PO) | Shop tra đơn: đơn đã huỷ/đã hoàn vẫn hiện "Chưa thanh toán" + nút **"Thanh toán lại"** + chữ thô `CANCELLED` → khách có thể trả tiền cho đơn đã huỷ. Có từ trước P8 | `frontend/app/shop/orders/OrderLookup.tsx` (+ BE checkout có chặn đơn CANCELLED không — cần kiểm) |
| L8-Q5 | Low | Hàng chờ CSKH hiện `1.000 kg` cho 1 kg (đọc kiểu VN là một nghìn kg) | BE serializer CSKH (định dạng kg) |
