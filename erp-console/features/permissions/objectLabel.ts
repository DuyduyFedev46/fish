// Tra nhãn tiếng Việt cho khoá trong `widened` (hộp "Cho thêm người xem dữ liệu khách?"), dùng chung ma trận và trang nhóm (Lô 6, B1).
// Khoá có thể là đối tượng phạm vi (`invoices`) hoặc việc V2 (`view_order_customer_info`): tra `data_scopes` trước, rồi registry GỐC
// (chưa lọc AI, để nhãn vẫn tra được dù việc đang bị ẩn). Không bao giờ trả khoá thô cho người dùng.
import type { DataScopeRow, RegistryItem } from "./types";

export const UNKNOWN_OBJECT_LABEL = "một phạm vi dữ liệu";

export function objectLabelOf(key: string, dataScopes: readonly Pick<DataScopeRow, "key" | "label">[] | undefined, registry: readonly Pick<RegistryItem, "key" | "label">[] | undefined): string {
  return dataScopes?.find((r) => r.key === key)?.label ?? registry?.find((r) => r.key === key)?.label ?? UNKNOWN_OBJECT_LABEL;
}
