"use client";

import Link from "next/link";
import { useCart } from "./CartContext";

export default function ShopHeader() {
  const { totalQty } = useCart();

  return (
    <header className="shop-header">
      <div className="shop-header-inner">
        <Link href="/shop" className="shop-logo">
          Cá Về <span className="shop-logo-sub">Shop</span>
        </Link>
        <nav className="shop-nav">
          <Link href="/shop/orders">Tra cứu đơn</Link>
          <Link href="/shop/checkout" className="cart-link">
            Giỏ hàng
            {totalQty > 0 && <span className="cart-badge">{totalQty}</span>}
          </Link>
        </nav>
      </div>
    </header>
  );
}
