"use client";

// Bọc các trang /ai/*: cờ AI tắt (SR-HIDE-AI-01) → hiện "Không tìm thấy trang này" (NotFoundScreen, SR-HIDE-AI-02) và KHÔNG mount màn AI,
// nên không có request /api/ai/* nào được gọi. Cờ bật → hiện đúng như cũ.
import { AI_FEATURES_ENABLED } from "@/shared/lib/features";
import { homePath } from "@/shared/lib/nav";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { NotFoundScreen } from "./NotFoundScreen";

export function AiFeatureGuard({ children }: { children: React.ReactNode }) {
  const { me } = useAuth();
  if (!AI_FEATURES_ENABLED) return <NotFoundScreen homeHref={me ? homePath(me) : "/overview/"} />;
  return <>{children}</>;
}
