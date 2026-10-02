"use client";

// Trang chi tiết nhà cung cấp (ED-22 / W5d): /suppliers/detail/?id=<pk>. Khung DetailPage: header (tên · chip Đang/Ngừng hợp tác · "Sửa" · "…"),
// cột trái: "Thông tin nhà cung cấp" (Tên, Số điện thoại, Ghi chú sửa tại chỗ; Loại sửa qua nút Sửa) · "Mua hàng" (chỉ đọc: số phiếu,
// tổng tiền mua CHỈ Chủ, lần nhập gần nhất) · bảng Phiếu nhập (R10) · bảng Lô đang bán (R5). Cột phải: khối Trợ lý AI (do page ghép qua `renderAi`,
// màn không import features/ai) rồi Dòng thời gian (guidance `supplier`).
// "Ngừng hợp tác" / "Bật lại hợp tác" nằm trong "…", có hỏi lại; BE không cho xoá nhà cung cấp nên FE không bao giờ gọi DELETE.
// Số điện thoại là dữ liệu đối tác, hiện đủ; không đưa vào URL, storage hay log. Mã phiếu nhập chỉ thành liên kết khi trang phiếu đã có (Lô 10).

import { Fragment, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { referenceHref } from "@/features/ledger/referenceRoutes";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, dateTime, kg, vnd } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { canView, homePath } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { updateSupplier } from "../api";
import { SUPPLIERS_MSG as M } from "../messages";
import { saveErrorMessage, validateField, type EditableTextField } from "../suppliersModel";
import type { Supplier, SupplierBatchRow, SupplierReceiptRow } from "../types";
import { useSupplierDetail, useSupplierId, type SupplierDetailState } from "../useSupplierDetail";
import { useSupplierBatches, useSupplierReceipts } from "../useSupplierRelated";
import { useSupplierTimeline } from "../useSupplierTimeline";
import { ConfirmActiveModal } from "./ConfirmActiveModal";
import { SupplierFormModal } from "./SupplierFormModal";
import s from "../suppliers.module.css";

const PERM_CHANGE_SUPPLIER = "purchasing.change_supplier";
const PERM_VIEW_RECEIPTS = "purchasing.view_purchasereceipt";
const PERM_VIEW_BATCHES = "inventory.view_batch";

/** Khối Trợ lý AI do page truyền vào (màn tính năng không import features/ai). */
export type SupplierAiTarget = { id: number };
type RenderAi = (target: SupplierAiTarget, onApplied: () => void) => React.ReactNode;

export function DetailSkeleton() {
  return (
    <div className={s.detailSkel} role="status" aria-busy="true">
      <span className="sr-only">{`Đang tải ${M.detailNoun}…`}</span>
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

export function SupplierDetailScreen({ renderAi }: { renderAi?: RenderAi }) {
  const { me } = useAuth();
  const id = useSupplierId();
  const detail = useSupplierDetail(id);
  const home = me ? homePath(me) : undefined;

  if (id === undefined) return <DetailSkeleton />;
  if (id === null) return <NotFoundScreen homeHref={home} />;
  if (detail.status === "forbidden") return <NoPermission homeHref={home} />;
  if (detail.status === "notfound") return <NotFoundScreen homeHref={home} />;
  if (detail.status === "error") return <ErrorScreen homeHref={home} onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) return <DetailSkeleton />;
  return <SupplierDetailBody key={id} supplier={detail.data} detail={detail} renderAi={renderAi} />;
}

function SupplierDetailBody({ supplier: c, detail, renderAi }: { supplier: Supplier; detail: SupplierDetailState; renderAi?: RenderAi }) {
  const { me } = useAuth();
  const toast = useToast();
  const [modal, setModal] = useState<"edit" | "active" | null>(null);
  const [version, setVersion] = useState(0);
  const [aiApplied, setAiApplied] = useState(0);
  const timeline = useSupplierTimeline(c.id, version);

  const canEdit = !!me?.permissions.includes(PERM_CHANGE_SUPPLIER);
  const canViewCost = !!me?.can_view_cost;
  const canSeeReceipts = !!me?.permissions.includes(PERM_VIEW_RECEIPTS);
  const canSeeBatches = !!me?.permissions.includes(PERM_VIEW_BATCHES);
  const canOpenBatch = canView(me, "inventory");
  const receipts = useSupplierReceipts(c.id, canSeeReceipts);
  const batches = useSupplierBatches(c.id, canSeeBatches, version + aiApplied);

  const afterChange = (message: string) => {
    toast.success(message);
    setVersion((n) => n + 1);
    void detail.reload();
  };

  /** Lưu MỘT trường tại chỗ: chỉ gửi khi giá trị đổi; lỗi ném lên cho ô hiện dưới ô, giữ nguyên giá trị đang gõ. */
  const saveField = (field: EditableTextField) => async (next: string) => {
    const value = next.trim();
    if (value === (c[field] ?? "")) return;
    try {
      await updateSupplier(c.id, { [field]: value });
    } catch (err) {
      throw new Error(saveErrorMessage(err));
    }
    afterChange(M.saved);
  };
  const validate = (field: EditableTextField) => (next: string) => validateField(field, next);

  const more: MoreMenuItem[] = [
    canEdit
      ? { key: "active", label: c.is_active ? M.deactivate : M.reactivate, danger: c.is_active, onSelect: () => setModal("active") }
      : { key: "active", label: c.is_active ? M.deactivate : M.reactivate, blockedReason: M.managerOnly },
    {
      key: "log",
      label: M.viewLog,
      onSelect: () => {
        const el = document.getElementById("supplier-timeline");
        el?.scrollIntoView({ block: "start" });
        el?.focus();
      },
    },
  ];

  const receiptCols: Column<SupplierReceiptRow>[] = useMemo(
    () => [
      { key: "code", header: M.colCode, mono: true, render: (r) => r.code },
      { key: "at", header: M.colReceivedAt, num: true, render: (r) => dateTime(r.created_at) },
      { key: "items", header: M.colItems, render: (r) => r.items_summary || <span className="muted">—</span> },
      { key: "qty", header: M.colQty, num: true, render: (r) => kg(r.total_qty) },
      { key: "amount", header: M.colAmount, num: true, locked: true, render: (r) => (r.purchase_amount === undefined ? <span className="muted">—</span> : vnd(r.purchase_amount)) },
      { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.purchaseReceiptStatus} value={r.status} /> },
    ],
    [],
  );
  const batchCols: Column<SupplierBatchRow>[] = useMemo(
    () => [
      { key: "batch", header: M.colBatch, mono: true, render: (b) => b.batch_id },
      { key: "item", header: M.colItem, render: (b) => b.item_name },
      { key: "stock", header: M.colStock, num: true, render: (b) => kg(b.qty_available) },
      { key: "expiry", header: M.colExpiry, num: true, render: (b) => dateOnly(b.expiry_date) },
      { key: "status", header: M.colStatus, render: (b) => <Chip table={ENUMS.batchStatus} value={b.status} /> },
    ],
    [],
  );

  const text = (field: EditableTextField, label: string, value: string, type?: "tel") =>
    canEdit ? (
      <InfoField kind="editable" label={label} value={value} type={type} onSave={saveField(field)} required={field === "name"} requiredMessage={field === "name" ? M.nameRequired : undefined} validate={validate(field)} />
    ) : (
      <InfoField label={label} value={value} />
    );

  return (
    <DetailPage
      id="supplier-detail"
      header={
        <DetailHeader
          back={{ href: "/suppliers/", label: M.backToList }}
          title={c.name || `#${c.id}`}
          status={<Chip table={ENUMS.supplierActive} value={c.is_active} />}
          primary={
            canEdit ? (
              <button type="button" className="btn primary" onClick={() => setModal("edit")}>
                {M.edit}
              </button>
            ) : null
          }
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
      aiSlot={renderAi ? <Fragment key={aiApplied}>{renderAi({ id: c.id }, () => { setAiApplied((n) => n + 1); void detail.reload(); })}</Fragment> : null}
      timeline={
        <div id="supplier-timeline" tabIndex={-1}>
          {timeline.status === "error" && (
            <p className={s.railNote} role="alert">
              <span>{M.timelineFailed}</span>
              <button type="button" className="btn" onClick={timeline.retry}>
                {M.retry}
              </button>
            </p>
          )}
          {timeline.status !== "error" && <Timeline entries={timeline.entries} truncated={timeline.truncated} title={M.timelineTitle} />}
        </div>
      }
    >
      <InfoGrid title={M.sectionInfo}>
        {text("name", M.fieldName, c.name ?? "")}
        <InfoField label={M.fieldType} value={c.supplier_type_label} />
        {text("phone", M.fieldPhone, c.phone ?? "", "tel")}
        {text("note", M.fieldNote, c.note ?? "")}
      </InfoGrid>

      <InfoGrid title={M.sectionPurchase}>
        <InfoField kind="locked" label={M.fieldReceipts} num reason={M.derivedReason} value={M.receiptsValue(c.receipt_count)} />
        {canViewCost && c.purchase_total !== undefined && <InfoField kind="locked" label={M.fieldTotal} num reason={M.costReason} value={vnd(c.purchase_total)} />}
        <InfoField kind="locked" label={M.fieldLast} num reason={M.derivedReason} value={c.last_received_at ? dateTime(c.last_received_at) : null} />
      </InfoGrid>

      {canSeeReceipts && !receipts.forbidden && (
        <section className={s.section} aria-label={M.receiptsTitle}>
          <h3 className={s.sectionH}>
            {M.receiptsTitle} {receipts.rows !== undefined && <span className={s.sectionCount}>{M.receiptsValue(receipts.count)}</span>}
          </h3>
          <DataTable
            caption={M.receiptsCaption}
            columns={receiptCols}
            rows={receipts.rows ?? null}
            rowKey={(r) => r.id}
            rowHref={(r) => referenceHref({ kind: "receipt", id: r.id }) ?? undefined}
            loading={receipts.loading && receipts.rows === undefined}
            error={receipts.rows === undefined && receipts.error != null ? `${M.receiptsFailed} ${loadErrorText(receipts.error)}` : null}
            onRetry={() => void receipts.reload()}
            noun={M.receiptsTitle.toLowerCase()}
            empty={{ icon: "receipt_long", title: M.receiptsEmpty, hint: M.receiptsEmptyHint }}
            canViewCost={canViewCost}
          />
          {(receipts.hasMore || receipts.moreError != null) && (
            <div className={s.sectionFoot}>
              {receipts.moreError != null && (
                <span className="field-err" role="alert">
                  {M.loadMoreFailed} {loadErrorText(receipts.moreError)}
                </span>
              )}
              {receipts.hasMore && (
                <button type="button" className="btn" onClick={() => void receipts.loadMore()} disabled={receipts.moreLoading} aria-busy={receipts.moreLoading || undefined}>
                  {receipts.moreLoading ? M.loadingMore : M.receiptsMore}
                </button>
              )}
            </div>
          )}
        </section>
      )}

      {canSeeBatches && !batches.forbidden && (
        <section className={s.section} aria-label={M.batchesTitle}>
          <h3 className={s.sectionH}>
            {M.batchesTitle} {batches.rows !== null && <span className={s.sectionCount}>{`${batches.count} lô`}</span>}
          </h3>
          <DataTable
            caption={M.batchesCaption}
            columns={batchCols}
            rows={batches.rows}
            rowKey={(b) => b.id}
            rowHref={canOpenBatch ? (b) => `/inventory/detail/?id=${b.id}` : undefined}
            loading={batches.loading && batches.rows === null}
            error={batches.rows === null && batches.error != null ? `${M.batchesFailed} ${loadErrorText(batches.error)}` : null}
            onRetry={batches.reload}
            noun="lô"
            empty={{ icon: "inventory_2", title: M.batchesEmpty, hint: M.batchesEmptyHint }}
            canViewCost={false}
          />
        </section>
      )}

      {modal === "edit" && (
        <SupplierFormModal
          supplier={c}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            afterChange(M.saved);
          }}
        />
      )}
      {modal === "active" && (
        <ConfirmActiveModal
          supplier={c}
          deactivating={c.is_active}
          onClose={() => setModal(null)}
          onDone={() => {
            setModal(null);
            afterChange(c.is_active ? M.deactivated : M.reactivated);
          }}
        />
      )}
    </DetailPage>
  );
}
