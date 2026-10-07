# Review techlead: lô dọn e2e (08/10)

Nhánh `chore/e2e-cleanup`, diff `git diff main...HEAD` (5 commit: 8e17ec5, d839a95, dbcadd9, 899b21c, 171404f).
Phạm vi: 45 file. Chỉ có `erp-console/e2e/*.py` và `03-dev-notes.md`, không đổi code sản phẩm (đã kiểm `--name-only`).
Không chạy lại e2e hay build vì điều phối viên đã chạy (bảng ở 03-dev-notes). Lệnh đã chạy: `python3 scripts/check_naming.py` cho OK, không phát sinh vi phạm mới.
`python3 -m py_compile erp-console/e2e/*.py` cũng sạch.

## Kết luận: **APPROVED**

Không có lỗi Critical, High hay Medium. Có 4 lỗi Low, nên sửa ở lần chạm sau và không chặn merge.

## 1. Bất biến 9 và bí mật (repo công khai)
- Đạt. `e2e_seed_qa.password()` đọc `QA_PASSWORD`, thiếu biến thì `SystemExit`, không có mặc định. Bốn kịch bản chuyển sang seed_qa đều dùng hàm này: `ed_batch3_real`, `ed_batch5_confirmation_real`, `ed_batch6_customers_real`, `p8_lo5_qa_real_backend`. `qa_ed_batch11_api` cũng vậy.
- Dòng thêm mới không có token, secret hay mật khẩu cứng. Còn chuỗi `Songbien2026` và `demo1234` trong `s41_s47_*`, `ed_batch14_permissions`, `qa_ed_batch3_real_ai` và `qa_ed_batch5_real`. Đây là mật khẩu của tài khoản mock hoặc demo giả, đã có từ trước lô này, không phải bí mật thật.
- Dữ liệu khách đều là dữ liệu giả: "Khách QA Giả nn", SĐT `09000000nn`, ghi chú gọi `0912345678` (ca kiểm BR-GH-19 chặn SĐT trong ghi chú) và "QA-Địa chỉ".
- Các kiểm PII vẫn còn hoặc được thêm. URL và storage không chứa SĐT. Tìm khách đi bằng POST, nên SĐT không vào URL. AuditLog không chép SĐT hay địa chỉ. Vai không có quyền vào màn khách thì DOM không có SĐT. ⌘K không lộ tên hay SĐT.
- Bộ lọc storage nay bỏ qua khoá `cave_erp_mock_*` ở cả sessionStorage. Đã kiểm: các khoá này chỉ được ghi trong `features/*/mock.ts`, bản build thật không có, nên ca kiểm không yếu đi trên BE thật.

## 2. Giá vốn
- Đạt. Số khẳng định liên quan giá vốn, 403 và SĐT trong từng file viết lại không giảm. Ví dụ `qa_ed_batch11_api` tăng từ 18 lên 21, `ed_batch3_real` từ 2 lên 3, các file còn lại giữ nguyên số. Kịch bản mới có thêm kiểm "không giá vốn / lãi". `ed_batch5_confirmation_real.py:84` kiểm JSON hàng chờ, `ed_batch6_customers_real.py:95` kiểm chi tiết khách.
- `qa_ed_batch7_mock` vẫn giữ `COST_NUMBERS` cùng ca vai không thấy giá vốn. Phần sửa chỉ thay `wait_for_timeout` bằng điều kiện chờ (`title_is`, `ready`, rAF), tức là chặt hơn.
- `p8_lo5_qa_real_backend` vẫn kiểm tiền NCC hoàn (sentinel) không hiện lại ở DOM, URL, storage hay console. Vòng lặp "GET không chứa sentinel" bị bỏ, nhưng trên main nó chỉ là `pass` nên không mất kiểm nào.

## 3. Có nới lỏng sai không
- **8e17ec5.** Phần lớn thay đổi là cập nhật theo hành vi đã duyệt: tên chuẩn 07/10, menu thêm "Hàng hoàn" và "Phân quyền", giao1 có "Hàng hoàn" (Lô 9), Quản lý có nút Nhập hàng hoàn (Lô bổ sung A), mục AI theo cờ build, ⌘K có lối "Mở chứng từ <mã>" (ED-07), bảng đơn 5 cột.
  - `qa_ed_batch1_shell`: khẳng định menu đổi từ đếm cứng sang so đúng `EXPECTED_MENU`, nên chặt hơn. Danh sách ⌘K được phép chỉ gồm tên màn trong menu, hoặc đúng mã đơn kèm "Mở chứng từ". Không có gì khác lọt qua.
  - Ca console `SECRET-NAME` (`qa_ed_batch1_shell.py:339`) chỉ loại đúng dòng `Error: qa-induced render error`. Dòng này do React tự ghi lỗi gốc. Quy ước "không đặt PII vào message của Error" đã có sẵn trong `app/(console)/error.tsx`, từ trước lô này. Ngoại lệ chấp nhận được.
  - `ed_batch14_permissions`: thêm bước chờ hết trạng thái "đang kiểm tra" trước khi đọc hộp, nên chặt hơn.
  - `qa_ed_batch7_mock`: bỏ ngủ cố định, đợi đúng màn, nên chặt hơn.
- **899b21c (xoá 14 file QA một lần).** Phần có giá trị vẫn được phủ:
  - Khách và PII (`qa_ed_batch6_*`) có ở `ed_batch6_customers_real` và test BE `sales/customers/tests/test_directory_permission.py`, `test_directory_api.py`.
  - Nhà cung cấp (`qa_ed_batch11_real`) có ở `qa_ed_batch11_api` (seed_qa, 153 ca).
  - Đơn (`qa_ed_batch3_real`) có ở `ed_batch3_real`.
  - Hàng hoàn và scope giao1 (`qa_ed_batch9_*`) có ở `inventory/returns/tests/test_list_scope.py`, `test_timeline_scope.py`, `test_approve.py`, `test_cancel.py`.
  - Giá vốn ở kho, lô và nhập (`qa_ed_batch7_real`, `qa_ed_batch10`, `qa_lo7_real_expired`) có ở `inventory/batches/tests/test_p8_lo7_*`, `test_list_filters_receipt.py` và `purchasing/receipts/tests/*`. Có 61 file test BE kiểm `landed_unit_cost`.
  - Kiểm kê (`qa_ed_batch8_*`) có ở các test BE kiểm kê.
  - Múi giờ SR-25 (`qa_lo8_real`) chỉ là UI, không chứa khẳng định quyền, PII hay giá vốn.

## 4. `finish()`
- Đạt. `e2e_support.py:23-31` thoát 1 khi có ca FAIL hoặc khi danh sách rỗng, ngược lại thoát 0. Nhận cả dạng tuple `(tên, đạt, …)` lẫn bool.
- `s14_s16_cancel_refund` dùng `orders_common.finish` có từ trước, lô này không đổi. `qa_ed_batch7_mock.finish(ctx, page)` là hàm khác, chỉ đóng context, và kịch bản vẫn thoát bằng `sys.exit(main())`.

## Lỗi Low (không chặn merge)
| # | File:dòng | Vấn đề | Sửa |
|---|---|---|---|
| L1 | `erp-console/e2e/p8_lo5_qa_real_backend.py:96-110` | Bước chốt lô được viết dạng `if/else` nên đi nhánh nào cũng đạt. seed_qa cố định, và QA-LO-03 chưa có phiếu kiểm kê APPROVED (BR-KK-05), nên luôn đi nhánh "mờ kèm lý do". Ca "chốt lô thật thành công (200)" không còn chạy, và nếu sau này nút chốt hỏng thì kịch bản vẫn đạt. | Bỏ nhánh, khẳng định đúng một kết quả theo seed: "Chốt lô" mờ và lý do chứa "kiểm kê". Muốn kiểm chốt thật thì thêm vào seed_qa một lô Quá hạn đã có kiểm kê APPROVED và hoá đơn mua. |
| L2 | `erp-console/e2e/qa_ed_batch4_round2.py:137-139` | Comment ghi rằng nợ "nút đóng toast 32px" đã có trong dev-notes lô dọn e2e, nhưng mục đó trong `03-dev-notes.md` không có. Nợ a11y của sản phẩm (vùng chạm < 44px) vì thế không được theo dõi. | Thêm dòng nợ Low này vào mục "Lô dọn e2e" của 03-dev-notes, hoặc vào backlog FE. |
| L3 | `erp-console/e2e/e2e_support.py:10` | Docstring vẫn ghi `import e2e_exit`, là tên cũ. | Đổi thành `from e2e_support import finish`. |
| L4 | `erp-console/e2e/e2e_support.py:23` | Tham số `label="ca"` không được dùng. | Bỏ tham số, hoặc dùng nó trong dòng in tổng kết. |
