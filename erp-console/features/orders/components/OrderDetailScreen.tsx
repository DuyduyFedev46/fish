"use client";

// Trang chi tiết đơn (ED-09, thay tấm trượt cũ): /orders/detail/?id=<pk>. Khung DetailPage: header (mã đơn · chip · nút chính ·
// "…"), thanh trạng thái, thông tin, bảng hàng/phân bổ lô/thanh toán/hoàn tiền; cột phải = khối Trợ lý AI (do trang ghép qua
// `renderAi`, vì feature không được import features/ai) và dòng thời gian. Nút chính/“…” theo bảng trạng thái của ED-09-AC3/4,
// nhưng nút CHỈ hiện khi `available_actions` của BE có thao tác (BE tính cả luật lẫn quyền). Không có "Hoàn tác": không thao
// tác nào ở đây hoàn tác được. URL chỉ có id; SĐT/địa chỉ hiện đủ cho người đã được xem đơn.

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { getGuidance } from "@/features/guidance/api";
import { nextStepLabel } from "@/features/guidance/detailAdapters";
import { EscalateModal } from "@/features/guidance/components/EscalateModal";
import { ESCALATE_MSG, escalatableStep } from "@/features/guidance/escalation";
import type { GuidanceNextStep } from "@/features/guidance/types";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, kg, vnd } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { PERM, canView } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { InfoStrip } from "@/shared/ui/detail/InfoStrip";
import { LookupCard } from "@/shared/ui/detail/LookupCard";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { Section } from "@/shared/ui/detail/Section";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline } from "@/shared/ui/detail/Timeline";
import type { SubmitConflict } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { useToast } from "@/shared/ui/overlay/Toast";
import { PersonalText } from "@/shared/ui/PersonalText";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { getOrder } from "../api";
import { DetailGate } from "../DetailGate";
import { ORDERS_MSG as M } from "../messages";
import {
  ORDER_STEPS,
  confirmPaymentToast,
  customerLinkHref,
  effectiveOrderStatus,
  holdInfo,
  orderActionPlan,
  orderPath,
  orderTimeline,
} from "../orderDetailModel";
import { refundableOfOrder } from "../refund";
import type { OrderAllocation, OrderDetail, OrderLine, OrderPayment, OrderRefund } from "../types";
import { useDetail, type DetailState } from "../useDetail";
import { useIdParam } from "../useIdParam";
import { holdLeftText, useHoldExpired, useNow } from "../useNow";
import { CancelOrderModal } from "./CancelOrderModal";
import { ConfirmPaymentModal } from "./ConfirmPaymentModal";
import { RefundModal } from "./RefundModal";
import s from "../orders.module.css";

type AiTarget = { id: number; code: string };

type LineRow = { key: string; line: OrderLine; alloc?: OrderAllocation; first: boolean };

type Props = {
  /** Trang ghép khối Trợ lý AI vào đây (feature không import features/ai). `onApplied` = tải lại đơn sau khi AI áp dụng đề xuất. */
  renderAi?: (target: AiTarget, onApplied: () => void) => React.ReactNode;
};

export function OrderDetailScreen({ renderAi }: Props) {
  const id = useIdParam();
  const detail = useDetail<OrderDetail>(id, getOrder);
  return (
    <DetailGate id={id} detail={detail} noun={M.detailNoun}>
      {(order) => <OrderDetailBody order={order} detail={detail} renderAi={renderAi} />}
    </DetailGate>
  );
}

/** Ô đếm ngược mm:ss: đồng hồ riêng nên chỉ ô này vẽ lại mỗi giây; dừng khi hết giờ. */
function HoldLeft({ until }: { until: string }) {
  const end = new Date(until).getTime();
  const now = useNow(Date.now() < end, 1000);
  return <>{holdLeftText("BOOKED", until, now)}</>;
}

type ModalKind = "confirm_payment" | "cancel" | "refund" | "escalate";

function OrderDetailBody({ order: o, detail, renderAi }: { order: OrderDetail; detail: DetailState<OrderDetail>; renderAi?: Props["renderAi"] }) {
  const { me } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [modal, setModal] = useState<ModalKind | null>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [suggest, setSuggest] = useState<string | null>(null);
  const [lookupDelivery, setLookupDelivery] = useState(false);
  const [next, setNext] = useState<string | null>(null);
  // #19: bước mình chưa làm được (guidance) → mục "Nhờ người xử lý" trong menu "…". Không có thì không hiện mục.
  const [stuckStep, setStuckStep] = useState<GuidanceNextStep | null>(null);
  // Bước đã nhờ xong trong phiên trang này: ẩn mục menu để khỏi nhờ lặp (BE không chống trùng).
  const [escalatedKey, setEscalatedKey] = useState<string | null>(null);
  const openedRef = useRef(false);

  // L5: trang không vẽ lại mỗi giây. Chỉ có một mốc giờ (chip đổi "Đã huỷ" khi hết giờ) và ô đếm ngược tự giữ đồng hồ (`HoldLeft`).
  const expired = useHoldExpired(o.status, o.reserved_until);
  const status = expired ? "AUTO_CANCELLED" : o.status;
  const hold = holdInfo(o.status, o.reserved_until, 0) ? { until: o.reserved_until as string } : null;
  const canViewCost = !!me?.can_view_cost;
  const canViewCustomer = !!me?.permissions.includes(PERM.viewCustomerList);
  const customerHref = customerLinkHref(o.customer.id, canViewCustomer);
  const hasRefund = o.available_actions.includes("create_refund") && !!o.invoice;

  const plan = useMemo(
    () =>
      orderActionPlan({
        status,
        deliveryStatus: o.delivery?.status ?? null,
        actions: o.available_actions,
        canCancel: !!me?.permissions.includes(PERM.cancelPaidOrder),
        canViewAudit: canView(me, "audit-logs"),
        canEscalate: !!stuckStep && stuckStep.key !== escalatedKey,
      }),
    [status, o.delivery?.status, o.available_actions, me, stuckStep, escalatedKey],
  );
  const beAiEnabled = me?.ai_features_enabled === true;
  const canOpenRefunds = canView(me, "refunds");
  const timeline = useMemo(() => orderTimeline(o, { canOpenRefund: canOpenRefunds }), [o, canOpenRefunds]);
  const path = orderPath({ status, deliveryStatus: o.delivery?.status ?? null, hasInvoice: !!o.invoice });

  // "Tiếp theo" của thanh trạng thái: lấy từ guidance, im lặng khi lỗi (thanh vẫn đủ nghĩa nếu thiếu dòng này).
  useEffect(() => {
    const c = new AbortController();
    getGuidance("order", o.id, c.signal)
      // Hướng dẫn của một trạng thái khác (BE chưa kịp cập nhật / dữ liệu cũ) thì bỏ, tránh gợi sai việc.
      .then((g) => {
        const stale = !!g.doc?.status && g.doc.status !== o.status;
        setNext(stale ? null : nextStepLabel(g));
        setStuckStep(stale ? null : escalatableStep(g, { ai_features_enabled: beAiEnabled }));
      })
      .catch(() => {
        setNext(null);
        setStuckStep(null);
      });
    return () => c.abort();
  }, [o.id, o.status, o.payments.length, o.refunds.length, beAiEnabled]);

  // `?open=refund` (từ màn gọi xác nhận) mở sẵn hộp "Lập phiếu hoàn" — một lần; xong bỏ tham số khỏi thanh địa chỉ.
  useEffect(() => {
    if (openedRef.current) return;
    openedRef.current = true;
    const q = new URLSearchParams(window.location.search);
    if (q.get("open") !== "refund") return;
    window.history.replaceState(null, "", `${window.location.pathname}?id=${o.id}`);
    if (hasRefund) setModal("refund");
  }, [o.id, hasRefund]);

  const reload = () => void detail.reload();
  const onConflict = (c: SubmitConflict) => {
    setModal(null);
    setConflict(c);
  };

  function copyCode() {
    const done = () => toast.success(M.copyDone);
    const fail = () => toast.warn(M.copyFailed);
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(o.code).then(done, fail);
    else fail();
  }

  function run(key: string) {
    if (key === "confirm_payment" || key === "cancel" || key === "refund") setModal(key);
    else if (key === "create_refund") setModal("refund");
    else if (key === "escalate") setModal("escalate");
    else if (key === "copy_code") copyCode();
    else if (key === "audit") router.push("/audit-logs/");
  }

  const primary = plan.primary ? (
    <button type="button" className={`btn ${plan.primary.danger ? "danger" : "primary"}`} onClick={() => run(plan.primary!.key)}>
      {plan.primary.label}
    </button>
  ) : null;
  const more: MoreMenuItem[] = plan.menu.map((m) => ({
    key: m.key,
    label: m.label,
    danger: m.danger,
    blockedReason: m.blockedReason,
    onSelect: m.blockedReason ? undefined : () => run(m.key),
  }));

  // Một bảng "Hàng & phân bổ lô" (board D2b): mỗi dòng bảng = một lô xuất của một dòng hàng. Dòng hàng có nhiều lô thì
  // tên hàng / đơn giá / thành tiền chỉ ghi ở dòng đầu (tránh cộng trùng); dòng hàng chưa phân bổ lô ghi "—" ở cột Lô.
  const rows: LineRow[] = o.lines.flatMap((l) => {
    const allocs = o.allocations.filter((a) => a.line_no === l.no);
    return (allocs.length ? allocs : [undefined]).map((a, i) => ({ key: `${l.no}-${a?.batch_id ?? "none"}`, line: l, alloc: a, first: i === 0 }));
  });
  const showCost = canViewCost && o.allocations.some((a) => a.unit_cost !== undefined);
  const lineCols: Column<LineRow>[] = [
    { key: "item", header: M.colItem, render: (r) => (r.first ? (
      <>
        {r.line.item_name} <span className={`muted ${s.mono}`}>{r.line.item_code}</span>
      </>
    ) : "") },
    { key: "batch", header: M.colBatch, mono: true, render: (r) => r.alloc?.batch_id ?? "—" },
    { key: "cost", header: M.colUnitCost, num: true, locked: true, render: (r) => (r.alloc?.unit_cost !== undefined ? vnd(r.alloc.unit_cost) : "—") },
    { key: "qty", header: M.colQty, num: true, render: (r) => kg(r.alloc?.qty_kg ?? r.line.qty_kg) },
    { key: "price", header: M.colUnitPrice, num: true, render: (r) => (r.first ? vnd(r.line.unit_price) : "") },
    { key: "discount", header: M.colDiscount, num: true, render: (r) => (r.first ? (Number(r.line.discount) > 0 ? vnd(r.line.discount) : "—") : "") },
    { key: "total", header: M.colLineTotal, num: true, render: (r) => (r.first ? vnd(r.line.line_total) : "") },
  ];
  const payCols: Column<OrderPayment>[] = [
    { key: "txn", header: M.colTxn, mono: true, render: (p) => p.bank_txn_id },
    { key: "amount", header: M.colAmount, num: true, render: (p) => vnd(p.amount) },
    { key: "match", header: M.colMatch, render: (p) => <Chip table={ENUMS.paymentMatchStatus} value={p.match_status} /> },
    { key: "at", header: M.colReceivedAt, num: true, render: (p) => (p.received_at ? dateTime(p.received_at) : "—") },
  ];
  const refundCols: Column<OrderRefund>[] = [
    { key: "amount", header: M.colRefundAmount, num: true, render: (r) => vnd(r.amount) },
    { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.refundStatus} value={r.status} /> },
    { key: "ref", header: M.colRefundRef, mono: true, render: (r) => r.bank_txn_ref || "—" },
  ];

  const canOpenPayments = canView(me, "payments");
  const canOpenDelivery = canView(me, "deliveries") || canView(me, "my-deliveries");
  const consent = "privacy_consent" in o ? o.privacy_consent : undefined;

  return (
    <DetailPage
      id="order-detail"
      header={
        <DetailHeader
          back={{ href: "/orders/", label: M.backToOrders }}
          title={o.code}
          mono
          status={<Chip table={ENUMS.salesOrderStatus} value={status} />}
          primary={primary}
          more={more}
        />
      }
      banner={
        <>
          {conflict && (
            <ConflictBanner
              noun={M.conflictNounOrder}
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
          {suggest && hasRefund && (
            <div className={`alert-box warn ${s.suggest}`} role="status">
              <Icon name="currency_exchange" />
              <span>{M.cancelSuggestText(suggest)}</span>
              <button type="button" className="btn primary" onClick={() => setModal("refund")}>
                {M.cancelSuggestRefund(suggest)}
              </button>
            </div>
          )}
        </>
      }
      aiSlot={renderAi?.({ id: o.id, code: o.code }, reload)}
      timeline={<Timeline entries={timeline} title={M.timelineDerived} />}
    >
      <InfoStrip label={M.stripLabel}>
        <InfoField label={M.fieldPlacedAt} num value={o.created_at ? dateTime(o.created_at) : null} />
        {hold && <InfoField label={M.fieldHoldLeft} num value={<span className={s.holdLeft}><HoldLeft until={hold.until} /></span>} />}
        {(hold || (o.status === "AUTO_CANCELLED" && o.reserved_until)) && (
          <InfoField label={M.fieldHoldUntil} num value={dateTime(o.reserved_until as string)} />
        )}
      </InfoStrip>

      <StatusPath
        steps={ORDER_STEPS}
        current={path.current}
        badEnd={path.badEnd}
        next={next ?? (plan.primary && plan.primary.key !== "cancel" ? plan.primary.label : null)}
        done={timeline.slice(0, 3).map((e) => e.label).reverse()}
      />

      <InfoGrid
        title={M.sectionOrderInfo}
        groups={[
          {
            title: M.groupPayment,
            children: (
              <>
                <InfoField label={M.fieldTotal} num value={o.total_amount ? vnd(o.total_amount) : null} />
                <InfoField label={M.fieldInvoice} mono value={o.invoice?.code ?? null} />
                <InfoField label={M.fieldMatched} value={o.payments.length ? M.countPayments(o.payments.length) : null} />
                <InfoField label={M.fieldRefund} value={o.refunds.length ? M.countRefunds(o.refunds.length) : null} />
                {(o.cancel_note ?? "").trim() !== "" && <InfoField label={M.fieldCancelNote} value={o.cancel_note} />}
              </>
            ),
          },
          {
            title: M.groupDelivery,
            children: (
              <>
                <InfoField
                  label={M.fieldCustomer}
                  value={
                    <>
                      <PersonalText value={o.customer.name} />
                      {customerHref && (
                        <>
                          {" · "}
                          <Link href={customerHref} className="inline-link">
                            {M.openCustomer}
                          </Link>
                        </>
                      )}
                    </>
                  }
                />
                <InfoField
                  label={M.fieldPhone}
                  num
                  value={
                    o.customer.phone ? (
                      <a href={`tel:${o.customer.phone}`} className="inline-link">
                        {o.customer.phone}
                      </a>
                    ) : (
                      <PersonalText value={o.customer.phone} />
                    )
                  }
                />
                <InfoField label={M.fieldAddress} value={<PersonalText value={o.customer.address} />} />
                {o.delivery &&
                  (canOpenDelivery ? (
                    <InfoField label={M.fieldDelivery} kind="link" mono value={o.delivery.code} onOpen={() => setLookupDelivery(true)} />
                  ) : (
                    <InfoField label={M.fieldDelivery} mono value={o.delivery.code} />
                  ))}
                {o.delivery && <InfoField label={M.fieldDeliveryStatus} value={<Chip table={ENUMS.deliveryStatus} value={o.delivery.status} />} />}
                {consent !== undefined && (
                  <InfoField
                    label={M.fieldConsent}
                    value={
                      consent ? (
                        <>
                          {M.consentValue(consent.policy_version, consent.accepted_at ? dateTime(consent.accepted_at) : null)}
                          {" · "}
                          <Link href={`/content/edit/?id=${consent.policy_entry_id}&version=${consent.policy_version}`} className="inline-link">
                            {M.consentOpen}
                          </Link>
                        </>
                      ) : (
                        <span className="muted">{M.consentNone}</span>
                      )
                    }
                  />
                )}
              </>
            ),
          },
        ]}
      />

      <Section title={M.linesTitle} count={o.lines.length} aria-label={M.linesTitle} flush>
        <DataTable
          caption={M.linesCaption}
          columns={lineCols}
          rows={rows}
          rowKey={(r) => r.key}
          noun={M.detailNoun}
          empty={{ icon: "inbox", title: M.linesEmpty }}
          canViewCost={showCost}
          dense
        />
        {o.total_amount && (
          <div className={s.totalRow}>
            <span>{M.totalSum}</span>
            <b className="num">{vnd(o.total_amount)}</b>
          </div>
        )}
      </Section>

      <Section title={M.paymentsTitle} count={o.payments.length} aria-label={M.paymentsTitle} flush>
        <DataTable
          caption={M.paymentsCaption}
          columns={payCols}
          rows={o.payments}
          rowKey={(p) => p.id}
          rowHref={canOpenPayments ? (p) => `/orders/payments/detail/?id=${p.id}` : undefined}
          noun={M.paymentNoun}
          empty={{ icon: "payments", title: M.paymentsEmpty }}
          canViewCost={false}
        />
      </Section>

      <Section title={M.refundsTitle} count={o.refunds.length} aria-label={M.refundsTitle} flush>
        <DataTable
          caption={M.refundsCaption}
          columns={refundCols}
          rows={o.refunds}
          rowKey={(r) => r.id}
          rowHref={canOpenRefunds ? (r) => `/orders/refunds/detail/?id=${r.id}` : undefined}
          noun={M.refundNoun}
          empty={{ icon: "currency_exchange", title: M.refundsEmpty }}
          canViewCost={false}
        />
      </Section>

      {modal === "confirm_payment" && (
        <ConfirmPaymentModal
          order={{ id: o.id, code: o.code, status, total_amount: o.total_amount ?? "0" }}
          onClose={() => setModal(null)}
          onConflict={onConflict}
          onAutoCancelled={(message) => {
            setModal(null);
            toast.warn(message);
            reload();
          }}
          onDone={(r) => {
            setModal(null);
            const t = confirmPaymentToast(r, o.code);
            if (t.kind === "success") toast.success(t.message);
            else toast.warn(t.message);
            reload();
          }}
        />
      )}
      {modal === "escalate" && stuckStep && (
        <EscalateModal
          docType="order"
          docId={o.id}
          step={stuckStep}
          onClose={() => setModal(null)}
          onReload={() => {
            setModal(null);
            reload();
          }}
          onDone={(who) => {
            setModal(null);
            setEscalatedKey(stuckStep.key);
            toast.success(ESCALATE_MSG.done(who));
          }}
        />
      )}
      {modal === "cancel" && (
        <CancelOrderModal
          order={{ id: o.id, code: o.code, total_amount: o.total_amount ?? "0", delivery_status: o.delivery?.status ?? null }}
          onClose={() => setModal(null)}
          onConflict={onConflict}
          onDone={(r) => {
            setModal(null);
            toast.success(M.cancelResult(o.code));
            if (r.suggest_refund_amount && Number(r.suggest_refund_amount) > 0) setSuggest(r.suggest_refund_amount);
            reload();
          }}
        />
      )}
      {modal === "refund" && o.invoice && (
        <RefundModal
          target={{ kind: "invoice", id: o.invoice.id, invoiceTotal: o.total_amount ?? "0" }}
          refundableMax={suggest ?? refundableOfOrder(o)}
          reasonDefault={status === "CANCELLED" || status === "AUTO_CANCELLED" ? M.refundReasonCancelled : ""}
          summary={[
            { label: M.rowOrder, value: o.code, mono: true },
            { label: M.rowOrderTotal, value: vnd(o.total_amount ?? "0"), num: true },
            { label: M.rowRefundable, value: vnd(refundableOfOrder(o)), num: true, strong: true },
          ]}
          onClose={() => setModal(null)}
          onConflict={onConflict}
          onDone={(r) => {
            setModal(null);
            setSuggest(null);
            toast.success(r.duplicate ? M.resultRefundDup(r.amount) : M.resultRefund(r.amount));
            reload();
          }}
        />
      )}
      {lookupDelivery && o.delivery && <LookupCard kind="delivery" id={o.delivery.id} onClose={() => setLookupDelivery(false)} />}
    </DetailPage>
  );
}
