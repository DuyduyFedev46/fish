"use client";

// ED-15 — Trang chi tiết một việc gọi xác nhận /confirmation/detail/?id=<note_id>.
// Khung DetailPage: header (mã đơn mono · chip · [Gọi khách] [nút chính] · …), StatusPath, Thông tin, Lịch sử cuộc gọi;
// cột phải = Trợ lý AI + dòng thời gian. Hộp: F2h Ghi kết quả gọi, F2i Hẹn gọi lại, F2j Đổi người nhận / địa chỉ, F2k Quyết định.
// Nút nào hiện do `available_actions` của BE quyết định (CSKH không có "Quyết định"). Phiếu ngoài phạm vi: BE trả 404 → "Không tìm thấy".
// Tên/SĐT/địa chỉ chỉ hiện trong trang; URL chỉ mang ?id=, không có log hay localStorage. Không có giá vốn ở màn này.
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { getGuidance } from "@/features/guidance/api";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, kg, timeHM, vnd } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { PersonalText } from "@/shared/ui/PersonalText";
import { SkeletonScreen } from "@/shared/ui/Skeleton";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline, type TimelineEntry } from "@/shared/ui/detail/Timeline";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { conflictOf, isConflictError, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { claimConfirmationTask, fetchConfirmationDetail } from "../api";
import { PATH_STEPS, callResultsOf, callToast, claimActive, decisionsOf, doneSteps, dueAt, hasAction, idFromSearch, lastCallerName, nextStepText, pathOf, telHref } from "../confirmationUi";
import type { CallResult, ConfirmationQueueDetail } from "../types";
import { ChangeRecipientModal } from "./ChangeRecipientModal";
import { ConfirmationAiBlock } from "./ConfirmationAiBlock";
import { DecideModal } from "./DecideModal";
import { RecordCallModal } from "./RecordCallModal";
import { UnconfirmModal } from "./UnconfirmModal";
import s from "../confirmation.module.css";

type Load = "loading" | "ready" | "error" | "notfound" | "forbidden";
type Modals = null | "call" | "callback" | "recipient" | "decide" | "unconfirm";
type History = { state: "loading" } | { state: "error" } | { state: "forbidden" } | { state: "notfound" } | { state: "ready"; entries: TimelineEntry[]; truncated: boolean };

const BACK = { href: "/confirmation/", label: "Gọi xác nhận" };
const HOME = "/confirmation/";

export function ConfirmationDetailScreen() {
  const id = idFromSearch(useSearchParams().get("id"));
  const { me } = useAuth();
  const toast = useToast();
  const router = useRouter();

  const [load, setLoad] = useState<Load>("loading");
  const [detail, setDetail] = useState<ConfirmationQueueDetail | null>(null);
  const [history, setHistory] = useState<History>({ state: "loading" });
  const [modal, setModal] = useState<Modals>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloading, setReloading] = useState(false);
  const seq = useRef(0);
  // Đã có dữ liệu đơn chưa (ref để loadDetail không đọc state cũ): tải lại lỗi thì giữ dữ liệu cũ và báo, không thay bằng màn lỗi.
  const hasDetail = useRef(false);

  const loadHistory = useCallback(() => {
    if (id === null) return;
    getGuidance("delivery", id)
      .then((g) => setHistory({ state: "ready", entries: toTimelineEntries(g.timeline), truncated: Boolean(g.timeline_truncated) }))
      .catch((err: unknown) => {
        // 403 = không có quyền xem lịch sử, 404 = không có lịch sử: thử lại cũng vô ích nên không hiện nút Thử lại.
        const status = err instanceof ApiError ? err.status : 0;
        setHistory({ state: status === 403 ? "forbidden" : status === 404 ? "notfound" : "error" });
      });
  }, [id]);

  const loadDetail = useCallback(
    async (initial: boolean) => {
      if (id === null) return;
      const mine = ++seq.current;
      if (initial) {
        hasDetail.current = false;
        setLoad("loading");
      } else setReloading(true);
      try {
        const data = await fetchConfirmationDetail(id);
        if (mine !== seq.current) return;
        hasDetail.current = true;
        setDetail(data);
        setLoad("ready");
        setConflict(null);
      } catch (err) {
        if (mine !== seq.current) return;
        if (err instanceof ApiError && err.status === 404) setLoad("notfound");
        else if (err instanceof ApiError && err.status === 403) setLoad("forbidden");
        else if (!hasDetail.current) setLoad("error");
        else setActionError("Chưa tải lại được đơn. Kiểm tra mạng rồi bấm Tải lại.");
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
    setModal(null);
    void loadDetail(false);
    loadHistory();
  }, [loadDetail, loadHistory]);

  if (id === null) return <NotFoundScreen homeHref={HOME} />;
  if (load === "loading")
    return (
      <SkeletonScreen label="Đang tải đơn cần gọi…">
        <div className={s.skelRow} />
        <div className={s.skelRow} />
        <div className={s.skelRow} />
      </SkeletonScreen>
    );
  if (load === "notfound") return <NotFoundScreen homeHref={HOME} />;
  if (load === "forbidden") return <NoPermission homeHref={HOME} />;
  if (load === "error" || !detail) return <ErrorScreen homeHref={HOME} onRetry={() => void loadDetail(true)} />;

  const item = detail;
  const actions = item.available_actions;
  const results = callResultsOf(actions);
  const decisions = decisionsOf(actions);
  const path = pathOf(item);
  const heldByOther = claimActive(item) && item.claimed_by?.id !== me?.id;
  const phone = item.recipient_phone ?? item.phone;
  const tel = telHref(phone);

  // Giữ phiếu (mềm 5 phút) trước khi mở hộp ghi cuộc gọi. 409 CLAIMED là lỗi thường: hiện nguyên câu của BE, không phải xung đột phiên bản.
  const claimThen = async (next: () => void) => {
    if (busy) return;
    setActionError(null);
    if (!hasAction(item, "claim")) {
      next();
      return;
    }
    setBusy("claim");
    try {
      await claimConfirmationTask(item.note_id);
      next();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setLoad("notfound");
      else if (isConflictError(err)) setConflict(conflictOf(err));
      else {
        setActionError(err instanceof Error && err.message ? err.message : "Chưa giữ được đơn để gọi. Bấm lại để thử lại.");
        if (err instanceof ApiError && err.code === "CLAIMED") void loadDetail(false);
      }
    } finally {
      setBusy(null);
    }
  };

  const more: MoreMenuItem[] = [];
  if (results.includes("CALLBACK")) more.push({ key: "callback", label: "Hẹn gọi lại", onSelect: () => void claimThen(() => setModal("callback")) });
  if (hasAction(item, "change_recipient")) more.push({ key: "recipient", label: "Đổi người nhận / địa chỉ", onSelect: () => setModal("recipient") });
  if (hasAction(item, "unconfirm")) more.push({ key: "unconfirm", label: "Huỷ xác nhận đơn", onSelect: () => setModal("unconfirm") });

  // Đang giữ đơn thì nút chỉ báo bận bằng aria-disabled (không `disabled`): nút bị vô hiệu hoá sẽ mất focus, đóng hộp không còn chỗ trả focus về (B7).
  const primary = (
    <>
      {tel && (
        <a className={`btn ${s.callBtn}`} href={tel} onClick={() => void claimThen(() => undefined)}>
          <Icon name="call" />
          <span>Gọi khách</span>
        </a>
      )}
      {decisions.length > 0 && (
        <button type="button" className="btn primary" onClick={() => (busy === null ? setModal("decide") : undefined)} aria-disabled={busy !== null || undefined}>
          Quyết định
        </button>
      )}
      {results.length > 0 && (
        <button
          type="button"
          className={`btn ${decisions.length > 0 ? "" : "primary"}`}
          onClick={() => void claimThen(() => setModal("call"))}
          aria-disabled={busy !== null || undefined}
        >
          {busy === "claim" ? <Icon name="progress_activity" className="spin" /> : null}
          <span>{busy === "claim" ? "Đang giữ đơn…" : "Ghi kết quả gọi"}</span>
        </button>
      )}
    </>
  );

  const due = dueAt(item);

  return (
    <DetailPage
      id="confirmation-detail"
      header={
        <DetailHeader
          back={BACK}
          title={item.order_code}
          mono
          status={item.confirm_state ? <Chip table={ENUMS.confirmTaskState} value={item.confirm_state} /> : <Chip table={ENUMS.deliveryStatus} value={item.note_status} />}
          primary={primary}
          more={more}
        />
      }
      banner={
        <>
          {conflict && (
            <ConflictBanner noun="đơn" updatedByName={conflict.updatedByName} updatedAt={conflict.updatedAt} onReload={refreshAll} reloading={reloading} />
          )}
          {heldByOther && item.claimed_by && (
            <FormAlert kind="warn">{`Đơn đang được ${item.claimed_by.display_name} xử lý tới ${timeHM(item.claimed_until)}.`}</FormAlert>
          )}
          {actionError && <FormAlert>{actionError}</FormAlert>}
        </>
      }
      aiSlot={<ConfirmationAiBlock noteId={item.note_id} onApplied={refreshAll} />}
      timeline={
        history.state === "ready" ? (
          <Timeline entries={history.entries} truncated={history.truncated} />
        ) : history.state === "forbidden" || history.state === "notfound" ? (
          <section className="state" role="status" aria-label="Dòng thời gian">
            <p className="state-title">{history.state === "forbidden" ? "Bạn không có quyền xem lịch sử này." : "Không tìm thấy lịch sử của đơn này."}</p>
          </section>
        ) : history.state === "error" ? (
          <section className="state state-err" role="alert" aria-label="Dòng thời gian">
            <p className="state-title">Chưa tải được lịch sử của đơn.</p>
            <button
              type="button"
              className="btn"
              onClick={() => {
                setHistory({ state: "loading" });
                loadHistory();
              }}
            >
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
      <StatusPath steps={PATH_STEPS} current={path.current} badEnd={path.badEnd} next={nextStepText(item, decisions.length > 0)} done={doneSteps(item)} />

      {item.guidance && (
        <div className={`alert-box warn ${s.guidance}`} role="status">
          <Icon name="info" />
          <span>{item.guidance}</span>
        </div>
      )}
      {item.confirm_state === "ESCALATED" && decisions.length === 0 && (
        <div className={`alert-box warn ${s.guidance}`} role="status">
          <Icon name="hourglass_top" />
          <span>Đơn đang chờ Chủ hoặc Quản lý quyết định.</span>
        </div>
      )}

      <InfoGrid title="Đơn & người nhận">
        <InfoField label="Mã đơn" value={item.order_code} mono />
        <InfoField label="Khách hàng" value={<PersonalText value={item.customer_name} />} />
        <InfoField
          label="Số điện thoại"
          value={
            item.phone === null ? (
              <PersonalText value={null} />
            ) : telHref(item.phone) ? (
              <a className={s.phoneLink} href={telHref(item.phone) ?? undefined}>
                {item.phone}
              </a>
            ) : (
              item.phone
            )
          }
        />
        <InfoField label="Người nhận" value={<PersonalText value={item.recipient_name ?? item.customer_name} />} />
        {item.recipient_phone && <InfoField label="Số người nhận" value={<PersonalText value={item.recipient_phone} />} />}
        <InfoField label="Địa chỉ giao" value={<PersonalText value={item.address} />} />
        <InfoField label="Hàng" value={item.lines_summary || "—"} />
        <InfoField label="Tổng số kg" value={kg(item.total_kg)} num />
        <InfoField label="Tổng tiền" value={vnd(item.total_amount)} num />
        <InfoField label="Trả tiền lúc" value={dateTime(item.paid_at)} num />
      </InfoGrid>

      <InfoGrid title="Gọi xác nhận">
        {item.escalation_label && <InfoField label="Lý do" value={item.escalation_label} />}
        <InfoField label="Lần gọi" value={`${item.attempts}/${item.max_attempts}`} num />
        <InfoField label={item.confirm_state === "ESCALATED" ? "Hạn quyết định" : "Hạn gọi"} value={dateTime(due)} num />
        <InfoField label="Người gọi" value={lastCallerName(item.calls) ?? "—"} />
        <InfoField label="Phiếu giao" value={item.note_code || "—"} mono />
        {item.refund && <InfoField label="Số tiền hoàn" value={vnd(item.refund.amount)} num />}
        {item.refund && <InfoField label="Hoàn tiền" value={item.refund.status_label || "—"} />}
      </InfoGrid>

      <section className={s.section} aria-label="Lịch sử cuộc gọi">
        <h3 className={s.sectionTitle}>Lịch sử cuộc gọi</h3>
        {item.calls.length > 0 ? (
          <div className="lt-card">
            <div className="lt-scroll">
              <table className="lt">
                <caption className="sr-only">Lịch sử cuộc gọi của đơn {item.order_code}</caption>
                <thead>
                  <tr>
                    <th scope="col">Thời gian</th>
                    <th scope="col">Người gọi</th>
                    <th scope="col">Kết quả</th>
                    <th scope="col">Ghi chú</th>
                  </tr>
                </thead>
                <tbody>
                  {item.calls.map((c) => (
                    <tr key={c.id}>
                      <td className="num">{dateTime(c.at)}</td>
                      <td>{c.by?.display_name || <span className="muted">Đã nghỉ việc</span>}</td>
                      <td>
                        <Chip table={ENUMS.confirmCallResult} value={c.result} />
                      </td>
                      <td className={s.noteCell}>{c.note || <span className="muted">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <p className="muted">Chưa có cuộc gọi nào cho đơn này.</p>
        )}
      </section>

      {(modal === "call" || modal === "callback") && (
        <RecordCallModal
          noteId={item.note_id}
          orderCode={item.order_code}
          customerName={item.customer_name}
          phone={item.phone}
          attempts={item.attempts}
          maxAttempts={item.max_attempts}
          results={results}
          mode={modal}
          onClose={() => setModal(null)}
          onStale={refreshAll}
          onDone={(res, ctx: { result: CallResult; callbackAt: string | null }) => {
            toast.success(callToast(ctx.result, res, item.max_attempts, ctx.callbackAt));
            refreshAll();
          }}
        />
      )}
      {modal === "recipient" && (
        <ChangeRecipientModal
          noteId={item.note_id}
          orderCode={item.order_code}
          initial={{ name: item.recipient_name ?? item.customer_name ?? "", phone: item.recipient_phone ?? item.phone ?? "", address: item.address ?? "" }}
          onClose={() => setModal(null)}
          onStale={refreshAll}
          onDone={(res, changed) => {
            if (res.label_invalidated) toast.warn("Đã lưu. Tem cũ hết hiệu lực: in tem mới rồi xé tem cũ.");
            else toast.success(changed ? "Đã lưu người nhận và địa chỉ." : "Không có gì thay đổi.");
            refreshAll();
          }}
        />
      )}
      {modal === "unconfirm" && (
        <UnconfirmModal
          noteId={item.note_id}
          orderCode={item.order_code}
          onClose={() => setModal(null)}
          onStale={refreshAll}
          onDone={() => {
            toast.success("Đã huỷ xác nhận. Đơn về Chờ xác nhận để gọi lại khách.");
            refreshAll();
          }}
        />
      )}
      {modal === "decide" && (
        <DecideModal
          noteId={item.note_id}
          orderCode={item.order_code}
          escalationLabel={item.escalation_label}
          attempts={item.attempts}
          decideDeadline={item.decide_deadline}
          actions={actions}
          onClose={() => setModal(null)}
          onStale={refreshAll}
          onDone={(decision, res) => {
            if (decision === "CANCEL") {
              toast.success("Đã huỷ đơn. Chuyển sang hoàn tiền cho khách.");
              setModal(null);
              if (res.order_id) router.push(`/orders/?order=${res.order_id}&open=refund`);
              else refreshAll();
              return;
            }
            toast.success(decision === "EXTEND" ? "Đã gia hạn. Đơn hẹn gọi lại khách." : "Đã cho giao không cần xác nhận. Đơn chuyển sang Soạn hàng.");
            refreshAll();
          }}
        />
      )}
    </DetailPage>
  );
}
