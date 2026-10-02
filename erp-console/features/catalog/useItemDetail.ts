"use client";

// Đọc `?id=` và tải MỘT mặt hàng cho trang chi tiết (ED-30). URL chỉ có id số. `status` gom các nhánh màn phải vẽ
// (đang tải · 403 · 404 · lỗi). Giữ dữ liệu cũ khi tải lại (không nháy trắng), bỏ kết quả về trễ, không setState sau unmount.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { getItem } from "./api";
import { parseItemId } from "./catalogModel";
import type { CatalogItem } from "./types";

/** `undefined` = chưa đọc URL (đang dựng trang); `null` = URL không có id hợp lệ. */
export function useItemId(): number | null | undefined {
  const [id, setId] = useState<number | null | undefined>(undefined);
  useEffect(() => {
    const sync = () => setId(parseItemId(window.location.search));
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  return id;
}

export type ItemDetailStatus = "loading" | "ok" | "forbidden" | "notfound" | "error";

export function statusOfError(err: unknown): ItemDetailStatus {
  if (err instanceof ApiError) {
    if (err.status === 403) return "forbidden";
    if (err.status === 404) return "notfound";
  }
  return "error";
}

export type ItemDetailState = {
  data: CatalogItem | null;
  status: ItemDetailStatus;
  error: unknown;
  /** Đang tải lại (đã có dữ liệu cũ). */
  reloading: boolean;
  reload: () => Promise<void>;
};

export function useItemDetail(id: number | null | undefined): ItemDetailState {
  const [data, setData] = useState<CatalogItem | null>(null);
  const [status, setStatus] = useState<ItemDetailStatus>("loading");
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
      const d = await getItem(cur, c.signal);
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
