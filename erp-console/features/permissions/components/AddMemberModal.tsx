"use client";

// Thêm người vào nhóm (ED-40, trang chi tiết nhóm): chọn trong danh sách nhân viên đang làm chưa thuộc nhóm, bấm "Thêm vào nhóm".
// Bản chất là PUT /api/staff/<id>/groups/ với tập nhóm mới = nhóm hiện có + nhóm này (BE kiểm quyền, người cuối cùng, BR-PQ-17).
// Thêm vào nhóm Chủ = cấp toàn quyền nên có một bước xác nhận nêu hậu quả. Lỗi BE hiện NGUYÊN VĂN, hộp giữ mở.
// Tên nhân viên chỉ ở bộ nhớ trang, không vào URL/storage/log.

import { useEffect, useMemo, useState } from "react";
import { setStaffGroups, listStaff } from "@/features/staff/api";
import type { StaffMember } from "@/features/staff/types";
import { groupLabel } from "@/shared/lib/groups";
import { loadErrorText } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { ROLE } from "@/shared/lib/roles";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { PERM_MSG as M } from "../messages";
import { foldText } from "../permissionsModel";
import s from "../permissions.module.css";

type Props = {
  groupCode: string;
  groupLabelText: string;
  onClose: () => void;
  onAdded: (member: StaffMember) => void;
};

type Load = { status: "loading" } | { status: "error"; error: unknown } | { status: "ok"; rows: StaffMember[] };

export function AddMemberModal({ groupCode, groupLabelText, onClose, onAdded }: Props) {
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [q, setQ] = useState("");
  const [confirming, setConfirming] = useState<StaffMember | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setLoad({ status: "loading" });
    listStaff("active")
      .then((rows) => live && setLoad({ status: "ok", rows }))
      .catch((error) => live && setLoad({ status: "error", error }));
    return () => {
      live = false;
    };
  }, [attempt]);

  const candidates = useMemo(() => {
    if (load.status !== "ok") return [];
    const needle = foldText(q.trim());
    return load.rows
      .filter((m) => !m.groups.includes(groupCode))
      .filter((m) => !needle || foldText(m.display_name).includes(needle) || foldText(m.username).includes(needle));
  }, [load, q, groupCode]);
  const totalCandidates = load.status === "ok" ? load.rows.filter((m) => !m.groups.includes(groupCode)).length : 0;

  const add = async (m: StaffMember) => {
    if (busyId !== null) return;
    setBusyId(m.id);
    setError(null);
    try {
      await setStaffGroups(m.id, [...m.groups, groupCode]);
      onAdded(m);
    } catch (err) {
      setError(errorText(err, M.saveFailed));
    } finally {
      setBusyId(null);
    }
  };

  const pick = (m: StaffMember) => {
    setError(null);
    if (groupCode === ROLE.owner) setConfirming(m);
    else void add(m);
  };

  if (confirming) {
    const busy = busyId === confirming.id;
    return (
      <Modal
        title={M.addOwnerTitle}
        size="sm"
        onClose={onClose}
        busy={busy}
        footer={
          <>
            <button type="button" className="btn" onClick={() => setConfirming(null)} disabled={busy}>
              {M.back}
            </button>
            <button type="button" className="btn danger solid" onClick={() => void add(confirming)} disabled={busy} aria-busy={busy || undefined}>
              {busy ? (
                <>
                  <Icon name="progress_activity" className="spin" />
                  <span>{M.saving}</span>
                </>
              ) : error ? (
                "Thử lại"
              ) : (
                M.addOwnerOk
              )}
            </button>
          </>
        }
      >
        {error && <FormAlert>{error}</FormAlert>}
        <p className={s.confirmBody}>{M.addOwnerBody(confirming.display_name)}</p>
      </Modal>
    );
  }

  return (
    <Modal title={M.addTitle(groupLabelText)} onClose={onClose} busy={busyId !== null} footer={<button type="button" className="btn" onClick={onClose} disabled={busyId !== null}>{M.cancel}</button>}>
      <div className={s.stack}>
        {error && <FormAlert>{error}</FormAlert>}
        {load.status === "loading" && (
          <p className={s.pickEmpty} role="status">
            {M.addLoading}
          </p>
        )}
        {load.status === "error" && (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{`${M.addLoadFailed} ${loadErrorText(load.error)}`}</span>
            <button type="button" className="btn" onClick={() => setAttempt((n) => n + 1)}>
              {M.retry}
            </button>
          </div>
        )}
        {load.status === "ok" && (
          <>
            <div className="fb-search search">
              <label htmlFor="add-member-q" className="sr-only">
                {M.addSearchLabel}
              </label>
              <Icon name="search" />
              <input
                id="add-member-q"
                name="q"
                type="search"
                data-autofocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={M.addSearchPlaceholder}
                autoComplete="off"
              />
            </div>
            {candidates.length === 0 ? (
              <p className={s.pickEmpty}>{totalCandidates === 0 ? M.addNone : M.addNoMatch}</p>
            ) : (
              <ul className={s.pickList} aria-label={M.addSearchLabel}>
                {candidates.map((m) => (
                  <li key={m.id} className={s.pickRow}>
                    <span className={s.pickMeta}>
                      <span className={s.memberName}>{m.display_name || m.username}</span>
                      <span className={s.memberUser}>{`${m.username}${m.groups.length ? ` · ${m.groups.map(groupLabel).join(", ")}` : ""}`}</span>
                    </span>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => pick(m)}
                      disabled={busyId !== null}
                      aria-busy={busyId === m.id || undefined}
                      aria-label={`${M.addOk}: ${m.display_name || m.username}`}
                    >
                      {busyId === m.id ? M.saving : M.addPick}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
