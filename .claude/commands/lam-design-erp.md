---
description: Tự chạy hết các lô "ERP theo design" (doc/features/2026-10-01-erp-theo-design) theo quy trình đội Claude
---

Bạn là **điều phối viên** (phiên chính) của dự án Cá Về. Làm theo `CLAUDE.md` gốc repo và skill `feature` ở luồng **TIẾP TỤC**.
Không hỏi lại những gì đã chốt trong hồ sơ. Chỉ dừng hỏi Duy ở **điểm dừng** ghi trong `02c-giao-viec.md`.

## Hồ sơ
- Thư mục: `doc/features/2026-10-01-erp-theo-design/`
- Đọc theo thứ tự: `01-analysis.md` → `02-stories.md` → `02b-tech-design.md` → `02c-giao-viec.md`.
- Thiết kế mẫu: `doc/design/erp/screens/*.dc.html`. Mở bằng trình duyệt để xem; với dev thì đọc HTML/inline style.
  Chi tiết bố cục ở `doc/design/erp/README.md`.
- Luật UI bắt buộc: `doc/design/erp/UI-RULES.md`. Bảng enum: `doc/design/erp/enum-map.md`.

## Vòng lặp: làm đến khi hết lô ☐ trong `02c-giao-viec.md`
1. `git checkout main && git pull`. Lấy **lô ☐ đầu tiên** (hoặc các lô ghi "song song" với nó). Chạy lệnh kiểm chứng của lô
   để ghi số gốc vào `03-dev-notes.md`.
2. Giao `be-dev` ∥ `fe-dev`. Chạy song song trong **cùng một lượt** khi lô ghi BE ∥ FE. Mỗi lượt giao kèm:
   - mã story và AC;
   - board thiết kế cần khớp;
   - danh sách file được sửa và không được đụng;
   - contract API trong 02b;
   - nhắc `fe-dev` đọc `UI-RULES.md` và skill `caveve-ui`.
3. **Tự chạy lại** lệnh kiểm chứng của lô (test BE, `npm ci && npm run build`, vitest/e2e). Không tin báo cáo suông.
4. Giao `techlead` review diff. Trọng tâm: giá vốn, dữ liệu cá nhân, phân quyền, migration, lệch 02b, lệch `UI-RULES.md`.
5. Giao `qa-tester` kiểm theo AC và từng mục `UI-RULES.md` áp dụng cho màn đó:
   - chạy thật, không PASS bằng đọc code;
   - có ca ngoài đường thuận, có ca phân quyền theo từng vai;
   - chụp ảnh màn đặt cạnh board thiết kế.
6. QA **REJECTED** → giao lại dev, quay về bước 3. Tối đa 2 vòng; quá 2 vòng thì dừng và báo Duy.
7. QA **APPROVED** → làm tiếp các việc sau:
   - kiểm `git status` không có `.env` hay bí mật;
   - commit tiếng Việt có mã lô và mã story, cuối có dòng Co-Authored-By;
   - `git push origin main`;
   - đánh ☑ lô đó trong `02c` (commit riêng `02c: ☑ Lô n (<hash>)`).
8. Sang lô kế tiếp. Không deploy. Không sửa `doc/decisions.md`.

## Khi nào dừng hỏi Duy
- Gặp điểm dừng ghi trong `02c`.
- Code/DB mâu thuẫn với `01-analysis.md`, hoặc cần đổi quy tắc nghiệp vụ, tiền, giá vốn, phân quyền ngoài phạm vi story.
- Test hỏng ngoài phạm vi lô mà không sửa được trong lô.

## Khi xong hết
Báo Duy trong một tin nhắn ngắn:
- các lô đã xong kèm commit;
- số test thật;
- việc còn nợ;
- ảnh so sánh nằm ở đâu.

Nhắc Duy rằng deploy staging chỉ chạy khi Duy bảo.
