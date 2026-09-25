"use client";

// Bộ nhớ đệm nhỏ cho dữ liệu đọc (kiểu SWR tối giản), để nhiều màn/khung dùng CHUNG một response:
// cùng `key` thì chỉ 1 request đang bay, kết quả dùng lại trong `maxAgeMs`; `reload()` buộc tải lại
// và mọi nơi đang dùng key đó cùng cập nhật. Component unmount thì thôi nhận cập nhật (không setState sau unmount).
// Tải lại thất bại → GIỮ dữ liệu cũ, chỉ gắn `error` (màn tự quyết hiện gì).

import { useCallback, useEffect, useReducer, useRef } from "react";

type Entry = {
  data: unknown;
  error: unknown;
  at: number;
  inflight: Promise<void> | null;
  listeners: Set<() => void>;
};

const cache = new Map<string, Entry>();

function entryOf(key: string): Entry {
  let e = cache.get(key);
  if (!e) {
    e = { data: undefined, error: null, at: 0, inflight: null, listeners: new Set() };
    cache.set(key, e);
  }
  return e;
}

function notify(e: Entry) {
  e.listeners.forEach((fn) => fn());
}

function run(key: string, loader: () => Promise<unknown>, force: boolean, maxAgeMs: number): Promise<void> {
  const e = entryOf(key);
  if (e.inflight) return e.inflight;
  if (!force && e.at && e.error == null && Date.now() - e.at < maxAgeMs) return Promise.resolve();
  e.inflight = loader()
    .then(
      (data) => {
        e.data = data;
        e.error = null;
        e.at = Date.now();
      },
      (err) => {
        e.error = err;
      }
    )
    .finally(() => {
      e.inflight = null;
      notify(e);
    });
  notify(e);
  return e.inflight;
}

/** Xoá dữ liệu đã đệm (vd khi đổi người dùng). Người đang nghe vẫn giữ đăng ký. */
export function clearResources(): void {
  cache.forEach((e) => {
    e.data = undefined;
    e.error = null;
    e.at = 0;
  });
}

export type Resource<T> = {
  data: T | undefined;
  error: unknown;
  /** Đang có request bay (lần đầu hoặc tải lại). */
  loading: boolean;
  reload: () => Promise<void>;
};

/** key = null → không tải (vd chưa có `me`, hoặc thiếu quyền). */
export function useResource<T>(key: string | null, loader: () => Promise<T>, maxAgeMs = 30_000): Resource<T> {
  const [, rerender] = useReducer((x: number) => x + 1, 0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    if (!key) return;
    const e = entryOf(key);
    e.listeners.add(rerender);
    void run(key, () => loaderRef.current(), false, maxAgeMs);
    return () => {
      e.listeners.delete(rerender);
    };
  }, [key, maxAgeMs]);

  const reload = useCallback(
    () => (key ? run(key, () => loaderRef.current(), true, maxAgeMs) : Promise.resolve()),
    [key, maxAgeMs]
  );

  const e = key ? cache.get(key) : undefined;
  return { data: e?.data as T | undefined, error: e?.error ?? null, loading: !!e?.inflight, reload };
}
