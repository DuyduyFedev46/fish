// Kiểu dữ liệu Kiểm kê (ED-28). Dựng theo contract THẬT của BE (backend/apps/inventory/stocktake/serializers.py):
// GET/POST /api/inventory/reconciliations/ …  Không có trường tiền nào: tồn và chênh lệch chỉ tính bằng kg, nên
// không có giá vốn để ẩn (bất biến 1). Không có dữ liệu khách (bất biến 9): chỉ có tên hiển thị của NHÂN VIÊN.
// Số kg là chuỗi thập phân 3 chữ số ("18.500"); không cộng trừ bằng float (xem stocktakeUi.ts).

// Luồng Nháp → Chờ duyệt → Đã duyệt (Duy chốt 02/10, #6/#20).
export type StocktakeStatus = "DRAFT" | "SUBMITTED" | "APPROVED";

/** Việc người xem được làm trên phiếu (BE suy ra từ quyền + BR-KK-02/08). */
export type StocktakeAction = "edit_lines" | "submit" | "return_to_draft" | "approve";

export type StaffRef = { id: number; display_name: string };

export type StocktakeListItem = {
  id: number;
  /** "KK-<id>". */
  code: string;
  /** Ngày kiểm kê, "yyyy-mm-dd". */
  count_date: string;
  status: StocktakeStatus;
  status_label: string;
  note: string;
  created_by: StaffRef | null;
  approved_by: StaffRef | null;
  approved_at: string | null;
  updated_at: string;
  /** Tên người thao tác gần nhất (nhân viên, "Hệ thống" hoặc "AI của …"). */
  updated_by_name: string;
  warehouse_names: string[];
  line_count: number;
  short_count: number;
  over_count: number;
  match_count: number;
  short_qty: string;
  over_qty: string;
  net_difference: string;
  available_actions: StocktakeAction[];
  // BE vẫn gửi `approve_blocked_reason` (luôn null từ 02/10: bỏ BR-KK-02/08). FE không đọc nữa.
};

export type StocktakeLine = {
  id: number;
  batch: number;
  batch_code: string;
  item_name: string;
  warehouse_name: string;
  system_qty: string;
  counted_qty: string;
  difference_qty: string;
  reason: string;
};

export type StocktakeDetail = StocktakeListItem & { lines: StocktakeLine[] };

/** Một dòng gửi lên BE. `system_qty` do BE tự chụp, client không gửi. */
export type StocktakeLineInput = { batch: number; counted_qty: string; reason: string };

export type StocktakeCreateInput = { count_date: string; note: string; lines?: StocktakeLineInput[] };

/** Lô còn tồn để đếm (GET /api/inventory/batches/?warehouse=&has_stock=1). Chỉ giữ các trường kg; KHÔNG giữ giá vốn. */
export type BatchOption = {
  id: number;
  batch_id: string;
  item_name: string;
  warehouse: number;
  warehouse_name: string;
  qty_available: string;
};

export type WarehouseOption = { id: number; name: string };
