"use client";

// Đọc `?id=` và tải MỘT phiếu hàng hoàn cho trang chi tiết (ED-26). URL chỉ có id số.
// `status` gom các nhánh màn phải vẽ (đang tải · 403 · 404 · lỗi). Giữ dữ liệu cũ khi tải lại (không nháy trắng),
// bỏ kết quả về trễ, không setState sau unmount. Không log, không ghi storage.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { getReturn } from "./api";
import { parseReturnId } from "./returnsModel";
import type { ReturnItem } from "./types";

/** `undefined` = chưa đọc URL (đang dựng trang); `null` = URL không có id hợp lệ. */
export function useReturnId(): number | null | undefined {
  const [id, setId] = useState<number | null | undefined>(undefined);
  useEffect(() => {
    const sync = () => setId(parseReturnId(window.location.search));
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  return id;
}

export type ReturnDetailStatus = "loading" | "ok" | "forbidden" | "notfound" | "error";

export function statusOfError(err: unknown): ReturnDetailStatus {
  if (err instanceof ApiError) {
    if (err.status === 403) return "forbidden";
    if (err.status === 404) return "notfound";
  }
  return "error";
}

export type ReturnDetailState = {
  data: ReturnItem | null;
  status: ReturnDetailStatus;
  error: unknown;
  /** Đang tải lại (đã có dữ liệu cũ). */
  reloading: boolean;
  reload: () => Promise<void>;
};

export function useReturnDetail(id: number | null | undefined): ReturnDetailState {
  const [data, setData] = useState<ReturnItem | null>(null);
  const [status, setStatus] = useState<ReturnDetailStatus>("loading");
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
      const d = await getReturn(cur, c.signal);
      if (n !== seq.current) return;
      setData(d);
      setStatus("ok");
      setReloading(false);
    } catch (err) {
      if (n !== seq.current || c.signal.aborted) return;
      if (err instanceof ApiError && err.status === 401) return; // đã về màn đăng nhập
      setError(err);
      setReloading(false);
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
