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
  totalQty: number;
  totalAmount: number;
};

const CartContext = createContext<CartContextValue | null>(null);

const STORAGE_KEY = "cangcaloc_cart_v1";

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CartLine[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Nạp giỏ hàng từ localStorage khi mount (chỉ chạy ở client).
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setLines(parsed);
      }
    } catch {
      // localStorage không khả dụng hoặc dữ liệu hỏng — bỏ qua, giỏ hàng rỗng.
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
