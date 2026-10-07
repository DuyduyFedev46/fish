// Nối ⌘K với từng module để tra chứng từ theo MÃ (ED-07, Lô 17b H1). Chỉ gọi các hàm `find…IdByCode` đã có phạm vi ở BE:
// đơn qua `GET orders/?q=`, phiếu giao qua `GET delivery/notes/?code=`, lô qua `GET inventory/batches/<mã>/`.
// Chuỗi không đúng mẫu mã không bao giờ tới đây (shared/lib/codeLookup.ts chặn trước).
//
// Nạp module bằng `import()` ĐỘNG: layout (console) dùng file này ở mọi trang, mà api của các module kéo theo mock và (khi bật mock) mã
// khởi tạo kho mock của chúng. Nạp tĩnh sẽ làm mọi trang gieo kho mock đơn hàng vào sessionStorage dù chưa ai mở màn Đơn.

import type { CodeFinder } from "@/shared/lib/codeLookup";

export const codeFinder: CodeFinder = {
  order: async (code, signal) => (await import("@/features/orders/api")).findOrderIdByCode(code, signal),
  note: async (code, signal) => (await import("@/features/deliveries/api")).findDeliveryNoteIdByCode(code, signal),
  batch: async (code, signal) => (await import("@/features/inventory/api")).findBatchIdByCode(code, signal),
};
