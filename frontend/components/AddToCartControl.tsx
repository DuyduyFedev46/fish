"use client";

import { useEffect, useState } from "react";
import { getSiteInfo } from "../features/site/api";
import { useCart } from "./CartContext";
import type { CatalogItem } from "../lib/types";

export default function AddToCartControl({ item }: { item: CatalogItem }) {
  const { addItem } = useCart();
  const [qty, setQty] = useState(1);
  const [added, setAdded] = useState(false);

  const outOfStock = !(Number(item.sellable_qty) > 0);
  const [sellerPhone, setSellerPhone] = useState<string | null>(null);

  // Hết hàng: nút "Liên hệ" gọi số người bán (nếu có). Chỉ tải khi cần, dùng chung cache getSiteInfo.
  useEffect(() => {
    if (!outOfStock) return;
    let active = true;
    getSiteInfo()
      .then((info) => {
        const phone = info?.seller?.phone?.replace(/[^\d+]/g, "") || null;
        if (active) setSellerPhone(phone);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [outOfStock]);

  function handleAdd() {
    if (qty <= 0) return;
    addItem(
      { item_code: item.item_code, name: item.name, price: Number(item.price), unit: "Kg" },
      qty
    );
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  }

  if (outOfStock) {
    // BR-BH (BE vẫn chặn đặt quá tồn): không bao giờ thêm vào giỏ; chỉ dẫn khách liên hệ.
    return (
      <div className="add-to-cart">
        <a
          className="btn btn-secondary btn-add"
          href={sellerPhone ? `tel:${sellerPhone}` : "#thong-tin-nguoi-ban"}
          data-testid="contact-button"
        >
          Liên hệ
        </a>
      </div>
    );
  }

  return (
    <div className="add-to-cart">
      <div className="qty-stepper">
        <button
          type="button"
          aria-label="Giảm số lượng"
          onClick={() => setQty((q) => Math.max(0.1, Math.round((q - 0.5) * 10) / 10))}
        >
          −
        </button>
        <input
          type="number"
          min={0.1}
          step={0.1}
          value={qty}
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
        >
          +
        </button>
        <span className="qty-unit">kg</span>
      </div>
      <button
        type="button"
        className="btn btn-primary btn-add"
        onClick={handleAdd}
      >
        {added ? "Đã thêm ✓" : "Thêm vào giỏ"}
      </button>
    </div>
  );
}
