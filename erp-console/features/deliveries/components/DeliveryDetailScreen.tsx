"use client";

// ED-17 — Trang chi tiết phiếu giao /deliveries/detail/?id=<số> (thay hộp DeliveryDetailModal).
// Khung DetailPage: header (mã mono · chip · [In tem] [nút chính] · …), StatusPath, Thông tin, dòng hàng theo lô; cột phải = Trợ lý AI + dòng thời gian.
// F2o "Giao cho người giao" là hộp Modal, chỉ hiện khi `available_actions` có "assign" (phiếu chưa lên xe + có quyền).
// Không có giá vốn ở màn này. Tên/SĐT/địa chỉ chỉ hiện trong trang, không đưa vào URL (chỉ ?id=), log hay localStorage.
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { getGuidance } from "@/features/guidance/api";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import { ENUMS, deliveryLabelText } from "@/shared/lib/enums";
import { dateOnly, dateTime, kg } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { PERM, canView, homePath } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { PersonalText } from "@/shared/ui/PersonalText";
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
import { conflictOf, isConflictError, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { fetchDeliveryNoteDetail, packDeliveryNote, printDeliveryLabel, startDelivery, voidDeliveryLabel } from "../api";
import { canAssign, doneSteps, hasAction, idFromSearch, nextStepText, pathOf, PATH_STEPS, telHref } from "../deliveryUi";
import { PICK_SHEET_HREF, canOpenPickSheet } from "../pickSheet";
import type { DeliveryNoteDetail, LabelPrintReason } from "../types";
import { AssignCourierModal } from "./AssignCourierModal";
import { ConfirmCompleteModal } from "./ConfirmCompleteModal";
import { ReportFailureModal } from "./ReportFailureModal";
import { ReprintLabelModal } from "./ReprintLabelModal";
import s from "../deliveries.module.css";

type Load = "loading" | "ready" | "error" | "notfound" | "forbidden";
type Modals = null | "assign" | "reprint" | "failure" | "complete";
type Timeline_ = { state: "loading" } | { state: "error" } | { state: "ready"; entries: TimelineEntry[]; truncated: boolean };

const BACK = { href: "/deliveries/", label: "Giao hàng" };
const BACK_MINE = { href: "/my-deliveries/", label: "Việc giao của tôi" };
// Phiếu mà thao tác Chủ/Quản lý có thể đưa về bước trước hoặc huỷ (chưa lên xe).
const CANCELLABLE = new Set(["CONFIRMING", "PREPARING", "READY"]);

export function DeliveryDetailScreen() {
  const id = idFromSearch(useSearchParams().get("id"));
  const { me } = useAuth();
  const toast = useToast();

  const [load, setLoad] = useState<Load>("loading");
  const [detail, setDetail] = useState<DeliveryNoteDetail | null>(null);
  const [history, setHistory] = useState<Timeline_>({ state: "loading" });
  const [modal, setModal] = useState<Modals>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloading, setReloading] = useState(false);
  const seq = useRef(0);

  const loadHistory = useCallback(() => {
    if (id === null) return;
    getGuidance("delivery", id)
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
        const data = await fetchDeliveryNoteDetail(id);
        if (mine !== seq.current) return;
        setDetail(data);
        setLoad("ready");
        setConflict(null);
      } catch (err) {
        if (mine !== seq.current) return;
        if (err instanceof ApiError && err.status === 404) setLoad("notfound");
        else if (err instanceof ApiError && err.status === 403) setLoad("forbidden");
        else if (initial || !detail) setLoad("error");
        else setActionError("Chưa tải lại được phiếu. Kiểm tra mạng rồi bấm Tải lại.");
      } finally {
        if (mine === seq.current) setReloading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Tải lại nhưng giữ hộp đang mở (hộp giao phiếu sau 409: người dùng chọn lại ngay trên dữ liệu mới).
  const reloadKeepModal = useCallback(() => {
    void loadDetail(false);
    loadHistory();
  }, [loadDetail, loadHistory]);

  const fail = (err: unknown, fallback: string) => {
    if (isConflictError(err)) {
      setConflict(conflictOf(err));
      return;
    }
    setActionError(err instanceof Error && err.message ? err.message : fallback);
  };

  const run = async (key: string, task: () => Promise<void>, fallback: string) => {
    if (busy) return;
    setBusy(key);
    setActionError(null);
    try {
      await task();
    } catch (err) {
      fail(err, fallback);
    } finally {
      setBusy(null);
    }
  };

  // Nhân viên giao không có menu Giao hàng (S7-AC2) nhưng được mở phiếu CỦA MÌNH; phiếu người khác BE trả 404 → "Không tìm thấy" (ED-19-AC6).
  const opsView = Boolean(me && canView(me, "deliveries"));
  const homeHref = me && !opsView ? homePath(me) : "/deliveries/";
  const back = opsView ? BACK : BACK_MINE;

  if (id === null) return <NotFoundScreen homeHref={homeHref} />;
  if (load === "loading")
    return (
      <SkeletonScreen label="Đang tải phiếu giao…">
        <div className={s.skelRow} />
        <div className={s.skelRow} />
        <div className={s.skelRow} />
      </SkeletonScreen>
    );
  if (load === "notfound") return <NotFoundScreen homeHref={homeHref} />;
  if (load === "forbidden") return <NoPermission homeHref={homeHref} />;
  if (load === "error" || !detail) return <ErrorScreen homeHref={homeHref} onRetry={() => void loadDetail(true)} />;

  const note = detail;
  const path = pathOf(note);
  const printAction = hasAction(note, "print_label") ? "print" : hasAction(note, "reprint_label") ? "reprint" : null;
  const canPack = note.status === "PREPARING" && hasAction(note, "set_status:READY");
  const canComplete = note.status === "DELIVERING" && hasAction(note, "set_status:COMPLETED");
  const canFail = note.status === "DELIVERING" && hasAction(note, "set_status:FAILED");
  const canStart = (note.status === "READY" || note.status === "FAILED") && hasAction(note, "set_status:DELIVERING");
  const assignable = canAssign(note);
  const assignIsPrimary = assignable && !canPack && !note.assigned_to;
  const assignLabel = note.assigned_to ? "Đổi người giao" : "Giao cho người giao";
  const mayAssign = Boolean(me?.permissions.includes(PERM.assignDelivery));

  const doPack = () =>
    run(
      "pack",
      async () => {
        const res = await packDeliveryNote(note.id, note.status);
        toast.success(res.already ? "Phiếu đã ở trạng thái Chờ lấy hàng." : "Đã đóng gói. Phiếu chuyển sang Chờ lấy hàng.");
        refreshAll();
      },
      "Chưa đóng gói được. Bấm lại để thử lại.",
    );

  const doPrint = (reason: LabelPrintReason) => {
    if (busy) return;
    // Mở cửa sổ ngay trong lần bấm (trình duyệt mới cho phép), rồi mới gọi API và chuyển tới trang tem.
    const win = window.open("", "_blank");
    if (!win) {
      setModal(null);
      setActionError("Trình duyệt đang chặn cửa sổ in tem. Cho phép cửa sổ bật lên cho trang này rồi bấm In tem lại.");
      return;
    }
    setModal(null);
    void run(
      "print",
      async () => {
        try {
          const res = await printDeliveryLabel(note.id, undefined, undefined, reason);
          win.location.href = `/print/label/?note=${note.id}&print_no=${res.print_no}`;
        } catch (err) {
          win.close();
          throw err;
        }
        loadHistory();
        void loadDetail(false);
      },
      "Chưa in được tem. Bấm In tem để thử lại.",
    );
  };

  const doVoid = (printNo: number) =>
    run(
      `void:${printNo}`,
      async () => {
        const res = await voidDeliveryLabel(note.id, printNo);
        toast.success(res.already ? `Tem lần ${printNo} đã được xác nhận huỷ trước đó.` : `Đã xác nhận huỷ tem giấy lần ${printNo}.`);
        void loadDetail(false);
      },
      "Chưa xác nhận huỷ tem được. Bấm lại để thử lại.",
    );

  const doStart = () =>
    run(
      "start",
      async () => {
        await startDelivery(note.id, note.status);
        toast.success(note.status === "FAILED" ? "Đã chuyển phiếu sang Đang giao để giao lại." : "Đã chuyển phiếu sang Đang giao.");
        refreshAll();
      },
      "Chưa chuyển sang Đang giao được. Bấm lại để thử lại.",
    );

  // ---- header
  const more: MoreMenuItem[] = [];
  // CS-16: phiếu soạn nội bộ (không có thông tin khách), mở ở tab mới để in khổ 100x150 mm. Chỉ khi đang Soạn hàng và có quyền in tem hoặc đóng gói.
  if (note.status === "PREPARING" && me && canOpenPickSheet(me.permissions)) {
    more.push({ key: "pick-sheet", label: "In phiếu soạn", onSelect: () => void window.open(PICK_SHEET_HREF(note.id), "_blank", "noopener") });
  }
  if (assignable && !assignIsPrimary) more.push({ key: "assign", label: assignLabel, onSelect: () => setModal("assign") });
  if (!assignable && mayAssign) {
    const reason = note.status === "DELIVERING" || note.status === "FAILED" ? "Phiếu đã lên xe, không đổi người giao." : "Phiếu đã kết thúc.";
    more.push({ key: "assign", label: "Đổi người giao", blockedReason: reason });
  }
  // ED-17-AC3: phiếu chưa in tem → "In lại tem" mờ, kèm lý do. Hai mục dưới là việc làm ở trang Đơn hàng nên mờ, có lý do ngắn (nợ: nối link khi Lô 3 xong).
  if (opsView && CANCELLABLE.has(note.status)) {
    if (!note.label.printed) more.push({ key: "reprint", label: "In lại tem", blockedReason: "Chưa in tem lần nào." });
    more.push({ key: "unconfirm", label: "Huỷ xác nhận đơn", blockedReason: "Đưa đơn về Gọi xác nhận." });
    more.push({ key: "cancel-order", label: "Huỷ đơn", blockedReason: "Mở đơn để huỷ và hoàn tiền cho khách." });
  }
  if (canStart) more.push({ key: "start", label: note.status === "FAILED" ? "Giao lại" : "Đã lấy hàng, bắt đầu giao", onSelect: () => void doStart() });
  if (canFail) more.push({ key: "fail", label: "Báo giao thất bại", danger: true, onSelect: () => setModal("failure") });

  const primary = (
    <>
      {printAction && (
        <button
          type="button"
          className="btn"
          onClick={() => (printAction === "print" ? doPrint("FIRST") : setModal("reprint"))}
          disabled={busy !== null}
        >
          {busy === "print" ? <Icon name="progress_activity" className="spin" /> : null}
          <span>{printAction === "print" ? "In tem" : "In lại tem"}</span>
        </button>
      )}
      {canPack && (
        <button type="button" className="btn primary" onClick={() => void doPack()} disabled={busy !== null}>
          {busy === "pack" ? <Icon name="progress_activity" className="spin" /> : null}
          <span>{busy === "pack" ? "Đang gửi…" : "Đã đóng gói"}</span>
        </button>
      )}
      {assignIsPrimary && (
        <button type="button" className="btn primary" onClick={() => setModal("assign")} disabled={busy !== null}>
          Giao cho người giao
        </button>
      )}
      {canComplete && (
        <button type="button" className="btn primary" onClick={() => setModal("complete")} disabled={busy !== null}>
          Đã giao xong
        </button>
      )}
    </>
  );

  const toVoid = note.label?.to_void ?? [];
  const canVoid = hasAction(note, "void_label");
  const phone = note.phone;
  const tel = telHref(phone);
  const hasFailure = note.failed_attempts > 0 || note.status === "FAILED";

  return (
    <DetailPage
      id="delivery-detail"
      header={
        <DetailHeader
          back={back}
          title={note.code}
          mono
          status={<Chip table={ENUMS.deliveryStatus} value={note.status} />}
          primary={primary}
          more={more}
        />
      }
      banner={
        <>
          {conflict && (
            <ConflictBanner
              noun="phiếu"
              updatedByName={conflict.updatedByName}
              updatedAt={conflict.updatedAt}
              onReload={refreshAll}
              reloading={reloading}
            />
          )}
          {actionError && <FormAlert>{actionError}</FormAlert>}
        </>
      }
      aiSlot={<AiDocBlockGate targetModel="delivery.deliverynote" targetId={note.id} onApplied={refreshAll} />}
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
      <StatusPath
        steps={PATH_STEPS}
        current={path.current}
        badEnd={path.badEnd}
        next={nextStepText(note)}
        done={doneSteps(note)}
      />

      {toVoid.length > 0 && (
        <div className={s.voidList}>
          {toVoid.map((no) => {
            const cancelled = note.status === "CANCELLED";
            return (
              <div key={no} className={`alert-box ${cancelled ? "err" : "warn"} ${s.voidRow}`} role="status">
                <Icon name={cancelled ? "error" : "warning"} />
                <span className={s.voidText}>
                  {cancelled ? `Đơn đã huỷ: xé tem lần ${no}.` : `Tem cũ lần ${no} hết hiệu lực: in tem mới rồi xé tem cũ.`}
                </span>
                {canVoid && (
                  <button type="button" className="btn" onClick={() => void doVoid(no)} disabled={busy !== null}>
                    {busy === `void:${no}` ? "Đang xử lý…" : "Đã huỷ tem"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      <InfoGrid title="Thông tin">
        <InfoField label="Đơn hàng" value={note.order?.code} mono />
        <InfoField label="Hoá đơn" value={note.invoice_code} mono />
        <InfoField label="Người nhận" value={<PersonalText value={note.recipient_name ?? note.customer_name} />} />
        <InfoField
          label="Số điện thoại"
          value={
            phone === null ? (
              <PersonalText value={null} />
            ) : tel && phone ? (
              <a className={s.phoneLink} href={tel}>
                {phone}
              </a>
            ) : (
              phone
            )
          }
        />
        <InfoField label="Địa chỉ giao" value={<PersonalText value={note.address} />} />
        {note.delivery_started_at ? <InfoField label="Bắt đầu giao" value={dateTime(note.delivery_started_at)} num /> : null}
        {note.failed_at ? <InfoField label="Giao thất bại" value={dateTime(note.failed_at)} num /> : null}
        <InfoField label="Người giao" value={note.assigned_to_name || (note.assigned_to ? "Đã giao" : "Chưa giao cho ai")} />
        <InfoField label="Tổng số kg" value={kg(note.total_kg)} num />
        <InfoField label="Tem" value={<Chip entry={deliveryLabelText(note.label.printed ? note.label.valid_print_no ?? 1 : null)} />} />
        <InfoField label="Ghi chú đơn" value={<PersonalText value={note.note} whenEmpty="" />} />
        {hasFailure && <InfoField label="Lý do giao thất bại" value={note.failure_reason_label} />}
        {hasFailure && <InfoField label="Ghi chú giao thất bại" value={<PersonalText value={note.failure_note} whenEmpty="" />} />}
        {hasFailure && <InfoField label="Lần giao thất bại" value={String(note.failed_attempts)} num />}
      </InfoGrid>

      <Section title="Hàng soạn theo lô" aria-label="Hàng soạn theo lô" flush={Boolean(note.lines && note.lines.length > 0)}>
        {note.lines && note.lines.length > 0 ? (
          <div className="lt-card">
            <div className="lt-scroll">
              <table className="lt">
                <caption className="sr-only">Hàng soạn theo lô của phiếu {note.code}</caption>
                <thead>
                  <tr>
                    <th scope="col">Mặt hàng</th>
                    <th scope="col">Kho</th>
                    <th scope="col">Lô xuất</th>
                    <th scope="col">Hạn dùng</th>
                    <th scope="col" className="r">
                      Số kg
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {note.lines.map((line, i) => (
                    <tr key={`${line.batch_id}-${i}`}>
                      <td>{line.item_name}</td>
                      <td>{line.warehouse_name || "—"}</td>
                      <td className="mono">{line.batch_id}</td>
                      <td className="num">{dateOnly(line.expiry_date)}</td>
                      <td className="r num">{kg(line.qty_kg)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <p className="muted">Phiếu này chưa có dòng hàng nào được soạn.</p>
        )}
      </Section>

      {modal === "assign" && (
        <AssignCourierModal
          note={note}
          onClose={() => setModal(null)}
          onReload={reloadKeepModal}
          onAssigned={(res, deliverer) => {
            toast.success(res.already ? `Phiếu đã giao cho ${deliverer.display_name} từ trước.` : `Đã giao phiếu cho ${deliverer.display_name}.`);
            refreshAll();
          }}
        />
      )}
      {modal === "reprint" && <ReprintLabelModal code={note.code} onClose={() => setModal(null)} onConfirm={doPrint} />}
      {modal === "failure" && (
        <ReportFailureModal
          note={note}
          onClose={() => setModal(null)}
          onReported={(res) => {
            toast.success(res.needs_decision ? "Đã báo giao thất bại. Phiếu này đã hỏng 2 lần, chờ Chủ hoặc Quản lý quyết định." : "Đã báo giao thất bại.");
            refreshAll();
          }}
        />
      )}
      {modal === "complete" && (
        <ConfirmCompleteModal
          note={note}
          onClose={() => setModal(null)}
          onConflict={refreshAll}
          onDone={() => {
            toast.success("Đã giao xong. Phiếu chuyển sang Hoàn tất.");
            refreshAll();
          }}
        />
      )}
    </DetailPage>
  );
}
