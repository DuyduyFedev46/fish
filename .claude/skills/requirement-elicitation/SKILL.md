---
name: requirement-elicitation
description: Kỹ thuật BA để biến một yêu cầu mơ hồ ("thêm chức năng X", "Lộc muốn Y") thành bản phân tích nghiệp vụ rõ ràng — tác nhân, luồng chính/phụ, ngoại lệ, business rule, tác động dữ liệu, câu hỏi mở. Dùng ở bước BA của workflow, hoặc khi cần làm rõ/đối chiếu yêu cầu với doc/URD.md và business-process-spec.md.
---

# Khai thác & phân tích yêu cầu (BA)

Nguồn tham khảo: BMAD `bmad-agent-analyst` + `bmad-advanced-elicitation`
(bmad-code-org/BMAD-METHOD), `business-analyst` (wshobson/agents), use-case-writer
(phucnt-bazone-vietnam). Viết lại cho Cá Về.

## Nguyên tắc

- **Bằng chứng trước, suy luận sau.** Mỗi khẳng định gắn nguồn: `URD §x`, `BR-xx-nn`,
  `decisions.md <ngày>`, hoặc "Duy nói trong phiên này". Không có nguồn → là **giả định (PA)**.
- **Không thiết kế giải pháp kỹ thuật.** BA mô tả *cái gì* và *vì sao*; *làm thế nào* là
  việc của BE/FE.
- **Đối chiếu trước khi viết mới.** Tìm trong spec xem quy trình/rule đã tồn tại chưa —
  phần lớn yêu cầu là *sửa* một P-0x có sẵn, không phải quy trình mới.
- **Không tự lật quyết định đã chốt** trong `decisions.md`. Nếu yêu cầu mâu thuẫn → nêu
  rõ mâu thuẫn, đưa vào câu hỏi mở.

## Quy trình

1. **Tóm lại yêu cầu bằng một câu** theo mẫu: *[Tác nhân] cần [việc] để [giá trị]*.
2. **Định vị trong spec**: quy trình P-0x nào, BR nào liên quan, quyết định nào ràng buộc.
3. **Hỏi dồn 5 góc** (tự trả lời từ tài liệu trước; chỉ hỏi Duy điều tài liệu không có):
   - *Ai*: tác nhân nào (Khách / Chủ / Quản lý / NV kho / NV giao / Hệ thống)? Group nào có quyền?
   - *Khi nào*: sự kiện kích hoạt, trạng thái trước/sau (state machine đơn, vòng đời lô).
   - *Tiền*: có làm đổi giá vốn, lãi lỗ, tiền rời túi không? → thuộc quyền Chủ.
   - *Hàng*: có trừ/cộng tồn, ảnh hưởng FIFO, giữ chỗ, hạn dùng, chuỗi lạnh không?
   - *Sai thì sao*: huỷ, hoàn tiền, giao thất bại, trùng thao tác, mạng rớt, TTL hết.
4. **Kiểm tra rủi ro Cá Về** (skill `caveve-domain`): rò giá vốn? xoá chứng từ? thiếu AuditLog?
5. **Viết use case** cho mỗi luồng: tiền điều kiện → luồng chính (đánh số) → luồng thay thế
   → ngoại lệ → hậu điều kiện.
6. **Phân loại câu hỏi mở**: 🔴 chặn (không trả lời thì không làm được) / 🟡 có mặc định
   PA đề xuất (ghi rõ mặc định) / 🟢 để sau.

## Mẫu đầu ra — `doc/features/<ngày>-<slug>/01-analysis.md`

```md
# <Tên tính năng> — Phân tích nghiệp vụ
> BA · <ngày> · Trạng thái: NHÁP / CHỜ DUYỆT / ĐÃ DUYỆT

## 1. Yêu cầu gốc
<nguyên văn yêu cầu> — nguồn: <ai, khi nào>

## 2. Tóm tắt
<Tác nhân> cần <việc> để <giá trị>.

## 3. Bối cảnh trong hệ thống
- Quy trình: P-0x … · Rule hiện có: BR-… · Quyết định ràng buộc: decisions.md <ngày>

## 4. Tác nhân & quyền
| Tác nhân | Group | Làm được gì | Quyền Tầng 2 cần |

## 5. Use case
### UC-1 <tên>
- Tiền điều kiện · Luồng chính (1..n) · Luồng thay thế · Ngoại lệ · Hậu điều kiện

## 6. Business rule
| Mã | Nội dung | Nhãn (L/D/PA) | Mới / Sửa / Giữ |

## 7. Tác động dữ liệu & tích hợp
Model/field bị ảnh hưởng (không thiết kế chi tiết), API/màn hình liên quan, bên thứ 3.

## 8. Rủi ro Cá Về
Giá vốn · phân quyền · chứng từ/AuditLog · FIFO/tồn · tiền

## 9. Ngoài phạm vi

## 10. Câu hỏi mở
| # | Mức | Câu hỏi | Mặc định PA đề xuất |
```

Bản phân tích đạt khi: mọi luồng có ngoại lệ, mọi rule có nhãn nguồn, không còn câu hỏi 🔴
chưa được Duy trả lời trước khi chuyển sang PO.
