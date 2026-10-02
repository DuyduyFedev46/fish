"use client";

// Danh sách nhà cung cấp theo từ khoá + loại + trạng thái (ED-22) — dùng khung phân trang chung `usePagedList` ("Tải thêm",
// bỏ kết quả trễ, đăng ký dải mất mạng). Từ khoá chỉ đi vào query của request, không vào URL trang hay storage.

import { usePagedList } from "@/shared/lib/usePagedList";
import { listSuppliers } from "./api";
import type { Supplier, SupplierListParams } from "./types";

export function useSupplierList(params: SupplierListParams, enabled: boolean) {
  return usePagedList<Supplier, SupplierListParams>(listSuppliers, params, enabled);
}
