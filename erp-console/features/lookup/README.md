# lookup — ⌘K nhảy theo mã chứng từ (ED-07)

Nối ô ⌘K (`shared/ui/shell/CommandSearch`) với các module để mở chứng từ theo **mã**. Nhận dạng mẫu mã và điều phối ở
`shared/lib/codeLookup.ts`; file ở đây chỉ chọn endpoint có phạm vi của từng module.

| Mã gõ | Cách tra |
|---|---|
| `SO…` (đơn) | `GET /api/sales/orders/?q=<mã>` rồi lọc dòng khớp đúng |
| `GH-…` (phiếu giao) | `GET /api/delivery/notes/?code=<mã>` (NV giao tra mã của người khác: không thấy) |
| mã lô | `GET /api/inventory/batches/<mã>/` |
| `PR-n` `KK-n` `RT-n` `#n` | mở thẳng trang chi tiết theo id (trang tự xử lý 404/403) |

Chuỗi không đúng mẫu mã (tên, SĐT, từ thường) giữ hành vi cũ (nhảy menu) và **không gọi API**. `app/(console)/layout.tsx` bọc `ConsoleCodeFinder` (client) để đưa `codeFinder`
vào `CodeFinderProvider`; các module được nạp bằng `import()` động.
