"use client";

// S47 "Quyền của tôi" + S46 (đổi mật khẩu, đăng xuất). Mọi dữ liệu lấy từ `me` (/api/auth/me/): nhóm
// (`group_labels`), việc được làm (`capabilities` — quyền Tầng 2), xem giá vốn / lãi lỗ. FE không tự suy quyền.
// Mục menu thấy được lấy từ bảng menu ↔ quyền (shared/lib/nav.ts) để người dùng hiểu vì sao thấy/không thấy.
// UI4: trang một cột kiểu trang cài đặt (Linear/Notion) — đầu trang người dùng, rồi từng phần tiêu đề + nhóm hàng;
// đổi mật khẩu trong tấm bên; kết quả báo bằng thông báo nổi.

import { useState } from "react";
import { groupLabel } from "@/shared/lib/groups";
import { visibleNav } from "@/shared/lib/nav";
import { Icon } from "@/shared/ui/Icon";
import { Loading } from "@/shared/ui/StateBox";
import { useAuth } from "./AuthProvider";
import { ChangePasswordForm } from "./ChangePasswordForm";
import { SideSheet } from "@/shared/ui/SideSheet";
import { Toast } from "@/shared/ui/Toast";
import { MSG } from "@/shared/lib/messages";
import s from "./account.module.css";

function YesNo({ value }: { value: boolean }) {
  return (
    <span className={`status ${value ? "good" : "mute"}`}>
      <span className="dot" aria-hidden="true" />
      {value ? "Có" : "Không"}
    </span>
  );
}

export function AccountScreen() {
  const { me, logout, refreshMe } = useAuth();
  const [pwOpen, setPwOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState<"logout" | "refresh" | null>(null);

  if (!me) return <Loading />;

  const name = me.display_name || me.username || "?";
  const groups = me.group_labels?.length
    ? me.group_labels
    : me.groups.map((g) => ({ code: g, label: groupLabel(g) }));
  const menu = visibleNav(me);

  return (
    <div className={`screen account ${s.page}`}>
      <section className={`who-card ${s.head}`} aria-labelledby="acc-who">
        <div className="avatar big" aria-hidden="true">
          {name.charAt(0).toUpperCase()}
        </div>
        <div className={s.headText}>
          <h2 id="acc-who">{name}</h2>
          <div className={s.meta}>
            <code>{me.username}</code>
            {me.phone ? (
              <a className={s.tel} href={`tel:${me.phone}`}>
                <Icon name="call" />
                {me.phone}
              </a>
            ) : (
              <span>Chưa có số điện thoại</span>
            )}
          </div>
          <div className="tags" aria-label="Nhóm của bạn">
            {groups.map((g) => (
              <span key={g.code} className="tag group-tag">
                {g.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className={s.section} aria-labelledby="acc-cap">
        <div className={s.sectionHead}>
          <h2 id="acc-cap">Việc bạn được làm</h2>
          <p>Quyền duyệt, chốt và tiền mà nhóm của bạn có.</p>
        </div>
        <div className={s.group}>
          {me.capabilities === undefined ? (
            <p className={s.empty}>Máy chủ chưa trả danh sách này (cần bản backend có S47).</p>
          ) : me.capabilities.length ? (
            <ul className={`cap-list ${s.caps}`}>
              {me.capabilities.map((c) => (
                <li key={c.code}>
                  <Icon name="check_circle" />
                  {c.label}
                </li>
              ))}
            </ul>
          ) : (
            <p className={s.empty}>
              Bạn chưa có quyền duyệt/chốt nào. Bạn vẫn làm được việc hằng ngày của nhóm mình trong các mục ở menu.
            </p>
          )}
          <dl className={`perm-yn ${s.yn}`}>
            <div className={s.ynRow}>
              <dt>Xem giá vốn</dt>
              <dd>
                <YesNo value={me.can_view_cost} />
              </dd>
            </div>
            <div className={s.ynRow}>
              <dt>Xem báo cáo lãi lỗ</dt>
              <dd>
                <YesNo value={me.can_view_profit} />
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className={s.section} aria-labelledby="acc-menu">
        <div className={s.sectionHead}>
          <h2 id="acc-menu">Mục bạn thấy trên menu</h2>
          <p>Thiếu mục hay nút cần dùng? Nhờ Chủ thêm nhóm cho bạn.</p>
        </div>
        <div className={s.group}>
          <ul className={s.menu}>
            {menu.map((n) => (
              <li key={n.key}>
                <Icon name={n.icon} />
                {n.label}
              </li>
            ))}
          </ul>
          <div className={s.menuFoot}>
            <p>Quyền đổi thì console tự cập nhật khi bạn mở lại app hoặc quay lại sau 5 phút.</p>
            <button
              type="button"
              className="btn"
              disabled={busy !== null}
              aria-busy={busy === "refresh" || undefined}
              onClick={async () => {
                setBusy("refresh");
                await refreshMe();
                setBusy(null);
                setToast(MSG.permsReloaded);
              }}
            >
              <Icon name={busy === "refresh" ? "progress_activity" : "sync"} className={busy === "refresh" ? "spin" : undefined} />
              Tải lại quyền
            </button>
          </div>
        </div>
      </section>

      <section className={s.section} aria-labelledby="acc-sec">
        <div className={s.sectionHead}>
          <h2 id="acc-sec">Mật khẩu và đăng xuất</h2>
          <p>Mỗi tài khoản chỉ có một phiên.</p>
        </div>
        <div className={s.group}>
          <div className={s.setting}>
            <span className={s.settingIcon} aria-hidden="true">
              <Icon name="key" />
            </span>
            <div className={s.settingText}>
              <b>Mật khẩu</b>
              <span>Đổi mật khẩu ở máy này thì các máy khác đang đăng nhập tài khoản của bạn bị đăng xuất.</span>
            </div>
            <button type="button" className="btn" onClick={() => setPwOpen(true)} disabled={busy !== null} aria-haspopup="dialog">
              Đổi mật khẩu
            </button>
          </div>
          <div className={s.setting}>
            <span className={`${s.settingIcon} ${s.dangerIcon}`} aria-hidden="true">
              <Icon name="logout" />
            </span>
            <div className={s.settingText}>
              <b>Đăng xuất</b>
              <span>Đăng xuất ở máy này thì các máy khác đang đăng nhập tài khoản của bạn cũng bị đăng xuất.</span>
            </div>
            <button
              type="button"
              className="btn danger"
              disabled={busy !== null}
              aria-busy={busy === "logout" || undefined}
              onClick={async () => {
                setBusy("logout");
                await logout();
              }}
            >
              {busy === "logout" && <Icon name="progress_activity" className="spin" />}
              {busy === "logout" ? "Đang đăng xuất…" : "Đăng xuất"}
            </button>
          </div>
        </div>
      </section>

      {pwOpen && (
        <SideSheet title="Đổi mật khẩu" onClose={() => setPwOpen(false)}>
          {(close) => (
            <ChangePasswordForm
              onDone={(msg) => {
                setToast(msg);
                close();
              }}
            />
          )}
        </SideSheet>
      )}

      {toast && !pwOpen && <Toast key={toast} message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
