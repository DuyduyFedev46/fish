# Báo cáo lãi lỗ (ED-32)

Màn của Chủ: lãi lỗ theo tháng (doanh thu, giá vốn, hoàn tiền, so với tháng trước), phần "Cấu thành lãi" và bảng "Lãi lỗ theo lô" (lô phát sinh trong tháng, có "Tải thêm", bấm mã lô mở chi tiết ở tấm bên). Chỉ đọc. Tháng chọn nằm trong state, không lên URL.

| File | Việc của file |
|---|---|
| `types.ts` | Kiểu dữ liệu theo contract BE: báo cáo kỳ (`PeriodReport`), dòng lô (`BatchReportRow`), tham số lọc. Tiền là chuỗi thập phân. |
| `api.ts` | `fetchPeriodReport(year, month)` và `fetchBatchReport(params, page)`. Có nhánh mock khi `NEXT_PUBLIC_USE_MOCK=1`. |
| `decimal.ts` | Cộng trừ tiền dạng chuỗi thập phân bằng BigInt (không dùng số thực). `roundToDong` làm tròn nửa lên, dùng cả cho gợi ý số tiền hoá đơn mua. |
| `reportView.ts` | Phần thuần cho màn: danh sách tháng, nhãn tháng, kỳ trống, các dòng "Cấu thành lãi", chi tiết lô, màu lãi / lỗ. |
| `components/ProfitReportScreen.tsx` | Màn chính: dải số liệu, Cấu thành lãi, bảng lô, tấm chi tiết lô. |
| `reports.module.css` | Kiểu riêng, chỉ dùng token trong `DESIGN.md`. |
| `mock.ts` | Dữ liệu giả (xem mục Mock). |
| `decimal.test.ts`, `reportView.test.ts` | Kiểm thử đơn vị. |

## Quyền

Chỉ `reports.view_profitreport` (Chủ). Vai khác không có menu, vào thẳng `/reports/` thấy "Không có quyền", và API trả 403 cũng ra màn đó. Mọi số trên màn là giá vốn hoặc lãi nên mang icon khoá; không có cách xem một phần.

## Quy tắc đáng nhớ

- Lỗi tải lại thì ẩn số cũ và hiện thông báo kèm "Thử lại" (số tiền không được lỗi thời một cách im lặng).
- Kỳ không có giao dịch hiện trạng thái trống, không hiện số 0 giả.
- API chỉ có lọc theo tháng nên chưa có lựa chọn theo năm.
- Chỉ dùng icon có trong tập con font `public/fonts/ms/` (thiếu icon thì hiện thành chữ).

## Mock

`window.__caveMock.reports("ok" | "fail")`. Dữ liệu bịa: 4 kỳ gần nhất có số liệu, 24 lô chia hai tháng (có lô lỗ, lô tạm tính).
