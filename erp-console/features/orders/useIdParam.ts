"use client";

// Đọc `?id=` của trang chi tiết (export tĩnh không có đường dẫn động: /orders/detail/?id=<pk>). Không dùng
// useSearchParams để khỏi cần Suspense ở trang tĩnh. Lần vẽ đầu = undefined (khớp HTML tĩnh), rồi đọc URL sau mount;
// popstate đọc lại. Trong URL chỉ có id số, không bao giờ có SĐT hay tên khách.

import { useEffect, useState } from "react";

/** `?id=12` → 12; thiếu, không phải số nguyên dương → null. */
export function parseId(search: string, key = "id"): number | null {
  const raw = new URLSearchParams(search).get(key);
  if (!raw || !/^\d{1,12}$/.test(raw)) return null;
  const n = Number(raw);
  return n > 0 ? n : null;
}

/** `undefined` = chưa đọc URL (đang dựng trang); `null` = URL không có id hợp lệ. */
export function useIdParam(key = "id"): number | null | undefined {
  const [id, setId] = useState<number | null | undefined>(undefined);
  useEffect(() => {
    const sync = () => setId(parseId(window.location.search, key));
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [key]);
  return id;
}
