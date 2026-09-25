"use client";

// Mảnh giao diện dùng chung trong module staff (UI4): avatar chữ cái, nhãn nhóm, chấm trạng thái, dòng lỗi BE,
// khung xác nhận nguy hiểm, và hook chuyển focus khi đổi chế độ trong tấm bên.

import { useEffect, useId, useRef } from "react";
import { groupLabel } from "@/shared/lib/groups";
import { Icon } from "@/shared/ui/Icon";
import { STAFF_MSG } from "../messages";
import { CopyButton } from "./CopyButton";
import s from "../staff.module.css";

/** Chữ cái đại diện: tên riêng tiếng Việt đứng CUỐI ("Anh Phúc" → "P"), tránh cả danh sách toàn "A"/"C". */
export function initialOf(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const w = words.length ? words[words.length - 1] : "?";
  return w.charAt(0).toLocaleUpperCase("vi-VN");
}

export function Avatar({ name, className }: { name: string; className: string }) {
  return (
    <span className={className} aria-hidden="true">
      {initialOf(name)}
    </span>
  );
}

/** Nhãn nhóm nhẹ. `group-tag` là móc e2e. */
export function GroupTags({ groups }: { groups: string[] }) {
  if (!groups.length) return <span className={s.none}>Chưa có nhóm</span>;
  return (
    <span className={`tags ${s.tags}`}>
      {groups.map((g) => (
        <span key={g} className="tag group-tag">
          {groupLabel(g)}
        </span>
      ))}
    </span>
  );
}

/** Chấm + chữ (không chỉ dựa vào màu): đang làm = chấm đặc xanh lá, đã nghỉ = vòng rỗng xám (`.status` chung). */
export function StatusLine({ active }: { active: boolean }) {
  return (
    <span className={`status ${active ? "good" : "mute"} ${s.statusLine}`}>
      <span className="dot" aria-hidden="true" />
      {active ? STAFF_MSG.statusActive : STAFF_MSG.statusInactive}
    </span>
  );
}

/** Lỗi nghiệp vụ BE, hiện NGUYÊN VĂN, đặt ngay trên nút thao tác; hiện ra thì cuộn tới cho thấy. */
export function ErrorLine({ error }: { error: string | null }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error) ref.current?.scrollIntoView({ block: "nearest" });
  }, [error]);
  if (!error) return null;
  return (
    <div className="alert-box err" role="alert" ref={ref}>
      <Icon name="error" />
      <span>{error}</span>
    </div>
  );
}

/**
 * Khi `key` đổi (đổi chế độ trong tấm bên), chuyển focus vào phần tử `[data-autofocus]` của chế độ mới, không có thì
 * vào chính khung. Lần render đầu bỏ qua (shared/ui/Sheet đã tự focus khi mở).
 */
export function useFocusOnSwap(key: string) {
  const ref = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const el = ref.current?.querySelector<HTMLElement>("[data-autofocus]");
    (el || ref.current)?.focus({ preventScroll: false });
  }, [key]);
  return ref;
}

type ConfirmProps = {
  /** crit: mất quyền/khoá tài khoản; warn: trao thêm quyền lớn. Nút xác nhận luôn màu crit. */
  tone: "crit" | "warn";
  icon: string;
  title: string;
  children: React.ReactNode;
  error: string | null;
  busy: boolean;
  cancelLabel: string;
  onCancel: () => void;
  confirmLabel: string;
  onConfirm: () => void;
};

/**
 * Xác nhận thao tác nguy hiểm: tiêu đề câu hỏi, hậu quả rõ, nút an toàn được focus trước (Enter không vô tình xác nhận),
 * nút xác nhận màu crit. `confirm-danger` là móc e2e.
 */
export function DangerConfirm({ tone, icon, title, children, error, busy, cancelLabel, onCancel, confirmLabel, onConfirm }: ConfirmProps) {
  const id = useId();
  return (
    <>
      <div
        className={`confirm-danger ${s.confirm}${tone === "warn" ? ` ${s.confirmWarn}` : ""}`}
        role="group"
        aria-labelledby={`${id}-t`}
        aria-describedby={`${id}-d`}
      >
        <span className={s.confirmIcon} aria-hidden="true">
          <Icon name={icon} />
        </span>
        <h3 id={`${id}-t`}>{title}</h3>
        <div id={`${id}-d`} className={s.confirm}>
          {children}
        </div>
      </div>
      <ErrorLine error={error} />
      <div className={`form-actions ${s.footer}`}>
        <button type="button" className="btn" onClick={onCancel} disabled={busy} data-autofocus aria-describedby={`${id}-d`}>
          {cancelLabel}
        </button>
        <button type="button" className="btn danger solid" onClick={onConfirm} disabled={busy} aria-busy={busy || undefined}>
          {busy && <Icon name="progress_activity" className="spin" />}
          {confirmLabel}
        </button>
      </div>
    </>
  );
}

/** Một dòng hậu quả trong khung xác nhận. */
export function Consequence({ icon, children }: { icon: string; children: React.ReactNode }) {
  return (
    <li>
      <Icon name={icon} />
      <span>{children}</span>
    </li>
  );
}

/**
 * Thông tin đăng nhập để Chủ đọc/gửi cho nhân viên (tạo xong, đặt lại mật khẩu xong). Mỗi dòng có nút chép riêng;
 * có tên đăng nhập thì thêm "Chép cả hai". `cred-username` / `cred-password` là móc e2e.
 */
export function Credentials({ username, password, passwordLabel }: { username?: string; password: string; passwordLabel: string }) {
  const lower = `${passwordLabel.charAt(0).toLowerCase()}${passwordLabel.slice(1)}`;
  return (
    <>
      <div className={s.cred}>
        {username && (
          <div className={s.credRow}>
            <div>
              <span className={s.credLabel}>Tên đăng nhập</span>
              <code className={`${s.credValue} cred-username`}>{username}</code>
            </div>
            <CopyButton value={username} what="tên đăng nhập" label="Chép" />
          </div>
        )}
        <div className={s.credRow}>
          <div>
            <span className={s.credLabel}>{passwordLabel}</span>
            <code className={`${s.credValue} cred-password`}>{password}</code>
          </div>
          <CopyButton value={password} what={lower} label="Chép" />
        </div>
      </div>
      {username && (
        <div>
          <CopyButton
            value={`Tên đăng nhập: ${username}\n${passwordLabel}: ${password}`}
            what={`tên đăng nhập và ${lower}`}
            label="Chép cả hai"
          />
        </div>
      )}
    </>
  );
}
