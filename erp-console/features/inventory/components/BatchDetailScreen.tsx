"use client";

// Chi tiết lô (W5b, ED-23) tại /inventory/detail/?id=<id>. Thay tấm bên BatchDetailSheet cũ.
// Cột trái: thanh trạng thái · Thông tin lô · Số lượng & giá vốn · Nhập xuất của lô · Đơn lấy hàng từ lô.
// Cột phải: khối Trợ lý AI (targetModel inventory.batch) · Dòng thời gian (guidance).
// Thao tác: Mở bán lô (nút chính khi lô Nháp); menu "…": Trả nhà cung cấp, Huỷ phần tồn ghi lỗ (chỉ Chủ, chỉ lô Quá hạn còn tồn),
// Chốt lô (cần tồn = 0), Sao chép mã lô, Xem nhật ký của lô. Mục bị chặn hiện mờ kèm lý do ngắn.
// Giá mua, chi phí phụ, giá vốn, lãi lỗ: chỉ người có quyền xem (khoá); người khác không có các ô này trong DOM.
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import type { Me } from "@/features/auth/types";
import { nextStepLabel, toTimelineEntries } from "@/features/guidance/detailAdapters";
import { getGuidance } from "@/features/guidance/api";
import { EscalateModal } from "@/features/guidance/components/EscalateModal";
import { ESCALATE_MSG, escalatableStep } from "@/features/guidance/escalation";
import type { GuidanceData } from "@/features/guidance/types";
import { fetchLedger } from "@/features/ledger/api";
import type { LedgerEntry } from "@/features/ledger/types";
import { referenceHref } from "@/features/ledger/referenceRoutes";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, kg, vnd } from "@/shared/lib/format";
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
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { useOfflineRegistration } from "@/shared/ui/states/offlineSource";
import type { SubmitConflict } from "@/shared/ui/form/useSubmit";
import { fetchBatch, fetchOrdersByBatch } from "../api";
import {
  BATCH_STEPS,
  batchAbility,
  closeBlockReason,
  doneLabels,
  expiredBlockReason,
  idFromSearch,
  pathOf,
  qtyAvailable,
  qtyReserved,
  stepLacksPermission,
  stepReason,
} from "../lotView";
import type { BatchApiRow, OrderUsingBatch } from "../types";
import { BatchLedgerSection, BatchOrdersSection, type Remote } from "./BatchSections";
import { CancelExpiredModal } from "./CancelExpiredModal";
import { CloseBatchModal } from "./CloseBatchModal";
import { PublishBatchModal } from "./PublishBatchModal";
import { ReturnToSupplierModal } from "./ReturnToSupplierModal";
import s from "../inventory.module.css";

type Load = { k: "loading" } | { k: "ready"; row: BatchApiRow; asOf: string } | { k: "error" } | { k: "notfound" } | { k: "forbidden" };
type ModalKind = "publish" | "return" | "cancel" | "close" | "escalate" | null;

const IDLE = { data: null, error: null, loading: true } as const;

// Mục tiêu cho khối Trợ lý AI: page ghép khối này (feature màn hình không import features/ai, 02b §2.3).
export type BatchAiTarget = { id: number; code: string };

type RenderAi = (target: BatchAiTarget, onApplied: () => void) => React.ReactNode;

export function BatchDetailScreen({ renderAi }: { renderAi?: RenderAi }) {
  const params = useSearchParams();
  const id = idFromSearch(params.get("id"));
  const { me } = useAuth();
  if (!me) return null;
  // `?id=` rác (chữ, âm, 0, quá dài): không gọi API, hiện "Không tìm thấy".
  if (id === null) return <NotFoundScreen homeHref="/inventory/" />;
  return <Loaded key={id} id={id} me={me} renderAi={renderAi} />;
}

function Loaded({ id, me, renderAi }: { id: number; me: Me; renderAi?: RenderAi }) {
  const toast = useToast();
  const ability = batchAbility(me);
  const [load, setLoad] = useState<Load>({ k: "loading" });
  const [version, setVersion] = useState(0);
  const [guidance, setGuidance] = useState<GuidanceData | null>(null);
  const [guidanceError, setGuidanceError] = useState(false);
  const [ledger, setLedger] = useState<Remote<{ rows: LedgerEntry[]; count: number }>>(IDLE);
  const [orders, setOrders] = useState<Remote<{ rows: OrderUsingBatch[]; count: number }>>(IDLE);
  const [modal, setModal] = useState<ModalKind>(null);
  // Bước đã nhờ xong trong phiên trang này: ẩn mục menu để khỏi nhờ lặp (BE không chống trùng).
  const [escalatedKey, setEscalatedKey] = useState<string | null>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [aiApplied, setAiApplied] = useState(0);
  const seq = useRef(0);

  const reload = useCallback(() => setVersion((v) => v + 1), []);

  // Lô (bắt buộc) + ba phần phụ tải song song; phần phụ lỗi không làm hỏng trang.
  useEffect(() => {
    const ac = new AbortController();
    const mine = ++seq.current;
    const live = () => mine === seq.current && !ac.signal.aborted;

    fetchBatch(id, ac.signal)
      .then((row) => live() && setLoad({ k: "ready", row, asOf: new Date().toISOString() }))
      .catch((err: unknown) => {
        if (!live()) return;
        if (err instanceof ApiError && err.status === 404) setLoad({ k: "notfound" });
        else if (err instanceof ApiError && err.status === 403) setLoad({ k: "forbidden" });
        else setLoad((cur) => (cur.k === "ready" ? cur : { k: "error" })); // đã có số liệu thì giữ, dải mất mạng lo phần còn lại
      });

    getGuidance("batch", id, ac.signal)
      .then((g) => {
        if (!live()) return;
        setGuidance(g);
        setGuidanceError(false);
      })
      .catch(() => live() && setGuidanceError(true));

    if (ability.viewLedger) {
      setLedger((cur) => ({ ...cur, loading: true, error: null }));
      fetchLedger({ batch: String(id) }, 1, ac.signal)
        .then((r) => live() && setLedger({ data: { rows: r.results, count: r.count }, error: null, loading: false }))
        .catch((err: unknown) => live() && setLedger((cur) => ({ ...cur, error: loadErrorText(err), loading: false })));
    }
    if (ability.viewOrders) {
      setOrders((cur) => ({ ...cur, loading: true, error: null }));
      fetchOrdersByBatch(id, ac.signal)
        .then((r) => live() && setOrders({ data: { rows: r.results, count: r.count }, error: null, loading: false }))
        .catch((err: unknown) => live() && setOrders((cur) => ({ ...cur, error: loadErrorText(err), loading: false })));
    }
    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, version, ability.viewLedger, ability.viewOrders]);

  useOfflineRegistration(load.k === "ready" ? { asOf: load.asOf, onRetry: reload } : null);

  if (load.k === "loading") {
    return (
      <SkeletonScreen label="Đang tải lô…">
        <SkeletonTable rows={6} cols={3} />
      </SkeletonScreen>
    );
  }
  if (load.k === "notfound") return <NotFoundScreen homeHref="/inventory/" />;
  if (load.k === "forbidden") return <NoPermission homeHref="/inventory/" />;
  if (load.k === "error") return <ErrorScreen onRetry={reload} homeHref="/inventory/" />;

  const row = load.row;
  const closeStep = guidance?.next_steps.find((st) => st.key === "close");
  const returnStep = guidance?.next_steps.find((st) => st.key === "return_to_supplier");
  const cancelStep = guidance?.next_steps.find((st) => st.key === "cancel_expired");

  const more: MoreMenuItem[] = [];
  if (ability.returnToSupplier && !stepLacksPermission(returnStep)) {
    more.push({ key: "return", label: "Trả nhà cung cấp", blockedReason: expiredBlockReason(row), onSelect: () => setModal("return") });
  }
  if (ability.cancelExpired && !stepLacksPermission(cancelStep)) {
    more.push({ key: "cancel", label: "Huỷ phần tồn, ghi lỗ", danger: true, blockedReason: expiredBlockReason(row), onSelect: () => setModal("cancel") });
  }
  if (ability.close && !stepLacksPermission(closeStep)) {
    more.push({ key: "close", label: "Chốt lô", blockedReason: closeBlockReason(row, stepReason(closeStep)), onSelect: () => setModal("close") });
  }
  const stuckStep = escalatableStep(guidance);
  if (stuckStep && stuckStep.key !== escalatedKey) {
    more.push({ key: "escalate", label: ESCALATE_MSG.menuLabel, onSelect: () => setModal("escalate") });
  }
  more.push({
    key: "copy",
    label: "Sao chép mã lô",
    onSelect: () => {
      void navigator.clipboard?.writeText(row.batch_id).then(
        () => toast.success(`Đã sao chép mã lô ${row.batch_id}.`),
        () => toast.error("Không sao chép được mã lô."),
      );
    },
  });
  more.push({
    key: "log",
    label: "Xem nhật ký của lô",
    onSelect: () => {
      const el = document.getElementById("batch-timeline");
      el?.scrollIntoView({ block: "start" });
      el?.focus();
    },
  });

  const primary =
    row.status === "DRAFT" && ability.publish ? (
      <button type="button" className="btn primary" onClick={() => setModal("publish")}>
        Mở bán lô
      </button>
    ) : undefined;

  const path = pathOf(row.status);
  const receiptHref = row.receipt ? referenceHref({ kind: "receipt", id: row.receipt.id }) : null;
  const purchase = row.purchase_rate !== undefined ? Number(row.purchase_rate) : null;
  const landed = row.landed_unit_cost !== undefined ? Number(row.landed_unit_cost) : null;
  const showCost = ability.viewCost && purchase !== null && landed !== null;

  const doneModal = (message: string) => {
    setModal(null);
    setConflict(null);
    toast.success(message);
    reload();
  };
  const common = {
    row,
    onClose: () => setModal(null),
    onDone: doneModal,
    onReload: () => {
      setModal(null);
      reload();
    },
    onConflict: (c: SubmitConflict) => {
      setModal(null);
      setConflict(c);
    },
  };

  return (
    <DetailPage
      id="batch-detail"
      header={
        <DetailHeader
          back={{ href: "/inventory/", label: "Kho & lô" }}
          title={row.batch_id}
          mono
          status={<Chip table={ENUMS.batchStatus} value={row.status} />}
          primary={primary}
          more={more}
        />
      }
      banner={
        conflict ? (
          <ConflictBanner
            noun="lô"
            updatedByName={conflict.updatedByName}
            updatedAt={conflict.updatedAt}
            onReload={() => {
              setConflict(null);
              reload();
            }}
          />
        ) : null
      }
      aiSlot={renderAi ? <Fragment key={aiApplied}>{renderAi({ id: row.id, code: row.batch_id }, () => { setAiApplied((n) => n + 1); reload(); })}</Fragment> : null}
      timeline={
        <div id="batch-timeline" tabIndex={-1}>
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
        steps={BATCH_STEPS}
        current={path.current}
        badEnd={path.badEnd}
        next={nextStepLabel(guidance)}
        done={doneLabels(guidance?.timeline ?? [])}
        label="Vòng đời của lô"
      />
      <InfoGrid title="Thông tin lô">
        <InfoField label="Lô" value={row.batch_id} mono />
        <InfoField label="Mặt hàng" value={row.item_name} />
        <InfoField label="Nhà cung cấp" value={row.supplier_name} />
        <InfoField
          label="Phiếu nhập"
          mono
          value={
            row.receipt ? (
              receiptHref ? (
                <Link href={receiptHref} className={s.codeLink}>
                  {row.receipt.code}
                </Link>
              ) : (
                row.receipt.code
              )
            ) : null
          }
        />
        <InfoField label="Kho" value={row.warehouse_name} />
        <InfoField label="Ngày nhập" value={dateOnly(row.received_date)} num />
        <InfoField label="Hạn dùng" value={dateOnly(row.expiry_date)} num />
      </InfoGrid>
      <InfoGrid title="Số lượng & giá vốn">
        <InfoField label="Nhập ban đầu" value={kg(row.qty_received)} num />
        <InfoField label="Tồn khả dụng" value={<span data-testid="qty-available">{kg(qtyAvailable(row))}</span>} num />
        <InfoField label="Lượng giữ chỗ" value={kg(qtyReserved(row))} num />
        {showCost && (
          <>
            <InfoField label="Giá mua/kg" kind="locked" value={vnd(purchase)} reason="Giá vốn chỉ Chủ được xem" num />
            <InfoField label="Chi phí phụ/kg" kind="locked" value={vnd(Math.max(0, (landed ?? 0) - (purchase ?? 0)))} reason="Giá vốn chỉ Chủ được xem" num />
            <InfoField label="Giá vốn/kg" kind="locked" value={vnd(landed)} reason="Giá vốn chỉ Chủ được xem" num />
          </>
        )}
      </InfoGrid>
      {ability.viewLedger && <BatchLedgerSection batchId={row.id} state={ledger} onRetry={reload} />}
      {ability.viewOrders && <BatchOrdersSection state={orders} onRetry={reload} />}

      {modal === "publish" && <PublishBatchModal {...common} />}
      {modal === "return" && <ReturnToSupplierModal {...common} />}
      {modal === "cancel" && <CancelExpiredModal {...common} viewCost={ability.viewCost} />}
      {modal === "close" && <CloseBatchModal {...common} viewProfit={ability.viewProfit} />}
      {modal === "escalate" && stuckStep && (
        <EscalateModal
          docType="batch"
          docId={row.id}
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
    </DetailPage>
  );
}
