"use client";

import { useState } from "react";
import { useCart } from "./CartContext";
import type { CatalogItem } from "../lib/types";

export default function AddToCartControl({ item }: { item: CatalogItem }) {
  const { addItem } = useCart();
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);

  const outOfStock = item.sellable_qty <= 0;

  function handleAdd() {
    if (qty <= 0 || outOfStock) return;
    addItem(
      { item_code: item.item_code, name: item.name, price: item.price, unit: "Kg" },
      qty
    );
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  }

  return (
    <div className="add-to-cart">
      <div className="qty-stepper">
        <button
          type="button"
          aria-label="Giảm số lượng"
          onClick={() => setQty((q) => Math.max(0.1, Math.round((q - 0.5) * 10) / 10))}
          disabled={outOfStock}
        >
          −
        </button>
        <input
          type="number"
          min={0.1}
          step={0.1}
          value={qty}
          disabled={outOfStock}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            setQty(Number.isFinite(v) && v > 0 ? v : 0.1);
          }}
          aria-label="Số kg"
        />
        <button
          type="button"
          aria-label="Tăng số lượng"
          onClick={() => setQty((q) => Math.round((q + 0.5) * 10) / 10)}
          disabled={outOfStock}
        >
          +
        </button>
        <span className="qty-unit">kg</span>
      </div>
      <button
        type="button"
        className="btn btn-primary btn-add"
        onClick={handleAdd}
        disabled={outOfStock}
      >
        {outOfStock ? "Hết hàng" : added ? "Đã thêm ✓" : "Thêm vào giỏ"}
      </button>
    </div>
  );
}
