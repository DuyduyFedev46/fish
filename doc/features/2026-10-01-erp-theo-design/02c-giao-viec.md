# Giao việc: ERP theo design (máy tính)
> Claude (điều phối) · 2026-10-01 · Trạng thái: **SẴN SÀNG CODE** (Duy duyệt 01/10/2026)
> Người hiện thực: đội Claude theo `CLAUDE.md`, lệnh `/lam-design-erp`.
> Nhánh làm việc: `main` (mỗi lô QA APPROVED → commit + `git push origin main` → đánh ☑ ở đây).

## Điều kiện đầu vào
- `01-analysis.md`: ĐÃ DUYỆT 01/10 · `02-stories.md`: ĐÃ DUYỆT 01/10 · `02b-tech-design.md`: ĐÃ DUYỆT 01/10 (§6 Duy đã trả lời).
- Đọc trước mỗi lô: `doc/design/erp/UI-RULES.md`, `doc/design/erp/enum-map.md`, board thiết kế của lô trong `doc/design/erp/screens/`.
- Chi tiết file được sửa / không được đụng / lệnh kiểm chứng của từng lô: **`02b-tech-design.md` §5.2** (đọc nguyên văn khi giao việc).

## Lô
Thứ tự chạy từ trên xuống. Cột "Song song" = lô được giao cùng lượt với lô đang làm (khác thư mục, không đụng nhau ngoài các file chung ở 02b §5.1).

| ☐/☑ | Lô | Story | Kiểu | Board chính | Phụ thuộc | Song song | Commit |
|---|---|---|---|---|---|---|---|
| ☐ | 1 | ED-01, ED-02, ED-03 (phần khung), ED-04 (mẫu danh sách) | FE | sidebar/topbar mọi board, W6g, W6h, W4h | — | BE của Lô 4, 6, 8 | — |
| ☐ | 2 | ED-03, ED-04 (trang chi tiết), ED-05 ∥ R1, R2 | BE ∥ FE | D2b (mẫu), W6a–W6f, W6i, modal F* | FE: 1 | BE Lô 4, 6, 8 | — |
| ☐ | 3 | ED-09, ED-10, ED-11, ED-12 ∥ R3 + số điện thoại đủ | BE ∥ FE | D2, D2b, D2c, W1a, W1a2, W1b, W1b2, F2a–F2g | FE: 1, 2 | Lô 7 (BE) | — |
| ☐ | 4 | ED-16, ED-17, ED-18, ED-19 ∥ B5, B6, R4 | BE ∥ FE | W1d, W1d2, W1e, W2e, F2l, F2o | FE: 1, 2 | Lô 5 | — |
| ☐ | 5 | ED-15 | FE | W1c, W1c2, F2h–F2k | 1, 2 | Lô 4 | — |
| ☐ | 6 | ED-13, ED-14 ∥ B2 | BE ∥ FE | W5a, W5b | FE: 1, 2, 3 | Lô 7 | — |
| ☐ | 7 | ED-23, ED-24, ED-25 (chỉ danh sách), ED-29 ∥ R5, R6, R7, R7b | BE ∥ FE | D3, W2f, W5i, W5k, W5l, F1e, F1g, F1h, F1i, F3m | FE: 1, 2 | Lô 6 | — |
| ☐ | 8 | ED-27, ED-28 ∥ B1 | BE ∥ FE | W2c, W2g, F1f, W6f | FE: 1, 2; BE sau 7 | Lô 10 | — |
| ☐ | 9 | ED-26 ∥ R9 | BE ∥ FE | W5e, W5f, F2m, F2n | FE: 1, 2, 4; BE sau 8 | Lô 11 | — |
| ☐ | 10 | ED-20 ∥ R10 | BE ∥ FE | W2a, W2b, F1a, F1c, F1d | FE: 1, 2 | Lô 8 | — |
| ☐ | 11 | ED-21, ED-22 ∥ B3 | BE ∥ FE | W5c, W5d, F1b | FE: 1, 2; BE sau 10 | Lô 9 | — |
| ☐ | 12 | ED-32, ED-33, ED-34 ∥ R11, R12, R13, R15 | BE ∥ FE | W3a, W5j, W5g, W5g2 | FE: 1, 2, 10; BE sau 11 | Lô 13 | — |
| ☐ | 13 | ED-30, ED-31 ∥ R14 | BE ∥ FE | W2d, W2h, W5o, W5h, W5m, F1k–F1o | FE: 1, 2 | Lô 12 | — |
| ☐ | 14 | ED-37, ED-38, ED-39, ED-40 ∥ B4, R16 | BE ∥ FE | W3e, W3g, W3h, W3i, F3a–F3f | FE: 1, 2; BE sau 4 và 6 | Lô 15 | — |
| ☐ | 15 | ED-06, ED-08, ED-41, ED-42 | FE | D1, W3f, W4b–W4h, F3g | 1, 2; W3f cần R16 (Lô 14) | Lô 14, 16 | — |
| ☐ | 16 | ED-35, ED-36 | FE | W3b, W3c, W3d, F3h–F3l | 1, 2 | Lô 15 | — |
| ☐ | 17 | ED-07 + dọn dẹp + hồi quy toàn bộ | FE | — | 1–16 | — | — |

Ghi chú:
- "Song song" là gợi ý; nếu hai lô cùng sửa một file chung (02b §5.1) thì commit lần lượt, lô sau rebase/merge lô trước.
- Lô 7: W5k **chỉ danh sách đọc**, không làm form F1j, không có nút "Ngừng bán lô" (Duy chốt 01/10).
- Lô 6: **không đụng** endpoint cũ `/api/sales/customers/` và test S5 (Duy chốt 01/10).
- Lô 12: Quản lý **vẫn thấy** tiền hoá đơn mua (Duy chốt 01/10).
- Câu hỏi Q1–Q7 trong `02-stories.md`: dùng mặc định ghi trong đó.

## Mỗi lô: điều kiện xong
1. Lệnh kiểm chứng ở 02b §5.0 + phần "Kiểm" của lô trong 02b §5.2, **điều phối viên tự chạy lại**; dán số liệu thật vào `03-dev-notes.md`.
2. Test bắt buộc:
   - phân quyền theo từng vai (Chủ, Quản lý, Nhân viên kho, Nhân viên giao, CSKH);
   - không rò giá vốn (gọi API bằng token nhân viên);
   - không rò dữ liệu cá nhân ra API công khai, log, AI;
   - đủ AC của story;
   - bộ kiểm G1–G10 trong `02-stories.md`.
3. `techlead` review diff (ghi `03b-review-techlead.md`), không còn lỗi Critical/High.
4. `qa-tester` APPROVED (`04-qa-report.md`):
   - chạy thật, có ca ngoài đường thuận;
   - có ảnh màn thật đặt cạnh board thiết kế (lưu `shots/lo<N>/`);
   - chấm theo từng mục `UI-RULES.md` áp dụng.
5. `npm ci` sạch; `git status` không có `.env`/bí mật; commit tiếng Việt có mã lô + mã story; push `main`; đánh ☑ + hash.

## Điểm dừng hỏi Duy
- Code/DB mâu thuẫn với `01-analysis.md` hoặc 02b mà không tự chốt được bằng nguyên tắc "code thắng về dữ liệu, thiết kế thắng về bố cục & wording" → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô.
- Việc đụng tiền, giá vốn, phân quyền, dữ liệu khách **ngoài** phạm vi story.
- Lô 14: codename trong registry B4 không tồn tại, hoặc `nv_giao` mất quyền cần cho Lô 4 khi chạy test.
- QA REJECTED quá 2 vòng.
- Test hỏng ngoài phạm vi lô mà không sửa được trong lô.
- Deploy: không tự làm; chỉ khi Duy bảo.
