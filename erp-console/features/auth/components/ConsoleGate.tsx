"use client";

// Cổng vào mọi màn nghiệp vụ: phải đăng nhập, đã đặt mật khẩu riêng (S48) và có Group; rồi mới vẽ Shell (menu theo quyền).
// Đăng xuất nối vào menu avatar của Shell (không còn nút đăng xuất rời).
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Shell } from "@/shared/ui/shell/Shell";
import { Icon } from "@/shared/ui/Icon";
import { ErrorBox, Loading } from "@/shared/ui/StateBox";
import { groupLabel } from "@/shared/lib/groups";
import { ACCOUNT_HREF, SET_PASSWORD_HREF } from "@/shared/lib/nav";
import type { Me } from "../types";
import { useAuth } from "./AuthProvider";
import { MSG } from "@/shared/lib/messages";

/** Nhãn nhóm: ưu tiên `group_labels` BE trả (S47), không có thì dịch mã. */
export function roleText(me: Me): string {
  if (me.group_labels?.length) return me.group_labels.map((g) => g.label).join(" · ");
  return me.groups.map(groupLabel).join(" · ");
}

type Props = {
  children: React.ReactNode;
};

// Chỉ bản mock: nạp công cụ thử của module AI (window.__caveMock.ai / aiConsent) cho e2e và DevTools. Trước đây AiAssistantGate nạp
// giùm; Lô 1 bỏ gate nên nạp ở đây, ngay khi layout console được tải (sớm hơn mọi màn). Điều kiện viết nguyên văn để bản build thật
// cắt cả import này (check-no-mock).
if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") void import("@/features/ai/mock");

export function ConsoleGate({ children }: Props) {
  const { status, me, error, loggedOut, refreshMe, logout, permNotice, dismissPermNotice, passwordNotice, dismissPasswordNotice } =
    useAuth();
  const router = useRouter();
  const pathname = usePathname() || "/";

  useEffect(() => {
    // Mở thẳng một trang khi chưa đăng nhập → nhớ trang đó để quay lại. Vừa bấm Đăng xuất → không nhớ.
    if (status === "anon") router.replace(loggedOut ? "/login/" : `/login/?next=${encodeURIComponent(pathname)}`);
    else if (status === "ready" && me?.must_change_password) router.replace(SET_PASSWORD_HREF); // S48-AC1
    else if (status === "ready" && me?.home === "no-role") router.replace("/no-role/");
  }, [status, me, router, pathname, loggedOut]);

  if (status === "error") {
    return (
      <div className="fullscreen">
        <div className="fullscreen-stack">
          <ErrorBox message={error || MSG.meLoadFailed} onRetry={() => void refreshMe()} />
          <button type="button" className="btn" onClick={() => void logout()}>
            Đăng nhập tài khoản khác
          </button>
        </div>
      </div>
    );
  }

  if (status !== "ready" || !me || me.must_change_password || me.home === "no-role") {
    return (
      <div className="fullscreen">
        <Loading label="Đang kiểm tra đăng nhập…" />
      </div>
    );
  }

  return (
    <Shell
      viewer={me}
      userName={me.display_name || me.username}
      roleText={roleText(me)}
      onLogout={logout}
      accountHref={ACCOUNT_HREF}
    >
      {permNotice && (
        <div className="alert-box info perm-notice" role="status">
          <Icon name="manage_accounts" />
          <span>{permNotice}</span>
          <button type="button" className="iconbtn" aria-label="Đóng thông báo" onClick={dismissPermNotice}>
            <Icon name="close" />
          </button>
        </div>
      )}
      {passwordNotice && (
        <div className="alert-box ok pw-done-notice" role="status">
          <Icon name="check_circle" />
          <span>{passwordNotice}</span>
          <button type="button" className="iconbtn" aria-label="Đóng thông báo" onClick={dismissPasswordNotice}>
            <Icon name="close" />
          </button>
        </div>
      )}
      {children}
    </Shell>
  );
}
