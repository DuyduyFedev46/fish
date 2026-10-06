// Kho nối hai mock "Đơn" và "Giao hàng" (W37 S6-AC8). CHỈ được import từ features/<x>/mock.ts: các file đó chỉ chạy khi
// NEXT_PUBLIC_USE_MOCK=1, nên bản build thật không chứa file này (tiền lệ: dashboardSummary.mock.ts). File không có seed,
// chỉ có hộp thư trao đổi giữa hai mock:
//  - Giao hàng → Đơn: mỗi lần phiếu đổi trạng thái, mock Giao hàng gửi kết quả (đơn nào, phiếu ra sao, đơn thành gì theo
//    BR-BH-18). Mock Đơn đọc hộp thư ở lần tải kế tiếp và áp vào đơn cùng `id` rồi bỏ khỏi hộp.
//  - Đơn → Giao hàng: mock Đơn báo đơn nào đã huỷ, để mock Giao hàng chặn như BE (BR-GH-24) kể cả khi phiếu cũ chưa huỷ.
// Lưu ở sessionStorage để qua được lần tải lại trang; mất khi đóng tab (giống kho mock Đơn).

export type DeliveryOutcome = {
  orderId: number;
  /** Trạng thái phiếu vừa chuyển tới (READY, DELIVERING, COMPLETED, FAILED…). */
  deliveryStatus: string;
  /** Trạng thái đơn sau lần chuyển theo luật dùng chung (`isDeliveryFinished`). */
  orderStatus: string;
};

const KEY = "cave_erp_mock_order_link";
type Box = { outcomes: DeliveryOutcome[]; cancelled: number[] };

function ss(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

// Bản trong bộ nhớ: dùng khi không có sessionStorage (vitest chạy trong node) và làm chỗ dự phòng.
let memory: Box = { outcomes: [], cancelled: [] };

function read(): Box {
  try {
    const raw = ss()?.getItem(KEY);
    if (raw) {
      const b = JSON.parse(raw) as Partial<Box>;
      return { outcomes: Array.isArray(b.outcomes) ? b.outcomes : [], cancelled: Array.isArray(b.cancelled) ? b.cancelled : [] };
    }
  } catch {
    /* hỏng → hộp rỗng */
  }
  return { outcomes: [...memory.outcomes], cancelled: [...memory.cancelled] };
}

function write(b: Box): void {
  memory = b;
  try {
    ss()?.setItem(KEY, JSON.stringify(b));
  } catch {
    /* bỏ qua */
  }
}

export function publishDeliveryOutcome(o: DeliveryOutcome): void {
  const b = read();
  b.outcomes.push(o);
  write(b);
}

/** Lấy hết kết quả giao hàng chưa áp (và xoá khỏi hộp). */
export function drainDeliveryOutcomes(): DeliveryOutcome[] {
  const b = read();
  if (!b.outcomes.length) return [];
  write({ ...b, outcomes: [] });
  return b.outcomes;
}

export function publishOrderCancelled(orderId: number): void {
  const b = read();
  if (!b.cancelled.includes(orderId)) write({ ...b, cancelled: [...b.cancelled, orderId] });
}

export function isOrderCancelledInMock(orderId: number | null | undefined): boolean {
  return orderId != null && read().cancelled.includes(orderId);
}

/** Xoá hộp (mock Đơn gieo lại kho thì kết quả cũ không còn nghĩa). */
export function resetOrderLink(): void {
  write({ outcomes: [], cancelled: [] });
}
