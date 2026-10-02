"use client";

// Danh mục & giá (W2d, ED-30/ED-31): bốn tab Mặt hàng · Bảng giá · Ưu đãi · Nhóm hàng. MỘT useTabParam (`?tab=items|prices|rules|groups`)
// cho cả trang; mỗi tab tự vẽ ListPage của nó (nhận khối <Tabs> từ đây). Tab thiếu quyền xem thì KHÔNG hiện: NV kho chỉ thấy
// "Mặt hàng" và không thấy giá; Quản lý xem được cả bốn tab nhưng không có nút ghi (ghi là việc của Chủ).
// Trang bọc <ViewGuard view="catalog"> (cần catalog.view_item).

import { useAuth } from "@/features/auth/components/AuthProvider";
import { Tabs, useTabParam, type TabItem } from "@/shared/ui/Tabs";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import { ItemGroupList } from "./ItemGroupList";
import { ItemListTab } from "./ItemListTab";
import { PriceListTab } from "./PriceListTab";
import { PricingRuleList } from "./PricingRuleList";
import s from "../catalog.module.css";

const TAB_KEYS = ["items", "prices", "rules", "groups"] as const;

export function CatalogScreen() {
  const { me } = useAuth();
  const [tab, select] = useTabParam(TAB_KEYS, "items");
  if (!me) return null;

  const ability = catalogAbility(me.permissions);
  const items: TabItem[] = [
    { key: "items", label: M.tabItems },
    ...(ability.viewPrices ? [{ key: "prices", label: M.tabPrices }] : []),
    ...(ability.viewRules ? [{ key: "rules", label: M.tabRules }] : []),
    ...(ability.viewGroups ? [{ key: "groups", label: M.tabGroups }] : []),
  ];
  const active = items.some((t) => t.key === tab) ? tab : "items";
  const tabs =
    items.length > 1 ? (
      <div className={s.tabsWrap}>
        <Tabs tabs={items} value={active} onChange={select} label={M.tabsLabel} panelId="catalog-panel" />
      </div>
    ) : null;

  if (active === "prices") return <PriceListTab tabs={tabs} />;
  if (active === "rules") return <PricingRuleList tabs={tabs} />;
  if (active === "groups") return <ItemGroupList tabs={tabs} />;
  return <ItemListTab tabs={tabs} />;
}
