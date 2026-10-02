"use client";

// F1i Chốt lô (BR-LO-04): cần tồn = 0; lô đã chốt không nhập, xuất hay sửa được nữa.
// Đã bán, Hao hụt, Lãi/lỗ lô chỉ hiện với người có quyền xem báo cáo lãi lỗ (reports.view_profitreport): lấy từ
// GET /api/reports/batch/<mã lô>/, và KHÔNG gọi API đó khi không có quyền (Quản lý không thấy lãi lỗ).
import { useEffect, useState } from "react";
import { kg, vnd } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { SummaryBlock, type SummaryRow } from "@/shared/ui/form/SummaryBlock";
import { Modal } from "@/shared/ui/overlay/Modal";
import { closeBatch, fetchBatchProfit } from "../api";
import { qtyAvailable } from "../lotView";
import type { BatchProfitReport } from "../types";
import { ActionError, useActionSubmit, type ActionProps } from "./useActionSubmit";

export function CloseBatchModal({ row, viewProfit, onClose, onDone, onReload, onConflict }: ActionProps & { viewProfit: boolean }) {
  const sub = useActionSubmit(() => closeBatch(row.id), () => onDone(`Đã chốt lô ${row.batch_id}.`), onConflict);
  const [report, setReport] = useState<BatchProfitReport | null>(null);
  const [reportFailed, setReportFailed] = useState(false);

  useEffect(() => {
    if (!viewProfit) return;
    const ac = new AbortController();
    fetchBatchProfit(row.batch_id, ac.signal)
      .then(setReport)
      .catch(() => {
        if (!ac.signal.aborted) setReportFailed(true);
      });
    return () => ac.abort();
  }, [viewProfit, row.batch_id]);

  const rows: SummaryRow[] = [
    { label: "Lô", value: row.batch_id, mono: true },
    { label: "Mặt hàng", value: row.item_name },
    { label: "Tồn còn", value: kg(qtyAvailable(row)), num: true },
  ];
  if (viewProfit && report) {
    rows.push(
      { label: "Đã bán", value: kg(report.qty_sold), num: true },
      { label: "Hao hụt", value: kg(report.shrinkage_qty), num: true },
      {
        label: report.provisional ? "Lãi/lỗ lô (tạm tính)" : "Lãi/lỗ lô",
        value: (
          <>
            <Icon name="lock" /> {vnd(report.profit)}
          </>
        ),
        num: true,
        strong: true,
      },
    );
  }
  return (
    <Modal
      title="Chốt lô"
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={() => void sub.submit()} disabled={sub.submitting || sub.blocked} aria-busy={sub.submitting}>
            {sub.submitting ? "Đang chốt…" : primaryLabel("Chốt lô", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <ActionError message={sub.error} stale={sub.stale} busy={sub.submitting} onReload={onReload} />}
      <SummaryBlock label="Lô sắp chốt" rows={rows} />
      {viewProfit && reportFailed && <p className="muted">Chưa tải được lãi lỗ của lô. Vẫn chốt lô được.</p>}
      <FormAlert kind="warn">Lô đã chốt không nhập, xuất hay sửa được nữa.</FormAlert>
    </Modal>
  );
}
