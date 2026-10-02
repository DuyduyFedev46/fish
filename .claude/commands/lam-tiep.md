---
description: Làm tiếp toàn bộ việc dở của đợt ERP theo design (đọc 05-tiep-tuc.md và chạy đến hết)
---

Bạn là **điều phối viên** (phiên chính) của dự án Cá Về. Làm theo `CLAUDE.md` và skill `feature` ở luồng **TIẾP TỤC**.
Không hỏi lại những gì đã chốt trong hồ sơ. Chỉ dừng để hỏi Duy ở mục "Chờ Duy quyết" hoặc ở điểm dừng ghi trong `02c-giao-viec.md`.

## Bước 0 — nắm tình hình (đọc, chưa làm)
1. `git checkout main && git pull`. Chạy `git worktree list` và `git status`.
2. Đọc `doc/features/2026-10-01-erp-theo-design/05-tiep-tuc.md`. **Đây là danh sách việc chuẩn.**
3. Đọc phần nợ ở cuối `02c-giao-viec.md` và `00-can-duy-quyet.md` (các mục "Duy quyết").
4. Kiểm dung lượng đĩa bằng `df -h /System/Volumes/Data`. Còn dưới 10GB trống thì dọn scratchpad cũ và `.next/cache` trước.

## Thứ tự làm (theo `05-tiep-tuc.md`)
1. **Kiểm `main` sau khi gộp nhóm A và nhóm B.** Chạy đủ lệnh kiểm chứng. Đạt thì đẩy lên staging theo `doc/ops/moi-truong.md`, rồi ghi nhật ký deploy.
2. **#3/#8 phần BE** (WIP trên main). Làm nốt, chạy test, techlead review, rồi commit. Sau đó làm FE nút "Xoá phiếu", QA, rồi đẩy staging.
3. **Nhóm C/D/E**: làm nốt trong worktree, gộp vào main, kiểm, rồi đẩy staging.
4. **Lô 15**: sửa nốt lỗi QA, `git rebase main`, kiểm, techlead re-review, QA trên BE thật, gộp, rồi đẩy staging.
5. **#15 Ghi tiền về muộn** theo `02d-tien-ve-muon.md`: BE ∥ FE, techlead, QA, rồi đẩy staging.
6. **Phạm vi dữ liệu cấu hình**: hoàn tất `02b`, chia lô, rồi làm từng lô.
7. **Lô 17**, sau đó **đợt 2 rà soát giao diện**.

Mỗi lô theo quy trình trong `CLAUDE.md`:
- giao dev;
- **tự chạy lại** lệnh kiểm chứng;
- techlead review;
- QA chạy thật trên BE thật (không PASS bằng đọc code);
- commit tiếng Việt, theo pathspec (nhớ `git add` file mới);
- push `main`;
- đánh ☑ ở `02c`;
- đẩy staging (Duy dặn "xong lô nào thì đẩy staging lô đó").

## Luật vận hành rút ra từ đợt trước
- **Tối đa 2 luồng build/e2e chạy song song.** Mỗi luồng copy `out/` vào thư mục riêng trong scratchpad, test xong thì xoá ngay. Không copy source hay `node_modules`.
- Mỗi agent dùng **cổng riêng**, và chỉ kill đúng cổng của mình.
- Worktree dùng `git rebase main` (main local), không dựa vào `origin`.
- Không deploy production. Không sửa `doc/decisions.md`. Không rò giá vốn hay dữ liệu cá nhân. Không commit `.env` hay bí mật.
- Khi xong một mục, cập nhật lại `05-tiep-tuc.md` (gạch mục đã xong) để lần sau đọc là biết đang ở đâu.

## Khi hết việc hoặc gặp mục "Chờ Duy quyết"
Báo Duy trong 1 tin ngắn gồm:
- các lô đã xong, kèm hash commit;
- số test thật đã chạy;
- những gì đã lên staging;
- các câu cần Duy quyết.
