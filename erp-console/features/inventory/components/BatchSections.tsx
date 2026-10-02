"use client";

// Hai bảng con của trang chi tiết lô: "Nhập xuất của lô" (R6 lọc theo lô) và "Đơn lấy hàng từ lô" (R3 lọc theo lô).
// Bảng nhập xuất dùng LedgerTable (chỉ đọc). Bảng đơn CHỈ hiện mã đơn, giờ đặt, trạng thái, giá trị: không đọc, không hiện tên hay SĐT khách.
import Link from "next/link";
import { LedgerTable } from "@/features/ledger/components/LedgerTable";
import type { LedgerEntry } from "@/features/ledger/types";
import { referenceHref } from "@/features/ledger/referenceRoutes";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, vnd } from "@/shared/lib/format";
import { Chip } from "@/shared/ui/Chip";
import { Section } from "@/shared/ui/detail/Section";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import type { OrderUsingBatch } from "../types";
import s from "../inventory.module.css";

export type Remote<T> = { data: T | null; error: string | null; loading: boolean };

export function BatchLedgerSection({ batchId, state, onRetry }: { batchId: number; state: Remote<{ rows: LedgerEntry[]; count: number }>; onRetry: () => void }) {
  const rows = state.data?.rows ?? null;
  return (
    <Section
      title="Nhập xuất của lô"
      aria-label="Nhập xuất của lô"
      flush
      action={
        rows && state.data ? (
          <span>
            Đang hiện {rows.length} / {state.data.count} dòng
          </span>
        ) : undefined
      }
    >
      <LedgerTable
        rows={rows}
        loading={state.loading && !state.data}
        error={state.error && !state.data ? state.error : null}
        onRetry={onRetry}
        caption="Nhập xuất của lô"
        hideBatch
        empty={{ icon: "receipt_long", title: "Lô chưa có dòng nhập xuất" }}
        skeletonRows={3}
      />
      {state.data && state.data.count > state.data.rows.length && (
        <Link href={`/ledger/?batch=${batchId}`} className={s.panelLink}>
          Xem đủ {state.data.count} dòng trong sổ nhập xuất
        </Link>
      )}
    </Section>
  );
}

export function BatchOrdersSection({ state, onRetry }: { state: Remote<{ rows: OrderUsingBatch[]; count: number }>; onRetry: () => void }) {
  const rows = state.data?.rows ?? null;
  const columns: Column<OrderUsingBatch>[] = [
    {
      key: "code",
      header: "Mã đơn",
      mono: true,
      render: (o) => {
        const href = referenceHref({ kind: "order", id: o.id });
        return href ? (
          <Link href={href} className={s.codeLink}>
            {o.code}
          </Link>
        ) : (
          <span className={s.codeCell}>{o.code}</span>
        );
      },
    },
    { key: "at", header: "Thời gian đặt", num: true, render: (o) => dateTime(o.created_at) },
    { key: "status", header: "Trạng thái", render: (o) => <Chip table={ENUMS.salesOrderStatus} value={o.status} /> },
    { key: "total", header: "Giá trị đơn", num: true, render: (o) => vnd(o.total_amount) },
  ];
  return (
    <Section
      title="Đơn lấy hàng từ lô"
      aria-label="Đơn lấy hàng từ lô"
      flush
      action={
        rows && state.data ? (
          <span>
            Đang hiện {rows.length} / {state.data.count} đơn
          </span>
        ) : undefined
      }
    >
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(o) => o.id}
        loading={state.loading && !state.data}
        error={state.error && !state.data ? state.error : null}
        onRetry={onRetry}
        noun="đơn"
        empty={{ icon: "shopping_bag", title: "Chưa có đơn nào lấy hàng từ lô này" }}
        canViewCost={false}
        caption="Đơn lấy hàng từ lô"
        skeletonRows={3}
      />
    </Section>
  );
}
