"use client";

// Tấm chi tiết một khoản tiền lệch (S12/S13). Chế độ: xem · gắn vào đơn · xác nhận đơn · lập phiếu hoàn. Nút CHỈ theo
// `available_actions` của khoản (BE tính luật + quyền). Thao tác xong: báo kết quả ngay trong tấm theo response BE, tải lại
// khoản (GET /api/sales/payments/{id}/ — thiếu thì sửa tại chỗ theo response), báo màn cha tải lại danh sách; đóng tấm →
// thông báo nổi. Đang gửi thì tấm không đóng (chống bỏ dở + chống bấm đúp cùng khoá trong form).

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { vnd } from "@/shared/lib/format";
import { SideSheet } from "@/shared/ui/SideSheet";
import { getPayment } from "../api";
import { ORDER_LABEL, RESOLUTION_LABEL, labelOf } from "../labels";
import { ORDERS_MSG, QUEUE_MSG } from "../messages";
import type { CreateRefundResult, PaymentAction, PaymentQueueItem, QueueOrderRef, ResolveResult } from "../types";
import { AttachOrderForm } from "./AttachOrderForm";
import { ConfirmOrderForm } from "./ConfirmOrderForm";
import type { ResultNote } from "./OrderDetailSheet";
import { PaymentView } from "./PaymentView";
import { RefundForm } from "./RefundForm";

type Mode = "view" | "attach_to_order" | "confirm_order" | "refund";

type Props = {
  item: PaymentQueueItem;
  /** Có thay đổi → màn cha tải lại danh sách khi đóng tấm; `toast` = câu hiện khi đóng. */
  onChanged: (toast: string) => void;
  onOpenOrder: (o: QueueOrderRef) => void;
  onClose: () => void;
};

export function PaymentSheet({ item, onChanged, onOpenOrder, onClose }: Props) {
  const [cur, setCur] = useState<PaymentQueueItem>(item);
  const [mode, setMode] = useState<Mode>("view");
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [stale, setStale] = useState(false);
  const [note, setNote] = useState<ResultNote | null>(null);
  const noteRef = useRef<HTMLDivElement>(null);
  const actionRef = useRef<HTMLButtonElement>(null);
  const seq = useRef(0);
  const onChangedRef = useRef(onChanged);
  onChangedRef.current = onChanged;

  useEffect(
    () => () => {
      seq.current += 1;
    },
    [],
  );

  useEffect(() => {
    if (note && mode === "view") noteRef.current?.focus();
  }, [note, mode]);

  /** Tải lại khoản sau thao tác; lỗi → giữ bản sửa tại chỗ `fallback` (nút ẩn hết, nhắc làm mới danh sách). */
  const refresh = useCallback(async (fallback: PaymentQueueItem) => {
    const id = ++seq.current;
    setRefreshing(true);
    try {
      const fresh = await getPayment(fallback.id);
      if (id !== seq.current) return;
      setCur(fresh);
      setStale(false);
    } catch (err) {
      if (id !== seq.current) return;
      if (err instanceof ApiError && err.status === 401) return;
      setCur(fallback);
      setStale(true);
    } finally {
      if (id === seq.current) setRefreshing(false);
    }
  }, []);

  const done = (n: ResultNote, fallback: PaymentQueueItem) => {
    setNote(n);
    setMode("view");
    onChangedRef.current(n.text);
    void refresh(fallback);
  };

  const onResolved = (r: ResolveResult, action: "ATTACH_TO_ORDER" | "CONFIRM_ORDER", order: QueueOrderRef) => {
    const statusText = labelOf(ORDER_LABEL, r.order_status);
    const open = r.resolution_status !== "RESOLVED";
    const base =
      action === "CONFIRM_ORDER"
        ? QUEUE_MSG.resultConfirmed(order.code, statusText, r.resolved_payment_ids?.length ?? 1)
        : open
          ? QUEUE_MSG.resultAttachedOpen(order.code, statusText)
          : QUEUE_MSG.resultAttached(order.code, statusText);
    const text =
      base +
      (r.delivery_note_code ? QUEUE_MSG.resultDelivery(r.delivery_note_code) : "") +
      (r.overpaid_amount ? ORDERS_MSG.resultOverpaid(r.overpaid_amount) : "");
    done(
      { tone: open ? "warn" : "ok", text, duplicate: false },
      {
        ...cur,
        order: { ...order, status: r.order_status, status_label: statusText },
        resolution_status: r.resolution_status,
        resolution: r.resolution,
        resolution_label: r.resolution ? labelOf(RESOLUTION_LABEL, r.resolution) : undefined,
        available_actions: [],
      },
    );
  };

  const onRefunded = (r: CreateRefundResult) => {
    done(
      { tone: r.duplicate ? "warn" : "ok", text: r.duplicate ? QUEUE_MSG.resultRefundDup(r.amount) : QUEUE_MSG.resultRefund(r.amount), duplicate: !!r.duplicate },
      {
        ...cur,
        refundable_amount:
          cur.refundable_amount !== undefined && !r.duplicate ? String(Math.max(0, Number(cur.refundable_amount) - Number(r.amount))) : cur.refundable_amount,
        available_actions: [],
      },
    );
  };

  const back = () => {
    setMode("view");
    requestAnimationFrame(() => actionRef.current?.focus());
  };

  const title =
    mode === "attach_to_order"
      ? QUEUE_MSG.attachTitle(cur.bank_txn_id)
      : mode === "confirm_order" && cur.order
        ? QUEUE_MSG.confirmTitle(cur.order.code)
        : mode === "refund"
          ? QUEUE_MSG.refundTitle(cur.bank_txn_id)
          : QUEUE_MSG.sheetTitle(cur.bank_txn_id);

  return (
    <SideSheet title={title} onClose={onClose} busy={busy}>
      {mode === "attach_to_order" ? (
        <AttachOrderForm item={cur} onBusy={setBusy} onCancel={back} onDone={(r, o) => onResolved(r, "ATTACH_TO_ORDER", o)} />
      ) : mode === "confirm_order" && cur.order ? (
        <ConfirmOrderForm item={cur} order={cur.order} onBusy={setBusy} onCancel={back} onDone={(r) => onResolved(r, "CONFIRM_ORDER", cur.order!)} />
      ) : mode === "refund" ? (
        <RefundForm
          target={{ kind: "payment", id: cur.id }}
          refundableMax={cur.refundable_amount ?? cur.amount}
          reasonDefault={QUEUE_MSG.refundReasonDefault[cur.match_status] || ""}
          subLabel={
            <>
              {cur.bank_txn_id} · {vnd(cur.amount)}
              {cur.order ? ` · ${cur.order.code}` : ""}
            </>
          }
          onBusy={setBusy}
          onCancel={back}
          onDone={onRefunded}
        />
      ) : (
        <PaymentView
          item={cur}
          refreshing={refreshing}
          stale={stale}
          note={note}
          noteRef={noteRef}
          actionRef={actionRef}
          onOpenOrder={onOpenOrder}
          onAction={(a: PaymentAction) => {
            if (a === "attach_to_order" || a === "confirm_order" || a === "refund") {
              setNote(null);
              setMode(a);
            }
          }}
        />
      )}
    </SideSheet>
  );
}
