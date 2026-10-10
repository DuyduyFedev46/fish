"use client";

import { useEffect, useId, useRef, useState } from "react";
import { formatPriceVnd } from "@/lib/format";
import { formatQty, parseQtyRule, stepUp } from "@/lib/quantity";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import ToggleButton from "../ui/ToggleButton";
import { cx } from "../ui/cx";
import { focusSoon } from "../ui/focusSoon";
import { contactTarget } from "../shopLinks";
import type { ProductCardItem } from "./ProductCard";
import QtyStepper from "./QtyStepper";
import s from "./AddToCart.module.css";

export interface AddToCartProps {
  item: ProductCardItem;
  /** card: trên thẻ ("Thêm 1 kg" thành bộ tăng giảm). detail: chọn số lượng và thanh mua ở trang chi tiết. */
  variant: "card" | "detail";
  /** Số lượng khách chọn đang có trong giỏ (không phải tồn kho). 0: chưa có. */
  quantityInCart: number;
  /** Có số hợp lệ thì gọi; không có thì nút dẫn tới trang Liên hệ. */
  hotline?: string;
  zaloUrl?: string;
  onAdd: (qty: number) => void;
  onChangeQty: (qty: number) => void;
  onRequestRemove: () => void;
  /** detail: thêm rồi sang giỏ. */
  onBuyNow?: (qty: number) => void;
}

/** Cụm hành động mua của một mặt hàng. Trình bày: container lo giỏ, toast và hộp thoại bỏ món. */
export default function AddToCart(props: AddToCartProps) {
  return props.variant === "card" ? <CardAction {...props} /> : <DetailAction {...props} />;
}

function unitLabel(item: ProductCardItem, qty: number): string {
  return `${formatQty(qty)} ${item.unit}`;
}

function CardAction({ item, quantityInCart, hotline, onAdd, onChangeQty, onRequestRemove }: AddToCartProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const touched = useRef(false);
  const prev = useRef(quantityInCart);
  const out = item.stockLevel === "out";

  // Nút cũ biến mất khi đổi qua lại, nên tiêu điểm phải được dời (không để rơi về <body>).
  useEffect(() => {
    const before = prev.current;
    prev.current = quantityInCart;
    if (!touched.current) return;
    if (before === 0 && quantityInCart > 0) {
      touched.current = false;
      focusSoon(rootRef.current?.querySelector<HTMLElement>("[data-qty-plus]"));
    } else if (before > 0 && quantityInCart === 0) {
      touched.current = false;
      focusSoon(rootRef.current?.querySelector<HTMLElement>("[data-add]"));
    }
  }, [quantityInCart]);

  if (out) {
    return (
      <div className={s.card}>
        <Button
          href={contactTarget(hotline)}
          variant="secondary"
          fullWidth
          iconStart={<Icon name="phone" size={18} />}
          aria-label={`Liên hệ Cá Về hỏi hàng ${item.name}`}
        >
          Liên hệ chúng tôi
        </Button>
      </div>
    );
  }

  return (
    <div ref={rootRef} className={s.card} onClickCapture={() => (touched.current = true)}>
      {quantityInCart > 0 ? (
        <QtyStepper
          value={quantityInCart}
          min={item.minQty}
          step={item.qtyStep}
          unit={item.unit}
          itemName={item.name}
          mode="cart"
          variant="filled"
          onChange={onChangeQty}
          onRequestRemove={onRequestRemove}
        />
      ) : (
        <Button
          variant="outline"
          fullWidth
          data-add=""
          aria-label={`Thêm ${unitLabel(item, item.minQty)} ${item.name} vào giỏ`}
          onClick={() => onAdd(item.minQty)}
        >
          Thêm {unitLabel(item, item.minQty)}
        </Button>
      )}
    </div>
  );
}

function DetailAction({
  item,
  hotline,
  zaloUrl,
  onAdd,
  onBuyNow,
}: AddToCartProps) {
  const rule = parseQtyRule(item.minQty, item.qtyStep, item.unit);
  const [selected, setSelected] = useState(rule.minQty);
  const headingId = useId();
  const hintId = useId();
  const out = item.stockLevel === "out";

  if (out) {
    return (
      <div className={s.bar}>
        <div className={s.barInner}>
          <Button
            href={contactTarget(hotline)}
            variant="primary"
            size="lg"
            fullWidth
            iconStart={<Icon name="phone" size={18} />}
          >
            {hotline ? `Gọi ${hotline}` : "Liên hệ chúng tôi"}
          </Button>
          {zaloUrl ? (
            <Button href={zaloUrl} external variant="outline" size="lg" fullWidth>
              Nhắn Zalo
            </Button>
          ) : null}
        </div>
      </div>
    );
  }

  const presets =
    item.unit === "kg"
      ? [0, 1, 2, 4].map((k) => (k === 0 ? rule.minQty : rule.minQty + k * rule.step))
      : [];
  const subtotal = Math.round((Number(item.price) || 0) * selected);
  const isKg = item.unit === "kg";

  return (
    <>
      <div className={s.select}>
        <h2 id={headingId} className={s.selectTitle}>
          {isKg ? "Chọn số kg" : "Số combo"}
        </h2>
        {presets.length > 0 ? (
          <div className={s.presets} role="group" aria-labelledby={headingId}>
            {presets.map((q) => (
              <ToggleButton
                key={q}
                label={`${formatQty(q)} kg`}
                pressed={selected === q}
                onPressedChange={() => setSelected(q)}
              />
            ))}
          </div>
        ) : null}
        <div className={s.stepperRow}>
          <QtyStepper
            value={selected}
            min={rule.minQty}
            step={rule.step}
            unit={item.unit}
            itemName={item.name}
            mode="select"
            variant="outline"
            describedBy={hintId}
            onChange={setSelected}
          />
          <span id={hintId} className={s.hint}>
            Tối thiểu {formatQty(rule.minQty)} {item.unit}
          </span>
        </div>
        <div className={s.subtotal}>
          <span>Tạm tính</span>
          <span className={cx(s.subtotalValue, "num")}>{formatPriceVnd(String(subtotal))}</span>
        </div>
      </div>
      <div className={s.bar}>
        <div className={s.barInner}>
          <Button variant="outline" size="lg" fullWidth onClick={() => onAdd(selected)}>
            Thêm vào giỏ
          </Button>
          <Button variant="primary" size="lg" fullWidth onClick={() => onBuyNow?.(selected)}>
            Chọn mua
          </Button>
        </div>
      </div>
    </>
  );
}
