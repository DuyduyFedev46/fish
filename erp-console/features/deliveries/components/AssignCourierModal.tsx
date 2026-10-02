"use client";

// F2o — Giao phiếu cho người giao / đổi người giao (BR-GH-23, B6). Chỉ mở khi phiếu còn CONFIRMING/PREPARING/READY và người xem có quyền.
// Danh sách người giao kèm "Đang giao n phiếu · Chờ lấy m phiếu" để chia đều việc. Gửi `expected_assigned_to` = người giao đang hiển thị:
// lệch (người khác vừa giao) → 409 STALE_STATE → ConflictBanner trong hộp; Tải lại nạp lại phiếu + danh sách người giao, giữ hộp mở để chọn lại.
import { useEffect, useId, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { kg } from "@/shared/lib/format";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { assignDeliveryNote, fetchDeliverers } from "../api";
import type { AssignDeliveryResponse, Deliverer, DeliveryNoteItem } from "../types";
import s from "../deliveries.module.css";

type Props = {
  note: Pick<DeliveryNoteItem, "id" | "code" | "order" | "total_kg" | "assigned_to" | "assigned_to_name">;
  onClose: () => void;
  /** Giao xong (kể cả `already`). */
  onAssigned: (res: AssignDeliveryResponse, deliverer: Deliverer) => void;
  /** Người dùng bấm Tải lại ở banner xung đột: màn cha tải lại phiếu. */
  onReload: () => void;
};

type Load = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; list: Deliverer[] };

export function AssignCourierModal({ note, onClose, onAssigned, onReload }: Props) {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [picked, setPicked] = useState<number | null>(null);
  const groupId = useId();
  const attempt = useRef(0);

  const fetchList = () => {
    const seq = ++attempt.current;
    setLoad({ state: "loading" });
    fetchDeliverers()
      .then((list) => seq === attempt.current && setLoad({ state: "ready", list }))
      .catch((err) => {
        if (seq !== attempt.current) return;
        const message = err instanceof ApiError && err.status === 403 ? err.message : "Chưa tải được danh sách người giao. Kiểm tra mạng rồi bấm Thử lại.";
        setLoad({ state: "error", message });
      });
  };

  useEffect(() => {
    fetchList();
    return () => {
      attempt.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sub = useSubmit(
    async () => {
      if (picked === null || load.state !== "ready") throw new Error("Chọn một người giao.");
      const deliverer = load.list.find((d) => d.id === picked);
      if (!deliverer) throw new Error("Chọn một người giao.");
      const res = await assignDeliveryNote(note.id, { assignedTo: picked, expectedAssignedTo: note.assigned_to });
      return { res, deliverer };
    },
    { onSuccess: ({ res, deliverer }) => onAssigned(res, deliverer) },
  );

  const reloadAfterConflict = () => {
    sub.reset();
    setPicked(null);
    fetchList();
    onReload();
  };

  const list = load.state === "ready" ? load.list : [];
  const sameAsCurrent = picked !== null && picked === note.assigned_to;
  const canSubmit = load.state === "ready" && picked !== null && !sameAsCurrent && !sub.conflict;
  const title = note.assigned_to ? "Đổi người giao" : "Giao cho người giao";

  return (
    <Modal
      title={title}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={() => void sub.submit()} disabled={!canSubmit || sub.submitting}>
            {sub.submitting ? "Đang gửi…" : primaryLabel("Giao phiếu", sub.failed && !sub.conflict)}
          </button>
        </>
      }
    >
      {sub.conflict && (
        <ConflictBanner noun="phiếu" updatedByName={sub.conflict.updatedByName} updatedAt={sub.conflict.updatedAt} onReload={reloadAfterConflict} />
      )}
      {sub.error && <FormAlert>{sub.error}</FormAlert>}

      <SummaryBlock
        label="Phiếu giao cần giao cho người giao"
        rows={[
          { label: "Phiếu giao", value: note.code, mono: true },
          { label: "Đơn", value: note.order?.code || "—", mono: true },
          { label: "Khối lượng", value: kg(note.total_kg), num: true },
          ...(note.assigned_to_name ? [{ label: "Người giao hiện tại", value: note.assigned_to_name }] : []),
        ]}
      />

      {load.state === "loading" && (
        <div role="status" aria-live="polite" className={s.section}>
          <span className="sr-only">Đang tải danh sách người giao…</span>
          <div className={s.skelRow} />
          <div className={s.skelRow} />
        </div>
      )}

      {load.state === "error" && (
        <div className="state state-err" role="alert">
          <span className="state-ic">
            <Icon name="error" />
          </span>
          <p className="state-title">{load.message}</p>
          <button type="button" className="btn" onClick={fetchList}>
            <Icon name="refresh" />
            Thử lại
          </button>
        </div>
      )}

      {load.state === "ready" && list.length === 0 && (
        <div className="state" role="status">
          <span className="state-ic">
            <Icon name="person_off" />
          </span>
          <p className="state-title">Chưa có người giao nào đang làm</p>
          <p>Nhờ Chủ thêm tài khoản thuộc nhóm Nhân viên giao rồi mở lại hộp này.</p>
        </div>
      )}

      {load.state === "ready" && list.length > 0 && (
        <fieldset className={s.pickList} aria-describedby={sameAsCurrent ? `${groupId}-same` : undefined}>
          <legend className={s.pickLegend}>Chọn người giao</legend>
          {list.map((d) => {
            const on = picked === d.id;
            return (
              <label key={d.id} className={`${s.pick} ${on ? s.pickOn : ""}`}>
                <input
                  className={s.pickInput}
                  type="radio"
                  name={`${groupId}-courier`}
                  value={d.id}
                  checked={on}
                  onChange={() => setPicked(d.id)}
                  disabled={sub.submitting}
                />
                <span className={s.pickBody}>
                  <span className={s.pickName}>{d.display_name}</span>
                  <span className={s.pickMeta}>
                    Đang giao {d.delivering_count} phiếu · Chờ lấy {d.ready_count} phiếu
                  </span>
                </span>
                {d.id === note.assigned_to && <span className={s.pickTag}>Đang giữ phiếu này</span>}
              </label>
            );
          })}
        </fieldset>
      )}
      {sameAsCurrent && (
        <p id={`${groupId}-same`} className="muted" role="status">
          Phiếu đã giao cho người này. Chọn người khác để đổi.
        </p>
      )}
    </Modal>
  );
}
