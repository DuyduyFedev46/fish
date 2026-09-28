# AI Native ERP — Phân tích nghiệp vụ
> BA · 2026-09-27 · Trạng thái: **ĐÃ DUYỆT** (Duy trả lời Q1–Q6 ngày 2026-09-27 — xem mục "Câu trả lời của Duy")

## Tóm tắt

**Nhân viên/Chủ vựa** cần ERP **nói được, gợi ý được, cảnh báo được** để **nhập liệu nhanh
tại cảng, giảm nút cổ chai khi Lộc vắng mặt, và chặn sai giá vốn ngay lúc nhập** — theo ADR
AI Native đã chốt (`00-adr-ai-native.md`, Duy + PA, 2026-09-27): hybrid Gemma 3n on-device (32k,
chốt Duy khi duyệt story) + MiMo-V2.6-Flash cloud, đi qua **một lớp lệnh nghiệp vụ dùng chung** cho UI/Admin/AI, phân
quyền đúng bằng quyền người đăng nhập, AuditLog actor `ai:<user>`, 10 entry point, tắt được
toàn bộ, có trần chi phí.

Điểm mấu chốt của bản phân tích:
- Hiện trạng backend đã có **service layer phân quyền 3 tầng + AuditLog rất gần** với ADR —
  thiếu: danh mục lệnh có schema + nhãn, kênh actor `ai:<user>`, router theo nhãn, lọc context
  cho prompt, trần chi phí. Không phải viết lại lõi, là **bọc + mở rộng**.
- **Xung đột phải Duy quyết**: ADR có ví dụ `negotiate_price` nhãn cloud+cao, trong khi rò giá
  vốn là rủi ro cao nhất dự án — cần chốt lệnh `cao` có được lên cloud không (🔴 Q5).
- **ERP đang thiếu màn nhập liệu** (mua hàng, kiểm kê, giao hàng, báo cáo) so với Django Admin —
  đề xuất xử lý **song song** với AI Native, và màn nhập lô (S28) chính là "xe" chở entry point
  số 1 (voice nhập lô). Không làm màn nhập lô trước theo lối cũ vì ADR bắt mọi entry point qua
  lớp lệnh — làm hai lần thì đắt.
- 4 câu hỏi mở ADR 5.4 (dữ liệu gửi Xiaomi, trần chi phí ai trả, thoả thuận với Lộc, máy
  spike) đều là 🔴 chặn — không trả lời thì không làm được phần cloud/on-device.

## Câu trả lời của Duy (2026-09-27) — quyết định đã chốt

| # | Trả lời của Duy | Hệ quả áp vào bản phân tích |
|---|---|---|
| Q1 | **"Local AI là bắt buộc — model không chạy được on-device thì phải đi tìm model khác."** | **Rule mới BR-AI-16 (Local-first bắt buộc):** mọi lệnh `local` phải có đường chạy on-device thật. Research 27/09: MiMo-7B CHƯA chạy được trên web runtime (LiteRT.js/WebLLM không hỗ trợ) → spike **wllama + GGUF**. **Duy chốt khi duyệt story: model on-device là Gemma 3n (context 32k token)** — S17 chọn bản E2B/E4B theo RAM máy tham chiếu; dự phòng Frog/SEA-LION/Sailor nếu Gemma 3n không chạy được on-device; MiMo-7B chỉ giữ làm ứng viên nếu spike chứng minh chạy được + tiếng Việt ổn. Cloud Xiaomi vẫn dùng theo Q2/Q5. |
| Q2 | **Trần chi phí: 100.000–200.000đ/tháng.** (Ai trả chưa chốt — gộp chờ cùng Q3.) | `AI_CLOUD_MONTHLY_BUDGET_VND = 200000` (cận trên), cảnh báo 80%, chặn 100% (BR-AI-11). Chỉ đủ ~2–4.000 câu cloud/tháng → PO ưu tiên lệnh local, lệnh cloud phải tiết kiệm. |
| Q3 | ⏳ *chưa trả lời — chờ Duy* | Không chặn viết story; chặn việc dùng dữ liệu vận hành cho bất kỳ việc gì ngoài chạy ERP (giữ nguyên cảnh báo). |
| Q4 | **Android ≥ 8GB RAM, Windows ≥ 8GB RAM; iPhone tạm chưa hỗ trợ (Duy, 27/09).** | Spike on-device chạy trên máy thật 8GB; S17 chọn E2B/E4B theo kết quả đo. Code vẫn viết bằng mock/LLMock cho tới khi spike chạy được. |
| Q5 | **Cho phép lệnh nhãn `cao` chạy qua cloud ngay.** | BR-AI-03 sửa: `cao` được lên cloud (bỏ mặc định local-only); 3 lệnh cấm-kênh-AI (BR-AI-07) không đổi. **Nghĩa vụ kèm theo:** trước khi bật cloud ở production phải có hợp đồng cam kết không-huấn-luyện + zero retention với nhà cung cấp API và ghi vào hồ sơ phân loại rủi ro (thiếu thì mất bảo hộ bí mật kinh doanh — Luật SHTT Đ.84). **PII khách vẫn cấm tuyệt đối vào prompt (BR-AI-09 không đổi).** |
| Q6 | **Đề xuất ghi `ai:<user>`, thực thi sau xác nhận ghi `user` + note mã đề xuất.** | BR-AI-08 sửa theo ngữ nghĩa này. |

**Bổ sung từ research (`05-deep-research.md`):**
- Runtime on-device: **wllama + GGUF** (bỏ LiteRT.js/WebLLM cho MiMo — chưa hỗ trợ).
- Nghĩa vụ pháp lý mới trước khi bật AI production: hồ sơ phân loại rủi ro (trung bình) + **thông báo Bộ KH&CN qua cổng một cửa AI** (Luật AI 134/2025, NĐ 142/2026 Đ.12/14 — hệ thống mới không có chuyển tiếp 12 tháng).
- PII vào prompt cloud = chuyển dữ liệu xuyên biên giới (Luật BVDLCN 91/2025 Đ.20, phạt tới 5% doanh thu) → giữ tuyệt đối BR-AI-09 + **chốt chặn kỹ thuật ở adapter** (allowlist + redaction + hard-block).
- **Chốt khi Duy duyệt story (27/09):** model on-device **Gemma 3n (32k)** — ADR điểm 9; **hiệu năng không đánh đổi** — website phải chạy mượt dù có AI Native (rule mới BR-AI-17, ADR điểm 10).

## Câu hỏi 🔴 chặn — đã trả lời (xem mục trên)

Q1 Local AI bắt buộc → BR-AI-16 · Q2 trần 200k/tháng · Q3 ⏳ chưa trả lời (thoả thuận với Lộc) ·
Q4 ✓ Android/Windows ≥ 8GB RAM, iPhone tạm chưa hỗ trợ · Q5 cloud+cao cho phép (kèm nghĩa vụ hợp đồng + hồ sơ) ·
Q6 đề xuất `ai:<user>`, thực thi `user` + note mã đề xuất.

## 1. Yêu cầu gốc

"ERP của chúng ta mang tính AI Native" (Duy, PO, 2026-09-27) — nâng cấp ERP theo ADR đã chốt
`doc/features/2026-09-27-ai-native-erp/00-adr-ai-native.md` (Duy dán nguyên văn, quyết định của
Duy + PA). ADR gồm 12 quyết định: model on-device MiMo-7B, model cloud MiMo-V2.6-Flash, kiến
trúc hybrid, router tĩnh theo nhãn, lớp lệnh nghiệp vụ dùng chung, phân quyền 3 tầng cho AI,
AuditLog `ai:<user>`, 10 entry point, chống tràn context, tải model thông minh, tuân thủ pháp
lý, dev không cần máy mạnh.

## 2. Định vị trong hệ thống

- **Quy trình bị ảnh hưởng:** P-01…P-10 — AI Native không tạo quy trình mới mà là **kênh thao
  tác thứ ba** (bên cạnh ERP console và Django Admin) cho mọi quy trình hiện có. Nặng nhất ở
  P-02 (nhập lô — voice entry point ưu tiên 1), P-04 (cảnh báo cận hạn), P-10 (báo cáo/insights).
- **Rule hiện có liên quan chặt:**
  - BR-PQ-12: phân quyền nằm ở API/queryset/serializer, không ở giao diện — áp y nguyên cho kênh
    AI: **không tin model/thiết bị**, lớp lệnh phía server kiểm lại quyền.
  - BR-PQ-13 (spec): mỗi Group phải có test gọi API bằng token đúng Group. ADR dẫn BR-PQ-13 với
    nghĩa "context lọc theo quyền" — **khác nghĩa** với rule hiện có → BA đề xuất thêm rule mới
    BR-AI-05 (xem §7), không sửa nghĩa BR-PQ-13.
  - BR-PQ-04/05/06/07: AuditLog cho hành động Tầng 2, append-only, actor None = system.
  - BR-PQ-11: SalesOrder/SalesInvoice chỉ Hệ thống tạo — chặn luôn cả "agent tạo đơn" (xem §11).
  - BR-BH-05/11 + BR-PQ-12: chọn lô FEFO một lần lúc tạo đơn, khách/AI không chọn lô tay.
  - BR-MH-06: đơn giá mua là field nhạy cảm → lệnh `nhap_lo` nhãn nhạy cảm `cao`.
  - BR-TT-07, BR-HT-07: xác nhận tiền/hoàn tiền chỉ Chủ — AI không được tự chạy (BR-AI-07).
- **Quyết định ràng buộc:**
  - decisions.md 2026-09-09: FastAPI chỉ là adapter mỏng cho bên thứ 3, không bên ngoài nào nối
    thẳng Django → **Xiaomi cloud là bên thứ 3 thứ hai, bắt buộc đi qua adapter**.
  - decisions.md 2026-09-10: phân quyền 3 tầng, 4 Group cộng dồn; ưu tiên Django Admin cho
    back-office (đến nay ERP console đang thay dần).
  - decisions.md 2026-09-26: FEFO; hạn dùng 365 ngày; cổng SePay.
  - ADR 5.3 yêu cầu cập nhật `decisions.md`/`URD.md`/`doctype-mapping.md` — **decisions.md do Duy
    tự sửa** (BA không đụng); URD/doctype-mapping ghi vào việc tiếp theo (§10).

## 3. Đối chiếu hiện trạng codebase

### 3.1 Đã có (đối chiếu từng mục ADR)

| Mục ADR | Hiện trạng (đã kiểm tra code) | Đánh giá |
|---|---|---|
| 2.5 Lớp lệnh dùng chung | Service layer theo module (`apps/<domain>/<feature>/services.py`): `submit_receipt`, `create_order`, `cancel_paid_order`, `available_actions`… — **đã là nghiệp vụ tập trung**, api.py mỏng (đọc input → kiểm quyền → gọi service → trả JSON). Quy tắc "module gọi module qua services" đã có (backend/README.md). | Thiếu: danh mục lệnh có 6 thành phần schema (tên/nhãn L-C/nhãn nhạy cảm/quyền tối thiểu/input-output JSON schema), endpoint liệt kê cho AI, kênh actor. Là **bọc service hiện có**, không viết lại. |
| 2.6 Phân quyền 3 tầng | Đã cài đủ: `BusinessModelPermissions` (T1), custom perms `Meta.permissions` (T2: publish/close/approve/confirm/view_costprice…), T3 qua `get_queryset` + `CostFieldSerializerMixin` (ẩn giá vốn) + `FULL_SCOPE_GROUPS`. Test rò giá vốn có mẫu. | Thiếu: "AI có đúng quyền user" chưa được phát biểu thành yêu cầu chạy được; context-lọc-cho-prompt chưa có (BR-AI-05). |
| 2.7 AuditLog | Model `accounts.AuditLog` append-only, `record_audit()` dùng chung; actor là FK User, None = system (BR-PQ-07). | **Khác ADR**: chưa có dạng actor `ai:<user>` — cần migration (field mới nullable, dòng cũ giữ nguyên — bất biến 8 có lý do trong hồ sơ này). |
| 2.1 Bật/tắt AI | Chưa có gì. Tham số nghiệp vụ theo env đã thành quy ước (`settings.py`: TTL, cận hạn, chuỗi lạnh…). | Thêm `AI_ENABLED` theo đúng quy ước sẵn có. |
| 3.1 Trần chi phí | Chưa có gì. Adapter hiện không đụng DB (quyết định 2026-09-09) → mức dùng phải ghi ở Django qua internal API. | Cần model mới append-only (xem §8). |
| Công tắc thanh toán | Có tiền lệ "tắt bằng cấu hình, code giữ" (`SEPAY_BANK_WEBHOOK_ENABLED` mặc định tắt, adapter/main.py). | Áp y hệt cho công tắc AI toàn cục và công tắc cloud. |
| ERP console | Đã có: đăng nhập token, menu theo quyền (`nav.ts`), overview, orders (+payments, refunds), inventory, catalog (danh sách + ảnh), staff, account; nháp form (`shared/lib/drafts.ts`). | Chưa có bất kỳ thành phần AI nào. |
| Shop (frontend/) | Landing + Shop tĩnh, khách không đăng nhập. | Không có AI; xem §5 (ngoài phạm vi). |
| Adapter | FastAPI mỏng: /healthz, /webhook/sepay (tắt), /ipn/sepay; forward có retry, không đụng DB. | Chỗ mở rộng tự nhiên: route `/ai/*` proxy MiMo cloud. |
| Job nền | Celery beat (TTL) + `update_batch_status` (cận hạn/quá hạn) + `check_ttl_job_health`. | Nền sẵn cho Proactive Alerts. |

### 3.2 Thiếu / cần đổi (tóm tắt)

1. **Danh mục lệnh** (registry trong Django + endpoint liệt kê lệnh theo quyền user) — mỗi lệnh
   có 6 trường schema theo ADR 2.5. Đề xuất PA: registry code + endpoint, chưa cần bảng DB;
   bật/tắt từng lệnh qua settings/env (🟡).
2. **Kênh AI của lớp lệnh**: endpoint thực thi cho AI (local gửi args JSON lên; server kiểm quyền
   3 tầng + validate input schema + ghi audit `ai:<user>`) và endpoint **đề xuất** (bản nháp chờ
   xác nhận cho hành động Tầng 2).
3. **Context builder lọc theo quyền** (BR-AI-05): trả dữ liệu cho prompt theo đúng quy tắc ẩn
   field của serializer (không `view_costprice` → không có field giá vốn trong context, kể cả user
   hỏi trực tiếp).
4. **Router tĩnh**: FE đọc nhãn local/cloud từ catalog để chọn runtime; BE chặn ngược (lệnh
   `local` không có đường thực thi qua kênh cloud — BR-AI-02).
5. **AuditLog actor `ai:<user>`** — migration mở rộng model (cần Duy chốt Q6).
6. **Công tắc toàn cục** `AI_ENABLED` (tắt → mọi API AI disabled, mọi màn AI ẩn, hệ thống chạy
   100%).
7. **Trần chi phí + ledger** (`AiUsageLedger` append-only; cảnh báo 80%, chặn 100%; số tiền chờ Q2).
8. **Adapter mở rộng**: route proxy MiMo cloud + đo token; Django giữ vai trò điều phối (kiểm
   budget, lọc context, gọi adapter). Adapter vẫn không đụng DB.
9. **FE**: `erp-console/features/ai/` (runtime **wllama + GGUF** — research 27/09: WebLLM/LiteRT.js
   không hỗ trợ MiMo; IndexedDB cache, chat, voice, đồng ý tải model, sliding window).

### 3.3 Khoảng trống nhập liệu của ERP so với Django Admin (mục riêng — Duy phàn nàn)

Đối chiếu trang console với Admin:

| Màn | Console hiện tại | Django Admin | Story đã lên kế hoạch |
|---|---|---|---|
| Mua hàng (nhập lô, hoá đơn, chi phí mua) | Placeholder (`app/(console)/purchasing/`) | Đầy đủ | S28 |
| Kiểm kê | Placeholder (`stocktake/`) | Đầy đủ | S34 |
| Giao hàng (bảng phiếu, gán người giao) | Placeholder (`deliveries/`) | Đầy đủ | S17 |
| Việc giao của tôi (NV giao) | Placeholder (`my-deliveries/`) | Không phù hợp mobile | S20 |
| Báo cáo lãi lỗ | Placeholder (`reports/`) | Đầy đủ | S36 |
| Danh mục & giá (tạo/sửa Item, bảng giá, combo) | Chỉ danh sách + ảnh | Đầy đủ | S38 |
| Nhà cung cấp, PurchaseCost, StockEntry | Chưa có | Đầy đủ | (gộp S28?) |

**Đề xuất xử lý (PA): SONG SONG với AI Native, không làm trước theo lối cũ.** Lý do: ADR bắt mọi
entry point đi qua lớp lệnh — nếu xây màn nhập lô trước bằng ViewSet riêng rồi mới làm lớp lệnh
sẽ phải sửa hai lần. Thứ tự khuyến nghị: (1) **S28 mua hàng** — là nút cổ chai vận hành thật tại
cảng và là "xe" của entry point số 1 (voice nhập lô): lớp lệnh nhóm P-02 → màn nhập lô → gắn
voice; (2) S34 kiểm kê; (3) S17/S20 giao hàng (cần cho cảnh báo chủ động + chat của nv_giao);
(4) S36 báo cáo (đầu vào cho dashboard insights cloud).

**Chốt của Duy (27/09):** dù admin (Duy) hay nhân viên (Lộc) đều xem và làm việc trên **ERP console**
— mọi tính năng phải hoàn thiện ở ERP, không chỉ ở Django Admin. Django Admin là công cụ nội bộ,
không phải mặt sản phẩm; story nào chỉ có màn Admin là chưa xong.

## 4. Phạm vi chi tiết — ADR thành yêu cầu phần mềm

### 4.1 Lớp lệnh nghiệp vụ dùng chung (backend Django)

- Mọi entry point (ERP console, Django Admin, AI local, AI cloud) thực thi nghiệp vụ **qua cùng
  một lớp lệnh** (BR-AI-01). Hiện trạng: service layer đã là nền; việc cần làm là (a) khai danh
  mục lệnh với 6 trường schema, (b) mở kênh AI vào service có sẵn, (c) chuyển dần Admin qua lớp
  lệnh (ADR 3.3 — "không dùng có sẵn hoàn toàn"; lộ trình, không làm 1 phát).
- Schema mỗi lệnh (ADR 2.5): tên lệnh, nhãn local/cloud, nhãn nhạy cảm (cao/trung bình/thấp),
  quyền tối thiểu, input JSON schema, output JSON schema.
- **Danh mục lệnh khởi đầu** (đối chiếu service hiện có; nhãn theo PA, chờ Duy chốt Q5):

| Tên lệnh | local/cloud | Nhạy cảm | Quyền tối thiểu | Nguồn service hiện có | Ghi chú |
|---|---|---|---|---|---|
| `nhap_lo` | local | cao | `nv_kho` (add_purchasereceipt) | `purchasing/receipts` `submit_receipt` | Giá mua nhạy cảm (BR-MH-06); Tầng 2 → xác nhận |
| `tra_ton` | local | trung bình | `nv_kho` (view_batch) | `inventory/batches`, dashboard | Tồn theo lô, không có dữ liệu cá nhân |
| `tra_lo` | local | cao | theo T3 (ẩn field giá vốn khi thiếu view_costprice) | `inventory/batches` | Context lọc theo quyền (BR-AI-05) |
| `tra_hang` | local | thấp | `nv_kho` (view_item) | `catalog/items` | |
| `tra_don` | local | trung bình | theo scope dòng hiện có | `sales/orders` | **Không kèm tên/SĐT/địa chỉ** (BR-AI-09) |
| `bao_cao_ton_kho` | cloud | thấp | `quan_ly` (view_dashboard) | dashboard summary | Tổng hợp, không cá nhân, không giá vốn |
| `bao_cao_lo` / `bao_cao_ky` | cloud (chốt Q5) | cao | `chu` (view_profitreport) | `reports/` | Chứa giá vốn + lãi lỗ — được lên cloud theo Q5 (kèm nghĩa vụ hợp đồng + hồ sơ) |
| `chot_lo` | local | cao | `chu` (close_batch) | `inventory/batches` | **Cấm kênh AI** (BR-AI-07) |
| `tao_phieu_hoan` | local | cao | `chu`/`quan_ly` (create_refund) | `sales/refunds` | Tầng 2 → xác nhận |
| `xac_nhan_hoan` | — | cao | `chu` | `sales/refunds` | **Cấm kênh AI** (BR-AI-07) |
| `xac_nhan_thanh_toan_tay` | — | cao | `chu` | `sales/payments` | **Cấm kênh AI** (BR-AI-07) |
| `kiem_ke` | local | trung bình | `nv_kho` | `inventory/stocktake` | Nhập số kiểm kê |
| `cap_nhat_giao` | local | trung bình | `nv_giao` (scope phiếu mình) | `delivery` | Chỉ đổi trạng thái phiếu được gán |

- Lưu ý đối chiếu: ví dụ `negotiate_price` (cloud+cao) trong ADR là **minh hoạ** — dự án hiện
  không có chức năng đàm phán giá (URD §4.2: giá niêm yết, không thương lượng). Không xây lệnh
  này; mâu thuẫn nhãn cao-trên-cloud vẫn phải chốt ở Q5 vì còn `bao_cao_lo`/`bao_cao_ky`.

### 4.2 Router tĩnh theo nhãn

- Router **không dùng độ tự tin của model** (ADR 2.4): nhãn local/cloud ghi sẵn trên từng lệnh,
  FE đọc từ catalog để chọn runtime, BE chặn ngược chiều (BR-AI-02).
- Lệnh `local`: chạy bằng model on-device trong trình duyệt — runtime **wllama** (GGUF, CPU+WebGPU); LiteRT.js/WebLLM chưa hỗ trợ MiMo (research 27/09). Model do spike chọn (BR-AI-16). Lệnh `cloud`:
  qua adapter → MiMo-V2.6-Flash.
- Máy không đủ RAM/WebGPU (máy kho, máy Duy): **không** đẩy lệnh local lên cloud thay thế — lệnh
  local chuyển về nhập tay; lệnh cloud vẫn chạy bình thường (🟡 PA).

### 4.3 Phân quyền 3 tầng cho AI

- **AI có đúng quyền người đăng nhập, không bao giờ vượt** (ADR 2.6, BR-AI-04): mọi thực thi từ
  kênh AI xác thực bằng chính user và đi lại đủ 3 tầng (T1 model perm, T2 custom perm, T3 scope
  dòng/cột). Lớp lệnh là điểm kiểm soát duy nhất phía server — không tin thiết bị/model
  (BR-PQ-12).
- **Context gửi model lọc theo quyền** (BR-AI-05): đúng quy tắc ẩn field của serializer — user
  không có `view_costprice` thì giá vốn không bao giờ xuất hiện trong prompt.
- **Hành động Tầng 2 luôn cần người xác nhận** (BR-AI-06): AI chỉ sinh bản nháp + args JSON;
  UI hiện khung xác nhận; người duyệt → thực thi với actor = user (+ note mã đề xuất, theo Q6).
- **AI không bao giờ tự** `confirm_refund`, `confirm_payment_manual`, `close_batch` (BR-AI-07) —
  đánh dấu cấm-kênh-AI trên lớp lệnh, kể cả khi user có quyền.

### 4.4 AuditLog actor `ai:<user>`

- Hiện trạng: `AuditLog.actor` là FK User (None = system). Yêu cầu: ghi được 3 loại actor
  `user` / `system` / `ai:<user>` (ai nào, thay cho user nào, lệnh gì, args gì, trước→sau) — giữ
  append-only, dòng cũ không đổi (BR-AI-08). Ngữ nghĩa đã chốt Q6: đề xuất ghi `ai:<user>`,
  thực thi sau xác nhận ghi `user` + note mã đề xuất. Migration mới, field nullable — lý do ghi trong hồ sơ này (bất biến 8).

### 4.5 10 entry point — phân BE/FE

| # | Entry point | Ưu tiên | Phần FE | Phần BE |
|---|---|---|---|---|
| 1 | Voice Input (nhập lô bằng giọng) | 1 | Mic + ASR on-device (Vosk-browser/Whisper WASM — không dùng Web Speech API, audio chứa giá mua) + model local parse (theo spike — BR-AI-16) → điền form nhập lô + khung xác nhận | Catalog lệnh + endpoint thực thi `nhap_lo` + audit `ai:<user>` |
| 2 | Inline Suggestions (gợi ý mã hàng trong form) | 2 | Ô gợi ý trong form nhập lô/kiểm kê | Endpoint gợi ý theo chữ nhập (Item/Supplier — không cá nhân); LLM tuỳ chọn, search API là đủ |
| 3 | Auto-fill | 3 | Điền form từ kết quả voice/AI | Validate args theo input schema từng lệnh |
| 4 | Proactive Alerts (lô cận hạn, đơn chờ, phiếu hoàn chờ) | 4 | Trung tâm thông báo + tóm tắt ngôn ngữ tự nhiên | Đã có nền: job `update_batch_status`, dashboard summary, hàng chờ thanh toán/hoàn; thêm luật alert + endpoint |
| 5 | Chat (hỏi đáp phức tạp) | 5 | Khung chat trong console | Endpoint điều phối: catalog theo quyền + context lọc + thực thi/tham chiếu |
| 6 | Image Input (chụp hoá đơn) | 6 | Chụp/tải ảnh | OCR on-device (PA — hoá đơn chứa giá mua, nhãn cao) → parse thành dòng phiếu nhập/chi phí mua |
| 7 | Smart Buttons (gợi ý lô FEFO) | 7 | Nút "điền theo FEFO" trên form | Đã có `allocate_fefo`/`sellable_batches` — nút chỉ gọi service gợi ý, không cần LLM; **không cho chọn lô tay** (BR-BH-05/11) |
| 8 | Dashboard Insights | 8 | Khối tóm tắt trên Tổng quan | Đã có dashboard/summary; thêm bản tóm tắt NLG qua cloud (dữ liệu gộp, nhãn thấp) |
| 9 | Semantic Search | 9 | Ô tìm kiếm ngữ nghĩa | Index tìm kiếm (mặt hàng, mã đơn — không field cá nhân) |
| 10 | Agent Actions (tạo đơn từ email) | 10 | — | Ngoài phạm vi giai đoạn 1: đụng BR-PQ-11 (SalesOrder chỉ Hệ thống tạo) — cần Duy quyết "AI agent có được coi là Hệ thống không" (§11) |

### 4.6 Chống tràn context

- Sliding window **bắt buộc**, summarization **nên có** (giai đoạn 2), RAG cục bộ tuỳ chọn, bộ
  nhớ phân tầng chưa cần (ADR 2.9).
- Ngưỡng: `MAX_CONTEXT_TOKENS` = 2048 (máy yếu) / 4096 (máy khá), luôn giữ đệm 20% (BR-AI-13).
  Áp cả phía FE (cắt hội thoại local) lẫn BE (chặn prompt quá cỡ trước khi gọi cloud).

### 4.7 Tải model thông minh

- Không bao giờ tự tải model lớn qua 4G/5G (BR-AI-12): chỉ tải khi người dùng **đồng ý**; ưu
  tiên Wi-Fi; 4G/5G → không tải, chạy cloud fallback cho lệnh cloud (lệnh local → nhập tay).
- Progressive: tải core (~200MB) trước, full sau; cache IndexedDB/Cache Storage. TTI < 2s không bị
  ảnh hưởng vì model tải background sau khi web tương tác được.

### 4.8 Công tắc bật/tắt AI toàn cục

- `AI_ENABLED` (env, mặc định theo môi trường): tắt → API AI trả disabled, mọi màn AI ẩn,
  **hệ thống chạy 100% bằng thao tác tay** (BR-AI-10). Tiền lệ trong dự án: công tắc
  `SEPAY_BANK_WEBHOOK_ENABLED` (tắt mà code/test giữ nguyên).

### 4.9 Trần chi phí cloud

- Ngân sách tháng cấu hình được (`AI_CLOUD_MONTHLY_BUDGET_VND`; đã chốt Q2: **200.000đ/tháng** — cận trên của khoảng 100–200k). Cảnh báo ở 80%, **chặn gọi cloud ở 100%** (BR-AI-11).
- Mức dùng (token, chi phí ước tính, lệnh, user) ghi **append-only** ở Django
  (`AiUsageLedger`), adapter chỉ đo và trả về cho Django ghi (adapter không đụng DB — quyết định
  2026-09-09). Chủ xem được bảng mức dùng.

### 4.10 Tuân thủ pháp lý & bảo vệ dữ liệu cá nhân

- **Luật AI 134/2025**: hệ thống AI của Cá Về thuộc rủi ro trung bình (chỉ đề xuất, không tự
  quyết — ADR 2.11); minh bạch (mọi giao diện AI nhận diện được là AI — BR-AI-14);
  human-in-the-loop cho mọi hành động ghi (BR-AI-06).
- **Bất biến 9 + go-live-phap-ly.md**: dữ liệu cá nhân khách (tên, SĐT, địa chỉ ở Customer/
  SalesOrder/DeliveryNote/IPN) **KHÔNG bao giờ vào prompt của model nào, local lẫn cloud**
  (BR-AI-09) — context chỉ dùng mã đơn/mã khách/trạng thái. Không log prompt chứa dữ liệu cá
  nhân; log chỉ ghi mã đơn/mã lệnh.
- **Chuyển dữ liệu xuyên biên giới** (go-live mục 6b): cloud model là bên thứ 3 mới (Xiaomi,
  Trung Quốc) — chỉ được bật khi có hợp đồng/ĐK xử lý dữ liệu và chính sách quyền riêng tư đã
  nêu; mọi dữ liệu gửi cloud phải lọc hết field cá nhân (BR-AI-09, tuyệt đối); field giá vốn
  được phép theo Q5 (kèm hợp đồng + hồ sơ phân loại). **Trước khi bật AI production:** hồ sơ
  phân loại rủi ro + thông báo Bộ KH&CN qua cổng một cửa AI (Luật AI 134/2025, NĐ 142/2026 —
  research 27/09 mục C).
- Kiểm chứng an toàn của ADR giữ nguyên: không tự tải model qua 4G/5G, không tự chạy lệnh tiền.

## 5. Tác nhân & quyền

| Tác nhân | Group | Dùng AI được gì | Quyền AI thừa hưởng |
|---|---|---|---|
| Chủ (Lộc) | `chu` | Toàn bộ lệnh (trừ lệnh cấm kênh AI); xem bảng mức dùng cloud; bật/tắt AI, duyệt chi phí | Đúng quyền `chu` |
| Quản lý | `quan_ly` | Đề xuất/thực thi lệnh vận hành (nhập lô, kiểm kê, tra cứu, cảnh báo); **không** thấy field giá vốn trong context | Đúng quyền `quan_ly` (không view_costprice/profitreport) |
| NV kho | `nv_kho` | Nhập lô bằng giọng, tra tồn/lô, kiểm kê | Đúng quyền `nv_kho` + scope dòng (phiếu của mình trong ngày) |
| NV giao | `nv_giao` | Tra đơn/phiếu **được gán** (không kèm tên/SĐT/địa chỉ), cập nhật trạng thái giao | Đúng quyền `nv_giao` + scope phiếu giao |
| Khách (Shop) | — | **Không** — AI Native chỉ trong ERP nội bộ (🟡 PA; khách không có tài khoản/quyền để cấp cho AI) | — |
| AI (local/cloud) | — | Là kênh của người dùng, không phải tác nhân độc lập; không có quyền riêng | = user đăng nhập (BR-AI-04) |

## 6. Use case

### UC-AI-01 Nhập lô bằng giọng tại cảng (entry point 1)
- **Tiền điều kiện:** user thuộc `nv_kho`/`quan_ly`/`chu`; AI bật; model local đã tải (hoặc có
  Wi-Fi và đã đồng ý); máy đủ RAM/WebGPU; có màn nhập lô (S28) làm nơi điền.
- **Luồng chính:**
  1. Mở màn nhập lô, bấm nút ghi âm. ASR chạy on-device (BR-AI-15).
  2. Model local (theo spike — BR-AI-16) chuyển lời nói thành args JSON cho lệnh `nhap_lo` (mã hàng, kg, đơn giá, nhà
     cung cấp) theo input schema; trường thiếu được hỏi lại bằng tiếng Việt.
  3. Form hiện nội dung AI điền + đánh dấu "do AI đề xuất" (BR-AI-14); user sửa nếu cần.
  4. User bấm xác nhận (hành động Tầng 2 — BR-AI-06).
  5. Lớp lệnh phía server kiểm quyền 3 tầng, validate, thực thi `submit_receipt`, ghi AuditLog
     (đề xuất `ai:<user>`, thực thi theo Q6).
- **Luồng thay thế:** máy không đủ RAM/WebGPU → thông báo "máy này không chạy AI local" → nhập
  tay (không đẩy lên cloud, BR-AI-02). Mất mạng lúc gửi → phiếu giữ nháp cục bộ (dùng cơ chế
  `shared/lib/drafts.ts` hiện có), gửi lại khi có mạng.
- **Ngoại lệ:** AI không hiểu/thiếu trường → hỏi lại tối đa N lần rồi chuyển form tay. Lệnh thiếu
  quyền → 403 (BR-PQ-12). AI gửi args sai schema → 400 kèm mã BR, không ghi gì. Model chưa tải
  xong và đang 4G → không tải, nhập tay (BR-AI-12).
- **Hậu điều kiện:** phiếu nhập SUBMITTED + lô sinh đúng BR-MH-01/02; AuditLog có dòng AI.

### UC-AI-02 Hỏi đáp tra cứu (chat) — tra tồn, tra lô, tra đơn
- **Tiền điều kiện:** user đã đăng nhập có quyền xem đối tượng hỏi.
- **Luồng chính:** gõ/hỏi "lô nào sắp hết hạn", "đơn SO-xxx đang ở đâu" → router chọn local/cloud
  theo nhãn lệnh → BE trả context đã lọc theo quyền (BR-AI-05) và không có dữ liệu cá nhân
  (BR-AI-09) → câu trả lời hiện kèm nhãn "AI".
- **Luồng thay thế:** hội thoại dài → sliding window cắt giữ các lượt gần nhất trong
  `MAX_CONTEXT_TOKENS` − 20% đệm (BR-AI-13); cần ngữ cảnh xa hơn → tóm tắt (giai đoạn 2).
- **Ngoại lệ:** hỏi field user không có quyền (giá vốn) → trả lời "không có quyền xem" và context
  chưa từng chứa field đó (BR-AI-05). Cloud quá trần → từ chối gọi cloud, báo "đã chạm trần chi
  phí tháng" (BR-AI-11). AI tắt → màn chat ẩn (BR-AI-10).
- **Hậu điều kiện:** câu trả lời được ghi log (mã lệnh, user, kênh, không nội dung cá nhân).

### UC-AI-03 AI đề xuất hành động, người xác nhận (mẫu chung cho Tầng 2)
- Áp cho: nhập lô, tạo phiếu hoàn, kiểm kê (đề xuất), huỷ đơn đã thanh toán (đề xuất).
- **Luồng chính:** AI sinh bản nháp (lệnh + args + lý do) → hiện khung xác nhận có nút "Đồng ý
  thực thi" phải tương tác thật (BR-AI-14, giảm rủi ro bấm không đọc) → người duyệt → lớp lệnh
  thực thi với quyền người duyệt → audit.
- **Ngoại lệ:** lệnh trong danh sách cấm kênh AI (confirm_refund/confirm_payment_manual/
  close_batch) → AI không bao giờ sinh bản nháp (BR-AI-07). Người duyệt thiếu quyền → 403.
  Quá hạn nháp (đề xuất giữ 15 phút, PA) → hết hiệu lực, tạo lại.
- **Hậu điều kiện:** hành động đúng quyền người duyệt; audit truy được AI + người + thời điểm
  xác nhận.

### UC-AI-04 Bật/tắt AI & đồng ý tải model
- **Luồng chính:** lần đầu dùng AI → hỏi đồng ý tải model (1,9–4,7GB tuỳ model spike) + chỉ tải khi Wi-Fi; người
  dùng chọn "để sau" → dùng được lệnh cloud, lệnh local nhập tay. Công tắc toàn cục do Duy/Chủ
  đổi (env) — tắt là tắt hết (BR-AI-10).
- **Ngoại lệ:** máy hết dung lượng/cache hỏng → tải lại có hỏi; đang 4G → nhắc đổi Wi-Fi, không
  tải ngầm (BR-AI-12).

### UC-AI-05 Báo cáo & dashboard insights qua cloud
- **Tiền điều kiện:** user có `view_dashboard` (chu/quan_ly/nv_kho) hoặc `view_profitreport`
  (chu) cho phần lãi lỗ.
- **Luồng chính:** mở Tổng quan/Báo cáo → hệ thống gọi cloud với dữ liệu gộp đã lọc (không cá
  nhân, không giá vốn trừ khi user có quyền và Q5 cho phép) → hiện tóm tắt tự nhiên kèm nhãn AI.
- **Ngoại lệ:** cloud lỗi/timeout → hiện số liệu thô như cũ (AI tắt = hệ thống vẫn 100%).
- **Hậu điều kiện:** mức dùng cloud tăng trong `AiUsageLedger`; không vượt trần.

### UC-AI-06 Giám sát trần chi phí cloud
- **Luồng chính:** Duy/Chủ xem bảng mức dùng tháng (lệnh, user, token, chi phí ước tính). Hệ
  thống cảnh báo ở 80% ngân sách, chặn gọi cloud ở 100% (BR-AI-11). Khi chặn: lệnh cloud báo
  "đã chạm trần", lệnh local vẫn chạy.
- **Hậu điều kiện:** không bao giờ vượt ngân sách đã chốt; số liệu append-only.

## 7. Business rule

| Mã | Nội dung | Nhãn | Mới/Sửa |
|---|---|---|---|
| BR-AI-01 | Mọi entry point (console, Admin, AI local, AI cloud) thực thi nghiệp vụ qua cùng một lớp lệnh; mỗi lệnh có đủ 6 trường: tên, nhãn local/cloud, nhãn nhạy cảm (cao/trung bình/thấp), quyền tối thiểu, input JSON schema, output JSON schema. | D (ADR 2.5) | Mới |
| BR-AI-02 | Router tĩnh theo nhãn lệnh, không dùng độ tự tin của model. Lệnh `local` chạy on-device, lệnh `cloud` qua adapter; lệnh `local` không bao giờ bị đẩy lên cloud; lệnh `cloud` không chạy on-device. | D (ADR 2.4) | Mới |
| BR-AI-03 | Nhãn nhạy cảm quyết định dữ liệu được đưa vào prompt: `thấp`/`trung bình` theo chốt của Duy; **`cao` được lên cloud kể từ chốt Q5 (2026-09-27)** — vẫn lọc context theo quyền (BR-AI-05) và PII vẫn cấm tuyệt đối (BR-AI-09). Trước khi bật cloud production: hợp đồng không-huấn-luyện + zero retention + ghi vào hồ sơ phân loại. | D (Q5, 2026-09-27) | Sửa (PA) |
| BR-AI-04 | AI có đúng quyền của người đăng nhập, không bao giờ vượt. Lớp lệnh phía server kiểm lại đủ 3 tầng (T1 perm, T2 custom perm, T3 scope dòng/cột) cho mọi thực thi từ kênh AI — không tin thiết bị/model (tinh thần BR-PQ-12). | D (ADR 2.6) | Mới |
| BR-AI-05 | Context gửi model (local lẫn cloud) lọc theo quyền đúng quy tắc ẩn field của serializer: user không có `view_costprice` thì field giá vốn không bao giờ xuất hiện trong prompt, kể cả user hỏi trực tiếp. | D (ADR 2.6 dẫn BR-PQ-13) | Mới (không đổi nghĩa BR-PQ-13 hiện có) |
| BR-AI-06 | Hành động Tầng 2 của AI luôn dừng ở bản nháp (lệnh + args + lý do); chỉ thực thi sau khi người xác nhận trên UI (human-in-the-loop, Luật AI 134/2025). | D (ADR 2.6/2.11) | Mới |
| BR-AI-07 | AI không bao giờ tự thực thi `confirm_refund`, `confirm_payment_manual`, `close_batch` — kể cả người dùng có quyền; các lệnh này đánh dấu cấm-kênh-AI trên lớp lệnh. | D (ADR 2.6) | Mới |
| BR-AI-08 | AuditLog phân biệt 3 loại actor: `user` / `system` / `ai:<user>`. Mọi đề xuất và thực thi từ AI ghi log: ai nào, thay cho user nào, lệnh gì, args, trước→sau. Giữ append-only (BR-PQ-06), dòng cũ không đổi. **Ngữ nghĩa chốt Q6:** bản đề xuất ghi actor `ai:<user>`; khi người xác nhận thực thi thì dòng thực thi ghi actor `user` + note mã đề xuất. | D (ADR 2.7 + Q6) | Mới |
| BR-AI-09 | Dữ liệu cá nhân khách (tên, SĐT, địa chỉ — bất biến 9) KHÔNG bao giờ vào prompt của model nào (local lẫn cloud); context chỉ dùng mã đơn/mã khách/mã phiếu + trạng thái. Không log prompt chứa dữ liệu cá nhân. | D + bất biến 9 | Mới |
| BR-AI-10 | Tắt AI toàn cục (công tắc `AI_ENABLED`) → mọi màn/API AI ẩn hoặc disabled, hệ thống chạy 100% bằng thao tác tay; không màn hình/flow nào phụ thuộc AI. | D (ADR 2.1) | Mới |
| BR-AI-11 | Trần chi phí cloud theo tháng (cấu hình `AI_CLOUD_MONTHLY_BUDGET_VND`): cảnh báo ở 80%, chặn gọi cloud ở 100%. Mức dùng (lệnh, user, token, chi phí) ghi append-only, Chủ xem được. | D (ADR 3.1) | Mới |
| BR-AI-12 | Không bao giờ tự tải model qua 4G/5G. Chỉ tải khi người dùng đồng ý; ưu tiên Wi-Fi; tải dần (core trước, full sau); cache IndexedDB. Máy không đủ RAM/WebGPU → không cố tải, lệnh local chuyển nhập tay. | D (ADR 2.10) | Mới |
| BR-AI-13 | Sliding window bắt buộc cho hội thoại AI; `MAX_CONTEXT_TOKENS` = 2048 (máy yếu) / 4096 (máy khá), luôn giữ đệm 20%; không bao giờ vượt ngưỡng. Model chốt Gemma 3n hỗ trợ context tới 32k token — mức dùng tối đa thực tế do S17 đo RAM quyết; mặc định vẫn 2048/4096 để chống tràn. | D (ADR 2.9) | Mới |
| BR-AI-14 | Mọi giao diện AI phải nhận diện được là AI (minh bạch, Luật AI 134/2025). Khung xác nhận Tầng 2 buộc tương tác thật (không bấm một chạm) và log thời điểm xác nhận (giảm rủi ro "bấm xác nhận không đọc"). | D (ADR 2.11 + bảng rủi ro) | Mới |
| BR-AI-15 | Thoại/ảnh của lệnh nhãn nhạy cảm `cao` chỉ xử lý on-device (ASR: Vosk-browser/Whisper WASM; không dùng Web Speech API gửi audio lên server). Không gửi audio/ảnh chứa dữ liệu nhạy cảm lên cloud. | D (ADR bảng rủi ro) | Mới |
| BR-AI-16 | **Local-first bắt buộc (Q1, 2026-09-27):** mọi lệnh nhãn `local` phải có đường chạy on-device thật trên thiết bị nhân viên; model không chạy được on-device thì phải thay model khác — không chấp nhận "local giả" (đẩy lên cloud). Runtime: wllama + GGUF (research 27/09). Model chốt theo Duy: **Gemma 3n (32k)** — S17 chọn bản E2B/E4B theo RAM; dự phòng Frog/SEA-LION/Sailor; MiMo-7B nếu spike chứng minh chạy được. | D (Q1, 2026-09-27) | Mới |
| BR-AI-17 | **Hiệu năng không đánh đổi (Duy, 27/09/2026, khi duyệt story):** website/ERP phải chạy mượt như khi chưa có AI. AI code lazy-load (dynamic import) — Shop và người không bật AI không tải code/model AI; runtime wllama + suy luận chạy ngoài main thread (Web Worker), không chặn tương tác; bundle/TTI không tăng đáng kể (TTI < 2s); lệnh cloud gọi async không chặn luồng nghiệp vụ; `AI_ENABLED=false` → hiệu năng y hệt khi chưa có AI. | D (chốt khi duyệt story, 2026-09-27) | Mới |

## 8. Tác động dữ liệu & tích hợp

- **`accounts.AuditLog`** (SỬA, migration): mở rộng để ghi actor `ai:<user>` — field mới
  nullable (dòng cũ giữ nguyên; append-only). Lý do đã ghi tại §4.4 (bất biến 8).
- **`AiUsageLedger`** (MỚI, append-only): tháng, user, lệnh, kênh local/cloud, token, chi phí
  ước tính — nền cho BR-AI-11.
- **Danh mục lệnh**: đề xuất PA là registry code trong Django + endpoint liệt kê (lọc theo quyền
  user) — chưa cần bảng DB; nếu sau này cần bật/tắt từng lệnh riêng thì nâng lên bảng cấu hình.
- **Không đổi model nghiệp vụ hiện có** (Item/Batch/Order/Refund… nguyên schema).
- **Tham số mới** (env/settings, theo quy ước không hard-code): `AI_ENABLED`,
  `AI_CLOUD_MONTHLY_BUDGET_VND`, `AI_CLOUD_ALERT_PCT` (80), `AI_MAX_CONTEXT_TOKENS`,
  `AI_DRAFT_TTL_MINUTES`; secret `MIMO_API_KEY` trong Secret Manager (không commit).
- **Adapter** (MỞ RỘNG): route `/ai/*` proxy MiMo-V2.6-Flash — bên thứ 3 thứ hai, bắt buộc qua
  adapter (decisions 2026-09-09), adapter không đụng DB; Django điều phối (kiểm trần → lọc
  context → gọi adapter → nhận token usage → ghi ledger).
- **ERP console** (MỞ RỘNG): `features/ai/` — runtime wllama (GGUF), IndexedDB cache, chat,
  voice, đồng ý tải model, sliding window; tái dùng nháp form (`shared/lib/drafts.ts`) cho
  offline tại cảng.
- **Django Admin** (DẦN): các action Tầng 2 chuyển sang gọi lớp lệnh (lộ trình, ADR 3.3).
- **Tài liệu**: `decisions.md` (Duy tự thêm quyết định AI Native), `URD.md` (thêm yêu cầu phi
  chức năng AI), `doctype-mapping.md` (viết lại kèm danh mục lệnh 2 cột nhãn) — ADR 5.3.

## 9. Rủi ro Cá Về

| Rủi ro | Mức | Giảm thiểu (rule tương ứng) |
|---|---|---|
| **Rò giá vốn qua prompt/context** — rủi ro cao nhất dự án | Cao | BR-AI-03/05: lọc context theo quyền như serializer; nhãn `cao` mặc định không rời máy; test gọi kênh AI bằng token từng Group (tinh thần BR-PQ-13) |
| **Rò dữ liệu cá nhân khách** (Critical — bất biến 9) | Cao | BR-AI-09: cấm PII vào model nào; cloud = bên thứ 3 mới phải Duy duyệt (Q1) + chính sách quyền riêng tư; không log prompt chứa PII |
| **Tiền / con số lời lỗ bị đổi** | Cao | BR-AI-07: cấm 3 lệnh tiền/chốt lô trên kênh AI; BR-AI-06: Tầng 2 luôn có người xác nhận; audit `ai:<user>` |
| **FEFO/tồn sai** | Cao | AI chỉ gợi ý qua `allocate_fefo`/`sellable_batches`; không cho chọn lô tay (BR-BH-05/11, BR-PQ-12); thực thi chạy lại service gốc |
| **Chứng từ/doanh thu khống** | Cao | AI không tạo SalesOrder/SalesInvoice (BR-PQ-11); không xoá chứng từ (BR-PQ-10); `agent actions` hoãn tới khi Duy quyết |
| **Nhân viên bấm xác nhận không đọc** | Trung bình | BR-AI-14: UI buộc tương tác, log thời gian xác nhận |
| **Chi phí cloud vượt kiểm soát** | Trung bình | BR-AI-11: cảnh báo 80%, chặn 100%, ledger append-only |
| **Model on-device chưa được chứng minh** (MiMo-7B chưa có đánh giá tiếng Việt; web runtime chưa hỗ trợ) | Cao | Spike 50 câu thật với Gemma 3n trên wllama trước khi cam kết voice (BR-AI-16); MiMo chỉ nếu spike chứng minh chạy được — chờ S17 spike trên máy tham chiếu 8GB (Q4 đã chốt) |
| **Tràn context gây crash** | Trung bình | BR-AI-13: sliding window + đệm 20% |
| **AI kéo tụt hiệu năng website** | Trung bình | BR-AI-17: lazy-load + Web Worker + TTI < 2s; QA đo perf ở mỗi lô có FE |
| **Mạng yếu tại cảng** | Trung bình | Voice chạy on-device không cần mạng; phiếu giữ nháp cục bộ rồi gửi |
| **AI tắt thì hệ thống chết** | Trung bình | BR-AI-10: tắt AI hệ thống chạy 100% — AC bắt buộc cho mọi story AI |

## 10. Phân đoạn thực hiện (đề xuất cho PO)

**Nguyên tắc:** MVP bắt đầu từ nền tảng (lớp lệnh + router + phân quyền + audit) + 2 entry point
đầu (voice/chat trên 2–3 lệnh), dùng **mock/LLMock** (ADR 2.12 — dev không cần máy mạnh); spike
on-device chạy song song trên máy tham chiếu ≥ 8GB (Q4 đã chốt).

- **Giai đoạn 0 — Nền (song song với S28):**
  1. Lớp lệnh: registry + 6 trường schema + endpoint catalog theo quyền + kênh thực thi/đề xuất
     cho AI (nhóm lệnh khởi đầu §4.1).
  2. Router tĩnh + công tắc `AI_ENABLED` + context builder lọc quyền (BR-AI-05) + kênh audit
     `ai:<user>` (migration) + `AiUsageLedger` + trần chi phí.
  3. S28 màn nhập lô qua lớp lệnh (không làm ViewSet riêng).
- **Giai đoạn 1 — MVP AI (chat + voice, 2–3 lệnh):** voice nhập lô (ASR on-device + model local theo
  spike → form xác nhận), chat tra tồn/tra lô; đóng băng mọi rule BR-AI-01…16. Spike 50 câu thật
  (ADR 5.1) trên máy tham chiếu 8GB; chưa sắp được máy thì tạm dùng mock và đánh dấu rủi ro.
- **Giai đoạn 2 — Mở rộng entry point + cloud:** inline suggestions, auto-fill, proactive alerts,
  dashboard insights (lệnh `thấp` qua adapter → MiMo cloud), smart buttons (FEFO), tải model
  thông minh hoàn thiện, summarization; hoàn thiện S34/S17/S20/S36 song song.
- **Giai đoạn 3 — Nâng cao:** image input (OCR on-device), semantic search, RAG cục bộ (tuỳ
  chọn), agent actions (sau quyết định BR-PQ-11), Admin chuyển hẳn qua lớp lệnh.

**Việc tiếp theo ngoài code:** Duy thêm quyết định vào `decisions.md`; cập nhật `URD.md`;
viết lại `doctype-mapping.md` kèm danh mục lệnh 2 cột nhãn (ADR 5.3).

## 11. Ngoài phạm vi (giai đoạn 1)

- **Shop/khách hàng**: không có AI (khách không tài khoản, không có quyền để cấp cho AI — 🟡).
- **Agent Actions** (tạo đơn từ email…): mâu thuẫn BR-PQ-11 (SalesOrder chỉ Hệ thống tạo) — cần
  Duy quyết riêng "AI agent có được coi là Hệ thống không" trước khi làm (🟢 để sau).
- RAG cục bộ, bộ nhớ phân tầng (ADR: tuỳ chọn/chưa cần); summarization làm ở giai đoạn 2.
- Lệnh `negotiate_price` trong ví dụ ADR — nghiệp vụ đàm phán giá đang outscope (URD §4.2).
- AI cho thanh toán/hỗ trợ khách trên Shop; kênh AI cho Django Admin toàn phần (chỉ chuyển dần
  các action Tầng 2).

## 12. Câu hỏi mở

### 🔴 Chặn (xem bảng đầu file)

Q1–Q6 — gồm 4 câu hỏi ADR 5.4 (Q1 dữ liệu gửi Xiaomi, Q2 trần chi phí + ai trả, Q3 thoả thuận
với Lộc, Q4 máy spike) và 2 câu phát sinh từ đối chiếu (Q5 lệnh nhạy cảm cao lên cloud, Q6 ngữ
nghĩa actor `ai:<user>` sau xác nhận).

### 🟡 Đã giả định (Duy lật được, ghi rõ mặc định)

| # | Giả định PA | Mặc định đề xuất |
|---|---|---|
| G1 | Phạm vi AI Native | Chỉ ERP console nội bộ; Shop không có AI |
| G2 | ASR giọng nói | On-device (Vosk-browser/Whisper WASM), không dùng Web Speech API |
| G3 | Máy không đủ RAM/WebGPU | Lệnh local chuyển nhập tay, không đẩy lên cloud |
| G4 | Danh mục lệnh | Registry code + endpoint; chưa cần bảng DB |
| G5 | Trần chi phí | Lưu và chặn ở Django (adapter chỉ đo token) |
| G6 | Bản nháp AI chờ xác nhận | TTL 15 phút, hết hạn tạo lại |
| G7 | MAX_CONTEXT_TOKENS | 2048 mặc định, đệm 20% |
| G8 | Offline tại cảng | Dùng nháp form hiện có (`shared/lib/drafts.ts`), chưa làm offline-first hoàn chỉnh |
| G9 | Model load lần đầu | Hỏi đồng ý từng thiết bị, không lưu PII (chỉ cờ đồng ý) |

### 🟢 Để sau

Semantic search chi tiết, image input chi tiết, RAG cục bộ, summarization, agent actions (chờ
quyết định BR-PQ-11), kênh AI cho Django Admin toàn phần.
