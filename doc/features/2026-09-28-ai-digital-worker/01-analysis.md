# AI của tôi: người dùng tự giao quyền cho AI ("nhân viên số") — Phân tích nghiệp vụ
> BA · 2026-09-28 (viết lại sau khi Duy trả lời Q1–Q3; bổ sung §4.7 cùng ngày) · Trạng thái:
> **CHỜ DUYỆT (bổ sung 28/09)**. Phần "AI của tôi" (§4.1–4.6) đã được Duy duyệt hướng. Phần mới §4.7
> "Hướng dẫn theo từng chứng từ" và các rule BR-AI-28…34 chờ Duy duyệt. Không có câu hỏi 🔴; các mặc
> định 🟡 ở §15 Duy lật được.
>
> **Đây là lật quyết định đã chốt** (ADR AI Native 27/09 §2.6 và lý do phân loại ở §2.11; BR-AI-06;
> BR-AI-07). Duy đã chốt hướng lật ngày 2026-09-28 (mục "Câu trả lời của Duy"). BA không sửa
> `decisions.md` hay ADR; Duy tự ghi quyết định sau khi đọc file này.
> Pháp lý: memo `01c-phap-ly.md` cùng thư mục (legal-vn, 2026-09-28).

## Câu trả lời của Duy (2026-09-28) — quyết định đã chốt

| # | Câu hỏi (bản trước) | Trả lời nguyên văn của Duy | Hệ quả áp vào bản phân tích |
|---|---|---|---|
| Q1 | "AI tự làm" nghĩa là gì trong giai đoạn này? | **"cho phép người dùng tự phân quyền cho AI của mình"** | Mô hình **AI của tôi**: mỗi người dùng tự chọn lệnh nào (trong quyền của mình) AI được làm và ở mức nào (A/B/C). Mặc định C khi chưa cấu hình. §4, §5. |
| Q2 | Ba lệnh tiền và chốt lô (BR-AI-07) | **Chọn "Mở theo công tắc của Chủ"** (Chủ tự bật tự chủ khi muốn). Duy chọn khi đã biết khuyến nghị ngược lại của BA và legal-vn. | BR-AI-07 đổi từ "cấm" thành "**đóng mặc định, chỉ Chủ mở bằng công tắc riêng**, và chỉ cho AI của người có quyền tương ứng". Sàn cứng §6 vẫn áp. Ghi trung thực phần AI vẫn không làm được ở §7. |
| Q3 | AI là ai, ai chịu trách nhiệm | **"ai cấp quyền thì người đó chịu trách nhiệm"** | Người cấu hình AI của mình chịu trách nhiệm cho việc AI làm theo cấu hình đó. AuditLog ghi **người cấp + phiên bản cấu hình tại thời điểm thực thi**. Lệnh vùng đỏ có hai lớp cấp: Chủ mở vùng, chủ AI cấu hình lệnh. §4.3. |
| Bổ sung | (yêu cầu mới, không phải câu hỏi) | **"chỗ Agent đó, có thể đề xuất bước tiếp hoặc những gì đã làm trong từng record để nhân viên nào cũng làm được thay vì phải học thuộc quy trình"** | Mục mới §4.7: khối "Tiếp theo" và "Đã làm" trên từng chứng từ. Phần bước hợp lệ và dòng thời gian là tất định, AI chỉ diễn đạt và đề nghị "để AI làm". |
| M1 (28/09) | Kiến trúc function cho AI (research `research/01-mcp-per-function.md`) | **Chọn "B+: decorator + MCP server"** | Mỗi function khai báo bằng decorator cạnh service, schema sinh từ serializer đầu vào, xuất MCP server chuẩn trong Django (chỉ console nội bộ, chưa mở agent ngoài), 3 nhóm tool: Thu mua · Bán hàng · CSKH. Registry viết tay của S01 được thay. Thiết kế ở `02b-tech-design.md`. |
| M1-sửa (28/09) | Làm rõ M1 | **"anh hiểu nhầm biến feature thành mcp rồi, nó sẽ gây context lớn và crash ?? mong muốn của anh là: mọi feature mới sinh ra đều tự động trở thành lệnh mà AI có thể gọi, chỉ bị giới hạn bởi phân quyền, chứ không bị hard-code trong registry."** | Thay M1: trọng tâm là **tự đăng ký lệnh** từ feature/service, mặc định an toàn khi feature không khai gì; giới hạn chỉ bằng phân quyền + "AI của tôi" + sàn cứng. MCP chỉ là tuỳ chọn giao thức. Không bao giờ nạp cả danh mục vào prompt: chọn lệnh 2 bước (lọc/tìm → nạp schema của ≤ 3–5 lệnh). |
| M-scope (28/09) | Vai trò tự định nghĩa + luồng CSKH | **"Tách 2 hồ sơ mới"**. Ý Duy: vai trò/quyền trên tính năng do người dùng tự định nghĩa (tự tạo profile vai trò, một user kiêm nhiệm nhiều vai; vựa này tách, trường hợp khác gộp). CSKH là nhân viên nội bộ: gọi khách xác nhận địa chỉ để tư vấn → tự động in tem → vào kho lấy hàng. | Hai hồ sơ BA riêng; hồ sơ này chỉ tham chiếu. |
| M-spike (28/09) | Spike Gemma 3n gọi tool trước khi thiết kế? | **"làm thiết kế đã, không duyệt là chưa làm"** | Viết thiết kế trước; spike và code chỉ làm sau khi Duy duyệt thiết kế. |
| Q4 | Chấp nhận hệ quả pháp lý? | Coi như đã trả lời bằng memo `01c-phap-ly.md` | Vẫn **rủi ro trung bình** (không thuộc Danh mục QĐ 33/2026). **Phải viết lại hồ sơ phân loại** (bỏ lý do "chỉ đề xuất, không tự quyết"). Vùng đỏ vướng **Luật Kế toán Đ.16** (người duyệt chứng từ), **Luật BVQLNTD 2023** (trách nhiệm với khách), **NĐ 356/2025** (quyết định tự động ảnh hưởng khách). Các nghĩa vụ này thành sàn cứng (§6) và điều kiện bật production (§6, S-L). |

## 1. Yêu cầu gốc

> "Chỉ tạo bản nháp, người bấm xác nhận mới ghi. Việc tiền và chốt lô thì AI không được đụng tới
> --> anh nghĩ là để AI tự làm cũng đc, coi AI như digital worker, cái nào ko làm đc thì escalate
> tới người dùng"

Nguồn: Duy (PO), 2026-09-28. Làm rõ bằng ba câu trả lời Q1–Q3 ở trên.

## 2. Tóm tắt

**Mỗi người dùng ERP** (Chủ, Quản lý, NV kho, NV giao) cần **tự giao cho "AI của mình" những lệnh
trong quyền của chính mình, ở mức tự chủ mình chọn**, để **bớt thao tác xác nhận và bớt nút cổ chai
khi Lộc vắng**. Người giao chịu trách nhiệm. Việc AI không làm được thì AI chuyển lại cho chính người
đó (hoặc người có quyền). Một số **sàn cứng** do bất biến dự án và luật đặt ra thì không cấu hình nào
vượt được.

Điểm then chốt:
1. **Quyền của AI = giao của quyền người dùng và cấu hình người dùng đặt.** Không bao giờ rộng hơn
   quyền người dùng (BR-AI-04 giữ nguyên).
2. **Mặc định mọi lệnh ghi ở mức C** (nháp chờ duyệt, y như hiện nay). Không cấu hình thì không có
   gì thay đổi.
3. **Ba lệnh vùng đỏ** (`chot_lo`, `xac_nhan_hoan`, `xac_nhan_thanh_toan_tay`) đóng mặc định. Chỉ Chủ
   mở được. Cả ba quyền này hiện chỉ Group `chu` có, nên **trên thực tế chỉ AI của Chủ** được giao.
4. **Bật công tắc không tạo ra dữ liệu AI không có.** AI vẫn không chuyển được tiền (SePay không có
   API chuyển tiền đi) và không đọc được sao kê. Khi bật, AI chỉ xử lý ca **khớp tuyệt đối bằng dữ liệu
   đã có trong hệ thống**. Mọi ca khác chuyển Chủ (§7). Với `xac_nhan_hoan`, ở V1 **không có nguồn
   dữ liệu nào**, nên bật lên cũng chưa có tác dụng.

## 3. Bối cảnh trong hệ thống

- **Quy trình bị ảnh hưởng**: không thêm quy trình. Đổi cách thực thi của P-02 (nhập lô), P-04 (chốt
  lô), P-05 (xác nhận thanh toán tay), P-06 (cập nhật giao), P-07 (phiếu hoàn), P-09 (kiểm kê).
- **Rule bị đụng**: BR-AI-04, 06, 07, 08, 14 (hồ sơ AI Native §7); BR-PQ-04, 07, 08, 11; BR-TT-03,
  05, 07, 15; BR-HT-03, 06, 07; BR-LO-04, 05; BR-KK-02, 05; BR-GH-05.
- **Quyết định ràng buộc**:
  - ADR AI Native 27/09 §2.4 (router tĩnh, không dùng độ tự tin), §2.6 (**lật**), §2.11 (**sửa lý do
    phân loại**).
  - decisions 2026-09-10 (phân quyền): ranh giới Chủ/Quản lý. Không bị lật: quyền của AI không vượt
    quyền người, nên AI của Quản lý vẫn không đụng được việc của Chủ.
  - decisions 2026-09-10 (hoàn tiền): SePay không có API hoàn tiền. Giữ nguyên, và đây là lý do
    `xac_nhan_hoan` gần như không tự động được.
  - decisions 2026-09-10 (mặc định PA): kiểm kê người nhập ≠ người duyệt.
  - decisions 2026-09-26: webhook ngân hàng SePay tắt ở V1; chỉ IPN `ORDER_PAID` xác nhận thanh toán.
  - Duy 27/09 (02b C4): "AI là 1 add-on thôi, bật/tắt agent theo từng user được".
- **Vận hành**: Lộc chưa bán. Không có số đo độ đúng của AI. Mọi ngưỡng là giả định (PA).

### 3.1 Hiện trạng code (kiểm tra 2026-09-28)

| Hạng mục | Hiện trạng | Nguồn |
|---|---|---|
| Registry 14 lệnh | 12 active, 2 draft. `needs_confirmation` ở `nhap_lo`, `tao_phieu_hoan`, `kiem_ke`. `forbidden_channel="ai"` ở 3 lệnh vùng đỏ. `handler=None`. | `backend/apps/ai/commands/registry.py` |
| Kênh execute/propose/confirm, `AiProposal` | **Chưa xây** (S02, Lô 2). | `03-dev-notes.md` |
| AuditLog | Đã có `actor_kind`, `ai_actor`, `proposal_ref` (S03). Chưa có chỗ ghi người cấp / phiên bản cấu hình. | `accounts/models.py`, migration 0007 |
| Cấu hình AI theo user | **Chưa có gì.** Chỉ có công tắc toàn cục `AI_ENABLED` (thiết kế S05). | 02b |
| `close_batch` | Kiểm tồn = 0 và có Purchase Invoice. **Không có service mở lại lô.** | `inventory/batches/services.py` |
| `confirm_refund` | Bắt buộc `bank_txn_ref` (BR-HT-03). | `sales/refunds/services.py` |
| `confirm_payment_manual` | Bắt buộc `bank_txn_id`, chạy chung đường ghi tiền với webhook. | `sales/payments/services.py` |
| Hàng chờ giao dịch lệch | `PaymentTransaction` có `match_status` UNMATCHED/UNDERPAID/ORPHAN/OVERPAID, `resolution_status` OPEN, `duplicate_warning` (BR-TT-15), `raw_payload` (có PII: tên người chuyển, nội dung CK). | `sales/models/payments.py` |
| Huỷ phiếu hoàn | Không có trạng thái huỷ; chỉ FAILED/retry. | `sales/refunds/services.py` |
| Huỷ phiếu nhập | **Không có.** Lô sinh ra ở Nháp, chưa lên Shop tới khi publish (BR-MH-05). | `purchasing/receipts/services.py` |

**Thời điểm**: S02 chưa xây, nên đưa mô hình này vào thiết kế S02 lúc này là rẻ nhất.

## 4. Mô hình "AI của tôi"

### 4.1 Khái niệm

- Mỗi người dùng ERP có **một AI của mình** (không phải một tài khoản User riêng; là "cấu hình uỷ
  quyền" gắn với User đó). AI luôn chạy **thay mặt** người đó.
- Người dùng mở màn **AI của tôi** và, với từng lệnh **nằm trong quyền của mình**, chọn một mức:

| Mức | Nghĩa | Người ở đâu |
|---|---|---|
| **Tắt** | AI không được dùng lệnh này (kể cả đọc) | — |
| **C** | AI soạn nháp, người bấm xác nhận mới ghi (y như BR-AI-06 cũ) | Duyệt trước |
| **B** | AI tự ghi, báo ngay, người hoàn tác được trong N phút | Giám sát sau |
| **A** | AI tự ghi, chỉ ghi nhật ký và vào báo cáo cuối ngày | Rà soát định kỳ |

- **D** không phải lựa chọn cấu hình. D là tình huống AI **không có dữ liệu hoặc không có tay chân**
  để làm, bất kể mức nào. Khi đó AI **chuyển việc** (escalate) cho chính chủ AI; nếu chủ AI không có
  quyền làm việc đó thì chuyển Group có quyền (§8).
- Mỗi lệnh có **mức tối đa** (trần) do hệ thống quy định (§5). Người dùng chỉ chọn được mức ≤ trần.
- Lệnh đọc (tra cứu, báo cáo) không có gì để "duyệt"; mặc định là A như hiện nay, người dùng chỉ có
  thể tắt (🟡 Q-M1).

### 4.2 Quyền hiệu lực

- **Quyền hiệu lực của AI = quyền hiện hành của người dùng ∩ cấu hình người dùng đặt ∩ trần của
  lệnh ∩ công tắc (toàn cục, theo user, vùng đỏ).** Không phép hợp nào.
- Kiểm **tại thời điểm thực thi**, không phải lúc cấu hình. Người dùng bị gỡ Group (vd NV kho chuyển
  sang NV giao) thì cấu hình cũ cho lệnh ngoài quyền **tự mất hiệu lực** ngay, không cần ai sửa.
- Phạm vi dòng/cột (Tầng 3) giữ nguyên: AI của NV giao chỉ thấy phiếu được gán cho người đó; AI của
  Quản lý không thấy giá vốn.

### 4.3 Trách nhiệm (Q3)

- **Người cấu hình chịu trách nhiệm** cho mọi việc AI của mình làm theo cấu hình đó (Duy, Q3).
- Lệnh vùng đỏ có **hai lớp cấp**: Chủ bật công tắc vùng đỏ (chịu trách nhiệm mở vùng) và chủ AI
  cấu hình lệnh (chịu trách nhiệm thực thi). Hiện hai lớp là cùng một người (Lộc), vì chỉ `chu` có
  quyền của ba lệnh này.
- **Trên chứng từ**: các field người thực hiện (`closed_by`, `confirmed_by`, `resolved_by`…) ghi
  **người cấp** (chủ AI), vì AI không có tư cách pháp lý (memo §4). AuditLog phân biệt rõ đây là do AI
  thực thi.
- ⚠ Pháp lý: memo §5 nói "người duyệt" chứng từ thu/chi/giá vốn không thể là AI. Việc ghi người cấp
  làm người duyệt khi người đó **đã uỷ quyền trước** có đủ điều kiện "người duyệt" theo Luật Kế toán
  Đ.16 hay không là điểm **cần kế toán/luật sư xác nhận** (memo §11 điểm 6). Duy đã chọn khi biết rủi
  ro. BA đặt thành điều kiện trước production (S-L1), không chặn PO.
- AI **không phải** "Hệ thống" (BR-PQ-07). Việc do model quyết ghi `actor_kind = ai`. Job tất định
  (TTL, IPN) vẫn là `system`.

### 4.4 Nhật ký và phiên bản cấu hình

- Mỗi lần người dùng (hoặc Chủ) đổi cấu hình AI → sinh **một phiên bản mới**, append-only; không sửa,
  không xoá phiên bản cũ. Ghi ai đổi, lúc nào, trước → sau.
- Mỗi lần AI thực thi (A/B) hoặc soạn nháp (C) → AuditLog ghi: `actor_kind = ai`, **chủ AI (người
  cấp)**, **mã phiên bản cấu hình đang hiệu lực**, mức, lệnh, args, trước → sau, lý do rơi mức (nếu
  có). Với C thì giữ ngữ nghĩa Q6 cũ (đề xuất `ai:<user>`, thực thi `user` + mã đề xuất).
- Hoàn tác (B) ghi một dòng AuditLog riêng.

### 4.5 Thu hồi, đổi, tắt khẩn

- Đổi hoặc thu hồi cấu hình có **hiệu lực tức thì**, không cần đăng nhập lại hay deploy.
- Việc B đang trong cửa sổ trì hoãn mà cấu hình bị thu hồi → **không ghi**, chuyển về C (🟡 Q-M5).
- **Tắt khẩn toàn cục** (mở rộng `AI_ENABLED` / công tắc tự thực thi riêng như memo §3 gợi ý): mọi
  AI rơi về C (hoặc tắt hẳn), tức thì. Ai bấm: Chủ (và Duy với vai quản trị) (🟡 Q-M3).
- **Tắt khẩn theo user**: chính người dùng và Chủ bấm được. AI của người đó rơi về C.
- Kill switch **luôn thắng** mọi cấu hình.

### 4.6 Công tắc vùng đỏ của Chủ

- Một công tắc riêng cho **từng lệnh** vùng đỏ: `chot_lo`, `xac_nhan_hoan`, `xac_nhan_thanh_toan_tay`.
  Mặc định **đóng**.
- Chỉ người có quyền quản lý chính sách AI (mặc định chỉ `chu`) bật được. Bật chỉ **cho phép** chủ AI
  có quyền tương ứng (`close_batch`, `confirm_refund`, `confirm_payment_manual`) cấu hình lệnh đó lên
  B; không tự đổi cấu hình của ai.
- Đóng công tắc → mọi cấu hình của lệnh đó rơi về C ngay.
- Chủ cũng đặt được **trần ngưỡng** (tiền, kg) cho từng lệnh; người dùng đặt thấp hơn được, không cao
  hơn (🟡 Q-M2).

### 4.7 Hướng dẫn theo từng chứng từ: "Tiếp theo" và "Đã làm" (bổ sung 28/09)

**Yêu cầu** (Duy, 28/09): *"chỗ Agent đó, có thể đề xuất bước tiếp hoặc những gì đã làm trong từng
record để nhân viên nào cũng làm được thay vì phải học thuộc quy trình"*.

**Tóm tắt**: **Mọi nhân viên** cần, trên màn chi tiết của **từng chứng từ**, thấy **việc tiếp theo hợp
lệ** (ai làm, còn thiếu gì, hạn khi nào, vì sao) và **những gì đã xảy ra** với chứng từ đó, để **làm
đúng quy trình mà không phải học thuộc P-01…P-10**.

**Nguyên tắc chính (PA)**:
1. **Phần sự thật là tất định.** Danh sách bước hợp lệ tính từ máy trạng thái, quyền và điều kiện
   nghiệp vụ trong service. Dòng thời gian lấy từ AuditLog và các mốc trạng thái. Không phần nào phụ
   thuộc model.
2. **AI chỉ diễn đạt.** AI tóm tắt dòng thời gian thành vài câu, giải thích bước tiếp bằng lời thường,
   trả lời "giờ tôi làm gì", và đề nghị "để AI làm" nếu người dùng đã giao lệnh đó cho AI của mình (§4.1).
3. **Tắt AI thì phần tất định vẫn hiện đủ** (BR-AI-10). Tắt AI chỉ mất câu tóm tắt và nút "để AI làm".
4. **Hướng dẫn không thay phân quyền.** Cảnh báo không chặn. Chặn chỉ nằm ở lớp quyền và service
   (BR-PQ-12).

#### 4.7.1 Máy trạng thái từng loại chứng từ (đối chiếu code 2026-09-28)

| Chứng từ | Trạng thái (code) | Chuyển trạng thái → ai làm (quyền) | Điều kiện / hạn | `available_actions` hiện có? |
|---|---|---|---|---|
| **Phiếu nhập** `PurchaseReceipt` | DRAFT → SUBMITTED | `submit_receipt` → NV kho/Quản lý/Chủ (`add_purchasereceipt`); sinh 1 lô/dòng | Hạn dùng không được cao hơn mặc định (BR-MH-02). Sau đó cần Purchase Invoice trước khi chốt lô (BR-MH-04). **Chưa có đường huỷ phiếu nhập.** | Không |
| **Lô** `Batch` | DRAFT → SELLING → NEAR_EXPIRY → SOLD_OUT / EXPIRED → CANCELLED → CLOSED | `publish_batch` (Chủ/Quản lý theo `publish_batch`); NEAR_EXPIRY, SOLD_OUT, EXPIRED do Hệ thống (job `update_batch_statuses`); EXPIRED → CANCELLED (Chủ huỷ, hạch toán lỗ, BR-LO-03); → CLOSED `close_batch` (Chủ) | Cận hạn 14 ngày (tham số, BR-LO-06). Chốt: tồn = 0 hoặc Quá hạn/Huỷ, có Purchase Invoice, không còn đơn mở (BR-LO-04); kiểm kê trước chốt (BR-KK-05, PA). **Code chưa có service EXPIRED → CANCELLED; `close_batch` chưa kiểm "không còn đơn mở" và BR-KK-05** (🟢 Q-L6). | Không |
| **Đơn** `SalesOrder` | BOOKED → PAID → PROCESSING → COMPLETED; BOOKED → AUTO_CANCELLED; PAID/PROCESSING → CANCELLED | Thanh toán: Hệ thống (IPN) hoặc Chủ (`confirm_payment_manual`); tự huỷ: Hệ thống (TTL); huỷ đơn đã trả: Quản lý/Chủ (`cancel_paid_order`) khi phiếu giao chưa Đang giao/Hoàn tất; phiếu hoàn: Quản lý/Chủ (`create_refund`) khi còn tiền hoàn được | Giữ chỗ TTL 30 phút (`SALES_ORDER_TTL_MINUTES`) | **Có** (`confirm_payment`, `cancel`, `create_refund`) |
| **Hoá đơn** `SalesInvoice` | ISSUED / CANCELLED | Chỉ Hệ thống (BR-PQ-11) | — | Không cần (không ai thao tác tay) |
| **Phiếu giao** `DeliveryNote` | PREPARING → READY → DELIVERING → COMPLETED \| FAILED; FAILED → DELIVERING; CANCELLED (theo đơn) | `advance_status`/`mark_failed` → NV giao được gán (scope phiếu mình), Quản lý; `return_to_warehouse` (tạo phiếu hàng hoàn) khi FAILED/DELIVERING | COMPLETED không quay lui (BR-GH-05). Thất bại ≥ `DELIVERY_MAX_FAILED_ATTEMPTS` → cần Quản lý/Chủ quyết (BR-GH-04) | Không |
| **Hàng hoàn** `ReturnToStock` | DRAFT (PENDING) → APPROVED (RESTOCK / WRITE_OFF) | `apply_return` → Quản lý/Chủ (`approve_returntostock`); NV giao không tự nhập kho (BR-HV-02) | Về đúng lô gốc (BR-HV-01); ngưỡng thời gian ngoài chuỗi lạnh (tham số) | Không |
| **Phiếu hoàn** `Refund` | PENDING → REFUNDED \| FAILED; FAILED → PENDING (thử lại) | Tạo: Quản lý/Chủ; xác nhận/đánh thất bại/thử lại: Chủ (`confirm_refund`) | Bắt buộc mã GD (BR-HT-03). Hạn hoàn 30 ngày khi khách đơn phương chấm dứt hợp lệ (Luật BVQLNTD, memo §4) | **Có** (`confirm`, `mark_failed`, `retry`) |
| **Giao dịch lệch** `PaymentTransaction` | OPEN → RESOLVED (ATTACHED / CONFIRMED / REFUNDED) | Chủ (`confirm_payment_manual`); lập phiếu hoàn cần thêm `create_refund` | BR-TT-04/05/09/10/15 | **Có** (`attach_to_order`, `confirm_order`, `refund`) |
| **Kiểm kê** `StockReconciliation` | DRAFT → APPROVED | Nhập số: NV kho; duyệt `apply_reconciliation` → người có `approve_stockreconciliation`, **khác người nhập** (BR-KK-02) | Chênh dương phải có lý do (BR-KK-04) | Không |
| **Chi phí mua** `PurchaseCost` | Không có trạng thái (ghi nhận là xong) | `record_purchase_cost` → Chủ (`add_purchasecost`); cập nhật giá vốn lô | Lô đã chốt thì không thêm được (BR-LO-05) | Không |

Nhận xét: đã có **quy ước `available_actions`** (BE tính luật + quyền, FE chỉ đọc để hiện nút) cho
đơn, phiếu hoàn, giao dịch lệch và nhân viên. Tính năng này **mở rộng quy ước đó**, không phát minh
cơ chế mới. Hiện quy ước chỉ trả **bước được phép**; cần thêm **bước bị chặn kèm lý do**.

#### 4.7.2 Khối "Tiếp theo"

Với mỗi chứng từ và **người đang xem**, hệ thống trả danh sách bước. Mỗi bước gồm:

| Trường | Ý nghĩa | Ví dụ (lô SOLD_OUT, người xem là Quản lý) |
|---|---|---|
| Việc | Tên thao tác bằng lời thường | "Chốt lô" |
| Bạn làm được? | Có / Không | Không |
| Ai làm được | Group/vai có quyền (không nêu tên người) | "Chủ" |
| Còn thiếu | Điều kiện nghiệp vụ chưa đạt, lời thường | "Chưa có hoá đơn mua (Purchase Invoice)" |
| Hạn | Nếu có mốc thời gian | Đơn giữ chỗ: "tự huỷ lúc 10:42" |
| Vì sao | Câu lời thường gắn mã BR, soạn sẵn | "Lô chỉ chốt khi đã có hoá đơn mua, để giá vốn đủ căn cứ (BR-LO-04)" |
| Để AI làm | Chỉ hiện khi AI của người xem được giao lệnh này (§4.1) | "AI soạn nháp chốt lô" (mức C) |

Quy tắc:
- **Một nguồn duy nhất**: cùng một hàm tính cho màn ERP, cho AI và cho mọi kênh. Không để FE hay model
  tự suy luận bước tiếp.
- **Không nói nhiều hơn service kiểm**: bước "được phép" phải thực sự chạy được. Nếu service chưa kiểm
  một điều kiện trong spec (vd `close_batch` chưa kiểm "không còn đơn mở"), khối Tiếp theo không được
  hứa, phải báo Tech Lead sửa service (🟢 Q-L6).
- **Bước bị chặn vì quyền** vẫn hiện (để nhân viên biết phải nhờ ai), nhưng **lý do không được lộ số
  nhạy cảm**: nói "chưa có chi phí mua", không nói "chi phí 1.250.000đ". Người thiếu quyền xem giá vốn
  không thấy bước chỉ có ý nghĩa với giá vốn (vd "thêm chi phí mua") ngoài dòng "Chủ xử lý" (🟡 Q-M15).
- **Bước do Hệ thống làm** (tự huỷ TTL, cận hạn, xác nhận IPN) hiện dạng "Hệ thống sẽ…, lúc…".
- **Chứng từ liên quan**: đơn hiện luôn bước của phiếu giao, phiếu hoàn, giao dịch gắn với nó (🟡 Q-M16).

#### 4.7.3 Khối "Đã làm" (dòng thời gian)

- **Nguồn**: AuditLog (append-only) của chính chứng từ và chứng từ liên quan; các mốc trạng thái có
  sẵn (`created_at`, `completed_at`, `confirmed_at`, `closed_at`…); sổ kho `StockLedgerEntry` cho lô.
  Không tạo bảng lịch sử mới.
- **Mỗi dòng**: lúc nào, ai (người / Hệ thống / AI), làm gì, trạng thái trước → sau. Dòng do AI ghi
  hiện **"AI của <người cấp>"**, mức tự chủ, và (với Chủ) phiên bản cấu hình (BR-AI-08, BR-AI-20).
- **Lọc theo quyền người xem** (Tầng 3):
  - Chỉ thấy dòng thời gian của chứng từ mình đã được xem (NV giao: phiếu được gán cho mình).
  - **Field giá vốn, lãi lỗ bị lọc khỏi dòng** khi người xem thiếu `view_costprice`/`view_profitreport`.
    Ví dụ thật trong code: AuditLog `close_batch` ghi `landed_unit_cost` trong `changes`;
    `recompute_landed_cost` và `record_purchase_cost` cũng đổi giá vốn. Người thiếu quyền chỉ thấy
    "Chủ đã chốt lô", "Chủ ghi nhận chi phí mua", không có con số.
  - Không hiện tên, SĐT, địa chỉ khách (bất biến 9); nội dung chuyển khoản không hiện.
- **Hiện trạng**: endpoint nhật ký `GET /api/audit-logs/` đòi `view_auditlog` (chỉ Chủ, Quản lý). NV
  kho, NV giao hiện **không xem được** nhật ký. Dòng thời gian theo chứng từ là quyền xem mới, **giới
  hạn trong chứng từ họ đã xem được**, không mở toàn bộ nhật ký (🟡 Q-M17).

#### 4.7.4 Vai trò của AI

| Việc | Tất định (không AI) | AI thêm gì |
|---|---|---|
| Bước tiếp theo | Danh sách, ai, còn thiếu, hạn, câu "vì sao" soạn sẵn | Diễn đạt gọn cho người mới; trả lời câu hỏi "giờ tôi làm gì với đơn này" |
| Đã làm | Dòng thời gian đầy đủ | Tóm tắt 2–3 câu ("Đơn đã trả tiền lúc 9:10, đang soạn hàng, chưa ai nhận giao") |
| Để AI làm | — | Nút hiện theo cấu hình AI của tôi; bấm thì đi đường A/B/C như §4.1 |
| Cảnh báo | Luật bất thường tất định (bảng §4.7.5) | Giải thích cảnh báo |

**Ràng buộc đầu vào của AI**:
- Đầu vào duy nhất là **bước tiếp và dòng thời gian đã lọc theo quyền người xem**. AI không đọc thêm gì.
- **Không PII khách** (H2): dùng mã đơn, mã khách.
- **Tên nhân viên** cũng là dữ liệu cá nhân (Luật BVDLCN áp cho mọi cá nhân, không chỉ khách). Khi lên
  cloud thì thay bằng vai ("NV giao", "Chủ"); tên thật chỉ ghép lại trên UI (🟡 Q-M18).
- **Nếu câu tóm tắt lệch với dòng thời gian thì dòng thời gian là sự thật.** Câu tóm tắt luôn gắn nhãn
  AI (BR-AI-14) và nằm cạnh dòng thời gian thô.

**Chạy ở đâu** (router tĩnh, BR-AI-02):
- Hai lệnh mới đề xuất: `tom_tat_chung_tu` (tóm tắt "Đã làm") và `giai_thich_buoc_tiep` (diễn đạt
  "Tiếp theo"). Nhãn **`local`**: đầu vào ngắn (một chứng từ), không tốn trần cloud, không gửi tên nhân
  viên ra ngoài. Nhãn nhạy cảm theo loại chứng từ: lô, phiếu nhập, chi phí mua → `cao`; đơn, phiếu
  giao, phiếu hoàn → `trung_binh`.
- **Máy không có model** (chưa tải, không đủ RAM, iPhone, 4G): hiện bản không AI, tức dòng thời gian
  và câu "vì sao" soạn sẵn. Không đẩy lên cloud thay (BR-AI-02, BR-AI-16).
- Chi phí: 0 đồng cloud. Nếu sau này muốn chất lượng tốt hơn trên cloud thì là quyết định riêng (🟡 Q-M19).
- Đọc nên mặc định mức A (lệnh đọc, §4.1); người dùng tắt được.

#### 4.7.5 Hướng dẫn cho người mới và cảnh báo

- **"Vì sao"**: mỗi luật dùng trong khối Tiếp theo có **một câu lời thường soạn sẵn** gắn mã BR (vd
  BR-KK-02 → "Người đếm và người duyệt phải khác nhau, để số kiểm kê có người thứ hai soát"). Bảng câu
  này là tất định; AI chỉ được diễn đạt lại, không được bịa luật.
- **Cảnh báo bất thường** (không chặn, tất định). Ví dụ đề xuất (PA):
  - Chốt lô khi lô chưa có chi phí mua nào (có thể thiếu đá, xe).
  - Phiếu nhập có đơn giá lệch nhiều so với lô gần nhất cùng mặt hàng (chỉ hiện cho người có
    `view_costprice`; người khác chỉ thấy "đơn giá cần kiểm lại", không thấy số).
  - Kiểm kê chênh dương mà chưa có lý do (BR-KK-04).
  - Đơn giữ chỗ sắp hết TTL; phiếu hoàn chờ quá X ngày (gần hạn 30 ngày theo Luật BVQLNTD).
  - Phiếu giao thất bại đạt ngưỡng lần.
- **Thao tác trái quy trình bị chặn** thì chặn ở service như hiện nay (BusinessError kèm mã BR). Khối
  hướng dẫn chỉ giúp người dùng hiểu trước, không là lớp kiểm soát thứ hai. Ẩn nút không phải là phân
  quyền (BR-PQ-12).

#### 4.7.6 Use case

**UC-DW-07 Nhân viên mở một chứng từ và làm bước tiếp**
- **Tiền điều kiện**: đăng nhập; người dùng xem được chứng từ (Tầng 3).
- **Luồng chính**: 1) Mở màn chi tiết. 2) Khối "Tiếp theo" hiện bước hợp lệ, ai làm, còn thiếu, hạn,
  vì sao. 3) Khối "Đã làm" hiện dòng thời gian đã lọc; nếu có model thì kèm câu tóm tắt AI. 4) Người
  dùng bấm bước mình làm được → chạy thao tác như nút hiện nay; hoặc bấm "để AI làm" nếu được giao.
  5) Sau thao tác, hai khối tính lại.
- **Luồng thay thế**: AI tắt hoặc máy không có model → chỉ phần tất định. Bước người dùng không làm được
  → hiện "Chủ xử lý", có thể bấm "Nhờ" để tạo việc chuyển (§8) (🟡 Q-M20).
- **Ngoại lệ**: dữ liệu đổi giữa lúc xem và lúc bấm → service từ chối với mã BR, khối tính lại. Người
  dùng thiếu quyền gọi thẳng API → 403. Câu tóm tắt AI lỗi hoặc quá chậm → ẩn câu, giữ dòng thời gian.
- **Hậu điều kiện**: không có dữ liệu nào đổi chỉ vì xem. Chỉ thao tác mới ghi AuditLog.

**UC-DW-08 Hỏi AI "giờ tôi làm gì"**
- **Luồng chính**: người dùng hỏi trong khung chat trên màn chứng từ → AI nhận đúng khối Tiếp theo và
  Đã làm đã lọc → trả lời bằng lời thường, dẫn mã BR.
- **Ngoại lệ**: hỏi về chứng từ không có quyền xem → "không có quyền xem". Hỏi giá vốn khi thiếu quyền →
  context chưa từng chứa số đó (BR-AI-05).

## 5. Bảng 14 lệnh: trần mức được cấu hình và mặc định

| # | Lệnh | Quyền cần | **Trần mức** | **Mặc định** | Cần công tắc Chủ | Ghi chú trần |
|---|---|---|---|---|---|---|
| 1 | `nhap_lo` | `add_purchasereceipt` | **B** | C | Không | Chứng từ gốc của giá vốn (BR-MH-06). Không cho A để luôn có thông báo + hoàn tác. B cần có nghiệp vụ **huỷ phiếu nhập bằng trạng thái** (khi lô chưa publish, chưa bán) hoặc trì hoãn ghi. Memo khuyến nghị giữ một lần xác nhận; người dùng tự chọn. Chỉ K1 (người ra lệnh có mặt): AI không tự nghĩ ra phiếu nhập. |
| 2 | `tra_ton` | `view_batch` | A | A | Không | Đọc. |
| 3 | `tra_lo` | `view_batch` | A | A | Không | Đọc; giá vốn chỉ khi chủ AI có `view_costprice`. |
| 4 | `tra_hang` | `view_item` | A | A | Không | Đọc. |
| 5 | `tra_don` | `view_salesorder` | A | A | Không | Đọc; không PII. |
| 6 | `bao_cao_ton_kho` | `view_dashboard` | A | A | Không | Đọc, cloud, tính vào trần chi phí. |
| 7 | `bao_cao_lo` | `view_profitreport` | A | A | Không | Đọc, cloud. |
| 8 | `bao_cao_ky` | `view_profitreport` | A | A | Không | Đọc, cloud. |
| 9 | `chot_lo` | `close_batch` (chỉ `chu`) | **B, chỉ kiểu trì hoãn ghi** | C | **Có** | Không đảo ngược (BR-LO-05). Không có A. Xem §7.1. |
| 10 | `tao_phieu_hoan` | `create_refund` (`chu`, `quan_ly`) | **B** cho ca tất định; **C** cho ca phán đoán | C | Không | Ca tất định: số tiền tính chính xác từ dữ liệu (tiền về sau khi đơn tự huỷ BR-TT-05, chuyển thừa BR-TT-10). Ca phán đoán (khách đổi ý, hàng hỏng, hoàn một phần): trần C vì là quyết định ảnh hưởng khách (NĐ 356, sàn H9) và đảo doanh thu (BR-HT-06). |
| 11 | `xac_nhan_hoan` | `confirm_refund` (chỉ `chu`) | **B, chỉ kiểu trì hoãn ghi** | C | **Có** | V1 không có nguồn dữ liệu, bật cũng chuyển Chủ hết. Xem §7.2. |
| 12 | `xac_nhan_thanh_toan_tay` | `confirm_payment_manual` (chỉ `chu`) | **B, chỉ kiểu trì hoãn ghi** | C | **Có** | Chỉ ca khớp tuyệt đối trong hàng chờ giao dịch. Xem §7.3. |
| 13 | `kiem_ke` (draft) | `add_stockreconciliation` | **B** cho vai *nhập số*; **C** cho vai *duyệt* | C | Không | Nhập số chưa đổi tồn (BR-KK-02). Duyệt hạch toán hao hụt vào lô (BR-KK-03) và là "người duyệt" theo Luật Kế toán: trần C. Sàn H6. |
| 14 | `cap_nhat_giao` (draft) | `change_deliverynote` (scope phiếu mình) | **A** cho chuyển trạng thái trung gian; **B kiểu trì hoãn ghi** cho Hoàn tất / Giao thất bại | C | Không | Sự kiện vật lý; chỉ khi người giao ra lệnh (K1). Hoàn tất không quay lui (BR-GH-05). |

**"B kiểu trì hoãn ghi"**: AI xếp lịch ghi, trong N phút chưa có chứng từ nào đổi; người hoàn tác
được bằng cách huỷ lịch. Hết N phút thì ghi thật. Dùng cho lệnh không có trạng thái huỷ.

**Lệnh ngoài registry** (chưa có trong 14 lệnh, 🟢 Q-L1): `publish_batch`, `cancel_paid_order`,
`approve_returntostock`, duyệt kiểm kê, `record_purchase_cost`, đổi giá bán. Đề xuất mặc định khi
thêm: `cancel_paid_order`, `record_purchase_cost`, đổi giá bán có trần C (vùng đỏ theo memo §7).

## 6. Sàn cứng: cấu hình không vượt được

Các ràng buộc dưới đây đến từ bất biến dự án hoặc luật. Không mức cấu hình, không công tắc nào (kể cả
của Chủ) vượt được. Mỗi sàn phải có test.

| # | Sàn cứng | Nguồn |
|---|---|---|
| H1 | AI không vượt quyền chủ AI; quyền kiểm lại đủ 3 tầng ở server tại thời điểm thực thi. Không ai cấu hình được AI của người khác lên cao hơn quyền người đó. | BR-AI-04, BR-PQ-12 |
| H2 | **Dữ liệu cá nhân khách không vào prompt** model nào (local, cloud). Gồm cả `raw_payload` IPN, nội dung chuyển khoản, sao kê (tên người chuyển). Việc khớp giao dịch (§7.3) làm bằng **code tất định**, model không đọc nội dung. | Bất biến 9, BR-AI-09, Luật BVDLCN |
| H3 | **Không rò giá vốn**: nội dung AI gửi cho ai (thông báo, việc chuyển người, báo cáo) lọc theo quyền **người nhận**. | Bất biến 1, BR-AI-05 |
| H4 | **Chứng từ không xoá.** Hoàn tác chỉ bằng trì hoãn ghi hoặc huỷ bằng trạng thái. | Bất biến 3, BR-PQ-10, Luật Kế toán Đ.18 |
| H5 | **Nhật ký bắt buộc, append-only**: mọi việc AI làm (A/B/C, hoàn tác, rơi mức) và mọi thay đổi cấu hình. Không ghi được nhật ký thì không thực thi. | BR-PQ-04/05/06, BR-AI-08, memo §3 |
| H6 | **Kiểm kê: người nhập ≠ người duyệt.** AI của cùng một user không đóng cả hai vai. AI của A nhập thì người duyệt không được là A, cũng không được là AI của A. AI không được tính là "người thứ hai". Vai duyệt trần C. | BR-KK-02, decisions 2026-09-10 |
| H7 | **SalesOrder/SalesInvoice chỉ Hệ thống tạo.** AI không tạo đơn, không tạo hoá đơn. | BR-PQ-11 |
| H8 | **Trần chi phí cloud** 200.000đ/tháng: cảnh báo 80%, chặn 100%. Việc của AI dùng cloud cũng bị chặn; khi chặn thì rơi về C hoặc nhập tay. | BR-AI-11 |
| H9 | **Quyết định tự động ảnh hưởng khách** (huỷ đơn đã trả, số tiền hoàn theo phán đoán, từ chối hoàn…) trần C. Chỉ được mở khi chính sách quyền riêng tư đã nêu việc xử lý tự động, có giải thích quy tắc và có đường cho khách phản đối/không tham gia. | NĐ 356/2025, Luật BVDLCN, memo §6 |
| H10 | **Dữ liệu người ngoài không phải lệnh**: ghi chú khách, nội dung chuyển khoản chỉ là dữ liệu. AI mức A/B không dựa vào trường chữ tự do để quyết số tiền hay đối tượng (chống prompt injection). | PA, rủi ro mới |
| H11 | **AI không tự sửa cấu hình**, không tự nâng mức, không giao lại quyền cho AI khác. | PA |
| H12 | **Kill switch luôn thắng** cấu hình. | ADR 2.1, memo §3 |
| H13 | **Lệnh `local` không chạy trên cloud.** AI chạy nền (không có trình duyệt của người dùng) không chạy được lệnh `local`. | BR-AI-02, BR-AI-16 |
| H14 | **Không gửi dữ liệu ra ngoài ERP** (Zalo, SMS, email) khi Duy chưa duyệt kênh đó; AI không tự nhắn khách. | Bất biến 9, memo §2 (mất miễn gắn nhãn nội bộ) |
| H15 | **AI không chuyển tiền**, không gọi API ngân hàng. | decisions 2026-09-10; memo §1 (vùng xám QĐ 33) |
| H16 | Điều kiện nghiệp vụ gốc vẫn áp y nguyên: BR-LO-04 (chốt lô), BR-HT-03/04 (hoàn tiền), BR-TT-03/05/15 (thanh toán), BR-MH-02 (hạn dùng)… AI không có đường tắt. | Service hiện có |

**Sàn triển khai (điều kiện bật mức A/B cho lệnh ghi ở production)**, từ memo §10:

| # | Điều kiện | Nguồn |
|---|---|---|
| S-L1 | Hồ sơ phân loại rủi ro viết lại, mô tả đúng mức tự chủ, danh sách lệnh, trần, kill switch; thông báo Bộ KH&CN (hoặc phân loại lại + thông báo trong 15 ngày làm việc nếu đã nộp bản cũ). Kế toán/luật sư xác nhận điểm "người cấp làm người duyệt" (§4.3). | NĐ 142/2026, Luật Kế toán Đ.16 |
| S-L2 | Quy chế uỷ quyền nội bộ một trang (Lộc ký) và thoả thuận Duy–Lộc về trách nhiệm. | Memo §4, §9 |
| S-L3 | Quy trình sự cố AI (5 ngày làm việc sơ bộ, 15 ngày chính thức, 72 giờ khẩn cấp); đầu mối Lộc, dự phòng Duy. | NĐ 142 |
| S-L4 | Riêng vùng đỏ: thêm chính sách quyền riêng tư nêu xử lý tự động nếu lệnh ảnh hưởng khách (H9). | NĐ 356 |

Ở staging, dùng dữ liệu giả thì bật được để thử mà không cần S-L1…S-L4.

## 7. Ba lệnh vùng đỏ: khi Chủ bật công tắc, AI làm được gì

Ghi trung thực: **bật công tắc không cho AI thêm dữ liệu hay tay chân**. Nó chỉ cho phép AI tự ghi
những ca mà dữ liệu trong hệ thống đã đủ để quyết một cách tất định.

### 7.1 `chot_lo`

- **AI dựa vào**: điều kiện BR-LO-04 (tồn = 0 hoặc lô Quá hạn/Huỷ, đã có Purchase Invoice, không còn
  đơn mở tham chiếu lô), **cộng** các điều kiện sàn thêm (PA):
  - Đã có kiểm kê được duyệt sau lần xuất cuối (BR-KK-05: kiểm kê bắt buộc trước khi chốt lô).
  - Đã qua ít nhất **N ngày** kể từ khi tồn về 0 mà không có chi phí mua mới gắn vào lô (🟡 Q-M6: 7 ngày).
  - Không có phiếu hoàn, hàng hoàn chờ duyệt, hay giao dịch lệch nào liên quan lô.
- **Cách ghi**: B kiểu trì hoãn ghi (N phút), báo Chủ, Chủ huỷ được trong cửa sổ.
- **Vẫn không làm được → chuyển Chủ**: biết chi phí phụ (đá, xe) có còn về hay không; mọi lô chưa đủ
  điều kiện trên. Sau khi chốt thì không mở lại được (BR-LO-05).

### 7.2 `xac_nhan_hoan`

- **Muốn tự xác nhận, AI cần bằng chứng tiền đã rời tài khoản Lộc**: một giao dịch tiền **ra** có mã
  giao dịch, số tiền **đúng bằng** phiếu hoàn, và nhận diện được đúng phiếu.
- **Hiện trạng V1: không có nguồn nào như vậy.** SePay không có API chuyển tiền đi. Webhook ngân hàng
  SePay đang tắt (decisions 2026-09-26), và **chưa xác minh** SePay có báo giao dịch tiền ra hay không
  (🟢 Q-L3). Mã giao dịch chỉ có khi Lộc tự gõ vào, mà lúc đó chính Lộc đang xác nhận.
- **Kết luận**: bật công tắc ở V1 **không có tác dụng thực tế**. Mọi phiếu hoàn PENDING đều chuyển Chủ
  kèm việc cần làm: "chuyển X đ cho phiếu hoàn RF-…, rồi nhập mã giao dịch". AI không bao giờ tự gõ
  hoặc tự đoán mã giao dịch.
- **Mở được khi nào**: khi có nguồn tiền-ra máy đọc được. Khi đó việc khớp là code tất định (có thể
  là `system`, không cần model), và sàn H2/H10 vẫn áp.

### 7.3 `xac_nhan_thanh_toan_tay`

- **Tình huống gốc** (E-05): IPN không về, Chủ đối chiếu sao kê rồi xác nhận tay. Sao kê chỉ Lộc truy
  cập được (BR-TT-07). **AI không đọc được sao kê**; đưa sao kê vào prompt là vi phạm H2.
- **AI chỉ dựa vào giao dịch đã có trong hệ thống**: các `PaymentTransaction` trong hàng chờ lệch
  (`match_status = UNMATCHED`, `resolution_status = OPEN`). Tự xác nhận chỉ khi **khớp tuyệt đối tất
  cả**:
  1. Số tiền giao dịch **đúng bằng** tổng đơn (không thiếu, không thừa).
  2. Mã đơn nhận diện được trong giao dịch khớp **đúng một** đơn (khớp bằng code, model không đọc
     nội dung CK).
  3. Đơn đang **Giữ chỗ** (đơn đã tự huỷ → BR-TT-05 không tự khôi phục → chuyển Chủ).
  4. Mã giao dịch **chưa dùng** cho đơn nào (BR-TT-03); không có cờ nghi trùng (BR-TT-15).
  5. Môi trường giao dịch đúng môi trường đang chạy (BR-TT-14).
- **Cách ghi**: B kiểu trì hoãn ghi, báo Chủ, Chủ huỷ được trong cửa sổ.
- **Vẫn không làm được → chuyển Chủ**: giao dịch không có trong hệ thống (webhook/IPN không về, tức
  đúng ca E-05 gốc); tiền thiếu/thừa; khớp nhiều đơn hoặc không khớp đơn nào; đơn đã tự huỷ; có cờ
  nghi trùng. Nếu sau này dùng API tra cứu giao dịch của SePay qua adapter thì phải qua hồ sơ riêng
  (🟢 Q-L3).
- **Ghi chú BA**: ca khớp tuyệt đối là việc tất định. Tech Lead có thể làm thành job khớp của Hệ thống
  thay vì AI; khi đó nó ghi `system` và không cần công tắc vùng đỏ. Duy nên biết giá trị thật của
  việc "để AI làm" ở lệnh này là nhỏ.

## 8. Chuyển việc (escalate)

- **Khi nào** (điều kiện tất định, không dùng độ tự tin model để cho phép tự ghi — ADR §2.4):
  thiếu trường, sai schema, lỗi nghiệp vụ (BusinessError), vượt ngưỡng từng lần hoặc hạn mức ngày,
  khớp mơ hồ, lệnh ở mức C, cần dữ liệu AI không có (§7), kill switch bật, chạm trần chi phí cloud.
  Độ tự tin model chỉ được **thêm** lý do chuyển người.
- **Chuyển cho ai**: trước hết là **chủ AI** (người đã giao việc, đúng ý "escalate tới người dùng").
  Nếu việc cần quyền chủ AI không có thì chuyển Group có quyền: tiền và chốt lô tới `chu`; kho, giao,
  phiếu hoàn tới `quan_ly` rồi `chu`.
- **Kênh**: trong ERP (trung tâm thông báo S12). Không kênh ngoài (H14).
- **Quá hạn**: nhắc lại, rồi đẩy lên cấp trên. **Không bao giờ tự thực thi vì hết hạn** (im lặng không
  phải đồng ý).
- **Nội dung**: loại việc, mã chứng từ, việc cần làm, hạn; lọc theo quyền người nhận (H3), không PII
  (H2).

## 9. Use case

### UC-DW-01 Người dùng cấu hình AI của mình
- **Tiền điều kiện**: đăng nhập; AI bật (BR-AI-10).
- **Luồng chính**: 1) Mở "AI của tôi". 2) Hệ thống liệt kê lệnh **trong quyền hiện hành** của người
  đó, với mức hiện tại, trần, mặc định. 3) Người dùng chọn mức (≤ trần) và ngưỡng (≤ trần ngưỡng
  Chủ đặt). 4) Bấm lưu, khung xác nhận nêu rõ "bạn chịu trách nhiệm cho việc AI làm theo cấu hình
  này". 5) Sinh phiên bản cấu hình mới, ghi AuditLog, hiệu lực tức thì.
- **Luồng thay thế**: lệnh vùng đỏ khi công tắc Chủ đóng → hiện khoá, ghi "Chủ chưa mở". Người dùng
  chọn "Tắt" cho một lệnh → AI không dùng lệnh đó.
- **Ngoại lệ**: gửi mức vượt trần hoặc lệnh ngoài quyền (gọi API thẳng) → server từ chối (H1). Hai
  tab lưu cùng lúc → bản sau thành phiên bản mới, không ghi đè im lặng.
- **Hậu điều kiện**: phiên bản cấu hình mới có hiệu lực; lịch sử cũ còn nguyên.

### UC-DW-02 AI thực thi theo cấu hình (mức A/B)
- **Tiền điều kiện**: lệnh ở mức A hoặc B trong phiên bản cấu hình hiệu lực; không kill switch.
- **Luồng chính**: 1) Người dùng ra lệnh qua AI (nói/gõ). 2) AI điền args theo input schema.
  3) Server kiểm quyền hiệu lực (§4.2), sàn cứng (§6), ngưỡng, hạn mức ngày. 4) Đạt → ghi (A) hoặc
  ghi/xếp lịch ghi kèm nút Hoàn tác đếm ngược (B). 5) AuditLog ghi chủ AI, phiên bản cấu hình, mức.
- **Luồng thay thế**: một điều kiện ở bước 3 không đạt → rơi về C (khung xác nhận) kèm lý do.
- **Ngoại lệ**: bấm Hoàn tác trong N phút → huỷ bằng trạng thái hoặc bỏ lịch ghi, có AuditLog. Quá N
  phút → sửa theo quy trình tay. Cấu hình bị thu hồi khi đang chờ ghi → không ghi, về C. Mất mạng →
  không ghi hai lần (idempotent).
- **Hậu điều kiện**: chứng từ ghi người cấp là người thực hiện; có trong báo cáo cuối ngày.

### UC-DW-03 AI soạn nháp, người duyệt (mức C — mặc định)
- Y như UC-AI-03 của hồ sơ AI Native (propose → confirm, TTL nháp, khung xác nhận buộc tương tác
  BR-AI-14). Thêm: AuditLog ghi phiên bản cấu hình.

### UC-DW-04 Chủ mở vùng đỏ
- **Tiền điều kiện**: người dùng có quyền quản lý chính sách AI (mặc định `chu`).
- **Luồng chính**: 1) Chủ mở màn công tắc vùng đỏ. 2) Hệ thống hiện cho từng lệnh: AI làm được gì khi
  bật, phần vẫn không làm được, cảnh báo pháp lý ngắn (§7, memo). 3) Chủ bật một lệnh, đặt trần ngưỡng.
  4) Khung xác nhận buộc tương tác; ghi AuditLog và phiên bản chính sách.
- **Ngoại lệ**: người không phải Chủ gọi API bật → 403. Ở production khi S-L1…S-L4 chưa đủ → hiện cảnh
  báo (🟡 Q-M7: chặn hay chỉ cảnh báo).
- **Hậu điều kiện**: chủ AI có quyền tương ứng được phép cấu hình lệnh lên B. Tắt lại → mọi cấu hình
  lệnh đó về C ngay.

### UC-DW-05 Tắt khẩn
- **Luồng chính**: Chủ bấm tắt khẩn toàn cục, hoặc một người bấm tắt AI của mình, hoặc Chủ tắt AI của
  một người. Có hiệu lực tức thì; việc B đang chờ ghi bị huỷ; ghi AuditLog.
- **Hậu điều kiện**: hệ thống chạy như khi mọi lệnh ở C (hoặc AI tắt hẳn, BR-AI-10).

### UC-DW-06 Chuyển việc và báo cáo cuối ngày
- **Luồng chính**: việc AI không làm được → tạo việc chuyển (§8). Cuối ngày Chủ nhận báo cáo: AI của
  ai đã làm gì ở mức A/B, việc đã chuyển, việc quá hạn, số lần hoàn tác.
- **Ngoại lệ**: không ai xử lý → nhắc và đẩy cấp; không tự thực thi.

## 10. Business rule

Mã BR-AI-18/19/20 khớp với đề xuất của memo `01c-phap-ly.md` §9, đã chỉnh theo trả lời của Duy.

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| BR-AI-04 | Giữ nguyên: AI không bao giờ vượt quyền người dùng. Thêm: quyền hiệu lực = quyền hiện hành ∩ cấu hình ∩ trần ∩ công tắc, kiểm tại thời điểm thực thi. | D + D (Q1 28/09) | **Sửa** (làm rõ) |
| BR-AI-06 | ~~Tầng 2 luôn dừng ở bản nháp.~~ → Mỗi lệnh ghi có mức A/B/C do **chủ AI tự cấu hình** trong trần của lệnh. **Mặc định C.** | D (Q1 28/09) | **Sửa (lật ADR §2.6)** |
| BR-AI-07 | ~~AI không bao giờ tự `confirm_refund`, `confirm_payment_manual`, `close_batch`.~~ → Ba lệnh này **đóng mặc định**; chỉ Chủ mở bằng công tắc riêng từng lệnh; chỉ AI của người có quyền tương ứng được cấu hình; trần B kiểu trì hoãn ghi; chỉ ca khớp tuyệt đối theo §7. | D (Q2 28/09) | **Sửa (lật ADR §2.6)** |
| BR-AI-08 | Thêm: mọi thực thi và nháp của AI ghi **chủ AI (người cấp)** và **mã phiên bản cấu hình** đang hiệu lực, mức tự chủ, lý do rơi mức; hoàn tác ghi dòng riêng. Ngữ nghĩa Q6 giữ cho mức C. | D (Q3 28/09) + D (Q6 27/09) | **Sửa** |
| BR-AI-14 | Khung xác nhận buộc tương tác áp cho mức C, cho lưu cấu hình và cho bật vùng đỏ. Mức B: thông báo "AI đã ghi" + nút hoàn tác đếm ngược. Chứng từ do AI ghi phải nhận diện được. | PA | **Sửa** |
| BR-AI-18 | **Vùng đỏ**: `chot_lo`, `xac_nhan_hoan`, `xac_nhan_thanh_toan_tay` mặc định C; chỉ mở bằng công tắc Chủ (§4.6). Lệnh ngoài registry thuộc vùng đỏ theo memo (huỷ đơn đã trả, chi phí mua, đổi giá bán, duyệt kiểm kê) trần C tới khi Duy quyết riêng. | D (Q2) + PA | Mới |
| BR-AI-19 | **AI của tôi**: mỗi người dùng tự cấu hình mức A/B/C (hoặc Tắt) cho từng lệnh trong quyền của mình, ≤ trần của lệnh, ngưỡng ≤ trần ngưỡng của Chủ. Mặc định C cho lệnh ghi, A cho lệnh đọc. | D (Q1) + PA | Mới |
| BR-AI-20 | **Người cấp chịu trách nhiệm**: chủ AI chịu trách nhiệm cho việc AI làm theo cấu hình; vùng đỏ thêm Chủ chịu trách nhiệm mở vùng. Chứng từ ghi người cấp ở field người thực hiện; AuditLog ghi `actor_kind = ai`. | D (Q3) | Mới |
| BR-AI-21 | **Phiên bản cấu hình append-only**; đổi/thu hồi hiệu lực tức thì; việc B đang chờ ghi bị huỷ khi cấu hình bị thu hồi. | PA | Mới |
| BR-AI-22 | **Tắt khẩn**: toàn cục (Chủ) và theo user (chính người đó hoặc Chủ); tức thì; luôn thắng cấu hình. | D (Duy 27/09 "bật/tắt theo user") + PA | Mới |
| BR-AI-23 | **Sàn cứng** H1–H16 (§6) không cấu hình nào vượt được; mỗi sàn có test. | Bất biến + luật | Mới |
| BR-AI-24 | **Hoàn tác không xoá chứng từ**: B = huỷ bằng trạng thái hoặc trì hoãn ghi; lệnh không có trạng thái huỷ chỉ dùng trì hoãn ghi. | Bất biến 3 + PA | Mới |
| BR-AI-25 | **Chuyển việc** (§8): điều kiện tất định; chuyển chủ AI trước, rồi Group có quyền; trong ERP; quá hạn nhắc và đẩy cấp; không tự thực thi vì hết hạn. | PA | Mới |
| BR-AI-26 | **Báo cáo cuối ngày** cho Chủ về mọi việc AI làm ở A/B, việc chuyển, hoàn tác. | PA + memo §3 | Mới |
| BR-AI-27 | **Sàn triển khai**: không bật A/B cho lệnh ghi ở production khi S-L1…S-L4 chưa xong. | Luật (memo §10) | Mới |
| BR-AI-28 | **Bước tiếp tất định**: với mỗi chứng từ và người xem, danh sách bước tiếp tính từ máy trạng thái + quyền + điều kiện nghiệp vụ trong service; một nguồn duy nhất cho ERP, AI và mọi kênh; hiện đủ khi AI tắt (BR-AI-10). Mở rộng quy ước `available_actions` hiện có. | D (Duy 28/09) + PA | Mới |
| BR-AI-29 | **Bước bị chặn** hiện kèm ai làm được (theo vai) và điều kiện còn thiếu bằng lời thường; không lộ số giá vốn, lãi lỗ hay PII trong lý do. Bước "được phép" phải thực sự chạy được (không hứa nhiều hơn service kiểm). | PA | Mới |
| BR-AI-30 | **Dòng thời gian theo chứng từ** lấy từ AuditLog + mốc trạng thái + sổ kho; append-only; lọc theo quyền người xem (chứng từ trong scope, field giá vốn/lãi lỗ bị lọc); dòng AI hiện "AI của <người cấp>" + mức. | D (Duy 28/09) + bất biến 1, 3, 9 | Mới |
| BR-AI-31 | **Tóm tắt/diễn đạt bằng AI** chỉ nhận đầu vào là khối Tiếp theo và Đã làm đã lọc; không PII khách; tên nhân viên thay bằng vai khi lên cloud; gắn nhãn AI; dòng thời gian là sự thật khi lệch. | PA + BR-AI-05/09/14 | Mới |
| BR-AI-32 | **"Vì sao" soạn sẵn**: mỗi luật dùng trong hướng dẫn có một câu lời thường gắn mã BR, tất định; AI không được bịa luật. | PA | Mới |
| BR-AI-33 | **Cảnh báo không chặn**: cảnh báo bất thường là tất định và chỉ để nhắc; chặn chỉ ở lớp quyền và service (BR-PQ-12). | PA | Mới |
| BR-AI-34 | **"Để AI làm" theo cấu hình**: nút chỉ hiện khi AI của người xem được giao lệnh tương ứng, và chạy đúng mức đã cấu hình (A/B/C, §4.1). | D (Q1) + PA | Mới |
| BR-AI-02, 05, 09, 10, 11, 16 | Giữ nguyên. | D | Giữ |
| BR-PQ-07, 11 | Giữ. AI không phải Hệ thống; AI không tạo SalesOrder/SalesInvoice. | D | Giữ (làm rõ) |
| BR-KK-02 | Giữ. Thêm: AI của một user không đóng cả hai vai; AI không phải "người thứ hai". | PA | Giữ (làm rõ) |
| BR-TT-03/05/07/15, BR-HT-03/04/07, BR-LO-04/05 | Giữ. Là điều kiện AI phải qua, không có đường tắt (H16). BR-TT-07 hiểu lại: vẫn "chỉ Chủ" vì AI chỉ làm được thay AI của Chủ. | L/D | Giữ |

## 11. Tác động dữ liệu & tích hợp

Chỉ nêu cái gì; thiết kế là việc của Tech Lead. Lý do thêm dữ liệu ghi ở đây (bất biến 8).

- **Cấu hình AI theo user (MỚI)**: với mỗi user, mỗi lệnh: mức (Tắt/A/B/C), ngưỡng. Có **lịch sử phiên
  bản append-only** (ai đổi, khi nào, trước → sau). Lý do: BR-AI-19/20/21 cần truy "cấu hình nào đang
  hiệu lực lúc AI làm việc này".
- **Chính sách của Chủ (MỚI)**: công tắc vùng đỏ từng lệnh, trần ngưỡng từng lệnh, tắt khẩn toàn cục
  và theo user. Cũng có lịch sử phiên bản. Phải đổi được trên ERP, không cần deploy (registry vẫn là
  code theo ADR 2.5/V4; phần chỉnh được nằm ngoài registry).
- **Quyền Tầng 2 mới** (PA): quản lý chính sách AI (gán `chu`). Có thể cần quyền "tự cấu hình AI của
  mình" cho mọi Group (hoặc mặc định ai đăng nhập cũng có). Thêm qua migration gán quyền theo mẫu
  0002/0006/0007.
- **Registry**: thêm **trần mức** và kiểu hoàn tác (huỷ trạng thái / trì hoãn ghi) cho mỗi lệnh; đổi
  nghĩa `forbidden_channel` của 3 lệnh vùng đỏ thành "cần công tắc Chủ".
- **`AiProposal`** (02b §4.2, chưa xây): cần thêm trạng thái cho việc chờ ghi (B trì hoãn), đã tự ghi,
  đã hoàn tác, đã chuyển người, quá hạn — hoặc một hàng chờ việc riêng.
- **`AuditLog`**: đã có `actor_kind`/`ai_actor`/`proposal_ref`; cần ghi thêm mã phiên bản cấu hình và
  mức tự chủ.
- **Nghiệp vụ huỷ phiếu nhập** (mới, nếu mở B cho `nhap_lo` kiểu huỷ trạng thái).
- **Khớp giao dịch tuyệt đối** cho `xac_nhan_thanh_toan_tay` (§7.3): chạy trên dữ liệu `PaymentTransaction`
  sẵn có; không đọc `raw_payload` vào model.
- **Trung tâm thông báo** (S12): kênh cho việc chuyển người, thông báo B, báo cáo cuối ngày.
- **Bên thứ 3**: không thêm. Không kênh ngoài ERP (H14).
- **Hướng dẫn theo chứng từ (§4.7)**:
  - **"Tiếp theo" theo chứng từ**: mở rộng `available_actions` hiện có (đơn, phiếu hoàn, giao dịch lệch)
    sang lô, phiếu nhập, phiếu giao, hàng hoàn, kiểm kê; trả thêm bước bị chặn, ai làm được, còn thiếu,
    hạn, mã BR, lệnh AI tương ứng (nếu có). Tech Lead chọn một endpoint chung hay nhúng vào từng API chi tiết.
  - **"Đã làm" theo chứng từ**: đọc AuditLog theo chứng từ (và chứng từ liên quan), lọc theo quyền người
    xem. Quyền xem mới, giới hạn trong chứng từ người xem đã thấy được; **không** mở `view_auditlog`
    toàn bộ cho NV kho, NV giao. Có thể cần chỉ mục tra AuditLog theo chứng từ (Tech Lead).
  - **Bảng câu "vì sao"** theo mã BR: dữ liệu tĩnh trong code, không cần bảng DB.
  - **Registry**: thêm 2 lệnh đọc `tom_tat_chung_tu`, `giai_thich_buoc_tiep` (nhãn `local`, nhạy cảm
    theo loại chứng từ).
  - **Không thêm model mới** cho phần này.
  - **Service cần sửa trước** (phát hiện khi đối chiếu): `close_batch` chưa kiểm "không còn đơn mở" (BR-LO-04)
    và kiểm kê trước chốt (BR-KK-05); chưa có service huỷ lô quá hạn (EXPIRED → CANCELLED, BR-LO-03).

### 11.1 Giao diện cần có (mô tả nhu cầu, không thiết kế)

| Màn / thành phần | Ai dùng | Nội dung |
|---|---|---|
| **AI của tôi** | Mọi user | Danh sách lệnh trong quyền mình; mức hiện tại, trần, mặc định; chọn mức + ngưỡng; nút **Tắt AI của tôi**; lịch sử phiên bản cấu hình của mình; câu nhắc "bạn chịu trách nhiệm". |
| **Chính sách AI** | Chủ | Công tắc vùng đỏ từng lệnh (kèm giải thích §7 và cảnh báo pháp lý); trần ngưỡng; tắt khẩn toàn cục; tắt AI của từng người; xem cấu hình AI của từng người; lịch sử phiên bản. |
| **Thông báo "AI đã ghi" + Hoàn tác** | Chủ AI | Hiện ngay sau khi AI ghi mức B, đếm ngược N phút. |
| **Khung xác nhận mức C** | Chủ AI | Như S02/S10 hiện tại. |
| **Việc được chuyển** | Người nhận | Trong trung tâm thông báo S12; lọc theo quyền người nhận. |
| **Báo cáo AI cuối ngày** | Chủ | Việc A/B, hoàn tác, việc chuyển, quá hạn. |
| **Nhãn AI trên chứng từ** | Mọi người xem chứng từ | Nhận diện chứng từ do AI ghi (BR-AI-14). |
| **Khối "Tiếp theo"** trên màn chi tiết mọi chứng từ | Mọi user | Bước làm được (nút), bước bị chặn (ai làm, còn thiếu), hạn, "vì sao", cảnh báo; nút "để AI làm" nếu được giao. Thay cho các nút rời rạc hiện nay. |
| **Khối "Đã làm"** trên màn chi tiết | Mọi user (lọc theo quyền) | Dòng thời gian; câu tóm tắt AI (nếu có model) nằm trên, gắn nhãn AI. |

Ghi chú: nhiều màn chi tiết còn là placeholder (mua hàng S07/S28, kiểm kê S34, giao hàng S17/S20). Hai
khối đi kèm khi các màn đó được xây; màn đã có (đơn, phiếu hoàn, giao dịch lệch, tồn kho/lô) làm trước.

## 12. Rủi ro Cá Về

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Nhân viên đặt mức A/B quá thoáng cho `nhap_lo`, giá mua sai lọt vào giá vốn | Cao | Trần B (luôn có hoàn tác); trần ngưỡng do Chủ đặt; báo cáo cuối ngày; sai sót phải sửa trước chốt lô (memo §7) |
| Doanh thu khống qua `xac_nhan_thanh_toan_tay` | Cao | Chỉ AI của Chủ; chỉ ca khớp tuyệt đối trong hàng chờ; trì hoãn ghi; BR-PQ-11 giữ |
| Sổ ghi "đã hoàn" khi tiền chưa đi | Cao | V1 AI không có nguồn → không tự xác nhận; không tự gõ mã GD |
| Chốt lô sớm, mất chi phí phụ về sau | Cao | Điều kiện thêm N ngày không có chi phí mới + kiểm kê đã duyệt; trì hoãn ghi |
| Rò giá vốn qua thông báo / việc chuyển | Cao | H3: lọc theo quyền người nhận |
| Rò PII qua prompt khi khớp giao dịch | Critical | H2: khớp bằng code; model không đọc `raw_payload` |
| Prompt injection từ nội dung chuyển khoản, ghi chú khách | Cao | H10 |
| Chứng từ AI "duyệt" bị coi không hợp lệ khi thanh tra (Luật Kế toán Đ.16) | Trung bình–Cao | Ghi người cấp làm người thực hiện; S-L1 xin kế toán/luật sư xác nhận; Duy đã chấp nhận rủi ro |
| Trách nhiệm dồn về Lộc (với khách) và Duy (với Lộc) | Trung bình | S-L2: quy chế uỷ quyền + thoả thuận Duy–Lộc trước production |
| Cấu hình cũ còn hiệu lực sau khi đổi Group | Trung bình | Kiểm quyền tại thời điểm thực thi (§4.2) |
| Chi phí cloud tăng khi AI tự làm nhiều | Trung bình | H8 |
| Hồ sơ phân loại mô tả sai mức tự chủ | Trung bình | S-L1 |
| Dòng thời gian lộ giá vốn cho người thiếu quyền (AuditLog `close_batch` có `landed_unit_cost`) | Cao | BR-AI-30: lọc field theo quyền người xem; test bằng token từng Group (BR-PQ-13) |
| Mở nhật ký cho NV kho, NV giao làm lộ chứng từ ngoài scope | Trung bình | Chỉ dòng thời gian của chứng từ người đó đã xem được, không mở `view_auditlog` |
| Khối Tiếp theo hứa bước mà service không kiểm (vd `close_batch` thiếu kiểm đơn mở) | Trung bình | BR-AI-29; sửa service trước (Q-L6) |
| AI tóm tắt sai, người mới tin theo | Trung bình | BR-AI-31: dòng thời gian thô là sự thật, nằm cạnh; AI chỉ nhận đầu vào đã lọc |
| Tên nhân viên lên cloud nước ngoài | Trung bình | BR-AI-31: thay bằng vai; mặc định chạy local |

## 13. Phân đoạn thực hiện (đề xuất cho PO)

- **Đoạn H0 — Hướng dẫn tất định, không cần AI** (làm được ngay, song song hoặc trước đoạn 0; không
  phụ thuộc model, không phụ thuộc pháp lý AI):
  khối "Tiếp theo" (mở rộng `available_actions`, thêm bước bị chặn + lý do + hạn + "vì sao") và khối
  "Đã làm" (dòng thời gian lọc quyền) trên các màn đã có: đơn, phiếu hoàn, giao dịch lệch, lô. Sửa
  `close_batch` cho khớp BR-LO-04 trước khi hiện bước chốt lô. Màn mới (mua hàng, kiểm kê, giao hàng)
  có hai khối ngay khi được xây. Lợi ích cho người mới có ngay cả khi AI tắt.
- **Đoạn H1 — AI diễn đạt** (sau S08 runtime on-device): `tom_tat_chung_tu`, `giai_thich_buoc_tiep`
  chạy local; máy không model hiện bản tất định.
- **Đoạn H2 — "Để AI làm"**: nút trên khối Tiếp theo nối với cấu hình AI của tôi (cần đoạn 0).
- **Đoạn 0 — Nền cấu hình, chưa ai tự ghi** (cùng Lô 2):
  S02 xây theo mức C như đã duyệt, cộng: trần mức trong registry; cấu hình AI theo user + phiên bản;
  chính sách Chủ + tắt khẩn (toàn cục, theo user); AuditLog ghi người cấp + phiên bản; màn **AI của
  tôi** (chỉ chọn Tắt/C cho lệnh ghi, A/Tắt cho lệnh đọc). Kết quả: hạ tầng xong, hành vi chưa đổi.
- **Đoạn 1 — Mở B/A cho lệnh vận hành rủi ro thấp**: `cap_nhat_giao` (khi S17 giao hàng xong),
  `kiem_ke` vai nhập số (khi S34 xong). Thông báo "AI đã ghi" + Hoàn tác; báo cáo cuối ngày; việc
  chuyển người qua S12.
- **Đoạn 2 — Mở B cho `nhap_lo`**: sau khi có nghiệp vụ huỷ phiếu nhập (hoặc trì hoãn ghi) và trần
  ngưỡng Chủ. Mở B cho ca tất định của `tao_phieu_hoan`.
- **Đoạn 3 — Vùng đỏ**: màn công tắc vùng đỏ của Chủ; `chot_lo` và `xac_nhan_thanh_toan_tay` theo §7
  (B trì hoãn ghi, khớp tuyệt đối). `xac_nhan_hoan`: chỉ làm phần chuyển việc, vì V1 không có nguồn.
- **Xuyên suốt**: sàn cứng H1–H16 có test từ đoạn 0. Production chỉ bật A/B khi đủ S-L1…S-L4
  (BR-AI-27); staging dùng dữ liệu giả bật được sớm.
- **Để sau**: AI chạy nền khi chủ AI không đăng nhập (🟡 Q-M4); lệnh ngoài registry (🟢 Q-L1).

## 14. Ngoài phạm vi

- AI chuyển tiền, gọi API ngân hàng (H15).
- AI tạo SalesOrder/SalesInvoice, tạo đơn từ email (H7).
- AI tự nhắn khách hoặc gửi dữ liệu ra kênh ngoài ERP (H14).
- Người dùng cấu hình AI của **người khác** (trừ Chủ tắt khẩn / đặt trần).
- AI đọc sao kê ngân hàng.
- Phân loại chi tiết các lệnh ngoài registry.

## 15. Câu hỏi mở

### 🔴 Chặn

Không còn. Q1–Q3 Duy đã trả lời; Q4 đã được memo `01c-phap-ly.md` trả lời. Phần bổ sung §4.7 không
phát sinh câu hỏi chặn: mọi điểm mở đều có mặc định an toàn (Q-M15…Q-M20).

### 🟡 Có mặc định (Duy lật được)

| # | Câu hỏi | Mặc định PA |
|---|---|---|
| Q-M1 | Lệnh đọc (tra cứu, báo cáo) có nằm trong cấu hình "mặc định C" không? | Không: lệnh đọc mặc định A (như hiện nay), người dùng chỉ tắt được. "Mặc định C" áp cho lệnh ghi. |
| Q-M2 | Chủ có đặt trần cho cấu hình AI của nhân viên không? | Có: Chủ đặt trần ngưỡng (tiền, kg) từng lệnh; nhân viên chọn mức ≤ trần của lệnh và ngưỡng ≤ trần của Chủ. Chủ không đổi hộ cấu hình của nhân viên, chỉ tắt. |
| Q-M3 | Ai bấm tắt khẩn? | Toàn cục: Chủ (và Duy với vai quản trị). Theo user: chính người đó và Chủ. |
| Q-M4 | AI của một người có chạy khi người đó không đăng nhập (chạy nền) không? | Chưa, ở đoạn 0–3. AI chỉ làm khi chủ AI đang ra lệnh. Việc phát hiện nền (lô đủ điều kiện chốt, phiếu hoàn chờ, giao dịch lệch) do job Hệ thống làm rồi chuyển người. Lý do: chạy nền không dùng được model on-device (H13), tốn cloud (H8). |
| Q-M5 | Việc B đang chờ ghi khi cấu hình bị thu hồi | Không ghi, về C. |
| Q-M6 | Điều kiện thêm của `chot_lo` khi Chủ bật | Đã qua 7 ngày từ khi tồn = 0 không có chi phí mua mới; đã có kiểm kê được duyệt; không còn việc chờ liên quan lô. |
| Q-M7 | Production thiếu S-L1…S-L4 mà Chủ vẫn bật vùng đỏ / mức A/B | Chặn ở production (BR-AI-27), chỉ cho bật ở staging. |
| Q-M8 | Cửa sổ hoàn tác / trì hoãn ghi | 10 phút; vùng đỏ 30 phút. |
| Q-M9 | Trần ngưỡng khởi đầu `nhap_lo` | 200 kg và 30.000.000đ mỗi phiếu. Số giả định, chỉnh khi Lộc vận hành. |
| Q-M10 | Hạn mức ngày AI tự ghi | 20 lần/ngày mỗi lệnh mỗi người; vùng đỏ 10 lần/ngày. |
| Q-M11 | Kênh chuyển việc | Chỉ trong ERP (S12). |
| Q-M12 | Hạn xử lý việc chuyển | Việc khách chờ: 2 giờ rồi đẩy lên Chủ. Việc tiền: nhắc mỗi 12 giờ. Không tự thực thi vì hết hạn. |
| Q-M13 | Mức A cho lệnh ghi có được phép không? | Chỉ `cap_nhat_giao` trạng thái trung gian (theo bảng §5). Lệnh ghi khác trần B để luôn có thông báo + hoàn tác. |
| Q-M14 | Lưu cấu hình có cần khung xác nhận không? | Có, nêu rõ trách nhiệm (BR-AI-14, BR-AI-20). |
| Q-M15 | Người thiếu quyền giá vốn có thấy bước liên quan giá vốn (vd "thêm chi phí mua") không? | Thấy một dòng "Chủ xử lý: chi phí mua", không có số. |
| Q-M16 | Khối trên đơn có gộp bước và dòng thời gian của chứng từ liên quan (hoá đơn, phiếu giao, phiếu hoàn, giao dịch) không? | Có, gộp theo chuỗi đơn → hoá đơn → phiếu giao → phiếu hoàn; mỗi dòng ghi rõ thuộc chứng từ nào. |
| Q-M17 | NV kho, NV giao có được xem dòng thời gian (ai làm gì) không? | Có, chỉ trên chứng từ họ đã xem được; không mở nhật ký chung. |
| Q-M18 | Tên nhân viên trong câu tóm tắt AI | Local: dùng tên được. Cloud: thay bằng vai. |
| Q-M19 | Tóm tắt chạy local hay cloud? | Local (0 đồng, không gửi dữ liệu ra ngoài); máy không model hiện bản tất định. |
| Q-M20 | Bước người xem không làm được có nút "Nhờ" (tạo việc chuyển cho người có quyền) không? | Có, đi qua cơ chế chuyển việc §8, trong ERP. |

### 🟢 Để sau

| # | Câu hỏi |
|---|---|
| Q-L1 | Trần mức cho lệnh ngoài registry (`publish_batch`, `cancel_paid_order`, `approve_returntostock`, duyệt kiểm kê, `record_purchase_cost`, đổi giá bán). |
| Q-L2 | Đối chiếu BR-HT-06 (đảo doanh thu lúc tạo phiếu hoàn) với code (docstring `confirm_refund` nói phiếu REFUNDED mới là bút toán đảo). Làm rõ trước đoạn 2. |
| Q-L3 | SePay có báo giao dịch tiền ra, và API tra cứu giao dịch dùng được qua adapter không. Nếu có thì mới có nguồn cho `xac_nhan_hoan` và mở rộng `xac_nhan_thanh_toan_tay`. |
| Q-L4 | Kế toán/luật sư xác nhận "người cấp làm người duyệt" theo Luật Kế toán Đ.16 (memo §11 điểm 6) — thuộc S-L1. |
| Q-L5 | Định nghĩa "sự cố AI" cho quy trình báo cáo (S-L3). |
| Q-L6 | Lệch spec và code phát hiện khi đối chiếu máy trạng thái: `close_batch` chưa kiểm "không còn đơn mở" (BR-LO-04) và kiểm kê trước chốt (BR-KK-05, PA); chưa có service huỷ lô quá hạn EXPIRED → CANCELLED (BR-LO-03). Tech Lead xử lý ở đoạn H0 trước khi khối Tiếp theo hiện bước chốt/huỷ lô. |
