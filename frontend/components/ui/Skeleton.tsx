import { cx } from "./cx";
import s from "./Skeleton.module.css";

export interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  radius?: "sm" | "md" | "lg" | "full";
  /** false: đứng yên (khung xương dưới ErrorState). */
  animated?: boolean;
}

/** Nguyên tử khung xương. Mọi khối đều aria-hidden; vùng chứa lo `aria-busy` và chữ ẩn "Đang tải hàng". */
export default function Skeleton({ width = "100%", height = 14, radius = "sm", animated = true }: SkeletonProps) {
  return (
    <span
      className={cx(s.bar, s[radius], animated && s.animated)}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

/** Thẻ sản phẩm dạng khung xương, cùng kích thước thẻ thật (ảnh, 2 dòng tên, giá, ghi chú, nút). */
export function ProductCardSkeleton({
  count = 4,
  animated = true,
}: {
  count?: number;
  animated?: boolean;
}) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={s.card} aria-hidden="true">
          <span className={cx(s.bar, s.md, animated && s.animated, s.cardImage)} />
          <Skeleton width="90%" height={14} animated={animated} />
          <Skeleton width="60%" height={14} animated={animated} />
          <Skeleton width="55%" height={20} animated={animated} />
          <Skeleton width="70%" height={12} animated={animated} />
          <Skeleton width="100%" height={44} radius="md" animated={animated} />
        </div>
      ))}
    </>
  );
}

/** Hàng chip lọc dạng khung xương. */
export function ChipRowSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className={s.chipRow} aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} width={48 + ((i * 11) % 28)} height={40} radius="full" />
      ))}
    </div>
  );
}
