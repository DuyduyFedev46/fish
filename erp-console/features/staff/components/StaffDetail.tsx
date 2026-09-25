"use client";

// Chi tiết một nhân viên + các thao tác S41/S42, trong tấm bên (UI4: phải trên máy tính, trượt đáy trên điện thoại).
// Nút CHỈ hiện theo `available_actions` BE trả (FE không tự suy luật). Lỗi BE (BR-PQ-17/18, BR-GH-08, BR-PQ-01,
// BR-PQ-08) hiện NGUYÊN VĂN ngay trên nút thao tác. Thao tác nguy hiểm (cho nghỉ, thêm/bỏ nhóm Chủ) phải xác nhận
// trước, nêu rõ hậu quả, nút xác nhận màu crit. Tiêu đề tấm đổi theo bước đang làm.

import { useState } from "react";
import Link from "next/link";
import { SideSheet } from "@/shared/ui/SideSheet";
import { ApiError } from "@/shared/lib/http";
import { dateTime } from "@/shared/lib/format";
import { groupLabel } from "@/shared/lib/groups";
import { ACCOUNT_HREF, GROUP } from "@/shared/lib/nav";
import { Icon } from "@/shared/ui/Icon";
import { deactivateStaff, reactivateStaff, resetStaffPassword, setStaffGroups, updateStaff } from "../api";
import type { StaffAction, StaffMember } from "../types";
import { GroupPicker } from "./GroupPicker";
import { PasswordField } from "./PasswordField";
import { Avatar, Consequence, Credentials, DangerConfirm, ErrorLine, GroupTags, StatusLine, useFocusOnSwap } from "./parts";
import { errorText } from "@/shared/lib/messages";
import { STAFF_MSG } from "../messages";
import s from "../staff.module.css";

type Mode = "view" | "edit" | "groups" | "groups-confirm" | "reset" | "reset-done" | "deactivate" | "reactivate";

type Props = {
  member: StaffMember;
  isSelf: boolean;
  /** Thao tác xong: `message` hiện thành thông báo nổi ở màn danh sách (danh sách tải lại). */
  onChanged: (message: string) => void;
  /** Tấm đã đóng hẳn (sau chuyển động ra). */
  onClose: () => void;
};

const ACTION_UI: Record<StaffAction, { label: string; icon: string; mode: Mode; danger?: boolean }> = {
  edit: { label: "Sửa hồ sơ", icon: "edit", mode: "edit" },
  set_groups: { label: "Đổi nhóm", icon: "group", mode: "groups" },
  reset_password: { label: "Đặt lại mật khẩu", icon: "key", mode: "reset" },
  reactivate: { label: "Cho làm lại", icon: "person_check", mode: "reactivate" },
  deactivate: { label: "Cho nghỉ", icon: "person_off", mode: "deactivate", danger: true },
};
const ACTION_ORDER: StaffAction[] = ["edit", "set_groups", "reset_password", "reactivate", "deactivate"];

function names(codes: string[]): string {
  return codes.map(groupLabel).join(", ");
}

export function StaffDetail({ member: m, isSelf, onChanged, onClose }: Props) {
  const [mode, setMode] = useState<Mode>("view");
  const [from, setFrom] = useState<Mode | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState(m.display_name);
  const [phone, setPhone] = useState(m.phone);
  const [groups, setGroups] = useState<string[]>(m.groups);
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const [missing, setMissing] = useState<"main" | "again" | null>(null);
  const swapRef = useFocusOnSwap(mode);
  const displayName = m.display_name || m.username;
  const who = m.display_name && m.display_name !== m.username ? `${m.display_name} (${m.username})` : m.username;

  const go = (next: Mode) => {
    setError(null);
    if (next === "view") setFrom(mode);
    setMode(next);
  };

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) {
        setError(errorText(err));
      }
    } finally {
      setBusy(false);
    }
  };

  const added = groups.filter((g) => !m.groups.includes(g));
  const removed = m.groups.filter((g) => !groups.includes(g));
  const addsChu = added.includes(GROUP.chu);
  const touchesChu = addsChu || removed.includes(GROUP.chu);

  const title: Record<Mode, string> = {
    view: displayName,
    edit: `Sửa hồ sơ · ${displayName}`,
    groups: `Đổi nhóm · ${displayName}`,
    "groups-confirm": `Đổi nhóm · ${displayName}`,
    reset: `Đặt lại mật khẩu · ${displayName}`,
    "reset-done": `Đặt lại mật khẩu · ${displayName}`,
    deactivate: `Cho nghỉ · ${displayName}`,
    reactivate: `Cho làm lại · ${displayName}`,
  };

  const body = (close: () => void) => {
    const saveGroups = () =>
      run(async () => {
        const r = await setStaffGroups(m.id, groups);
        onChanged(STAFF_MSG.groupsChanged(who, names(r.added), names(r.removed)));
        close();
      });

    // ---------- Sửa hồ sơ ----------
    if (mode === "edit") {
      return (
        <form
          className={s.pane}
          noValidate
          aria-label="Sửa hồ sơ"
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              await updateStaff(m.id, { display_name: name.trim(), phone: phone.trim() });
              onChanged(STAFF_MSG.profileSaved(m.username));
              close();
            });
          }}
        >
          <p className={s.readonly}>
            Tên đăng nhập <code>{m.username}</code> không đổi được.
          </p>
          <div className="field">
            <label htmlFor="se-name">Tên hiển thị</label>
            <input id="se-name" data-autofocus value={name} onChange={(e) => setName(e.target.value)} disabled={busy} />
          </div>
          <div className="field">
            <label htmlFor="se-phone">
              Số điện thoại
              <span className={s.req} aria-hidden="true">
                *
              </span>
            </label>
            <input
              id="se-phone"
              type="tel"
              inputMode="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={busy}
              required
            />
          </div>
          <ErrorLine error={error} />
          <div className={`form-actions ${s.footer}`}>
            <button type="button" className="btn" onClick={() => go("view")} disabled={busy}>
              Quay lại
            </button>
            <button type="submit" className="btn primary" disabled={busy} aria-busy={busy || undefined}>
              {busy && <Icon name="progress_activity" className="spin" />}
              Lưu hồ sơ
            </button>
          </div>
        </form>
      );
    }

    // ---------- Đổi nhóm ----------
    if (mode === "groups") {
      const unchanged = !added.length && !removed.length;
      return (
        <form
          className={s.pane}
          noValidate
          aria-label="Đổi nhóm"
          onSubmit={(e) => {
            e.preventDefault();
            if (touchesChu) go("groups-confirm");
            else void saveGroups();
          }}
        >
          <GroupPicker value={groups} onChange={setGroups} disabled={busy} legend={`Nhóm của ${who}`} autoFocus />
          <div className={s.diff} aria-live="polite">
            {unchanged ? (
              <span>Chưa đổi gì.</span>
            ) : (
              <>
                {added.length > 0 && (
                  <span>
                    Thêm: <b>{names(added)}</b>
                  </span>
                )}
                {removed.length > 0 && (
                  <span>
                    Bỏ: <b>{names(removed)}</b>
                  </span>
                )}
              </>
            )}
          </div>
          {groups.length === 0 && (
            <p className="help">Bỏ hết nhóm: người này đăng nhập được nhưng không dùng được mục nào.</p>
          )}
          <p className="help">
            Đổi nhóm không làm đổi chứng từ cũ. Người này thấy quyền mới ở lần mở app kế tiếp, không cần đăng nhập lại.
          </p>
          <ErrorLine error={error} />
          <div className={`form-actions ${s.footer}`}>
            <button type="button" className="btn" onClick={() => go("view")} disabled={busy}>
              Quay lại
            </button>
            <button
              type="submit"
              className="btn primary"
              disabled={busy || unchanged}
              aria-busy={busy || undefined}
              title={unchanged ? "Chọn hoặc bỏ ít nhất một nhóm để lưu" : undefined}
            >
              {busy && <Icon name="progress_activity" className="spin" />}
              Lưu nhóm
            </button>
          </div>
        </form>
      );
    }

    // ---------- Xác nhận thêm / bỏ nhóm Chủ ----------
    if (mode === "groups-confirm") {
      return (
        <div className={s.pane}>
          <DangerConfirm
            tone={addsChu ? "warn" : "crit"}
            icon={addsChu ? "shield_person" : "remove_moderator"}
            title={addsChu ? "Cấp quyền Chủ?" : "Gỡ quyền Chủ?"}
            error={error}
            busy={busy}
            cancelLabel="Quay lại"
            onCancel={() => go("groups")}
            confirmLabel={addsChu ? "Thêm nhóm Chủ" : "Bỏ nhóm Chủ"}
            onConfirm={() => void saveGroups()}
          >
            {addsChu ? (
              <p>
                Bạn sắp <b>thêm nhóm Chủ</b> cho {who}. Nhóm Chủ có toàn quyền: tiền, giá vốn, lãi lỗ và quản lý nhân
                viên.
              </p>
            ) : (
              <p>
                Bạn sắp <b>bỏ nhóm Chủ</b> của {who}. Người này mất quyền tiền, giá vốn, lãi lỗ và quản lý nhân viên.
              </p>
            )}
          </DangerConfirm>
        </div>
      );
    }

    // ---------- Đặt lại mật khẩu ----------
    if (mode === "reset") {
      return (
        <form
          className={s.pane}
          noValidate
          aria-label="Đặt lại mật khẩu"
          onSubmit={(e) => {
            e.preventDefault();
            // UI5: nút không bị tắt khi thiếu ô — báo tại ô trống đầu tiên và đưa focus vào đó.
            const empty = !password ? "main" : !again ? "again" : null;
            setMissing(empty);
            if (empty) {
              document.getElementById(empty === "main" ? "sr-password" : "sr-password-again")?.focus();
              return;
            }
            if (password !== again) {
              setError(null);
              setMismatch(true); // S48-AC3: không gọi API
              return;
            }
            void run(async () => {
              await resetStaffPassword(m.id, password);
              setMode("reset-done");
              onChanged(STAFF_MSG.passwordReset(who));
            });
          }}
        >
          <div className="alert-box info">
            <Icon name="info" />
            <span>
              Máy nào đang đăng nhập tài khoản <b>{m.username}</b> sẽ bị đăng xuất ở lần thao tác kế tiếp.
            </span>
          </div>
          <PasswordField
            id="sr-password"
            label="Mật khẩu mới"
            autoFocus
            value={password}
            onChange={(v) => {
              setPassword(v);
              setMismatch(false);
              if (missing === "main") setMissing(null);
            }}
            again={again}
            onAgainChange={(v) => {
              setAgain(v);
              setMismatch(false);
              if (missing === "again") setMissing(null);
            }}
            mismatch={mismatch}
            missing={missing}
            username={m.username}
            disabled={busy}
          />
          <ErrorLine error={error} />
          <div className={`form-actions ${s.footer}`}>
            <button type="button" className="btn" onClick={() => go("view")} disabled={busy}>
              Quay lại
            </button>
            <button
              type="submit"
              className="btn primary"
              disabled={busy}
              aria-busy={busy || undefined}
            >
              {busy && <Icon name="progress_activity" className="spin" />}
              Đặt lại mật khẩu
            </button>
          </div>
        </form>
      );
    }

    if (mode === "reset-done") {
      return (
        <div className={s.pane}>
          <div className={s.success} role="status">
            <span className={s.successIcon} aria-hidden="true">
              <Icon name="check" />
            </span>
            <h3>Đã đặt lại mật khẩu cho {who}</h3>
            <p>Đọc hoặc gửi mật khẩu dưới đây cho nhân viên.</p>
          </div>
          <Credentials password={password} passwordLabel="Mật khẩu mới" />
          <div className={`form-actions ${s.footer}`}>
            <button type="button" className="btn primary" onClick={close} data-autofocus>
              Xong
            </button>
          </div>
        </div>
      );
    }

    // ---------- Cho nghỉ ----------
    if (mode === "deactivate") {
      return (
        <div className={s.pane}>
          <DangerConfirm
            tone="crit"
            icon="person_off"
            title={`Cho ${who} nghỉ?`}
            error={error}
            busy={busy}
            cancelLabel="Thôi"
            onCancel={() => go("view")}
            confirmLabel="Cho nghỉ"
            onConfirm={() =>
              void run(async () => {
                await deactivateStaff(m.id);
                onChanged(STAFF_MSG.deactivated(who));
                close();
              })
            }
          >
            <ul className={s.consequences}>
              <Consequence icon="lock">Tài khoản bị khoá ngay và bị đăng xuất khỏi mọi máy.</Consequence>
              <Consequence icon="description">Chứng từ cũ vẫn giữ tên người này.</Consequence>
              <Consequence icon="undo">Có thể cho làm lại sau.</Consequence>
            </ul>
          </DangerConfirm>
        </div>
      );
    }

    // ---------- Cho làm lại (không nguy hiểm) ----------
    if (mode === "reactivate") {
      return (
        <div className={s.pane}>
          <p className={s.lead}>
            Cho <b>{who}</b> làm lại? Người này đăng nhập lại bằng mật khẩu cũ (hoặc đặt lại mật khẩu sau).
          </p>
          <ErrorLine error={error} />
          <div className={`form-actions ${s.footer}`}>
            <button type="button" className="btn" onClick={() => go("view")} disabled={busy} data-autofocus>
              Thôi
            </button>
            <button
              type="button"
              className="btn primary"
              disabled={busy}
              aria-busy={busy || undefined}
              onClick={() =>
                void run(async () => {
                  await reactivateStaff(m.id);
                  onChanged(STAFF_MSG.reactivated(who));
                  close();
                })
              }
            >
              {busy && <Icon name="progress_activity" className="spin" />}
              Cho làm lại
            </button>
          </div>
        </div>
      );
    }

    // ---------- Xem ----------
    const actions = ACTION_ORDER.filter((a) => m.available_actions.includes(a));
    const normal = actions.filter((a) => !ACTION_UI[a].danger);
    const danger = actions.filter((a) => ACTION_UI[a].danger);
    const start = (a: StaffAction) => {
      setGroups(m.groups);
      setName(m.display_name);
      setPhone(m.phone);
      setPassword("");
      setAgain("");
      setMismatch(false);
      setMissing(null);
      go(ACTION_UI[a].mode);
    };
    const actionBtn = (a: StaffAction) => {
      const ui = ACTION_UI[a];
      return (
        <button
          key={a}
          type="button"
          className={`${s.action}${ui.danger ? ` ${s.actionDanger}` : ""}`}
          onClick={() => start(a)}
          data-autofocus={from === ui.mode ? true : undefined}
        >
          <Icon name={ui.icon} />
          {ui.label}
        </button>
      );
    };
    return (
      <div className={s.pane}>
        <div className={s.profile}>
          <Avatar name={displayName} className={s.avatarLg} />
          <div className={s.profileText}>
            <code>{m.username}</code>
            <span className={s.status}>
              <StatusLine active={m.is_active} />
            </span>
          </div>
        </div>

        <dl className={s.props}>
          <div className={s.prop}>
            <dt>Số điện thoại</dt>
            <dd>
              {m.phone ? (
                <a className={s.tel} href={`tel:${m.phone}`}>
                  {m.phone}
                </a>
              ) : (
                <span className={s.muted}>Chưa có</span>
              )}
            </dd>
          </div>
          <div className={s.prop}>
            <dt>Nhóm</dt>
            <dd>
              <GroupTags groups={m.groups} />
            </dd>
          </div>
          <div className={s.prop}>
            <dt>Đăng nhập gần nhất</dt>
            <dd className={m.last_login ? "num" : s.muted}>{m.last_login ? dateTime(m.last_login) : STAFF_MSG.neverLoggedIn}</dd>
          </div>
        </dl>

        {actions.length > 0 ? (
          <div className={`${s.actions} staff-actions`}>
            {normal.length > 0 && <div className={s.actionGroup}>{normal.map(actionBtn)}</div>}
            {danger.length > 0 && (
              <>
                <div className={s.actionGroup}>{danger.map(actionBtn)}</div>
                <p className={s.dangerNote}>Khoá tài khoản và đăng xuất khỏi mọi máy. Có thể cho làm lại sau.</p>
              </>
            )}
          </div>
        ) : (
          <p className="help">{STAFF_MSG.noActions}</p>
        )}
        {isSelf && (
          <p className="help">
            Đây là tài khoản của bạn. Đổi mật khẩu ở <Link href={ACCOUNT_HREF}>Tài khoản của tôi</Link>.
          </p>
        )}
      </div>
    );
  };

  return (
    <SideSheet title={title[mode]} onClose={onClose} busy={busy}>
      {(close) => (
        <div className={s.swap} ref={swapRef} tabIndex={-1} key={mode}>
          {body(close)}
        </div>
      )}
    </SideSheet>
  );
}
