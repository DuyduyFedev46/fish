"use client";

// S16 — Tấm chi tiết một phiếu hoàn chờ chuyển. Chế độ: xem · xác nhận đã chuyển · báo thất bại · thử lại. Nút CHỈ vẽ
// theo `available_actions` mà BE trả TRONG danh sách/tấm — cả ba thao tác đều gác sau MỘT quyền `sales.confirm_refund`
// (S16-AC7, contract chỉ có một câu 403 chung), nên vào được thao tác này nghĩa là làm được cả ba. Contract
// confirm/mark-failed/retry chỉ trả `{status}` (không có `available_actions` mới) — FE suy nút tiếp theo THẲNG theo
// state machine cố định của BR-HT-09 (PENDING ⇄ FAILED qua mark-failed/retry, PENDING → REFUNDED qua confirm là chốt),
// không phải tự đặt luật quyền. Đóng tấm → báo màn cha tải lại danh sách (phiếu REFUNDED biến khỏi danh sách vì lọc
// `status=PENDING,FAILED`).

import { useEffect, useRef, useState } from "react";
import { SideSheet } from "@/shared/ui/SideSheet";
import { REFUND_Q_MSG } from "../messages";
import type { ConfirmRefundResult, MarkRefundFailedResult, RefundQueueAction, RefundQueueItem, RetryRefundResult } from "../types";
import { ConfirmRefundForm } from "./ConfirmRefundForm";
import { MarkRefundFailedForm } from "./MarkRefundFailedForm";
import type { ResultNote } from "./OrderDetailSheet";
import { RefundView } from "./RefundView";
import { RetryRefundForm } from "./RetryRefundForm";

type Mode = "view" | "confirm" | "mark_failed" | "retry";

type Props = {
  item: RefundQueueItem;
  /** Có thay đổi → màn cha tải lại danh sách khi đóng tấm; `toast` = câu hiện khi đóng. */
  onChanged: (toast: string) => void;
  onClose: () => void;
};

export function RefundSheet({ item, onChanged, onClose }: Props) {
  const [cur, setCur] = useState<RefundQueueItem>(item);
  const [mode, setMode] = useState<Mode>("view");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<ResultNote | null>(null);
  const noteRef = useRef<HTMLDivElement>(null);
  const actionRef = useRef<HTMLButtonElement>(null);
  const onChangedRef = useRef(onChanged);
  onChangedRef.current = onChanged;

  useEffect(() => {
    if (note && mode === "view") noteRef.current?.focus();
  }, [note, mode]);

  const back = () => {
    setMode("view");
    requestAnimationFrame(() => actionRef.current?.focus());
  };

  const done = (n: ResultNote, next: RefundQueueItem) => {
    setNote(n);
    setMode("view");
    setCur(next);
    onChangedRef.current(n.text);
  };

  const onConfirmed = (r: ConfirmRefundResult) =>
    done(
      { tone: "ok", text: REFUND_Q_MSG.confirmResult, duplicate: false },
      { ...cur, status: r.status, status_label: r.status_label, confirmed_at: r.confirmed_at, available_actions: [] },
    );

  const onFailed = (r: MarkRefundFailedResult) =>
    done(
      { tone: "warn", text: REFUND_Q_MSG.markFailedResult, duplicate: false },
      { ...cur, status: r.status, status_label: r.status_label, available_actions: ["retry"] },
    );

  const onRetried = (r: RetryRefundResult) =>
    done(
      { tone: "ok", text: REFUND_Q_MSG.retryResult, duplicate: false },
      { ...cur, status: r.status, status_label: r.status_label, failure_reason: "", available_actions: ["confirm", "mark_failed"] },
    );

  const title = REFUND_Q_MSG.sheetTitle(cur.id);

  return (
    <SideSheet title={title} onClose={onClose} busy={busy}>
      {mode === "confirm" ? (
        <ConfirmRefundForm item={cur} onBusy={setBusy} onCancel={back} onDone={onConfirmed} />
      ) : mode === "mark_failed" ? (
        <MarkRefundFailedForm item={cur} onBusy={setBusy} onCancel={back} onDone={onFailed} />
      ) : mode === "retry" ? (
        <RetryRefundForm item={cur} onBusy={setBusy} onCancel={back} onDone={onRetried} />
      ) : (
        <RefundView
          item={cur}
          refreshing={false}
          note={note}
          noteRef={noteRef}
          actionRef={actionRef}
          onAction={(a: RefundQueueAction) => {
            if (a === "confirm" || a === "mark_failed" || a === "retry") {
              setNote(null);
              setMode(a);
            }
          }}
        />
      )}
    </SideSheet>
  );
}
