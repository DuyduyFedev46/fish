"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Money, SaleUnit } from "@/lib/types";

/**
 * Một dòng giỏ. Chỉ giữ mã hàng, tên, đơn vị, giá lúc thêm và số lượng; không bao giờ có tên, SĐT hay địa chỉ
 * khách (bất biến 9, SHOP-1-01 AC6). `min_qty`/`qty_step` không lưu: màn giỏ lấy từ catalog, thiếu thì theo đơn vị.
 */
export type CartEntry = {
  item_code: string;
  name: string;
  unit: SaleUnit;
  /** Giá lúc thêm (chuỗi số nguyên đồng). Màn giỏ so với catalog để báo đổi giá. */
  price: Money;
  qty: number;
};

/** Dữ liệu một món khi thêm vào giỏ (không gồm số lượng). */
export type CartEntryInput = Omit<CartEntry, "qty">;

type CartContextValue = {
  lines: CartEntry[];
  /** false cho tới khi đã đọc xong giỏ trong trình duyệt (tránh nháy "giỏ trống"). */
  ready: boolean;
  /** Thêm `qty`; món đã có thì cộng dồn. */
  addItem: (item: CartEntryInput, qty: number) => void;
  /** Đặt đúng số lượng cho một dòng (không cộng dồn). Số ≤ 0 thì bỏ dòng. */
  setQty: (itemCode: string, qty: number) => void;
  removeItem: (itemCode: string) => void;
  /** Cập nhật hàng loạt (màn giỏ chỉnh số lượng cũ, ghi giá mới). Trả về mảng mới. */
  updateEntries: (updater: (prev: CartEntry[]) => CartEntry[]) => void;
  clear: () => void;
  /** Số món (số dòng): giá trị của badge giỏ (UI-RULES §4.4). */
  lineCount: number;
  /** Tạm tính theo giá lúc thêm. Chỉ để xem; tổng thật do máy chủ tính lúc đặt. */
  totalAmount: number;
};

const CartContext = createContext<CartContextValue | null>(null);

const STORAGE_KEY = "cangcaloc_cart_v1";

/** Đọc giỏ từ chuỗi đã lưu; chuỗi hỏng hay dòng sai dạng thì bỏ qua, không bao giờ ném lỗi (SHOP-1-01 AC7). */
export function parseStoredCart(raw: string | null): CartEntry[] {
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const lines: CartEntry[] = [];
  for (const entry of parsed) {
    if (!entry || typeof entry !== "object") continue;
    const e = entry as Record<string, unknown>;
    const qty = Number(e.qty);
    // Giỏ cũ lưu giá dạng số hoặc chuỗi Decimal ("260000.00") -> chuẩn về chuỗi đồng nguyên.
    const price = Number(e.price);
    if (typeof e.item_code !== "string" || !e.item_code) continue;
    if (!Number.isFinite(qty) || qty <= 0) continue;
    // Giỏ cũ ghi unit "Kg"; chỉ "combo" là combo.
    const unit: SaleUnit = typeof e.unit === "string" && e.unit.toLowerCase() === "combo" ? "combo" : "kg";
    lines.push({
      item_code: e.item_code,
      name: typeof e.name === "string" ? e.name : e.item_code,
      unit,
      price: Number.isFinite(price) && price >= 0 ? String(Math.round(price)) : "0",
      qty,
    });
  }
  return lines;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartEntry[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Nạp giỏ hàng từ localStorage khi mount (chỉ chạy ở client).
  useEffect(() => {
    try {
      setLines(parseStoredCart(window.localStorage.getItem(STORAGE_KEY)));
    } catch {
      // localStorage không khả dụng — giỏ rỗng.
    }
    setHydrated(true);
  }, []);

  // Lưu lại mỗi khi giỏ hàng thay đổi.
  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
    } catch {
      // bỏ qua nếu không lưu được
    }
  }, [lines, hydrated]);

  // Giữ nhiều tab đồng bộ: tab khác đổi giỏ thì tab này cập nhật badge.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setLines(parseStoredCart(e.newValue));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const addItem = useCallback((item: CartEntryInput, qty: number) => {
    if (!(qty > 0)) return;
    setLines((prev) => {
      const existing = prev.find((l) => l.item_code === item.item_code);
      if (existing) {
        return prev.map((l) =>
          l.item_code === item.item_code
            ? { ...l, qty: Math.round((l.qty + qty) * 1000) / 1000, price: item.price, name: item.name }
            : l
        );
      }
      return [...prev, { ...item, qty }];
    });
  }, []);

  const setQty = useCallback((itemCode: string, qty: number) => {
    setLines((prev) => {
      if (!(qty > 0)) return prev.filter((l) => l.item_code !== itemCode);
      return prev.map((l) => (l.item_code === itemCode ? { ...l, qty } : l));
    });
  }, []);

  const removeItem = useCallback((itemCode: string) => {
    setLines((prev) => prev.filter((l) => l.item_code !== itemCode));
  }, []);

  const updateEntries = useCallback((updater: (prev: CartEntry[]) => CartEntry[]) => {
    setLines((prev) => updater(prev));
  }, []);

  const clear = useCallback(() => setLines([]), []);

  const lineCount = lines.length;
  const totalAmount = useMemo(
    () => lines.reduce((sum, l) => sum + l.qty * (Number(l.price) || 0), 0),
    [lines]
  );

  const value: CartContextValue = {
    lines,
    ready: hydrated,
    addItem,
    setQty,
    removeItem,
    updateEntries,
    clear,
    lineCount,
    totalAmount,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error("useCart phải được dùng bên trong <CartProvider>");
  }
  return ctx;
}
