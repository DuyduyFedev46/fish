"use client";

// Nguồn dữ liệu cho dải mất mạng chung (UI-RULES §7, ED-03-AC4). Shell đặt MỘT dải; màn đang hiển thị dữ liệu
// "đăng ký" mốc dữ liệu (`asOf`) và hàm tải lại (`onRetry`) để dải ghi "Dữ liệu lúc dd/mm/yyyy hh:mm" và có nút Thử lại.
// Kho nhỏ ở mức module (không cần Provider, nên ListPage / usePagedList dùng được ở mọi nơi). Nhiều màn cùng đăng ký
// (vd màn + khối con) thì lấy cái đăng ký SAU CÙNG. Màn rời đi thì gỡ đăng ký.
import { useEffect, useRef, useSyncExternalStore } from "react";

export type OfflineSource = {
  /** Mốc dữ liệu đang hiển thị (ISO; `as_of` của BE hoặc giờ tải xong). */
  asOf?: string | null;
  /** Hàm tải lại dữ liệu của màn. */
  onRetry?: () => void;
};

type Entry = { id: number; asOf: string | null; retry: (() => void) | null };

let entries: Entry[] = [];
let snapshot: OfflineSource | null = null;
let nextId = 1;
const listeners = new Set<() => void>();

function publish() {
  const last = entries[entries.length - 1];
  snapshot = last ? { asOf: last.asOf, onRetry: last.retry ?? undefined } : null;
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** Đọc nguồn đang đăng ký (dùng trong dải mất mạng). */
export function useOfflineSource(): OfflineSource | null {
  return useSyncExternalStore(
    subscribe,
    () => snapshot,
    () => null,
  );
}

/**
 * Màn đang hiển thị dữ liệu gọi hàm này để dải mất mạng biết mốc dữ liệu và cách tải lại.
 * Truyền `null` (hoặc không có cả `asOf` lẫn `onRetry`) = không đăng ký.
 */
export function useOfflineRegistration(source: OfflineSource | null): void {
  const retryRef = useRef<(() => void) | undefined>(undefined);
  retryRef.current = source?.onRetry;
  const active = !!source && (!!source.asOf || !!source.onRetry);
  const hasRetry = !!source?.onRetry;
  const asOf = source?.asOf ?? null;

  useEffect(() => {
    if (!active) return;
    const id = nextId++;
    entries = [...entries, { id, asOf, retry: hasRetry ? () => retryRef.current?.() : null }];
    publish();
    return () => {
      entries = entries.filter((e) => e.id !== id);
      publish();
    };
  }, [active, asOf, hasRetry]);
}

/** Chỉ để test: xoá toàn bộ đăng ký. */
export function resetOfflineSourcesForTest(): void {
  entries = [];
  publish();
}
