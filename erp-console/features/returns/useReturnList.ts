"use client";

// Danh sách phiếu hàng hoàn theo trạng thái + tháng (ED-26) — khung phân trang chung `usePagedList` ("Tải thêm", bỏ kết quả trễ, dải mất mạng).

import { usePagedList } from "@/shared/lib/usePagedList";
import { listReturns } from "./api";
import type { ReturnItem, ReturnListParams } from "./types";

export function useReturnList(params: ReturnListParams, enabled: boolean) {
  return usePagedList<ReturnItem, ReturnListParams>(listReturns, params, enabled);
}
