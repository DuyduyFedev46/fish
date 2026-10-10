// Chỉ dùng trong test vitest (môi trường node, không có jsdom / testing-library): bộ hook React giả đủ để chạy các
// hook tải dữ liệu (useState · useRef · useCallback · useMemo · useEffect) và quan sát chuyển trạng thái.
// Dùng: vi.mock("react", async () => (await import("@/shared/lib/fakeReactHooks")).fakeReact);
// rồi `renderHook(() => useDetail(...))`. Không import "react" ở đây để tránh vòng lặp với vi.mock.

type Slot = { value?: unknown; set?: (u: unknown) => void; deps?: unknown[]; cleanup?: (() => void) | void; memo?: unknown; ref?: { current: unknown } };
type Instance = { slots: Slot[]; idx: number; pending: Array<() => void>; render: () => void; mounted: boolean };

let current: Instance | null = null;

function slot(): Slot {
  const inst = current as Instance;
  const s = inst.slots[inst.idx] ?? (inst.slots[inst.idx] = {});
  inst.idx += 1;
  return s;
}

const same = (a?: unknown[], b?: unknown[]) => !!a && !!b && a.length === b.length && a.every((x, i) => Object.is(x, b[i]));

function useState<T>(init: T | (() => T)): [T, (u: T | ((p: T) => T)) => void] {
  const inst = current as Instance;
  const s = slot();
  if (!("value" in s)) s.value = typeof init === "function" ? (init as () => T)() : init;
  if (!s.set) {
    s.set = (u) => {
      const next = typeof u === "function" ? (u as (p: unknown) => unknown)(s.value) : u;
      if (Object.is(next, s.value)) return;
      s.value = next;
      if (inst.mounted) inst.render();
    };
  }
  return [s.value as T, s.set as (u: T | ((p: T) => T)) => void];
}

function useRef<T>(init: T): { current: T } {
  const s = slot();
  if (!s.ref) s.ref = { current: init };
  return s.ref as { current: T };
}

function useMemo<T>(fn: () => T, deps: unknown[]): T {
  const s = slot();
  if (!same(s.deps, deps)) {
    s.memo = fn();
    s.deps = deps;
  }
  return s.memo as T;
}

function useCallback<T>(fn: T, deps: unknown[]): T {
  return useMemo(() => fn, deps);
}

function useEffect(fn: () => void | (() => void), deps?: unknown[]): void {
  const inst = current as Instance;
  const s = slot();
  if (deps && same(s.deps, deps)) return;
  s.deps = deps;
  inst.pending.push(() => {
    if (typeof s.cleanup === "function") s.cleanup();
    s.cleanup = fn();
  });
}

export const fakeReact = { useState, useRef, useMemo, useCallback, useEffect, useLayoutEffect: useEffect };

export type RenderedHook<R> = { readonly result: R; rerender: () => void; unmount: () => void };

/** Dựng hook một lần (chạy effect như lúc mount). Trả `result` luôn là giá trị mới nhất. */
export function renderHook<R>(hook: () => R): RenderedHook<R> {
  let result: R;
  const inst: Instance = { slots: [], idx: 0, pending: [], mounted: false, render: () => undefined };
  inst.render = () => {
    const prev = current;
    current = inst;
    inst.idx = 0;
    try {
      result = hook();
    } finally {
      current = prev;
    }
    inst.mounted = true;
    const effects = inst.pending.splice(0);
    effects.forEach((e) => e());
  };
  inst.render();
  return {
    get result() {
      return result;
    },
    rerender: () => inst.render(),
    unmount: () => {
      inst.slots.forEach((s) => {
        if (typeof s.cleanup === "function") s.cleanup();
      });
      inst.mounted = false;
    },
  };
}

/** Chờ các promise đang bay (loader giả) xong. */
export const flush = () => new Promise<void>((r) => setTimeout(r, 0));
