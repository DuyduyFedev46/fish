"use client";

// Kho & lô (W5a, ED-23/24/25): ba tab Tồn theo lô · Điều chỉnh tồn (chỉ đọc) · Kho. MỘT useTabParam cho cả trang;
// mỗi tab tự vẽ ListPage của nó (nhận khối <Tabs> từ đây). Tab thiếu quyền xem thì không hiện (xem `PERM`).
import { useAuth } from "@/features/auth/components/AuthProvider";
import { PERM } from "@/shared/lib/nav";
import { Tabs, useTabParam, type TabItem } from "@/shared/ui/Tabs";
import { LotsTab } from "./LotsTab";
import { StockEntriesTab } from "./StockEntriesTab";
import { WarehousesTab } from "./WarehousesTab";
import s from "../inventory.module.css";

const TAB_KEYS = ["lots", "adjustments", "warehouses"] as const;

export function InventoryScreen() {
  const { me } = useAuth();
  const [tab, select] = useTabParam(TAB_KEYS, "lots");
  if (!me) return null;

  const has = (perm: string) => me.permissions.includes(perm);
  const items: TabItem[] = [
    { key: "lots", label: "Tồn theo lô" },
    ...(has(PERM.viewStockEntry) ? [{ key: "adjustments", label: "Điều chỉnh tồn" }] : []),
    ...(has(PERM.viewWarehouse) ? [{ key: "warehouses", label: "Kho" }] : []),
  ];
  const active = items.some((t) => t.key === tab) ? tab : "lots";
  const tabs = (
    <div className={s.tabsWrap}>
      <Tabs tabs={items} value={active} onChange={select} label="Các phần của Kho & lô" panelId="inventory-panel" />
    </div>
  );

  if (active === "adjustments") return <StockEntriesTab tabs={tabs} />;
  if (active === "warehouses") return <WarehousesTab tabs={tabs} me={me} />;
  return <LotsTab tabs={tabs} me={me} />;
}
