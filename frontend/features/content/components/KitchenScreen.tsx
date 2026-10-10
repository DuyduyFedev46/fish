"use client";

// SHOP-5-05: Góc bếp `/blog/` (danh sách, lọc `?category=`) và `/blog/?slug=` (bài viết). 02b §1.4: danh sách dùng
// header `sticky` + thanh đáy; bài viết dùng header `sub`, không thanh đáy.

import { useSearchParams } from "next/navigation";
import ShopFrame from "@/components/ShopFrame";
import { KITCHEN_HREF } from "@/components/shopLinks";
import KitchenArticleView from "./KitchenArticleView";
import KitchenListView from "./KitchenListView";

export default function KitchenScreen() {
  const params = useSearchParams();
  const slug = params.get("slug") ?? "";
  if (slug) {
    return (
      <ShopFrame header="sub" title="Góc bếp" footer="full" bottomNav={false} backHref={KITCHEN_HREF}>
        <KitchenArticleView key={slug} slug={slug} />
      </ShopFrame>
    );
  }
  const category = params.get("category") ?? "";
  const pageNumber = Number.parseInt(params.get("page") ?? "1", 10);
  return (
    <ShopFrame header="sticky" footer="full" bottomNav>
      <KitchenListView category={category} page={Number.isFinite(pageNumber) && pageNumber > 0 ? pageNumber : 1} />
    </ShopFrame>
  );
}
