"use client";

// Tài khoản của tôi (ED-06 / W4e; gồm S47 "Quyền của tôi" + S46 đổi mật khẩu, đăng xuất). Mọi dữ liệu lấy từ `me`
// (/api/auth/me/): nhóm (`group_labels`), việc được làm (`capabilities` — quyền Tầng 2), xem giá vốn / lãi lỗ. FE không tự suy quyền.
// Mục menu thấy được lấy từ bảng menu ↔ quyền (shared/lib/nav.ts) để người dùng hiểu vì sao thấy/không thấy.
// Trang một cột kiểu trang cài đặt (Linear/Notion): đầu trang người dùng + 3 hàng thông tin, rồi từng phần tiêu đề + nhóm hàng.
// "Phiên đăng nhập": BE chưa có danh sách phiên, FE chỉ nhớ MỐC GIỜ đăng nhập ở máy này (signedInAt.ts, không có dữ liệu cá nhân).
// Đổi mật khẩu trong tấm bên (đang gửi thì không đóng được); kết quả báo bằng thông báo nổi.

import Link from "next/link";
import { useEffect, useState } from "react";
import { dateTime } from "@/shared/lib/format";
import { groupLabel } from "@/shared/lib/groups";
import { AI_SETTINGS_HREF, canView, visibleNav } from "@/shared/lib/nav";
import { MSG } from "@/shared/lib/messages";
import { Icon } from "@/shared/ui/Icon";
import { SideSheet } from "@/shared/ui/SideSheet";
import { useToast } from "@/shared/ui/overlay/Toast";
import { Loading } from "@/shared/ui/StateBox";
import { forgetSignedIn, readSignedIn } from "../signedInAt";
import { useAuth } from "./AuthProvider";
import { ChangePasswordForm } from "./ChangePasswordForm";
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
  const toast = useToast();
  const [pwOpen, setPwOpen] = useState(false);
  const [pwBusy, setPwBusy] = useState(false);
  const [busy, setBusy] = useState<"logout" | "refresh" | null>(null);
  // Đọc sau khi mount (trang xuất tĩnh, localStorage chỉ có ở trình duyệt).
  const [signedIn, setSignedIn] = useState<string | null>(null);
  useEffect(() => setSignedIn(readSignedIn()), []);

  if (!me) return <Loading />;

  const name = me.display_name || me.username || "?";
  const groups = me.group_labels?.length
    ? me.group_labels
    : me.groups.map((g) => ({ code: g, label: groupLabel(g) }));
  const menu = visibleNav(me);
  const aiSettings = canView(me, "ai-settings");

  const reloadPerms = async () => {
    setBusy("refresh");
    try {
      await refreshMe();
      toast.success(MSG.permsReloaded);
    } finally {
      setBusy(null);
    }
  };

  const doLogout = async () => {
    setBusy("logout");
    forgetSignedIn();
    await logout();
  };

  return (
    <div className={`screen account ${s.page}`}>
      <section className={`who-card ${s.head}`} aria-labelledby="acc-who">
        <div className="avatar big" aria-hidden="true">
          {name.charAt(0).toUpperCase()}
        </div>
        <div className={s.headText}>
          <h2 id="acc-who">{name}</h2>
        </div>
        <dl className={s.info}>
          <div className={s.infoRow}>
            <dt>Tên đăng nhập</dt>
            <dd>
              <code>{me.username}</code>
            </dd>
          </div>
          <div className={s.infoRow}>
            <dt>Số điện thoại</dt>
            <dd>
              {me.phone ? (
                <a className={s.tel} href={`tel:${me.phone}`}>
                  <Icon name="call" />
                  {me.phone}
                </a>
              ) : (
                <span className="muted">Chưa có</span>
              )}
            </dd>
          </div>
          <div className={s.infoRow}>
            <dt>Vai trò</dt>
            <dd>
              <span className="tags" aria-label="Nhóm của bạn">
                {groups.map((g) => (
                  <span key={g.code} className="tag group-tag">
                    {g.label}
                  </span>
                ))}
              </span>
            </dd>
          </div>
        </dl>
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
              onClick={() => void reloadPerms()}
            >
              <Icon name={busy === "refresh" ? "progress_activity" : "sync"} className={busy === "refresh" ? "spin" : undefined} />
              Tải lại quyền
            </button>
          </div>
        </div>
      </section>

      <section className={s.section} aria-labelledby="acc-sec">
        <div className={s.sectionHead}>
          <h2 id="acc-sec">Bảo mật và đăng nhập</h2>
          <p>Mỗi tài khoản chỉ có một phiên.</p>
        </div>
        <div className={s.group}>
          <div className={s.setting} data-row="session">
            <span className={s.settingIcon} aria-hidden="true">
              <Icon name="schedule" />
            </span>
            <div className={s.settingText}>
              <b>Phiên đăng nhập</b>
              <span>{signedIn ? `Đăng nhập từ ${dateTime(signedIn)}` : "Đang đăng nhập"}</span>
            </div>
            <span className="tag">Máy này</span>
          </div>
          <div className={s.setting} data-row="password">
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
          {aiSettings && (
            <div className={s.setting} data-row="ai">
              <span className={s.settingIcon} aria-hidden="true">
                <Icon name="auto_awesome" />
              </span>
              <div className={s.settingText}>
                <b>AI của tôi</b>
                <span>Bật tắt trợ lý AI và đặt hạn mức riêng của bạn.</span>
              </div>
              <Link href={AI_SETTINGS_HREF} className="btn">
                Mở cài đặt AI
              </Link>
            </div>
          )}
          <div className={s.setting} data-row="logout">
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
              onClick={() => void doLogout()}
            >
              {busy === "logout" && <Icon name="progress_activity" className="spin" />}
              {busy === "logout" ? "Đang đăng xuất…" : "Đăng xuất"}
            </button>
          </div>
        </div>
      </section>

      {pwOpen && (
        <SideSheet title="Đổi mật khẩu" busy={pwBusy} onClose={() => setPwOpen(false)}>
          {(close) => (
            <ChangePasswordForm
              onCancel={close}
              onBusyChange={setPwBusy}
              onDone={(msg) => {
                toast.success(msg);
                close();
              }}
            />
          )}
        </SideSheet>
      )}
    </div>
  );
}
