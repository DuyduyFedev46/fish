"use client";

// Hộp "Lượt dùng mã" (SHOP-3b-02): mỗi dòng một đơn đã giữ hoặc dùng mã: mã đơn, số giảm, giờ (GMT+7), trạng thái.
// Chỉ có 4 thông tin này, KHÔNG có tên, SĐT, địa chỉ khách (bất biến 9). Phân trang "Tải thêm"; lỗi tải có nút Thử lại.

import { useCallback, useEffect, useRef, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, vnd } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { Chip } from "@/shared/ui/Chip";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { Modal } from "@/shared/ui/overlay/Modal";
import { listVoucherRedemptions } from "../api";
import { VOUCHER_MSG as M } from "../messages";
import type { Voucher, VoucherRedemption } from "../types";
import s from "../catalog.module.css";

export function VoucherRedemptions({ voucher, onClose }: { voucher: Voucher; onClose: () => void }) {
  const [rows, setRows] = useState<VoucherRedemption[] | null>(null);
  const [count, setCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [moreError, setMoreError] = useState<unknown>(null);
  const [moreLoading, setMoreLoading] = useState(false);
  const page = useRef(1);
  const seq = useRef(0);

  const loadFirst = useCallback(async () => {
    const n = ++seq.current;
    page.current = 1;
    setRows(null);
    setError(null);
    try {
      const res = await listVoucherRedemptions(voucher.id, 1);
      if (n !== seq.current) return;
      setRows(res.results);
      setCount(res.count);
      setHasMore(!!res.next);
    } catch (err) {
      if (n === seq.current) setError(err);
    }
  }, [voucher.id]);

  useEffect(() => {
    void loadFirst();
    return () => {
      seq.current += 1;
    };
  }, [loadFirst]);

  const loadMore = async () => {
    if (moreLoading) return;
    const n = seq.current;
    setMoreLoading(true);
    setMoreError(null);
    try {
      const res = await listVoucherRedemptions(voucher.id, page.current + 1);
      if (n !== seq.current) return;
      page.current += 1;
      setRows((prev) => [...(prev ?? []), ...res.results]);
      setHasMore(!!res.next);
    } catch (err) {
      setMoreError(err);
    } finally {
      setMoreLoading(false);
    }
  };

  const columns: Column<VoucherRedemption>[] = [
    { key: "order", header: M.usesColOrder, mono: true, render: (r) => r.order_code },
    { key: "amount", header: M.usesColAmount, num: true, render: (r) => vnd(r.discount_amount) },
    { key: "at", header: M.usesColAt, tabular: true, render: (r) => dateTime(r.at) },
    { key: "state", header: M.usesColState, render: (r) => <Chip table={ENUMS.voucherRedemptionState} value={r.state} /> },
  ];

  return (
    <Modal
      title={M.usesTitle(voucher.code)}
      onClose={onClose}
      size="xl"
      footer={
        <button type="button" className="btn" onClick={onClose}>
          {M.usesClose}
        </button>
      }
    >
      <p className={s.railNote}>{M.usesNote}</p>
      <DataTable
        caption={M.usesCaption}
        columns={columns}
        rows={rows}
        rowKey={(r) => r.order_code}
        loading={rows === null && error == null}
        error={rows === null && error != null ? `${M.usesFailed} ${loadErrorText(error)}` : null}
        onRetry={() => void loadFirst()}
        noun={M.listNoun}
        empty={{ icon: "receipt_long", title: M.usesEmpty }}
        canViewCost={false}
        countText={rows ? `${count}` : undefined}
        dense
      />
      <div className={s.sectionFoot}>
        {moreError != null && (
          <span className="field-err" role="alert">
            {M.loadMoreFailed} {loadErrorText(moreError)}
          </span>
        )}
        {hasMore && (
          <button type="button" className="btn" onClick={() => void loadMore()} disabled={moreLoading} aria-busy={moreLoading || undefined}>
            {moreLoading ? M.loadingMore : M.loadMore}
          </button>
        )}
      </div>
    </Modal>
  );
}
