"use client";

import { Suspense } from "react";
import ShopFrame from "@/components/ShopFrame";
import { ContentSkeleton } from "@/features/content/components/ContentState";
import PageScreen from "@/features/content/components/PageScreen";

// `/pages/?slug=` — trang CMS: chính sách (F3), Liên hệ (F4), Cách mua (F5). SHOP-5-04. Route mỏng.
export default function PagesRoute() {
  return (
    <Suspense
      fallback={
        <ShopFrame header="sub" title="Chính sách" footer="full" bottomNav={false} backHref="/">
          <ContentSkeleton />
        </ShopFrame>
      }
    >
      <PageScreen />
    </Suspense>
  );
}
