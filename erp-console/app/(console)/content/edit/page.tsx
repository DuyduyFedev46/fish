"use client";

// Soạn bài viết / trang: `/content/edit/?id=<bài>` (sửa), `?new=post|page` (tạo), `&version=N` (xem phiên bản, SR-19).
// Toàn bộ giao diện nằm ở features/content/components/EntryEditScreen.tsx.
import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { EntryEditScreen } from "@/features/content/components/EntryEditScreen";

export default function ContentEditPage() {
  return (
    <ViewGuard view="content">
      <Suspense fallback={null}>
        <EntryEditScreen />
      </Suspense>
    </ViewGuard>
  );
}
