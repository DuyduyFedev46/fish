"use client";

// Đọc `?id=` và tải MỘT nhà cung cấp cho trang chi tiết (ED-22). URL chỉ có id số, không bao giờ có tên hay số điện thoại.
// `status` gom các nhánh màn phải vẽ (đang tải · 403 · 404 · lỗi). Giữ dữ liệu cũ khi tải lại (không nháy trắng),
// bỏ kết quả về trễ, không setState sau unmount. Không log, không ghi storage.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { getSupplier } from "./api";
import type { Supplier } from "./types";

/** `?id=12` → 12; thiếu hoặc không phải số nguyên dương → null. */
export function parseSupplierId(search: string): number | null {
  const raw = new URLSearchParams(search).get("id");
  if (!raw || !/^\d{1,12}$/.test(raw)) return null;
  const n = Number(raw);
  return n > 0 ? n : null;
}

/** `undefined` = chưa đọc URL (đang dựng trang); `null` = URL không có id hợp lệ. */
export function useSupplierId(): number | null | undefined {
  const [id, setId] = useState<number | null | undefined>(undefined);
  useEffect(() => {
    const sync = () => setId(parseSupplierId(window.location.search));
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  return id;
}

export type SupplierDetailStatus = "loading" | "ok" | "forbidden" | "notfound" | "error";

export function statusOfError(err: unknown): SupplierDetailStatus {
  if (err instanceof ApiError) {
    if (err.status === 403) return "forbidden";
    if (err.status === 404) return "notfound";
  }
  return "error";
}

export type SupplierDetailState = {
  data: Supplier | null;
  status: SupplierDetailStatus;
  error: unknown;
  /** Đang tải lại (đã có dữ liệu cũ). */
  reloading: boolean;
  reload: () => Promise<void>;
};

export function useSupplierDetail(id: number | null | undefined): SupplierDetailState {
  const [data, setData] = useState<Supplier | null>(null);
  const [status, setStatus] = useState<SupplierDetailStatus>("loading");
  const [error, setError] = useState<unknown>(null);
  const [reloading, setReloading] = useState(false);
  const seq = useRef(0);
  const idRef = useRef(id);
  idRef.current = id;
  const ctrl = useRef<AbortController | null>(null);

  const run = useCallback(async (keep: boolean): Promise<void> => {
    const cur = idRef.current;
    if (!cur) return;
    const n = ++seq.current;
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    if (keep) setReloading(true);
    else {
      setData(null);
      setStatus("loading");
    }
    setError(null);
    try {
      const d = await getSupplier(cur, c.signal);
      if (n !== seq.current) return;
      setData(d);
      setStatus("ok");
      setReloading(false);
    } catch (err) {
      if (n !== seq.current || c.signal.aborted) return;
      if (err instanceof ApiError && err.status === 401) return; // đã về màn đăng nhập
      setError(err);
      setReloading(false);
      // Tải lại lỗi mà còn dữ liệu cũ → giữ màn cũ, chỉ báo lỗi qua `error`.
      setStatus((s) => (keep && s === "ok" ? "ok" : statusOfError(err)));
    }
  }, []);

  useEffect(() => {
    if (!id) return;
    void run(false);
    return () => {
      seq.current += 1;
      ctrl.current?.abort();
    };
  }, [id, run]);

  const reload = useCallback(() => run(true), [run]);
  return { data, status, error, reloading, reload };
}
