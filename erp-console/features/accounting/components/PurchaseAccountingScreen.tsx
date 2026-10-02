"use client";

// Hoá đơn mua & chi phí phụ (W5g, ED-34): hai tab "Hoá đơn mua" · "Chi phí phụ", MỘT useTabParam (`?tab=invoices|costs`).
// Dùng lại hai danh sách của Lô 10 (cùng API, cùng form thêm). Quyền: hoá đơn mua cần view_purchaseinvoice (Chủ, Quản lý; Quản lý thấy
// số tiền theo quyết định D-3 nhưng không thêm được); chi phí phụ chỉ Chủ (cả chứng từ là giá vốn). Tab thiếu quyền không hiện;
// không có tab nào (vd nhân viên kho vào thẳng URL) thì ra "Không có quyền". Màn "Mua hàng" vẫn có hai tab tương ứng cho người quen cách cũ.
import { useAuth } from "@/features/auth/components/AuthProvider";
import { receiptAbility } from "@/features/purchasing/receiptView";
import { PERM } from "@/shared/lib/nav";
import { Tabs, useTabParam, type TabItem } from "@/shared/ui/Tabs";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { PurchaseCostList } from "./PurchaseCostList";
import { PurchaseInvoiceList } from "./PurchaseInvoiceList";
import s from "../accounting.module.css";

const TAB_KEYS = ["invoices", "costs"] as const;
const PANEL_ID = "accounting-panel";

export function PurchaseAccountingScreen() {
  const { me } = useAuth();
  const [tab, select] = useTabParam(TAB_KEYS, "invoices");
  if (!me) return null;

  const ability = receiptAbility(me);
  const items: TabItem[] = [
    ...(ability.viewInvoices ? [{ key: "invoices", label: "Hoá đơn mua" }] : []),
    ...(ability.viewCosts ? [{ key: "costs", label: "Chi phí phụ" }] : []),
  ];
  if (items.length === 0) return <NoPermission />;

  const active = items.some((t) => t.key === tab) ? tab : items[0].key;
  const tabs =
    items.length > 1 ? (
      <div className={s.tabsWrap}>
        <Tabs tabs={items} value={active} onChange={select} label="Các phần của Hoá đơn mua và chi phí phụ" panelId={PANEL_ID} />
      </div>
    ) : null;

  if (active === "costs") return <PurchaseCostList tabs={tabs} canAdd={ability.addCost} panelId={PANEL_ID} homeHref="/overview/" />;
  return <PurchaseInvoiceList tabs={tabs} canAdd={ability.addInvoice} canPickSupplier={me.permissions.includes(PERM.viewSupplier)} panelId={PANEL_ID} homeHref="/overview/" />;
}
