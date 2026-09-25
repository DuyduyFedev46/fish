# Xuất kho FEFO: user stories
> Điều phối viên, 2026-09-26. Nguồn: 01-analysis.md (ĐÃ DUYỆT; Duy chốt Q1 = áp cho toàn bộ mặt hàng, Q2 = V1 chưa cho chọn tay lô). Trạng thái: **ĐÃ DUYỆT** (phạm vi nhỏ, theo luồng gọn; Duy đã duyệt phân tích).

## F1: Chọn lô theo FEFO · Must · BE
**Là** Chủ vựa, **tôi muốn** hệ thống luôn xuất lô có hạn dùng sớm nhất trước, **để** hàng đông lạnh không bị quá hạn trong kho.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| F1-AC1 | Lô A nhập 01/09 hạn 30/11; lô B nhập 05/09 hạn 20/10 (cùng mặt hàng, đều còn bán) | Khách đặt 1 kg | Hệ thống phân bổ lô **B**, dù B nhập sau | BR-BH-05 (sửa) |
| F1-AC2 | Hai lô cùng hạn | Đặt hàng | Lô nhập sớm hơn ra trước; nếu trùng cả ngày nhập thì lô tạo trước ra trước | BR-BH-05 |
| F1-AC3 | Đơn cần nhiều hơn tồn của lô hạn sớm nhất | Đặt hàng | Lấy hết lô hạn sớm nhất, phần còn lại lấy lô có hạn kế tiếp | BR-BH-06 |
| F1-AC4 | Có lô đã quá hạn nhưng hạn sớm hơn mọi lô khác | Đặt hàng | Lô quá hạn **không** được chọn | BR-LO-02 |
| F1-AC5 | Combo có 2 thành phần | Đặt combo | Mỗi thành phần tự chọn lô theo FEFO | spec §3.1 |
| F1-AC6 | Đơn đã giữ chỗ trên một lô, sau đó nhập một lô hạn sớm hơn | Chủ xác nhận thanh toán | Hệ thống vẫn trừ đúng lô đã giữ, không chọn lại | BR-BH-11 (mới) |
| F1-AC7 | Hàng hoàn hoặc đơn bị huỷ | Nhập lại kho | Trả về lô gốc, giữ nguyên hạn của lô gốc | BR-HV-01, BR-HT-05 |
| F1-AC8 | Có dữ liệu thật | Xem Shop, Tổng quan, báo cáo | Tồn bán được không đổi (FEFO chỉ đổi thứ tự lô). Không lộ giá vốn | BR-PQ-13 |

Ghi chú: chỉ sửa thứ tự trong `sellable_batches` (nguồn duy nhất) và mọi chỗ tự sắp riêng. Đổi tên `allocate_fifo` thành tên trung tính (giữ alias nếu cần). Không có migration.

## F2: Hiển thị và tài liệu · Must · FE + doc
| Mã | Tiêu chí nghiệm thu |
|---|---|
| F2-AC1 | ERP không còn chữ "FIFO theo ngày nhập". Bảng tồn theo lô ở Tổng quan sắp theo thứ tự xuất (FEFO), phụ đề ghi "Xuất theo hạn dùng sớm nhất (FEFO)" |
| F2-AC2 | Sửa URD §6.2 và thuật ngữ, spec BR-BH-05, spec §3.1 combo, thêm BR-BH-11, BUILD-PLAN; `caveve-domain` bất biến #6; README/PRODUCT.md có nhắc FIFO |

## Thứ tự
F1 (BE) và F2 (FE, doc) làm song song, sau đó QA, rồi commit và push.
