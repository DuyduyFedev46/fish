"use client";

// Chi tiết một đơn trong tấm bên (S10): tải GET /api/sales/orders/{id}/, vẽ dòng hàng, phân bổ lô, thanh toán, giao hàng,
// hoàn tiền, dòng thời gian. Nút thao tác CHỈ theo `available_actions` (FE không tự suy luật); L7 nối "confirm_payment"
// (S11). Xác nhận xong: báo kết quả ngay trong tấm (theo `result` BE trả), tải lại chi tiết, sửa dòng trong danh sách,
// và khi đóng tấm thì hiện thông báo nổi (chỉ với kết quả PAID).

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { SideSheet } from "@/shared/ui/SideSheet";
import { ErrorBox } from "@/shared/ui/StateBox";
import { getOrder } from "../api";
import { ORDER_LABEL } from "../labels";
import { ORDERS_MSG } from "../messages";
import type { ConfirmPaymentResult, OrderDetail, OrderListItem } from "../types";
import { ConfirmPaymentForm } from "./ConfirmPaymentForm";
import { OrderDetailView } from "./OrderDetailView";
import s from "../orders.module.css";

type Mode = "view" | "confirm";
/** `queueLink` = kèm liên kết tới hàng chờ thanh toán (khoản thiếu / về sau khi huỷ / chuyển thừa vào hàng chờ). */
export type ResultNote = { tone: "ok" | "warn"; text: string; duplicate: boolean; queueLink?: boolean };

type Props = {
  /** Dòng đã bấm trong danh sách — để có tiêu đề/tổng tiền ngay khi chi tiết đang tải. */
  summary: OrderListItem;
  /** Chi tiết đổi sau thao tác → sửa dòng trong danh sách; `toast` = câu hiện khi đóng tấm (nếu có). */
  onChanged: (change: Partial<OrderListItem>, toast?: string) => void;
  onClose: () => void;
};

function resultNote(r: ConfirmPaymentResult, code: string): ResultNote {
  let text: string;
  let tone: ResultNote["tone"] = "warn";
  if (r.result === "PAID") {
    tone = "ok";
    text = ORDERS_MSG.resultPaid(code, r.delivery_note_code) + (r.overpaid_amount ? ORDERS_MSG.resultOverpaid(r.overpaid_amount) : "");
  } else if (r.result === "UNDERPAID") {
    text = ORDERS_MSG.resultUnder(r.paid_total || "0", r.missing || "0");
  } else if (r.result === "ORPHAN") {
    text = ORDERS_MSG.resultOrphan;
  } else {
    text = ORDERS_MSG.resultOther(ORDER_LABEL[r.order_status] || r.order_status);
  }
  return { tone, text, duplicate: r.duplicate, queueLink: !!r.overpaid_amount || r.result === "UNDERPAID" || r.result === "ORPHAN" };
}

export function OrderDetailSheet({ summary, onChanged, onClose }: Props) {
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<Mode>("view");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<ResultNote | null>(null);
  const seq = useRef(0);
  const noteRef = useRef<HTMLDivElement>(null);
  const actionRef = useRef<HTMLButtonElement>(null);
  const onChangedRef = useRef(onChanged);
  onChangedRef.current = onChanged;

  const load = useCallback(
    async (after?: (d: OrderDetail) => void) => {
      const id = ++seq.current;
      setLoading(true);
      setError(null);
      try {
        const d = await getOrder(summary.id);
        if (id !== seq.current) return;
        setDetail(d);
        after?.(d);
      } catch (err) {
        if (id !== seq.current) return;
        if (!(err instanceof ApiError && err.status === 401)) setError(err);
      } finally {
        if (id === seq.current) setLoading(false);
      }
    },
    [summary.id],
  );

  useEffect(() => {
    void load();
    return () => {
      seq.current += 1;
    };
  }, [load]);

  // Có kết quả mới → đưa focus vào dòng báo để người dùng (và trình đọc màn hình) thấy ngay.
  useEffect(() => {
    if (note && mode === "view") noteRef.current?.focus();
  }, [note, mode]);

  const code = detail?.code || summary.code;
  const title = mode === "confirm" ? ORDERS_MSG.confirmTitle(code) : `Đơn ${code}`;

  const onConfirmed = (r: ConfirmPaymentResult) => {
    const n = resultNote(r, code);
    setNote(n);
    setMode("view");
    void load((d) => {
      onChangedRef.current(
        {
          status: d.status,
          status_label: d.status_label || ORDER_LABEL[d.status] || d.status,
          reserved_until: d.reserved_until ?? null,
          delivery_status: d.delivery ? d.delivery.status : null,
        },
        r.result === "PAID" && !r.duplicate ? n.text : undefined,
      );
    });
  };

  return (
    <SideSheet title={title} onClose={onClose} busy={busy}>
      {mode === "confirm" && detail ? (
        <ConfirmPaymentForm
          order={detail}
          fallbackTotal={summary.total_amount}
          onBusy={setBusy}
          onCancel={() => {
            setMode("view");
            requestAnimationFrame(() => actionRef.current?.focus());
          }}
          onDone={onConfirmed}
        />
      ) : detail ? (
        <OrderDetailView
          order={detail}
          fallback={summary}
          refreshing={loading}
          refreshError={error ? loadErrorText(error) : null}
          onRetry={() => void load()}
          note={note}
          noteRef={noteRef}
          actionRef={actionRef}
          onAction={(a) => {
            if (a === "confirm_payment") {
              setNote(null);
              setMode("confirm");
            }
          }}
        />
      ) : error ? (
        <div className={s.pane}>
          <ErrorBox
            icon={error instanceof ApiError && error.status === 403 ? "lock" : undefined}
            message={loadErrorText(error)}
            onRetry={() => void load()}
          />
        </div>
      ) : (
        <div className={s.pane} role="status" aria-busy="true">
          <span className="sr-only">{ORDERS_MSG.detailLoading}</span>
          <div className={s.skel} aria-hidden="true">
            <span className="sk sk-s" />
            <span className={`sk sk-m ${s.skBig}`} />
            <span className="sk sk-l" />
            <span className="sk sk-m" />
            <span className="sk sk-l" />
            <span className="sk sk-s" />
          </div>
        </div>
      )}
    </SideSheet>
  );
}
