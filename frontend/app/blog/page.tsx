"use client";

import { Suspense } from "react";
import ShopFrame from "@/components/ShopFrame";
import { ContentSkeleton } from "@/features/content/components/ContentState";
import KitchenScreen from "@/features/content/components/KitchenScreen";

// `/blog/` — Góc bếp: danh sách (`?category=`) và bài (`?slug=`). SHOP-5-05. Route mỏng.
export default function BlogRoute() {
  return (
    <Suspense
      fallback={
        <ShopFrame header="sticky" footer="full" bottomNav>
          <ContentSkeleton label="Đang tải bài" />
        </ShopFrame>
      }
    >
      <KitchenScreen />
    </Suspense>
  );
}
