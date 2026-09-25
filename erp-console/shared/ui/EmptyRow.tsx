// Dòng rỗng trong bảng: đang tìm mà không khớp → "Không khớp tìm kiếm" (+ nút "Hiện tất cả" nếu truyền onClearSearch),
// còn lại → tiêu đề rỗng + câu hướng dẫn + một hành động kế tiếp (DESIGN.md: Empty = icon, tiêu đề, một câu, một hành động).
import { Icon } from "./Icon";

type Props = {
  cols: number;
  searching: boolean;
  emptyText?: string;
  /** Câu hướng dẫn dưới tiêu đề khi chưa có dữ liệu. */
  hint?: string;
  /** Hành động kế tiếp khi chưa có dữ liệu (nút/liên kết). */
  action?: React.ReactNode;
  /** Có → hiện nút "Hiện tất cả" khi tìm không khớp. */
  onClearSearch?: () => void;
};

export function EmptyRow({ cols, searching, emptyText = "Chưa có dữ liệu", hint, action, onClearSearch }: Props) {
  return (
    <tr className="empty-row">
      <td colSpan={cols}>
        <div className="state">
          <span className="state-ic">
            <Icon name={searching ? "search_off" : "inbox"} />
          </span>
          <b className="state-title">{searching ? "Không khớp tìm kiếm" : emptyText}</b>
          {searching ? (
            onClearSearch && (
              <>
                <p>Thử từ khoá khác, hoặc bỏ tìm để xem lại toàn bộ.</p>
                <button type="button" className="btn" onClick={onClearSearch}>
                  Hiện tất cả
                </button>
              </>
            )
          ) : (
            <>
              {hint && <p>{hint}</p>}
              {action}
            </>
          )}
        </div>
      </td>
    </tr>
  );
}
