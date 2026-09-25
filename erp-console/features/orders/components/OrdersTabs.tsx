"use client";

// Tab con của "Đơn & tiền": Đơn hàng · Hàng chờ thanh toán (S12) · Phiếu hoàn chờ chuyển (S16). Trên máy tính menu trái
// đã có mục con nên tab chỉ hiện ở điện thoại (< 768px, menu trái là ngăn kéo, menu đáy không có mục con). Mỗi tab con
// chỉ hiện khi người xem mở được màn đó — không có quyền nào thì không vẽ cả thanh tab (chỉ còn "Đơn hàng" thì cũng ẩn).

import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { canView, navItem } from "@/shared/lib/nav";
import { QUEUE_MSG } from "../messages";
import s from "../orders.module.css";

export function OrdersTabs({ current }: { current: "orders" | "payments" | "refunds" }) {
  const { me } = useAuth();
  const showQueue = canView(me, "payments");
  const showRefunds = canView(me, "refunds");
  if (!showQueue && !showRefunds) return null;
  const tabs = [
    { key: "orders" as const, href: navItem("orders").href, label: QUEUE_MSG.tabOrders },
    ...(showQueue ? [{ key: "payments" as const, href: navItem("payments").href, label: QUEUE_MSG.tabQueue }] : []),
    ...(showRefunds ? [{ key: "refunds" as const, href: navItem("refunds").href, label: QUEUE_MSG.tabRefunds }] : []),
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
