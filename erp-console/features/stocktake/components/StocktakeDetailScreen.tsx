"use client";

// ED-28 W2g — Chi tiết phiếu kiểm kê /stocktake/detail/?id=<số>. Khung DetailPage: header (mã mono · chip · nút theo trạng thái · …),
// StatusPath Nháp → Chờ duyệt → Đã duyệt, Thông tin, bảng dòng (tồn hệ thống · đếm được · chênh lệch · lý do); cột phải = Trợ lý AI + dòng thời gian.
// Nút theo `available_actions` của BE (Duy chốt 02/10, #6/#20): Nháp có [Sửa số đếm] [Gửi duyệt]; Chờ duyệt có [Duyệt và điều chỉnh tồn] [Trả về nháp].
// Không còn khối chặn người nhập số tự duyệt (BR-KK-02/08 đã bỏ). Mọi việc đổi trạng thái có hộp xác nhận; duyệt đổi tồn kho.
// RECON_NOT_SUBMITTED / RECON_NOT_DRAFT (phiếu đã đổi trạng thái ở nơi khác): hiện câu của BE rồi tải lại phiếu.
// Không có số tiền (chỉ kg). Không có dữ liệu khách. URL chỉ mang ?id=.
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, dateTime } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { homePath } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { SkeletonScreen } from "@/shared/ui/Skeleton";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { Section } from "@/shared/ui/detail/Section";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline, type TimelineEntry } from "@/shared/ui/detail/Timeline";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { Modal } from "@/shared/ui/overlay/Modal";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { approveStocktake, fetchStocktake, fetchStocktakeTimeline, returnStocktakeToDraft, submitStocktake } from "../api";
import {
  LIST_HREF,
  PATH_STEPS,
  changedLineCount,
  cleanMessage,
  diffTone,
  doneSteps,
  editHref,
  hasAction,
  idFromSearch,
  lineErrorOf,
  nextStepText,
  qtyText,
  signedQtyText,
  toMilli,
} from "../stocktakeUi";
import type { StocktakeDetail } from "../types";
import s from "../stocktake.module.css";

type Load = "loading" | "ready" | "error" | "notfound" | "forbidden";
type History = { state: "loading" } | { state: "error" } | { state: "ready"; entries: TimelineEntry[]; truncated: boolean };

const BACK = { href: LIST_HREF, label: "Kiểm kê" };

/** Câu lỗi của BE cho hộp Gửi duyệt / Trả về nháp: bỏ mã luật (UI-RULES §4.1). */
function cleanErrorText(err: unknown): string {
  return err instanceof ApiError ? cleanMessage(err.message) : "Không gửi được, thử lại sau.";
}

export function StocktakeDetailScreen() {
  const id = idFromSearch(useSearchParams().get("id"));
  const { me } = useAuth();
  const toast = useToast();

  const [load, setLoad] = useState<Load>("loading");
  const [detail, setDetail] = useState<StocktakeDetail | null>(null);
  const [history, setHistory] = useState<History>({ state: "loading" });
  const [confirming, setConfirming] = useState(false);
  const [step, setStep] = useState<"submit" | "return" | null>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [lineError, setLineError] = useState<{ index: number; message: string } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloading, setReloading] = useState(false);
  const seq = useRef(0);

  const loadHistory = useCallback(() => {
    if (id === null) return;
    fetchStocktakeTimeline(id)
      .then((g) => setHistory({ state: "ready", entries: toTimelineEntries(g.timeline), truncated: Boolean(g.timeline_truncated) }))
      .catch(() => setHistory({ state: "error" }));
  }, [id]);

  const loadDetail = useCallback(
    async (initial: boolean) => {
      if (id === null) return;
      const mine = ++seq.current;
      if (initial) setLoad("loading");
      else setReloading(true);
      try {
        const d = await fetchStocktake(id);
        if (mine !== seq.current) return;
        setDetail(d);
        setLoad("ready");
        setConflict(null);
        setLineError(null);
      } catch (err) {
        if (mine !== seq.current) return;
        if (err instanceof ApiError && err.status === 404) setLoad("notfound");
        else if (err instanceof ApiError && err.status === 403) setLoad("forbidden");
        else if (initial) setLoad("error");
        else setActionError("Chưa tải lại được phiếu. Kiểm tra mạng rồi bấm Tải lại.");
      } finally {
        if (mine === seq.current) setReloading(false);
      }
    },
    [id],
  );

  useEffect(() => {
    void loadDetail(true);
    loadHistory();
    return () => {
      seq.current += 1;
    };
  }, [loadDetail, loadHistory]);

  const refreshAll = useCallback(() => {
    setConfirming(false);
    setStep(null);
    setActionError(null);
    void loadDetail(false);
    loadHistory();
  }, [loadDetail, loadHistory]);

  /** Phiếu đã đổi trạng thái ở nơi khác (BE báo sai trạng thái): tải lại để nút khớp trạng thái mới. */
  const onStaleStatus = (err: unknown) => {
    if (err instanceof ApiError && (err.code === "RECON_NOT_SUBMITTED" || err.code === "RECON_NOT_DRAFT")) {
      void loadDetail(false);
      loadHistory();
    }
  };

  const approve = useSubmit(
    async () => {
      try {
        return await approveStocktake(id as number);
      } catch (err) {
        onStaleStatus(err);
        const le = lineErrorOf(err);
        if (le) setLineError(le);
        if (err instanceof ApiError && err.status !== 409) throw new ApiError(cleanMessage(err.message), err.status, err.code, err.details);
        throw err;
      }
    },
    {
      onSuccess: (res) => {
        setConfirming(false);
        setDetail(res);
        setLineError(null);
        setConflict(null);
        toast.success("Đã duyệt. Tồn kho đã cộng hoặc trừ theo chênh lệch đã ghi.");
        loadHistory();
      },
    },
  );

  // Xung đột / lỗi của lần duyệt được đưa ra trang (hộp xác nhận đóng lại để người dùng thấy dòng lỗi).
  useEffect(() => {
    if (approve.conflict) {
      setConflict(approve.conflict);
      setConfirming(false);
    } else if (approve.failed && approve.error) {
      setActionError(approve.error);
      setConfirming(false);
    }
  }, [approve.conflict, approve.failed, approve.error]);

  const homeHref = me ? homePath(me) : "/overview/";
  if (id === null) return <NotFoundScreen homeHref={homeHref} />;
  if (load === "loading")
    return (
      <SkeletonScreen label="Đang tải phiếu kiểm kê…">
        <div className={s.skelRow} />
        <div className={s.skelRow} />
        <div className={s.skelRow} />
      </SkeletonScreen>
    );
  if (load === "notfound") return <NotFoundScreen homeHref={homeHref} />;
  if (load === "forbidden") return <NoPermission homeHref={homeHref} />;
  if (load === "error" || !detail) return <ErrorScreen homeHref={homeHref} onRetry={() => void loadDetail(true)} />;

  const rec = detail;
  const canApprove = hasAction(rec, "approve");
  const canEdit = hasAction(rec, "edit_lines");
  const canSubmit = hasAction(rec, "submit");
  const canReturn = hasAction(rec, "return_to_draft");
  const changed = changedLineCount(rec);
  const manyWarehouses = rec.warehouse_names.length > 1;

  const more: MoreMenuItem[] = [];

  const primary = (
    <>
      {canEdit && (
        <Link href={editHref(rec.id)} className="btn">
          Sửa số đếm
        </Link>
      )}
      {canReturn && (
        <button type="button" className="btn" onClick={() => { setActionError(null); setStep("return"); }}>
          Trả về nháp
        </button>
      )}
      {canSubmit && (
        <button type="button" className="btn primary" onClick={() => { setActionError(null); setStep("submit"); }}>
          Gửi duyệt
        </button>
      )}
      {canApprove && (
        <button type="button" className="btn primary" onClick={() => { approve.reset(); setActionError(null); setConfirming(true); }}>
          Duyệt và điều chỉnh tồn
        </button>
      )}
    </>
  );

  return (
    <DetailPage
      id="stocktake-detail"
      header={<DetailHeader back={BACK} title={rec.code} mono status={<Chip table={ENUMS.stockReconciliationStatus} value={rec.status} />} primary={primary} more={more} />}
      banner={
        <>
          {conflict && (
            <ConflictBanner noun="phiếu" updatedByName={conflict.updatedByName} updatedAt={conflict.updatedAt} onReload={refreshAll} reloading={reloading} />
          )}
          {actionError && <FormAlert>{actionError}</FormAlert>}
        </>
      }
      aiSlot={<AiDocBlockGate targetModel="inventory.stockreconciliation" targetId={rec.id} onApplied={refreshAll} />}
      timeline={
        history.state === "ready" ? (
          <Timeline entries={history.entries} truncated={history.truncated} />
        ) : history.state === "error" ? (
          <section className="state state-err" role="alert" aria-label="Dòng thời gian">
            <p className="state-title">Chưa tải được lịch sử của phiếu.</p>
            <button type="button" className="btn" onClick={() => { setHistory({ state: "loading" }); loadHistory(); }}>
              <Icon name="refresh" />
              Thử lại
            </button>
          </section>
        ) : (
          <section role="status" aria-label="Dòng thời gian">
            <span className="sr-only">Đang tải lịch sử…</span>
            <div className={s.skelRow} />
          </section>
        )
      }
    >
      <StatusPath steps={PATH_STEPS} current={rec.status} next={nextStepText(rec)} done={doneSteps(rec)} />

      <InfoGrid title="Thông tin">
        <InfoField label="Phiếu" value={rec.code} mono />
        <InfoField label="Ngày kiểm kê" value={dateOnly(rec.count_date)} num />
        <InfoField label="Kho" value={rec.warehouse_names.join(", ") || "—"} />
        <InfoField label="Người nhập số" value={rec.created_by?.display_name || "—"} />
        <InfoField label="Cập nhật lần cuối" value={`${dateTime(rec.updated_at)}${rec.updated_by_name ? ` · ${rec.updated_by_name}` : ""}`} />
        <InfoField label="Ghi chú" value={rec.note} />
        {rec.status === "APPROVED" && <InfoField label="Người duyệt" value={rec.approved_by?.display_name || "—"} />}
        {rec.status === "APPROVED" && <InfoField label="Duyệt lúc" value={rec.approved_at ? dateTime(rec.approved_at) : "—"} />}
      </InfoGrid>

      <Section
        title="Số đếm từng lô"
        count={rec.lines.length}
        aria-label="Số đếm từng lô"
        flush
        action={
          <p className={s.totals} data-totals>
            <span>
              Lô hụt <b>{rec.short_count}</b> · {qtyText(rec.short_qty)} kg
            </span>
            <span>
              Lô dư <b>{rec.over_count}</b> · {qtyText(rec.over_qty)} kg
            </span>
            <span>
              Chênh lệch ròng <b>{signedQtyText(rec.net_difference)} kg</b>
            </span>
          </p>
        }
      >
        {rec.lines.length === 0 ? (
          <div className={`${s.empty} ${s.emptyFlat}`} data-stocktake-empty>
            <p className={s.emptyTitle}>Phiếu chưa có dòng nào</p>
            <p className={s.emptyHint}>{canEdit ? "Bấm Sửa số đếm để nạp lô và nhập số đếm." : "Chờ người lập phiếu nhập số đếm."}</p>
          </div>
        ) : (
          <div className="lt-card">
            <div className="lt-scroll">
              <table className={`lt ${s.linesTable}`}>
                <caption className="sr-only">Số đếm từng lô của phiếu {rec.code}</caption>
                <thead>
                  <tr>
                    <th scope="col">Lô và mặt hàng</th>
                    <th scope="col" className="r">
                      Hệ thống (kg)
                    </th>
                    <th scope="col" className="r">
                      Đếm được (kg)
                    </th>
                    <th scope="col" className="r">
                      Chênh lệch (kg)
                    </th>
                    <th scope="col">Lý do</th>
                  </tr>
                </thead>
                <tbody>
                  {rec.lines.map((line, i) => {
                    const diff = toMilli(line.difference_qty);
                    const tone = diffTone(diff);
                    const bad = lineError?.index === i;
                    return (
                      <tr key={line.id} className={bad ? s.rowInvalid : undefined} data-line-row data-invalid={bad || undefined}>
                        <td>
                          <span className="mono">{line.batch_code}</span>
                          <span className={s.lineMeta}>
                            {line.item_name}
                            {manyWarehouses && line.warehouse_name ? ` · ${line.warehouse_name}` : ""}
                          </span>
                        </td>
                        <td className="r num">{qtyText(line.system_qty)}</td>
                        <td className="r num">{qtyText(line.counted_qty)}</td>
                        <td className={`r num ${tone === "crit" ? s.diffShort : tone === "warn" ? s.diffOver : ""}`} data-diff>
                          {signedQtyText(line.difference_qty)}
                        </td>
                        <td className={s.reason}>
                          {line.reason || "—"}
                          {bad && (
                            <p className={s.lineErr} role="alert" data-line-error>
                              {lineError.message}
                            </p>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Section>

      {step === "submit" && (
        <ConfirmModal
          title="Gửi duyệt phiếu kiểm kê"
          confirmLabel="Gửi duyệt"
          busyLabel="Đang gửi…"
          noun="phiếu"
          run={() => submitStocktake(rec.id)}
          onError={onStaleStatus}
          errorText={cleanErrorText}
          onReload={refreshAll}
          onDone={(res) => {
            setStep(null);
            setDetail(res);
            setLineError(null);
            setConflict(null);
            toast.success("Đã gửi duyệt. Phiếu chờ Chủ hoặc Quản lý duyệt.");
            loadHistory();
          }}
          onClose={() => setStep(null)}
        >
          <p>Gửi phiếu {rec.code} đi duyệt. Sau khi gửi không sửa số đếm được, trừ khi người có quyền trả phiếu về nháp.</p>
        </ConfirmModal>
      )}
      {step === "return" && (
        <ConfirmModal
          title="Trả phiếu kiểm kê về nháp"
          confirmLabel="Trả về nháp"
          busyLabel="Đang gửi…"
          noun="phiếu"
          run={() => returnStocktakeToDraft(rec.id)}
          onError={onStaleStatus}
          errorText={cleanErrorText}
          onReload={refreshAll}
          onDone={(res) => {
            setStep(null);
            setDetail(res);
            setLineError(null);
            setConflict(null);
            toast.success("Đã trả phiếu về nháp. Có thể sửa số đếm lại.");
            loadHistory();
          }}
          onClose={() => setStep(null)}
        >
          <p>Phiếu {rec.code} quay về nháp để sửa số đếm. Tồn kho chưa đổi.</p>
        </ConfirmModal>
      )}
      {confirming && (
        <Modal
          title="Duyệt và điều chỉnh tồn kho"
          size="sm"
          onClose={() => setConfirming(false)}
          busy={approve.submitting}
          footer={
            <>
              <button type="button" className="btn" onClick={() => setConfirming(false)} disabled={approve.submitting}>
                Quay lại
              </button>
              <button type="button" className="btn primary" onClick={() => void approve.submit()} disabled={approve.submitting}>
                {approve.submitting ? "Đang gửi…" : primaryLabel("Duyệt phiếu", approve.failed)}
              </button>
            </>
          }
        >
          <SummaryBlock
            label="Phiếu cần duyệt"
            rows={[
              { label: "Phiếu", value: rec.code, mono: true },
              { label: "Lô đổi tồn", value: `${changed} / ${rec.line_count}`, num: true },
              { label: "Chênh lệch ròng", value: `${signedQtyText(rec.net_difference)} kg`, num: true, strong: true },
            ]}
          />
          <p>{changed > 0 ? "Mỗi lô lệch sẽ được cộng hoặc trừ đúng phần chênh lệch đã ghi lúc đếm (không đặt lại bằng số đếm). Phiếu đã duyệt không sửa lại được." : "Số đếm khớp sổ nên tồn kho không đổi. Phiếu đã duyệt không sửa lại được."}</p>
        </Modal>
      )}
    </DetailPage>
  );
}
