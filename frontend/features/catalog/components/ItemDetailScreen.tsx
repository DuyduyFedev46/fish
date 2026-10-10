"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { getCatalogItem } from "@/lib/api";
import { formatKg } from "@/lib/format";
import type { CatalogItemDetail } from "@/lib/types";
import ShopFrame from "@/components/ShopFrame";
import { useHotline } from "@/components/useHotline";
import AddToCart from "@/components/catalog/AddToCart";
import ImageFrame from "@/components/catalog/ImageFrame";
import PriceTag from "@/components/catalog/PriceTag";
import StockBadge from "@/components/catalog/StockBadge";
import MiniCart from "@/components/cart/MiniCart";
import Banner from "@/components/ui/Banner";
import Breadcrumb from "@/components/ui/Breadcrumb";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import { CART_HREF } from "@/components/shopLinks";
import { formatQty } from "@/lib/quantity";
import { useCartActions } from "@/features/cart/useCartActions";
import { toCardItem } from "../cardItem";
import { groupIconOf } from "../groupIcon";
import s from "./ItemDetailScreen.module.css";

/** Chi tiết món `/shop/item/?code=` (A3), món hết (A7), combo (A10). Khối thông tin chỉ hiện khi có chữ. */
export default function ItemDetailScreen() {
  const router = useRouter();
  const code = useSearchParams().get("code") ?? "";
  const [item, setItem] = useState<CatalogItemDetail | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [retrying, setRetrying] = useState(false);
  const { hotline, zaloUrl } = useHotline();
  const actions = useCartActions();
  const { cart } = actions;

  const load = useCallback(() => {
    if (!code) {
      setState("missing");
      return Promise.resolve();
    }
    return getCatalogItem(code)
      .then((d) => {
        setItem(d);
        setState(d ? "ready" : "missing");
      })
      .catch(() => setState("error"));
  }, [code]);

  useEffect(() => {
    setState("loading");
    load();
  }, [load]);

  useEffect(() => {
    if (item) document.title = `${item.name} | Cá Về`;
  }, [item]);

  // Thanh mua dính đáy (điện thoại): toast phải nổi phía trên nó.
  const hasBar = state === "ready";
  useEffect(() => {
    if (!hasBar) return;
    document.body.dataset.buyBar = "1";
    return () => {
      delete document.body.dataset.buyBar;
    };
  }, [hasBar]);

  const isCombo = item?.item_type === "BUNDLE";
  const frameTitle = isCombo ? "Chi tiết combo" : "Chi tiết sản phẩm";
  const out = item?.stock_level === "out";

  let body;
  if (state === "loading") {
    body = (
      <div className={s.skeleton} aria-busy="true">
        <span className="visually-hidden" role="status">Đang tải</span>
        <Skeleton width="100%" height={260} radius="lg" />
        <Skeleton width="60%" height={24} />
        <Skeleton width="40%" height={28} />
      </div>
    );
  } else if (state === "error") {
    body = (
      <ErrorState
        title="Chưa tải được món này"
        description="Kiểm tra kết nối mạng rồi thử lại"
        showGhostGrid={false}
        retrying={retrying}
        onRetry={async () => {
          setRetrying(true);
          await load();
          setRetrying(false);
        }}
      />
    );
  } else if (state === "missing" || !item) {
    body = (
      <EmptyState
        icon="search"
        title="Không tìm thấy món này"
        primaryAction={{ label: "Xem hàng đang có", href: "/shop/" }}
      />
    );
  } else {
    const card = toCardItem(item);
    const infoRows = [
      { label: "Danh mục", value: item.group.name },
      { label: "Quy cách", value: item.spec },
      { label: "Bảo quản", value: item.storage },
      { label: "Nguồn hàng", value: item.origin },
      { label: "Đơn vị bán", value: item.unit === "kg" ? "Kg" : "Combo" },
    ].filter((r) => r.value.trim() !== "");
    body = (
      <div className={s.layout}>
        <div className={s.media}>
          <ImageFrame
            image={item.image}
            alt={item.name}
            group={groupIconOf(item.group.slug, item.item_type)}
            ratio="1/1"
            loadingPriority="eager"
            dimmed={out}
            topLeft={isCombo ? <span className={s.comboTag}>Combo</span> : undefined}
            topRight={item.stock_level === "out" ? <StockBadge level="out" /> : undefined}
          />
        </div>
        <div className={s.info}>
          <p className={s.meta}>
            {item.group.name} · Mã {item.item_code}
          </p>
          <h1 className={s.name}>{item.name}</h1>
          <PriceTag amount={item.price} unit={item.unit} size="detail" tone={out ? "muted" : "accent"} />
          <div>
            <StockBadge level={item.stock_level} placement="inline" size="md" />
          </div>
          {item.short_note ? <p className={s.note}>{item.short_note}</p> : null}

          {out ? (
            <Banner tone="info">Món này đang hết. Liên hệ để hỏi khi nào có hàng.</Banner>
          ) : null}

          {isCombo && item.bundle_components && item.bundle_components.length > 0 ? (
            <section className={s.block} aria-labelledby="combo-parts">
              <h2 id="combo-parts" className={s.blockTitle}>
                Trong combo có
              </h2>
              <table className={s.table}>
                <thead>
                  <tr>
                    <th scope="col">Món</th>
                    <th scope="col">Số lượng</th>
                  </tr>
                </thead>
                <tbody>
                  {item.bundle_components.map((c) => (
                    <tr key={c.item_code}>
                      <td>{c.name}</td>
                      <td className="num">{formatKg(c.qty_per_bundle)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className={s.caption}>Nếu một món trong combo hết, combo tạm ngưng bán.</p>
            </section>
          ) : null}

          <AddToCart
            item={card}
            variant="detail"
            quantityInCart={actions.qtyOf(item.item_code)}
            hotline={hotline}
            zaloUrl={zaloUrl}
            onAdd={(qty) => actions.add(item, qty)}
            onChangeQty={() => {}}
            onRequestRemove={() => {}}
            onBuyNow={(qty) => {
              cart.addItem(
                { item_code: item.item_code, name: item.name, unit: item.unit, price: item.price },
                qty
              );
              router.push(CART_HREF);
            }}
          />

          <section className={s.block} aria-labelledby="item-info">
            <h2 id="item-info" className={s.blockTitle}>
              Thông tin sản phẩm
            </h2>
            <dl className={s.dl}>
              {infoRows.map((r) => (
                <div key={r.label} className={s.dlRow}>
                  <dt>{r.label}</dt>
                  <dd>{r.value}</dd>
                </div>
              ))}
            </dl>
            {item.description.trim() ? <p className={s.description}>{item.description}</p> : null}
          </section>
        </div>
      </div>
    );
  }

  const crumbs = item
    ? [
        { label: "Trang chủ", href: "/" },
        { label: "Hàng đang có", href: "/shop/" },
        {
          label: item.group.name,
          href: item.group.slug === "combo" ? "/shop/?type=combo" : `/shop/?group=${encodeURIComponent(item.group.slug)}`,
        },
        { label: item.name },
      ]
    : null;

  const miniLines = cart.lines.map((l) => ({
    itemCode: l.item_code,
    name: l.name,
    qtyText: `${formatQty(l.qty)} ${l.unit}`,
    amount: String(Math.round(l.qty * (Number(l.price) || 0))),
    group: groupIconOf("", l.unit === "combo" ? "BUNDLE" : "SIMPLE"),
    image: item && item.item_code === l.item_code ? item.image : null,
  }));

  return (
    <ShopFrame
      header="sub"
      title={frameTitle}
      footer="full"
      bottomNav={false}
      currentGroupSlug={item?.group.slug}
    >
      <div className={s.page}>
        {crumbs ? (
          <div className={s.crumbs}>
            <Breadcrumb items={crumbs} />
          </div>
        ) : null}
        {body}
      </div>
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
    </ShopFrame>
  );
}
