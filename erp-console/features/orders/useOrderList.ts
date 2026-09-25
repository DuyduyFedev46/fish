"use client";

// Danh sách đơn theo bộ lọc (S10) — dùng khung phân trang chung `usePagedList` (cùng cách tải với hàng chờ S12).
// Sau một thao tác trên chi tiết (S11) → `patch()` sửa đúng dòng đó tại chỗ, không tải lại cả danh sách (giữ vị trí cuộn).

import { listOrders } from "./api";
import type { OrderListItem, OrderListParams } from "./types";
import { usePagedList, type PagedState } from "./usePagedList";

export type OrderListState = PagedState<OrderListItem>;

export function useOrderList(params: OrderListParams, enabled: boolean) {
  return usePagedList<OrderListItem, OrderListParams>(listOrders, params, enabled);
}
