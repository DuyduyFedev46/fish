"use client";

// M5 — Hộp Xác nhận nhập mặt hàng từ Excel (FISH-66 S6; 02a §3.4).
// - Khi có dòng giá gắn cờ "Kiểm lại số 0" hoặc "Chênh lớn", bắt buộc đánh dấu ô "Tôi đã kiểm n giá cần xem".
// - Focus ban đầu ở nút "Quay lại xem" (mặc định an toàn).
// - Đang ghi: khoá hai nút, không đóng hộp khi bấm Esc hay nền mờ.

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { vnd } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { Modal } from "@/shared/ui/overlay/Modal";
import {
  countPriceFlags,
  formatConfirmSubmitLabel,
  formatConfirmTitle,
  groupValidFromSummary,
  splitPreviewSections,
} from "../itemFilesModel";
import type { ImportPreviewResponse } from "../itemFilesTypes";
import { CATALOG_MSG as CM, ITEM_IMPORT_MSG as M } from "../messages";
import s from "../catalog.module.css";

const MAX_FLAGGED_PREVIEW = 5;

export type CommitModalError =
  | { kind: "network"; message: string }
  | { kind: "server"; message: string }
  | { kind: "forbidden"; message: string }
  | null;

type Props = {
  open: boolean;
  preview: ImportPreviewResponse;
  busy: boolean;
  error: CommitModalError;
  onClose: () => void;
  onConfirm: () => void;
};

export function ImportConfirmModal({
  open,
  preview,
  busy,
  error,
  onClose,
  onConfirm,
}: Props) {
  const { summary, rows } = preview;
  const { priceRows } = splitPreviewSections(rows);
  const { flaggedRows } = countPriceFlags(priceRows);
  const flaggedCount = flaggedRows.length;
  const needsAck = flaggedCount > 0;

  const [checked, setChecked] = useState(false);
  const cancelBtnRef = useRef<HTMLButtonElement>(null);
  const reasonId = useId();

  useEffect(() => {
    if (open) {
      setChecked(false);
      const id = window.requestAnimationFrame(() => {
        cancelBtnRef.current?.focus();
      });
      return () => window.cancelAnimationFrame(id);
    }
  }, [open]);

  const canSubmit = (!needsAck || checked) && !busy && error?.kind !== "forbidden";
  const topFlagged = flaggedRows.slice(0, MAX_FLAGGED_PREVIEW);
  const extraFlaggedCount = Math.max(0, flaggedCount - topFlagged.length);

  if (!open) return null;

  return (
    <Modal
      onClose={busy ? () => {} : onClose}
      busy={busy}
      title={formatConfirmTitle(summary)}
      size="md"
      footer={
        <div className={s.confirmFoot}>
          {needsAck && !checked && (
            <span id={reasonId} className={s.blockedReason}>
              {M.confirmCheckBlockedReason}
            </span>
          )}
          <button
            ref={cancelBtnRef}
            type="button"
            className="btn"
            onClick={onClose}
            disabled={busy}
            data-autofocus
            data-testid="import-confirm-cancel"
          >
            {M.backToPreview}
          </button>
          {error?.kind === "forbidden" ? (
            <Link href="/catalog/?tab=items" className="btn primary">
              {M.backToList}
            </Link>
          ) : (
            <button
              type="button"
              className="btn primary"
              onClick={onConfirm}
              disabled={!canSubmit}
              aria-busy={busy || undefined}
              aria-describedby={needsAck && !checked ? reasonId : undefined}
              data-testid="import-confirm-submit"
            >
              {busy
                ? M.committing
                : error
                  ? M.retry
                  : formatConfirmSubmitLabel(summary)}
            </button>
          )}
        </div>
      }
    >
      <div className={s.confirmStack} data-testid="import-confirm-modal">
        <SummaryBlock
          rows={[
            { label: M.confirmSummaryPrices, value: summary.price_changed, num: true },
            { label: M.confirmSummaryNew, value: summary.created, num: true },
            { label: M.confirmSummaryUpdated, value: summary.updated, num: true },
            { label: M.confirmSummaryWillShow, value: summary.will_show_on_shop, num: true },
            { label: M.confirmSummaryWillHide, value: summary.will_hide_from_shop, num: true },
            { label: M.confirmSummaryDates, value: groupValidFromSummary(priceRows) },
          ]}
        />

        {needsAck && (
          <div className="alert-box warn" data-testid="import-confirm-flagged-alert">
            <Icon name="warning" />
            <div>
              <strong>Cần kiểm lại {flaggedCount} mức giá có chênh lệch lớn:</strong>
              <ul className={s.flaggedList}>
                {topFlagged.map((r) => (
                  <li key={r.code}>
                    <span className="mono">{r.code}</span> ({r.name}):{" "}
                    {r.price?.old != null ? vnd(r.price.old) : CM.none} →{" "}
                    <strong>{r.price ? vnd(r.price.new) : CM.none}</strong>
                  </li>
                ))}
                {extraFlaggedCount > 0 && <li>{M.confirmMoreFlagged(extraFlaggedCount)}</li>}
              </ul>
            </div>
          </div>
        )}

        {needsAck && (
          <label className={s.check}>
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              disabled={busy}
              data-testid="import-confirm-ack-checkbox"
            />
            <span>{M.confirmCheckLabel(flaggedCount)}</span>
          </label>
        )}

        {error && (
          <div className="alert-box err" role="alert" data-testid="import-confirm-error">
            <Icon name="error" />
            <div>{error.message}</div>
          </div>
        )}
      </div>
    </Modal>
  );
}
