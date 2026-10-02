"use client";

// Mảnh giao diện dùng chung trong module Nhân sự: nhãn nhóm, dòng hậu quả, khối thông tin đăng nhập (tạo xong / đặt lại mật khẩu).

import { groupLabel } from "@/shared/lib/groups";
import { Icon } from "@/shared/ui/Icon";
import { CopyButton } from "./CopyButton";
import s from "../staff.module.css";

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

/** Một dòng hậu quả trong hộp xác nhận. */
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
 * Mật khẩu chỉ nằm trong state của hộp, không vào storage/URL/log.
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
