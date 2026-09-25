"use client";

// S48: màn "Đặt mật khẩu mới" — màn DUY NHẤT mở được khi `me.must_change_password` (tài khoản vừa được Chủ tạo hoặc
// đặt lại mật khẩu). Không có menu. Đổi xong (POST /api/auth/change-password/ của S46) → `me` tải lại, cờ tắt → vào
// home theo vai; câu xác nhận "Đã đặt mật khẩu mới" hiện ở đầu màn home (AuthProvider.passwordNotice → ConsoleGate),
// vì màn này rời đi ngay khi cờ tắt (code review trước deploy 1). Chưa đăng nhập → về đăng nhập; không bị ép → về home.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/shared/ui/Icon";
import { Loading } from "@/shared/ui/StateBox";
import { homePath } from "@/shared/lib/nav";
import { MSG } from "@/shared/lib/messages";
import { useAuth } from "./AuthProvider";
import { ChangePasswordForm } from "./ChangePasswordForm";

export function SetPasswordScreen() {
  const { status, me, logout } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "anon" || status === "error") router.replace("/login/");
    else if (status === "ready" && me && !me.must_change_password) router.replace(homePath(me));
  }, [status, me, router]);

  if (status !== "ready" || !me || !me.must_change_password) {
    return (
      <div className="fullscreen">
        <Loading />
      </div>
    );
  }

  return (
    <main className="login setpw">
      <div className="card">
        <div className="lg">
          <div className="mark">
            <Icon name="set_meal" />
          </div>
          <div>
            <b>Cá Về</b>
            <small>Vận hành</small>
          </div>
        </div>
        <h1>{MSG.mustChangeTitle}</h1>
        <p>
          Xin chào <b>{me.display_name || me.username}</b> ({me.username}). {MSG.mustChangeIntro}
        </p>
        {/* Xác nhận thành công hiện ở màn home (ConsoleGate) — màn này tự rời đi khi cờ tắt. */}
        <ChangePasswordForm mustChange onDone={() => undefined} />
        <div className="hint">
          Không phải bạn?{" "}
          <button
            type="button"
            className="inline-link"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              await logout();
            }}
          >
            Đăng xuất
          </button>
        </div>
      </div>
    </main>
  );
}
