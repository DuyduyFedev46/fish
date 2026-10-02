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
| ☑ | 1 | ED-01, ED-02, ED-03 (phần khung), ED-04 (mẫu danh sách) | FE | sidebar/topbar mọi board, W6g, W6h, W4h | — | BE của Lô 4, 6, 8 | a25edbc |
| ☑ | 2 | ED-03, ED-04 (trang chi tiết), ED-05 ∥ R1, R2 | BE ∥ FE | D2b (mẫu), W6a–W6f, W6i, modal F* | FE: 1 | BE Lô 4, 6, 8 | BE 1237d9b · FE da93d77 |
| ☑ | 3 | ED-09, ED-10, ED-11, ED-12 ∥ R3 + số điện thoại đủ | BE ∥ FE | D2, D2b, D2c, W1a, W1a2, W1b, W1b2, F2a–F2g | FE: 1, 2 | Lô 7 (BE) | BE 1237d9b · FE 70b23ca |
| ☑ | 4 | ED-16, ED-17, ED-18, ED-19 ∥ B5, B6, R4 | BE ∥ FE | W1d, W1d2, W1e, W2e, F2l, F2o | FE: 1, 2 | Lô 5 | BE 1237d9b · FE 7f3b7b1 (merge 4374ebb) |
| ☑ | 5 | ED-15 | FE | W1c, W1c2, F2h–F2k | 1, 2 | Lô 4 | FE 63b305d (merge e851109) |
| ☑ | 6 | ED-13, ED-14 ∥ B2 | BE ∥ FE | W5a, W5b | FE: 1, 2, 3 | Lô 7 | BE 1237d9b · FE ce21a33 |
| ☑ | 7 | ED-23, ED-24, ED-25 (chỉ danh sách), ED-29 ∥ R5, R6, R7, R7b | BE ∥ FE | D3, W2f, W5i, W5k, W5l, F1e, F1g, F1h, F1i, F3m | FE: 1, 2 | Lô 6 | BE 1237d9b · FE af35b16 (merge 9d8d70e) |
| ☑ | 8 | ED-27, ED-28 ∥ B1 | BE ∥ FE | W2c, W2g, F1f, W6f | FE: 1, 2; BE sau 7 | Lô 10 | BE 1237d9b · FE 76853c6 (merge ca08d23) |
| ☑ | 9 | ED-26 ∥ R9 | BE ∥ FE | W5e, W5f, F2m, F2n | FE: 1, 2, 4; BE sau 8 | Lô 11 | BE 1237d9b · FE+BE 0ba9223 |
| ☑ | 10 | ED-20 ∥ R10 | BE ∥ FE | W2a, W2b, F1a, F1c, F1d | FE: 1, 2 | Lô 8 | BE 1237d9b, bb0137c, 9c727c0 · FE 5593a26 (merge c4ee720) |
| ☑ | 11 | ED-21, ED-22 ∥ B3 | BE ∥ FE | W5c, W5d, F1b | FE: 1, 2; BE sau 10 | Lô 9 | BE 1237d9b · FE 46f601b |
| ☑ | 12 | ED-32, ED-33, ED-34 ∥ R11, R12, R13, R15 | BE ∥ FE | W3a, W5j, W5g, W5g2 | FE: 1, 2, 10; BE sau 11 | Lô 13 | FE b249d4a, fea2326 (merge 68a38c2) |
| ☑ | 13 | ED-30, ED-31 ∥ R14 | BE ∥ FE | W2d, W2h, W5o, W5h, W5m, F1k–F1o | FE: 1, 2 | Lô 12 | FE 080a7f6, 76b614e (merge 812edbc) |
| ☑ | 14 | ED-37, ED-38, ED-39, ED-40 ∥ B4, R16 | BE ∥ FE | W3e, W3g, W3h, W3i, F3a–F3f | FE: 1, 2; BE sau 4 và 6 | Lô 15 | FE+BE 6267120, 1684ffd (merge c385dcd) |
| ☐ | 15 | ED-06, ED-08, ED-41, ED-42 | FE | D1, W3f, W4b–W4h, F3g | 1, 2; W3f cần R16 (Lô 14) | Lô 14, 16 | — |
| ☑ | 16 | ED-35, ED-36 | FE | W3b, W3c, W3d, F3h–F3l | 1, 2 | Lô 15 | FE 57f0eda, c86ebfd (merge d38ce85) |
| ☐ | 17 | ED-07 + dọn dẹp + hồi quy toàn bộ | FE | — | 1–16 | — | — |
| ☑ | bổ sung A | Quyết định Duy 02/10 (#1, 2, 5, 6, 8 huỷ, 10, 11, 14, 15, 17, 18, 19, 20, 21, 22) | BE ∥ FE | — | 1–11 | — | 0fe91c4 |

Nợ từ review Lô bổ sung A (03b, TLA-*):
- TLA-L2 → **Lô 14**: thêm ô "tạo hàng hoàn" vào ma trận phân quyền (registry chưa có năng lực này).
- TLA-L3 → **Lô 17**: bỏ GET `customer-directory/?q=` sau khi FE đã dùng POST search.
- TLA-L5: câu `COST_ALLOCATED_LOCKED` "Liên hệ Chủ" trong khi chỉ Chủ gọi được → sửa cùng story huỷ chi phí.
- Nhãn guidance kiểm kê `update_reconciliation_lines` / `update_stockreconciliation` còn "Có thay đổi" → Lô 17.
- TLA-FE-M1 → **Lô 17**: "Nhờ người xử lý" hiện cả khi bước bị luật chặn (không chỉ thiếu quyền) → BE thêm cờ `blocked_by` cho từng bước, FE lọc theo.
- TLA-FE-L4 → **Lô 14** (cùng TLA-L2): `canCancel` phiếu hoàn tính cả quyền `add_returntostock`.
- TLA-FE-L6 → **Lô 17**: câu lỗi `STEP_NOT_FOUND` của BE lộ mã bước nội bộ.
- **Lô 17**: dời các hộp xác nhận riêng từng module sang `shared/ui/overlay/ConfirmModal`; "Nhờ người xử lý" chỉ ẩn bước kẹt đầu tiên sau khi nhờ (gộp TLA-FE-M1).
- QA N1 → **Lô 17**: BE `/ai/actions/escalate/` không loại trùng (tải lại trang rồi nhờ lại tạo thêm action) → trả action ESCALATED cũ nếu đã có.
- QA N2 → **Lô 17**: hộp Gửi duyệt khi phiếu đã đổi vẫn có nút "Thử lại" vô ích → đổi thành "Tải lại".
- QA N4: chi phí phụ `amount: "0"` vẫn được nhận (có từ trước) → gộp story huỷ chi phí.

Nợ BE từ review Lô 12 (03b, TL12-FE):
- `/api/reports/*` trả tiền/kg dạng number (Decimal → float) → đổi sang chuỗi; trước khi đổi rà các chỗ dùng chung (AI, dashboard). FE Lô 12 đã tự chuẩn hoá.
- Hoá đơn mua: BE chưa từ chối phiếu nhập khác nhà cung cấp (FE đã chặn).
- `paid_at`: bắt buộc khi đã trả, không cho giờ tương lai.
- Báo cáo theo năm; `q` cho danh sách phiếu nhập (ưu tiên thấp).
- PO: sửa ED-33-AC4 / ED-34-AC5 trong `02-stories.md` cho khớp #12 (kho xem hoá đơn bán, không giá vốn).
- QA Lô 12 N1 (**chờ Duy**, có từ trước): NV kho mở được `/orders/detail/` và API `sales/orders/<id>/` trả tên/SĐT/địa chỉ khách; `/orders/` hiện tên khách → gộp "Phạm vi dữ liệu cấu hình" hoặc vá ngay nếu Duy muốn.
- QA Lô 12 N3: BE hoá đơn mua nhận `amount = 0` (FE đã chặn).
- QA Lô 12 N4/N5 → **Lô 17**: 360px mã hoá đơn cao 18px, cột Đơn cắt mã, dòng Đã huỷ chưa gạch; ô tìm hoá đơn bán đi qua URL GET.
- Review Lô 12 L-a → **Lô 17**: `ReceiptDetailScreen.tsx:116` còn "Nhập chi phí mua"; `e2e/qa_ed_batch10_real.py` còn kiểm tab "Chi phí mua".
- Review Lô 13 → **Lô 17**: ô tiền ưu đãi đi qua `Number` không giới hạn chữ số; `toFixed(3)` âm thầm ở định mức combo/kg tối thiểu; đổi tên `ImageUploadSheet`. Nợ BE: `q` danh sách mặt hàng, lọc `price_list`, tồn combo, sự kiện đặt giá trên dòng thời gian mặt hàng.
- Review Lô 14 L2 (nợ BE): chip "Được gán" ở ma trận là hằng số FE (`permissionsModel.ts:32`) → BE trả phạm vi dữ liệu trong danh sách nhóm. Hỏi Duy: superuser ngoài nhóm Chủ có được ghi phân quyền ở BE không (hiện BE cho, FE chặn).
- Review Lô 16 L1 → **Lô 17**: `Tabs` dùng chung (`.tab`) rộng 39px ở 360px, dưới 44px.
- Review Lô 16 L2 → **PO**: ED-35-AC6 lệch quyền mặc định (Quản lý mặc định có quyền đăng bài).
- **Lô 17**: e2e `ed_batch9_returns` đỏ 5 ca từ 03/10 (mock tính ngày "tháng trước" lệch khi sang đầu tháng) — cố định ngày mock theo tháng.
- Re-review Lô 14 → **Lô 17**: (QA N2: sửa bộ chọn `.screen` → `main` trong `e2e/s41_s47_real.py`; comment cũ `PermissionMatrixScreen.tsx:45`; cột "Thành viên" ở bảng nhóm W3h) hộp "Cho nghỉ" chỉ đếm trang đầu (20) phiếu Đang giao; danh sách là ảnh chụp lúc mở hồ sơ (giao xong phải tải lại).
- Review Lô 15 → **Lô 17 / BE**:
  - `dashboard/summary/` thêm `id` cho `alerts[]`, `batches[]`, `recent_orders[]` (ED-08-AC3: dòng bấm mở chi tiết).
  - `audit-logs/` thêm `?date_from=&date_to=&q=` (ED-41-AC2).
  - `can_do` của BE chứa "BR-LO-04".
  - `forgetSignedIn` chuyển vào `AuthProvider.logout`.
  - **L5 (dữ liệu cá nhân, BE):** `AuditLog.note` chép chữ người dùng gõ (ghi chú tiền về, lý do hoàn) → có thể lộ tên người chuyển khoản ở cột Ghi chú Nhật ký.
  - Viết lại hoặc xoá `e2e/s8_views.py`.
  - PO: ED-42-AC2 có làm màn danh sách phiên bản chính sách AI không.
- TLA-L4: không chạy lùi migration `inventory/0007` khi đã có phiếu hoàn bị huỷ.
- Lưu `item_price_id` (FK nullable PROTECT) trên dòng đơn → gộp với nợ Lô 13 L4.
- Chờ Duy/PO: story "Huỷ chi phí phụ" (TLA-H1b, #14) và "Ghi tiền về muộn ở hàng chờ" (TLA-M3, #15).

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
- Deploy: không tự làm; chỉ khi Duy bảo. **Không deploy bản có Lô 1 mà chưa có Lô 2 FE** (khung mới bỏ cột phải → nút "Tóm tắt" AI tạm mất, review Lô 1 M3).
