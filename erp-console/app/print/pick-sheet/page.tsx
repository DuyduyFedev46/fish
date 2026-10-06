"use client";

// CS-16: /print/pick-sheet/?note=<số> — phiếu soạn nội bộ 100x150 mm. Logic ở features/deliveries/components/PickSheetScreen.
import { Suspense } from "react";
import { PickSheetScreen } from "@/features/deliveries/components/PickSheetScreen";

export default function PickSheetPage() {
  return (
    <Suspense
      fallback={
        <div role="status" style={{ padding: "var(--space-6)" }}>
          <p className="muted">Đang nạp phiếu soạn…</p>
        </div>
      }
    >
      <PickSheetScreen />
    </Suspense>
  );
}
