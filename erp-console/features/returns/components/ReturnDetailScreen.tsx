"use client";

// Chi tiết hàng hoàn về kho (ED-26 / W5f): /returns/detail/?id=<pk>. Khung DetailPage: header (mã mono · chip · [Tái nhập vào lô] [Huỷ bỏ, ghi lỗ]),
// StatusPath (Chờ duyệt → Đã duyệt) kèm Tiếp theo / Đã làm, khối thông tin, cột phải = Trợ lý AI + dòng thời gian.
// Hai nút duyệt chỉ hiện cho người có inventory.approve_returntostock khi phiếu còn Chờ duyệt; cả hai mở hộp F2n (chọn sẵn quyết định đã bấm).
// "Huỷ phiếu hàng hoàn" (Lô bổ sung A #8) nằm trong menu "…": phiếu còn Chờ duyệt, người có quyền duyệt/sửa hoặc người tạo phiếu; có hộp xác nhận
// vì không khôi phục được. Phiếu đã huỷ: chip Đã huỷ, StatusPath kết thúc đỏ, hết nút duyệt và huỷ (Chủ còn mục "Xoá phiếu hàng hoàn" trong menu "…" khi BE cho `delete`). Không có tiền hay giá vốn. Ghi chú là chữ tự do: chỉ hiện trong trang.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, kg } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { canView, homePath } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { Icon } from "@/shared/ui/Icon";
import { PersonalText } from "@/shared/ui/PersonalText";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { RETURNS_MSG as M } from "../messages";
import { PATH_STEPS, canApprove, canCancel, canDelete, doneSteps, isOutsideLong, nextStepText, outsideText } from "../returnsModel";
import { cancelReturn, deleteReturn } from "../api";
import type { ApproveDecision, ReturnItem } from "../types";
import { useReturnOrderId } from "../useReturnOrderId";
import { useReturnDetail, useReturnId, type ReturnDetailState } from "../useReturnDetail";
import { useReturnTimeline } from "../useReturnTimeline";
import { ApproveReturnModal } from "./ApproveReturnModal";
import s from "../returns.module.css";

export function DetailSkeleton() {
  return (
    <div className={s.detailSkel} role="status" aria-busy="true">
      <span className="sr-only">{M.loadingDetail}</span>
      <div aria-hidden="true">
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-s" />
      </div>
    </div>
  );
}

type Props = {
  /** Trang ghép khối Trợ lý AI vào đây (feature không import features/ai). `onApplied` = tải lại phiếu sau khi AI áp dụng đề xuất. */
  renderAi?: (id: number, onApplied: () => void) => ReactNode;
};

export function ReturnDetailScreen({ renderAi }: Props) {
  const { me } = useAuth();
  const id = useReturnId();
  const detail = useReturnDetail(id);
  const home = me ? homePath(me) : undefined;

  if (id === undefined) return <DetailSkeleton />;
  if (id === null) return <NotFoundScreen homeHref={home} />;
  if (detail.status === "forbidden") return <NoPermission homeHref={home} />;
  if (detail.status === "notfound") return <NotFoundScreen homeHref={home} />;
  if (detail.status === "error") return <ErrorScreen homeHref={home} onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) return <DetailSkeleton />;
  return <ReturnDetailBody item={detail.data} detail={detail} renderAi={renderAi} />;
}

function ReturnDetailBody({ item: r, detail, renderAi }: { item: ReturnItem; detail: ReturnDetailState; renderAi?: Props["renderAi"] }) {
  const { me } = useAuth();
  const toast = useToast();
  const router = useRouter();
  const [modal, setModal] = useState<{ decision: ApproveDecision } | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteGone, setDeleteGone] = useState(false);
  const [version, setVersion] = useState(0);
  const timeline = useReturnTimeline(r.id, version);

  const mayApprove = canApprove(me?.permissions, r);
  // Liên kết tới đối tượng liên quan (board W5f, UI-RULES §Chi tiết mục 4): chỉ khi người xem có quyền mở màn đó.
  // Lô chưa có liên kết: màn Kho & lô (Lô 7) chưa vào main, ghi nợ ở 03-dev-notes.
  const canOpenNote = canView(me, "deliveries") || canView(me, "my-deliveries");
  const canOpenOrder = canView(me, "orders");
  const orderId = useReturnOrderId(r.delivery_note, r.order_code, canOpenOrder);

  const refresh = () => {
    setVersion((n) => n + 1);
    void detail.reload();
  };

  const more: MoreMenuItem[] = [];
  if (canCancel(me, r)) more.push({ key: "cancel", label: M.cancelMenu, danger: true, onSelect: () => setCancelling(true) });
  if (canDelete(r)) more.push({ key: "delete", label: M.deleteMenu, danger: true, onSelect: () => { setDeleteGone(false); setDeleting(true); } });

  const primary = mayApprove ? (
    <>
      <button type="button" className="btn primary" onClick={() => setModal({ decision: "RESTOCK" })}>
        {M.restock}
      </button>
      <button type="button" className="btn" onClick={() => setModal({ decision: "WRITE_OFF" })}>
        {M.writeOff}
      </button>
    </>
  ) : null;

  return (
    <DetailPage
      id="return-detail"
      header={
        <DetailHeader
          back={{ href: "/returns/", label: M.backToList }}
          title={r.code}
          mono
          status={<Chip table={ENUMS.returnToStockStatus} value={r.status} />}
          primary={primary}
          more={more}
        />
      }
      banner={
        detail.error != null && !detail.reloading ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(detail.error)}</span>
            <button type="button" className="btn" onClick={() => void detail.reload()}>
              {M.retry}
            </button>
          </div>
        ) : undefined
      }
      aiSlot={renderAi?.(r.id, refresh)}
      timeline={
        <>
          {timeline.status === "error" && (
            <p className={s.railNote} role="alert">
              <span>{M.timelineFailed}</span>
              <button type="button" className="btn" onClick={timeline.retry}>
                {M.retry}
              </button>
            </p>
          )}
          {timeline.status === "loading" && (
            <section role="status" aria-label={M.timelineTitle}>
              <span className="sr-only">Đang tải lịch sử…</span>
              <div className={s.skelRow} />
            </section>
          )}
          {timeline.status === "ok" && <Timeline entries={timeline.entries} truncated={timeline.truncated} title={M.timelineTitle} />}
        </>
      }
    >
      {r.status === "CANCELLED" ? (
        <StatusPath steps={PATH_STEPS.slice(0, 1)} current="DRAFT" badEnd={{ label: ENUMS.returnToStockStatus.CANCELLED.label, after: "DRAFT" }} next={null} done={doneSteps(r)} />
      ) : (
        <StatusPath steps={PATH_STEPS} current={r.status} next={nextStepText(r)} done={doneSteps(r)} />
      )}

      <InfoGrid title={M.sectionInfo}>
        <InfoField
          label={M.fieldDeliveryNote}
          value={
            canOpenNote && r.delivery_note_code ? (
              <Link href={`/deliveries/detail/?id=${r.delivery_note}`} className="inline-link" prefetch={false}>
                {r.delivery_note_code}
              </Link>
            ) : (
              r.delivery_note_code
            )
          }
          mono
        />
        <InfoField
          label={M.fieldOrder}
          value={
            orderId !== null && r.order_code ? (
              <Link href={`/orders/detail/?id=${orderId}`} className="inline-link" prefetch={false}>
                {r.order_code}
              </Link>
            ) : (
              r.order_code
            )
          }
          mono
        />
        <InfoField label={M.fieldBatch} value={r.batch_code} mono />
        <InfoField label={M.fieldItem} value={r.item_name} />
        <InfoField label={M.fieldQty} value={kg(r.qty)} num />
        <InfoField label={M.fieldLeftAt} value={r.left_warehouse_at ? dateTime(r.left_warehouse_at) : null} num />
        <InfoField label={M.fieldReturnedAt} value={r.returned_at ? dateTime(r.returned_at) : null} num />
        <InfoField
          label={M.fieldOutside}
          value={
            isOutsideLong(r.outside_minutes) ? (
              <span className="warn-text">
                {outsideText(r.outside_minutes)}
                <span className="sr-only"> ({M.outsideLong})</span>
              </span>
            ) : (
              outsideText(r.outside_minutes)
            )
          }
          num
        />
        <InfoField label={M.fieldCreatedBy} value={r.created_by_name} />
        {r.status === "APPROVED" && <InfoField label={M.fieldApprovedBy} value={r.approved_by_name} />}
        {r.status === "APPROVED" && <InfoField label={M.fieldDecision} value={<Chip table={ENUMS.returnToStockDecision} value={r.decision} />} />}
        <InfoField label={M.fieldNote} value={<PersonalText value={r.note} whenEmpty="" />} />
      </InfoGrid>

      {cancelling && (
        <ConfirmModal
          title={M.cancelTitle}
          confirmLabel={M.cancelConfirm}
          danger
          noun="phiếu"
          run={() => cancelReturn(r.id)}
          onDone={() => {
            setCancelling(false);
            toast.success(M.cancelled);
            refresh();
          }}
          onClose={() => setCancelling(false)}
          onReload={() => {
            setCancelling(false);
            refresh();
          }}
        >
          <p>{M.cancelBody(r.code)}</p>
        </ConfirmModal>
      )}
      {deleting && deleteGone && (
        <ConfirmModal
          title={M.deleteTitle}
          confirmLabel={M.deleteGoneConfirm}
          noun="phiếu"
          run={async () => undefined}
          onDone={() => router.push("/returns/")}
          onClose={() => router.push("/returns/")}
          backLabel="Đóng"
        >
          <p className="alert-box err" role="alert" data-testid="delete-gone">
            {M.deleteGone}
          </p>
        </ConfirmModal>
      )}
      {deleting && !deleteGone && (
        <ConfirmModal
          title={M.deleteTitle}
          confirmLabel={M.deleteConfirm}
          danger
          noun="phiếu"
          run={async () => {
            try {
              return await deleteReturn(r.id);
            } catch (e) {
              if (e instanceof ApiError && e.status === 404) setDeleteGone(true);
              throw e;
            }
          }}
          onDone={() => {
            toast.success(M.deleted);
            router.push("/returns/");
          }}
          onClose={() => setDeleting(false)}
          onReload={() => {
            setDeleting(false);
            refresh();
          }}
        >
          <p>{M.deleteBody(r.code)}</p>
          {r.status === "DRAFT" && <p data-testid="delete-draft-note">{M.deleteDraftNote}</p>}
        </ConfirmModal>
      )}
      {modal && (
        <ApproveReturnModal
          item={r}
          initialDecision={modal.decision}
          onClose={() => setModal(null)}
          onApproved={(res) => {
            setModal(null);
            toast.success(res.decision === "WRITE_OFF" ? M.approvedWriteOff : M.approvedRestock);
            refresh();
          }}
          onReload={() => {
            setModal(null);
            refresh();
          }}
        />
      )}
    </DetailPage>
  );
}
