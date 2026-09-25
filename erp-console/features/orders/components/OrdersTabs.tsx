"use client";

// Tab con của "Đơn & tiền": Đơn hàng · Hàng chờ thanh toán (S12). Trên máy tính menu trái đã có mục con nên tab chỉ hiện
// ở điện thoại (< 768px, menu trái là ngăn kéo, menu đáy không có mục con). Tab "Hàng chờ" chỉ hiện khi người xem mở được
// màn đó (S12-AC7: chỉ Chủ) — không có quyền thì không vẽ cả thanh tab.

import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { canView, navItem } from "@/shared/lib/nav";
import { QUEUE_MSG } from "../messages";
import s from "../orders.module.css";

export function OrdersTabs({ current }: { current: "orders" | "payments" }) {
  const { me } = useAuth();
  if (!canView(me, "payments")) return null;
  const tabs = [
    { key: "orders" as const, href: navItem("orders").href, label: QUEUE_MSG.tabOrders },
    { key: "payments" as const, href: navItem("payments").href, label: QUEUE_MSG.tabQueue },
  ];
  return (
    <nav className={`${s.tabs} orders-tabs`} aria-label={QUEUE_MSG.tabsLabel}>
      {tabs.map((t) => (
        <Link key={t.key} href={t.href} className={s.tab} aria-current={current === t.key ? "page" : undefined}>
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
