"use client";

// Hai bảng phụ của trang chi tiết nhà cung cấp: Phiếu nhập (R10) và Lô đang bán (R5). Mỗi bảng tải riêng: một bảng lỗi hay
// bị 403 KHÔNG làm hỏng trang (bảng đó hiện câu lỗi + Thử lại, hoặc ẩn hẳn khi 403). `version` đổi → tải lại.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { usePagedList } from "@/shared/lib/usePagedList";
import { listSupplierBatches, listSupplierReceipts } from "./api";
import type { SupplierBatchRow, SupplierReceiptRow } from "./types";

/** Phiếu nhập của nhà cung cấp, "Tải thêm" 20 dòng/trang. `enabled=false` (thiếu quyền xem phiếu) → không gọi. */
export function useSupplierReceipts(supplierId: number, enabled: boolean) {
  const list = usePagedList<SupplierReceiptRow, { supplier: number }>(
    (p, page) => listSupplierReceipts(p.supplier, page),
    { supplier: supplierId },
    enabled,
  );
  const forbidden = list.error instanceof ApiError && list.error.status === 403;
  return { ...list, forbidden };
}

export type SupplierBatchesState = {
  rows: SupplierBatchRow[] | null;
  count: number;
  loading: boolean;
  error: unknown;
  forbidden: boolean;
  reload: () => void;
};

/** Lô còn hàng của nhà cung cấp (trang đầu). `version` đổi → tải lại (vd sau khi AI áp đề xuất). */
export function useSupplierBatches(supplierId: number, enabled: boolean, version: number): SupplierBatchesState {
  const [rows, setRows] = useState<SupplierBatchRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const seq = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    const n = ++seq.current;
    const c = new AbortController();
    setLoading(true);
    setError(null);
    listSupplierBatches(supplierId, c.signal)
      .then((res) => {
        if (n !== seq.current) return;
        setRows(res.results);
        setCount(res.count);
        setLoading(false);
      })
      .catch((err) => {
        if (n !== seq.current || c.signal.aborted) return;
        setError(err);
        setLoading(false);
      });
    return () => c.abort();
  }, [supplierId, enabled, version, attempt]);

  const reload = useCallback(() => setAttempt((a) => a + 1), []);
  return { rows, count, loading, error, forbidden: error instanceof ApiError && error.status === 403, reload };
}
