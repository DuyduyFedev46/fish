"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCatalog } from "@/lib/api";
import { formatQty } from "@/lib/quantity";
import type { CatalogResponse } from "@/lib/types";
import ShopFrame from "@/components/ShopFrame";
import { useHotline } from "@/components/useHotline";
import { groupHref, contactTarget } from "@/components/shopLinks";
import ProductCard from "@/components/catalog/ProductCard";
import SideFilter from "@/components/catalog/SideFilter";
import SortControl, { type SortValue } from "@/components/catalog/SortControl";
import SearchBox from "@/components/search/SearchBox";
import CartBar from "@/components/cart/CartBar";
import MiniCart from "@/components/cart/MiniCart";
import RemoveItemDialog from "@/components/cart/RemoveItemDialog";
import Breadcrumb from "@/components/ui/Breadcrumb";
import Chip from "@/components/ui/Chip";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import { ChipRowSkeleton, ProductCardSkeleton } from "@/components/ui/Skeleton";
import { useCartActions } from "@/features/cart/useCartActions";
import { itemHref, toCardItem } from "../cardItem";
import { filterAndSort, rulesText } from "../catalogView";
import { groupIconOf } from "../groupIcon";
import { useSearchSuggest } from "../useSearchSuggest";
import s from "./CatalogScreen.module.css";

const SORTS: SortValue[] = ["default", "price_asc", "price_desc"];

/** Danh mục `/shop/` (A2): lọc nhóm, sắp xếp, tìm, thêm theo bước. Lọc và sắp xếp tại chỗ trên catalog đã tải. */
export default function CatalogScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const group = params.get("group") ?? "";
  const type = params.get("type") === "combo" ? "combo" : "";
  const sortParam = params.get("sort") as SortValue | null;
  const sort: SortValue = sortParam && SORTS.includes(sortParam) ? sortParam : "default";
  const focusSearch = params.get("focus") === "search";

  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [retrying, setRetrying] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const { hotline } = useHotline();
  const search = useSearchSuggest();
  const actions = useCartActions();
  const { cart } = actions;

  const load = useCallback((fresh: boolean) => {
    return getCatalog({ fresh })
      .then((c) => {
        setCatalog(c);
        setState("ready");
        return true;
      })
      .catch(() => {
        setState("error");
        return false;
      });
  }, []);

  useEffect(() => {
    load(false);
  }, [load]);

  // Có CartBar thì thanh đáy và Toast phải nhường chỗ.
  const showBar = cart.lineCount > 0;
  useEffect(() => {
    if (!showBar) return;
    document.body.dataset.cartBar = "1";
    return () => {
      delete document.body.dataset.cartBar;
    };
  }, [showBar]);

  async function retry() {
    setRetrying(true);
    const ok = await load(true);
    setRetrying(false);
    if (ok) headingRef.current?.focus();
  }

  const items = catalog?.items ?? [];
  const visible = useMemo(() => filterAndSort(items, { q, group, type, sort }), [items, q, group, type, sort]);
  const currentSlug = type === "combo" ? "combo" : group;
  const currentGroup = catalog?.groups.find((g) => g.slug === currentSlug);
  const unknownGroup = !!currentSlug && !currentGroup && state === "ready";
  const heading = q
    ? `Kết quả cho “${q}”`
    : currentGroup
      ? currentGroup.name
      : unknownGroup
        ? "Không tìm thấy nhóm hàng"
        : "Tất cả hải sản";

  const hrefWith = (next: Record<string, string>) => {
    const sp = new URLSearchParams();
    const merged = { q, sort: sort === "default" ? "" : sort, ...next };
    for (const [k, v] of Object.entries(merged)) if (v) sp.set(k, v);
    const qs = sp.toString();
    return qs ? `/shop/?${qs}` : "/shop/";
  };
  const groupLink = (slug: string) => {
    const base = slug === "combo" ? { group: "", type: "combo" } : slug ? { group: slug, type: "" } : { group: "", type: "" };
    return hrefWith(base);
  };

  function changeSort(v: SortValue) {
    router.replace(hrefWith({ group, type, sort: v === "default" ? "" : v }));
  }

  const groupChips = [{ slug: "", name: "Tất cả" }, ...(catalog?.groups ?? [])];
  const busy = state === "loading";
  const miniLines = cart.lines.map((l) => {
    const it = items.find((i) => i.item_code === l.item_code);
    return {
      itemCode: l.item_code,
      name: l.name,
      qtyText: `${formatQty(l.qty)} ${l.unit}`,
      amount: String(Math.round(l.qty * (Number(l.price) || 0))),
      group: groupIconOf(it?.group.slug ?? "", it?.item_type),
      image: it?.image,
    };
  });

  const crumbs = [
    { label: "Trang chủ", href: "/" },
    { label: "Hàng đang có", href: currentGroup || q ? "/shop/" : undefined },
    ...(currentGroup ? [{ label: currentGroup.name }] : q ? [{ label: `Tìm “${q}”` }] : []),
  ];

  const emptyAction = {
    suggestions: (catalog?.groups ?? []).map((g) => ({ label: g.name, href: groupHref(g.slug) })),
    contactHref: contactTarget(hotline),
  };

  return (
    <ShopFrame header="sticky" footer="full" bottomNav currentGroupSlug={currentSlug || undefined}>
      <div className={s.page} aria-busy={busy || undefined}>
        <div className={s.mobileSearch}>
          <SearchBox key={q} variant="page" defaultValue={q} placeholder="Tìm cá, tôm, mực…" autoFocus={focusSearch} {...search} />
        </div>

        <nav className={s.chips} aria-label="Danh mục">
          {busy ? (
            <ChipRowSkeleton />
          ) : (
            groupChips.map((g) => (
              <Chip
                key={g.slug || "all"}
                label={g.name}
                href={groupLink(g.slug)}
                selected={(g.slug || "") === currentSlug}
              />
            ))
          )}
        </nav>

        <div className={s.container}>
          <div className={s.crumbs}>
            <Breadcrumb items={crumbs} />
          </div>
          <div className={s.layout}>
            {!busy && state === "ready" ? (
              <div className={s.side}>
                <SideFilter
                  currentSlug={currentSlug || "all"}
                  rulesText={rulesText(items)}
                  groups={[
                    { slug: "all", label: "Tất cả hải sản", count: items.length, href: groupLink("") },
                    ...(catalog?.groups ?? []).map((g) => ({
                      slug: g.slug,
                      label: g.name,
                      count: g.item_count,
                      href: groupLink(g.slug),
                    })),
                  ]}
                />
              </div>
            ) : null}
            <div className={s.content}>
              <div className={s.headRow}>
                <h1 ref={headingRef} tabIndex={-1} className={s.title}>
                  {heading}
                  {state === "ready" && !unknownGroup ? <span className={s.titleCount}> · {visible.length} món</span> : null}
                </h1>
                {state === "ready" ? <SortControl value={sort} onChange={changeSort} resultCount={visible.length} /> : null}
              </div>

              {busy ? (
                <>
                  <span className="visually-hidden" role="status">
                    Đang tải hàng
                  </span>
                  <div className={s.grid}>
                    <ProductCardSkeleton count={6} />
                  </div>
                </>
              ) : state === "error" ? (
                <ErrorState
                  title="Chưa tải được hàng"
                  description="Kiểm tra kết nối mạng rồi thử lại"
                  onRetry={retry}
                  retrying={retrying}
                />
              ) : visible.length === 0 ? (
                <EmptyState
                  icon="search"
                  title={q ? `Không tìm thấy “${q}”` : unknownGroup ? "Không tìm thấy nhóm hàng này" : "Nhóm này chưa có món"}
                  description="Thử từ khoá khác hoặc xem các nhóm hàng bên dưới"
                  {...emptyAction}
                />
              ) : (
                <ul className={s.grid} aria-label="Danh sách sản phẩm">
                  {visible.map((it) => (
                    <li key={it.item_code} className={s.cell}>
                      <ProductCard
                        item={toCardItem(it)}
                        variant="grid"
                        href={itemHref(it.item_code)}
                        hotline={hotline}
                        quantityInCart={actions.qtyOf(it.item_code)}
                        onAdd={(qty) => actions.add(it, qty)}
                        onChangeQty={(qty) => actions.change(it, qty)}
                        onRequestRemove={() => actions.askRemove(it)}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="visually-hidden" role="status" aria-live="polite">
        {actions.live}
      </div>
      {showBar ? <CartBar itemCount={cart.lineCount} subtotal={String(Math.round(cart.totalAmount))} /> : null}
      <MiniCart
        open={actions.miniOpen}
        onClose={actions.closeMini}
        lines={miniLines}
        itemCount={cart.lineCount}
        subtotal={String(Math.round(cart.totalAmount))}
      />
      <RemoveItemDialog item={actions.pendingView} onKeep={actions.keep} onRemove={actions.confirmRemove} />
    </ShopFrame>
  );
}
