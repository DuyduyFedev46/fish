// Thanh AI mảnh trên danh sách (UI-RULES §4.5): "AI · Có n đề xuất: …  Xem" + chip "AI đề xuất" trên dòng liên quan.
// AI KHÔNG phải menu riêng. Component chỉ vẽ: đếm và câu tóm tắt do màn lấy từ API (R1) rồi truyền vào —
// không import gì của features/ai (giữ code AI nặng ra khỏi chunk màn nghiệp vụ).
import Link from "next/link";
import { Icon } from "./Icon";

type Props = {
  /** Số đề xuất đang chờ; 0/undefined → không vẽ gì. */
  count: number | null | undefined;
  /** Tóm tắt một dòng (do màn dựng, không chứa dữ liệu cá nhân của khách). */
  children?: React.ReactNode;
  /** Link "Xem" tới đề xuất đầu tiên (hoặc trang chứa nó). */
  href?: string;
  onView?: () => void;
};

export function AiBar({ count, children, href, onView }: Props) {
  if (!count) return null;
  return (
    <div className="ai-bar" role="status">
      <Icon name="auto_awesome" />
      <span className="ai-bar-text">
        <b>AI</b> · Có {count} đề xuất{children ? <>: {children}</> : null}
      </span>
      {href ? (
        <Link href={href} className="ai-bar-view">
          Xem
        </Link>
      ) : onView ? (
        <button type="button" className="ai-bar-view" onClick={onView}>
          Xem
        </button>
      ) : null}
    </div>
  );
}

/** Chip nhỏ "AI đề xuất" đặt cạnh mã trên dòng liên quan (cột riêng hoặc cùng hàng với mã, không chồng dưới). */
export function AiChip() {
  return (
    <span className="ai-chip">
      <Icon name="auto_awesome" />
      AI đề xuất
    </span>
  );
}
