import Link from "next/link";
import type { GroupIcon, ItemImage, Money, SaleUnit, StockLevel } from "@/lib/types";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import { contactTarget } from "../shopLinks";
import AddToCart from "./AddToCart";
import ImageFrame from "./ImageFrame";
import PriceTag from "./PriceTag";
import StockBadge from "./StockBadge";
import s from "./ProductCard.module.css";

export interface ProductCardItem {
  itemCode: string;
  name: string;
  unit: SaleUnit;
  price: Money;
  /** Chỉ mức tồn, không có prop số kg (BR-BH-23). */
  stockLevel: StockLevel;
  shortNote?: string;
  image?: ItemImage | null;
  group: GroupIcon;
  isCombo: boolean;
  /** `min_qty` từ API (kg: 1, combo: 1). */
  minQty: number;
  /** `qty_step` từ API (kg: 0,5, combo: 1). */
  qtyStep: number;
}

export interface ProductCardProps {
  item: ProductCardItem;
  /**
   * rail: thẻ trang chủ, cuộn ngang trên điện thoại, nút "Chọn mua" dẫn sang trang chi tiết (không thêm giỏ).
   * row: một dòng ngang, cả dòng là link, không có nút.
   * grid: thẻ trong lưới danh mục, nút "Thêm 1 kg" biến thành bộ tăng giảm.
   */
  variant?: "grid" | "rail" | "row";
  href: string;
  /** Số hotline hợp lệ cho nút "Liên hệ chúng tôi" của món hết; không có thì nút dẫn tới trang Liên hệ. */
  hotline?: string;
  /** grid: số lượng khách chọn đang có trong giỏ (không phải tồn kho). 0: chưa có. */
  quantityInCart?: number;
  onAdd?: (qty: number) => void;
  onChangeQty?: (qty: number) => void;
  onRequestRemove?: () => void;
}

function ComboTag() {
  return <span className={s.comboTag}>Combo</span>;
}

/** Thẻ một mặt hàng. Thẻ là trình bày: không gọi API, không đọc giỏ. Không bao giờ hiện số kg tồn. */
export default function ProductCard({
  item,
  variant = "grid",
  href,
  hotline,
  quantityInCart = 0,
  onAdd,
  onChangeQty,
  onRequestRemove,
}: ProductCardProps) {
  const out = item.stockLevel === "out";
  const titleId = `pc-${variant}-${item.itemCode}`;

  const image = (
    <ImageFrame
      image={item.image}
      alt=""
      group={item.group}
      ratio={variant === "grid" ? "3/2" : "1/1"}
      squareSize={variant === "row" ? 72 : undefined}
      dimmed={out}
      className={variant === "rail" ? s.railImage : undefined}
      topLeft={variant !== "row" && item.isCombo ? <ComboTag /> : undefined}
      topRight={
        variant !== "row" && item.stockLevel !== "in" ? <StockBadge level={item.stockLevel} /> : undefined
      }
    />
  );

  if (variant === "row") {
    return (
      <article className={s.row} aria-labelledby={titleId}>
        <Link href={href} className={s.rowLink}>
          {image}
          <span className={s.rowText}>
            <span id={titleId} className={cx(s.rowName, out && s.muted)}>
              {item.name}
            </span>
            {item.shortNote ? <span className={s.note}>{item.shortNote}</span> : null}
            <PriceTag amount={item.price} unit={item.unit} size="rail" tone={out ? "muted" : "default"} />
            {item.stockLevel !== "in" ? <StockBadge level={item.stockLevel} placement="inline" /> : null}
          </span>
          <span className={s.chevron}>
            <Icon name="chevron-right" size={18} strokeWidth={2} />
          </span>
        </Link>
      </article>
    );
  }

  if (variant === "grid") {
    return (
      <article className={s.grid} aria-labelledby={titleId}>
        {/* Link ảnh chỉ để bấm, bỏ khỏi thứ tự Tab: mỗi thẻ một điểm dừng là tên. */}
        <Link href={href} className={s.mediaLink} tabIndex={-1} aria-hidden="true">
          {image}
        </Link>
        <h3 className={s.name}>
          <Link id={titleId} href={href} className={cx(s.nameLink, out && s.muted)}>
            {item.name}
          </Link>
        </h3>
        <PriceTag amount={item.price} unit={item.unit} size="card" tone={out ? "muted" : "default"} />
        <p className={s.note}>{item.shortNote ?? ""}</p>
        <AddToCart
          item={item}
          variant="card"
          quantityInCart={quantityInCart}
          hotline={hotline}
          onAdd={(q) => onAdd?.(q)}
          onChangeQty={(q) => onChangeQty?.(q)}
          onRequestRemove={() => onRequestRemove?.()}
        />
      </article>
    );
  }

  return (
    <article className={s.rail} aria-labelledby={titleId}>
      {/* Link ảnh chỉ để bấm, bỏ khỏi thứ tự Tab: mỗi thẻ một điểm dừng là tên. */}
      <Link href={href} className={s.mediaLink} tabIndex={-1} aria-hidden="true">
        {image}
      </Link>
      <h3 className={s.name}>
        <Link id={titleId} href={href} className={cx(s.nameLink, out && s.muted)}>
          {item.name}
        </Link>
      </h3>
      <PriceTag amount={item.price} unit={item.unit} size="rail" tone={out ? "muted" : "default"} />
      <p className={s.note}>{item.shortNote ?? ""}</p>
      {out ? (
        <Button
          href={contactTarget(hotline)}
          variant="secondary"
          fullWidth
          className={s.buy}
          iconStart={<Icon name="phone" size={18} />}
          aria-label={`Liên hệ Cá Về hỏi hàng ${item.name}`}
        >
          Liên hệ chúng tôi
        </Button>
      ) : (
        <Button
          href={href}
          variant="primary"
          shape="pill"
          fullWidth
          className={s.buy}
          aria-label={`Chọn mua ${item.name}`}
        >
          Chọn mua
        </Button>
      )}
    </article>
  );
}
