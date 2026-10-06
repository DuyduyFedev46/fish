# Tiếp tục sau khi tắt máy (03/10/2026)

## Kế hoạch chạy hết phần còn lại, không tính AI (06/10/2026)
Duy chốt 06/10 (ghi ở `doc/decisions.md`): D-1 giữ V2 bật, Chủ tự tắt · superuser được ghi phân quyền (FE mở) · #14 để sau production · **làm** CSKH lô 5.

| Đợt | Việc | Ở đâu | Trạng thái |
|---|---|---|---|
| 1 | #3/#8 BE hoàn tất | worktree `duy-quyet` (nhánh `wip/duy-quyet-03-10`) | đang chạy |
| 1 | Rà soát C/D/E hoàn tất | worktree `agent-adb46da0acecd2601` | đang chạy |
| 1 | Lô 15 hoàn tất (tuân cờ ẩn AI) | worktree `agent-adeaae51549099388` | đang chạy |
| 1 | Phạm vi dữ liệu Lô 1–2 BE | worktree `pham-vi` (nhánh `feat/pham-vi-du-lieu`) | đang chạy |
| 1 | CSKH lô 5 BE | worktree `cskh-lo5` (nhánh `feat/cskh-lo5`) | đang chạy |
| 2 | Gộp C/D/E, Lô 15, #3/#8 vào main → kiểm chứng đủ → techlead → QA → push | main | chờ |
| 2 | #8 FE nút "Xoá phiếu" · CSKH lô 5 FE · Phạm vi Lô F1 FE (mock) | — | chờ |
| 3 | Phạm vi Lô 3–7 · #15 Ghi tiền về muộn (sau #3/#8) | — | chờ |
| 4 | Lô 17 (nợ + hồi quy, gồm FE mở phân quyền cho superuser) · đợt 2 rà soát giao diện | — | chờ |
| 5 | Deploy staging (chỉ khi Duy bảo) | — | chờ |


Đọc file này trước khi làm tiếp. Nói với Claude: "đọc `05-tiep-tuc.md` rồi làm tiếp".

## Đã xong, đã lên staging
- Lô 1–14, Lô 16, Lô bổ sung A (☑ trong `02c-giao-viec.md`).
- Staging: backend `api:v12` (rev `cangca-api-staging-00010-zl5`), ERP + Shop build trỏ staging.
- Sửa theo Duy 03/10: nội dung giãn full width; Dòng thời gian thành thẻ.

## Đã gộp vào `main` nhưng CHƯA lên staging
- Rà soát giao diện **nhóm A** (danh sách, `b9c511f`) và **nhóm B** (trang chi tiết, `871dab1`). Merge `9b4abb1`.
  - Mới chạy `tsc` sau khi gộp. **Cần** chạy đủ: vitest, build mock=0 + `check-no-mock` + `check-ai-chunks`, e2e `ed_batch1`–`16`, `ed_bonusA_ui`, `p8_lo8_fe_erp_tz`, `s14_s16_cancel_refund`, `s41_s47_staff`, `s48_password`. Đạt rồi mới đẩy staging.

## Đang dở, nằm trong worktree hoặc working tree (đã commit WIP)
| Việc | Ở đâu | Còn lại |
|---|---|---|
| Rà soát giao diện **nhóm C/D/E** (form, popup, đăng nhập) | worktree `.claude/worktrees/agent-adb46da0acecd2601` | Chạy nốt e2e (8, 11, 13, 14, 16, bonusA, `s41_s47`, `s48`), chụp ảnh, ghi dev-notes, commit sạch. Rồi gộp vào main (dễ xung đột `shared/ui/globals.css` với nhóm A). |
| **Lô 15** (Tổng quan, AI của tôi, Chính sách AI, Báo cáo AI, Nhật ký, Tài khoản) | worktree `.claude/worktrees/agent-adeaae51549099388` | Commit WIP chứa sửa M1/M2/L1–L3. Còn: lỗi QA (bảng Chính sách AI vỡ ở 1280; tên việc AI lẫn tiếng Anh/mã; Tổng quan thiếu cột "Lý do"; nhãn bị cắt ở 360; "AI của bạn đang bật" mâu thuẫn banner). Sau đó `git rebase main`, chạy lại kiểm chứng, techlead re-review, QA trên BE thật. |
| **#3** timeline không chép chữ tự do + tiền "đ"; **#8** xoá mềm phiếu hoàn ở màn chi tiết (chỉ Chủ/admin, chỉ phiếu Nháp/Đã huỷ) | nhánh **`wip/duy-quyet-03-10`** (đã push) — `git merge wip/duy-quyet-03-10` vào main khi bắt đầu | BE gần xong (2872 test, đã sửa test đỏ cuối; chưa chạy lại toàn bộ). Xem `03-dev-notes.md` mục "Duy quyết 03/10 — #3 timeline, #8 xoá phiếu hoàn (BE)" (có contract FE). Còn: chạy lại `manage.py test` + `makemigrations --check`, techlead review, chặn xoá cứng ở Django admin (`has_delete_permission=False`). Sau đó FE thêm nút "Xoá phiếu" ở chi tiết phiếu hoàn. |

## Đã thiết kế, chưa code
- **#15 Ghi tiền về muộn**: `02d-tien-ve-muon.md` (16 AC, endpoint `POST /api/sales/payments/record-late/`, không migration). Làm SAU #3/#8 (cùng đụng `timeline.py`). Câu hỏi Q1–Q3 dùng mặc định trong file.
- **Phạm vi dữ liệu cấu hình** (#9/#12/#13, stories PV-01..14 Duy đã duyệt 03/10): techlead đang viết `doc/features/2026-10-02-pham-vi-du-lieu-cau-hinh/02b-tech-design.md`. Kiểm xem đã đủ chưa, rồi chia lô và code. Tính năng này xử lý luôn việc NV kho đang thấy tên/SĐT/địa chỉ khách ở chi tiết đơn.

## Chờ Duy quyết
- **AI on-device:** chọn Gemma 3n **E2B** (~1,9GB, đề xuất) hay E4B (~2,8GB). Có bật `AI_ENABLED=1` trên staging ngay (câu trả lời giả LLMock) không. Khi chốt: làm lô "AI on-device thật" gồm cài `@wllama/wllama`, đưa GGUF lên bucket GCS staging, đặt `AI_MODEL_GGUF_URL`, đo TTI < 2s, QA máy thật.
- **#14 Huỷ chi phí phụ** (đảo phân bổ giá vốn, không xoá chứng từ): có làm không, nên làm trước production.
- Superuser ngoài nhóm Chủ có được ghi phân quyền ở BE không (hiện BE cho, FE chặn).

## Lô cuối
- **Lô 17** (dọn dẹp + hồi quy toàn bộ): nợ ghi ở cuối `02c-giao-viec.md`.
- **Đợt 2 rà soát giao diện** (màn lệch hẳn bố cục): phân quyền W3h/W3i, báo cáo lãi lỗ W3a, soạn bài W3b–d, màn theo vai W1e/W2e, Tài khoản W4e. Xem `04b-ra-soat-giao-dien.md`.

## Lưu ý vận hành
- **Đĩa:** máy từng đầy (ENOSPC) khi chạy 4–5 build song song. Chạy **tối đa 2 luồng build**, xoá bản sao `out/` trong scratchpad ngay sau khi test, không chép `node_modules`.
- Deploy staging: quyền đã có trong `.claude/settings.local.json` (job migrate, service api-staging, firebase staging). Build image: `gcloud builds submit backend --tag …/api:vNN`. Nhật ký deploy ghi ở `doc/ops/moi-truong.md`.
- `ed_batch9_returns` đỏ 5 ca do ngày mock (đã biết, nợ Lô 17). `ed_batch3_fixes` đỏ 2 ca `aiOrderProposal` (có sẵn từ trước).
- Worktree còn lại: `agent-a0b18110f65579b39` (nhóm B) và `agent-a73704f8c60108a8c` (nhóm A) đã gộp, gỡ được. `agent-adb46da0acecd2601` (C/D/E) và `agent-adeaae51549099388` (Lô 15) còn việc.

## Nhánh WIP đã push lên GitHub (03/10, lúc tắt máy)
| Nhánh | Nội dung | Commit |
|---|---|---|
| `wip/duy-quyet-03-10` | #3 timeline + #8 xoá mềm phiếu hoàn (BE) | `1ec71cd` |
| `wip/ra-soat-cde` | Rà soát giao diện nhóm C/D/E (form, popup, đăng nhập) | `1180092` |
| `wip/lo15` | Lô 15 + sửa review M1/M2/L1–L3 | `50c0859` |
Worktree trên máy vẫn còn; nếu mất thì tạo lại bằng `git worktree add .claude/worktrees/<tên> <nhánh>`.

### Lô 15 — trạng thái chi tiết lúc dừng (`wip/lo15` = `50c0859`)
- Đã sửa: M1, M2, L1–L3; bảng Chính sách AI (bỏ cột thừa, container query); nhãn tiếng Việt cho lệnh AI (`features/ai/commandLabels.ts`); cột "Lý do" Tổng quan hiện ở 1280; nhãn ô số liệu 360px; "AI đang tắt cho cả vựa".
- Kiểm: tsc sạch, vitest 941, build mock=0 + 2 check xanh, `ed_batch15` 192/193 (ca đỏ là selector e2e mới đếm 8 span thay vì 5 — sửa selector).
- Còn: sửa selector đó; chạy `ed_batch1`, `s48_password`, `ed_batch14`; ghi dev-notes (lệch contract: `recent_orders` không có lý do → BE thêm `cancel_reason`; BE nên có `AiMeta.title` tiếng Việt); `git rebase main` + chuyển sang `DataTable title/countText`, `Section`; techlead re-review; QA trên BE thật.

### Nhóm C/D/E — trạng thái chi tiết lúc dừng (`wip/ra-soat-cde` = `46c2535`)
- Đạt: tsc, vitest 900, build mock=0 + 2 check, e2e 1, 2, 3_orders, 4–8, 10–14, 16, bonusA, s41_s47 (9 và 3_fixes đỏ đã biết).
- Còn: build lại mock=1, chạy lại 5, 6, 7, 8 và `s48_password` sau 4 thay đổi cuối (radio gradient, toast trên thanh nút, `.pw-eye` 44px, FormPage min-height 100dvh); rà ảnh so board; gộp vào main (`globals.css` chỉ sửa login/.field/.pw-*/toast/.btn.block).
