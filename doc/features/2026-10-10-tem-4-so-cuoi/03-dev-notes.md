# Dev notes — TEM-01 (tem chỉ hiện 4 số cuối SĐT)

## BE
- `backend/apps/common/pii.py`: thêm `mask_phone_last4(phone)`: chuẩn hoá bằng `normalize_phone`, trả `xxxxxx` + 4 số cuối; rỗng hoặc dưới 4 chữ số trả `***`. `mask_phone` KHÔNG đổi (AC4: hàng chờ gọi, content scan, AI vẫn dạng `09xx xxx 123`).
- `backend/apps/delivery/labels/services.py`: `recipient_phone_masked` dùng `mask_phone_last4`. Khoá JSON giữ nguyên. Ví dụ: `"recipient_phone_masked": "xxxxxx4567"`.
- Không migration, không endpoint mới. `ai/policy/rules.py` chỉ liệt kê tên khoá, không cần đổi.
- Test: `apps/common/tests/test_mask_phone_last4.py` (AC1-AC4, gồm `mask_phone` cũ không đổi); `Tem01LabelLast4Tests` trong `apps/delivery/tests/test_confirmation_queue_and_labels.py` (API tem với 4 dạng SĐT, chuỗi trả về chỉ chứa 4 chữ số). Sửa hai test tem cũ kỳ vọng `09xx xxx ...` (`test_confirmation_operations.py`, `test_confirmation_queue_and_labels.py`).
- AC6: không đổi API nào khác, không thêm log.
- Nợ: không.

## FE (TEM-01 AC5 + nợ L2)

- `erp-console/features/deliveries/mock.ts`: `recipient_phone_masked` đổi sang `xxxxxx4567` (số giả). Màn `app/print/label/page.tsx` in chuỗi BE trả nguyên văn, không che/định dạng lại, nên không đổi code. `features/confirmation/**` (hàng chờ gọi xác nhận) giữ nguyên định dạng cũ; chỉ sửa test tem CS-11-AC5 trong `confirmation.test.ts` (kỳ vọng `xxxxxx4567`).
- `e2e/ed_batch4_delivery.py` (`label_masks_phone`): kiểm `xxxxxx\d{4}` thay cho `09xx xxx nnn`; vẫn kiểm không có SĐT đủ.
- L2: `features/permissions/permissions.module.css`. Tên đăng nhập/tên dài xuống dòng (`overflow-wrap: anywhere`, `white-space: normal`, `min-width: 0`); bảng Thành viên bỏ `min-width: 600px` của bảng dense để không cuộn ngang ở 360px. Nút "Bỏ khỏi nhóm" nằm trong khung ở 360 và 1280 (đo Playwright, thêm 2 thành viên giả tên 52 và 150 ký tự vào `localStorage` mock chỉ trong script đo, không đổi mock).
- Ảnh: scratchpad `shots/l2_360.png`, `shots/l2_1280.png`.
- Nợ: `ed_batch4_delivery.py` chạy qua `http.server` hay rớt ngẫu nhiên (ERR_SOCKET_NOT_CONNECTED, các ca khác nhau mỗi lần); ca Tem luôn PASS.
