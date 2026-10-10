import { foldVietnamese, composeVietnamese } from "@/lib/text";
import { formatPriceVnd } from "@/lib/format";
import type { GroupIcon, ItemImage, Money, SaleUnit } from "@/lib/types";
import ImageFrame from "../catalog/ImageFrame";
import Chip from "../ui/Chip";
import { cx } from "../ui/cx";
import s from "./SearchSuggest.module.css";

export interface SuggestItem {
  itemCode: string;
  name: string;
  price: Money;
  unit: SaleUnit;
  group: GroupIcon;
  image?: ItemImage | null;
}

export interface SearchSuggestProps {
  /** id của listbox (SearchBox trỏ `aria-controls` tới đây). */
  listboxId: string;
  /** Tiền tố id của từng dòng: `${optionIdPrefix}-${i}`. */
  optionIdPrefix: string;
  query: string;
  items: SuggestItem[];
  /** Có dòng "Xem tất cả kết quả cho …" (khi đã gõ đủ 2 ký tự). */
  showViewAll: boolean;
  /** Chỉ số dòng đang trỏ bằng phím (0..items.length; dòng cuối là "Xem tất cả"); -1: không có. */
  activeIndex: number;
  recent: string[];
  onPickItem: (item: SuggestItem) => void;
  onViewAll: () => void;
  onPickRecent: (q: string) => void;
  onClearRecent: () => void;
  /** Điện thoại: panel cách ô 8 và kèm nền mờ do SearchBox lo. */
  className?: string;
}

/** Giữ tiêu điểm ở ô tìm khi bấm vào dòng gợi ý. */
function keepInputFocus(e: { preventDefault: () => void }) {
  e.preventDefault();
}

/** Tô đậm phần khớp (so khớp bỏ dấu) trong tên món. */
function Highlighted({ text, query }: { text: string; query: string }) {
  const composed = composeVietnamese(text);
  const needle = foldVietnamese(query.trim());
  const at = needle ? foldVietnamese(composed).indexOf(needle) : -1;
  if (at < 0) return <>{composed}</>;
  return (
    <>
      {composed.slice(0, at)}
      <strong className={s.match}>{composed.slice(at, at + needle.length)}</strong>
      {composed.slice(at + needle.length)}
    </>
  );
}

/**
 * Danh sách gợi ý khi gõ (SHOP-2-04): tối đa 5 món + "Xem tất cả" + "Tìm gần đây".
 * Trình bày: SearchBox giữ trạng thái combobox, container lọc catalog tại chỗ (không gọi API mỗi lần gõ).
 */
export default function SearchSuggest({
  listboxId,
  optionIdPrefix,
  query,
  items,
  showViewAll,
  activeIndex,
  recent,
  onPickItem,
  onViewAll,
  onPickRecent,
  onClearRecent,
  className,
}: SearchSuggestProps) {
  const hasQuery = showViewAll;
  return (
    <div className={cx(s.panel, className)}>
      {hasQuery ? (
        <>
          {items.length > 0 ? <p className={s.heading}>Gợi ý</p> : null}
          <ul id={listboxId} role="listbox" aria-label="Gợi ý tìm kiếm" className={s.list}>
            {items.map((it, i) => (
              <li
                key={it.itemCode}
                id={`${optionIdPrefix}-${i}`}
                role="option"
                aria-selected={activeIndex === i}
                className={cx(s.option, activeIndex === i && s.active)}
                onMouseDown={keepInputFocus}
                onClick={() => onPickItem(it)}
              >
                <ImageFrame image={it.image} alt="" group={it.group} ratio="1/1" squareSize={44} />
                <span className={s.name}>
                  <Highlighted text={it.name} query={query} />
                </span>
                <span className={cx(s.price, "num")}>
                  {formatPriceVnd(it.price)}
                  <span className={s.unit}> /{it.unit}</span>
                </span>
              </li>
            ))}
            <li
              id={`${optionIdPrefix}-${items.length}`}
              role="option"
              aria-selected={activeIndex === items.length}
              className={cx(s.viewAll, activeIndex === items.length && s.active)}
              onMouseDown={keepInputFocus}
              onClick={onViewAll}
            >
              Xem tất cả kết quả cho “{query.trim()}”
            </li>
          </ul>
        </>
      ) : null}
      {recent.length > 0 ? (
        <div className={s.recent}>
          <div className={s.recentHead}>
            <p className={s.heading}>Tìm gần đây</p>
            <button
              type="button"
              className={s.clear}
              aria-label="Xoá lịch sử tìm gần đây"
              onMouseDown={keepInputFocus}
              onClick={onClearRecent}
            >
              Xoá
            </button>
          </div>
          <ul className={s.chips}>
            {recent.map((q) => (
              <li key={q}>
                <Chip
                  variant="link"
                  label={q}
                  icon="clock"
                  href={`/shop/?q=${encodeURIComponent(q)}`}
                  onClick={() => onPickRecent(q)}
                />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
