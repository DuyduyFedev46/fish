"use client";

// Trang chi tiết khoản tiền (ED-11): /orders/payments/detail/?id=<pk>. Nút theo `available_actions` của khoản (Quản lý: rỗng,
// BE vẫn chặn 403): Gắn vào đơn (F2d) · Xác nhận đơn đủ tiền (F2e) · Lập phiếu hoàn (F2c). Nội dung chuyển khoản chỉ hiện khi
// BE trả (người có quyền); không bao giờ đưa vào log hay yêu cầu AI. 409 → ConflictBanner, không xử lý lần hai.

import { useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS, enumOf } from "@/shared/lib/enums";
import { dateTime, vnd } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { canView } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { Section } from "@/shared/ui/detail/Section";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline } from "@/shared/ui/detail/Timeline";
import type { SubmitConflict } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { getPayment } from "../api";
import { DetailGate } from "../DetailGate";
import { ORDERS_MSG as M } from "../messages";
import { PAYMENT_STEPS, paymentActionPlan, paymentTimeline } from "../orderDetailModel";
import { digits } from "../amount";
import type { PaymentQueueItem, QueueRefund } from "../types";
import { useDetail, type DetailState } from "../useDetail";
import { useIdParam } from "../useIdParam";
import { AttachOrderModal } from "./AttachOrderModal";
import { ConfirmOrderModal } from "./ConfirmOrderModal";
import { RefundModal } from "./RefundModal";
import s from "../orders.module.css";

type Props = {
  /** Trang ghép khối Trợ lý AI vào đây (feature không import features/ai). `onApplied` = tải lại khoản tiền sau khi AI áp dụng đề xuất. */
  renderAi?: (target: { id: number }, onApplied: () => void) => React.ReactNode;
};

export function PaymentDetailScreen({ renderAi }: Props) {
  const id = useIdParam();
  const detail = useDetail<PaymentQueueItem>(id, getPayment);
  return (
    <DetailGate id={id} detail={detail} noun={M.paymentNoun}>
      {(p) => <PaymentDetailBody payment={p} detail={detail} renderAi={renderAi} />}
    </DetailGate>
  );
}

type ModalKind = "attach_to_order" | "confirm_order" | "refund";

function PaymentDetailBody({ payment: p, detail, renderAi }: { payment: PaymentQueueItem; detail: DetailState<PaymentQueueItem>; renderAi?: Props["renderAi"] }) {
  const { me } = useAuth();
  const toast = useToast();
  const [modal, setModal] = useState<ModalKind | null>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);

  const plan = useMemo(() => paymentActionPlan(p.available_actions), [p.available_actions]);
  const timeline = useMemo(() => paymentTimeline(p), [p]);
  const order = p.order;
  const diff = order ? Number(order.total_amount) - Number(order.paid_total) : 0;
  const canOpenOrder = canView(me, "orders");
  const canOpenRefunds = canView(me, "refunds");
  const refundMax = digits(p.refundable_amount ?? p.amount);

  const reload = () => void detail.reload();
  const onConflict = (c: SubmitConflict) => {
    setModal(null);
    setConflict(c);
  };

  const primary = plan.primary ? (
    <button type="button" className="btn primary" onClick={() => setModal(plan.primary!.key as ModalKind)}>
      {plan.primary.label}
    </button>
  ) : null;
  const more: MoreMenuItem[] = plan.menu.map((m) => ({ key: m.key, label: m.label, onSelect: () => setModal(m.key as ModalKind) }));

  const refundCols: Column<QueueRefund>[] = [
    { key: "amount", header: M.colRefundAmount, num: true, render: (r) => vnd(r.amount) },
    { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.refundStatus} value={r.status} /> },
    { key: "ref", header: M.colRefundRef, mono: true, render: (r) => r.bank_txn_ref || "—" },
  ];

  return (
    <DetailPage
      id="payment-detail"
      header={
        <DetailHeader
          back={{ href: "/orders/payments/", label: M.backToQueue }}
          title={p.bank_txn_id}
          mono
          status={<Chip table={ENUMS.paymentResolutionStatus} value={p.resolution_status} />}
          primary={primary}
          more={more}
        />
      }
      banner={
        <>
          {conflict && (
            <ConflictBanner
              noun={M.conflictNounPayment}
              updatedByName={conflict.updatedByName}
              updatedAt={conflict.updatedAt}
              reloading={detail.reloading}
              onReload={() => {
                setConflict(null);
                reload();
              }}
            />
          )}
          {detail.error != null && !detail.reloading && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>{loadErrorText(detail.error)}</span>
              <button type="button" className="btn" onClick={reload}>
                Thử lại
              </button>
            </div>
          )}
        </>
      }
      aiSlot={renderAi?.({ id: p.id }, reload)}
      timeline={<Timeline entries={timeline} title={M.timelineDerived} />}
    >
      <StatusPath steps={PAYMENT_STEPS} current={p.resolution_status === "RESOLVED" ? "RESOLVED" : "OPEN"} />

      <InfoGrid title={M.sectionInfo}>
        <InfoField label={M.fieldTxn} mono value={p.bank_txn_id} />
        <InfoField label={M.fieldAmount} num value={vnd(p.amount)} />
        <InfoField label={M.fieldMatch} value={<Chip table={ENUMS.paymentMatchStatus} value={p.match_status} />} />
        <InfoField label={M.fieldReceivedAt} num value={p.received_at ? dateTime(p.received_at) : null} />
        <InfoField label={M.fieldSource} value={p.source ? <Chip table={ENUMS.paymentSource} value={p.source} /> : null} />
        {typeof p.content === "string" && p.content !== "" && <InfoField label={M.fieldTransferContent} value={p.content} />}
        <InfoField label={M.fieldResolution} value={<Chip table={ENUMS.paymentResolutionStatus} value={p.resolution_status} />} />
        {p.resolution && <InfoField label={M.fieldResolutionHow} value={<Chip table={ENUMS.paymentResolution} value={p.resolution} />} />}
        {typeof p.resolved_by === "string" && p.resolved_by !== "" && <InfoField label={M.fieldResolvedBy} value={p.resolved_by} />}
        {p.resolved_at && <InfoField label={M.fieldResolvedAt} num value={dateTime(p.resolved_at)} />}
        {p.resolution_note && <InfoField label={M.fieldNote} value={p.resolution_note} />}
      </InfoGrid>

      {order ? (
        <InfoGrid title={M.fieldRelatedOrder} label={M.fieldRelatedOrder}>
          <InfoField
            label={M.rowOrder}
            mono
            value={
              canOpenOrder ? (
                <Link href={`/orders/detail/?id=${order.id}`} className="inline-link">
                  {order.code}
                </Link>
              ) : (
                order.code
              )
            }
          />
          <InfoField label={M.colStatus} value={<Chip table={ENUMS.salesOrderStatus} value={order.status} />} />
          <InfoField label={M.fieldOrderTotal} num value={vnd(order.total_amount)} />
          <InfoField label={M.fieldOrderPaid} num value={vnd(order.paid_total)} />
          {diff > 0 && <InfoField label={M.fieldOrderMissing} num value={vnd(String(diff))} />}
          {diff < 0 && <InfoField label={M.fieldOrderOver} num value={vnd(String(-diff))} />}
        </InfoGrid>
      ) : (
        <Section title={M.fieldRelatedOrder} aria-label={M.fieldRelatedOrder}>
          <p className="muted">{M.noOrderHint}</p>
        </Section>
      )}

      {(p.refunds?.length ?? 0) > 0 && (
        <Section title={M.paymentRefundsTitle} count={p.refunds?.length} aria-label={M.paymentRefundsTitle} flush>
          <DataTable
            caption={M.paymentRefundsCaption}
            columns={refundCols}
            rows={p.refunds ?? []}
            rowKey={(r) => r.id}
            rowHref={canOpenRefunds ? (r) => `/orders/refunds/detail/?id=${r.id}` : undefined}
            noun={M.refundNoun}
            empty={{ icon: "currency_exchange", title: M.refundsEmpty }}
            canViewCost={false}
          />
        </Section>
      )}

      {modal === "attach_to_order" && (
        <AttachOrderModal
          payment={{ id: p.id, bank_txn_id: p.bank_txn_id, amount: p.amount }}
          onClose={() => setModal(null)}
          onConflict={onConflict}
          onDone={(r, picked) => {
            setModal(null);
            const label = r.order_status ? enumOf(ENUMS.salesOrderStatus, r.order_status).label : "";
            if (r.resolution_status === "RESOLVED") toast.success(M.resultAttached(picked.code, label));
            else toast.warn(M.resultAttachedOpen(picked.code, label));
            reload();
          }}
        />
      )}
      {modal === "confirm_order" && order && (
        <ConfirmOrderModal
          payment={p}
          onClose={() => setModal(null)}
          onConflict={onConflict}
          onDone={(r) => {
            setModal(null);
            const label = enumOf(ENUMS.salesOrderStatus, r.order_status).label;
            toast.success(M.resultConfirmed(order.code, label, r.resolved_payment_ids?.length ?? 1));
            reload();
          }}
        />
      )}
      {modal === "refund" && (
        <RefundModal
          target={{ kind: "payment", id: p.id }}
          refundableMax={refundMax}
          reasonDefault={M.refundReasonByStatus[p.match_status] ?? ""}
          summary={[
            { label: M.rowSourcePayment, value: p.bank_txn_id, mono: true },
            { label: M.fieldAmount, value: vnd(p.amount), num: true },
            { label: M.rowRefundable, value: vnd(refundMax), num: true, strong: true },
          ]}
          onClose={() => setModal(null)}
          onConflict={onConflict}
          onDone={(r) => {
            setModal(null);
            toast.success(r.duplicate ? M.resultRefundDup(r.amount) : M.resultRefund(r.amount));
            reload();
          }}
        />
      )}
    </DetailPage>
  );
}
