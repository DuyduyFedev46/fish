"use client";

// "/" chỉ điều hướng: chưa đăng nhập → /login/, đã đăng nhập → trang mặc định theo `me.home`.
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loading } from "@/shared/ui/StateBox";
import { homePath } from "@/shared/lib/nav";
import { useAuth } from "./AuthProvider";

export function RootRedirect() {
  const { status, me } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "anon" || status === "error") router.replace("/login/");
    else if (status === "ready" && me) router.replace(homePath(me));
  }, [status, me, router]);

  return (
    <div className="fullscreen">
      <Loading label="Đang mở console…" />
    </div>
  );
}
