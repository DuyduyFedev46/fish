"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCatalog } from "@/lib/api";
import { formatQty } from "@/lib/quantity";
import type { CatalogItem } from "@/lib/types";
import ShopFrame from "@/components/ShopFrame";
import { useHotline } from "@/components/useHotline";
import ProductCard from "@/components/catalog/ProductCard";
import CartLine, { CartLineSkeleton } from "@/components/cart/CartLine";
import CartSummary from "@/components/cart/CartSummary";
import CheckoutSteps from "@/components/cart/CheckoutSteps";
import RemoveItemDialog from "@/components/cart/RemoveItemDialog";
import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { focusSoon } from "@/components/ui/focusSoon";
import { useToast } from "@/components/ui/Toast";
import { useCart } from "@/components/CartContext";
import { itemHref, toCardItem } from "@/features/catalog/cardItem";
import { groupIconOf } from "@/features/catalog/groupIcon";
import { reconcileCart } from "../reconcile";
import s from "./CartScreen.module.css";

const NOTICE_ID = "cart-out-notice";

/** Giỏ hàng `/shop/cart/` (B1–B4): so giá và tồn với catalog, báo đổi giá, món hết, số lượng lẻ cũ. */
export default function CartScreen() {
  const router = useRouter();
  const toast = useToast();
  const cart = useCart();
  const { hotline } = useHotline();
  const [catalog, setCatalog] = useState<CatalogItem[] | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [retrying, setRetrying] = useState(false);
  const [adjustedNotice, setAdjustedNotice] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [live, setLive] = useState("");
  const headingRef = useRef<HTMLHeadingElement>(null);
  const focusNext = useRef<string | null | undefined>(undefined);

  const load = useCallback((fresh: boolean) => {
    return getCatalog({ fresh })
      .then((c) => {
        setCatalog(c.items);
        setLoadState("ready");
      })
      .catch(() => setLoadState("error"));
  }, []);

  useEffect(() => {
    load(true);
  }, [load]);

  const result = useMemo(
    () => reconcileCart(cart.lines, loadState === "ready" ? catalog : null),
    [cart.lines, catalog, loadState]
  );

  // Số lượng lẻ từ Shop cũ: làm tròn lên mức hợp lệ, ghi lại và báo (AC6). Không tự xoá món.
  useEffect(() => {
    if (!cart.ready || result.adjustedCount === 0) return;
    const fixed = new Map(result.lines.map((l) => [l.entry.item_code, l.qty]));
    cart.updateEntries((prev) => prev.map((e) => ({ ...e, qty: fixed.get(e.item_code) ?? e.qty })));
    setAdjustedNotice(true);
  }, [cart.ready, result, cart]);

  // Hết món hết thì dòng báo lỗi mất.
  useEffect(() => {
    if (result.outCount === 0) setBlocked(false);
  }, [result.outCount]);

  // Sau khi bỏ một dòng: tiêu điểm về tên dòng kế tiếp, hết dòng thì về tiêu đề.
  useEffect(() => {
    if (focusNext.current === undefined) return;
    const code = focusNext.current;
    focusNext.current = undefined;
    const target = code ? document.querySelector<HTMLElement>(`[data-line-name="${CSS.escape(code)}"]`) : null;
    focusSoon(target ?? headingRef.current);
  }, [cart.lines]);

  const removeLine = useCallback(
    (code: string, name: string) => {
      const idx = cart.lines.findIndex((l) => l.item_code === code);
      const next = cart.lines[idx + 1] ?? cart.lines[idx - 1];
      focusNext.current = next ? next.item_code : null;
      cart.removeItem(code);
      setLive(`Đã bỏ ${name} khỏi giỏ`);
    },
    [cart]
  );

  const byCode = useMemo(() => new Map((catalog ?? []).map((i) => [i.item_code, i])), [catalog]);
  const total = String(result.subtotal);
  const itemCount = result.lines.length;
  const available = itemCount - result.outCount;
  const pendingLine = pending ? result.lines.find((l) => l.entry.item_code === pending) : undefined;

  function proceed() {
    if (result.outCount > 0) {
      setBlocked(true);
      const first = result.lines.find((l) => l.status === "out");
      if (first) {
        focusSoon(document.querySelector<HTMLElement>(`[data-line-remove="${CSS.escape(first.entry.item_code)}"]`));
      }
      return;
    }
    // Ghi giá mới vào giỏ rồi sang bước nhận hàng.
    const prices = new Map(result.lines.map((l) => [l.entry.item_code, l.unitPrice]));
    cart.updateEntries((prev) => prev.map((e) => ({ ...e, price: prices.get(e.item_code) ?? e.price })));
    router.push("/shop/checkout/");
  }

  // Gợi ý khi giỏ trống: một món kg còn hàng và một combo còn hàng.
  const suggestions = useMemo(() => {
    const items = (catalog ?? []).filter((i) => i.stock_level !== "out");
    const simple = items.find((i) => i.item_type === "SIMPLE");
    const combo = items.find((i) => i.item_type === "BUNDLE");
    return [simple, combo].filter((x): x is CatalogItem => !!x);
  }, [catalog]);

  const ready = cart.ready;
  let main;
  if (!ready || (loadState === "loading" && cart.lines.length > 0)) {
    main = (
      <div aria-busy="true">
        <span className="visually-hidden" role="status">Đang tải giỏ hàng</span>
        <ul className={s.list}>
          <CartLineSkeleton count={Math.max(cart.lines.length, 2)} />
        </ul>
      </div>
    );
  } else if (cart.lines.length === 0) {
    main = (
      <div className={s.empty}>
        <EmptyState
          icon="cart"
          title="Giỏ hàng đang trống"
          description="Mua tối thiểu 1 kg mỗi món, giá tính theo kg"
          primaryAction={{ label: "Xem hàng đang có", href: "/shop/" }}
          framed={false}
        />
        {suggestions.length > 0 ? (
          <section className={s.suggest} aria-labelledby="cart-suggest">
            <h2 id="cart-suggest" className={s.suggestTitle}>Gợi ý cho bạn</h2>
            <div className={s.suggestGrid}>
              {suggestions.map((it) => (
                <ProductCard
                  key={it.item_code}
                  item={toCardItem(it)}
                  variant="grid"
                  href={itemHref(it.item_code)}
                  hotline={hotline}
                  quantityInCart={0}
                  onAdd={(qty) => {
                    cart.addItem({ item_code: it.item_code, name: it.name, unit: it.unit, price: it.price }, qty);
                    toast.show({ message: `Đã thêm ${formatQty(qty)} ${it.unit} ${it.name} vào giỏ` });
                  }}
                />
              ))}
            </div>
          </section>
        ) : null}
      </div>
    );
  } else {
    main = (
      <div className={s.layout}>
        <div className={s.listCol}>
          {loadState === "error" ? (
            <div className={s.banner}>
              <Banner
                tone="warn"
                live="polite"
                action={
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={retrying}
                    onClick={async () => {
                      setRetrying(true);
                      await load(true);
                      setRetrying(false);
                    }}
                  >
                    Thử lại
                  </Button>
                }
              >
                Chưa cập nhật được giá. Thử lại
              </Banner>
            </div>
          ) : null}
          {result.priceChangedCount > 0 || result.outCount > 0 ? (
            <div className={s.banner}>
              <Banner tone="warn" title="Giỏ hàng có thay đổi từ lần trước" />
            </div>
          ) : null}
          {adjustedNotice ? (
            <div className={s.banner}>
              <Banner tone="info" live="polite">
                Số lượng đã chỉnh theo mức bán
              </Banner>
            </div>
          ) : null}
          <ul className={s.list} aria-label="Các món trong giỏ">
            {result.lines.map((l) => {
              const it = byCode.get(l.entry.item_code);
              return (
                <CartLine
                  key={l.entry.item_code}
                  line={{
                    itemCode: l.entry.item_code,
                    name: l.entry.name,
                    unit: l.entry.unit,
                    qty: l.qty,
                    unitPrice: l.unitPrice,
                    previousUnitPrice: l.previousUnitPrice,
                    image: it?.image,
                    group: groupIconOf(it?.group.slug ?? "", l.entry.unit === "combo" ? "BUNDLE" : "SIMPLE"),
                    minQty: l.rule.minQty,
                    qtyStep: l.rule.step,
                  }}
                  status={l.status}
                  href={itemHref(l.entry.item_code)}
                  hotline={hotline}
                  onChangeQty={(q) => {
                    cart.setQty(l.entry.item_code, q);
                    setLive(`Đã cập nhật ${l.entry.name}: ${formatQty(q)} ${l.entry.unit}`);
                  }}
                  onRequestRemove={() => setPending(l.entry.item_code)}
                  onRemoveNow={() => removeLine(l.entry.item_code, l.entry.name)}
                />
              );
            })}
          </ul>
          <p className={s.rule}>Mua tối thiểu 1 kg mỗi món.</p>
        </div>
        <div className={s.summaryCol}>
          <CartSummary
            context="cart"
            itemCount={itemCount}
            availableCount={available}
            subtotal={total}
            total={total}
            notice={blocked && result.outCount > 0 ? { id: NOTICE_ID, text: "Bỏ món đã hết để đặt hàng." } : undefined}
            cta={{
              label: "Tiếp tục: nhập thông tin nhận hàng",
              labelDesktop: "Tiếp tục",
              onClick: proceed,
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <ShopFrame header="sub" title="Giỏ hàng" showCart={false} desktopHeader="compact" footer="compact" bottomNav={false} backHref="/shop/">
      <div className={s.page}>
        <div className={s.head}>
          <h1 ref={headingRef} tabIndex={-1} className={s.title}>
            Giỏ hàng{cart.lines.length > 0 ? <span className={s.count}> ({cart.lines.length})</span> : null}
          </h1>
          <CheckoutSteps current={1} />
        </div>
        {main}
      </div>
      <div className="visually-hidden" role="status" aria-live="polite">
        {live}
      </div>
      <RemoveItemDialog
        item={
          pendingLine
            ? { name: pendingLine.entry.name, unit: pendingLine.entry.unit, minQty: pendingLine.rule.minQty }
            : null
        }
        onKeep={() => setPending(null)}
        onRemove={() => {
          if (pendingLine) removeLine(pendingLine.entry.item_code, pendingLine.entry.name);
          setPending(null);
        }}
      />
    </ShopFrame>
  );
}
