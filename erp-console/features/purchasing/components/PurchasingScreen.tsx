"use client";

// Mua hàng (W2a, ED-20): ba tab Phiếu nhập · Hoá đơn mua · Chi phí phụ. MỘT useTabParam (`?tab=receipts|invoices|costs`) cho cả trang;
// mỗi tab tự vẽ ListPage của nó (nhận khối <Tabs> từ đây). Tab thiếu quyền thì không hiện:
// Hoá đơn mua cần view_purchaseinvoice (Chủ, Quản lý); Chi phí phụ chỉ Chủ (view_purchasecost và can_view_cost).
// Form nhập lô tại cảng là trang riêng /purchasing/new/ (F1a).
import { PurchaseCostList } from "@/features/accounting/components/PurchaseCostList";
import { PurchaseInvoiceList } from "@/features/accounting/components/PurchaseInvoiceList";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { PERM } from "@/shared/lib/nav";
import { Tabs, useTabParam, type TabItem } from "@/shared/ui/Tabs";
import { receiptAbility } from "../receiptView";
import { ReceiptListTab } from "./ReceiptListTab";
import s from "../purchasing.module.css";

const TAB_KEYS = ["receipts", "invoices", "costs"] as const;

export function PurchasingScreen() {
  const { me } = useAuth();
  const [tab, select] = useTabParam(TAB_KEYS, "receipts");
  if (!me) return null;

  const ability = receiptAbility(me);
  const items: TabItem[] = [
    { key: "receipts", label: "Phiếu nhập" },
    ...(ability.viewInvoices ? [{ key: "invoices", label: "Hoá đơn mua" }] : []),
    ...(ability.viewCosts ? [{ key: "costs", label: "Chi phí phụ" }] : []),
  ];
  const active = items.some((t) => t.key === tab) ? tab : "receipts";
  const tabs =
    items.length > 1 ? (
      <div className={s.tabsWrap}>
        <Tabs tabs={items} value={active} onChange={select} label="Các phần của Mua hàng" panelId="purchasing-panel" />
      </div>
    ) : null;

  if (active === "invoices") return <PurchaseInvoiceList tabs={tabs} canAdd={ability.addInvoice} canPickSupplier={me.permissions.includes(PERM.viewSupplier)} />;
  if (active === "costs") return <PurchaseCostList tabs={tabs} canAdd={ability.addCost} />;
  return <ReceiptListTab tabs={tabs} me={me} />;
}
