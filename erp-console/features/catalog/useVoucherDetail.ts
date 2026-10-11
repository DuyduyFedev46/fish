"use client";

// Tải MỘT mã giảm giá cho trang sửa (`?id=`, SHOP-3b-02). URL chỉ có id số. Gom các nhánh màn phải vẽ: đang tải, 403, 404, lỗi.
// Bỏ kết quả về trễ, không setState sau khi rời trang.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { getVoucher } from "./api";
import { parseItemId } from "./catalogModel";
import type { Voucher } from "./types";

export type VoucherDetailStatus = "loading" | "ok" | "forbidden" | "notfound" | "error";

/** `undefined` = chưa đọc URL; `null` = URL không có id hợp lệ. */
export function useVoucherId(): number | null | undefined {
  const [id, setId] = useState<number | null | undefined>(undefined);
  useEffect(() => {
    setId(parseItemId(window.location.search));
  }, []);
  return id;
}

export function useVoucherDetail(id: number | null | undefined) {
  const [data, setData] = useState<Voucher | null>(null);
  const [status, setStatus] = useState<VoucherDetailStatus>("loading");
  const seq = useRef(0);

  const load = useCallback(async () => {
    if (!id) return;
    const n = ++seq.current;
    setStatus("loading");
    try {
      const v = await getVoucher(id);
      if (n !== seq.current) return;
      setData(v);
      setStatus("ok");
    } catch (err) {
      if (n !== seq.current) return;
      if (err instanceof ApiError && err.status === 401) return; // đã về màn đăng nhập
      setStatus(err instanceof ApiError && err.status === 403 ? "forbidden" : err instanceof ApiError && err.status === 404 ? "notfound" : "error");
    }
  }, [id]);

  useEffect(() => {
    void load();
    return () => {
      seq.current += 1;
    };
  }, [load]);

  return { data, status, reload: load, setData };
}
