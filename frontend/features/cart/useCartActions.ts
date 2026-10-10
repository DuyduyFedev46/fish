"use client";

import { useCallback, useState } from "react";
import { useCart } from "@/components/CartContext";
import { useToast } from "@/components/ui/Toast";
import { CART_HREF } from "@/components/shopLinks";
import { formatQty, parseQtyRule } from "@/lib/quantity";
import type { CatalogItem } from "@/lib/types";

type Ref = { item_code: string; name: string; unit: "kg" | "combo"; min_qty: string; qty_step: string };

/**
 * Thao tác giỏ dùng chung cho danh mục và chi tiết: thêm (toast + giỏ nhanh), đổi số lượng,
 * hỏi bỏ món (hộp thoại B2) và câu báo cho `aria-live`. Container gắn kết quả vào component trình bày.
 */
export function useCartActions() {
  const cart = useCart();
  const toast = useToast();
  const [pending, setPending] = useState<Ref | null>(null);
  const [live, setLive] = useState("");
  const [miniOpen, setMiniOpen] = useState(false);

  const qtyOf = useCallback(
    (code: string) => cart.lines.find((l) => l.item_code === code)?.qty ?? 0,
    [cart.lines]
  );

  const add = useCallback(
    (item: CatalogItem, qty: number) => {
      cart.addItem({ item_code: item.item_code, name: item.name, unit: item.unit, price: item.price }, qty);
      const text = `Đã thêm ${formatQty(qty)} ${item.unit} ${item.name} vào giỏ`;
      toast.show({ message: text, action: { label: "Xem giỏ", href: CART_HREF } });
      setLive(text);
      setMiniOpen(true);
    },
    [cart, toast]
  );

  const change = useCallback(
    (item: Ref, qty: number) => {
      cart.setQty(item.item_code, qty);
      setLive(`Đã cập nhật ${item.name}: ${formatQty(qty)} ${item.unit}`);
    },
    [cart]
  );

  const askRemove = useCallback((item: Ref) => setPending(item), []);
  const keep = useCallback(() => setPending(null), []);
  const confirmRemove = useCallback(() => {
    if (!pending) return;
    cart.removeItem(pending.item_code);
    setLive(`Đã bỏ ${pending.name} khỏi giỏ`);
    setPending(null);
  }, [cart, pending]);

  const pendingView = pending
    ? { name: pending.name, unit: pending.unit, minQty: parseQtyRule(pending.min_qty, pending.qty_step, pending.unit).minQty }
    : null;

  return {
    cart,
    qtyOf,
    add,
    change,
    askRemove,
    keep,
    confirmRemove,
    pendingView,
    live,
    setLive,
    miniOpen,
    closeMini: useCallback(() => setMiniOpen(false), []),
  };
}
