# AI của tôi: nhân viên số, lệnh tự sinh từ API, hướng dẫn theo chứng từ — User stories
> PO · 2026-09-28 · Nguồn: `01-analysis.md` (ĐÃ DUYỆT 28/09), `02b-tech-design.md` (ĐÃ DUYỆT 28/09),
> `01c-phap-ly.md`, `research/01-mcp-per-function.md` (đã bị điều chỉnh M1-sửa thay thế) · Trạng thái:
> **ĐÃ DUYỆT (Duy 28/09 — chốt scope qua câu hỏi)**.

## Chốt scope của Duy (28/09) áp vào file này

| Chốt | Hệ quả trong story |
|---|---|
| Mọi mặc định 🟡 (01-analysis §15 Q-M1…Q-M20, 02b §15 Q-T1…Q-T7) lấy theo đề xuất | Con số trong AC dùng đúng mặc định: nháp C sống 15 phút, hoàn tác 10 phút, vùng đỏ trì hoãn 30 phút, trần `nhap_lo` 200 kg / 30.000.000đ, hạn mức 20 lần/ngày (vùng đỏ 10), việc chuyển quá 2 giờ đẩy lên Chủ, chờ 3 giây mới duyệt được. |
| T1: L-1 (chốt lô), L-3 (Nhật ký lộ giá vốn), L-5 (không throttle), L-6 (tra đơn dò được) **tách sang hồ sơ `2026-09-28-sua-loi-bao-mat`, làm trước** | Không story nào ở đây sửa 4 lỗi này. Ghi phụ thuộc: DW-05 (bước chốt lô) và DW-25 cần L-1 xong. L-2 (huỷ lô quá hạn) thành DW-06, L-4 (dòng AI trên dòng thời gian) nằm trong DW-03. |
| T2: lệnh **đọc** của feature chưa khai gì chạy ngay mức A, kết quả có lọc; lệnh **ghi** mặc định C | DW-07-AC2, DW-10. |
| Vai trò tự tạo **không** làm đợt này | Test phân quyền theo 4 Group `chu`, `quan_ly`, `nv_kho`, `nv_giao` và Group `cskh` (từ hồ sơ CSKH). Không hard-code tên Group trong lớp AI (DW-12-AC10). |
| Thứ tự: P2 = Lô 1 (H0) · P3 = Lô 0 spike → Lô 2–4 · P7 (cuối) = Lô 5–6, **chỉ staging** tới khi xong S-L1…S-L4 | Bảng thứ tự cuối file. Mọi AC mức B/A đều có ca "production → bị chặn" (BR-AI-27). |
| CMS cũng tự thành lệnh AI | Không có story riêng. Hồ sơ `2026-09-28-cms-viet-bai` chỉ cần qua test kỷ luật tự đăng ký của DW-08 (API ghi CMS tự vào trần C). |

## Mục tiêu & thước đo

**Vì sao làm.** (1) Nhân viên nào mở một chứng từ cũng thấy **việc tiếp theo, ai làm, còn thiếu gì, vì
sao**, và **những gì đã xảy ra**, để làm đúng quy trình mà không phải học thuộc P-01…P-10. (2) **Mọi
feature có API tự thành lệnh AI gọi được**, không ai sửa danh sách lệnh viết tay, và chỉ bị giới hạn bởi
phân quyền, "AI của tôi" và sàn cứng. (3) Mỗi người **tự giao cho AI của mình** các lệnh trong quyền, ở
mức mình chọn, và chịu trách nhiệm cho cấu hình đó.

| Thước đo | Kiểm bằng |
|---|---|
| Khối Tiếp theo · Đã làm hiện trên 4 loại chứng từ (đơn, phiếu hoàn, giao dịch lệch, lô) và chạy đủ khi AI tắt | DW-03…DW-05 (AC "AI tắt") |
| Khối Tiếp theo **không bao giờ hứa** bước mà service từ chối: 0 ca `allowed=true` mà gọi thao tác nhận 400 trên bộ fixture | DW-03-AC2, DW-05-AC2 |
| Thêm một ViewSet mới không khai gì → tự có trong chỉ mục, mặc định an toàn, **0 dòng sửa ở lớp AI** | DW-07-AC2 |
| 0 khoá giá vốn trong kết quả lệnh AI với `quan_ly`/`nv_kho`/`nv_giao`; 0 chuỗi PII khách trong kết quả, `AiAction`, AuditLog, log với **mọi** Group | DW-07-AC5/6, DW-10-AC2/3 |
| Không prompt nào vượt 80% `n_ctx`; tối đa 5 tên lệnh và 1 schema (n_ctx 2048) vào prompt | DW-09-AC2 |
| Mọi việc AI làm truy được: chủ AI, phiên bản cấu hình, mức | DW-11-AC1, DW-19-AC1 |
| Production: 0 lệnh ghi chạy mức A/B khi S-L1…S-L4 chưa xong | DW-19-AC2, DW-24-AC3 |

## Phạm vi

**Trong:** ERP console (`erp-console/`) và backend Django. Lô 0 spike · Lô 1 hướng dẫn tất định ·
Lô 2 tự đăng ký lệnh + chọn lệnh 2 bước · Lô 3 mức C + AI của tôi + tắt khẩn · Lô 4 nhập lô · Lô 5 mức
B + hoàn tác + trì hoãn ghi + trần + báo cáo ngày + chuyển việc · Lô 6 vùng đỏ.

**Ngoài:** 4 lỗi bảo mật L-1/L-3/L-5/L-6 (hồ sơ `sua-loi-bao-mat`); vai trò tự định nghĩa (hồ sơ
`vai-tro-tu-dinh-nghia`); luồng CSKH (hồ sơ `cskh-xac-nhan-in-tem`); MCP server và agent ngoài ERP; AI
chuyển tiền, gọi API ngân hàng, đọc sao kê (H15); AI tạo đơn/hoá đơn (H7); AI nhắn khách hay gửi ra kênh
ngoài (H14); AI chạy nền khi chủ AI không đăng nhập (Q-M4); Shop.

## Definition of Done (chung, không lặp trong từng story)

1. `cd backend && .venv/bin/python manage.py test` xanh; `makemigrations --check --dry-run` sạch; migration
   đi kèm mọi đổi model (lý do ở 02b §7).
2. `cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build` sạch.
3. QA report APPROVED, mỗi AC có ít nhất 1 test tự động, truy vết theo mã `DW-xx-ACy`.
4. **Ma trận Group 02b §11.3** xanh cho mọi lô có BE (token từng Group `chu`, `quan_ly`, `nv_kho`, `nv_giao`;
   thêm `cskh` khi Group đó đã có).
5. Không rò giá vốn (bất biến 1), không rò PII (bất biến 9): test/doc/mock chỉ dùng dữ liệu giả; log chỉ
   mã lệnh, mã chứng từ, id user.
6. AI tắt (`AI_ENABLED=false`) → mọi màn nghiệp vụ chạy như cũ (BR-AI-10); First Load JS của route không
   AI không tăng quá 1 KB so với trước lô (BR-AI-17).
7. Rule mới ghi vào hồ sơ này; không sửa `decisions.md` (việc của Duy).
8. Lô QA APPROVED → commit + `git push origin main` (quy ước 25/09).

## Ký hiệu

- **Contract**: bảng endpoint và JSON mẫu ở 02b §6 là contract chính thức; story chỉ ghi mục tham chiếu và
  phần **mới/khác** 02b. FE mock theo đúng contract (`NEXT_PUBLIC_USE_MOCK=1`); đổi tên field phải báo PO.
- **"Không thấy lệnh"** = lệnh không có trong `GET /api/ai/commands/index/` và `GET /api/ai/commands/<id>/`
  trả 404 `COMMAND_UNKNOWN` (cùng thân với lệnh không tồn tại).
- **PII giả chuẩn** dùng trong test: tên "Khach Thu Nghiem", SĐT "0900000123", địa chỉ "1 Duong Gia, Q.Test".
- Mã rule: BR-AI-01…34 (hồ sơ AI Native + 01-analysis §10 hồ sơ này), H1–H16 (sàn cứng 01-analysis §6),
  S-L1…S-L4 (sàn triển khai). Rule mới đề xuất ở file này: **BR-MH-07** (DW-18).

---

# LÔ 0 — Spike (chạy trước Lô 2; không đổi hành vi production)

## DW-01 — Spike BE: sinh schema từ serializer + gọi lại view trong tiến trình · Must · BE
**Là** Tech Lead (thay Duy), **tôi muốn** đo trên code thật việc sinh schema lệnh và gọi lại view bằng token
người dùng, **để** chắc hướng "lệnh tự sinh từ API" chạy được trước khi code Lô 2.

Bối cảnh: 02b §13 S-4, S-5. Kết quả ghi `research/02-spike-be.md`. Code spike không merge vào luồng chạy
production (chỉ script/test).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-01-AC1 | Toàn bộ route dưới `/api/` hiện có | chạy `serializer_to_schema` trên mọi view | báo cáo có: tổng số lệnh sau lọc §3, số `form_only`, danh sách kiểu field chưa hỗ trợ, phân bố `schema_tokens_est`; **100% lệnh đọc có schema** | BR-AI-01 |
| DW-01-AC2 | Bộ test phân quyền `inventory/batches/tests/test_api.py` và test API đơn hàng | chạy lại qua `dispatch.py` thay cho `APIClient` | 100% ca cho cùng mã HTTP, cùng JSON, cùng số dòng AuditLog | BR-AI-04, H1, H16 |
| DW-01-AC3 (giá vốn) | Token `nv_kho` | gọi danh sách lô qua dispatch | JSON không có `purchase_rate`, `landed_unit_cost`, giống hệt `APIClient` | bất biến 1, H3 |
| DW-01-AC4 (quyền) | User bị vô hiệu (ca BR-PQ-19 hiện có) | gọi qua dispatch | bị chặn cùng mã như gọi HTTP | BR-PQ-19 |
| DW-01-AC5 (lỗi) | Một tiêu chí không đạt (vd schema `nhap_lo` ước lượng > 450 token) | kết thúc spike | báo cáo ghi rõ con số và đề xuất; Tech Lead cập nhật 02b **trước** khi mở Lô 2 | — |
| DW-01-AC6 (PII) | — | đọc báo cáo và fixture spike | chỉ dữ liệu giả; không tên/SĐT/địa chỉ thật | bất biến 9 |

## DW-02 — Spike FE: Gemma 3n chọn lệnh, tìm từ khoá, ngân sách token · Must · FE
**Là** Tech Lead, **tôi muốn** đo độ đúng chọn lệnh, recall tìm từ khoá và độ ổn định bộ nhớ trên máy tham
chiếu, **để** chốt số ứng viên, `margin` và bảng ngân sách 02b §5.3 bằng số thật.

Bối cảnh: 02b §13 S-1, S-2, S-3. Máy Android/Windows ≥ 8 GB (Q4 27/09). Dùng lại bộ 50 câu giả của S17.
Chỉ mục lấy từ kết quả DW-01. Kết quả ghi `research/03-spike-fe.md`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-02-AC1 | 50 câu giả, N = 3 và 5 ứng viên, n_ctx 2048/4096, E2B/E4B | chạy lượt A (chọn lệnh) | ghi tỉ lệ chọn đúng; **đạt khi ≥ 90% ở N ≤ 5**; ghi độ trễ token đầu và RAM đỉnh | BR-AI-16 |
| DW-02-AC2 | Cùng bộ câu, 1 schema (`nhap_lo`, `inventory.batch.list`) | chạy lượt B (điền args) | ≥ 90% args qua serializer của view | BR-AI-01 |
| DW-02-AC3 | Chỉ mục thật ~110–150 lệnh, BM25 bỏ dấu | tìm 50 câu | **recall@5 ≥ 95%**; chốt `margin` top-1/top-2 để bỏ lượt A | — |
| DW-02-AC4 (không crash) | 200 lượt liên tiếp ở 2048 và 4096 | đo bằng tokenizer Gemma thật | 0 crash tab; không prompt nào > 80% n_ctx; bảng §5.3 cập nhật bằng số đo | BR-AI-13 |
| DW-02-AC5 (lỗi) | recall@5 < 95% hoặc chọn đúng < 90% | kết thúc spike | thử thêm `keywords` rồi đo lại; vẫn không đạt thì báo Duy kèm đề xuất (embedding nhỏ / đổi N), **không** mở Lô 2 FE khi chưa có quyết định | — |
| DW-02-AC6 (PII) | — | toàn bộ spike | chỉ câu và dữ liệu giả; không ghi prompt vào console hay file ngoài báo cáo | bất biến 9, BR-AI-09 |

Phụ thuộc: runtime wllama của **S08** (hồ sơ 27/09, đang dở). Spike dùng harness tối thiểu nếu S08 chưa xong.

---

# LÔ 1 — H0: Hướng dẫn tất định "Tiếp theo · Đã làm" (không phụ thuộc AI)

Contract: 02b §6.7 (`GET /api/guidance/<loại>/<id>/`). Endpoint **không** nằm dưới `/api/ai/`, không bao
giờ trả 410.

## DW-03 — Khối "Tiếp theo · Đã làm" trên màn Đơn hàng (dựng khung chung) · Must · BE+FE
**Là** Quản lý (và mọi nhân viên xem được đơn), **tôi muốn** mở một đơn là thấy việc tiếp theo hợp lệ, ai
làm, hạn khi nào, vì sao, cùng dòng thời gian của đơn và các chứng từ đi kèm, **để** xử lý đúng quy trình
mà không phải hỏi Lộc.

Bối cảnh: UC-DW-07; 01-analysis §4.7.1–4.7.3; BR-AI-28…33; Q-M16 (gộp chứng từ liên quan), Q-M17. Story
này dựng khung `apps/common/guidance/` (bảng câu "vì sao" `reasons.py`, khung dòng thời gian, index AuditLog
`(model_name, object_id, created_at)`) và sửa L-4.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-03-AC1 | Đơn BOOKED tạo lúc 10:12, `SALES_ORDER_TTL_MINUTES=30`, Quản lý đăng nhập | mở chi tiết đơn | `next_steps` có bước `actor=system` "Hệ thống sẽ tự huỷ" `deadline=10:42`; bước "Xác nhận thanh toán tay" `allowed=false`, `who=["Chủ"]`, `why.br="BR-TT-07"` | BR-AI-28, BR-AI-29, BR-TT-07 |
| DW-03-AC2 | Bộ fixture đơn ở mọi trạng thái × 4 Group | so `available_actions` của API đơn trước và sau đổi | `available_actions` = đúng danh sách `key` có `allowed=true` trong `next_steps`, và bằng kết quả cũ; với mỗi bước `allowed=true`, gọi thao tác thật **không** trả 400 | BR-AI-28, BR-AI-29 |
| DW-03-AC3 | Đơn PAID có phiếu giao và phiếu hoàn | mở chi tiết | `timeline` gộp dòng của đơn, hoá đơn, phiếu giao, phiếu hoàn theo thứ tự thời gian, mỗi dòng có `doc`; `related` liệt kê mã các chứng từ đó | BR-AI-30, Q-M16 |
| DW-03-AC4 (dòng AI, L-4) | AuditLog có dòng `actor_kind=ai`, `ai_actor`=Chủ | mở dòng thời gian | dòng hiện "AI của <tên hiển thị>" kèm mức, **không** hiện "Hệ thống"; field `config_version` chỉ có khi người xem có `ai.manage_ai_policy` (trước Lô 3: không có với ai) | BR-AI-08, BR-AI-30 |
| DW-03-AC5 (PII) | Đơn fixture có PII giả chuẩn và nội dung chuyển khoản | gọi guidance bằng token **Chủ** | response không chứa tên, SĐT, địa chỉ, nội dung CK; dòng thời gian không có `changes` thô | bất biến 9, BR-AI-30 |
| DW-03-AC6 (giá vốn) | Người xem thiếu `view_costprice` | gọi guidance đơn có hoá đơn | không khoá `unit_cost`, `landed_unit_cost`, `profit`, `margin`, `cogs` ở bất kỳ tầng nào | bất biến 1, BR-AI-29 |
| DW-03-AC7 (quyền) | User không xem được đơn này ở API chi tiết đơn (thiếu `view_salesorder` hoặc ngoài scope T3) | gọi guidance | nhận cùng mã lỗi như API chi tiết đơn (403 hoặc 404), không lộ bước hay dòng nào; NV kho/NV giao **không** được mở `/api/audit-logs/` nhờ tính năng này | BR-PQ-12, Q-M17 |
| DW-03-AC8 (lỗi) | Đơn tự huỷ giữa lúc xem và lúc bấm "Xác nhận thanh toán" | Chủ bấm | service trả `BusinessError` kèm mã BR; FE hiện thông điệp và tải lại khối (1 lần gọi guidance) | BR-TT-05 |
| DW-03-AC9 (AI tắt) | `AI_ENABLED=false` | mở chi tiết đơn | endpoint trả 200 đủ `next_steps`, `timeline`, `warnings`; field `ai` của mọi bước = `null`; FE hiện đủ hai khối | BR-AI-10 |
| DW-03-AC10 (vì sao) | — | quét `reasons.py` | mọi `why.br` dùng trong `next_steps`/`missing` có đúng 1 câu soạn sẵn; không câu nào chứa số tiền | BR-AI-32 |
| DW-03-AC11 (FE) | Guidance lỗi mạng hoặc 500 | mở chi tiết đơn | phần còn lại của màn đơn vẫn hiện; khối hiện trạng thái lỗi có nút thử lại; có trạng thái tải và rỗng | BR-AI-10 |

## DW-04 — "Tiếp theo · Đã làm" trên Phiếu hoàn và Giao dịch lệch · Must · BE+FE
**Là** Quản lý, **tôi muốn** thấy trên phiếu hoàn và giao dịch lệch việc còn phải làm, ai làm và hạn,
**để** không để khách chờ quá hạn hoàn 30 ngày và biết khi nào phải nhờ Chủ.

Bối cảnh: 01-analysis §4.7.1 (dòng Refund, PaymentTransaction), §4.7.5 cảnh báo; BR-HT-03/07, BR-TT-04/05/09/10/15.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-04-AC1 | Phiếu hoàn PENDING, Quản lý xem | gọi `GET /api/guidance/refund/<id>/` | bước "Xác nhận đã hoàn" `allowed=false`, `who=["Chủ"]`, `missing` có "cần mã giao dịch chuyển khoản" (BR-HT-03) | BR-HT-03, BR-HT-07 |
| DW-04-AC2 | Phiếu hoàn PENDING tạo cách đây 25 ngày (ngưỡng cảnh báo cấu hình, mặc định 25) | xem | `warnings` có cảnh báo "phiếu hoàn gần hạn 30 ngày"; phiếu 10 ngày thì không có | BR-AI-33 |
| DW-04-AC3 | Fixture phiếu hoàn và giao dịch lệch mọi trạng thái | so `available_actions` cũ và mới | bằng nhau; mỗi bước `allowed=true` chạy thật không 400 | BR-AI-28/29 |
| DW-04-AC4 (PII) | Giao dịch lệch có `raw_payload`, nội dung CK, tên người chuyển giả | gọi guidance bằng token **Chủ** | response không chứa các chuỗi đó | bất biến 9, H2 |
| DW-04-AC5 (quyền) | `nv_kho`, `nv_giao` | gọi guidance phiếu hoàn / giao dịch lệch | cùng mã lỗi với API chi tiết tương ứng (403), không lộ bước | BR-PQ-12 |
| DW-04-AC6 (lỗi) | Phiếu hoàn vừa được Chủ xác nhận ở tab khác | Quản lý bấm bước cũ | 400 kèm mã BR; khối tải lại | BR-HT-08 |
| DW-04-AC7 (AI tắt) | `AI_ENABLED=false` | mở hai màn | hai khối đủ, `ai=null` | BR-AI-10 |

## DW-05 — "Tiếp theo · Đã làm" trên Lô (lọc giá vốn trong dòng thời gian) · Must · BE+FE
**Là** NV kho, **tôi muốn** mở một lô là thấy lô đang ở đâu trong vòng đời, bước tiếp theo và lịch sử nhập,
xuất, **để** biết khi nào báo Chủ chốt lô hay huỷ lô mà không cần thấy giá vốn.

Bối cảnh: 01-analysis §4.7.1 (dòng Batch), §4.7.3 (AuditLog `close_batch` có `landed_unit_cost`), Q-M15.
Dòng thời gian lô = AuditLog + `StockLedgerEntry` + mốc trạng thái.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-05-AC1 | Lô SELLING, hạn dùng còn 10 ngày, `NEAR_EXPIRY_DAYS=14` | NV kho xem | bước `actor=system` "Hệ thống sẽ chuyển Cận hạn" có `deadline`; bước "Mở bán"/"Chốt lô" không hiện `allowed=true` cho NV kho | BR-LO-06, BR-AI-28 |
| DW-05-AC2 | Lô SOLD_OUT còn một đơn BOOKED tham chiếu lô | Chủ xem, rồi gọi thẳng thao tác chốt | bước "Chốt lô" `allowed=false`, `missing` có BR-LO-04 "còn đơn đang mở"; gọi thẳng nhận 400 BR-LO-04 (cùng hàm `check_close_batch`) | BR-LO-04, BR-AI-29 |
| DW-05-AC3 (giá vốn) | Lô đã chốt (AuditLog `close_batch` có `landed_unit_cost`) và có `record_purchase_cost` | `quan_ly` và `nv_kho` xem dòng thời gian | thấy "Chủ đã chốt lô", "Chủ ghi nhận chi phí mua", **không** có con số; `chu` thấy số | bất biến 1, BR-AI-30 |
| DW-05-AC4 (giá vốn, bước) | Lô chưa có chi phí mua, `nv_kho` xem | gọi guidance | chỉ có một dòng "Chủ xử lý: chi phí mua", không số; cảnh báo "lô chưa có chi phí mua" không kèm số; `chu` thấy cảnh báo cùng câu | Q-M15, BR-AI-33 |
| DW-05-AC5 (quyền) | `nv_giao` (không `view_batch`) | gọi guidance lô | 403, không lộ bước | BR-PQ-12 |
| DW-05-AC6 (PII) | Lô có đơn xuất kho fixture PII giả | gọi guidance | không tên/SĐT/địa chỉ khách trong dòng sổ kho | bất biến 9 |
| DW-05-AC7 (AI tắt) | `AI_ENABLED=false` | mở màn tồn kho/lô | hai khối đủ | BR-AI-10 |

Phụ thuộc cứng: **L-1** của hồ sơ `sua-loi-bao-mat` (`close_batch` kiểm "không còn đơn mở", BR-KK-05, khoá
dòng) phải xong trước khi bước "Chốt lô" được hiện `allowed=true`. Trước đó bước chốt lô luôn `allowed=false`
với `missing` "Chủ chốt lô trên màn lô cũ" — không hứa bước service chưa kiểm (BR-AI-29).

## DW-06 — Chủ huỷ lô quá hạn (EXPIRED → CANCELLED, hạch toán lỗ) · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** huỷ lô đã quá hạn ngay trên ERP, **để** ghi nhận lỗ hàng hết hạn vào đúng lô
và chốt được lô đó.

Bối cảnh: L-2 / Q-L6; BR-LO-03; sơ đồ P-04 (Quá hạn → Huỷ → Đã chốt). Không migration model (trạng thái
đã có); thêm quyền Tầng 2 mới `inventory.cancel_expired_batch` gán `chu` (data migration theo mẫu
`accounts/0007`). Quyền Tầng 2 mới chưa có trong bảng luật §3 → lệnh AI tự sinh **trần C ép**.

Contract (mới):
```
POST /api/inventory/batches/<pk>/cancel-expired/   {}
→ 200 {"id": 123, "batch_id": "CA01-…", "status": "CANCELLED"}
→ 400 {"detail": "Chỉ huỷ được lô Quá hạn.", "code": "BR-LO-03"}
→ 403 (thiếu quyền) · 404 (không tồn tại)
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-06-AC1 | Lô EXPIRED còn 5 kg | Chủ bấm "Huỷ lô", xác nhận | lô CANCELLED; `StockLedgerEntry` ghi xuất huỷ 5 kg; lãi lỗ lô có dòng lỗ hết hạn = 5 × `landed_unit_cost`; AuditLog 1 dòng | BR-LO-03, BR-PQ-05 |
| DW-06-AC2 (lỗi) | Lô SELLING hoặc NEAR_EXPIRY | gọi API | 400 BR-LO-03, không đổi dữ liệu | BR-LO-03 |
| DW-06-AC3 (song song) | Hai request huỷ cùng lô cùng lúc | gọi | đúng 1 request thành công, sổ kho có đúng 1 dòng huỷ (`atomic` + `select_for_update`) | bất biến 4 |
| DW-06-AC4 (quyền) | `quan_ly`, `nv_kho`, `nv_giao` | gọi API | 403, không đổi dữ liệu; nút không hiện | BR-PQ-12 |
| DW-06-AC5 (giá vốn) | Sau khi huỷ, `quan_ly` xem dòng thời gian lô | — | thấy "Chủ đã huỷ lô", không có số lỗ | bất biến 1 |
| DW-06-AC6 (guidance) | Lô EXPIRED | Chủ xem khối Tiếp theo | có bước "Huỷ lô" `allowed=true`; sau khi huỷ, bước kế là "Chốt lô" | BR-AI-28 |
| DW-06-AC7 (AI tắt) | `AI_ENABLED=false` | huỷ lô | chạy bình thường | BR-AI-10 |

---

# LÔ 2 — Tự đăng ký lệnh + chỉ mục + chọn lệnh 2 bước

## DW-07 — Lệnh AI tự sinh từ API, chỉ mục theo quyền, mặc định an toàn · Must · BE
**Là** Chủ vựa, **tôi muốn** mọi feature có API tự thành lệnh AI, chỉ hiện với người có quyền và an toàn
khi feature không khai gì, **để** thêm feature mới không phải sửa danh sách lệnh và không mở lỗ rò.

Bối cảnh: Duy M1-sửa; 02b §2, §3, §5.5, §6.2; T2. Registry cũ S01 và `GET /api/commands/catalog/` **giữ
nguyên** tới DW-15. Gồm `list_query_serializer` cho lô (lọc `item_code`, `status` dùng chung với màn lô).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-07-AC1 | Khởi động app | `chu` gọi `GET /api/ai/commands/index/` | mỗi lệnh có `id`, `title`, `group` (thu_mua/ban_hang/cskh), `kind`, `level`, `screens`, `keywords`, `index_version`; id đúng quy tắc 02b §2.3; snapshot id lệnh khớp file snapshot | BR-AI-01 |
| DW-07-AC2 (feature mới không khai gì) | Gắn ViewSet thử không khai gì (02b §11.2) trỏ `Batch` và `SalesOrder`, có `@action` POST đọc `request.data` tay và field `note` | gọi index/descriptor | lệnh chỉ hiện với Group có `view_*` tương ứng; `sensitivity=cao`, `channel=local`; lệnh đọc `level=A`; lệnh ghi `level=C`, `max_level=C`; action đọc tay `form_only=true`; thêm `required_perms=("sales.confirm_refund",)` → `red_zone=true`; quyền Tầng 2 lạ → `max_level=C` | T2, BR-AI-18, BR-AI-19 |
| DW-07-AC3 (danh sách chặn) | Registry thật | quét chỉ mục của `chu` | không lệnh nào: tiền tố `/api/shop/`, `/api/internal/`, `/api/auth/`, `/api/ai/`, `/api/staff/`, `/api/audit-logs/`, `/api/commands/`; method DELETE/PUT; upload; quyền `auth.*`/`manage_staff`/`view_auditlog`/`manage_ai_policy`; ghi lên `SalesOrder`/`SalesInvoice`; resource `customer`. Tập `red_zone=true` **đúng bằng** các action có `close_batch`/`confirm_refund`/`confirm_payment_manual` | H4, H7, H11, H14, BR-PQ-11 |
| DW-07-AC4 (quyền theo Group) | Token 4 Group | gọi index | `nv_giao` không có lệnh `purchasing.*`, `inventory.batch.close`, `reports.*`; `quan_ly`/`nv_kho`/`nv_giao` không có `reports.batch_pnl`, `reports.period_pnl`; lệnh không thấy → descriptor 404 `COMMAND_UNKNOWN`, thân giống hệt lệnh không tồn tại | BR-AI-04, H1 |
| DW-07-AC5 (giá vốn) | `quan_ly`, `nv_kho` | `GET /api/ai/commands/inventory.batch.list/` | `output_fields` không có `purchase_rate`, `landed_unit_cost`; `chu` có | bất biến 1, H3 |
| DW-07-AC6 (PII) | Mọi Group | quét descriptor mọi lệnh | không `output_fields` nào chứa khoá PII của 02b §3; không lệnh nào trên resource `customer` | bất biến 9, H2 |
| DW-07-AC7 (ngân sách) | Lệnh có enum > 20 giá trị hoặc mô tả dài | gọi descriptor | mô tả ≤ 80 ký tự; enum > 20 đổi thành `string`; `schema_tokens_est > AI_SCHEMA_MAX_TOKENS (450)` → `form_only=true` | BR-AI-13 |
| DW-07-AC8 (hiệu năng) | — | gọi index | chỉ query bảng `auth_*`/`ai_*` (assertNumQueries/bắt SQL), không bảng nghiệp vụ; registry build 1 lần mỗi tiến trình | BR-AI-17 |
| DW-07-AC9 (AI tắt) | `AI_ENABLED=false` | gọi index, descriptor | 410 `AI_DISABLED`; `/api/commands/catalog/` cũ vẫn trả y JSON cũ (7 test `test_catalog.py` xanh) | BR-AI-10 |
| DW-07-AC10 (lọc lô) | Màn lô và lệnh `inventory.batch.list` | lọc `item_code=CA-001` | cả màn và lệnh chỉ trả lô của mặt hàng đó, thứ tự FEFO | bất biến 6 |

## DW-08 — Khai quyền Tầng 2 trên mọi action + test kỷ luật tự đăng ký · Must · BE
**Là** Tech Lead, **tôi muốn** mọi `@action` khai `required_perms` và được cưỡng chế trước thân action, cùng
test CI bắt feature mới quên khai, **để** chỉ mục lệnh không bao giờ rộng hơn quyền thật và feature sau (CMS,
CSKH…) tự đúng luật.

Bối cảnh: 02b §2.5, §2.7; Q-T7 (refactor 18 action, hành vi không đổi).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-08-AC1 | 18 `@action` hiện có | chạy `test_moi_custom_action_co_required_perms` | xanh; bỏ khai ở một action thử → fail và in tên action | BR-PQ-12 |
| DW-08-AC2 | User thiếu từng quyền | chạy `test_required_perms_khop_require_perm` | quyền mà `require_perm` trong thân kiểm ⊆ `required_perms` cho mọi action | H1 |
| DW-08-AC3 (quyền, không đổi hành vi) | Toàn bộ test hiện có | chạy test backend | xanh, số test ≥ baseline trước lô; user thiếu quyền gọi action qua UI nhận 403 **cùng thân** như trước | BR-PQ-12 |
| DW-08-AC4 | Action ghi thiếu docstring tiếng Việt | chạy test | fail, in tên | BR-AI-01 |
| DW-08-AC5 (lỗi) | Action mới đọc `request.data` tay | chạy `test_form_only_bao_cao` | action **mới** → fail; 15 chỗ nợ hiện có → chỉ in báo cáo | — |
| DW-08-AC6 | Đổi basename/URL một ViewSet | chạy `test_id_lenh_on_dinh` | fail cho tới khi snapshot được cập nhật có chủ ý | Q-T3 |
| DW-08-AC7 (AI tắt) | `AI_ENABLED=false` | gọi mọi action từ UI | hành vi như AI bật (cưỡng chế quyền không phụ thuộc AI) | BR-AI-10 |

## DW-09 — FE chọn lệnh 2 bước + ngân sách token (chạy với LLMock) · Must · FE
**Là** NV kho, **tôi muốn** hỏi AI bằng câu thường mà tab không treo, **để** dùng được trên máy 8 GB tại cảng.

Bối cảnh: 02b §5; Duy 28/09 "không để context lớn và crash". Module `erp-console/features/ai/commands/`
(`index.ts`, `search.ts`, `budget.ts`, `planner.ts`). Mock chỉ mục ~20 lệnh giả đủ 3 nhóm, 4 Group
(02b §6.8). Tham số `margin`, K lấy từ kết quả DW-02.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-09-AC1 | Đang ở màn tồn kho, hỏi "còn bao nhiêu cá thu" | chạy tìm kiếm | ≤ 3 ứng viên (trần cứng 5), top-1 `inventory.batch.list`; top-1 vượt top-2 quá `margin` → bỏ lượt A | — |
| DW-09-AC2 (ngân sách) | Chỉ mục giả 150 lệnh, bảng tham số n_ctx 2048/4096 | chạy planner cho 50 câu mẫu | mọi prompt ≤ 80% n_ctx (đo bằng tokenizer, mock trong unit test); lượt A ≤ 5 tên; lượt B ≤ 1 schema (2048) / ≤ 2 (4096); prompt **không** chứa id lệnh ngoài top-K | BR-AI-13 |
| DW-09-AC3 | Lệnh có `form_only=true` hoặc schema > 450 token | được chọn | không chạy lượt B; mở form của lệnh, điền sẵn trường suy được tất định (số kg, mã hàng) | BR-AI-13 |
| DW-09-AC4 (lỗi) | Không ứng viên nào đạt điểm tối thiểu | hỏi | hỏi lại tối đa 3 lần rồi gợi ý câu mẫu; không gọi model | UC-AI-02 |
| DW-09-AC5 (không crash) | Kết quả mock 500 dòng | lượt C | chỉ đưa ≤ 20 dòng vào prompt, hiện "còn 480 dòng — xem màn danh sách"; tab không crash | BR-AI-13 |
| DW-09-AC6 (quyền) | Chỉ mục từ server đã lọc theo user | đổi `index_version` | FE tải lại chỉ mục; FE không tự thêm lệnh nào ngoài chỉ mục | BR-AI-04 |
| DW-09-AC7 (PII) | — | chạy luồng | không ghi câu hỏi, prompt, kết quả vào `console`, `localStorage` hay URL; chỉ mục giữ trong bộ nhớ JS | bất biến 9, BR-AI-09 |
| DW-09-AC8 (AI tắt) | index trả 410 | mở console | chunk AI không tải (lazy); màn nghiệp vụ không đổi | BR-AI-10, BR-AI-17 |

---

# LÔ 3 — Mức C + AI của tôi + tắt khẩn (hạ tầng xong, chưa ai tự ghi)

Env mặc định mọi môi trường ở lô này: `AI_WRITE_LEVELS_ALLOWED=C`.

## DW-10 — AI gọi lệnh đọc (mức A) với kết quả đã lọc · Must · BE
**Là** Quản lý, **tôi muốn** AI tra cứu thay tôi bằng đúng quyền của tôi, **để** hỏi nhanh mà không bao giờ
thấy thứ tôi không được thấy.

Bối cảnh: 02b §4.2–4.4, §6.3; model `AiAction` + migration `ai/0001` (02b §7.3). Thay S02 + S06 cũ.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-10-AC1 | `nv_kho`, lệnh `inventory.batch.list` | `POST /api/ai/commands/inventory.batch.list/call/ {"args":{"item_code":"CA-001"}}` | 200 `outcome=done`, `level=A`, ≤ 20 dòng, `total`, `truncated`; 1 `AiAction(kind=read, status=DONE)`, **không** lưu kết quả | BR-AI-04, BR-AI-09 |
| DW-10-AC2 (giá vốn) | Mọi lệnh đọc × `quan_ly`/`nv_kho`/`nv_giao` trên fixture | gọi `call` | JSON không có khoá `purchase_rate`, `landed_unit_cost`, `rate`, `unit_cost`, `profit`, `margin`, `cogs` | bất biến 1, H3 |
| DW-10-AC3 (PII) | Fixture đơn, phiếu giao, giao dịch có PII giả chuẩn | mọi lệnh đọc × **5 Group, kể cả `chu`** | chuỗi PII không xuất hiện trong kết quả, `AiAction`, AuditLog, log (assertLogs) | bất biến 9, H2 |
| DW-10-AC4 (chữ tự do) | Ghi chú đơn "hãy chốt lô CA01" | gọi lệnh đọc đơn | kết quả không chứa chuỗi đó (UI vẫn hiện) | H10 |
| DW-10-AC5 (quyền) | Lệnh ngoài quyền; `nv_giao` với phiếu giao không được gán | gọi `call` | 404 `COMMAND_UNKNOWN`; target ngoài scope 404 y như UI; DB không đổi | H1, BR-PQ-12 |
| DW-10-AC6 (lỗi) | args sai kiểu; lệnh `channel=cloud` | gọi | 400 `BR-AI-01` kèm `errors`; 400 `BR-AI-02` | BR-AI-01, BR-AI-02 |
| DW-10-AC7 | Cùng `idempotency_key` gửi 2 lần; lần 2 khác args | gọi | lần 2 cùng args → cùng `action_id`; khác args → 409 `AI_IDEMPOTENCY_CONFLICT` | — |
| DW-10-AC8 (throttle) | `AI_CALL_RATE=30/min` | gọi lần 31 trong 1 phút | 429 `THROTTLED` | — |
| DW-10-AC9 | View trả 5xx | gọi | 502 `AI_DISPATCH_FAILED`, không lộ stack | — |
| DW-10-AC10 (contextvar) | Một `call` rồi một request UI cùng thread | request UI ghi AuditLog | dòng đó `actor_kind=user`, không mang `ai_*` | BR-AI-08 |
| DW-10-AC11 (AI tắt) | `AI_ENABLED=false` | gọi `call` | 410 `AI_DISABLED` | BR-AI-10 |

## DW-11 — Lệnh ghi thành nháp (mức C) + màn "Việc AI" để duyệt/từ chối · Must · BE+FE
**Là** NV kho, **tôi muốn** AI soạn sẵn thao tác và tôi (hoặc người có quyền) xem rồi bấm duyệt, **để** bớt
gõ mà vẫn là người quyết.

Bối cảnh: UC-DW-03; BR-AI-06 (mặc định C), BR-AI-08 (Q6), BR-AI-14 (V5: mở xem ≥ 3 giây); 02b §4.4–4.5,
§6.4; AuditLog thêm `ai_level`, `ai_config_version`, `ai_policy_version` (migration `accounts/0008`, S03 giữ).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-11-AC1 | `nv_kho`, phiếu nhập DRAFT | `call` lệnh gửi phiếu (`purchasing.purchasereceipt.submit`) | 200 `outcome=proposal`, `level=C`, `expires_at`=+15 phút; phiếu **vẫn DRAFT**; AuditLog `propose_…` `actor_kind=ai`, `ai_actor`=NV kho, `ai_level=C`, `ai_config_version` | BR-AI-06, BR-AI-08 |
| DW-11-AC2 | Nháp ở AC1, người có quyền mở chi tiết ≥ 3 giây | `POST /api/ai/actions/<id>/confirm/ {confirm_nonce}` | view chạy bằng token **người duyệt**; phiếu SUBMITTED; AuditLog thực thi `actor_kind=user`, actor = người duyệt, `proposal_ref`=id; `AiAction` CONFIRMED | BR-AI-08 (Q6) |
| DW-11-AC3 (lỗi) | Chưa mở chi tiết hoặc < 3 giây; duyệt lần 2; quá 15 phút | confirm | 400 `BR-AI-14`; 409 `AI_ACTION_ALREADY_DECIDED`; 410 `AI_ACTION_EXPIRED` — phiếu không đổi | BR-AI-14 |
| DW-11-AC4 | Nháp bất kỳ | `reject` | `AiAction` REJECTED, chứng từ không đổi, AuditLog 1 dòng | BR-AI-08 |
| DW-11-AC5 (quyền) | Người duyệt thiếu quyền của lệnh | confirm | 403 `BR-AI-04`, DB không đổi; `scope=all` chỉ người có `manage_ai_policy`, người khác chỉ thấy việc của mình | H1 |
| DW-11-AC6 (kiểm kê, H6) | `AiAction` nhập số kiểm kê của AI của A (fixture service) | A duyệt | bị từ chối BR-KK-02 ở `actions/services.py` **và** service kiểm kê | BR-KK-02, H6 |
| DW-11-AC7 (giá vốn) | Nháp có `rate` trong args | người thiếu `view_costprice` (kể cả chủ nháp là NV kho) xem danh sách/chi tiết | `args_preview` không có `rate`; `chu` thấy | bất biến 1, BR-MH-06 |
| DW-11-AC8 (PII) | Nháp đụng đơn có PII giả | xem | `target` chỉ loại + mã; không tên/SĐT/địa chỉ; không `object_repr` | bất biến 9 |
| DW-11-AC9 (AI tắt) | `AI_ENABLED=false` | confirm / reject / GET | confirm 410; reject và GET vẫn chạy | BR-AI-10 |
| DW-11-AC10 (FE) | Màn "Việc AI" | mở | tab Chờ duyệt / Đã xử lý; nút "Đồng ý thực thi" bật sau đếm ngược 3 giây; nhãn "AI của <tên>"; trạng thái tải/lỗi/rỗng | BR-AI-14 |

## DW-12 — Màn "AI của tôi": tự giao lệnh, phiên bản cấu hình, tắt AI của mình · Must · BE+FE
**Là** NV kho (và mọi nhân viên), **tôi muốn** tự chọn lệnh nào trong quyền của tôi AI được dùng và ở mức
nào, **để** giao việc cho AI của mình và biết mình chịu trách nhiệm cho cấu hình đó.

Bối cảnh: UC-DW-01, UC-DW-05; BR-AI-19/20/21/22; Q-M1, Q-M14; model `AiConfigVersion` (02b §7.1); contract
02b §6.5. Lô này chỉ chọn được Tắt/C (ghi) và Tắt/A (đọc).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-12-AC1 | `nv_kho` chưa cấu hình | `GET /api/ai/my-config/` | chỉ lệnh trong quyền, chia 3 nhóm; lệnh ghi `level=C`, `choices=["OFF","C"]`; lệnh đọc `level=A`, `choices=["OFF","A"]` | BR-AI-19, Q-M1 |
| DW-12-AC2 | Tick "tôi chịu trách nhiệm" | PUT đặt `inventory.batch.list=OFF` | `version`+1, 1 dòng `AiConfigVersion` mới, bản cũ nguyên; AuditLog; `call` lệnh đó ngay sau → 404 (hiệu lực tức thì) | BR-AI-20, BR-AI-21 |
| DW-12-AC3 (lỗi) | PUT không tick; mức vượt trần; `base_version` cũ | PUT | 400 `BR-AI-14`; 400 `BR-AI-19` kèm `errors`; 409 `AI_CONFIG_CONFLICT` — không ghi | BR-AI-14, BR-AI-19 |
| DW-12-AC4 (quyền, H1) | `nv_kho` PUT lệnh `sales.refund.confirm` | PUT | 400 `BR-AI-19` "Lệnh ngoài quyền của bạn" | H1 |
| DW-12-AC5 (đổi Group) | `nv_kho` có override C cho lệnh gửi phiếu nhập; bị gỡ khỏi `nv_kho` | GET, rồi `call` | lệnh không còn trong GET; `call` → 404; override vẫn nằm trong phiên bản cũ | BR-AI-04 |
| DW-12-AC6 (tắt AI của tôi) | Người dùng bấm "Tắt AI của tôi" | `POST /api/ai/my-config/kill/ {"killed":true}` rồi `call` lệnh ghi | phiên bản mới `killed=true`; lệnh ghi chỉ ra nháp C (dù cấu hình cao hơn); bật lại được bằng `killed:false` | BR-AI-22, H12 |
| DW-12-AC7 (vùng đỏ) | `chu` | GET | `inventory.batch.close` có `choices=["OFF","C"]`, `locked_reason.code="BR-AI-18"` | BR-AI-18 |
| DW-12-AC8 (không sửa hộ) | Bất kỳ | tìm endpoint sửa cấu hình người khác | không tồn tại (PUT `/api/ai/policy/users/<id>/config/` → 405) | H11, Q-M2 |
| DW-12-AC9 (AI tắt) | `AI_ENABLED=false` | GET/PUT/kill | vẫn 200, `ai_enabled=false`; FE hiện băng "AI đang tắt" | BR-AI-10 |
| DW-12-AC10 (Group không hard-code) | Fixture Group `cskh` với quyền mẫu (xem phiếu hoàn) | GET bằng user `cskh` | chỉ lệnh qua quyền của Group đó; code lớp AI không so tên Group nào | BR-PQ, Duy 28/09 |
| DW-12-AC11 (PII) | — | `GET /api/ai/my-config/versions/` | chỉ tên hiển thị nhân viên, không dữ liệu khách | bất biến 9 |

## DW-13 — Chính sách AI của Chủ: tắt khẩn toàn cục, tắt AI của một người, xem cấu hình · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** một chỗ tắt khẩn mọi AI hoặc AI của một người và xem ai đang giao gì cho AI,
**để** dừng ngay khi có sự cố.

Bối cảnh: UC-DW-05; BR-AI-22; Q-M2, Q-M3; model `AiPolicyVersion` + quyền `ai.manage_ai_policy` gán `chu`
(02b §7.2, migration `ai/0002`); contract 02b §6.6 (phần vùng đỏ/trần làm ở DW-20, DW-24).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-13-AC1 | Chủ PUT `global_mode=c_only` (tick trách nhiệm) | người bất kỳ `call` lệnh ghi | chỉ ra nháp C; phiên bản chính sách +1, AuditLog | BR-AI-22, H12 |
| DW-13-AC2 | Chủ PUT `global_mode=off` | người bất kỳ gọi index | chỉ mục rỗng; `call` → 404 | BR-AI-22 |
| DW-13-AC3 | Chủ tắt AI của user X | `POST /api/ai/policy/users/<X>/kill/` | phiên bản cấu hình mới của X `created_by`=Chủ, `killed=true`; X thấy `killed=true` | BR-AI-22 |
| DW-13-AC4 | Chủ | `GET /api/ai/policy/users/<X>/config/` | chỉ đọc; không có đường đổi mức của X | Q-M2 |
| DW-13-AC5 (quyền) | `quan_ly`, `nv_kho`, `nv_giao`, `cskh` | GET/PUT `/api/ai/policy/*` | 403; migration gán `manage_ai_policy` chỉ cho `chu`, rollback gỡ | BR-PQ-12 |
| DW-13-AC6 (lỗi) | `base_version` lệch; không tick | PUT | 409 `AI_POLICY_CONFLICT`; 400 `BR-AI-14` | BR-AI-14 |
| DW-13-AC7 (append-only) | — | tìm đường sửa/xoá `AiPolicyVersion`, `AiConfigVersion` | không có API; Admin chỉ đọc | BR-AI-21, H5 |
| DW-13-AC8 (PII/giá vốn) | — | GET policy | `users` chỉ tên hiển thị, Group, số lệnh theo mức | bất biến 1, 9 |
| DW-13-AC9 (AI tắt) | `AI_ENABLED=false` | gọi policy | vẫn chạy | BR-AI-10 |

## DW-14 — Chat gọi lệnh qua `call` + nút "Để AI làm" trên khối Tiếp theo · Must · BE+FE
**Là** Quản lý, **tôi muốn** hỏi AI bằng tiếng Việt và bấm "Để AI làm" ngay trên bước tiếp theo của chứng từ,
**để** không phải tìm màn và thao tác từng bước.

Bối cảnh: UC-DW-08; BR-AI-34; 02b §1, §8.1 (trường `ai` của bước). Chạy với LLMock; model thật khi S08 xong.
Thay S09 cũ.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-14-AC1 | `nv_kho` hỏi "còn bao nhiêu CA-001" | chat chạy index → tìm → descriptor → `call` | câu trả lời có nhãn "AI", số khớp `result` của `call` | BR-AI-14 |
| DW-14-AC2 | Chủ có `inventory.batch.close` ở C; Quản lý không có quyền | mở khối Tiếp theo của lô | Chủ: bước có `ai={"level":"C","label":"AI soạn nháp chốt lô"}`; Quản lý: `ai=null` | BR-AI-34 |
| DW-14-AC3 | Bước có `ai.level=C` | bấm "Để AI làm" | tạo nháp và mở chi tiết trong "Việc AI"; chứng từ chưa đổi | BR-AI-06 |
| DW-14-AC4 (giá vốn) | Quản lý hỏi "giá vốn lô B-01" | chạy luồng | payload gửi LLMock không có khoá giá vốn; trả lời "bạn không có quyền xem giá vốn" | BR-AI-05, bất biến 1 |
| DW-14-AC5 (PII) | Hỏi "đơn SO… của ai" | chạy luồng | prompt và câu trả lời chỉ mã đơn, trạng thái; không tên/SĐT/địa chỉ | BR-AI-09 |
| DW-14-AC6 (lỗi) | `call` trả 400 `BR-LO-04` | chat | hiện nguyên thông điệp tiếng Việt + mã; không tự thử lại | H16 |
| DW-14-AC7 (máy không model) | Chưa tải model, máy yếu hoặc 4G | mở chat | báo nhập tay; không đẩy lệnh local lên cloud | BR-AI-02, BR-AI-12 |
| DW-14-AC8 (AI tắt) | `AI_ENABLED=false` | mở console | chat và nút "Để AI làm" ẩn; khối Tiếp theo đủ | BR-AI-10 |

## DW-15 — Gỡ registry viết tay S01 và catalog cũ · Must · BE+FE
**Là** Tech Lead, **tôi muốn** chỉ còn một nguồn lệnh, **để** không có hai danh sách lệch nhau.

Bối cảnh: 02b §9.1 bước 2–3, §9.2, Phụ lục B. Chạy sau DW-07 và DW-14.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-15-AC1 | Sau khi gỡ | `GET /api/commands/catalog/` | 404; `registry.py`, `commands/api.py`, `commands/serializers.py`, `test_catalog.py` không còn; FE không còn `getCommandCatalog`, `CommandSpec` | — |
| DW-15-AC2 | 12 lệnh active cũ × 4 Group | đối chiếu Phụ lục B | Group nào thấy lệnh cũ ở catalog thì thấy lệnh tự sinh tương ứng trong chỉ mục (trừ ca Phụ lục B ghi rõ, vd `nhap_lo` chờ DW-17) | BR-AI-04 |
| DW-15-AC3 | Tìm "tra tồn", "tra_ton" | `search.ts` | top-3 có `inventory.batch.list` (tên cũ thành `keywords`) | — |
| DW-15-AC4 (quyền/giá vốn/PII) | Test `test_registry.py` giữ ý (tên duy nhất, schema hợp lệ Draft 2020-12, không khoá PII, quyền tồn tại, có mô tả) | chạy | xanh trên registry tự sinh | BR-AI-01, H2 |
| DW-15-AC5 (AI tắt) | `AI_ENABLED=false` | mở console | không lỗi do thiếu catalog | BR-AI-10 |

## DW-16 — AI tóm tắt "Đã làm" và diễn đạt "Tiếp theo" (chạy trên máy) · Should · FE
**Là** nhân viên mới, **tôi muốn** đọc 2–3 câu tóm tắt chứng từ, **để** hiểu nhanh mà không đọc hết dòng thời gian.

Bối cảnh: Đoạn H1; UC-DW-08; BR-AI-31; Q-M18, Q-M19 (local, 0 đồng). Nút "Tóm tắt" gọi model với payload
guidance, không qua chọn lệnh (02b §2.6). Should: có ích nhưng khối tất định đã đủ dùng.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-16-AC1 | Model local đã tải | bấm "Tóm tắt" trên đơn | ≤ 3 câu, nhãn "AI", nằm trên dòng thời gian thô | BR-AI-14, BR-AI-31 |
| DW-16-AC2 | — | kiểm payload gửi model (LLMock) | chỉ là JSON guidance đã lọc của người xem, không gọi thêm API nào | BR-AI-31 |
| DW-16-AC3 (giá vốn) | `quan_ly` tóm tắt lô đã chốt | — | payload và câu trả lời không có số giá vốn | bất biến 1 |
| DW-16-AC4 (PII) | Đơn có PII giả | tóm tắt | payload không chứa PII (guidance đã bỏ) | bất biến 9 |
| DW-16-AC5 (máy không model) | Không model / iPhone / 4G | mở chứng từ | không có nút tóm tắt; 0 request ra ngoài; không đẩy cloud | BR-AI-02, BR-AI-16 |
| DW-16-AC6 (lỗi) | Model lỗi hoặc quá 10 giây | tóm tắt | ẩn câu, giữ dòng thời gian, báo "không tóm tắt được" | BR-AI-12 |
| DW-16-AC7 (AI tắt) | `AI_ENABLED=false` | mở chứng từ | không nút tóm tắt, khối tất định đủ | BR-AI-10 |

---

# LÔ 4 — Nhập lô trên ERP (form và AI dùng chung một action)

## DW-17 — Nhập lô mua tại cảng trên ERP · Must · BE+FE
**Là** NV kho, **tôi muốn** nhập phiếu mua tại cảng ngay trên ERP (mỗi dòng sinh một lô), **để** không phải
dùng Django Admin, và AI của tôi soạn được đúng phiếu này.

Bối cảnh: L-8; 02b §2.5 ví dụ 2 (action `nhap-lo`, `NhapLoInput`, `create_and_submit_receipt`); BR-MH-01/02/05/06.
Thay S07 cũ. Lệnh AI tự sinh `purchasing.purchasereceipt.nhap_lo` ở **trần C** vì chưa có action huỷ
(`locked_reason=AI_UNDO_MISSING`) cho tới DW-18.

Contract: 02b §2.5, cộng field tuỳ chọn `idempotency_key` (chuỗi ≤ 64) ở body để gửi lại không tạo trùng.
```
POST /api/purchasing/receipts/nhap-lo/
{"supplier": 3, "received_date": "2026-09-28", "idempotency_key": "…",
 "lines": [{"item_code": "CA-001", "qty": "50.000", "rate": "80000.00", "shelf_life_days": 60}]}
→ 201 {"receipt": {...}, "batches": [{"batch_id": "CA01-…", "status": "DRAFT", "expiry_date": "…"}]}
   // "rate" chỉ có khi người gọi có view_costprice
→ 400 {"detail": "…", "code": "BR-MH-02"} · 400 {"errors": {...}} · 403
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-17-AC1 | NV kho, 2 dòng hàng | gửi form | 201; 1 phiếu SUBMITTED, 2 lô DRAFT; hạn = ngày nhập + `shelf_life_days` (mặc định 90); AuditLog `user` | BR-MH-01, BR-MH-02, BR-MH-05 |
| DW-17-AC2 (lỗi) | `shelf_life_days` > mặc định; `lines` rỗng | gửi | 400 BR-MH-02 / lỗi field; không phiếu, không lô (atomic) | BR-MH-02 |
| DW-17-AC3 | Gửi lại cùng `idempotency_key` (mất mạng, `drafts.ts` gửi lại) | gửi | không tạo phiếu thứ hai, trả phiếu đã tạo; nháp cục bộ xoá sau khi gửi thành công | PA G8 |
| DW-17-AC4 (quyền) | `nv_giao` | mở menu / gọi API | menu ẩn; 403, không đổi dữ liệu | BR-PQ-12 |
| DW-17-AC5 (giá vốn) | `nv_kho`, `quan_ly` | xem response và danh sách lô | không `rate`, `purchase_rate`, `landed_unit_cost`; `chu` có | BR-MH-06, bất biến 1 |
| DW-17-AC6 (lệnh AI) | NV kho | index, rồi `call` lệnh `nhap_lo` | `level=C`, `choices=["OFF","C"]`, `locked_reason.code=AI_UNDO_MISSING`; `call` → nháp, DB không đổi; duyệt → phiếu tạo, AuditLog `user` + `proposal_ref` | BR-AI-06, BR-AI-19 |
| DW-17-AC7 (PII) | — | xem phiếu, lô, nháp | không dữ liệu khách | bất biến 9 |
| DW-17-AC8 (AI tắt) | `AI_ENABLED=false` | mở màn nhập lô | form đủ, không nút AI | BR-AI-10 |

---

# LÔ 5 — Mức B (AI tự ghi có hoàn tác) · CHỈ STAGING tới khi S-L1…S-L4 xong

Env: staging `AI_WRITE_LEVELS_ALLOWED=B`; production giữ `C` và `AI_PRODUCTION_READY=false` (BR-AI-27).

## DW-18 — Huỷ phiếu nhập bằng trạng thái (BR-MH-07 mới) · Must · BE+FE
**Là** NV kho, **tôi muốn** huỷ phiếu nhập vừa nhập sai khi lô còn Nháp, **để** sửa sai mà không xoá chứng
từ — và để AI của tôi có đường hoàn tác khi tự ghi.

Bối cảnh: 01-analysis §5 dòng 1, §11 "nghiệp vụ huỷ phiếu nhập"; H4, BR-AI-24. **BR-MH-07 (đề xuất, PA):**
"Phiếu nhập huỷ được bằng trạng thái khi mọi lô sinh từ phiếu còn **Nháp** (chưa publish), chưa xuất kho,
chưa gắn Purchase Cost hay Purchase Invoice. Huỷ phiếu → các lô đó chuyển Huỷ, sổ kho ghi bút toán đảo,
không xoá dòng nào. Người tạo phiếu huỷ được phiếu của mình; Quản lý, Chủ huỷ được mọi phiếu." Không thêm
trạng thái mới nếu `PurchaseReceipt` đã có CANCELLED; nếu chưa có → migration thêm choice (Tech Lead ghi lý
do theo bất biến 8).

Contract (mới): `POST /api/purchasing/receipts/<pk>/cancel/ {}` → 200 `{"id", "status": "CANCELLED"}` · 400
`{"code": "BR-MH-07"}` · 403.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-18-AC1 | Phiếu SUBMITTED, 2 lô DRAFT chưa xuất | người tạo phiếu bấm Huỷ | phiếu CANCELLED, 2 lô CANCELLED, sổ kho có bút toán đảo, AuditLog; không dòng nào bị xoá | BR-MH-07, bất biến 3 |
| DW-18-AC2 (lỗi) | Một lô đã publish, hoặc có Purchase Cost/Invoice | huỷ | 400 BR-MH-07, không đổi | BR-MH-07 |
| DW-18-AC3 (quyền) | `nv_kho` khác người tạo; `nv_giao` | huỷ | 403 | BR-PQ-12 |
| DW-18-AC4 (song song) | Huỷ phiếu cùng lúc publish lô | gọi đồng thời | đúng một thao tác thành công | bất biến 4 |
| DW-18-AC5 (giá vốn) | `quan_ly` xem dòng thời gian phiếu đã huỷ | — | không có `rate` | bất biến 1 |
| DW-18-AC6 (lệnh AI) | Sau khi action `cancel` có | xem descriptor `nhap_lo` | `max_level=B`, `locked_reason` không còn `AI_UNDO_MISSING` | BR-AI-24 |
| DW-18-AC7 (AI tắt) | `AI_ENABLED=false` | huỷ phiếu | chạy bình thường | BR-AI-10 |

## DW-19 — Mức B: AI tự ghi, báo ngay, hoàn tác trong 10 phút · Must · BE+FE
**Là** NV kho, **tôi muốn** cho AI tự ghi phiếu nhập dưới ngưỡng tôi đặt và hoàn tác được trong 10 phút,
**để** nhập nhanh tại cảng mà vẫn sửa được nếu AI sai.

Bối cảnh: UC-DW-02; BR-AI-19/20/24/27; Q-M8 (10 phút), Q-M9 (200 kg / 30.000.000đ), Q-M10 (20 lần/ngày),
Q-M13 (lệnh ghi trần B trừ `cap_nhat_giao`); 02b §4.2 bước 7–8.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-19-AC1 | Staging, NV kho đặt `nhap_lo=B`, ngưỡng 150 kg | `call` phiếu 50 kg | `outcome=done`, `level=B`, `undo_until`=+10 phút; phiếu người thực hiện = NV kho; AuditLog `actor_kind=ai`, `ai_level=B`, `ai_config_version` | BR-AI-08, BR-AI-20 |
| DW-19-AC2 (production) | `AI_WRITE_LEVELS_ALLOWED=C` | GET my-config / PUT `B` | `choices` không có B; PUT → 400 `BR-AI-27` | BR-AI-27 |
| DW-19-AC3 | Trong 10 phút | `POST /api/ai/actions/<id>/undo/` | phiếu và lô CANCELLED qua action `cancel` (DW-18); `AiAction` UNDONE; AuditLog hoàn tác riêng | BR-AI-24 |
| DW-19-AC4 (lỗi) | Quá 10 phút, hoặc lô đã publish | undo | 410 `AI_UNDO_WINDOW_CLOSED` / 400 BR-MH-07; không đổi | BR-AI-24 |
| DW-19-AC5 (hạ mức) | Phiếu 180 kg (> ngưỡng 150); lần thứ 21 trong ngày; `global_mode=c_only`; user bị tắt khẩn | `call` | `outcome=proposal`, `level=C`, `downgrade_reason.code` tương ứng (`AI_LIMIT_KG`, `AI_DAILY_LIMIT`, …); DB không đổi | BR-AI-19, BR-AI-22 |
| DW-19-AC6 (H5) | Ép ghi AuditLog lỗi | `call` mức B | phiếu không được tạo (rollback) | H5 |
| DW-19-AC7 (quyền) | Mọi lệnh thuộc "trần C ép" (02b §3) | PUT B | 400 `BR-AI-19` | BR-AI-18 |
| DW-19-AC8 (giá vốn) | Thông báo "AI đã ghi" | người thiếu `view_costprice` xem | không có đơn giá | bất biến 1 |
| DW-19-AC9 (FE) | AI ghi mức B | — | thông báo "AI đã ghi" + nút Hoàn tác đếm ngược tới `undo_until`; nhãn AI trên phiếu | BR-AI-14 |
| DW-19-AC10 (AI tắt) | `AI_ENABLED=false` | undo | 410; phiếu sửa theo quy trình tay (DW-18) | BR-AI-10 |

## DW-20 — Chủ đặt trần ngưỡng và hạn mức ngày cho lệnh AI · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** đặt trần kg, tiền và số lần mỗi ngày cho từng lệnh, **để** nhân viên không cấu
hình AI thoáng hơn mức tôi chịu được.

Bối cảnh: Q-M2, Q-M9, Q-M10; 02b §6.6 `caps`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-20-AC1 | Chủ PUT `caps.nhap_lo={kg:200, vnd:30000000, daily:20}` | NV kho PUT ngưỡng 250 kg | 400 `BR-AI-19` "vượt trần của Chủ" | BR-AI-19 |
| DW-20-AC2 | NV kho đặt 150 kg; Chủ hạ trần còn 100 kg | NV kho `call` phiếu 120 kg | hạ C (ngưỡng hiệu lực = min) | BR-AI-19 |
| DW-20-AC3 (production) | `AI_PRODUCTION_READY=false` | Chủ PUT trần `max_level` > C | 400 `BR-AI-27` | BR-AI-27 |
| DW-20-AC4 (quyền) | `quan_ly` | PUT caps | 403 | BR-PQ-12 |
| DW-20-AC5 (lỗi) | Số âm hoặc không phải số | PUT | 400, không phiên bản mới | — |
| DW-20-AC6 (AI tắt) | `AI_ENABLED=false` | PUT caps | vẫn chạy | BR-AI-10 |

## DW-21 — Trì hoãn ghi (B cho lệnh không có trạng thái huỷ) + job chạy việc tới hạn · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** việc AI tự ghi mà không có đường huỷ được xếp lịch và tôi huỷ được trong cửa sổ,
**để** có thời gian chặn trước khi chứng từ thật đổi.

Bối cảnh: 01-analysis §5 "B kiểu trì hoãn ghi"; BR-AI-21/24; Q-M5; 02b §4.2 (job `run_due_ai_actions`).
Nền cho DW-25 và cho `cap_nhat_giao` (hồ sơ giao hàng). Test bằng lệnh thử khai `undo="defer"`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-21-AC1 | Lệnh `undo="defer"` ở mức B | `call` | `outcome=scheduled`, `execute_after`=+N phút; chứng từ **chưa đổi** | BR-AI-24 |
| DW-21-AC2 | Tới hạn, mọi điều kiện còn đạt | job chạy | kiểm lại bước 2–7 rồi gọi view; `AiAction` DONE; AuditLog `ai_level=B` | BR-AI-04 |
| DW-21-AC3 (thu hồi) | Trong cửa sổ: cấu hình về C, hoặc tắt khẩn, hoặc mất quyền, hoặc điều kiện nghiệp vụ đổi | job chạy | không ghi; `AiAction` PENDING (C) kèm lý do | BR-AI-21, Q-M5, H12 |
| DW-21-AC4 | Chủ AI bấm huỷ lịch trong cửa sổ | `undo` | `AiAction` CANCELLED, chứng từ không đổi | BR-AI-24 |
| DW-21-AC5 (idempotent) | Hai tiến trình job chạy cùng lúc | — | view được gọi đúng 1 lần (`select_for_update(skip_locked=True)`) | bất biến 6 (tinh thần job idempotent) |
| DW-21-AC6 (quyền) | — | tìm đường gọi `_force_auth_user` từ HTTP | không có; test chứng minh chỉ job dùng được | H1 |
| DW-21-AC7 (PII/giá vốn) | Lệnh thử trên lô và đơn có PII giả | log job | chỉ id lệnh + mã chứng từ | bất biến 1, 9 |
| DW-21-AC8 (AI tắt) | `AI_ENABLED=false` lúc tới hạn | job chạy | không ghi, chuyển PENDING | BR-AI-10 |
| DW-21-AC9 (FE) | Việc đã xếp lịch | xem "Việc AI" | đếm ngược tới `execute_after`, nút "Huỷ lịch" | BR-AI-14 |

## DW-22 — Báo cáo AI cuối ngày cho Chủ · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** mỗi ngày xem AI của từng người đã tự làm gì, bị hoàn tác, bị chuyển hay quá hạn,
**để** rà soát định kỳ đúng nghĩa vụ giám sát.

Bối cảnh: UC-DW-06; BR-AI-26; memo pháp lý §10 (báo cáo hằng ngày là điều kiện bật tự thực thi); contract
02b §6.6 `GET /api/ai/report/daily/`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-22-AC1 | Ngày 28/09 có 3 việc B, 1 hoàn tác, 2 nháp C duyệt, 1 nháp hết hạn, 1 chuyển việc | `GET /api/ai/report/daily/?date=2026-09-28` | `by_user` đếm đúng từng cột; `items` liệt kê đủ | BR-AI-26 |
| DW-22-AC2 (lỗi) | Ngày không có việc; ngày sai định dạng | GET | 200 danh sách rỗng; 400 | — |
| DW-22-AC3 (quyền) | `quan_ly`, `nv_*` | GET | 403 | BR-PQ-12 |
| DW-22-AC4 (PII) | Việc đụng đơn có PII giả | GET | chỉ mã chứng từ | bất biến 9 |
| DW-22-AC5 (AI tắt) | `AI_ENABLED=false` | GET | vẫn xem được lịch sử | BR-AI-10 |

## DW-23 — Chuyển việc cho người có quyền + nút "Nhờ" · Should · BE+FE
**Là** NV kho, **tôi muốn** bấm "Nhờ" trên bước tôi không làm được (vd chốt lô), và việc AI không làm được tự
chuyển đúng người, **để** việc không bị bỏ quên.

Bối cảnh: 01-analysis §8; BR-AI-25; Q-M11 (chỉ trong ERP), Q-M12 (việc khách chờ 2 giờ rồi đẩy Chủ; việc tiền
nhắc mỗi 12 giờ), Q-M20. Hiện trong tab "Được chuyển" của màn "Việc AI" (không chờ S12). Should: giá trị cao
nhưng không chặn B.

Contract (mới, Tech Lead chốt): `POST /api/ai/actions/escalate/ {"doc_type":"batch","doc_id":123,"step_key":"close"}`
→ 201 `{"action_id","assignee_group":"chu"}` · 400 bước không tồn tại / người gửi làm được bước đó.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-23-AC1 | NV kho xem lô, bước "Chốt lô" `allowed=false` | bấm "Nhờ" | `AiAction` ESCALATED, `assignee_group=chu`; Chủ thấy trong tab "Được chuyển" | BR-AI-25, Q-M20 |
| DW-23-AC2 | Job B (DW-21) gặp `BusinessError` | job chạy | ESCALATED cho chủ AI; nếu chủ AI thiếu quyền → Group có quyền (tiền/chốt lô → `chu`; kho, giao, phiếu hoàn → `quan_ly` rồi `chu`) | BR-AI-25 |
| DW-23-AC3 (quá hạn) | Việc khách chờ quá 2 giờ | job nhắc | đẩy lên `chu`; **không** tự thực thi | BR-AI-25 |
| DW-23-AC4 (giá vốn) | Việc chuyển tới `quan_ly` về lô | xem | không số giá vốn (lọc theo người nhận) | H3 |
| DW-23-AC5 (PII) | Việc đụng đơn | xem | chỉ mã đơn, việc cần làm, hạn | H2 |
| DW-23-AC6 (quyền/lỗi) | Người gửi tự làm được bước; bước không tồn tại | escalate | 400 | — |
| DW-23-AC7 (AI tắt) | `AI_ENABLED=false` | bấm "Nhờ" | vẫn chạy (không cần model) | BR-AI-10 |

---

# LÔ 6 — Vùng đỏ (cuối cùng) · CHỈ STAGING tới khi S-L1…S-L4 xong

## DW-24 — Công tắc vùng đỏ của Chủ · Should · BE+FE
**Là** Chủ vựa, **tôi muốn** tự mở từng lệnh vùng đỏ cho AI của mình, biết rõ AI làm được và không làm được gì,
**để** bớt thao tác khi vắng mà vẫn là người chịu trách nhiệm.

Bối cảnh: UC-DW-04; BR-AI-07 (mới), BR-AI-18, BR-AI-27; Q-M7 (production chặn); contract 02b §6.6 `red_zone`.
Should: Duy xếp cuối cùng, và giá trị thực nhỏ (01-analysis §7).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-24-AC1 | Staging, Chủ | GET policy | 3 mục vùng đỏ (`close_batch`, `confirm_refund`, `confirm_payment_manual`) có `can_do`, `cannot_do`, `legal_note`, mặc định `open=false` | BR-AI-18 |
| DW-24-AC2 | Chủ PUT mở `inventory.close_batch` (tick trách nhiệm) | GET my-config của Chủ | `inventory.batch.close` `choices` có B; phiên bản chính sách +1, AuditLog | BR-AI-07 |
| DW-24-AC3 (production) | `AI_PRODUCTION_READY=false` | PUT mở vùng đỏ | 400 `BR-AI-27` | BR-AI-27, Q-M7 |
| DW-24-AC4 (đóng lại) | Chủ đang để B, có việc SCHEDULED | Chủ đóng công tắc | cấu hình rơi về C ngay; việc SCHEDULED không ghi, về PENDING | BR-AI-07, BR-AI-21 |
| DW-24-AC5 (quyền) | `quan_ly` | PUT policy; GET my-config | 403; không thấy 3 lệnh vùng đỏ | H1, BR-HT-07 |
| DW-24-AC6 (feature mới) | Action thử dùng quyền `close_batch` | mở công tắc | action đó tự theo công tắc (khoá theo quyền) | BR-AI-18 |
| DW-24-AC7 (AI tắt) | `AI_ENABLED=false` | xem policy | vẫn xem/đổi được | BR-AI-10 |

## DW-25 — AI của Chủ chốt lô (trì hoãn 30 phút) khi đủ điều kiện sàn · Should · BE
**Là** Chủ vựa, **tôi muốn** AI của tôi xếp lịch chốt những lô đã đủ mọi điều kiện, **để** không bỏ sót lô
chờ chốt khi tôi đi cảng.

Bối cảnh: 01-analysis §7.1; Q-M6 (7 ngày không chi phí mới, kiểm kê đã duyệt, không việc chờ); Q-M8 (30 phút);
Q-M10 (10 lần/ngày). Phụ thuộc L-1 (hồ sơ `sua-loi-bao-mat`), DW-21, DW-24.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-25-AC1 | Lô SOLD_OUT đủ BR-LO-04, có kiểm kê duyệt sau lần xuất cuối, 7 ngày không chi phí mới, không phiếu hoàn/hàng hoàn/giao dịch lệch chờ; công tắc mở; Chủ đặt B | AI `call` chốt lô | `scheduled`, `execute_after`=+30 phút; tới hạn → CLOSED, `closed_by`=Chủ, AuditLog `ai_level=B`, `ai_policy_version` | BR-LO-04, BR-KK-05, BR-AI-20 |
| DW-25-AC2 (hạ mức) | Thiếu 1 điều kiện (vd chi phí mua mới 3 ngày trước) | `call` | hạ C, `downgrade_reason` nêu điều kiện; không xếp lịch | BR-AI-19 |
| DW-25-AC3 | Chủ huỷ lịch trong 30 phút | `undo` | lô không chốt | BR-AI-24 |
| DW-25-AC4 (lỗi) | Có đơn mới giữ lô trong 30 phút | job tới hạn | không chốt, về PENDING + chuyển việc Chủ | BR-LO-04, H16 |
| DW-25-AC5 (giá vốn) | Thông báo / việc chuyển về lô | người thiếu `view_costprice` | không số | H3 |
| DW-25-AC6 (quyền) | `quan_ly` có cấu hình cũ | `call` | 404 | H1 |
| DW-25-AC7 (AI tắt) | `AI_ENABLED=false` | Chủ chốt tay | chạy bình thường | BR-AI-10 |

## DW-26 — Xác nhận thanh toán tay cho ca khớp tuyệt đối · Could · BE
**Là** Chủ vựa, **tôi muốn** giao dịch lệch khớp tuyệt đối với một đơn đang giữ chỗ được xác nhận mà không cần
tôi, **để** khách không bị huỷ đơn oan khi IPN đến trễ.

Bối cảnh: 01-analysis §7.3; Q-T5 (mặc định đã duyệt: làm bằng **job Hệ thống**, `actor_kind=system`; chốt lại ở
đầu Lô 6 — xem câu hỏi V-DW1). Could: 01-analysis ghi giá trị thực nhỏ.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-26-AC1 | Giao dịch UNMATCHED/OPEN: số tiền **đúng bằng** tổng đơn, mã đơn khớp **đúng 1** đơn BOOKED, mã GD chưa dùng, không cờ nghi trùng, đúng môi trường | đường thực thi theo Q-T5 chạy | đơn PAID qua đúng đường ghi tiền hiện có; giao dịch RESOLVED; AuditLog | BR-TT-03, BR-TT-14, BR-TT-15 |
| DW-26-AC2 (không khớp) | Thiếu/thừa tiền; khớp 0 hoặc ≥ 2 đơn; đơn đã tự huỷ; có cờ nghi trùng | chạy | không xác nhận; chuyển việc cho `chu` kèm lý do | BR-TT-05, BR-AI-25 |
| DW-26-AC3 (PII, H2) | — | kiểm luồng | khớp bằng code; không có đường nào đưa `raw_payload`/nội dung CK vào model; log chỉ mã GD + mã đơn | H2, H10 |
| DW-26-AC4 (quyền) | `quan_ly` | xem/gọi | không thấy lệnh; 404 | BR-TT-07 |
| DW-26-AC5 (production) | `AI_PRODUCTION_READY=false` | production | không chạy | BR-AI-27 |
| DW-26-AC6 (AI tắt) | `AI_ENABLED=false` | Chủ xác nhận tay | chạy bình thường | BR-AI-10 |

## DW-27 — Xác nhận hoàn tiền: AI luôn chuyển Chủ kèm việc cần làm · Should · BE
**Là** Chủ vựa, **tôi muốn** AI nhắc tôi đúng phiếu hoàn cần chuyển tiền và không bao giờ tự đánh dấu "đã hoàn",
**để** sổ không ghi "đã hoàn" khi tiền chưa đi.

Bối cảnh: 01-analysis §7.2 (V1 không có nguồn tiền-ra); BR-HT-03; Q-L3 để sau.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| DW-27-AC1 | Phiếu hoàn PENDING, công tắc `confirm_refund` mở, Chủ đặt B | AI `call` `sales.refund.confirm` | luôn hạ C với `downgrade_reason.code=AI_NO_EVIDENCE`; tạo việc chuyển "chuyển X đ cho phiếu RF-…, rồi nhập mã giao dịch" | BR-AI-07, BR-HT-03 |
| DW-27-AC2 (lỗi) | args do model điền có `bank_txn_ref` | `call` | vẫn chỉ C; `bank_txn_ref` từ model không bao giờ được ghi tự động | H10, BR-HT-03 |
| DW-27-AC3 (quyền) | `quan_ly` (có `create_refund`) | index | không có `sales.refund.confirm` | BR-HT-07 |
| DW-27-AC4 (PII) | Việc chuyển | xem | chỉ mã phiếu, số tiền, hạn; không tên/số tài khoản khách | bất biến 9 |
| DW-27-AC5 (AI tắt) | `AI_ENABLED=false` | Chủ xác nhận tay | chạy bình thường | BR-AI-10 |

---

# Tổng kết

## Bảng story

| Mã | Tiêu đề | Lô | BE/FE | MoSCoW | Phụ thuộc |
|---|---|---|---|---|---|
| DW-01 | Spike BE: sinh schema + gọi lại view | 0 | BE | Must | — |
| DW-02 | Spike FE: chọn lệnh, tìm từ khoá, ngân sách token | 0 | FE | Must | DW-01 (chỉ mục), S08 (harness) |
| DW-03 | Tiếp theo · Đã làm trên Đơn (khung chung) | 1 | BE+FE | Must | — |
| DW-04 | Tiếp theo · Đã làm trên Phiếu hoàn, Giao dịch lệch | 1 | BE+FE | Must | DW-03 |
| DW-05 | Tiếp theo · Đã làm trên Lô | 1 | BE+FE | Must | DW-03, L-1 (sua-loi-bao-mat) cho bước chốt |
| DW-06 | Chủ huỷ lô quá hạn (BR-LO-03) | 1 | BE+FE | Must | DW-05 |
| DW-07 | Lệnh AI tự sinh, chỉ mục theo quyền, mặc định an toàn | 2 | BE | Must | DW-01 |
| DW-08 | Khai `required_perms` + test kỷ luật tự đăng ký | 2 | BE | Must | DW-07 |
| DW-09 | FE chọn lệnh 2 bước + ngân sách token | 2 | FE | Must | DW-02, mock DW-07 |
| DW-10 | AI gọi lệnh đọc (A) kết quả đã lọc | 3 | BE | Must | DW-07, DW-08 |
| DW-11 | Lệnh ghi thành nháp C + màn Việc AI | 3 | BE+FE | Must | DW-10 |
| DW-12 | Màn AI của tôi + tắt AI của mình | 3 | BE+FE | Must | DW-10 |
| DW-13 | Chính sách AI: tắt khẩn toàn cục/theo người | 3 | BE+FE | Must | DW-12 |
| DW-14 | Chat qua `call` + nút "Để AI làm" | 3 | BE+FE | Must | DW-09, DW-11, DW-12, S08 |
| DW-15 | Gỡ registry S01 + catalog cũ | 3 | BE+FE | Must | DW-07, DW-14 |
| DW-16 | AI tóm tắt Đã làm (local) | 3 | FE | Should | DW-03, S08 |
| DW-17 | Nhập lô mua tại cảng trên ERP | 4 | BE+FE | Must | DW-11 |
| DW-18 | Huỷ phiếu nhập bằng trạng thái (BR-MH-07) | 5 | BE+FE | Must | DW-17 |
| DW-19 | Mức B: tự ghi + hoàn tác 10 phút | 5 | BE+FE | Must | DW-18, DW-20 |
| DW-20 | Chủ đặt trần ngưỡng, hạn mức ngày | 5 | BE+FE | Must | DW-13 |
| DW-21 | Trì hoãn ghi + job việc tới hạn | 5 | BE+FE | Must | DW-19 |
| DW-22 | Báo cáo AI cuối ngày | 5 | BE+FE | Must | DW-19 |
| DW-23 | Chuyển việc + nút "Nhờ" | 5 | BE+FE | Should | DW-21, DW-03 |
| DW-24 | Công tắc vùng đỏ của Chủ | 6 | BE+FE | Should | DW-20, DW-21 |
| DW-25 | AI chốt lô trì hoãn 30 phút | 6 | BE | Should | DW-24, L-1 |
| DW-26 | Xác nhận thanh toán ca khớp tuyệt đối | 6 | BE | Could | DW-24, V-DW1 |
| DW-27 | Xác nhận hoàn: luôn chuyển Chủ | 6 | BE | Should | DW-24, DW-23 |

MoSCoW một dòng: **Must** = hướng dẫn tất định (P2), nền lệnh tự sinh + mức C + tắt khẩn (P3), và phần tối
thiểu để "AI của tôi" có nghĩa (B có hoàn tác, trần, báo cáo ngày — điều kiện pháp lý của tự thực thi);
**Should** = tóm tắt AI, chuyển việc, vùng đỏ (Duy xếp cuối, giá trị thực nhỏ); **Could** = DW-26 (Q-T5 còn
cân nhắc đường thực thi); **Won't (đợt này)** = mục "Để sau".

## Thứ tự làm (BE ∥ FE mỗi lô; mỗi lô QA APPROVED → commit + push)

| Bước | Story | Lý do |
|---|---|---|
| Trước tất cả | Hồ sơ `2026-09-28-sua-loi-bao-mat` (L-1, L-3, L-5, L-6) | Duy T1: làm trước; L-1 chặn bước chốt lô của DW-05, DW-25 |
| **Lô 1 (P2)** | DW-03 → DW-04 ∥ DW-05 → DW-06 | Không phụ thuộc AI, có lợi ngay khi AI tắt; DW-03 dựng khung |
| **Lô 0** (song song Lô 1) | DW-01 (BE) ∥ DW-02 (FE) | Spike phải xong và đạt trước Lô 2 |
| **Lô 2 (P3)** | DW-07 → DW-08 (BE) ∥ DW-09 (FE mock) | Nguồn lệnh trước, kỷ luật CI sau; FE theo contract 02b §6.2 |
| **Lô 3 (P3)** | DW-10 → DW-11 ∥ DW-12 → DW-13; DW-14 (FE) → DW-15; DW-16 khi S08 xong | Đọc trước ghi; cấu hình trước tắt khẩn; gỡ catalog cuối lô |
| **Lô 4 (P3)** | DW-17 | Cần nháp C (DW-11) |
| **Lô 5 (P7, staging)** | DW-18 → DW-20 → DW-19 → DW-21 → DW-22 ∥ DW-23 | Có đường huỷ và trần trước khi mở B |
| **Lô 6 (P7, staging)** | DW-24 → DW-25 ∥ DW-27 → DW-26 | Công tắc trước lệnh; DW-26 cuối vì Could |
| Production | Chỉ khi S-L1…S-L4 xong và Duy đổi env (`AI_WRITE_LEVELS_ALLOWED`, `AI_PRODUCTION_READY`) | BR-AI-27 |

## Story cũ hồ sơ `2026-09-27-ai-native-erp` — thay / giữ

| Story cũ | Trạng thái cũ | Số phận | Ghi chú |
|---|---|---|---|
| S01 Danh mục lệnh + catalog | Đã code | **Thay** bởi DW-07, gỡ ở DW-15 | Catalog giữ nguyên JSON tới DW-15; ý các test giữ, đổi đích (02b §9.2) |
| S02 execute/propose/confirm | Chưa xây | **Thay** bởi DW-10, DW-11 | `AiProposal` → `AiAction`; không có kênh `ui` riêng |
| S03 AuditLog actor `ai:<user>` | Đã code | **Giữ**, mở rộng ở DW-11 | Thêm `ai_level`, `ai_config_version`, `ai_policy_version` + index; lỗi L-3 sửa ở hồ sơ sua-loi-bao-mat |
| S04 Trần chi phí cloud | Chưa | **Giữ** nguyên | H8 |
| S05 `AI_ENABLED` + `/api/ai/status` | Chưa | **Giữ** nguyên | Mọi DW dùng công tắc này |
| S06 Context builder allowlist | Chưa | **Thay** bởi DW-10 (serializer của view + lọc đầu ra §3) | |
| S07 Màn nhập lô qua lớp lệnh | Chưa | **Thay** bởi DW-17 | Contract đổi: `POST /api/purchasing/receipts/nhap-lo/` |
| S08 Runtime on-device | **Đang dở** | **Giữ**, làm tiếp | DW-02, DW-14, DW-16 phụ thuộc; trước đó dùng LLMock |
| S09 Chat tra cứu 3 lệnh | Chưa | **Thay** bởi DW-09 + DW-10 + DW-14 | Ý AC (giá vốn, PII, tràn context, hỏi lại 3 lần) chuyển sang DW-09/DW-14 |
| S10 Voice nhập lô | Chưa | **Giữ**, đổi contract | propose/confirm → `call` (C) + `actions/confirm`; phụ thuộc DW-17, DW-11, S08 |
| S11 Adapter cloud | Chưa | **Giữ** | Orchestrator cloud gọi cùng lớp thực thi kênh `ai_cloud`, từ chối lệnh `local` (H13) |
| S12 Proactive Alerts | Chưa | **Giữ** | Việc chuyển hiện ở "Việc AI" (DW-23), S12 gom sau |
| S13 Dashboard Insights | Chưa | **Giữ** | |
| S14 Inline Suggestions + Auto-fill | Chưa | **Giữ**, đổi nguồn schema | Auto-fill theo descriptor (DW-07) thay registry S01 |
| S15 Smart Buttons FEFO | Chưa | **Giữ** | Bỏ gợi ý `POST /api/commands/execute`; nếu cần endpoint thì là API thường, tự thành lệnh |
| S16 Tóm tắt hội thoại | Chưa | **Giữ** (Could) | |
| S17 Spike 50 câu thật | Chờ máy | **Giữ** | DW-02 dùng lại bộ 50 câu |

## Rủi ro / phụ thuộc

1. **Hồ sơ `sua-loi-bao-mat` chưa có file** lúc viết story. DW-05 (bước chốt lô) và DW-25 chặn cứng bởi L-1.
2. **S08 đang dở**: DW-14, DW-16 nghiệm thu với LLMock; E2E với model thật chạy lại khi S08 xong.
3. **Spike không đạt** (DW-01/02): không mở Lô 2; Tech Lead sửa 02b, PO chỉnh AC con số.
4. **Màn chưa có** (phiếu giao S17/S20, kiểm kê S34, phiếu nhập chi tiết S28, hàng hoàn): khối Tiếp theo · Đã làm
   và `AiMeta` của các màn đó thuộc story của hồ sơ tương ứng; phải qua test kỷ luật DW-08.
5. **Group `cskh`** đến từ hồ sơ CSKH; DW-12-AC10 dùng Group fixture để không chờ.
6. **Pháp lý**: production chỉ mức C cho tới khi S-L1…S-L4 xong (Duy/Lộc làm, không phải code).
7. **BR-MH-07** là rule mới (PA) — Duy ghi vào spec/decisions khi nghiệm thu DW-18.

## Để sau (ngoài đợt này)

- B cho ca tất định của `tao_phieu_hoan` (01-analysis §5): 02b §3 đã xếp `create_refund` vào "trần C ép"; mở
  cần Duy quyết riêng (kèm Q-L2 BR-HT-06).
- `cap_nhat_giao` A/B, `kiem_ke` vai nhập số B: khai `AiMeta` khi hồ sơ giao hàng (S17) và kiểm kê (S34) xây.
- AI chạy nền khi chủ AI không đăng nhập (Q-M4); tìm lệnh bằng embedding (chỉ khi DW-02 không đạt); tóm tắt trên
  cloud (Q-M19); MCP / agent ngoài ERP (Q-T2); vai trò tự định nghĩa; nguồn tiền-ra cho `xac_nhan_hoan` (Q-L3).

## Câu hỏi cho Duy (🟡 — có mặc định, không chặn code)

| # | Câu hỏi | Mặc định PO |
|---|---|---|
| V-DW1 | DW-26: nếu làm bằng job Hệ thống (Q-T5), job có cần qua công tắc riêng của Chủ không? | **Có**: công tắc riêng, mặc định đóng, chỉ bật ở staging tới khi S-L xong — vì đây là tự xác nhận tiền không có người. |
| V-DW2 | DW-18: ai được huỷ phiếu nhập? | Người tạo phiếu (phiếu của mình) + Quản lý, Chủ (mọi phiếu); chỉ khi mọi lô còn Nháp. |
| V-DW3 | DW-06: quyền huỷ lô quá hạn | Quyền Tầng 2 mới `cancel_expired_batch`, chỉ `chu` (đổi con số lời lỗ). |
| V-DW4 | DW-12: "Tắt AI của tôi" là rơi về C hay tắt hẳn? | Rơi về C cho lệnh ghi, lệnh đọc vẫn chạy (theo 01-analysis §4.5). |
