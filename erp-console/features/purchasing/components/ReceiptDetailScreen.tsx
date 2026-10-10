"use client";

// Chi tiết phiếu nhập (W2b, ED-20) tại /purchasing/detail/?id=<id>.
// Cột trái: thanh trạng thái · Thông tin phiếu · Dòng nhập · Hoá đơn mua (theo quyền) · Chi phí phụ (chỉ Chủ).
// Cột phải: khối Trợ lý AI (targetModel purchasing.purchasereceipt, page ghép) · Dòng thời gian (guidance, chỉ có timeline).
// Thao tác: nút chính theo trạng thái (Nháp: Ghi nhận phiếu; đã ghi nhận chưa hoá đơn: Thêm hoá đơn, chỉ Chủ); menu "…": Huỷ phiếu,
// Nhập chi phí, Sao chép mã phiếu, Xem nhật ký. Mục bị chặn hiện mờ kèm lý do ngắn.
// Giá mua, thành tiền, giá vốn, chi phí phụ: chỉ người có quyền xem (khoá); người khác không có các ô này trong DOM.
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import type { Me } from "@/features/auth/types";
import { ScopeLostInApp } from "@/features/auth/components/AppStates";
import { PurchaseInvoiceForm } from "@/features/accounting/components/PurchaseInvoiceForm";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import type { GuidanceData } from "@/features/guidance/types";
import { ApiError } from "@/shared/lib/http";
import { MSG } from "@/shared/lib/messages";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, kg, vnd } from "@/shared/lib/format";
import { PERM } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { useToast } from "@/shared/ui/overlay/Toast";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { useOfflineRegistration } from "@/shared/ui/states/offlineSource";
import { fetchReceipt, fetchReceiptGuidance } from "../api";
import { isOwnReceiptFromEarlierDay } from "../receiptScope";
import { RECEIPT_STEPS, cancelBlockReason, canCancelReceipt, idFromSearch, nextReceiptStep, receiptAbility, receiptDoneLabels, receiptPathOf } from "../receiptView";
import type { ReceiptDetail } from "../types";
import { CancelReceiptModal, SubmitReceiptModal } from "./ReceiptActionModals";
import { ReceiptCostsSection, ReceiptInvoicesSection, ReceiptLinesSection } from "./ReceiptSections";
import s from "../purchasing.module.css";

type Load = { k: "loading" } | { k: "ready"; row: ReceiptDetail; asOf: string } | { k: "error" } | { k: "notfound" } | { k: "forbidden" } | { k: "scope_lost"; ownEarlierDay: boolean };
type ModalKind = "submit" | "cancel" | "invoice" | null;

/** Mục tiêu cho khối Trợ lý AI: page ghép khối này (feature màn hình không import features/ai, 02b §2.3). */
export type ReceiptAiTarget = { id: number; code: string };
type RenderAi = (target: ReceiptAiTarget, onApplied: () => void) => React.ReactNode;

export function ReceiptDetailScreen({ renderAi }: { renderAi?: RenderAi }) {
  const params = useSearchParams();
  const id = idFromSearch(params.get("id"));
  const { me } = useAuth();
  if (!me) return null;
  // `?id=` rác (chữ, âm, 0, quá dài): không gọi API, hiện "Không tìm thấy".
  if (id === null) return <NotFoundScreen homeHref="/purchasing/" />;
  return <Loaded key={id} id={id} me={me} renderAi={renderAi} />;
}

function Loaded({ id, me, renderAi }: { id: number; me: Me; renderAi?: RenderAi }) {
  const toast = useToast();
  const router = useRouter();
  const ability = receiptAbility(me);
  const [load, setLoad] = useState<Load>({ k: "loading" });
  const [version, setVersion] = useState(0);
  const [guidance, setGuidance] = useState<GuidanceData | null>(null);
  const [guidanceError, setGuidanceError] = useState(false);
  const [modal, setModal] = useState<ModalKind>(null);
  const [aiApplied, setAiApplied] = useState(0);
  const seq = useRef(0);

  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    const ac = new AbortController();
    const mine = ++seq.current;
    const live = () => mine === seq.current && !ac.signal.aborted;

    fetchReceipt(id, ac.signal)
      .then((row) => live() && setLoad({ k: "ready", row, asOf: new Date().toISOString() }))
      .catch((err: unknown) => {
        if (!live()) return;
        if (err instanceof ApiError && err.status === 404) {
          // PV-13: đã có dữ liệu phiếu mà tải lại 404 → mất quyền; xoá dữ liệu cũ, chỉ giữ cờ AC2 (tính từ bản trước khi xoá).
          // Tải lần đầu 404 vẫn là "Không tìm thấy" (ED-19-AC6).
          setLoad((cur) =>
            cur.k === "ready"
              ? { k: "scope_lost", ownEarlierDay: isOwnReceiptFromEarlierDay(cur.row, me.id) }
              : cur.k === "scope_lost"
                ? cur
                : { k: "notfound" },
          );
          setGuidance(null);
        }
        else if (err instanceof ApiError && err.status === 403) setLoad({ k: "forbidden" });
        else setLoad((cur) => (cur.k === "ready" ? cur : { k: "error" })); // đã có số liệu thì giữ, dải mất mạng lo phần còn lại
      });

    fetchReceiptGuidance(id, ac.signal)
      .then((g) => {
        if (!live()) return;
        setGuidance(g);
        setGuidanceError(false);
      })
      .catch(() => live() && setGuidanceError(true));
    return () => ac.abort();
  }, [id, version, me.id]);

  useOfflineRegistration(load.k === "ready" ? { asOf: load.asOf, onRetry: reload } : null);

  if (load.k === "loading") {
    return (
      <SkeletonScreen label="Đang tải phiếu nhập…">
        <SkeletonTable rows={6} cols={3} />
      </SkeletonScreen>
    );
  }
  if (load.k === "scope_lost") return <ScopeLostInApp listHref="/purchasing/" extra={load.ownEarlierDay ? MSG.scopeLostOwnReceiptEarlierDay : null} />;
  if (load.k === "notfound") return <NotFoundScreen homeHref="/purchasing/" />;
  if (load.k === "forbidden") return <NoPermission homeHref="/purchasing/" />;
  if (load.k === "error") return <ErrorScreen onRetry={reload} homeHref="/purchasing/" />;

  const row = load.row;
  const submitted = row.status === "SUBMITTED";
  const showCost = ability.viewCost && row.purchase_amount !== undefined;
  const hasInvoice = row.invoice !== null;

  const more: MoreMenuItem[] = [];
  if (ability.addCost && submitted) {
    more.push({ key: "cost", label: "Nhập chi phí phụ", onSelect: () => router.push(`/purchasing/costs/new/?receipt=${row.id}`) });
  }
  if (canCancelReceipt(me, row)) {
    more.push({ key: "cancel", label: "Huỷ phiếu", danger: true, blockedReason: cancelBlockReason(row), onSelect: () => setModal("cancel") });
  }
  more.push({
    key: "copy",
    label: "Sao chép mã phiếu",
    onSelect: () => {
      void navigator.clipboard?.writeText(row.code).then(
        () => toast.success(`Đã sao chép mã phiếu ${row.code}.`),
        () => toast.error("Không sao chép được mã phiếu."),
      );
    },
  });
  more.push({
    key: "log",
    label: "Xem nhật ký của phiếu",
    onSelect: () => {
      const el = document.getElementById("receipt-timeline");
      el?.scrollIntoView({ block: "start" });
      el?.focus();
    },
  });

  let primary: React.ReactNode = undefined;
  if (row.status === "DRAFT" && ability.submit) {
    primary = (
      <button type="button" className="btn primary" onClick={() => setModal("submit")} data-testid="submit-receipt">
        Ghi nhận phiếu
      </button>
    );
  } else if (submitted && !hasInvoice && ability.addInvoice) {
    primary = (
      <button type="button" className="btn primary" onClick={() => setModal("invoice")} data-testid="add-invoice">
        Thêm hoá đơn
      </button>
    );
  }

  const path = receiptPathOf(row.status);
  const done = (message: string) => {
    setModal(null);
    toast.success(message);
    reload();
  };

  const invoiceAction =
    ability.addInvoice && submitted && !hasInvoice ? (
      <button type="button" className="btn" onClick={() => setModal("invoice")}>
        Thêm hoá đơn
      </button>
    ) : undefined;
  const costAction =
    ability.addCost && submitted ? (
      <button type="button" className="btn" onClick={() => router.push(`/purchasing/costs/new/?receipt=${row.id}`)} data-testid="add-cost">
        Nhập chi phí
      </button>
    ) : undefined;

  return (
    <DetailPage
      id="receipt-detail"
      header={
        <DetailHeader
          back={{ href: "/purchasing/", label: "Mua hàng" }}
          title={row.code}
          mono
          status={<Chip table={ENUMS.purchaseReceiptStatus} value={row.status} />}
          primary={primary}
          more={more}
        />
      }
      aiSlot={renderAi ? <Fragment key={aiApplied}>{renderAi({ id: row.id, code: row.code }, () => { setAiApplied((n) => n + 1); reload(); })}</Fragment> : null}
      timeline={
        <div id="receipt-timeline" tabIndex={-1}>
          {guidanceError && !guidance ? (
            <p className={s.hint} role="status">
              Chưa tải được dòng thời gian.{" "}
              <button type="button" className="btn" onClick={reload}>
                Thử lại
              </button>
            </p>
          ) : (
            <Timeline entries={toTimelineEntries(guidance?.timeline)} truncated={guidance?.timeline_truncated} />
          )}
        </div>
      }
    >
      <StatusPath
        steps={RECEIPT_STEPS}
        current={path.current}
        badEnd={path.badEnd}
        next={nextReceiptStep(row, ability)}
        done={receiptDoneLabels(row)}
        label="Vòng đời của phiếu nhập"
      />
      <InfoGrid title="Thông tin phiếu">
        <InfoField label="Phiếu nhập" value={row.code} mono />
        <InfoField label="Nhà cung cấp" value={row.supplier_name} />
        <InfoField label="Kho nhận" value={row.warehouse_name} />
        <InfoField label="Ngày nhập" value={dateOnly(row.received_date)} num />
        <InfoField label="Tổng số kg" value={kg(row.total_qty)} num />
        <InfoField label="Người lập" value={row.created_by_name} />
        {showCost && <InfoField label="Tiền mua" kind="locked" value={vnd(row.purchase_amount)} reason="Giá vốn chỉ Chủ được xem" num />}
        {row.note ? <InfoField label="Ghi chú" value={row.note} /> : null}
      </InfoGrid>
      <ReceiptLinesSection lines={row.lines} canViewCost={ability.viewCost} canOpenBatch={me.permissions.includes(PERM.viewBatch)} />
      {ability.viewInvoices && row.invoices !== undefined && <ReceiptInvoicesSection invoices={row.invoices} action={invoiceAction} />}
      {ability.viewCosts && row.costs !== undefined && <ReceiptCostsSection costs={row.costs} allocatedTotal={row.allocated_amount} action={costAction} />}

      {modal === "submit" && <SubmitReceiptModal row={row} onClose={() => setModal(null)} onDone={done} onReload={() => { setModal(null); reload(); }} />}
      {modal === "cancel" && <CancelReceiptModal row={row} onClose={() => setModal(null)} onDone={done} onReload={() => { setModal(null); reload(); }} />}
      {modal === "invoice" && (
        <PurchaseInvoiceForm
          receipt={{
            id: row.id,
            code: row.code,
            supplier: row.supplier,
            supplierName: row.supplier_name,
            purchaseAmount: row.purchase_amount !== undefined ? Number(row.purchase_amount) : null,
          }}
          onClose={() => setModal(null)}
          onDone={(inv) => done(`Đã thêm hoá đơn ${inv.code} cho phiếu ${row.code}.`)}
        />
      )}
    </DetailPage>
  );
}
