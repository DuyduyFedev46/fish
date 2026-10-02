"use client";

// Tải MỘT chứng từ cho trang chi tiết: giữ dữ liệu cũ khi tải lại (không nháy trắng), bỏ kết quả về trễ, không setState
// sau unmount. `status` gom các nhánh màn phải vẽ (đang tải · 403 · 404 · lỗi) để DetailGate không phải đoán.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";

export type DetailStatus = "loading" | "ok" | "forbidden" | "notfound" | "error";

export type DetailState<T> = {
  data: T | null;
  status: DetailStatus;
  error: unknown;
  /** Đang tải lại (đã có dữ liệu cũ). */
  reloading: boolean;
  /** Tải lại; trả dữ liệu mới (null khi lỗi) để màn dùng tiếp ngay. */
  reload: () => Promise<T | null>;
};

export function statusOfError(err: unknown): DetailStatus {
  if (err instanceof ApiError) {
    if (err.status === 403) return "forbidden";
    if (err.status === 404) return "notfound";
  }
  return "error";
}

export function useDetail<T>(id: number | null | undefined, loader: (id: number, signal: AbortSignal) => Promise<T>): DetailState<T> {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<DetailStatus>("loading");
  const [error, setError] = useState<unknown>(null);
  const [reloading, setReloading] = useState(false);
  const seq = useRef(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const idRef = useRef(id);
  idRef.current = id;
  const ctrl = useRef<AbortController | null>(null);

  const run = useCallback(async (keep: boolean): Promise<T | null> => {
    const cur = idRef.current;
    if (!cur) return null;
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
      const d = await loaderRef.current(cur, c.signal);
      if (n !== seq.current) return null;
      setData(d);
      setStatus("ok");
      setReloading(false);
      return d;
    } catch (err) {
      if (n !== seq.current || c.signal.aborted) return null;
      if (err instanceof ApiError && err.status === 401) return null; // đã về màn đăng nhập
      setError(err);
      setReloading(false);
      // Tải lại lỗi mà vẫn còn dữ liệu cũ → giữ màn cũ (status ok), chỉ báo lỗi qua `error`.
      setStatus((s) => (keep && s === "ok" ? "ok" : statusOfError(err)));
      return null;
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
