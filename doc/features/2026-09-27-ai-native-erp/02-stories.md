# AI Native ERP — User stories
> PO · 2026-09-27 · Nguồn: 01-analysis.md (ĐÃ DUYỆT, Q1–Q6 đã chốt) · Trạng thái: **ĐÃ DUYỆT (Duy, 27/09)** — chốt kèm: model Gemma 3n 32k (ADR điểm 9); máy chuẩn Android/Windows ≥ 8GB RAM, iPhone tạm chưa hỗ trợ; AI là add-on bật/tắt theo user, giữ 1 bản build (chuẩn "không tải/không chạy"); hiệu năng không đánh đổi (BR-AI-17, ADR điểm 10).

## Mục tiêu & thước đo

**Vì sao làm:** ERP **nói được, gợi ý được, cảnh báo được** — nhập liệu nhanh tại cảng, giảm nút
cổ chai khi Lộc vắng mặt, chặn sai giá vốn ngay lúc nhập — trong ngân sách cloud ≤ 200.000đ/tháng
và tuân thủ Luật AI 134/2025 + bất biến 9 (không rò dữ liệu cá nhân khách).

**Đo thành công bằng gì** (kiểm bằng AC trong file này):

| Thước đo | AC gắn |
|---|---|
| Tỉ lệ đúng field của voice trên 50 câu thật ≥ ngưỡng Duy chốt (đề xuất 80%, xem câu hỏi V1) | S17-AC1 |
| Chi phí cloud không bao giờ vượt 200.000đ/tháng; cảnh báo đúng lúc 160.000đ (80%) | S04-AC1…4 |
| Mọi thực thi nghiệp vụ từ UI/AI đi qua lớp lệnh; dấu vết audit truy được AI + người | S01-AC1, S02-AC1 |
| Tắt AI toàn cục → hệ thống chạy 100% bằng tay (AC có trong mọi story AI) | BR-AI-10 |
| 0 lần PII khách xuất hiện trong prompt/log/test/doc (kiểm bằng test chặn) | S06-AC3, S11-AC2 |

## Phạm vi

**Trong:** ERP console nội bộ (`erp-console/`), backend Django, adapter FastAPI — theo 3 giai đoạn
của BA §10: Giai đoạn 0 (lớp lệnh + router + context + audit + trần + màn nhập lô S28) → Giai đoạn 1
(voice nhập lô + chat tra cứu 2–3 lệnh) → Giai đoạn 2 (entry point mở rộng + cloud).

**Ngoài (giai đoạn này):** Shop/khách hàng (không AI), agent actions (chờ Duy quyết BR-PQ-11),
image input/OCR, semantic search, RAG cục bộ, bộ nhớ phân tầng, kênh AI cho Django Admin toàn phần,
lệnh `negotiate_price` (nghiệp vụ không tồn tại — URD §4.2). Story S34/S17/S20/S36/S38 (kiểm kê,
giao hàng, báo cáo, danh mục) thuộc hồ sơ khác, chỉ phối hợp thứ tự.

## Definition of Done (chung — không lặp lại trong từng story)

1. Backend: `cd backend && .venv/bin/python manage.py test` xanh; migration đi kèm nếu đổi model.
2. ERP console: `tsc --noEmit && npm run build` sạch; adapter: `pytest -q` xanh.
3. QA report APPROVED (mỗi AC có ít nhất 1 test tự động, QA truy vết theo mã AC).
4. Không rò giá vốn: test kênh AI/UI bằng token từng Group (tinh thần BR-PQ-13).
5. Không rò PII: prompt/log/test/doc chỉ dùng dữ liệu giả; log chỉ ghi mã lệnh/mã đơn/mã user.
6. Không dùng dữ liệu vận hành thật cho test/spike khi Q3 chưa chốt (checklist research #9).
7. Doc cập nhật nếu đổi rule; BR mới ghi vào hồ sơ feature.
8. Commit + push origin main khi lô QA APPROVED (quy ước 2026-09-25).

## Ký hiệu & nguồn rule

- **Mã AC** `S01-AC2` — QA truy vết theo mã này; "(lỗi)"/"(quyền)"/"(giá vốn)"/"(PII)"/"(AI tắt)" ghi rõ loại AC.
- **BR-AI-01…16** — rule mới của hồ sơ này (01-analysis §7); **BR-MH/BR-PQ/BR-BH** — rule hiện có.
- **Q1…Q6** — câu trả lời đã chốt của Duy (đầu 01-analysis); **V1…V5** — câu hỏi mới của PO (cuối file).
- **Kênh** trong API: `ui` / `ai_local` / `ai_cloud` — lớp lệnh nhận tham số `channel` để chặn đúng chiều (BR-AI-02).
- **Contract API** trong mỗi story là dự kiến để BE/FE làm song song; FE dựng mock theo đúng contract, đổi tên field phải báo PO.

---

# GIAI ĐOẠN 0 — Nền tảng (lớp lệnh + router + phân quyền + audit + trần chi phí + màn nhập lô)

## S01 — Danh mục lệnh nghiệp vụ + catalog theo quyền · Must · BE
**Là** Chủ vựa/Quản lý/NV kho, **tôi muốn** hệ thống có một danh mục lệnh nghiệp vụ (6 trường schema)
liệt kê đúng theo quyền của tôi, **để** AI không bao giờ gợi ý lệnh tôi không được làm và mọi kênh
dùng chung một bộ mô tả.

Bối cảnh: ADR 2.5 + BR-AI-01; BA §4.1 (14 lệnh khởi đầu); hiện trạng service layer đã có, thiếu danh mục.
Đề xuất PA G4: registry bằng code trong Django + endpoint, chưa cần bảng DB.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S01-AC1 | Registry khai danh đủ các lệnh §4.1 | gọi `GET /api/commands/catalog` bằng token `chu` | nhận danh sách lệnh, mỗi lệnh có đủ 6 trường: `name`, `channel` (local/cloud), `sensitivity` (cao/trung bình/thấp), `min_permissions`, `input_schema`, `output_schema` (JSON Schema hợp lệ), `status` (active/draft) | BR-AI-01 |
| S01-AC2 (quyền) | NV giao đăng nhập | gọi catalog | chỉ nhận lệnh NV giao có quyền tối thiểu (vd `cap_nhat_giao` khi active, `tra_don`); không thấy `nhap_lo`, `bao_cao_lo` | BR-AI-04, BR-PQ-12 |
| S01-AC3 (giá vốn) | Quản lý (không `view_profitreport`) đăng nhập | gọi catalog | không thấy `bao_cao_lo`/`bao_cao_ky`; Chủ thì thấy | BR-AI-05, bất biến 1 |
| S01-AC4 (cấm kênh AI) | token bất kỳ | gọi catalog | 3 lệnh `chot_lo`, `xac_nhan_hoan`, `xac_nhan_thanh_toan_tay` có cờ `forbidden_channel: "ai"`; không lệnh nào khác có cờ này | BR-AI-07 |
| S01-AC5 (lỗi) | token không đăng nhập | gọi catalog | nhận 401, không lộ tên lệnh | BR-PQ-12 |
| S01-AC6 (nhãn) | — | đọc registry | nhãn đúng theo bảng §4.1 đã chốt Q5: `nhap_lo`=local/cao, `tra_ton`=local/trung bình, `tra_don`=local/trung bình, `bao_cao_ton_kho`=cloud/thấp, `bao_cao_lo`/`bao_cao_ky`=cloud/cao | BR-AI-03 |

Ghi chú kỹ thuật:
- 14 lệnh khởi đầu §4.1. `status: active` cho lệnh có service sẵn: `nhap_lo`, `tra_ton`, `tra_lo`,
  `tra_hang`, `tra_don`, `bao_cao_ton_kho`, `bao_cao_lo`, `bao_cao_ky`, `chot_lo`, `tao_phieu_hoan`,
  `xac_nhan_hoan`, `xac_nhan_thanh_toan_tay`; `draft` cho lệnh chưa có màn/service tương ứng
  (`kiem_ke`, `cap_nhat_giao` — active khi S34/S17 của hồ sơ khác hoàn thành). Catalog chỉ trả lệnh `active`.
- Endpoint đặt dưới `config/api_urls.py`, module `apps/ai/commands/` (tên app mới `ai` cho phần điều phối
  AI; registry không đụng model nghiệp vụ hiện có — bất biến 8 ghi lý do trong hồ sơ này).

## S02 — Kênh thực thi & đề xuất lệnh cho AI (execute/propose/confirm) · Must · BE
**Là** Chủ vựa, **tôi muốn** mọi thực thi nghiệp vụ — dù từ UI hay từ AI — đi qua một kênh lệnh duy nhất
kiểm đủ 3 tầng quyền, **để** AI không bao giờ vượt quyền người đăng nhập và hành động Tầng 2 luôn có người xác nhận.

Bối cảnh: UC-AI-03; BR-AI-04/06/07/08; Q6. Phụ thuộc S01, S03. Hiện trạng: api.py mỏng gọi service —
kênh này bọc service hiện có, không viết lại.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S02-AC1 | NV kho đăng nhập | `POST /api/commands/execute` `{command:"tra_ton", args:{ma_hang:"CA-001"}, channel:"ai_local"}` | nhận kết quả tồn theo quyền NV kho; AuditLog ghi 1 dòng actor `ai:<nv_kho>` kèm lệnh + args | BR-AI-04, BR-AI-08 |
| S02-AC2 (quyền T2) | NV kho gửi `nhap_lo` qua kênh `ai_local` | lệnh chạy | chỉ nhận bản nháp (proposal), KHÔNG tự thực thi; chờ người xác nhận | BR-AI-06 |
| S02-AC3 (đề xuất→xác nhận) | NV kho `POST /api/commands/propose` `{command:"nhap_lo", args:…, reason:…}` | sau đó Chủ/NV kho có quyền bấm xác nhận trên UI | nhận `proposal_id` + `expires_at` (TTL 15 phút — PA G6); khi confirm thì dòng thực thi ghi actor `user` + note mã đề xuất; đề xuất ghi actor `ai:<user>` | BR-AI-08 (Q6), BR-AI-06 |
| S02-AC4 (lỗi schema) | args sai input schema (thiếu trường, sai kiểu) | gửi execute | nhận 400 kèm mã BR, không đổi dữ liệu, không ghi audit | BR-AI-01 |
| S02-AC5 (cấm kênh AI) | Chu đăng nhập, gửi `execute chot_lo channel:"ai_local"` | dù Chu có quyền close_batch | nhận 403 kèm mã BR-AI-07, không đổi trạng thái lô; UI vẫn chốt lô bình thường (channel `ui`) | BR-AI-07 |
| S02-AC6 (router chặn ngược) | gửi lệnh `tra_ton` (local) với `channel:"ai_cloud"` | hoặc `bao_cao_ton_kho` (cloud) với `channel:"ai_local"` | nhận 400/403 kèm mã BR-AI-02, không thực thi | BR-AI-02 |
| S02-AC7 (AI tắt) | `AI_ENABLED=false` | gọi execute/propose với channel `ai_local`/`ai_cloud` | nhận 410 `AI_DISABLED`; channel `ui` vẫn chạy bình thường | BR-AI-10 |
| S02-AC8 (quyền T3) | NV giao gửi `tra_don` cho đơn không được gán | — | nhận 403 hoặc kết quả rỗng theo scope dòng hiện có; không thấy đơn người khác | BR-AI-04, BR-PQ-12 |

Contract API (FE mock theo):
```
POST /api/commands/execute   {command, args, channel:"ui"|"ai_local"|"ai_cloud", proposal_id?}
  → 200 {result} | 400 {error, br_code} | 403 {error, br_code} | 410 {error:"AI_DISABLED"}
POST /api/commands/propose   {command, args, reason, channel:"ai_local"|"ai_cloud"}
  → 200 {proposal_id, expires_at}   (chỉ sinh bản nháp — không thực thi)
POST /api/commands/proposals/<id>/confirm  {channel:"ui"}
  → 200 {result} | 410 {error:"PROPOSAL_EXPIRED"} (quá TTL 15 phút) | 403 (người confirm thiếu quyền)
```
Ghi chú: quy tắc Tầng 2 = lệnh nào cần xác nhận do registry khai báo (field `needs_confirmation`);
kênh `ui` coi nút bấm của người là xác nhận; kênh AI bắt buộc đi qua propose→confirm (BR-AI-06).

## S03 — AuditLog actor `ai:<user>` (migration) · Must · BE
**Là** Chủ vựa, **tôi muốn** audit phân biệt được 3 loại actor `user` / `system` / `ai:<user>`, **để** truy vết
hành động nào do AI đề xuất, ai xác nhận, lúc nào — phục vụ giải trình (Luật AI) và gỡ lỗi.

Bối cảnh: BR-AI-08 (Q6); bất biến 3, 5, 8. Hiện trạng: `AuditLog.actor` là FK User (None = system).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S03-AC1 | model `accounts.AuditLog` sau migration | đọc schema | có field mở rộng để ghi được 3 loại actor (vd `actor_kind`: user/system/ai + `ai_actor` FK nullable + `proposal_ref` nullable); dòng cũ giữ nguyên giá trị | BR-AI-08, bất biến 8 |
| S03-AC2 | FE hiển thị nhật ký | đọc dòng đề xuất AI | hiện `ai:<tên user>` rõ ràng, kèm lệnh + thời điểm | BR-AI-08, BR-AI-14 |
| S03-AC3 (bất biến) | thử sửa/xoá dòng AuditLog cũ | gọi UPDATE/DELETE | bị chặn (append-only giữ nguyên); FK User vẫn PROTECT | bất biến 3, 5 |
| S03-AC4 (PII) | dòng audit của hành động đụng đơn hàng | đọc `detail` | chỉ chứa mã đơn/mã lệnh/mã đề xuất; không chép tên/SĐT/địa chỉ khách | BR-AI-09, bất biến 9 |
| S03-AC5 (quyền) | NV kho/NV giao đăng nhập | gọi API danh sách audit | nhận 403 hoặc chỉ thấy dòng liên quan scope của mình — không đọc toàn bộ nhật ký | BR-PQ-12 |

Ghi chú kỹ thuật: migration mới, field nullable — lý do đã ghi trong 01-analysis §4.4 (bất biến 8).
`record_audit()` hiện có mở tham số `actor_kind`/`ai_actor`/`proposal_ref` thay vì đổi chữ ký cũ.

## S04 — Trần chi phí cloud 200.000đ/tháng + AiUsageLedger + màn mức dùng · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** có trần chi phí cloud 200.000đ/tháng (cảnh báo 80%, chặn 100%) với sổ
mức dùng append-only xem được trên console, **để** không bao giờ lố ngân sách đã chốt (Q2).

Bối cảnh: UC-AI-06; BR-AI-11; Q2. Phụ thuộc S01 (catalog). Adapter không đụng DB — Django giữ điều phối (PA G5).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S04-AC1 | tháng chưa dùng gì, `AI_CLOUD_MONTHLY_BUDGET_VND=200000` | adapter báo mức dùng (qua internal API) | `AiUsageLedger` ghi dòng mới: lệnh, user, kênh, token in/out, chi phí ước tính VND, thời điểm | BR-AI-11 |
| S04-AC2 (chặn) | tổng chi tháng đạt 200.000đ | Django định gọi cloud | từ chối trước khi gọi adapter, trả 429 `BUDGET_EXCEEDED` + thông báo tiếng Việt "đã chạm trần chi phí tháng"; lệnh local vẫn chạy | BR-AI-11 |
| S04-AC3 (cảnh báo) | tổng chi đạt 160.000đ (80%) | gọi cloud | gọi vẫn chạy, `status=warning`; Chủ nhìn thấy cảnh báo trên màn mức dùng | BR-AI-11 |
| S04-AC4 (quyền) | Quản lý/NV kho đăng nhập | mở màn mức dùng | nhận 403 hoặc màn ẩn — chỉ Chủ (`chu`) xem được bảng mức dùng | BR-AI-11, BR-PQ-12 |
| S04-AC5 (append-only) | thử sửa/xoá dòng `AiUsageLedger` | gọi UPDATE/DELETE | bị chặn; số liệu tháng trước không đổi khi sang tháng mới (đếm lại từ 0 của tháng mới) | BR-AI-11 |
| S04-AC6 (AI tắt) | `AI_ENABLED=false` | mở console | màn mức dùng vẫn xem được (dữ liệu lịch sử); không có gọi cloud nào mới | BR-AI-10 |
| S04-AC7 (PII) | đọc bảng mức dùng | — | không có cột nội dung prompt; chỉ metadata (lệnh, user, token, chi phí) | BR-AI-09 |

Contract API:
```
GET /api/ai/usage?month=YYYY-MM          (chu)
  → {month, budget_vnd:200000, spent_vnd, pct, status:"ok"|"warning"|"blocked",
     rows:[{command, user, channel, input_tokens, output_tokens, cost_vnd, created_at}]}
Internal (adapter → Django, token nội bộ):
POST /internal/ai/usage  {user, command, channel:"ai_cloud", input_tokens, output_tokens, cost_vnd}
  → 200 | 401 (sai token)
```
Ghi chú: `AI_CLOUD_MONTHLY_BUDGET_VND`/`AI_CLOUD_ALERT_PCT=80` đọc từ settings/env (quy ước không hard-code).
Đơn giá token cấu hình được (`AI_CLOUD_PRICE_PER_1M_INPUT/OUTPUT`) để đổi nhà cung cấp không sửa code.

## S05 — Công tắc AI toàn cục `AI_ENABLED` + trạng thái AI cho FE · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** tắt AI toàn cục bằng một công tắc cấu hình, **để** khi AI trục trặc ERP vẫn
chạy 100% bằng thao tác tay — không màn hình nào phụ thuộc AI.

Bối cảnh: UC-AI-04; BR-AI-10. Tiền lệ dự án: `SEPAY_BANK_WEBHOOK_ENABLED` (tắt mà code/test giữ nguyên).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S05-AC1 | `AI_ENABLED=false` | FE mở console | mọi màn/menu AI (chat, nút mic, khối insights, nhãn AI) bị ẩn; các màn nghiệp vụ vẫn đầy đủ chức năng tay | BR-AI-10 |
| S05-AC2 | `AI_ENABLED=false` | gọi bất kỳ endpoint `/api/ai/*` hoặc kênh `ai_*` của lớp lệnh | nhận 410 `AI_DISABLED`; kênh `ui` không đổi | BR-AI-10 |
| S05-AC3 | `AI_ENABLED=true` | FE gọi `GET /api/ai/status` | nhận `{ai_enabled:true, cloud_enabled:bool, model:{name, source}, budget:{spent, limit}}`; FE dùng để bật màn AI | BR-AI-10 |
| S05-AC4 (quyền) | NV kho đăng nhập | đọc status | thấy `ai_enabled` và thông tin model — không cần quyền đặc biệt (không lộ dữ liệu nghiệp vụ); đổi công tắc chỉ qua env, không có API bật/tắt | BR-PQ-12 |
| S05-AC5 (lỗi) | FE không lấy được status (mạng lỗi) | mở console | mặc định coi AI tắt, không chặn màn nghiệp vụ | BR-AI-10 |

Contract API:
```
GET /api/ai/status → 200 {ai_enabled, cloud_enabled, model:{name, version, gguf_url},
                          budget:{spent_vnd, limit_vnd, status}}
```
Ghi chú: thêm công tắc riêng `AI_CLOUD_ENABLED` (mặc định tắt — tiền lệ SePay): chặn riêng kênh cloud
kể cả khi `AI_ENABLED=true`. Bật cloud production chỉ sau khi hợp đồng + hồ sơ phân loại hoàn tất (Q5, S11).

## S06 — Context builder lọc theo quyền (allowlist default-deny) · Must · BE
**Là** Quản lý, **tôi muốn** dữ liệu đưa vào prompt chỉ gồm đúng field được khai báo cho lệnh và theo
đúng quyền của tôi, **để** giá vốn và dữ liệu cá nhân khách không bao giờ xuất hiện trong prompt.

Bối cảnh: BR-AI-05/09; research checklist #1/#2. Phụ thuộc S01. Nguồn dữ liệu: serializer hiện có
(tái dùng đúng quy tắc ẩn field — không viết song song một bộ lọc khác).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S06-AC1 | NV kho gọi `POST /api/ai/context {command:"tra_ton", args_hint:{ma_hang:"CA-001"}}` | — | nhận context chỉ có field khai báo của `tra_ton` (tên hàng, tồn từng lô, hạn dùng); không field nào khác lọt vào | BR-AI-05 |
| S06-AC2 (giá vốn) | Quản lý (không `view_costprice`) hỏi `tra_lo` về lô cụ thể | kể cả hỏi trực tiếp "giá vốn lô này bao nhiêu" | context KHÔNG có `purchase_rate`/`landed_unit_cost`/lãi lỗ; Chủ thì có | BR-AI-05, bất biến 1 |
| S06-AC3 (PII) | user bất kỳ gọi context `tra_don` | với đơn có khách | context chỉ có mã đơn, ngày, trạng thái, tổng tiền — không tên/SĐT/địa chỉ | BR-AI-09, bất biến 9 |
| S06-AC4 (quyền T3) | NV giao gọi context `tra_don` cho phiếu không được gán | — | trả rỗng hoặc 403 — đúng scope dòng hiện có | BR-AI-04 |
| S06-AC5 (lỗi) | gọi context với lệnh không tồn tại/không active | — | nhận 400 kèm mã BR; không trả dữ liệu gì | BR-AI-01 |
| S06-AC6 (AI tắt) | `AI_ENABLED=false` | gọi context | 410 `AI_DISABLED` | BR-AI-10 |

Contract API:
```
POST /api/ai/context  {command, args_hint?}
  → 200 {context:{...}}  (allowlist theo lệnh; default-deny: field không khai báo bị loại)
  | 400 | 403 | 410
```
Ghi chú: allowlist field khai báo ngay trong registry (S01) — thêm 1 trường `context_fields` cho mỗi lệnh
tra cứu; không dùng denylist (research: allowlist mạnh hơn, không phụ thuộc nhận diện mẫu).

## S07 — Màn nhập lô qua lớp lệnh (thay placeholder purchasing) · Must · BE+FE
**Là** NV kho, **tôi muốn** tạo phiếu nhập lô ngay trên ERP console qua đúng lệnh `nhap_lo` của lớp
lệnh, **để** nhập liệu tại cảng không phụ thuộc Django Admin và sẵn sàng nhận voice (S10) — không làm
hai lần (BA §3.3).

Bối cảnh: UC-AI-01; S28; BR-MH-01/02, BR-MH-06. Phụ thuộc S01, S02. Dùng service `submit_receipt` hiện có — không viết ViewSet riêng.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S07-AC1 | NV kho có quyền `add_purchasereceipt` | mở màn Mua hàng, điền mặt hàng/kg/đơn giá/số lô/hạn dùng, bấm Lưu | phiếu nhập SUBMITTED qua lệnh `nhap_lo` (channel `ui`); lô sinh đúng BR-MH-01/02; AuditLog actor `user` | BR-AI-01, BR-MH-01/02 |
| S07-AC2 (lỗi) | thiếu trường bắt buộc (vd chưa chọn mặt hàng) | bấm Lưu | nhận 400 kèm mã BR + thông báo tiếng Việt; không tạo phiếu, không ghi audit | BR-AI-01 |
| S07-AC3 (quyền) | NV giao đăng nhập | mở màn Mua hàng / gọi lệnh `nhap_lo` | màn ẩn trong menu; gọi API nhận 403, không đổi dữ liệu | BR-AI-04, BR-PQ-12 |
| S07-AC4 (giá vốn) | user không có `view_costprice` | xem danh sách lô sau khi nhập | không thấy `purchase_rate`/`landed_unit_cost`; người nhập lô chỉ nhập đơn giá mua lúc tạo phiếu (quyền `add_purchasereceipt`), không thấy lãi lỗ | BR-MH-06, bất biến 1 |
| S07-AC5 (AI tắt) | `AI_ENABLED=false` | mở màn nhập lô | form nhập tay đầy đủ chức năng, không có ô/nút AI nào | BR-AI-10 |
| S07-AC6 (offline) | mất mạng lúc điền form | bấm Lưu | phiếu giữ nháp cục bộ (cơ chế `shared/lib/drafts.ts` hiện có), gửi lại khi có mạng, không mất dữ liệu đã gõ | PA G8 |

Contract API:
```
FE màn /purchasing: form phiếu nhập + danh sách dòng (mặt hàng, kg, đơn giá, số lô, hạn dùng)
  → POST /api/commands/execute {command:"nhap_lo", args:{supplier_id, lines:[{item_id, quantity, unit,
       purchase_rate, batch_no?, expiry_date?}]}, channel:"ui"}
Danh sách mặt hàng/nhà cung cấp: dùng API catalog hiện có (màn quản lý nhà cung cấp để sau — câu hỏi V2).
```
Ghi chú: màn này là "xe" cho voice (S10): form điền được bằng tay lẫn bằng args JSON của AI — cùng một
input schema. Không phát sinh model nghiệp vụ mới (bất biến 8).

---

# GIAI ĐOẠN 1 — MVP AI (voice nhập lô + chat tra cứu)

## S08 — Runtime on-device + tải model thông minh (wllama + GGUF) · Must · FE
**Là** NV kho, **tôi muốn** model AI chạy ngay trong trình duyệt (runtime wllama + GGUF) và chỉ tải về
khi tôi đồng ý trên Wi-Fi, **để** dùng voice/chat tại cảng kể cả mất mạng, không tốn 4G, không đẩy
lệnh local lên cloud ("local giả" bị cấm — BR-AI-16).

Bối cảnh: UC-AI-04; BR-AI-12/16/17; ADR 2.10/2.12; research 27/09 (LiteRT.js/WebLLM không hỗ trợ MiMo →
wllama). Model chốt theo Duy: **Gemma 3n (context 32k token)** — S17 chọn bản E2B/E4B theo RAM;
dự phòng Frog/SEA-LION, MiMo-7B chỉ nếu spike chứng minh chạy được. Dev/test dùng mock/LLMock (ADR 2.12).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S08-AC1 | máy có RAM/WebGPU đủ, Wi-Fi, model chưa tải | người dùng mở màn AI và bấm "Tải model" sau khi đọc thông báo dung lượng | tải GGUF Gemma 3n Q4 (~1,9–2,8GB tuỳ bản S17 chốt), cache IndexedDB, tải background không ảnh hưởng TTI < 2s | BR-AI-12 |
| S08-AC2 (4G) | đang dùng 4G/5G, chưa đồng ý tải | mở màn AI | KHÔNG tự tải model; nhắc đổi Wi-Fi hoặc "để sau"; lệnh local chuyển nhập tay, lệnh cloud vẫn chạy | BR-AI-12 |
| S08-AC3 (máy yếu) | máy không đủ RAM/WebGPU | mở màn AI | báo "máy này không chạy AI local" → nhập tay; KHÔNG đẩy lệnh local lên cloud thay thế | BR-AI-12, BR-AI-02 |
| S08-AC4 (chạy thật) | model đã tải | gửi prompt tiếng Việt đơn giản ("còn bao nhiêu cá thu") | wllama sinh câu trả lời on-device (WebGPU nếu có, CPU fallback); không có request nào đi ra ngoài trong lúc suy luận | BR-AI-16 |
| S08-AC5 (cache) | model đã tải, mở lại trình duyệt | dùng màn AI | không tải lại từ đầu — đọc IndexedDB; cache hỏng → tải lại có hỏi | BR-AI-12 |
| S08-AC6 (quyền) | không đăng nhập ERP | mở console | không thấy màn AI/menu AI nào (AI chỉ ERP nội bộ) | BR-AI-04 |
| S08-AC7 (AI tắt) | `AI_ENABLED=false` | mở console | không tải model, không chạy runtime; không ảnh hưởng màn nghiệp vụ | BR-AI-10 |
| S08-AC8 (PII) | dev/test | chạy runtime với LLMock | mọi prompt dùng dữ liệu giả; không ghi prompt vào log/console | BR-AI-09 |

Ghi chú kỹ thuật: module `erp-console/features/ai/runtime` — `@wllama/wllama` (GGUF trực tiếp,
CPU-WASM mọi trình duyệt + WebGPU); **runtime + suy luận chạy trong Web Worker** (không chặn main
thread — BR-AI-17) và **import động (lazy)** — người không mở AI không tải module/model; feature-detect `navigator.gpu`; `wllama-compat` cho Safari/iOS
(chỉ phép model ≤ ~1GB trên iPhone — research 5.3). Mock qua LLMock ở env dev/test; đường production
luôn trỏ runtime thật (BR-AI-16). Model URL/nguồn cấu hình được để S17 đổi model không sửa code.

## S09 — Chat tra cứu 3 lệnh local (tra_ton, tra_lo, tra_hang) · Must · BE+FE
**Là** Quản lý, **tôi muốn** hỏi đáp bằng tiếng Việt về tồn kho/lô/mặt hàng ngay trong ERP, **để** tra
cứu nhanh không cần mở từng màn, đúng quyền của tôi.

Bối cảnh: UC-AI-02; BR-AI-05/09/13/14. Phụ thuộc S01, S02, S06, S08. Router tĩnh: câu hỏi ánh xạ sang
lệnh local trong catalog — không dùng độ tự tin của model.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S09-AC1 | NV kho hỏi "còn bao nhiêu CA-001" | model local chọn `tra_ton` từ catalog, gọi execute channel `ai_local` | câu trả lời tiếng Việt kèm số tồn đúng; câu trả lời có nhãn "AI" | BR-AI-02, BR-AI-14 |
| S09-AC2 (giá vốn) | Quản lý (không `view_costprice`) hỏi "giá vốn lô B-01" | — | trả "không có quyền xem"; context đã không chứa field giá vốn (S06-AC2) | BR-AI-05 |
| S09-AC3 (PII) | hỏi "đơn SO-001 của ai" | — | trả lời chỉ dùng mã đơn/trạng thái, không có tên/SĐT/địa chỉ; log chỉ ghi mã lệnh | BR-AI-09 |
| S09-AC4 (tràn context) | hội thoại vượt `MAX_CONTEXT_TOKENS` (2048 mặc định) | gửi lượt mới | FE cắt giữ các lượt gần nhất, luôn giữ đệm 20% (không gửi quá 1638 token); không crash | BR-AI-13 |
| S09-AC5 (lỗi) | model không hiểu câu hỏi | — | hỏi lại bằng tiếng Việt tối đa 3 lần rồi gợi ý câu hỏi mẫu; không đoán bừa | UC-AI-02 |
| S09-AC6 (quyền) | NV giao hỏi đơn không được gán | — | trả "không có quyền xem đơn này" | BR-AI-04 |
| S09-AC7 (AI tắt) | `AI_ENABLED=false` | mở console | màn chat ẩn; mọi màn tra cứu tay vẫn dùng được | BR-AI-10 |

Contract API (FE dựng mock theo):
```
GET  /api/commands/catalog        (S01 — chọn lệnh local theo câu hỏi)
POST /api/ai/context {command, args_hint?}   (S06 — dữ liệu đã lọc cho prompt)
POST /api/commands/execute {command, args, channel:"ai_local"}   (S02 — kết quả thật từ server)
```
Ghi chú: FE giữ hội thoại ở bộ nhớ phiên, sliding window cắt phía FE (BR-AI-13); BE chỉ nhận từng lệnh —
không lưu trữ hội thoại. Chat chỉ tra cứu 3 lệnh local; lệnh cloud (bao_cao_*) thêm ở S13.

## S10 — Voice nhập lô: ASR on-device → model parse → form xác nhận · Must · BE+FE
**Là** NV kho, **tôi muốn** đọc thông tin lô bằng giọng ngay tại cảng rồi chỉ xác nhận trên màn hình,
**để** nhập lô rảnh tay trong lúc bốc hàng — chặn sai giá vốn ngay lúc nhập.

Bối cảnh: UC-AI-01 (entry point 1); BR-AI-15/16/06/14. Phụ thuộc S02, S07, S08. Audio chứa giá mua
(nhãn cao) → ASR on-device, KHÔNG dùng Web Speech API.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S10-AC1 | NV kho mở màn nhập lô (S07), model đã tải | bấm nút ghi âm, đọc "cá thu 50 ký, giá 80 ngàn, của cô Lan chợ Đà Nẵng" | ASR on-device nhận dạng; model local sinh args JSON đúng schema `nhap_lo` (mã hàng, kg, đơn giá, nhà cung cấp) | BR-AI-15, BR-AI-16 |
| S10-AC2 (xác nhận) | args AI đã điền vào form | bấm thực thi | form hiện nội dung AI điền kèm nhãn "do AI đề xuất"; chỉ sau khi người bấm xác nhận mới gọi confirm proposal → phiếu SUBMITTED; đề xuất ghi `ai:<user>`, thực thi ghi `user` + note mã đề xuất | BR-AI-06, BR-AI-08 (Q6), BR-AI-14 |
| S10-AC3 (thiếu trường) | lời nói thiếu trường (vd chưa nói giá) | — | AI hỏi lại bằng tiếng Việt tối đa 3 lần rồi chuyển form tay, giữ phần đã điền | UC-AI-01 |
| S10-AC4 (PII/âm thanh) | bấm ghi âm, tắt mạng | — | nhận dạng vẫn chạy (on-device); không byte audio nào gửi lên server/cloud trong mọi trường hợp | BR-AI-15, BR-AI-09 |
| S10-AC5 (4G) | model chưa tải, đang 4G | bấm ghi âm | không tải model; báo nhập tay (form S07 vẫn dùng được) | BR-AI-12 |
| S10-AC6 (quyền) | người xác nhận không có quyền `add_purchasereceipt` (vd NV giao) | bấm xác nhận | 403, không tạo phiếu | BR-AI-04 |
| S10-AC7 (AI tắt) | `AI_ENABLED=false` | mở màn nhập lô | nút ghi âm ẩn; nhập tay 100% | BR-AI-10 |
| S10-AC8 (máy yếu) | máy không đủ RAM/WebGPU | bấm ghi âm | báo "máy này không chạy AI local", nhập tay; không đẩy lên cloud | BR-AI-12, BR-AI-02 |

Contract API: dùng lại S02 (`propose` → `proposals/<id>/confirm`) + S07 (form). BE bổ sung nhỏ: kiểm
tra args `nhap_lo` sinh từ AI đi qua đúng luồng propose (không có execute trực tiếp channel `ai_*` cho
lệnh Tầng 2 — đã ở S02-AC2).

## S17 — Spike on-device trên máy thật (50 câu thật, chốt model) · Must (chờ Q4) · Spike
> ĐÁNH DẤU RIÊNG — phụ thuộc Q4 (Duy giao máy tham chiếu). KHÔNG chặn story nào khác; code S08/S10
> vẫn viết bằng mock/LLMock, model cấu hình được để đổi sau spike.

**Là** Chủ vựa (Duy), **tôi muốn** kiểm chứng model on-device bằng 50 câu nói thật trên máy của nhân
viên, **để** chốt model chạy được on-device thật đúng BR-AI-16 trước khi cam kết voice.

Bối cảnh: ADR 5.1; BR-AI-16; research 02 §5; Duy chốt model **Gemma 3n 32k** (dự phòng Frog/SEA-LION,
MiMo-7B chỉ nếu spike chứng minh). Toàn bộ dùng dữ liệu giả (Q3 chưa chốt — checklist #9).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S17-AC1 | máy tham chiếu (Q4), bộ 50 câu nói thật bằng dữ liệu giả | chạy Gemma 3n (E2B rồi E4B tuỳ RAM) trên wllama | đo tỉ lệ đúng field (`ma_hang`, `so_luong`, `don_vi`, đơn giá) ≥ ngưỡng Duy chốt (câu hỏi V1); kết quả ghi bảng vào hồ sơ feature | BR-AI-16 |
| S17-AC2 | cùng máy | đo độ trễ giọng→JSON, RAM đỉnh, context 2K/32K (native Gemma 3n), có crash tab không | ghi số cụ thể; máy không đủ RAM → kết luận "không chạy local" chứ không chấp nhận đẩy cloud | BR-AI-16, BR-AI-12 |
| S17-AC3 | MiMo-7B (chỉ nếu thời gian cho phép) | thử nạp GGUF Qwenified qua wllama | nếu không nạp được hoặc tiếng Việt kém → loại khỏi danh sách, giữ Gemma 3n (chốt Duy) | BR-AI-16 |
| S17-AC4 | kết thúc spike | — | chốt 1 model chính thức cho S08/S10; Duy ghi quyết định vào `decisions.md`; cập nhật `02-stories.md` (nghiệm thu) | ADR 5.3 |
| S17-AC5 (PII) | toàn bộ spike | — | không dùng dữ liệu vận hành thật; không ghi âm giọng người thật vào repo/doc | bất biến 9, Q3 |

Ghi chú: nếu Duy chốt Q4 trễ mà S08/S10 đã xong — chỉ đổi cấu hình model (URL GGUF + prompt few-shot),
không sửa kiến trúc (ADR 2.4: router không phụ thuộc model).

---

# GIAI ĐOẠN 2 — Mở rộng entry point + cloud

## S11 — Adapter proxy MiMo cloud + chốt chặn kỹ thuật (allowlist + redaction + hard-block) · Must · BE
**Là** Chủ vựa, **tôi muốn** mọi prompt gửi lên cloud MiMo-V2.6-Flash phải đi qua adapter với chốt chặn
kỹ thuật (allowlist + che PII + chặn cứng), **để** dữ liệu cá nhân khách không bao giờ rời máy chủ —
kể cả khi code phía gọi có lỗi.

Bối cảnh: Q5 + BR-AI-03/09/11; research C/4 (Presidio/redaction, hard-block); decisions 2026-09-09
(bên thứ 3 đi qua adapter). Phụ thuộc S04, S05. Lệnh `cao` được lên cloud theo Q5 — nhưng vẫn qua
allowlist và không bao giờ kèm PII.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S11-AC1 | lệnh `bao_cao_ton_kho` (cloud/thấp), `AI_CLOUD_ENABLED=true` | Django gọi cloud qua adapter | prompt gửi tới MiMo chỉ gồm field cho phép của lệnh; adapter trả văn bản + token usage; Django ghi ledger (S04) | BR-AI-03, BR-AI-11 |
| S11-AC2 (PII chặn cứng) | prompt chứa SĐT giả "09xx xxx 123" hoặc tên/địa chỉ khách (test) | gửi qua adapter | adapter chặn cứng (422), KHÔNG một byte nào ra khỏi adapter; ghi log chỉ có mã lệnh | BR-AI-09 |
| S11-AC3 (allowlist) | prompt chứa field ngoài allowlist của lệnh (vd field giá vốn trong lệnh `thấp`) | — | field đó bị loại trước khi gửi; không phụ thuộc nhận diện mẫu | BR-AI-05, OWASP LLM06 |
| S11-AC4 (cao theo Q5) | lệnh `bao_cao_lo` (cloud/cao) — user là Chu | gọi cloud | được phép gửi số liệu gộp đã lọc (không PII); mọi field vẫn qua allowlist | BR-AI-03 (Q5) |
| S11-AC5 (trần) | tổng chi tháng đã chạm 200.000đ | gọi cloud | Django từ chối trước khi gọi adapter, trả 429 `BUDGET_EXCEEDED` | BR-AI-11 |
| S11-AC6 (công tắc) | `AI_CLOUD_ENABLED=false` | gọi cloud | trả 410 `CLOUD_DISABLED`; lệnh local không đổi. **Bật production chỉ khi** hợp đồng không-huấn-luyện + zero retention + hồ sơ phân loại + thông báo Bộ KH&CN hoàn tất (Q5 — việc vận hành, không phải code) | BR-AI-10, Q5 |
| S11-AC7 (adapter mỏng) | — | kiểm tra adapter | adapter vẫn không đụng DB; chỉ proxy + chặn + đo token; `MIMO_API_KEY` lấy từ Secret Manager | decisions 2026-09-09 |
| S11-AC8 (quyền) | NV giao gọi cloud với lệnh `bao_cao_ton_kho` (quyền tối thiểu `quan_ly`) | — | nhận 403 trước khi gọi adapter; không tốn chi phí cloud | BR-AI-04 |
| S11-AC9 (AI tắt) | `AI_ENABLED=false` | gọi cloud | 410 `AI_DISABLED` trước cả kiểm trần | BR-AI-10 |

Contract API:
```
Django:  POST /api/ai/cloud/complete {command, prompt}
  → 200 {text, usage:{input_tokens, output_tokens}} | 410 | 422 | 429
Adapter: POST /ai/v1/chat/completions (OpenAI-compatible) → proxy api.xiaomimimo.com/v1
  — trước khi forward: allowlist theo lệnh → redaction PII (SĐT 10 số VN, pattern tên/địa chỉ) →
    hard-block nếu vẫn còn PII (422) → forward; response đo token trả về Django.
```
Ghi chú: nghiệp vụ "hợp đồng + hồ sơ phân loại + thông báo Bộ KH&CN" là việc của Duy/Lộc trước khi
bật `AI_CLOUD_ENABLED` ở production — story này chỉ code, không thay nghĩa vụ đó.

## S12 — Proactive Alerts: lô cận hạn, đơn chờ, phiếu hoàn chờ · Should · BE+FE
**Là** Quản lý, **tôi muốn** hệ thống chủ động cảnh báo lô cận hạn/đơn chờ thanh toán/phiếu hoàn chờ
theo đúng quyền, **để** xử lý kịp trước khi hỏng hàng hoặc quá hạn.

Bối cảnh: entry point 4; nền sẵn có: job `update_batch_status`, dashboard summary. Phụ thuộc S01.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S12-AC1 | có lô cận hạn ≤ ngưỡng cấu hình (`ALERT_BATCH_EXPIRY_DAYS`) | mở trung tâm thông báo | thấy cảnh báo kèm mã lô, mặt hàng, số ngày còn lại, tồn | BR-LO-*, tham số env |
| S12-AC2 (quyền) | NV giao đăng nhập | mở thông báo | chỉ thấy cảnh báo liên quan phiếu được gán; không thấy lô/đơn ngoài scope | BR-AI-04, BR-PQ-12 |
| S12-AC3 (PII) | cảnh báo về đơn chờ | — | nội dung chỉ mã đơn/trạng thái/giá trị; không tên/SĐT/địa chỉ khách | BR-AI-09 |
| S12-AC4 (AI tắt) | `AI_ENABLED=false` | mở thông báo | danh sách cảnh báo vẫn đầy đủ (dạng thô); chỉ phần "tóm tắt ngôn ngữ tự nhiên" ẩn | BR-AI-10 |
| S12-AC5 (lỗi) | không có cảnh báo nào | mở thông báo | hiện "không có cảnh báo", không lỗi | — |

Contract API:
```
GET /api/ai/alerts → 200 {alerts:[{type:"batch_expiry|order_pending|refund_pending", id, ref_code,
  message, created_at}]}  (lọc theo quyền T3; không PII)
```
Ghi chú: luật cảnh báo đọc từ settings (không hard-code); tóm tắt NLG thêm ở S13 (dùng endpoint cloud S11).

## S13 — Dashboard Insights: tóm tắt Tổng quan qua cloud (lệnh thấp) · Should · BE+FE
**Là** Chủ vựa, **tôi muốn** màn Tổng quan có đoạn tóm tắt tiếng Việt từ số liệu gộp đã lọc, **để** nắm
tình hình trong 30 giây mỗi sáng.

Bối cảnh: UC-AI-05; entry point 8. Phụ thuộc S11. Dữ liệu gộp, nhãn thấp, không PII, không giá vốn
(trừ khi user có quyền và lệnh đúng nhãn).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S13-AC1 | Chu mở Tổng quan, cloud bật | hệ thống gọi `bao_cao_ton_kho` qua cloud với dữ liệu gộp | hiện đoạn tóm tắt tiếng Việt kèm nhãn "AI"; ledger tăng đúng mức dùng | BR-AI-03, BR-AI-14 |
| S13-AC2 (lỗi) | cloud lỗi/timeout | mở Tổng quan | hiện số liệu thô như cũ, không chặn màn | UC-AI-05 |
| S13-AC3 (trần) | đã chạm trần 200.000đ | mở Tổng quan | báo "đã chạm trần chi phí tháng", vẫn hiện số liệu thô | BR-AI-11 |
| S13-AC4 (giá vốn) | Quản lý (không `view_profitreport`) | xem insights | prompt/trả lời không chứa giá vốn/lãi lỗ; Chu xem báo cáo lãi lỗ qua lệnh riêng (S11-AC4) | BR-AI-05, bất biến 1 |
| S13-AC5 (quyền) | NV giao (không có `view_dashboard`) | mở Tổng quan | không thấy khối tóm tắt AI | BR-AI-04, BR-PQ-12 |
| S13-AC6 (AI tắt) | `AI_ENABLED=false` | mở Tổng quan | khối tóm tắt ẩn; số liệu thô đầy đủ | BR-AI-10 |

Contract API: dùng lại `POST /api/ai/cloud/complete {command:"bao_cao_ton_kho", prompt}` (S11);
FE chỉ thêm khối hiển thị + nhãn AI trên màn Tổng quan.

## S14 — Inline Suggestions + Auto-fill (gợi ý mã hàng, điền form từ AI) · Should · BE+FE
**Là** NV kho, **tôi muốn** gõ vài chữ là có gợi ý mặt hàng và form tự điền từ kết quả AI, **để** nhập
liệu ít gõ, ít sai mã.

Bối cảnh: entry point 2+3. Gợi ý mã hàng dùng search API là đủ (LLM tuỳ chọn); auto-fill validate args
theo input schema từng lệnh (S01). Phụ thuộc S01, S07.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S14-AC1 | gõ "cá thu" vào ô mặt hàng form nhập lô | — | gợi ý ≤ 10 mặt hàng khớp tên (search API); chọn 1 cái → điền mã hàng vào form | — |
| S14-AC2 (PII) | — | gợi ý bất kỳ | chỉ trả Item/Supplier (mã + tên hàng); không bao giờ có dữ liệu khách | BR-AI-09 |
| S14-AC3 (auto-fill) | có args JSON từ voice (S10) hoặc đề xuất AI | chọn "điền vào form" | form điền đúng field theo input schema lệnh; field sai kiểu không điền và báo rõ | BR-AI-01 |
| S14-AC4 (quyền) | NV giao (không có `view_item`) | gọi `items/suggest` | nhận rỗng hoặc 403 — không lộ danh mục | BR-AI-04 |
| S14-AC5 (lỗi) | gõ chuỗi không khớp mặt hàng nào | — | hiện "không tìm thấy", không đề xuất bừa | — |
| S14-AC6 (AI tắt) | `AI_ENABLED=false` | gõ ô mặt hàng | gợi ý bằng tìm kiếm thường vẫn dùng được (không nhãn AI); phần gợi ý LLM ẩn | BR-AI-10 |

Contract API:
```
GET /api/catalog/items/suggest?q=… → 200 {items:[{id, code, name}]}   (search, không PII)
```
Ghi chú: gợi ý LLM (khi bật cloud) dùng endpoint S11 — không bắt buộc cho MVP; search API là đủ.

## S15 — Smart Buttons FEFO: nút "điền theo FEFO" khi xuất kho · Should · BE+FE
**Là** Quản lý, **tôi muốn** nút "điền theo FEFO" gợi ý đúng lô xuất trước trên form soạn hàng, **để**
không bao giờ chọn nhầm lô cũ — lô vẫn chốt một lần lúc tạo đơn như quy định.

Bối cảnh: entry point 7; BR-BH-05/11. KHÔNG cần LLM — chỉ gọi service `allocate_fefo`/`sellable_batches`
hiện có. Phụ thuộc màn soạn hàng (story S17 của hồ sơ khác — phối hợp thứ tự, không chặn AI Native).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S15-AC1 | form soạn hàng có các dòng đã chọn | bấm "điền theo FEFO" | gợi ý lô theo FEFO (hạn sớm nhất → nhập trước → tạo trước) từ `sellable_batches` | BR-BH-05, bất biến 6 |
| S15-AC2 (chốt một lần) | đơn đã tạo | thay đổi lô | hệ thống không chọn lại lô; gợi ý chỉ áp cho đơn mới | BR-BH-05/11 |
| S15-AC3 (không chọn tay) | user cố sửa lô tay ngoài FEFO | — | không có ô chọn lô tự do; mọi thay đổi qua service gợi ý | BR-BH-05, BR-PQ-12 |
| S15-AC4 (quyền) | NV giao không có quyền soạn hàng | mở form soạn | nút FEFO ẩn hoặc gọi API nhận 403 | BR-AI-04 |
| S15-AC5 (lỗi) | không còn lô bán được của mặt hàng | bấm "điền theo FEFO" | báo "không còn lô bán được", không điền gì | BR-BH-05 |
| S15-AC6 (AI tắt) | `AI_ENABLED=false` | bấm nút FEFO | nút vẫn hoạt động (không phụ thuộc model — ví dụ "hệ thống chạy 100%" khi tắt AI) | BR-AI-10 |

Ghi chú: nút chỉ gọi service hiện có, không đi qua LLM — giữ nguyên nguồn duy nhất `sellable_batches`
(bất biến 6). Không cần contract mới ngoài endpoint gợi ý đã có; nếu chưa có endpoint thì thêm
`POST /api/commands/execute {command:"goi_y_fefo", channel:"ui"}` (lệnh mới đề xuất, nhãn local/thấp).

## S16 — Summarization hội thoại dài · Could · FE
**Là** Quản lý, **tôi muốn** hội thoại dài được tóm tắt tự động thay vì cắt cụt, **để** hỏi tiếp không
mất ngữ cảnh cũ khi vượt ngưỡng context.

Bối cảnh: ADR 2.9 tầng 2 ("nên có"); BR-AI-13. Phụ thuộc S09.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S16-AC1 | hội thoại vượt `MAX_CONTEXT_TOKENS` (2048/4096) | gửi lượt mới | các lượt cũ được gộp thành 1 tóm tắt thay vì cắt thô; vẫn giữ đệm 20% | BR-AI-13 |
| S16-AC2 (quyền/PII) | hội thoại chứa nội dung tra cứu | tóm tắt | bản tóm tắt chỉ gồm nội dung các lượt user có quyền; không thêm field mới, không có PII | BR-AI-05, BR-AI-09 |
| S16-AC3 (on-device) | chạy tóm tắt | — | tóm tắt bằng model local (không gửi hội thoại lên cloud) | BR-AI-03 |
| S16-AC4 (lỗi) | tóm tắt thất bại | gửi lượt mới | fallback về cắt thô sliding window như S09, không crash, không mất lượt mới nhất | BR-AI-13 |
| S16-AC5 (AI tắt) | `AI_ENABLED=false` | — | màn chat ẩn (S09-AC7) nên không áp dụng; không màn nào phụ thuộc tóm tắt | BR-AI-10 |

Ghi chú: làm sau cùng, chỉ khi chat (S09) đã ổn định; không chặn gì.

---

# Tổng kết — bảng story, thứ tự làm, lô đề xuất

## Bảng tổng story

| Mã | Tiêu đề | GĐ | MoSCoW | BE/FE | Phụ thuộc |
|---|---|---|---|---|---|
| S01 | Danh mục lệnh + catalog theo quyền | 0 | Must | BE | — |
| S02 | Kênh thực thi & đề xuất lệnh (execute/propose/confirm) | 0 | Must | BE | S01, S03 |
| S03 | AuditLog actor `ai:<user>` (migration) | 0 | Must | BE | — |
| S04 | Trần chi phí 200.000đ/tháng + AiUsageLedger + màn mức dùng | 0 | Must | BE+FE | S01 |
| S05 | Công tắc `AI_ENABLED` + trạng thái AI | 0 | Must | BE+FE | — |
| S06 | Context builder lọc quyền (allowlist) | 0 | Must | BE | S01 |
| S07 | Màn nhập lô qua lớp lệnh (thay placeholder) | 0 | Must | BE+FE | S01, S02 |
| S08 | Runtime on-device + tải model thông minh (wllama+GGUF) | 1 | Must | FE | — (mock) |
| S09 | Chat tra cứu 3 lệnh local | 1 | Must | BE+FE | S01, S02, S06, S08 |
| S10 | Voice nhập lô (ASR on-device → form xác nhận) | 1 | Must | BE+FE | S02, S07, S08 |
| S11 | Adapter proxy MiMo cloud + chốt chặn kỹ thuật | 2 | Must | BE | S04, S05 |
| S12 | Proactive Alerts (cận hạn, đơn chờ, hoàn chờ) | 2 | Should | BE+FE | S01 |
| S13 | Dashboard Insights qua cloud | 2 | Should | BE+FE | S11 |
| S14 | Inline Suggestions + Auto-fill | 2 | Should | BE+FE | S01, S07 |
| S15 | Smart Buttons FEFO | 2 | Should | BE+FE | màn soạn hàng (hồ sơ khác) |
| S16 | Summarization hội thoại dài | 2 | Could | FE | S09 |
| S17 | Spike on-device 50 câu thật (chốt model) | 1 | Must ⏳ Q4 | Spike | máy tham chiếu (Q4) |

Lý do MoSCoW một dòng: Must = nền tảng + chốt của Duy (local bắt buộc, trần chi phí, chốt chặn PII,
tắt AI 100%, 2 entry point MVP); Should = giá trị vận hành giai đoạn 2, không chặn MVP; Could = tối ưu
hội thoại; Won't (ngoài file này) = image input, semantic search, RAG, agent actions, Shop AI, Admin AI.

## Thứ tự làm đề xuất + lô (1–3 story/lô, BE ∥ FE song song)

| Lô | Story | Vì sao lô này |
|---|---|---|
| **Lô 1** | S01 (BE) ∥ S03 (BE) ∥ S08 (FE) | Nền registry + audit; FE làm runtime bằng mock ngay — không phụ thuộc BE |
| **Lô 2** | S02 (BE) ∥ S05 (BE+FE) ∥ S06 (BE) | S02 sau S01+S03; công tắc + context độc lập nhau |
| **Lô 3** | S07 (BE+FE) ∥ S04 (BE+FE) | Màn nhập lô trên kênh lệnh đã sẵn; trần chi phí chuẩn bị cho cloud |
| **Lô 4** | S09 (BE+FE) ∥ S10 (BE+FE) | MVP AI: chat + voice — S10 cần S07+S08, S09 cần S06 |
| **Lô 5** | S11 (BE) ∥ S14 (BE+FE) ∥ S15 (BE+FE) | Mở cloud + 2 entry point không cần LLM (search/FEFO) song song |
| **Lô 6** | S12 (BE+FE) ∥ S13 (BE+FE) | Cảnh báo + insights (S13 cần S11) |
| **Lô 7** | S16 (FE) | Tối ưu sau khi chat ổn định |
| **Riêng** | S17 (spike) | Khi Duy giao máy (Q4); kết quả đổi model S08/S10 bằng cấu hình, không sửa kiến trúc |

Nguyên tắc: mỗi lô QA APPROVED → commit + push (quy ước 2026-09-25). Giai đoạn 0 xong mới "đóng băng"
BR-AI-01…16 và vào Giai đoạn 1 (BA §10).

## Rủi ro / phụ thuộc

1. **S08/S10 phụ thuộc spike S17 để chốt model** — đã giảm thiểu: runtime wllama độc lập model; Gemma 3n
   32k là mặc định (chốt Duy khi duyệt story); dev dùng LLMock; nếu spike đổi model chỉ đổi cấu hình.
2. **MiMo-7B chưa chạy được trên web runtime** — không dùng MiMo cho tới khi S17-AC3 chứng minh; không
   coi đây là việc "có sẵn" (BR-AI-16).
3. **Q3 chưa chốt** — mọi test/spike/doc dùng dữ liệu giả (DoD 6); không dùng dữ liệu vận hành thật.
4. **Bật cloud production chờ việc vận hành** (hợp đồng không-huấn-luyện + zero retention + hồ sơ phân
   loại + thông báo Bộ KH&CN) — code S11 làm trước, công tắc `AI_CLOUD_ENABLED` mặc định tắt (Q5).
5. **S15 phụ thuộc màn soạn hàng (story khác)** — không chặn AI Native; làm khi màn soạn hàng có.
6. **Việc ngoài code của Duy** (ADR 5.3): `decisions.md`, `URD.md`, `doctype-mapping.md` — không thuộc story này.
7. **Hiệu năng website không được đánh đổi** (chốt Duy khi duyệt story) — BR-AI-17: AI code lazy-load,
   runtime + suy luận trong Web Worker, TTI < 2s, AI tắt = y hệt cũ; QA đo perf mỗi lô có FE.

## Câu hỏi cho Duy (🟡 — không chặn việc code)

| # | Câu hỏi | Đề xuất của PO |
|---|---|---|
| V1 | Ngưỡng chấp nhận của spike S17: tỉ lệ đúng field trên 50 câu thật bao nhiêu thì chốt model? | ≥ 80% đúng field `ma_hang`/`so_luong`/`don_vi`/đơn giá; dưới 80% → thử bản còn lại (E2B/E4B) rồi dự phòng Frog/SEA-LION/Sailor2-1B |
| V2 | Màn nhập lô (S07): có gộp luôn màn quản lý nhà cung cấp + PurchaseCost + StockEntry không? | Không gộp — S07 chỉ phiếu nhập + dòng (chọn nhà cung cấp từ dropdown API hiện có); 3 màn kia làm story sau (hoặc gộp vào S28 của hồ sơ purchasing) |
| V3 | Endpoint lớp lệnh dùng chung đặt tại `/api/commands/*` (không phải `/api/ai/*`) để Admin/UI/AI dùng chung một cổng — Duy duyệt? | Đồng ý đặt `/api/commands/*`; phần riêng AI (`status`, `context`, `usage`) ở `/api/ai/*` |
| V4 | Registry lệnh bằng code + env (chưa cần bảng DB — PA G4), Duy duyệt? | Code registry; khi nào cần bật/tắt từng lệnh riêng thì nâng lên bảng cấu hình |
| V5 | Khung xác nhận Tầng 2 (BR-AI-14 "buộc tương tác thật"): dùng cách nào? | Nút "Đồng ý thực thi" chỉ bật sau khi mở xem chi tiết bản nháp + đếm ngược 3 giây; log thời điểm xác nhận vào audit |

---

*Hồ sơ đầy đủ: 00-adr-ai-native.md · 01-analysis.md · 05-deep-research.md · 02-stories.md (file này).*



