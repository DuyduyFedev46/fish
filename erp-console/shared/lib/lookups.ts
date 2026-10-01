// Thẻ tra nhanh (LookupCard): đọc một lô / mặt hàng / phiếu giao / đơn theo id, chỉ lấy vài trường tối thiểu để hiện popup,
// để các module KHÔNG import chéo nhau (UI-RULES §5.4: trường trỏ tới đối tượng khác là link, bấm mở popup của đối tượng đó).
// Quy tắc cứng:
//  - KHÔNG đọc giá vốn (landed_unit_cost…) dù BE có trả: danh sách trường dưới đây là danh sách cho phép.
//  - KHÔNG đọc tên / SĐT / địa chỉ khách của đơn hay phiếu giao; KHÔNG có thẻ khách hàng (không gọi API khách).
// Mỗi hàm là một lời gọi `apiFetch` có nhánh mock riêng (mockLookups.ts, bị cắt khỏi bản build thật).

import { apiFetch } from "./http";
import { ENUMS, enumOf, type EnumEntry } from "./enums";
import { dateTime, date, kg, vnd } from "./format";
import { mockLookup } from "./mockLookups";

export type LookupKind = "batch" | "item" | "delivery" | "order";

export type LookupRow = { label: string; value: string; mono?: boolean };

export type LookupCardData = {
  kind: LookupKind;
  /** Tiêu đề thẻ (mã chứng từ hoặc tên mặt hàng). */
  title: string;
  /** Chip trạng thái (nhãn + tông). */
  status?: EnumEntry;
  rows: LookupRow[];
  /** Trang đầy đủ của đối tượng và nhãn nút "Mở trang …". */
  href: string;
  hrefLabel: string;
};

const PATH: Record<LookupKind, (id: number | string) => string> = {
  batch: (id) => `/api/inventory/batches/${id}/`,
  item: (id) => `/api/catalog/items/${id}/`,
  delivery: (id) => `/api/delivery/notes/${id}/`,
  order: (id) => `/api/sales/orders/${id}/`,
};

/** Địa chỉ trang đầy đủ của từng loại (02b §2.1). */
export function lookupHref(kind: LookupKind, id: number | string): string {
  const base: Record<LookupKind, string> = {
    batch: "/inventory/detail/",
    item: "/catalog/detail/",
    delivery: "/deliveries/detail/",
    order: "/orders/detail/",
  };
  return `${base[kind]}?id=${encodeURIComponent(String(id))}`;
}

const HREF_LABEL: Record<LookupKind, string> = {
  batch: "Mở trang lô",
  item: "Mở trang mặt hàng",
  delivery: "Mở trang phiếu giao",
  order: "Mở trang đơn",
};

type Raw = Record<string, unknown>;
const str = (v: unknown): string => (typeof v === "string" ? v : typeof v === "number" ? String(v) : "");
const row = (label: string, value: string, mono = false): LookupRow | null => (value ? { label, value, mono } : null);
const compact = (rows: Array<LookupRow | null>): LookupRow[] => rows.filter((r): r is LookupRow => r !== null);

/** Rút dữ liệu thô của BE thành thẻ — CHỈ các trường trong danh sách cho phép. Xuất ra để vitest kiểm "không lộ giá vốn / khách". */
export function toLookupCard(kind: LookupKind, id: number | string, raw: Raw): LookupCardData {
  const href = lookupHref(kind, id);
  const hrefLabel = HREF_LABEL[kind];
  if (kind === "batch") {
    return {
      kind,
      title: str(raw.batch_id) || `Lô ${id}`,
      status: enumOf(ENUMS.batchStatus, str(raw.status)),
      rows: compact([
        row("Mặt hàng", str(raw.item_name) || str(raw.item_code)),
        row("Còn bán", raw.qty_available !== undefined ? kg(str(raw.qty_available)) : ""),
        row("Đang giữ", raw.qty_reserved !== undefined ? kg(str(raw.qty_reserved)) : ""),
        row("Nhập ngày", raw.received_date ? date(str(raw.received_date)) : ""),
        row("Hạn dùng", raw.expiry_date ? date(str(raw.expiry_date)) : ""),
        row("Kho", str(raw.warehouse_name)),
      ]),
      href,
      hrefLabel,
    };
  }
  if (kind === "item") {
    return {
      kind,
      title: str(raw.name) || `Mặt hàng ${id}`,
      status: enumOf(ENUMS.itemActive, raw.is_active === undefined ? "" : String(raw.is_active)),
      rows: compact([
        row("Mã", str(raw.code), true),
        row("Nhóm hàng", str(raw.group_name)),
        row("Loại", raw.item_type ? enumOf(ENUMS.itemType, str(raw.item_type)).label : ""),
      ]),
      href,
      hrefLabel,
    };
  }
  if (kind === "delivery") {
    const order = raw.order && typeof raw.order === "object" ? (raw.order as Raw) : null;
    return {
      kind,
      title: str(raw.code) || `Phiếu giao ${id}`,
      status: enumOf(ENUMS.deliveryStatus, str(raw.status)),
      rows: compact([
        row("Đơn", order ? str(order.code) : "", true),
        row("Hàng", str(raw.lines_summary)),
        row("Tổng", raw.total_kg !== undefined ? kg(str(raw.total_kg)) : ""),
        row("Tạo lúc", raw.created_at ? dateTime(str(raw.created_at)) : ""),
      ]),
      href,
      hrefLabel,
    };
  }
  return {
    kind,
    title: str(raw.code) || `Đơn ${id}`,
    status: enumOf(ENUMS.salesOrderStatus, str(raw.status)),
    rows: compact([
      row("Tổng tiền", raw.total_amount !== undefined ? vnd(str(raw.total_amount)) : ""),
      row("Tạo lúc", raw.created_at ? dateTime(str(raw.created_at)) : ""),
    ]),
    href,
    hrefLabel,
  };
}

/** Tải thẻ tra nhanh. 403/404 ném ApiError như mọi API khác — LookupCard hiện lỗi trong popup. */
export async function fetchLookup(kind: LookupKind, id: number | string, signal?: AbortSignal): Promise<LookupCardData> {
  const raw = await apiFetch<Raw>(PATH[kind](id), {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockLookup(kind, id) : undefined,
  });
  return toLookupCard(kind, id, raw);
}
