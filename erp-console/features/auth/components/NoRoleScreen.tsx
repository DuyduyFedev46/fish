"use client";

// S7-AC5 / S47-AC5 + D-3 (Duy 08/10): tài khoản không thuộc Group nào và không phải superuser → không có menu, không có trợ lý;
// BE cũng chặn mọi API ERP bằng 403 AUTH_NO_ROLE.
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/shared/ui/Icon";
import { Loading } from "@/shared/ui/StateBox";
import { homePath } from "@/shared/lib/nav";
import { useAuth } from "./AuthProvider";

export function NoRoleScreen() {
  const { status, me, logout } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "anon" || status === "error") router.replace("/login/");
    else if (status === "ready" && me && (me.home !== "no-role" || me.must_change_password)) router.replace(homePath(me));
  }, [status, me, router]);

  if (status !== "ready" || !me || me.home !== "no-role" || me.must_change_password) {
    return (
      <div className="fullscreen">
        <Loading />
      </div>
    );
  }

  return (
    <main className="login">
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
        <div className="auth-icon" aria-hidden="true">
          <Icon name="person_off" />
        </div>
        <h1>Bạn không có quyền vào hệ thống vận hành</h1>
        <p>
          Tài khoản <b>{me.username}</b> chưa thuộc nhóm nào nên không vào được hệ thống vận hành. Nhờ Chủ vựa xếp nhóm cho tài khoản này.
        </p>
        <div className="auth-actions">
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              await logout();
            }}
          >
            <Icon name={busy ? "progress_activity" : "logout"} className={busy ? "spin" : undefined} />
            {busy ? "Đang đăng xuất…" : "Đăng xuất"}
          </button>
        </div>
      </div>
    </main>
  );
}
