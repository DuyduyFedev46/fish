"use client";

// ED-19 — Việc giao của tôi (nhân viên giao): chỉ phiếu gán cho mình (`assigned_to=me`), chia nhóm
// Đang giao · Chờ lấy hàng · Giao thất bại · Đã xong (hôm nay). Thẻ lớn cho điện thoại 360px.
// "Gọi khách" hiện đủ số và mở `tel:`. Lô bổ sung A #17: số lấy thẳng từ `phone` trong danh sách `assigned_to=me` (không gọi thêm chi tiết từng phiếu);
// số chỉ nằm trong bộ nhớ trang: không ghi localStorage, URL, log.
// F2l "Báo giao thất bại" là hộp riêng. Lô 9: thẻ Giao thất bại có nút "Mang hàng về kho" mở hộp F2m (CreateReturnModal) với phiếu giao điền sẵn;
// nút chỉ mở hộp, việc ghi phiếu hoàn tiền do hộp đó làm (BE chặn nếu phiếu không còn Đang giao/Giao thất bại).
import { useMemo, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { kg, todayInVietnam } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { usePagedList } from "@/shared/lib/usePagedList";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { PersonalText } from "@/shared/ui/PersonalText";
import { SkeletonScreen } from "@/shared/ui/Skeleton";
import { ErrorBox } from "@/shared/ui/StateBox";
import { isConflictError } from "@/shared/ui/form/useSubmit";
import { useToast } from "@/shared/ui/overlay/Toast";
import { fetchDeliveryNotes, startDelivery } from "../api";
import { MINE_GROUPS, completeToast, groupMine, isOrderCancelledError, orderCancelledMessage, hasAction, lineNames, telHref, type MineGroupKey } from "../deliveryUi";
import type { DeliveryNoteItem } from "../types";
import { ConfirmCompleteModal } from "./ConfirmCompleteModal";
import { ReportFailureModal } from "./ReportFailureModal";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { CreateReturnModal } from "@/features/returns/components/CreateReturnModal";
import { canCreate } from "@/features/returns/returnsModel";
import s from "../deliveries.module.css";

type Params = { assigned_to: string; status: string; completed_from?: string };

const ACTIVE: Params = { assigned_to: "me", status: "READY,DELIVERING,FAILED" };

function MineCard({
  note,
  busy,
  error,
  onStart,
  onComplete,
  onFail,
  onReturn,
}: {
  note: DeliveryNoteItem;
  busy: boolean;
  error: string | undefined;
  onStart: () => void;
  onComplete: () => void;
  onFail: () => void;
  onReturn: () => void;
}) {
  const showCall = note.status === "DELIVERING" || note.status === "FAILED";
  const phone = note.phone ?? null; // null/thiếu = đã ẩn theo cửa sổ 7 ngày
  const tel = phone ? telHref(phone) : null;
  const canStart = (note.status === "READY" || note.status === "FAILED") && hasAction(note, "set_status:DELIVERING");
  const canComplete = note.status === "DELIVERING" && hasAction(note, "set_status:COMPLETED");
  const canFail = note.status === "DELIVERING" && hasAction(note, "set_status:FAILED");
  // Nút chỉ hiện khi có quyền nhập hàng hoàn (BE vẫn chặn 403).
  const { me } = useAuth();
  const canReturn = note.status === "FAILED" && canCreate(me?.permissions);

  return (
    <li className={s.card} data-note-id={note.id} data-status={note.status}>
      <div className={s.cardTop}>
        <span className={s.cardCode}>{note.code}</span>
        <Chip table={ENUMS.deliveryStatus} value={note.status} />
      </div>
      <dl className={s.cardFields}>
        <dt>Người nhận</dt>
        <dd className={s.strong}>
          <PersonalText value={note.customer_name} />
        </dd>
        <dt>Đơn</dt>
        <dd className="mono">{note.order?.code || "—"}</dd>
        <dt>Địa chỉ</dt>
        <dd>
          <PersonalText value={note.address} />
        </dd>
        <dt>Số kg</dt>
        <dd className="num">{kg(note.total_kg)}</dd>
        <dt>Hàng</dt>
        <dd>{lineNames(note.lines_summary) || "—"}</dd>
        {note.note ? (
          <>
            <dt>Ghi chú đơn</dt>
            <dd>{note.note}</dd>
          </>
        ) : null}
        {note.status === "FAILED" && (
          <>
            <dt>Lý do</dt>
            <dd>{note.failure_reason_label || "Chưa rõ lý do"}</dd>
            <dt>Lần thất bại</dt>
            <dd className="num">{note.failed_attempts}</dd>
          </>
        )}
      </dl>
      <p className={s.cardPaid}>Đã thanh toán, không thu thêm</p>
      {error && (
        <p className={`alert-box err ${s.cardAlert}`} role="alert">
          <Icon name="error" />
          <span>{error}</span>
        </p>
      )}

      <div className={s.cardActions}>
        {showCall &&
          (tel ? (
            <a className="btn" href={tel} aria-label={`Gọi khách, số ${phone}`}>
              <Icon name="call" />
              <span>Gọi khách</span>
              <span className="num">{phone}</span>
            </a>
          ) : (
            <span className={s.cardMeta}>Số điện thoại đã ẩn (quá 7 ngày)</span>
          ))}
        {canFail && (
          <button type="button" className="btn danger" onClick={onFail} disabled={busy}>
            Báo giao thất bại
          </button>
        )}
        {canReturn && (
          <button type="button" className="btn" onClick={onReturn} disabled={busy}>
            <Icon name="assignment_return" />
            <span>Mang hàng về kho</span>
          </button>
        )}
        {canComplete && (
          <button type="button" className={`btn primary ${s.grow}`} onClick={onComplete} disabled={busy}>
            Đã giao xong
          </button>
        )}
        {canStart && (
          <button type="button" className={`btn primary ${s.grow}`} onClick={onStart} disabled={busy}>
            {busy ? <Icon name="progress_activity" className="spin" /> : null}
            <span>{busy ? "Đang gửi…" : note.status === "FAILED" ? "Giao lại" : "Đã lấy hàng, bắt đầu giao"}</span>
          </button>
        )}
      </div>
    </li>
  );
}

export function MyDeliveriesScreen() {
  const toast = useToast();
  const doneParams: Params = useMemo(() => ({ assigned_to: "me", status: "COMPLETED", completed_from: todayInVietnam() }), []);
  const active = usePagedList<DeliveryNoteItem, Params>((p, page) => fetchDeliveryNotes({ ...p, page }), ACTIVE, true);
  const done = usePagedList<DeliveryNoteItem, Params>((p, page) => fetchDeliveryNotes({ ...p, page }), doneParams, true);

  const [busyId, setBusyId] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<number, string>>({});
  const [failFor, setFailFor] = useState<DeliveryNoteItem | null>(null);
  const [completeFor, setCompleteFor] = useState<DeliveryNoteItem | null>(null);
  const [returnFor, setReturnFor] = useState<DeliveryNoteItem | null>(null);

  const reloadAll = () => {
    void active.reload();
    void done.reload();
  };

  const setError = (id: number, message: string | null) =>
    setErrors((e) => {
      const next = { ...e };
      if (message) next[id] = message;
      else delete next[id];
      return next;
    });

  const onStart = async (note: DeliveryNoteItem) => {
    if (busyId !== null) return;
    setBusyId(note.id);
    setError(note.id, null);
    try {
      await startDelivery(note.id, note.status);
      toast.success(note.status === "FAILED" ? "Đã chuyển sang Đang giao để giao lại." : "Đã chuyển sang Đang giao.");
      reloadAll();
    } catch (err) {
      if (isConflictError(err)) {
        toast.warn("Phiếu vừa đổi trạng thái. Đã tải lại danh sách.");
        reloadAll();
      } else if (isOrderCancelledError(err)) {
        setError(note.id, orderCancelledMessage(err));
        reloadAll();
      } else {
        setError(note.id, err instanceof Error && err.message ? err.message : "Chưa chuyển sang Đang giao được. Bấm lại để thử lại.");
      }
    } finally {
      setBusyId(null);
    }
  };

  const rows = useMemo(() => [...(active.rows ?? []), ...(done.rows ?? [])], [active.rows, done.rows]);
  const groups = useMemo(() => groupMine(rows), [rows]);
  const forbidden = active.error instanceof ApiError && active.error.status === 403;
  const loading = active.rows === undefined && !active.error;

  if (loading) {
    return (
      <SkeletonScreen label="Đang tải việc giao của bạn…">
        <div className={s.skelRow} />
        <div className={s.skelRow} />
        <div className={s.skelRow} />
      </SkeletonScreen>
    );
  }
  if (active.rows === undefined) {
    return <ErrorBox icon={forbidden ? "lock" : undefined} message={loadErrorText(active.error)} onRetry={() => void active.reload()} />;
  }

  const total = rows.length;
  const summary = [
    groups.DELIVERING.length ? `${groups.DELIVERING.length} đang giao` : "",
    groups.READY.length ? `${groups.READY.length} chờ lấy hàng` : "",
    groups.FAILED.length ? `${groups.FAILED.length} giao thất bại` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className={s.mine} id="my-deliveries">
      <div className={s.mineHead}>
        <p className={s.summary} aria-live="polite">
          {total === 0 ? "Bạn chưa có phiếu giao nào." : summary || "Hôm nay bạn đã giao xong hết."}
        </p>
        <button type="button" className="btn" onClick={reloadAll} disabled={active.loading || done.loading}>
          <Icon name="refresh" className={active.loading || done.loading ? "spin" : undefined} />
          <span>Tải lại</span>
        </button>
      </div>

      {(active.error != null || done.error != null) && (
        <div className="alert-box err" role="alert">
          <Icon name="sync_problem" />
          <span>{loadErrorText(active.error ?? done.error)}</span>
          <button type="button" className="btn" onClick={reloadAll}>
            Thử lại
          </button>
        </div>
      )}

      {total === 0 && (
        <div className="state" role="status">
          <span className="state-ic">
            <Icon name="two_wheeler" />
          </span>
          <b className="state-title">Chưa có phiếu giao nào gán cho bạn</b>
          <p>Khi Chủ hoặc Quản lý giao phiếu cho bạn, phiếu sẽ hiện ở đây.</p>
        </div>
      )}

      {MINE_GROUPS.map((g) => {
        const list = groups[g.key as MineGroupKey];
        if (list.length === 0) return null;
        const titleId = `mine-${g.key}`;
        return (
          <section key={g.key} className={s.group} aria-labelledby={titleId} data-group={g.key}>
            <h2 className={s.groupHead} id={titleId}>
              <span className={s.groupTitle}>{g.title}</span>
              <span className={s.groupCount}>{list.length}</span>
            </h2>
            <ul className={s.cards}>
              {list.map((n) => (
                <MineCard
                  key={n.id}
                  note={n}
                  busy={busyId === n.id}
                  error={errors[n.id]}
                  onStart={() => void onStart(n)}
                  onComplete={() => setCompleteFor(n)}
                  onFail={() => setFailFor(n)}
                  onReturn={() => setReturnFor(n)}
                />
              ))}
            </ul>
          </section>
        );
      })}

      {active.hasMore && (
        <button type="button" className="btn" onClick={() => void active.loadMore()} disabled={active.moreLoading}>
          {active.moreLoading ? "Đang tải…" : "Tải thêm"}
        </button>
      )}

      {failFor && (
        <ReportFailureModal
          note={failFor}
          onClose={() => setFailFor(null)}
          onReload={() => {
            setFailFor(null);
            reloadAll();
          }}
          onReported={(res) => {
            setFailFor(null);
            toast.success(res.needs_decision ? "Đã báo giao thất bại. Phiếu đã hỏng 2 lần, chờ Chủ hoặc Quản lý quyết định." : "Đã báo giao thất bại.");
            reloadAll();
          }}
        />
      )}
      {returnFor && (
        <CreateReturnModal
          initialNote={{ id: returnFor.id, code: returnFor.code }}
          onClose={() => setReturnFor(null)}
          onCreated={() => {
            setReturnFor(null);
            toast.success("Đã gửi phiếu hàng hoàn, chờ duyệt.");
            reloadAll();
          }}
        />
      )}
      {completeFor && (
        <ConfirmCompleteModal
          note={completeFor}
          onClose={() => setCompleteFor(null)}
          onConflict={() => {
            setCompleteFor(null);
            reloadAll();
          }}
          onDone={(res) => {
            setCompleteFor(null);
            toast.success(completeToast(res.order_status, "Đã giao xong."));
            reloadAll();
          }}
        />
      )}
    </div>
  );
}
