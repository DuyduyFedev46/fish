"use client";

// Bảng Sổ nhập xuất dùng chung (Lô 7): trang /ledger/, khối "Nhập xuất gần đây" ở Kho & lô, mục "Nhập xuất của lô" ở chi tiết lô.
// CHỈ ĐỌC: không có cột hay nút sửa, xoá. Cột: Thời gian · Loại · Lô · Mặt hàng · Thay đổi (kg) · Tồn sau (kg) · Chứng từ · Người làm.
// Một ô một giá trị; giờ dd/mm/yyyy hh:mm (Việt Nam); số căn phải, tabular-nums; mã chứng từ chữ mono.
import Link from "next/link";
import { dateTime } from "@/shared/lib/format";
import { kg } from "@/shared/lib/format";
import { ENUMS } from "@/shared/lib/enums";
import { Chip } from "@/shared/ui/Chip";
import { DataTable, type Column, type EmptyState } from "@/shared/ui/list/DataTable";
import { actorOf, signedKg } from "../ledgerView";
import { referenceHref } from "../referenceRoutes";
import type { LedgerEntry } from "../types";
import s from "../ledger.module.css";

type Props = {
  rows: LedgerEntry[] | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  query?: string;
  onClearQuery?: () => void;
  caption: string;
  empty: EmptyState;
  /** Ẩn cột Lô và Mặt hàng (đã biết ở trang chi tiết lô). */
  hideBatch?: boolean;
  skeletonRows?: number;
};

export function LedgerTable({ rows, loading, error, onRetry, query, onClearQuery, caption, empty, hideBatch = false, skeletonRows }: Props) {
  const columns: Column<LedgerEntry>[] = [
    { key: "at", header: "Thời gian", num: true, width: "148px", render: (r) => dateTime(r.created_at) },
    { key: "type", header: "Loại", render: (r) => <Chip table={ENUMS.stockMovementType} value={r.movement_type} /> },
    ...(hideBatch
      ? []
      : ([
          {
            key: "batch",
            header: "Lô",
            mono: true,
            render: (r) => (
              <Link href={`/inventory/detail/?id=${r.batch}`} className={s.codeLink}>
                {r.batch_code}
              </Link>
            ),
          },
          { key: "item", header: "Mặt hàng", render: (r) => r.item_name },
        ] as Column<LedgerEntry>[])),
    {
      key: "change",
      header: "Thay đổi (kg)",
      num: true,
      render: (r) => <span className={Number(r.qty_change) < 0 ? s.out : s.in}>{signedKg(r.qty_change)}</span>,
    },
    { key: "balance", header: "Tồn sau (kg)", num: true, render: (r) => kg(r.balance_after) },
    {
      key: "ref",
      header: "Chứng từ",
      mono: true,
      render: (r) => {
        const href = referenceHref(r.reference_link);
        // Chỉ dùng chuỗi đã tra của BE; không lộ chuỗi gốc kỹ thuật (kiểu `cancel_expired_batch LO-…`). Không tra được thì hiện "—".
        const text = r.reference_display;
        if (!text) return <span className="muted">—</span>;
        return href ? (
          <Link href={href} className={s.codeLink}>
            {text}
          </Link>
        ) : (
          text
        );
      },
    },
    { key: "actor", header: "Người làm", render: (r) => actorOf(r) },
  ];
  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={(r) => r.id}
      loading={loading}
      error={error}
      onRetry={onRetry}
      query={query}
      onClearQuery={onClearQuery}
      noun="dòng nhập xuất"
      empty={empty}
      canViewCost={false}
      caption={caption}
      skeletonRows={skeletonRows}
    />
  );
}
