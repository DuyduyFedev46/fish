"use client";

// Đọc `?id=` và tải MỘT khách cho trang chi tiết (ED-14). URL chỉ có id số, không bao giờ có tên/SĐT/địa chỉ.
// `status` gom các nhánh màn phải vẽ (đang tải · 403 · 404 · lỗi). Giữ dữ liệu cũ khi tải lại (không nháy trắng),
// bỏ kết quả về trễ, không setState sau unmount. Không log, không ghi storage.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { getCustomer } from "./api";
import type { CustomerDetail } from "./types";

/** `?id=12` → 12; thiếu hoặc không phải số nguyên dương → null. */
export function parseCustomerId(search: string): number | null {
  const raw = new URLSearchParams(search).get("id");
  if (!raw || !/^\d{1,12}$/.test(raw)) return null;
  const n = Number(raw);
  return n > 0 ? n : null;
}

/** `undefined` = chưa đọc URL (đang dựng trang); `null` = URL không có id hợp lệ. */
export function useCustomerId(): number | null | undefined {
  const [id, setId] = useState<number | null | undefined>(undefined);
  useEffect(() => {
    const sync = () => setId(parseCustomerId(window.location.search));
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  return id;
}

export type CustomerDetailStatus = "loading" | "ok" | "forbidden" | "notfound" | "error" | "scope_lost";

export function statusOfError(err: unknown): CustomerDetailStatus {
  if (err instanceof ApiError) {
    if (err.status === 403) return "forbidden";
    if (err.status === 404) return "notfound";
  }
  return "error";
}

export type CustomerDetailState = {
  data: CustomerDetail | null;
  status: CustomerDetailStatus;
  error: unknown;
  /** Đang tải lại (đã có dữ liệu cũ). */
  reloading: boolean;
  reload: () => Promise<void>;
};

export function useCustomerDetail(id: number | null | undefined): CustomerDetailState {
  const [data, setData] = useState<CustomerDetail | null>(null);
  const [status, setStatus] = useState<CustomerDetailStatus>("loading");
  const statusRef = useRef<CustomerDetailStatus>("loading");
  const put = useCallback((st: CustomerDetailStatus) => {
    statusRef.current = st;
    setStatus(st);
  }, []);
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
      put("loading");
    }
    setError(null);
    try {
      const d = await getCustomer(cur, c.signal);
      if (n !== seq.current) return;
      setData(d);
      put("ok");
      setReloading(false);
    } catch (err) {
      if (n !== seq.current || c.signal.aborted) return;
      if (err instanceof ApiError && err.status === 401) return; // đã về màn đăng nhập
      setError(err);
      setReloading(false);
      // PV-13: đã có dữ liệu mà tải lại bị 404 = mục đã ra ngoài phạm vi của người xem → XOÁ dữ liệu (không giữ tên/SĐT/địa chỉ
      // khách đã tải), màn chuyển sang "mất quyền". Chỉ 404; 403/500/mạng giữ màn cũ và báo lỗi qua `error`.
      if (keep && err instanceof ApiError && err.status === 404 && (statusRef.current === "ok" || statusRef.current === "scope_lost")) {
        setData(null);
        put("scope_lost");
        return;
      }
      // Tải lại lỗi mà còn dữ liệu cũ → giữ màn cũ (status ok), chỉ báo lỗi qua `error`.
      put(keep && statusRef.current === "ok" ? "ok" : statusOfError(err));
    }
  }, [put]);

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
