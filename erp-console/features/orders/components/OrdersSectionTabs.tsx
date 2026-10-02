"use client";

// Ba tab của "Đơn & tiền": Đơn hàng · Hàng chờ thanh toán · Phiếu hoàn (ED-09). Mỗi tab là một trang riêng (menu trái cũng
// có mục con) nên đổi tab = chuyển trang. Tab chỉ hiện khi người xem mở được màn đó; chỉ còn "Đơn hàng" thì ẩn cả thanh.

import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { canView, navItem } from "@/shared/lib/nav";
import { Tabs } from "@/shared/ui/Tabs";
import { ORDERS_MSG as M } from "../messages";

export type OrdersSection = "orders" | "payments" | "refunds";

export function OrdersSectionTabs({ current }: { current: OrdersSection }) {
  const { me } = useAuth();
  const router = useRouter();
  const tabs = [
    { key: "orders", label: M.tabOrders },
    ...(canView(me, "payments") ? [{ key: "payments", label: M.tabQueue }] : []),
    ...(canView(me, "refunds") ? [{ key: "refunds", label: M.tabRefunds }] : []),
  ];
  if (tabs.length < 2) return null;
  return <Tabs tabs={tabs} value={current} label={M.tabsLabel} onChange={(k) => k !== current && router.push(navItem(k as OrdersSection).href)} />;
}
