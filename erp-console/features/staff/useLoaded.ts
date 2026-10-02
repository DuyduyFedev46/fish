"use client";

// Hook tải dữ liệu dùng chung cho Nhân sự và Phân quyền (Phân quyền import từ đây, không ngược lại). Không cache giữa các màn:
// sau mỗi thao tác của Chủ màn phải thấy đúng số của BE. Giữ dữ liệu cũ khi tải lại (không nháy trắng), bỏ kết quả về trễ,
// không setState sau unmount. `status` gom các nhánh màn phải vẽ: đang tải · 403 · 404 · lỗi. Không log, không ghi storage.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";

export type LoadStatus = "loading" | "ok" | "forbidden" | "notfound" | "error";

export type Loaded<T> = {
  data: T | null;
  status: LoadStatus;
  error: unknown;
  /** Đang tải lại (đã có dữ liệu cũ). */
  reloading: boolean;
  reload: () => Promise<void>;
  /** Thay dữ liệu bằng bản BE vừa trả (sau PUT) mà khỏi gọi lại. */
  replace: (next: T) => void;
};

export function statusOfError(err: unknown): LoadStatus {
  if (err instanceof ApiError) {
    if (err.status === 403) return "forbidden";
    if (err.status === 404) return "notfound";
  }
  return "error";
}

/** `key` null = chưa tải (chưa biết người dùng / chưa có id). `key` đổi = tải lại từ đầu. */
export function useLoaded<T>(key: string | null, load: (signal: AbortSignal) => Promise<T>): Loaded<T> {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<unknown>(null);
  const [reloading, setReloading] = useState(false);
  const seq = useRef(0);
  const ctrl = useRef<AbortController | null>(null);
  const loadRef = useRef(load);
  loadRef.current = load;

  const run = useCallback(async (keep: boolean): Promise<void> => {
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
      const d = await loadRef.current(c.signal);
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
    if (key === null) return;
    void run(false);
    return () => {
      seq.current += 1;
      ctrl.current?.abort();
    };
  }, [key, run]);

  const reload = useCallback(() => run(true), [run]);
  const replace = useCallback((next: T) => {
    setData(next);
    setStatus("ok");
    setError(null);
  }, []);
  return { data, status, error, reloading, reload, replace };
}
