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

// Giỏ chỉ giữ mã hàng, tên món, đơn vị, giá lúc thêm và số lượng. Không bao giờ có tên, SĐT hay địa chỉ
// (bất biến 9, SHOP-1-01 AC6). Lô 2 đổi kiểu dòng giỏ sang CartEntry; lô 1 chỉ đưa giỏ lên gốc và đổi badge.
export type CartLine = {
  item_code: string;
  name: string;
  price: number;
  unit: "Kg";
  qty: number;
};

type CartContextValue = {
  lines: CartLine[];
  addItem: (item: Omit<CartLine, "qty">, qty: number) => void;
  updateQty: (itemCode: string, qty: number) => void;
  removeItem: (itemCode: string) => void;
  clear: () => void;
  /** Tổng số lượng (kg cộng dồn). Dùng để tính tiền, KHÔNG dùng cho badge. */
  totalQty: number;
  /** Số món (số dòng) trong giỏ: giá trị của badge giỏ (UI-RULES §4.4). */
  lineCount: number;
  totalAmount: number;
};

const CartContext = createContext<CartContextValue | null>(null);

const STORAGE_KEY = "cangcaloc_cart_v1";

/** Đọc giỏ từ chuỗi đã lưu; chuỗi hỏng hay dòng sai dạng thì bỏ qua, không bao giờ ném lỗi (SHOP-1-01 AC7). */
function parseStoredCart(raw: string | null): CartLine[] {
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const lines: CartLine[] = [];
  for (const entry of parsed) {
    if (!entry || typeof entry !== "object") continue;
    const e = entry as Record<string, unknown>;
    const qty = Number(e.qty);
    // Giỏ cũ có thể lưu giá dạng chuỗi Decimal ("260000.00") -> ép về số.
    const price = Number(e.price);
    if (typeof e.item_code !== "string" || !e.item_code) continue;
    if (!Number.isFinite(qty) || qty <= 0) continue;
    lines.push({
      item_code: e.item_code,
      name: typeof e.name === "string" ? e.name : e.item_code,
      price: Number.isFinite(price) ? price : 0,
      unit: "Kg",
      qty,
    });
  }
  return lines;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>([]);
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

  const addItem = useCallback((item: Omit<CartLine, "qty">, qty: number) => {
    if (qty <= 0) return;
    setLines((prev) => {
      const existing = prev.find((l) => l.item_code === item.item_code);
      if (existing) {
        return prev.map((l) =>
          l.item_code === item.item_code ? { ...l, qty: l.qty + qty } : l
        );
      }
      return [...prev, { ...item, qty }];
    });
  }, []);

  const updateQty = useCallback((itemCode: string, qty: number) => {
    setLines((prev) => {
      if (qty <= 0) return prev.filter((l) => l.item_code !== itemCode);
      return prev.map((l) => (l.item_code === itemCode ? { ...l, qty } : l));
    });
  }, []);

  const removeItem = useCallback((itemCode: string) => {
    setLines((prev) => prev.filter((l) => l.item_code !== itemCode));
  }, []);

  const clear = useCallback(() => setLines([]), []);

  const totalQty = useMemo(() => lines.reduce((sum, l) => sum + l.qty, 0), [lines]);
  const lineCount = lines.length;
  const totalAmount = useMemo(
    () => lines.reduce((sum, l) => sum + l.qty * l.price, 0),
    [lines]
  );

  const value: CartContextValue = {
    lines,
    addItem,
    updateQty,
    removeItem,
    clear,
    totalQty,
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
