---
name: feature
description: Điều phối workflow đội dự án Cá Về (BA → PO → BE ∥ FE → QA → Review → Deploy) bằng các subagent ba-analyst, po-owner, be-dev, fe-dev, qa-tester. PHẢI dùng mỗi khi Duy nhờ bằng lời thường một việc làm thay đổi sản phẩm — thêm/sửa/bỏ chức năng, "Lộc muốn…", "khách phàn nàn…", sửa lỗi, đổi giao diện, đổi quy tắc nghiệp vụ, viết yêu cầu/story, test thử một luồng, deploy — kể cả khi không nhắc tới workflow hay tên agent. Không dùng cho câu hỏi thuần giải thích/tra cứu.
argument-hint: "<yêu cầu bằng lời thường>"
---

# Workflow đội dự án Cá Về

Yêu cầu: **$ARGUMENTS** (nếu trống: lấy từ tin nhắn gần nhất của Duy)

Duy chỉ nói bằng ngôn ngữ tự nhiên, không gõ lệnh. Việc đầu tiên là **nhận diện đúng
luồng** (bảng dưới), báo Duy **một dòng** luồng đã chọn — vd *"→ Luồng NHANH (sửa lỗi
FE): QA sẽ kiểm lại sau khi sửa"* — rồi chạy luôn. Duy nói khác thì đổi luồng.

## Nhận diện luồng

| Dấu hiệu trong lời Duy | Luồng | Bắt đầu từ |
|---|---|---|
| Chức năng mới; đổi quy trình/quy tắc nghiệp vụ (tiền, tồn kho, giá vốn, phân quyền, đơn hàng, hoàn tiền); "Lộc muốn…"; yêu cầu còn mơ hồ hoặc đụng nhiều màn hình | **ĐẦY ĐỦ** | Bước 1 (BA) |
| Lỗi/sai rõ ràng ("bị lỗi", "không chạy", "hiện sai"); chỉnh nhỏ đã rõ phải làm gì (đổi chữ, màu, bố cục, thêm 1 field hiển thị); không đổi quy tắc nghiệp vụ | **NHANH** | Luồng nhanh |
| "Phân tích…", "làm rõ yêu cầu…", "viết URD/spec…" | **CHỈ BA** | Bước 1, dừng sau điểm dừng 1 |
| "Viết story/backlog/tiêu chí nghiệm thu…" | **CHỈ PO** | Bước 2 (chạy BA trước nếu chưa có 01-analysis) |
| "Test thử / kiểm tra / QA … xem có lỗi không" | **CHỈ QA** | Bước 4, không tự sửa — báo lỗi rồi hỏi có sửa không |
| "Review code…", "kiểm tra bảo mật…" | **REVIEW** | Bước 5 |
| "Deploy / đưa lên / cập nhật bản thật" | **DEPLOY** | Bước 6 — xác nhận lại phạm vi trước khi chạy |
| Làm tiếp tính năng đang dở ("làm tiếp", "ok duyệt") | **TIẾP TỤC** | Đọc trạng thái trong `doc/features/<gần nhất>/` |

Quy tắc khi phân vân:
- Lỗi nhưng gốc là *quy tắc nghiệp vụ chưa rõ* (vd "tính lãi sai" mà không rõ công thức
  đúng) → nâng lên **ĐẦY ĐỦ**.
- Đụng giá vốn, tiền, phân quyền, xoá dữ liệu → không bao giờ bỏ qua QA.
- Câu hỏi thuần ("cái này chạy thế nào?", "đang có bao nhiêu test?") → **không** chạy
  workflow, trả lời trực tiếp.
- Việc hạ tầng/vận hành không đổi code sản phẩm (xem log, đổi mật khẩu, seed dữ liệu) →
  làm trực tiếp, không qua agent.

Bạn (luồng chính) là **điều phối viên**. Subagent không gọi được subagent khác, nên mọi
lượt giao việc đều đi qua bạn. Bạn không tự viết code nghiệp vụ — bạn giao việc, kiểm
kết quả, và giữ Duy trong vòng lặp. Ý tưởng lấy từ BMAD-METHOD (vai trò), GitHub Spec Kit
(spec → plan → tasks) và superpowers (subagent-driven development, verify before done).

## 0. Khởi tạo
- Tạo slug ngắn không dấu từ yêu cầu; thư mục `doc/features/<YYYY-MM-DD>-<slug>/`.
- Báo Duy 1 dòng: thư mục hồ sơ + các bước sắp chạy.

## 1. BA — phân tích
Giao `ba-analyst`: yêu cầu nguyên văn + đường dẫn thư mục hồ sơ.
➜ **ĐIỂM DỪNG 1**: đưa Duy tóm tắt + câu hỏi 🔴 (dùng AskUserQuestion nếu câu hỏi có
phương án rõ). Ghi câu trả lời vào `01-analysis.md`, đổi trạng thái `ĐÃ DUYỆT`.
Không có câu hỏi 🔴 và Duy đã nói "cứ làm" → đi tiếp, không cần dừng.

## 2. PO — story & AC
Giao `po-owner` (chế độ viết story).
➜ **ĐIỂM DỪNG 2**: đưa Duy bảng story (mã · tiêu đề · ưu tiên · BE/FE) + thứ tự làm. Duy
duyệt/cắt bớt → cập nhật `02-stories.md` thành `ĐÃ DUYỆT`.

## 3. BE ∥ FE — hiện thực
- Story `BE` → `be-dev`; story `FE` → `fe-dev`; story `BE+FE` → cả hai, **chạy song song
  trong cùng một lượt** (FE dùng mock theo contract trong story).
- Giao theo lô nhỏ (1–3 story/lượt) theo thứ tự PO đề xuất, không dồn cả backlog.
- Sau mỗi lượt: **tự kiểm** (skill `tdd-workflow` — cổng kiểm chứng): chạy lại
  `manage.py test` / `npm run build`, xem diff. Không tin báo cáo suông.
- Nếu contract BE thực tế lệch story → giao `fe-dev` chỉnh lại theo contract thật.

## 3b. UI review (khi lô có đổi giao diện)
Giao `fe-dev` một lượt **chỉ để soát và đánh bóng**:
- `impeccable audit` + `web-design-guidelines` (chấm điểm và liệt kê lỗi)
- `impeccable polish` + `emil-design-eng` (sửa chi tiết)
- `fixing-accessibility`

Theo "Cổng chất lượng UI" trong skill `caveve-ui`. Có ảnh trước và sau.

## 4. QA — kiểm thử
Giao `qa-tester` với danh sách story đã làm.
- **REJECTED** → giao lỗi chặn về đúng `be-dev`/`fe-dev` → QA lại. Tối đa **2 vòng**; quá
  2 vòng → dừng, báo Duy tình trạng + lỗi còn lại.
- **APPROVED** → sang bước 5.

## 4b. Commit & push (Duy yêu cầu)
Khi lô đã QA APPROVED:
1. Tự chạy lại test/build.
2. `git add -A`, rồi commit với message tiếng Việt có mã story. Cuối message thêm dòng Co-Authored-By.
3. `git push origin main`.

Trước khi push, kiểm `git status` không có `.env`, DB hay bí mật nào.

## 5. Review & nghiệm thu
- Chạy `/code-review` (hoặc `/security-review` nếu đụng phân quyền, thanh toán, webhook,
  giá vốn) trên phần đã đổi; sửa lỗi xác thực được qua `be-dev`/`fe-dev`.
- Giao `po-owner` (chế độ nghiệm thu) đối chiếu `04-qa-report.md` với AC.
- Rule nghiệp vụ mới/đổi → đề xuất cập nhật `doc/business-process-spec.md` (hỏi Duy trước
  khi sửa spec gốc).

## 6. Tổng kết & deploy
➜ **ĐIỂM DỪNG 3**: báo Duy: story xong · test (số liệu thật) · QA · review · việc còn nợ.
**Chỉ deploy khi Duy nói rõ** — Cloud Run `cangca-api` / Firebase `cangca-loc`,
`cangca-erp` (xem memory deploy). Có migration → nhắc chạy migrate trên Cloud SQL.

## Luồng nhanh
Cho bug nhỏ / chỉnh sửa rõ ràng, 1 story:
1. Tự viết 3–5 AC ngắn vào `doc/features/<ngày>-<slug>/02-stories.md` (bỏ bước BA),
   cho Duy xem trong 1 tin nhắn — không cần chờ nếu Duy đã nói "cứ làm".
2. `be-dev` và/hoặc `fe-dev` (TDD, test tái hiện bug trước).
3. `qa-tester` (chỉ AC + hồi quy app liên quan).
4. Tổng kết như bước 6.

## Nguyên tắc điều phối
- Mỗi lượt giao việc: nêu rõ đường dẫn hồ sơ, mã story, phạm vi file được sửa, đầu ra cần trả.
- Giữ chat ngắn: kết quả chi tiết nằm trong `doc/features/…`, chat chỉ tóm tắt + link file.
- Commit + push sau mỗi lô đã qua QA (bước 4b). Deploy chỉ làm khi Duy nói rõ.
