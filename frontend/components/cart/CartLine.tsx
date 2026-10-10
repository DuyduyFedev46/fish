"use client";

import Link from "next/link";
import type { GroupIcon, ItemImage, Money, SaleUnit } from "@/lib/types";
import { formatQty } from "@/lib/quantity";
import { formatPriceVnd } from "@/lib/format";
import ImageFrame from "../catalog/ImageFrame";
import PriceTag from "../catalog/PriceTag";
import QtyStepper from "../catalog/QtyStepper";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import IconButton from "../ui/IconButton";
import Skeleton from "../ui/Skeleton";
import { cx } from "../ui/cx";
import { contactTarget } from "../shopLinks";
import s from "./CartLine.module.css";

export type CartLineStatus = "ok" | "price-changed" | "out";

export interface CartLineProps {
  line: {
    itemCode: string;
    name: string;
    unit: SaleUnit;
    qty: number;
    unitPrice: Money;
    previousUnitPrice?: Money;
    image?: ItemImage | null;
    group: GroupIcon;
    minQty: number;
    qtyStep: number;
  };
  status?: CartLineStatus;
  href: string;
  hotline?: string;
  onChangeQty: (qty: number) => void;
  /** Bỏ món còn hàng: container mở hộp thoại xác nhận (UI-RULES §5.4). */
  onRequestRemove: () => void;
  /** Món đã hết: bỏ ngay, không hỏi lại (02b §6.1). */
  onRemoveNow: () => void;
}

/** Một dòng món trong giỏ: ảnh, tên, đơn giá, số lượng, thành tiền; có trạng thái đổi giá và hết hàng. */
export default function CartLine({
  line,
  status = "ok",
  href,
  hotline,
  onChangeQty,
  onRequestRemove,
  onRemoveNow,
}: CartLineProps) {
  const out = status === "out";
  const lineTotal = String(Math.round((Number(line.unitPrice) || 0) * line.qty));
  const image = (
    <ImageFrame
      image={line.image}
      alt=""
      group={line.group}
      ratio="1/1"
      squareSize={68}
      dimmed={out}
      className={s.image}
    />
  );

  if (out) {
    return (
      <li className={cx(s.line, s.out)}>
        <span className={s.imageCell}>{image}</span>
        <div className={s.outText}>
          <Link href={href} className={s.name} data-line-name={line.itemCode}>
            {line.name}
            <span className="visually-hidden">, đã hết hàng</span>
          </Link>
          <span className={cx(s.outInfo, "num")}>
            {formatQty(line.qty)} {line.unit} · {formatPriceVnd(line.unitPrice)} / {line.unit} · không tính vào tổng
          </span>
          <span className={s.outFlag}>
            <Icon name="ban" size={16} strokeWidth={2} />
            Món này đã hết
          </span>
        </div>
        <div className={s.outActions}>
          <Button
            href={contactTarget(hotline)}
            variant="secondary"
            aria-label={`Liên hệ Cá Về hỏi hàng ${line.name}`}
          >
            Liên hệ
          </Button>
          <Button
            variant="secondary"
            data-line-remove={line.itemCode}
            aria-label={`Bỏ ${line.name} khỏi giỏ`}
            onClick={onRemoveNow}
          >
            Bỏ khỏi giỏ
          </Button>
        </div>
      </li>
    );
  }

  return (
    <li className={s.line}>
      <span className={s.imageCell}>{image}</span>
      <Link href={href} className={cx(s.name, s.nameArea)} data-line-name={line.itemCode}>
        {line.name}
      </Link>
      <span className={s.removeCell}>
        <IconButton
          label={`Bỏ ${line.name} khỏi giỏ`}
          icon="close"
          variant="danger-ghost"
          iconSize={20}
          onClick={onRequestRemove}
        />
      </span>
      <div className={s.priceCell}>
        <PriceTag
          amount={line.unitPrice}
          unit={line.unit}
          size="meta"
          previousAmount={status === "price-changed" ? line.previousUnitPrice : undefined}
        />
        {status === "price-changed" ? <span className={s.tag}>Giá đã cập nhật</span> : null}
      </div>
      <div className={s.qtyCell}>
        <QtyStepper
          value={line.qty}
          min={line.minQty}
          step={line.qtyStep}
          unit={line.unit}
          itemName={line.name}
          mode="cart"
          variant="outline"
          size="sm"
          onChange={onChangeQty}
          onRequestRemove={onRequestRemove}
        />
      </div>
      <div className={s.totalCell}>
        <PriceTag amount={lineTotal} size="line" />
      </div>
    </li>
  );
}

/** Khung xương một dòng giỏ khi đang tải lại catalog để so giá. */
export function CartLineSkeleton({ count = 2 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <li key={i} className={s.line} aria-hidden="true">
          <span className={s.imageCell}>
            <Skeleton width={68} height={68} radius="md" />
          </span>
          <span className={s.nameArea}>
            <Skeleton width="70%" height={14} />
          </span>
          <span className={s.priceCell}>
            <Skeleton width="40%" height={12} />
          </span>
          <span className={s.qtyCell}>
            <Skeleton width={150} height={40} radius="md" />
          </span>
          <span className={s.totalCell}>
            <Skeleton width={72} height={16} />
          </span>
        </li>
      ))}
    </>
  );
}
