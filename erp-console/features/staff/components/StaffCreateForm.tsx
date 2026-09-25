"use client";

// S41: Chủ tạo tài khoản nhân viên, chọn một hay nhiều nhóm. Form GIỮ NHÁP (S7-AC6): hết phiên giữa chừng →
// đăng nhập lại cùng người thì form mở lại đủ nội dung đã gõ. Mật khẩu KHÔNG lưu vào nháp (không để mật khẩu
// nằm trong localStorage, S48-AC5) → phải gõ lại. Thêm/bỏ nhóm Chủ → hỏi xác nhận trước khi gửi.
// S48: ô mật khẩu tạm + ô "Nhập lại" (khác nhau → báo tại ô, không gọi API); nút "Tạo tài khoản" chỉ khoá khi đang gửi,
// mọi lỗi dữ liệu khác do BE trả (nguyên văn, ngay trên nút gửi) — bấm là gửi POST.
// UI4: một cột, nhãn trên ô, gợi ý dưới ô, ba phần (thông tin · nhóm · mật khẩu), thanh nút dính đáy.

import { useId, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { Icon } from "@/shared/ui/Icon";
import { GROUP } from "@/shared/lib/nav";
import { createStaff } from "../api";
import type { StaffMember } from "../types";
import { GroupPicker } from "./GroupPicker";
import { PasswordField } from "./PasswordField";
import { Consequence, DangerConfirm, ErrorLine, useFocusOnSwap } from "./parts";
import { errorText } from "@/shared/lib/messages";
import { STAFF_MSG } from "../messages";
import s from "../staff.module.css";

/** Phần được giữ nháp (không có mật khẩu). `open` = form đang mở lúc lưu → mở lại sau khi đăng nhập lại. */
export type CreateDraft = {
  open: boolean;
  username: string;
  display_name: string;
  phone: string;
  groups: string[];
};

export const EMPTY_CREATE_DRAFT: CreateDraft = { open: false, username: "", display_name: "", phone: "", groups: [] };

export function hasDraftContent(d: CreateDraft): boolean {
  return !!(d.username.trim() || d.display_name.trim() || d.phone.trim() || d.groups.length);
}

type Props = {
  draft: CreateDraft;
  setDraft: (d: CreateDraft) => void;
  restored: boolean;
  onCreated: (member: StaffMember, password: string) => void;
  onDiscard: () => void;
  onBusy: (busy: boolean) => void;
};

function Req() {
  return (
    <span className={s.req} aria-hidden="true">
      *
    </span>
  );
}

export function StaffCreateForm({ draft, setDraft, restored, onCreated, onDiscard, onBusy }: Props) {
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmChu, setConfirmChu] = useState(false);
  const swapRef = useFocusOnSwap(confirmChu ? "confirm" : "form");
  const uid = useId();

  const set = (patch: Partial<CreateDraft>) => setDraft({ ...draft, ...patch });

  const send = async () => {
    setBusy(true);
    onBusy(true);
    setError(null);
    try {
      const m = await createStaff({
        username: draft.username.trim(),
        display_name: draft.display_name.trim(),
        phone: draft.phone.trim(),
        groups: draft.groups,
        password,
      });
      onCreated(m, password);
    } catch (err) {
      // 401 → apiFetch đã đưa về đăng nhập, nháp còn giữ. Còn lại: hiện nguyên văn thông điệp BE.
      if (!(err instanceof ApiError && err.status === 401)) {
        setError(errorText(err));
      }
      setConfirmChu(false);
    } finally {
      setBusy(false);
      onBusy(false);
    }
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    if (password !== again) {
      setError(null);
      setMismatch(true); // S48-AC3: không gọi API
      return;
    }
    if (draft.groups.includes(GROUP.chu) && !confirmChu) {
      setConfirmChu(true);
      return;
    }
    void send();
  };

  if (confirmChu) {
    return (
      <div className={s.pane} ref={swapRef} tabIndex={-1}>
        <DangerConfirm
          tone="warn"
          icon="shield_person"
          title="Tạo tài khoản thuộc nhóm Chủ?"
          error={error}
          busy={busy}
          cancelLabel="Quay lại"
          onCancel={() => setConfirmChu(false)}
          confirmLabel="Tạo tài khoản Chủ"
          onConfirm={() => void send()}
        >
          <p>
            Tài khoản <b>{draft.username.trim()}</b> sẽ thuộc nhóm <b>Chủ</b>. Chắc chắn tạo?
          </p>
          <ul className={s.consequences}>
            <Consequence icon="payments">Toàn quyền tiền, giá vốn, lãi lỗ.</Consequence>
            <Consequence icon="manage_accounts">Quản lý nhân viên.</Consequence>
          </ul>
        </DangerConfirm>
      </div>
    );
  }

  const hUser = `${uid}-u`;
  const hGroups = `${uid}-g`;
  return (
    <form onSubmit={onSubmit} className={s.pane} ref={swapRef as unknown as React.Ref<HTMLFormElement>} tabIndex={-1} aria-label="Tạo tài khoản nhân viên" noValidate>
      {restored && hasDraftContent(draft) && (
        <div className="alert-box info" role="status">
          <Icon name="history" />
          <span>{STAFF_MSG.draftRestored}</span>
        </div>
      )}

      <div className={s.section}>
        <div className="field">
          <label htmlFor="sc-username">
            Tên đăng nhập
            <Req />
          </label>
          <input
            id="sc-username"
            data-autofocus
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            value={draft.username}
            onChange={(e) => set({ username: e.target.value })}
            disabled={busy}
            required
            aria-describedby={hUser}
          />
          <span className="help" id={hUser}>
            Chữ, số và @ . + - _, không dấu cách. Ví dụ: giao4
          </span>
        </div>
        <div className="field">
          <label htmlFor="sc-name">Tên hiển thị</label>
          <input
            id="sc-name"
            autoComplete="off"
            value={draft.display_name}
            onChange={(e) => set({ display_name: e.target.value })}
            disabled={busy}
          />
        </div>
        <div className="field">
          <label htmlFor="sc-phone">
            Số điện thoại
            <Req />
          </label>
          <input
            id="sc-phone"
            type="tel"
            inputMode="tel"
            autoComplete="off"
            value={draft.phone}
            onChange={(e) => set({ phone: e.target.value })}
            disabled={busy}
            required
          />
        </div>
      </div>

      <div className={s.section}>
        <GroupPicker
          value={draft.groups}
          onChange={(groups) => set({ groups })}
          disabled={busy}
          describedBy={draft.groups.length === 0 ? hGroups : undefined}
        />
        {draft.groups.length === 0 && (
          <p className="help" id={hGroups}>
            Chưa chọn nhóm nào: người này đăng nhập được nhưng chưa dùng được mục nào.
          </p>
        )}
      </div>

      <div className={s.section}>
        <PasswordField
          id="sc-password"
          label="Mật khẩu tạm"
          value={password}
          onChange={(v) => {
            setPassword(v);
            setMismatch(false);
          }}
          again={again}
          onAgainChange={(v) => {
            setAgain(v);
            setMismatch(false);
          }}
          mismatch={mismatch}
          username={draft.username}
          disabled={busy}
        />
      </div>

      <ErrorLine error={error} />
      <div className={`form-actions ${s.footer}`}>
        <button type="button" className="btn" onClick={onDiscard} disabled={busy}>
          <Icon name="delete" />
          Bỏ nháp
        </button>
        <button type="submit" className="btn primary" disabled={busy} aria-busy={busy || undefined}>
          {busy && <Icon name="progress_activity" className="spin" />}
          {busy ? "Đang tạo…" : "Tạo tài khoản"}
        </button>
      </div>
    </form>
  );
}
