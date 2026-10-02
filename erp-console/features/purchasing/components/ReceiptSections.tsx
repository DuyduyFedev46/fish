"use client";

// Ba bảng con của trang chi tiết phiếu nhập: Dòng nhập (kèm lô) · Hoá đơn mua · Chi phí phụ.
// Giá mua, thành tiền, giá vốn/kg, chi phí phụ: cột khoá, chỉ Chủ có trong DOM (DataTable bỏ cột khi canViewCost = false;
// màn cha cũng không dựng bảng chi phí cho người khác). Hoá đơn: Quản lý thấy số tiền (D-3), nhân viên kho không có bảng.
import Link from "next/link";
import { referenceHref } from "@/features/ledger/referenceRoutes";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, kg, vnd } from "@/shared/lib/format";
import { Chip } from "@/shared/ui/Chip";
import { Section } from "@/shared/ui/detail/Section";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import type { ReceiptCost, ReceiptInvoice, ReceiptLine } from "../types";
import s from "../purchasing.module.css";

const num = (v: string | number | null | undefined) => {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n : 0;
};

export function ReceiptLinesSection({ lines, canViewCost, canOpenBatch }: { lines: ReceiptLine[]; canViewCost: boolean; canOpenBatch: boolean }) {
  const columns: Column<ReceiptLine>[] = [
    { key: "item", header: "Mặt hàng", render: (l) => l.item_name },
    { key: "qty", header: "Số kg", num: true, render: (l) => kg(l.qty) },
    {
      key: "batch",
      header: "Lô",
      mono: true,
      render: (l) => {
        if (!l.batch_code || l.batch === null) return <span className="muted">Chưa có lô</span>;
        const href = canOpenBatch ? referenceHref({ kind: "batch", id: l.batch }) : null;
        return href ? (
          <Link href={href} className={s.codeLink}>
            {l.batch_code}
          </Link>
        ) : (
          l.batch_code
        );
      },
    },
    { key: "batchStatus", header: "Trạng thái lô", render: (l) => <Chip table={ENUMS.batchStatus} value={l.batch_status} /> },
    { key: "expiry", header: "Hạn dùng", num: true, render: (l) => (l.expiry_date ? dateOnly(l.expiry_date) : l.shelf_life_days ? `${l.shelf_life_days} ngày` : <span className="muted">—</span>) },
    { key: "rate", header: "Giá mua/kg", num: true, locked: true, render: (l) => (l.rate === undefined ? "—" : vnd(l.rate)) },
    { key: "amount", header: "Thành tiền", num: true, locked: true, render: (l) => (l.purchase_amount === undefined ? "—" : vnd(l.purchase_amount)) },
    { key: "landed", header: "Giá vốn/kg", num: true, locked: true, render: (l) => (l.landed_unit_cost ? vnd(l.landed_unit_cost) : "—") },
  ];
  return (
    <Section title="Dòng nhập" count={lines.length} aria-label="Dòng nhập" flush>
      <DataTable
        columns={columns}
        rows={lines}
        rowKey={(l) => l.id}
        noun="dòng"
        empty={{ icon: "list_alt", title: "Phiếu chưa có dòng nhập" }}
        canViewCost={canViewCost}
        caption="Dòng nhập của phiếu"
        skeletonRows={3}
      />
    </Section>
  );
}

export function ReceiptInvoicesSection({ invoices, action }: { invoices: ReceiptInvoice[]; action?: React.ReactNode }) {
  const columns: Column<ReceiptInvoice>[] = [
    { key: "code", header: "Hoá đơn", mono: true, render: (i) => i.code },
    { key: "date", header: "Ngày hoá đơn", num: true, render: (i) => dateOnly(i.invoice_date) },
    { key: "amount", header: "Số tiền", num: true, render: (i) => (i.amount === undefined ? "—" : vnd(i.amount)) },
    { key: "paid", header: "Tình trạng", render: (i) => <Chip table={ENUMS.purchaseInvoicePaid} value={String(i.is_paid)} /> },
  ];
  return (
    <Section title="Hoá đơn mua" count={invoices.length} action={action} aria-label="Hoá đơn mua" data-testid="receipt-invoices" flush>
      <DataTable
        columns={columns}
        rows={invoices}
        rowKey={(i) => i.id}
        noun="hoá đơn"
        empty={{ icon: "receipt_long", title: "Phiếu chưa có hoá đơn mua" }}
        canViewCost
        caption="Hoá đơn mua của phiếu"
        skeletonRows={2}
      />
    </Section>
  );
}

export function ReceiptCostsSection({ costs, allocatedTotal, action }: { costs: ReceiptCost[]; allocatedTotal: string | undefined; action?: React.ReactNode }) {
  const columns: Column<ReceiptCost>[] = [
    { key: "date", header: "Ngày phát sinh", num: true, render: (c) => dateOnly(c.incurred_date) },
    { key: "type", header: "Loại chi phí", render: (c) => <Chip table={ENUMS.purchaseCostType} value={c.cost_type} /> },
    { key: "method", header: "Cách chia", render: (c) => <Chip table={ENUMS.purchaseCostAllocation} value={c.allocation_method} /> },
    { key: "lots", header: "Số lô nhận", num: true, render: (c) => c.batch_count },
    { key: "amount", header: "Tổng chi phí", num: true, locked: true, render: (c) => vnd(c.amount) },
    { key: "allocated", header: "Chia vào phiếu này", num: true, locked: true, render: (c) => vnd(c.allocated_amount) },
  ];
  const total = allocatedTotal !== undefined ? allocatedTotal : costs.reduce((a, c) => a + num(c.allocated_amount), 0);
  return (
    <Section title="Chi phí phụ" count={costs.length} action={action} aria-label="Chi phí phụ" data-testid="receipt-costs" flush>
      <DataTable
        columns={columns}
        rows={costs}
        rowKey={(c) => c.id}
        noun="khoản chi phí"
        empty={{ icon: "payments", title: "Phiếu chưa có chi phí phụ", hint: "Đá, vận chuyển, bốc vác chia vào giá vốn của lô." }}
        canViewCost
        caption="Chi phí phụ chia vào lô của phiếu"
        skeletonRows={2}
      />
      {costs.length > 0 && (
        <p className={s.sectionSum}>
          Tổng chi phí phụ đã chia vào phiếu này: <span className="num">{vnd(total)}</span>
        </p>
      )}
    </Section>
  );
}
