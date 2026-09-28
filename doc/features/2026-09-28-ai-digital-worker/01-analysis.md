# AI như "nhân viên số" (digital worker): tự thực thi, không làm được thì chuyển người — Phân tích nghiệp vụ
> BA · 2026-09-28 · Trạng thái: **CHỜ DUYỆT**
>
> **Đây là đề xuất LẬT quyết định đã chốt** (ADR 2.6/2.11 ngày 27/09, BR-AI-06, BR-AI-07). BA không
> tự lật: mọi thay đổi rule trong file này là **đề xuất chờ Duy duyệt**. `decisions.md` và ADR do
> Duy tự sửa sau khi chốt. Phần pháp lý chi tiết do `legal-vn` viết song song trong cùng thư mục;
> file này chỉ nêu điểm giao (§8.6).

## 1. Yêu cầu gốc

> "Chỉ tạo bản nháp, người bấm xác nhận mới ghi. Việc tiền và chốt lô thì AI không được đụng tới
> --> anh nghĩ là để AI tự làm cũng đc, coi AI như digital worker, cái nào ko làm đc thì escalate
> tới người dùng"

Nguồn: Duy (PO), 2026-09-28, phản hồi trên hai câu tóm tắt BR-AI-06 và BR-AI-07 của hồ sơ
`2026-09-27-ai-native-erp`.

## 2. Tóm tắt

**Chủ vựa và nhân viên** cần **AI tự thực thi những việc nó làm được như một nhân viên số, và tự
chuyển cho đúng người những việc nó không làm được**, để **bớt thao tác bấm xác nhận và bớt nút cổ
chai khi Lộc vắng** mà **không làm tiền rời túi sai, không ghi doanh thu khống, không đổi con số
lời lỗ âm thầm**.

Kết luận chính của BA:

1. **Hai trong ba việc "tiền và chốt lô" AI không làm được về mặt vật lý**, dù có bỏ luật cấm.
   `xac_nhan_hoan` cần một lệnh chuyển khoản từ app ngân hàng của Lộc, vì SePay không có API
   chuyển tiền đi (decisions 2026-09-10). `xac_nhan_thanh_toan_tay` cần đối chiếu sao kê mà chỉ Lộc
   truy cập được (BR-TT-07). Lật BR-AI-07 cho hai lệnh này không giúp AI làm thêm được gì, chỉ mở
   thêm lỗ hổng. Cách đúng với tinh thần "digital worker" là AI **chuẩn bị việc rồi chuyển Chủ**.
2. **`chot_lo` AI có đủ dữ liệu để kiểm điều kiện, nhưng hậu quả không đảo ngược** (BR-LO-05: lô
   đã chốt khoá vĩnh viễn). AI cũng không biết chi phí phụ (đá, xe) còn về nữa hay không (decisions
   2026-09-10: giá vốn hồi tố). Đề xuất: cho AI **đề xuất** chốt lô (hiện đang cấm cả việc sinh
   nháp) nhưng Chủ vẫn là người bấm.
3. **Giá trị thật của yêu cầu nằm ở chỗ khác**: bỏ khung xác nhận cho các lệnh ghi rủi ro thấp khi
   **chính người dùng ra lệnh qua AI** (nhập lô bằng giọng, nhập số kiểm kê, cập nhật giao), thay
   bằng "ghi ngay, hoàn tác được trong N phút", và cho AI **chạy nền phát hiện việc rồi chuyển
   người** (lô đủ điều kiện chốt, phiếu hoàn chờ chuyển khoản, tiền về sau khi đơn đã huỷ).
4. **AI chạy nền không có người đăng nhập** nên không chạy được model on-device (model nằm trong
   trình duyệt của nhân viên). Việc nền phải chạy trên server, tức là dùng cloud (trần 200.000đ/tháng)
   hoặc job tất định không cần model. Phần lớn việc "phát hiện rồi chuyển người" giải được bằng job
   tất định rẻ và test được, AI chỉ soạn lời nhắn.

## 3. Bối cảnh trong hệ thống

- **Quy trình bị ảnh hưởng**: không thêm quy trình mới. Đổi *cách thực thi* của P-02 (nhập lô),
  P-04 (chốt lô), P-05 (xác nhận thanh toán tay), P-06 (cập nhật giao), P-07 (phiếu hoàn), P-09
  (kiểm kê).
- **Rule hiện có bị đụng**: BR-AI-04, 06, 07, 08, 14 (hồ sơ AI Native §7); BR-PQ-04, 07, 11
  (phân quyền); BR-TT-05, 07; BR-HT-03, 06, 07; BR-LO-04, 05; BR-KK-02; BR-GH-05.
- **Quyết định ràng buộc**:
  - ADR AI Native 27/09 §2.6: "Hành động tầng 2 luôn cần người xác nhận. AI không bao giờ tự
    `confirm_refund`, `confirm_payment_manual`, `close_batch`." Trạng thái ADR: **ĐÃ CHỐT**.
  - ADR §2.11: phân loại **rủi ro trung bình** với lý do "đề xuất, không tự quyết"; human-in-the-loop.
  - ADR §2.4: router tĩnh, **không** dùng độ tự tin của model.
  - decisions 2026-09-10 (phân quyền): Quản lý được uỷ việc *làm khách phải chờ*; Chủ giữ việc
    *làm tiền rời túi hoặc đổi con số lời lỗ*; `confirm_payment_manual` không uỷ được vì phải đối
    chiếu sao kê; SalesOrder/SalesInvoice chỉ Hệ thống tạo.
  - decisions 2026-09-10 (hoàn tiền): SePay không có API hoàn tiền. Hoàn tiền là chuyển khoản tay
    trên app ngân hàng của Lộc, hệ thống chỉ ghi sổ.
  - decisions 2026-09-10 (landed cost): giá vốn hồi tố; chốt lô đông cứng lãi/lỗ; `close_batch`
    chỉ Chủ.
  - decisions 2026-09-10 (mặc định PA): kiểm kê, người nhập số và người duyệt phải khác nhau.
- **Bối cảnh vận hành**: Lộc chưa bán (decisions, lưu ý xuyên suốt). Chưa có dữ liệu thật nào để
  đo AI đúng sai bao nhiêu phần trăm. Mọi ngưỡng trong file này là **giả định (PA)**.

### 3.1 Hiện trạng code (đã kiểm tra 2026-09-28)

| Hạng mục | Hiện trạng | Nguồn |
|---|---|---|
| Registry 14 lệnh | 12 active, 2 draft (`kiem_ke`, `cap_nhat_giao`). `needs_confirmation=True` chỉ ở `nhap_lo`, `tao_phieu_hoan`, `kiem_ke`. `forbidden_channel="ai"` ở `chot_lo`, `xac_nhan_hoan`, `xac_nhan_thanh_toan_tay`. `handler=None` cho tất cả. | `backend/apps/ai/commands/registry.py` |
| Kênh execute/propose/confirm (S02), `AiProposal` | **Chưa làm** (Lô 2). Chỉ mới có catalog (S01) và AuditLog `actor_kind`/`ai_actor`/`proposal_ref` (S03). | `03-dev-notes.md`, `backend/apps/ai/README.md` |
| Agent chạy nền | **Không có.** Mô hình hiện tại: AI luôn chạy thay mặt người đang đăng nhập (BR-AI-04). | 01-analysis AI Native §5 |
| `close_batch` | Kiểm tồn = 0 (hoặc lô Quá hạn/Huỷ) và đã có Purchase Invoice rồi đổi trạng thái CLOSED. **Không có service mở lại lô.** | `inventory/batches/services.py` |
| `confirm_refund` | Bắt buộc `bank_txn_ref` (BR-HT-03). Chỉ đổi sổ, không chuyển tiền. | `sales/refunds/services.py` |
| `confirm_payment_manual` | Bắt buộc `bank_txn_id`, chạy chung đường ghi tiền với webhook. | `sales/payments/services.py` |
| Huỷ phiếu hoàn | Không có trạng thái "huỷ". Chỉ có `mark_refund_failed` (FAILED) và `retry_refund`. | `sales/refunds/services.py` |
| Huỷ phiếu nhập | **Không có service huỷ phiếu nhập.** `submit_receipt` sinh lô ở trạng thái Nháp (chưa lên Shop tới khi `publish_batch`, BR-MH-05). | `purchasing/receipts/services.py` |
| Trường chữ tự do do người ngoài nhập | `Customer.note`, nội dung chuyển khoản trong `PaymentTransaction` (IPN/sao kê, có thể chứa tên người chuyển). | `sales/models/*` |

**Hệ quả thời điểm**: S02 chưa xây nên đây là lúc rẻ nhất để đổi thiết kế kênh thực thi. Nếu Duy
chốt muộn hơn Lô 2 thì phải sửa lại ma trận chặn channel và contract S02.

## 4. Mô hình "nhân viên số" — hai trục phải tách

Yêu cầu của Duy trộn hai chuyện khác nhau về rủi ro. BA tách thành hai trục.

**Trục 1: ai khởi phát việc**

| Kiểu | Mô tả | Ví dụ |
|---|---|---|
| **K1. Người ra lệnh qua AI** | Người đang đăng nhập nói/gõ yêu cầu; AI chỉ là tay chân. Ý định là của người. | NV kho nói "nhập 50 ký mực, giá 120 nghìn, nhà cung cấp Tư". |
| **K2. AI tự khởi phát (chạy nền)** | Không ai ra lệnh. AI (hoặc job) tự phát hiện tình huống rồi tự làm hoặc chuyển người. | Đêm qua có tiền về cho một đơn đã tự huỷ; AI tự lập phiếu hoàn hoặc báo Chủ. |

**Trục 2: mức tự chủ** (theo khung Duy/điều phối viên gợi ý)

| Mức | Nghĩa | Người ở đâu trong vòng |
|---|---|---|
| **A** | AI tự làm, không cần ai | Không cần (chỉ đọc, hoặc việc không có hậu quả) |
| **B** | AI tự làm, báo ngay, cho hoàn tác trong N phút | Người **giám sát sau** (human-on-the-loop) |
| **C** | AI chuẩn bị, người duyệt rồi mới ghi (như BR-AI-06 hiện tại) | Người **duyệt trước** (human-in-the-loop) |
| **D** | AI không làm được (thiếu dữ liệu hoặc không có tay chân vật lý) → chuẩn bị việc và **chuyển người** | Người **làm** |

**Tiêu chí xếp mức** cho mỗi lệnh: (1) AI có nguồn sự thật để quyết không; (2) sai thì thiệt hại
bao nhiêu; (3) có đảo ngược được bằng trạng thái không (chứng từ không xoá — BR-PQ-10); (4) có đổi
giá vốn, lãi lỗ, doanh thu hoặc tiền không (ranh giới Chủ, decisions 2026-09-10).

**Lưu ý về "hoàn tác" ở Cá Về**: chứng từ không xoá được. Vì vậy "hoàn tác trong N phút" (mức B)
chỉ có hai cách hiểu hợp lệ về nghiệp vụ: (a) **trì hoãn ghi**, tức trong N phút chưa có chứng từ
thật nào được ghi; hoặc (b) **ghi rồi huỷ bằng trạng thái**, để lại dấu vết đầy đủ. Lệnh nào không
có trạng thái huỷ (vd phiếu nhập hiện chưa có service huỷ, phiếu giao đã Hoàn tất không quay lui
theo BR-GH-05) thì chỉ dùng được cách (a). Chọn cách nào là việc của Tech Lead; BA chỉ nêu ràng buộc.

## 5. Phân loại 14 lệnh

Cột "Hiện tại" lấy từ registry. Cột K1, K2 là **mức đề xuất (PA)**, chờ Duy duyệt.

| # | Lệnh | Hiện tại | **K1** (người ra lệnh qua AI) | **K2** (AI tự khởi phát) | Lý do |
|---|---|---|---|---|---|
| 1 | `nhap_lo` | Nháp, chờ xác nhận | **B** nếu đủ trường, mã hàng và nhà cung cấp khớp duy nhất, dưới ngưỡng kg/tiền. Vượt ngưỡng hoặc mơ hồ thì **C** | **D** | Số kg và giá mua là sự thật ở cảng, chỉ người có mặt biết; AI không tự nghĩ ra được một phiếu nhập. Sai giá mua làm sai giá vốn lô (BR-MH-06). Lô sinh ra ở trạng thái Nháp, chưa lên Shop (BR-MH-05) nên cửa sổ sửa sai có thật, **nhưng hiện chưa có service huỷ phiếu nhập** (§3.1). |
| 2 | `tra_ton` | Chạy ngay | **A** | **A** | Chỉ đọc, không có PII. |
| 3 | `tra_lo` | Chạy ngay | **A** | **A**, với điều kiện giá vốn chỉ lộ khi người nhận kết quả có `view_costprice` | Chỉ đọc. Rủi ro là rò giá vốn khi AI nền đọc bằng quyền rộng rồi gửi cho người quyền hẹp (§8.1). |
| 4 | `tra_hang` | Chạy ngay | **A** | **A** | Chỉ đọc, dữ liệu công khai. |
| 5 | `tra_don` | Chạy ngay | **A** | **A** | Chỉ đọc; không kèm tên, SĐT, địa chỉ (BR-AI-09). |
| 6 | `bao_cao_ton_kho` | Chạy ngay (cloud) | **A** | **A** | Dữ liệu gộp, nhãn thấp. |
| 7 | `bao_cao_lo` | Chạy ngay (cloud) | **A** | **A**, chỉ gửi cho người có `view_profitreport` (Chủ) | Chứa lãi lỗ. Đọc thì vô hại, gửi sai người là rò. |
| 8 | `bao_cao_ky` | Chạy ngay (cloud) | **A** | **A**, như trên | Như trên. |
| 9 | `chot_lo` | **Cấm kênh AI**, cấm cả sinh nháp | **C** | **D**: AI gom "lô đủ điều kiện chốt" rồi chuyển Chủ | Điều kiện BR-LO-04 kiểm được bằng dữ liệu, nhưng **không đảo ngược** (BR-LO-05, code không có mở lại lô) và AI không biết chi phí phụ còn về không (giá vốn hồi tố). Đổi con số lời lỗ vĩnh viễn nên thuộc ranh giới Chủ. |
| 10 | `tao_phieu_hoan` | Nháp, chờ xác nhận | **C** | **B** chỉ cho ca tất định: tiền về sau khi đơn đã tự huỷ (BR-TT-05, E-03), chuyển thừa. Ca khác **D** | Tạo phiếu hoàn chưa làm tiền rời túi (còn phải `confirm_refund`), nhưng **đảo doanh thu** (BR-HT-06). Với khách đổi ý hay hàng hỏng, số tiền và lý do là phán đoán, thông tin nằm ngoài hệ thống. Với ca tiền thừa, số tiền tính được chính xác từ dữ liệu. Hoàn tác được bằng trạng thái (hiện chỉ có FAILED, không có "huỷ"). |
| 11 | `xac_nhan_hoan` | **Cấm kênh AI** | **D** | **D**: AI lập danh sách "phiếu chờ chuyển khoản" rồi chuyển Chủ | Tiền rời túi thật. AI **không chuyển tiền được** (SePay không có API chuyển tiền đi) và **không có mã giao dịch** (BR-HT-03) cho tới khi Lộc chuyển xong trên app ngân hàng. |
| 12 | `xac_nhan_thanh_toan_tay` | **Cấm kênh AI** | **D** | **D**: AI báo đơn nghi đã trả tiền mà chưa có IPN rồi chuyển Chủ | Cần sao kê, **chỉ Lộc truy cập** (BR-TT-07). AI không có dữ liệu để quyết. Nếu làm sai thì ghi **doanh thu khống**. Thanh toán tự động đã là việc của Hệ thống qua IPN; lệnh tay này tồn tại chính vì tự động đã thất bại. |
| 13 | `kiem_ke` (draft) | Nháp, chờ xác nhận | **B** cho bước *nhập số đếm* (chưa đổi tồn sổ). **C** cho bước *duyệt*, và người duyệt phải khác người nhập | **D** | AI không đếm được cá. Nhập số chưa làm đổi tồn (BR-KK-02: chưa duyệt thì tồn sổ chưa đổi). Duyệt thì hạch toán hao hụt vào lô, làm giảm lãi (BR-KK-03). |
| 14 | `cap_nhat_giao` (draft) | Chạy ngay | **B** cho trạng thái trung gian (Chờ lấy → Đang giao). **B kiểu trì hoãn ghi** cho Hoàn tất và Giao thất bại | **D** | Giao hàng là sự kiện vật lý, chỉ người giao biết. Hoàn tất không quay lui (BR-GH-05) nên không có "huỷ bằng trạng thái"; muốn hoàn tác thì phải trì hoãn ghi. |

**Đếm nhanh**: A = 7 lệnh đọc/báo cáo (không đổi so với hiện nay). B = 3 lệnh ghi khi người ra
lệnh (`nhap_lo`, `kiem_ke` bước nhập, `cap_nhat_giao`) và 1 ca nền (`tao_phieu_hoan` tiền thừa).
C = `chot_lo`, `tao_phieu_hoan` (K1), `kiem_ke` bước duyệt. D = 2 lệnh tiền, cộng mọi lệnh ghi
khi AI tự khởi phát mà thiếu nguồn sự thật.

**Lệnh ngoài registry** mà một nhân viên số sẽ sớm cần (chưa phân loại, 🟢 để sau): `publish_batch`,
`cancel_paid_order`, `approve_returntostock`, duyệt kiểm kê, `record_purchase_cost`. Riêng
`record_purchase_cost` đổi giá vốn lô nên mặc định **C, chỉ Chủ**.

## 6. Tác nhân & quyền

### 6.1 Ba phương án danh tính cho AI

| Phương án | Mô tả | Được | Mất |
|---|---|---|---|
| **P1. Mượn quyền user** (hiện tại, BR-AI-04) | AI luôn chạy thay mặt người đang đăng nhập, đúng bằng quyền người đó | Đơn giản, đã có | **Không chạy nền được**: đêm không ai đăng nhập thì AI không có danh tính |
| **P2. Tài khoản AI riêng** | Một `User` riêng cho AI, thuộc một Group mới (vd `ai_worker`) với quyền hẹp do Chủ cấp. Mọi chứng từ AI tạo trỏ FK tới tài khoản này (PROTECT, BR-PQ-02) | Chạy nền được, truy vết rõ | Nếu cấp rộng thì AI vượt quyền người ra lệnh |
| **P3. Lai** (BA đề xuất) | K1: quyền hiệu lực = **giao** của quyền người ra lệnh và chính sách tự chủ của lệnh (không bao giờ là hợp). K2: dùng tài khoản AI riêng (P2), quyền hẹp | Giữ nguyên tinh thần BR-AI-04 cho K1, vẫn có danh tính cho K2 | Thêm một tài khoản và một Group; BR-PQ-08 (quyền gán qua Group) vẫn giữ |

### 6.2 Ai chịu trách nhiệm

- **K1**: người ra lệnh chịu trách nhiệm như khi tự bấm (PA). AuditLog ghi rõ đây là thực thi do AI
  làm theo lệnh của người đó.
- **K2**: người **bật tự chủ** cho lệnh đó (mặc định là Chủ) chịu trách nhiệm (PA). Mỗi dòng AuditLog
  phải truy được về quyết định bật tự chủ nào, của ai, lúc nào.
- AI **không phải** là "Hệ thống" theo BR-PQ-07 (Hệ thống là code tất định: job TTL, webhook). Việc
  do model quyết phải ghi `actor_kind = ai`, không được ghi là `system`. Đây là câu trả lời BA đề
  xuất cho câu hỏi mở cũ "AI agent có được coi là Hệ thống không": **không**. Hệ quả: BR-PQ-11 giữ
  nguyên, AI **không tạo SalesOrder/SalesInvoice** (chống doanh thu khống). Entry point "Agent
  Actions tạo đơn từ email" vẫn ngoài phạm vi.
- AI **không được tính là "người thứ hai"** cho quy tắc hai người khác nhau ở kiểm kê (BR-KK-02) (PA).

### 6.3 Bảng quyền

| Tác nhân | Group | Làm được gì với AI | Quyền Tầng 2 cần |
|---|---|---|---|
| Chủ (Lộc) | `chu` | Mọi lệnh theo mức §5; bật/tắt tự chủ từng lệnh; nhận mọi việc chuyển về tiền và chốt lô | Như hiện nay + quyền quản lý chính sách tự chủ (mới, PA) |
| Quản lý | `quan_ly` | K1 cho lệnh vận hành; nhận việc chuyển về kho, giao, phiếu hoàn | Như hiện nay |
| NV kho | `nv_kho` | K1 `nhap_lo`, `kiem_ke` (nhập số), tra cứu | Như hiện nay |
| NV giao | `nv_giao` | K1 `cap_nhat_giao` cho phiếu của mình, `tra_don` | Như hiện nay, scope phiếu mình |
| Tài khoản AI (P2/P3) | `ai_worker` (mới, PA) | K2: đọc, phát hiện, chuyển người; mức B cho ca đã được Chủ bật | Tối thiểu; **không bao giờ** có `confirm_refund`, `confirm_payment_manual`, `close_batch`, `manage_staff`, `view_costprice` (mặc định) |

## 7. Use case

### UC-DW-01 Người ra lệnh qua AI, AI tự ghi (mức B)
- **Tiền điều kiện**: AI bật (BR-AI-10); tự chủ mức B đã được Chủ bật cho lệnh này; người dùng có
  đủ quyền lệnh (BR-AI-04).
- **Luồng chính**:
  1. Người dùng nói/gõ yêu cầu (vd nhập lô bằng giọng).
  2. AI điền args theo input schema.
  3. Hệ thống kiểm điều kiện tự chủ tất định: đủ trường bắt buộc, khớp mã duy nhất, dưới ngưỡng
     từng lần và hạn mức ngày, không vi phạm rule nghiệp vụ.
  4. Đạt hết → ghi (hoặc xếp lịch ghi, theo cách hoàn tác §4). Màn hình hiện kết quả kèm nhãn
     "AI đã ghi" và nút **Hoàn tác** đếm ngược N phút (BR-AI-14 sửa).
  5. Ghi AuditLog: `actor_kind = ai`, người ra lệnh, lệnh, args, trước→sau, mức tự chủ.
- **Luồng thay thế**: bất kỳ điều kiện ở bước 3 không đạt → rơi xuống **mức C** (khung xác nhận như
  hiện tại), kèm lý do rơi mức.
- **Ngoại lệ**: người dùng bấm Hoàn tác trong N phút → huỷ bằng trạng thái hoặc bỏ lịch ghi, có
  AuditLog. Quá N phút → không hoàn tác từ AI được nữa, sửa theo quy trình tay thường. Mất mạng giữa
  chừng → không ghi hai lần (idempotent). Kill switch đang bật → không tự ghi, rơi về C.
- **Hậu điều kiện**: chứng từ đúng quyền người ra lệnh; AuditLog truy được AI, người, mức tự chủ,
  thời điểm; có mục trong báo cáo cuối ngày cho Chủ.

### UC-DW-02 AI chạy nền phát hiện việc và chuyển người (mức D)
- **Tiền điều kiện**: AI nền bật; tài khoản AI (P2/P3) tồn tại.
- **Luồng chính**:
  1. Theo lịch hoặc theo sự kiện, AI/job quét tình huống: lô đủ điều kiện chốt (BR-LO-04); phiếu
     hoàn PENDING quá X giờ; đơn nghi đã trả tiền mà chưa có IPN; tiền về sau khi đơn đã huỷ
     (BR-TT-05); lô cận hạn.
  2. Soạn **một việc chuyển người** gồm: loại việc, mã chứng từ, số liệu cần thiết (không PII, không
     giá vốn nếu người nhận không có quyền), việc cần làm, hạn xử lý.
  3. Gửi tới **Group có quyền làm việc đó**: tiền và chốt lô tới `chu`; phiếu hoàn, kho, giao tới
     `quan_ly` rồi `chu`.
  4. Người nhận xử lý bằng giao diện thường (vd Lộc chuyển khoản trên app ngân hàng, nhập mã GD trên
     ERP). Việc chuyển được đóng tự động khi chứng từ đổi trạng thái.
- **Ngoại lệ**: quá hạn không ai xử lý → nhắc lại, rồi đẩy lên cấp trên (Quản lý → Chủ). **Không
  bao giờ tự thực thi khi hết hạn** (im lặng không phải đồng ý). Chủ vắng dài ngày → việc tiền nằm
  chờ; đó là cố ý (decisions 2026-09-10: tiền không uỷ quyền). Trùng việc → gộp, không gửi hai lần.
- **Hậu điều kiện**: không chứng từ nào đổi trạng thái do AI; có dấu vết ai được giao, ai xử lý,
  mất bao lâu.

### UC-DW-03 AI nền tự làm việc tất định (mức B, K2) — ca tiền thừa
- **Tiền điều kiện**: Chủ đã bật tự chủ B cho ca này.
- **Luồng chính**: có giao dịch tiền vào cho đơn đã tự huỷ, hoặc chuyển thừa → tính số tiền phải
  hoàn từ dữ liệu → tạo phiếu hoàn PENDING (tiền chưa đi) → chuyển việc "chuyển khoản hoàn" cho Chủ
  (UC-DW-02) → Chủ vẫn `confirm_refund` bằng tay.
- **Ngoại lệ**: số tiền không xác định được duy nhất (vd một giao dịch khớp nhiều đơn) → D. Vượt
  ngưỡng tiền → D.
- **Ghi chú BA**: ca này **tất định**, không cần model. Tech Lead có thể làm như job Hệ thống;
  khi đó nó là `system` (BR-PQ-07), không phải AI. Duy cần biết điều này khi nghe "AI tự làm".

### UC-DW-04 Chủ đề xuất/điều khiển mức tự chủ và kill switch
- **Luồng chính**: Chủ xem danh sách lệnh với mức hiện hành; bật/tắt B cho từng lệnh, từng người
  dùng (Duy đã nói ngày 27/09: "bật/tắt agent theo từng user được"); đặt ngưỡng; bấm **dừng khẩn**
  làm mọi lệnh rơi về C/D ngay lập tức, không cần deploy.
- **Ngoại lệ**: AI **không được tự nâng mức tự chủ** hay tự sửa ngưỡng của chính nó. Người không
  phải Chủ không đổi được chính sách.
- **Hậu điều kiện**: mọi thay đổi chính sách ghi AuditLog.

### UC-DW-05 Chạy bóng (shadow) trước khi mở tự chủ
- **Luồng chính**: với lệnh sắp mở mức B, AI vẫn đi đường C (người xác nhận) nhưng hệ thống ghi lại
  "nếu tự làm thì AI đã ghi gì". Sau đủ số lần hoặc đủ thời gian, Chủ xem tỉ lệ khớp giữa AI và
  người sửa rồi quyết định mở B.
- **Lý do**: chưa có vận hành thật nên không có số đo độ đúng. Đây là cách duy nhất để có số trước
  khi bỏ người xác nhận.

## 8. Rủi ro Cá Về

### 8.1 Rò giá vốn
- AI nền (K2) đọc bằng tài khoản AI. Nếu tài khoản này có `view_costprice` và gửi kết quả cho Quản
  lý thì là rò (bất biến 1). Quy tắc đề xuất: **quyền của nội dung gửi đi = quyền của người nhận**,
  không phải quyền của AI. Mặc định tài khoản AI không có `view_costprice`.
- Việc chuyển về chốt lô gửi Chủ có thể kèm lãi/lỗ dự kiến; gửi Quản lý thì không.

### 8.2 Doanh thu khống
- Giữ BR-PQ-11 và BR-TT-07. AI không tạo đơn, không xác nhận thanh toán tay. Đây là hai đường duy
  nhất để có doanh thu mà không có tiền thật.

### 8.3 Tiền rời túi sai
- AI không có tay chân chuyển tiền (không có API chuyển tiền đi). Rủi ro thật là **ghi sổ "đã
  hoàn" khi tiền chưa đi** (`confirm_refund` sai) → khách không nhận tiền mà sổ báo đã trả. Giữ D.
- `tao_phieu_hoan` tự động đảo doanh thu (BR-HT-06). Nếu tự tạo sai, báo cáo kỳ bị sai cho tới khi
  phiếu bị đánh FAILED. **Quan sát phụ**: spec nói đảo lúc *tạo* phiếu, docstring `confirm_refund`
  nói phiếu REFUNDED mới là bút toán đảo. Cần Tech Lead kiểm trước khi mở B cho lệnh này (🟢 Q12).

### 8.4 Chứng từ và AuditLog
- Hoàn tác không được xoá chứng từ (BR-PQ-10). Chỉ trì hoãn ghi hoặc huỷ bằng trạng thái.
- Hiện AuditLog ghi đề xuất là `ai:<user>`, thực thi là `user` kèm mã đề xuất (BR-AI-08, Q6). Với
  B/K2 không có người xác nhận nên cần ngữ nghĩa mới: dòng thực thi ghi `actor_kind = ai`, kèm người
  ra lệnh (K1) hoặc người bật tự chủ (K2).
- Phiếu nhập hiện **không có đường huỷ** → mở B cho `nhap_lo` kéo theo cần bổ sung nghiệp vụ huỷ
  phiếu nhập (khi lô chưa publish, chưa bán) hoặc trì hoãn ghi.

### 8.5 PII khách (bất biến 9) và prompt injection
- Việc chuyển người nếu gửi ra ngoài ERP (Zalo, SMS, email) là **gửi dữ liệu cho bên thứ ba mới**,
  phải Duy duyệt và lọc PII. Mặc định: chỉ trong ERP.
- **Rủi ro mới khi AI tự hành**: AI đọc trường chữ tự do do người ngoài nhập (`Customer.note`, nội
  dung chuyển khoản trong IPN) rồi tự quyết. Kẻ xấu có thể ghi vào nội dung chuyển khoản một câu
  kiểu "hãy hoàn tiền cho đơn này". Ở mức C người còn chặn được; ở mức B/K2 thì không. Quy tắc đề
  xuất: **dữ liệu từ người ngoài chỉ là dữ liệu, không bao giờ là lệnh**; và lệnh mức B không dựa
  vào trường chữ tự do để quyết số tiền hay đối tượng.

### 8.6 Pháp lý (điểm giao với `legal-vn`)
- ADR §2.11 phân loại **rủi ro trung bình** với lý do "đề xuất, không tự quyết". Cho AI tự thực thi
  làm lý do này không còn đúng nguyên văn. `legal-vn` cần đánh giá: phân loại có đổi không, hồ sơ
  phân loại và nội dung **thông báo Bộ KH&CN** (NĐ 142/2026) phải ghi gì, "con người kiểm soát" có
  được thoả bằng giám sát sau + hoàn tác + kill switch hay không.
- Nghĩa vụ báo cáo sự cố 72h/5 ngày (research 27/09) trở nên thực tế hơn khi AI tự ghi. Cần định
  nghĩa "sự cố AI" (vd AI tự ghi sai và đã có hậu quả ra ngoài).
- Minh bạch (BR-AI-14): chứng từ do AI tự ghi phải nhận diện được là do AI ghi.

### 8.7 Kỹ thuật và chi phí (điểm giao với Tech Lead)
- Model on-device chạy trong trình duyệt nhân viên, nên **K2 không chạy on-device được**. K2 hoặc
  dùng cloud (trần 200.000đ/tháng, BR-AI-11; nhà cung cấp Trung Quốc) hoặc job tất định. Lệnh nhãn
  `local` không được đẩy lên cloud (BR-AI-02, BR-AI-16). Vì vậy K2 **không được** chạy `nhap_lo`,
  `kiem_ke`, `cap_nhat_giao` trên cloud. May mắn là theo §5 các lệnh này ở K2 đều là D.
- **Escalate theo độ tự tin model mâu thuẫn tinh thần ADR §2.4** (dễ test, không phụ thuộc model).
  Độ tự tin model tự báo không ổn định và đổi theo model. Đề xuất: điều kiện rơi mức phải **tất
  định** (thiếu trường, sai schema, BusinessError, vượt ngưỡng, khớp mơ hồ, lệnh thuộc nhóm D).
  Độ tự tin chỉ được dùng để **thêm** lý do chuyển người, không bao giờ để bớt.

## 9. Rào chắn thay cho "người xác nhận từng lần"

| # | Rào chắn | Nội dung nghiệp vụ | Nhãn |
|---|---|---|---|
| R1 | Mức tự chủ khai trên từng lệnh | Mặc định C; Chủ mới được nâng lên B; D là cứng, không nâng được | PA |
| R2 | Ngưỡng từng lần | vd `nhap_lo`: tổng kg và tổng tiền mỗi phiếu; `tao_phieu_hoan` (ca tiền thừa): số tiền tối đa | PA, số chờ Duy |
| R3 | Hạn mức ngày | Tổng số lần / tổng tiền AI tự ghi mỗi ngày; chạm hạn mức thì rơi về C | PA |
| R4 | Kill switch | Toàn cục (`AI_ENABLED` đã có), theo lệnh, theo người dùng; có hiệu lực ngay, không cần deploy | D (Duy 27/09 "bật/tắt theo user") + PA |
| R5 | Hoàn tác N phút | Trì hoãn ghi hoặc huỷ bằng trạng thái, không xoá | PA |
| R6 | AuditLog đầy đủ | Mức tự chủ, lý do rơi mức, người ra lệnh hoặc người bật tự chủ | D (BR-AI-08) + PA |
| R7 | Báo cáo cuối ngày cho Chủ | Danh sách việc AI tự làm, việc đã chuyển, việc quá hạn | PA |
| R8 | Chạy bóng trước khi mở B | Đủ N lần hoặc N ngày, tỉ lệ khớp ≥ ngưỡng thì Chủ mới mở | PA |
| R9 | AI không tự nâng quyền | Không tự sửa chính sách, ngưỡng, mức của chính nó | PA |
| R10 | Dữ liệu người ngoài không phải lệnh | Chống prompt injection (§8.5) | PA |
| R11 | Im lặng không phải đồng ý | Việc chuyển người quá hạn thì nhắc và đẩy cấp, không tự thực thi | PA |

## 10. Business rule

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| BR-AI-04 | AI không bao giờ vượt quyền. **K1**: quyền hiệu lực = giao của quyền người ra lệnh và chính sách tự chủ. **K2**: chạy bằng tài khoản AI riêng, quyền tối thiểu do Chủ cấp qua Group. Lớp lệnh phía server vẫn kiểm đủ 3 tầng. | D + PA | **Sửa** (thêm K2) |
| BR-AI-06 | ~~Hành động Tầng 2 luôn dừng ở bản nháp~~ → Mỗi lệnh ghi có **mức tự chủ** A/B/C/D. Mặc định C (như cũ). Chủ được nâng lên B cho lệnh không thuộc nhóm D. B = ghi ngay, báo ngay, hoàn tác được N phút. | PA, **lật D** | **Sửa (lật quyết định đã chốt)** |
| BR-AI-07 | `confirm_refund` và `confirm_payment_manual`: **giữ cấm thực thi** qua AI (D cứng), nhưng **cho phép AI chuẩn bị việc và chuyển Chủ** (hiện đang cấm cả sinh nháp). `close_batch`: **cho phép AI đề xuất (mức C)**, Chủ bấm; không bao giờ B. | PA, **lật một phần D** | **Sửa (lật một phần)** |
| BR-AI-08 | Thêm ngữ nghĩa: dòng thực thi mức B ghi `actor_kind = ai` kèm người ra lệnh (K1) hoặc người bật tự chủ (K2), mức tự chủ, lý do; dòng hoàn tác ghi riêng. | PA | **Sửa** |
| BR-AI-14 | Khung xác nhận buộc tương tác chỉ áp cho mức C. Mức B thay bằng thông báo "AI đã ghi" kèm nút hoàn tác đếm ngược. Mọi chứng từ do AI tự ghi phải nhận diện được là do AI. | PA | **Sửa** |
| BR-AI-02 | Giữ. Router tĩnh; việc nền K2 không được đẩy lệnh `local` lên cloud. | D | Giữ |
| BR-AI-09 | Giữ. Mở rộng áp cho nội dung việc chuyển người. | D | Giữ |
| BR-PQ-07 | Giữ. AI không phải "Hệ thống"; việc do model quyết ghi `ai`, không ghi `system`. | D | Giữ (làm rõ) |
| BR-PQ-11 | Giữ. AI không tạo SalesOrder/SalesInvoice. | D | Giữ |
| BR-TT-07, BR-HT-03, BR-HT-07 | Giữ nguyên. | L/D | Giữ |
| BR-KK-02 | Giữ. AI không được tính là người thứ hai. | PA | Giữ (làm rõ) |
| BR-AI-18 | **Hai trục**: phân biệt K1 (người ra lệnh) và K2 (AI tự khởi phát). Mức tự chủ khai riêng cho từng trục. | PA | Mới |
| BR-AI-19 | **Điều kiện rơi mức tất định**: thiếu trường, sai schema, lỗi nghiệp vụ, vượt ngưỡng từng lần hoặc hạn mức ngày, khớp mơ hồ, kill switch bật → rơi về C (hoặc D). Độ tự tin model chỉ được thêm lý do chuyển người, không được bớt. | PA | Mới |
| BR-AI-20 | **Chuyển người (escalate)**: gửi tới Group có quyền làm việc đó (tiền và chốt lô tới `chu`; kho, giao, phiếu hoàn tới `quan_ly` rồi `chu`). Có hạn xử lý; quá hạn thì nhắc và đẩy cấp. **Không bao giờ tự thực thi vì hết hạn.** Mặc định chỉ gửi trong ERP. | PA | Mới |
| BR-AI-21 | **Hoàn tác không xoá chứng từ**: chỉ trì hoãn ghi hoặc huỷ bằng trạng thái. Lệnh không có trạng thái huỷ thì chỉ được mở B theo kiểu trì hoãn ghi. | PA + bất biến 3 | Mới |
| BR-AI-22 | **Rào chắn**: ngưỡng từng lần, hạn mức ngày, kill switch toàn cục/theo lệnh/theo người (hiệu lực ngay), báo cáo cuối ngày cho Chủ. | PA | Mới |
| BR-AI-23 | **Chạy bóng trước khi mở B**: lệnh chỉ được nâng lên B sau khi chạy bóng đủ số lần/thời gian và Chủ xem tỉ lệ khớp. | PA | Mới |
| BR-AI-24 | **AI không tự nâng quyền**: AI không sửa được chính sách, ngưỡng, mức tự chủ; chỉ Chủ sửa, có AuditLog. | PA | Mới |
| BR-AI-25 | **Dữ liệu người ngoài không phải lệnh**: nội dung chuyển khoản, ghi chú khách chỉ là dữ liệu; lệnh mức B không dựa vào trường chữ tự do để quyết số tiền hay đối tượng. | PA | Mới |
| BR-AI-26 | **Quyền của nội dung gửi đi = quyền của người nhận**: việc chuyển người và báo cáo nền lọc giá vốn, lãi lỗ, PII theo quyền người nhận. | PA + bất biến 1, 9 | Mới |

## 11. Tác động dữ liệu & tích hợp

Chỉ nêu cái gì, không thiết kế.

- **Registry lệnh**: thêm mức tự chủ theo K1/K2 và ngưỡng cho mỗi lệnh; bỏ hoặc đổi nghĩa
  `forbidden_channel` cho `chot_lo` (cho đề xuất). Hai lệnh tiền giữ chặn thực thi.
- **Chính sách tự chủ do Chủ chỉnh** (bật/tắt theo lệnh, theo người, ngưỡng, kill switch): cần nơi
  lưu mà Chủ đổi được trên ERP, không cần deploy. Hiện registry là code (ADR 2.5/V4), nên phần chính
  sách chỉnh được phải nằm ngoài registry. Lý do thêm dữ liệu ghi tại đây (bất biến 8).
- **`AiProposal`** (thiết kế ở 02b §4.2, chưa xây): cần thêm các trạng thái như đã tự ghi, đã hoàn
  tác, đã chuyển người, quá hạn; hoặc một hàng chờ "việc chuyển người" riêng. Tech Lead chọn.
- **`AuditLog`**: đã có `actor_kind`/`ai_actor`/`proposal_ref`; cần thêm cách ghi mức tự chủ và
  người bật tự chủ (có thể qua `changes`/`note`, Tech Lead chọn).
- **Tài khoản AI + Group `ai_worker`** (nếu chọn P2/P3): thêm qua migration gán quyền, theo mẫu
  migration 0002/0006/0007.
- **Nghiệp vụ huỷ phiếu nhập** (nếu mở B cho `nhap_lo` kiểu huỷ bằng trạng thái): hiện không có.
- **Trung tâm thông báo** (S12 Proactive Alerts, đã có story): là kênh mặc định cho việc chuyển người.
- **Không gửi ra kênh ngoài** (Zalo, SMS, email) nếu Duy chưa duyệt. Nếu duyệt thì đó là bên thứ ba
  mới, phải đi qua adapter (decisions 2026-09-09) và lọc PII.
- **Story đã duyệt bị ảnh hưởng**: S02 (AC2, AC5, ma trận chặn channel), S10-AC2 (khung xác nhận voice),
  S12 (thêm việc chuyển người), 02b §2.2–2.3. **S02 chưa xây** nên đổi lúc này còn rẻ.
- **Tài liệu Duy tự sửa sau khi chốt**: `decisions.md` (thêm quyết định mới, ghi rõ lật ADR §2.6
  và một phần §2.11), ADR `00-adr-ai-native.md` (mục điều chỉnh).

## 12. Phân đoạn đề xuất (cho PO)

- **Đoạn 0 — Không đổi luật, chỉ thêm quan sát** (làm được ngay cùng Lô 2):
  xây S02 với mức C như đã thiết kế, nhưng registry có sẵn trường mức tự chủ (mặc định C); ghi dữ
  liệu chạy bóng. AI nền chỉ **phát hiện và chuyển người** (UC-DW-02, mức D). Không lệnh nào tự ghi.
  Đoạn này không lật quyết định nào ngoài việc cho AI chuẩn bị việc tiền/chốt lô.
- **Đoạn 1 — Mở B cho K1, rủi ro thấp**: `cap_nhat_giao` trạng thái trung gian, `kiem_ke` bước nhập
  số. Hai việc này không đổi tồn sổ và không đổi tiền. Điều kiện: chạy bóng đạt, có kill switch.
- **Đoạn 2 — Mở B cho `nhap_lo` K1** có ngưỡng, sau khi có nghiệp vụ huỷ phiếu nhập (hoặc trì hoãn
  ghi) và sau khi Lộc vận hành thật đủ lâu để có số chạy bóng. Mở B cho ca tiền thừa của
  `tao_phieu_hoan` (hoặc làm luôn thành job Hệ thống).
- **Đoạn 3 — Xem xét lại**: `chot_lo` vẫn C; hai lệnh tiền vẫn D. Chỉ mở lại khi có điều kiện mới
  (vd cổng thanh toán có API hoàn tiền, hoặc bật webhook ngân hàng cho phép đối chiếu tiền ra
  một cách tất định; khi đó việc đối chiếu là của Hệ thống, không phải AI).

Vì Lộc chưa bán, **đoạn 1 trở đi không có số đo thật để chứng minh AI đủ đúng**. BA khuyến nghị dừng
ở đoạn 0 cho tới go-live.

## 13. Ngoài phạm vi

- AI tự chuyển tiền (không khả thi: SePay không có API chuyển tiền đi).
- AI tạo SalesOrder/SalesInvoice, Agent Actions tạo đơn từ email (BR-PQ-11 giữ).
- AI tự đổi giá bán, tự giảm giá lô cận hạn (BR-LO-01: quyết định kinh doanh không để máy làm).
- AI tự quản lý nhân viên (`manage_staff`), tự sửa chính sách của chính nó.
- Gửi việc chuyển người ra kênh ngoài ERP (chờ Duy duyệt riêng).
- Phân loại chi tiết các lệnh ngoài registry 14 lệnh.

## 14. Câu hỏi mở

### 🔴 Chặn (phải có trả lời trước khi chuyển PO)

| # | Câu hỏi | Phương án | BA đề xuất |
|---|---|---|---|
| Q1 | "AI tự làm" nghĩa là gì trong giai đoạn này? | **(a)** Chỉ bỏ khung xác nhận khi **chính người dùng ra lệnh qua AI** (K1), thay bằng hoàn tác N phút. **(b)** Như (a), cộng thêm AI **chạy nền tự khởi phát** việc (K2), được tự ghi ở mức B. **(c)** AI nền chỉ phát hiện và chuyển người (K2 mức D), K1 giữ xác nhận như cũ. **(d)** Giữ nguyên BR-AI-06, không đổi. | **(c) ngay, (a) sau go-live** khi có số chạy bóng |
| Q2 | Ba lệnh "tiền và chốt lô" (BR-AI-07) xử lý thế nào? | **(a)** Giữ cấm hoàn toàn như hiện nay (AI không được sinh cả bản nháp). **(b)** Hai lệnh tiền: AI không thực thi, **được chuẩn bị việc và chuyển Chủ**; `chot_lo`: AI **được đề xuất**, Chủ bấm. **(c)** Mở cả ba theo mức tự chủ, Chủ tự bật khi muốn. | **(b)**. Lý do: hai lệnh tiền AI không có dữ liệu và không có tay chân để làm; `chot_lo` không đảo ngược được |
| Q3 | AI là ai trong hệ thống, và ai chịu trách nhiệm khi AI tự làm sai? | **(a)** Chỉ mượn quyền người đăng nhập (như hiện nay), không có AI chạy nền. **(b)** Tài khoản AI riêng, Group riêng, quyền hẹp; Chủ chịu trách nhiệm. **(c)** Lai: K1 dùng giao quyền người ra lệnh với chính sách, người ra lệnh chịu trách nhiệm; K2 dùng tài khoản AI riêng, người bật tự chủ (Chủ) chịu trách nhiệm. | **(c)** |
| Q4 | Anh có chấp nhận hệ quả pháp lý của việc đổi từ "AI đề xuất, người quyết" sang "AI tự làm, người giám sát" không? (Hồ sơ phân loại rủi ro và thông báo Bộ KH&CN phải ghi theo; chi tiết trong file của `legal-vn`.) | **(a)** Chấp nhận, cập nhật hồ sơ theo kết luận của `legal-vn`. **(b)** Chỉ mở tự chủ ở mức mà `legal-vn` xác nhận vẫn giữ nguyên phân loại rủi ro trung bình. **(c)** Hoãn mọi mức B tới sau khi đã nộp thông báo lần đầu. | **(b)** |

### 🟡 Có mặc định (Duy lật được)

| # | Câu hỏi | Mặc định PA |
|---|---|---|
| Q5 | Cửa sổ hoàn tác mức B | 10 phút |
| Q6 | Ngưỡng tự ghi `nhap_lo` (K1) | Tối đa 200 kg và 30.000.000đ mỗi phiếu; vượt thì rơi về C. Số giả định, phải chỉnh khi Lộc vận hành thật |
| Q7 | Hạn mức ngày cho việc AI tự ghi | 20 lần/ngày mỗi lệnh; chạm hạn mức thì rơi về C |
| Q8 | Kênh chuyển người | Chỉ trong ERP (trung tâm thông báo S12). Không Zalo/SMS/email |
| Q9 | Hạn xử lý việc chuyển người | Việc khách chờ (phiếu hoàn, giao): 2 giờ rồi đẩy lên Chủ. Việc tiền: nhắc mỗi 12 giờ, không tự làm |
| Q10 | Điều kiện mở B sau chạy bóng | Tối thiểu 50 lần chạy bóng và tỉ lệ AI khớp với người ≥ 95%; Chủ bấm mở |
| Q11 | Thời điểm với Lô 2 (S02) | Vẫn xây S02 theo mức C như đã duyệt, thêm sẵn trường mức tự chủ mặc định C; không chặn Lô 2 chờ quyết định này |
| G1 | AI có được tính là "người thứ hai" ở kiểm kê (BR-KK-02) | Không |
| G2 | AI có phải "Hệ thống" (BR-PQ-07/11) | Không. Việc do model quyết ghi `ai`; AI không tạo đơn |
| G3 | Tài khoản AI có `view_costprice` | Không |
| G4 | Độ tự tin model | Chỉ dùng để thêm lý do chuyển người, không dùng để cho phép tự ghi |

### 🟢 Để sau

| # | Câu hỏi |
|---|---|
| Q12 | Đối chiếu BR-HT-06 (đảo doanh thu lúc tạo phiếu hoàn) với code (docstring nói phiếu REFUNDED mới là bút toán đảo). Cần làm rõ trước khi cho AI tự tạo phiếu hoàn. |
| Q13 | Phân loại mức tự chủ cho các lệnh ngoài registry (`publish_batch`, `cancel_paid_order`, `approve_returntostock`, duyệt kiểm kê, `record_purchase_cost`). |
| Q14 | Nếu sau này bật webhook ngân hàng SePay và nó báo cả tiền ra, có cho Hệ thống (không phải AI) tự khớp `confirm_refund` theo mã giao dịch không. Cần kiểm chứng tài liệu SePay trước. |
| Q15 | Định nghĩa "sự cố AI" để báo cáo 72h/5 ngày (phối hợp `legal-vn`). |
