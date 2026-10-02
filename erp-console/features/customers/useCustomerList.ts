"use client";

// Danh sách khách theo từ khoá + thứ tự (ED-14) — dùng khung phân trang chung `usePagedList` ("Tải thêm", bỏ kết quả trễ,
// đăng ký dải mất mạng). Từ khoá chỉ đi vào query của request, không vào URL trang hay storage.

import { usePagedList } from "@/shared/lib/usePagedList";
import { listCustomers } from "./api";
import type { CustomerListItem, CustomerListParams } from "./types";

export function useCustomerList(params: CustomerListParams, enabled: boolean) {
  return usePagedList<CustomerListItem, CustomerListParams>(listCustomers, params, enabled);
}
