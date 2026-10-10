"use client";

// SHOP-5-05 AC2, AC3: khối "Món dùng trong bài" (màn G2-KitchenArticle · DesktopKitchenArticle), thay ItemCard cũ.
// Mỗi khối `item_card` của bài = ProductCard `row` (giá theo kg/combo, nhãn tồn 3 mức, không số kg) + AddToCart `card`
// ("Thêm 1 kg" → bộ tăng giảm, toast "Xem giỏ", máy tính có MiniCart, bước 1 kg bấm trừ thì hỏi bỏ món: như SHOP-2-03 AC3, AC5).
// Món hết: nút "Liên hệ chúng tôi". Món ngưng bán / không còn trong catalog: ẩn thẻ. Catalog lỗi: ẩn cả khối, bài vẫn đọc được.
// Nạp catalog đúng 1 lần cho cả bài (SR-23 F7); bài không có thẻ thì không gọi.

import { useEffect, useId, useMemo, useState } from "react";
import ProductCard from "@/components/catalog/ProductCard";
import AddToCart from "@/components/catalog/AddToCart";
import MiniCart from "@/components/cart/MiniCart";
import RemoveItemDialog from "@/components/cart/RemoveItemDialog";
import Skeleton from "@/components/ui/Skeleton";
import { useHotline } from "@/components/useHotline";
import { getCatalog } from "@/lib/api";
import { formatQty } from "@/lib/quantity";
import type { CatalogItem } from "@/lib/types";
import { toCardItem } from "@/features/catalog/cardItem";
import { groupIconOf } from "@/features/catalog/groupIcon";
import { useCartActions } from "@/features/cart/useCartActions";
import type { PublicBlock } from "../types";
import s from "./ArticleItems.module.css";

/** Mã hàng trong các khối `item_card` của bài, giữ thứ tự, bỏ trùng. */
export function itemCodesOf(blocks: PublicBlock[]): string[] {
  const codes: string[] = [];
  for (const b of blocks) {
    if (b.type === "item_card" && typeof b.item_code === "string" && !codes.includes(b.item_code)) codes.push(b.item_code);
  }
  return codes;
}

/** Link sang trang món có UTM theo bài (BR-ND-09, CMS-06 AC4). */
function itemLink(code: string, postSlug: string): string {
  const q = new URLSearchParams({
    code,
    utm_source: "caveve_web",
    utm_medium: "bai_viet",
    utm_campaign: postSlug,
  });
  return `/shop/item/?${q.toString()}`;
}

type CatalogState = { kind: "loading" } | { kind: "error" } | { kind: "ready"; items: CatalogItem[] };

export default function ArticleItems({ codes, postSlug }: { codes: string[]; postSlug: string }) {
  const headingId = useId();
  const [catalog, setCatalog] = useState<CatalogState>({ kind: "loading" });
  const { hotline } = useHotline();
  const actions = useCartActions();
  const { cart } = actions;
  const hasCodes = codes.length > 0;

  useEffect(() => {
    if (!hasCodes) return;
    let active = true;
    getCatalog()
      .then((c) => active && setCatalog({ kind: "ready", items: c.items || [] }))
      .catch(() => active && setCatalog({ kind: "error" }));
    return () => {
      active = false;
    };
  }, [hasCodes]);

  const shown = useMemo(() => {
    if (catalog.kind !== "ready") return [];
    const byCode = new Map(catalog.items.map((it) => [it.item_code, it]));
    return codes.map((c) => byCode.get(c)).filter((it): it is CatalogItem => !!it);
  }, [catalog, codes]);

  if (!hasCodes || catalog.kind === "error") return null;
  if (catalog.kind === "ready" && shown.length === 0) return null;

  const allItems = catalog.kind === "ready" ? catalog.items : [];
  const miniLines = cart.lines.map((l) => {
    const it = allItems.find((i) => i.item_code === l.item_code);
    return {
      itemCode: l.item_code,
      name: l.name,
      qtyText: `${formatQty(l.qty)} ${l.unit}`,
      amount: String(Math.round(l.qty * (Number(l.price) || 0))),
      group: groupIconOf(it?.group.slug ?? "", it?.item_type),
      image: it?.image,
    };
  });

  return (
    <section className={s.section} aria-labelledby={headingId}>
      <h2 id={headingId} className={s.title}>
        Món dùng trong bài
      </h2>
      {catalog.kind === "loading" ? (
        <div className={s.list} aria-busy="true">
          <span className="visually-hidden" role="status">
            Đang tải món trong bài
          </span>
          {codes.slice(0, 3).map((c) => (
            <div key={c} className={s.item}>
              <Skeleton height={72} radius="md" />
            </div>
          ))}
        </div>
      ) : (
        <ul className={s.list}>
          {shown.map((it) => {
            const card = toCardItem(it);
            return (
              <li key={it.item_code} className={s.item}>
                <ProductCard variant="row" item={card} href={itemLink(it.item_code, postSlug)} hotline={hotline} />
                <AddToCart
                  item={card}
                  variant="card"
                  quantityInCart={actions.qtyOf(it.item_code)}
                  hotline={hotline}
                  onAdd={(qty) => actions.add(it, qty)}
                  onChangeQty={(qty) => actions.change(it, qty)}
                  onRequestRemove={() => actions.askRemove(it)}
                />
              </li>
            );
          })}
        </ul>
      )}
      <div className="visually-hidden" role="status" aria-live="polite">
        {actions.live}
      </div>
      <MiniCart
        open={actions.miniOpen}
        onClose={actions.closeMini}
        lines={miniLines}
        itemCount={cart.lineCount}
        subtotal={String(Math.round(cart.totalAmount))}
      />
      <RemoveItemDialog item={actions.pendingView} onKeep={actions.keep} onRemove={actions.confirmRemove} />
    </section>
  );
}
