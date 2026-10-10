"use client";

// Trang chi tiết phiếu hoàn tiền (ED-12): /orders/refunds/detail/?id=<pk>. Chủ: "Xác nhận đã hoàn tiền" (F2f) hoặc "Chuyển lại" khi
// Thất bại; "Báo chuyển thất bại" (F2g) nằm trong "…". Quản lý xem được nhưng `available_actions` rỗng → không có nút (BE 403
// nếu gọi). Phiếu Thất bại hiện "Lý do thất bại" thành một trường riêng. SĐT hiện đủ; BE trả sẵn `order_code` nhưng không trả
// id đơn nên link "Xem đơn" tra id theo mã đơn (đúng mã, không ghi vào URL).

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, vnd } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { canView } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline } from "@/shared/ui/detail/Timeline";
import type { SubmitConflict } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { useToast } from "@/shared/ui/overlay/Toast";
import { personalText, type CustomerHiddenReason } from "@/shared/lib/personalData";
import { PersonalText } from "@/shared/ui/PersonalText";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { getRefund, listOrders } from "../api";
import { DetailGate } from "../DetailGate";
import { ORDERS_MSG as M } from "../messages";
import { REFUND_STEPS, refundActionPlan, refundPath, refundTimeline } from "../orderDetailModel";
import type { RefundQueueItem } from "../types";
import { useDetail, type DetailState } from "../useDetail";
import { useIdParam } from "../useIdParam";
import { ConfirmRefundModal, MarkRefundFailedModal, RetryRefundModal } from "./RefundActionModals";

/** §2.7: ô khách đã bị che (`null`) ghi lý do (quá 7 ngày / không có quyền xem thông tin khách); còn lại như PersonalText. */
function CustomerCell({ value, reason }: { value: string | null | undefined; reason?: CustomerHiddenReason | null }) {
  if (value === null) return <span className="muted">{personalText(null, "—", reason)}</span>;
  return <PersonalText value={value} />;
}

type Props = {
  /** Trang ghép khối Trợ lý AI vào đây (feature không import features/ai). `onApplied` = tải lại phiếu hoàn tiền sau khi AI áp dụng đề xuất. */
  renderAi?: (target: { id: number }, onApplied: () => void) => React.ReactNode;
};

export function RefundDetailScreen({ renderAi }: Props) {
  const id = useIdParam();
  const detail = useDetail<RefundQueueItem>(id, getRefund);
  return (
    <DetailGate id={id} detail={detail} noun={M.refundNoun} listHref="/orders/refunds/">
      {(r) => <RefundDetailBody refund={r} detail={detail} renderAi={renderAi} />}
    </DetailGate>
  );
}

type ModalKind = "confirm" | "mark_failed" | "retry";

function RefundDetailBody({ refund: r, detail, renderAi }: { refund: RefundQueueItem; detail: DetailState<RefundQueueItem>; renderAi?: Props["renderAi"] }) {
  const { me } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [modal, setModal] = useState<ModalKind | null>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [opening, setOpening] = useState(false);

  const plan = useMemo(() => refundActionPlan(r.available_actions), [r.available_actions]);
  const timeline = useMemo(() => refundTimeline(r), [r]);
  const path = refundPath(r.status);
  const canOpenOrder = canView(me, "orders") && !!r.order_code;

  const reload = () => void detail.reload();
  const onConflict = (c: SubmitConflict) => {
    setModal(null);
    setConflict(c);
  };

  async function openOrder() {
    if (!r.order_code || opening) return;
    setOpening(true);
    try {
      const page = await listOrders({ status: "", date_from: "", date_to: "", q: r.order_code });
      const hit = page.results.find((o) => o.code === r.order_code);
      if (hit) router.push(`/orders/detail/?id=${hit.id}`);
      else toast.warn(M.orderNotFound);
    } catch (err) {
      toast.error(loadErrorText(err));
    } finally {
      setOpening(false);
    }
  }

  const primary = plan.primary ? (
    <button type="button" className="btn primary" onClick={() => setModal(plan.primary!.key as ModalKind)}>
      {plan.primary.label}
    </button>
  ) : null;
  const more: MoreMenuItem[] = plan.menu.map((m) => ({ key: m.key, label: m.label, danger: m.danger, onSelect: () => setModal(m.key as ModalKind) }));
  const common = { refund: r, onClose: () => setModal(null), onConflict };

  return (
    <DetailPage
      id="refund-detail"
      header={
        <DetailHeader
          back={{ href: "/orders/refunds/", label: M.backToRefunds }}
          title={M.refundIdTitle(r.id)}
          status={<Chip table={ENUMS.refundStatus} value={r.status} />}
          primary={primary}
          more={more}
        />
      }
      banner={
        <>
          {conflict && (
            <ConflictBanner
              noun={M.conflictNounRefund}
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
      aiSlot={renderAi?.({ id: r.id }, reload)}
      timeline={<Timeline entries={timeline} title={M.timelineDerived} />}
    >
      <StatusPath steps={REFUND_STEPS} current={path.current} badEnd={path.badEnd} />

      <InfoGrid title={M.sectionInfo}>
        <InfoField label={M.fieldRefundAmount} num value={vnd(r.amount)} />
        <InfoField label={M.fieldRefundReason} value={r.reason} />
        {r.status === "FAILED" && <InfoField label={M.fieldRefundFailure} value={r.failure_reason || null} />}
        <InfoField
          label={M.fieldRefundOrder}
          mono
          value={
            r.order_code ? (
              canOpenOrder ? (
                <button type="button" className="inline-link" onClick={() => void openOrder()} disabled={opening} aria-busy={opening || undefined}>
                  {r.order_code}
                </button>
              ) : (
                r.order_code
              )
            ) : (
              <span className="muted">{M.noInvoice}</span>
            )
          }
        />
        <InfoField label={M.fieldRefundCustomer} value={<CustomerCell value={r.customer_name} reason={r.customer_hidden_reason} />} />
        <InfoField label={M.fieldRefundPhone} num value={<CustomerCell value={r.customer_phone} reason={r.customer_hidden_reason} />} />
        <InfoField label={M.fieldRefundSourceTxn} mono value={r.source_bank_txn_id || null} />
        <InfoField label={M.fieldRefundRef} mono value={r.bank_txn_ref || null} />
        {r.method && <InfoField label={M.fieldRefundMethod} value={<Chip table={ENUMS.refundMethod} value={r.method} />} />}
        <InfoField label={M.fieldRefundCreatedAt} num value={r.created_at ? dateTime(r.created_at) : null} />
        {r.confirmed_at && <InfoField label={M.fieldRefundConfirmedAt} num value={dateTime(r.confirmed_at)} />}
      </InfoGrid>

      {modal === "confirm" && (
        <ConfirmRefundModal
          {...common}
          onDone={() => {
            setModal(null);
            toast.success(M.resultRefundConfirmed);
            reload();
          }}
        />
      )}
      {modal === "mark_failed" && (
        <MarkRefundFailedModal
          {...common}
          onDone={() => {
            setModal(null);
            toast.warn(M.resultRefundFailed);
            reload();
          }}
        />
      )}
      {modal === "retry" && (
        <RetryRefundModal
          {...common}
          onDone={() => {
            setModal(null);
            toast.success(M.resultRetry);
            reload();
          }}
        />
      )}
    </DetailPage>
  );
}
