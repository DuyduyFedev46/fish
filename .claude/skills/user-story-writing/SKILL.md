---
name: user-story-writing
description: Viết user story + tiêu chí nghiệm thu (Given/When/Then) theo INVEST cho Cá Về, chia lát theo giá trị, gán ưu tiên và phạm vi. Dùng ở bước PO của workflow, khi chia tính năng thành backlog, hoặc khi cần tiêu chí nghiệm thu đủ rõ để QA viết test.
---

# Viết user story & tiêu chí nghiệm thu (PO)

Nguồn tham khảo: `user-stories`, `create-prd` (phuryn/pm-skills), `agile-product-owner`
(alirezarezvani/claude-skills). Viết lại cho Cá Về.

## Đầu vào
`01-analysis.md` đã được Duy duyệt. Không viết story từ yêu cầu chưa qua BA (trừ việc nhỏ
Duy nói bỏ qua BA).

## Quy tắc

- **3C**: Card (tiêu đề + 1 câu) · Conversation (ý đồ, bối cảnh) · Confirmation (AC).
- **INVEST**: độc lập, thương lượng được, có giá trị, ước lượng được, **nhỏ** (≤ 1–2 ngày
  làm), **test được**. Story quá to → chia theo lát dọc (một luồng chạy đủ BE→FE), không
  chia theo tầng ("làm model", "làm API").
- **Ngôn ngữ đời thường**, tiếng Việt; tác nhân dùng tên vai trò của vựa
  (Khách, Chủ vựa, Quản lý, NV kho, NV giao), không dùng "user".
- **AC dạng Given/When/Then**, mỗi AC kiểm được bằng 1 test tự động. Tối thiểu mỗi story có:
  1 luồng chính · 1 ngoại lệ/lỗi · 1 AC phân quyền (ai *không* được làm) · AC giá vốn nếu
  story đụng tới dữ liệu giá vốn/lãi lỗ.
- Mỗi AC ghi mã BR nó kiểm (nếu có). Gắn mã AC dạng `S2-AC3` để QA truy vết.
- **Ưu tiên MoSCoW** (Must/Should/Could/Won't) + lý do một dòng.
- **Definition of Done** chung (không lặp lại trong từng story): test BE xanh, FE build
  sạch, QA report APPROVED, không rò giá vốn, doc cập nhật nếu đổi rule.

## Mẫu đầu ra — `doc/features/<ngày>-<slug>/02-stories.md`

```md
# <Tên tính năng> — User stories
> PO · <ngày> · Nguồn: 01-analysis.md · Trạng thái: CHỜ DUYỆT / ĐÃ DUYỆT

## Mục tiêu & thước đo
<vì sao làm; đo thành công bằng gì>

## Phạm vi
Trong: … · Ngoài: …

## S1 — <tiêu đề>  · Must · BE+FE
**Là** <tác nhân>, **tôi muốn** <việc>, **để** <giá trị>.
Bối cảnh: <conversation ngắn, link UC-x>

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S1-AC1 | … | … | … | BR-BH-06 |
| S1-AC2 (lỗi) | … | … | … | |
| S1-AC3 (quyền) | NV giao đăng nhập | gọi … | nhận 403, không đổi dữ liệu | BR-PQ-… |

Ghi chú kỹ thuật cho dev (nếu có): API/màn hình dự kiến, không bắt buộc.

## Thứ tự làm đề xuất
S1 → S2 → …  (lý do)

## Rủi ro / phụ thuộc
```

Tự kiểm trước khi giao: mỗi UC trong 01-analysis có ít nhất 1 story phủ; mỗi ngoại lệ có AC;
không AC nào chứa chữ mơ hồ ("nhanh", "dễ dùng", "hợp lý") mà không có con số.
