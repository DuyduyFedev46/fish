"use client";

// Bảng danh sách mẫu (UI-RULES §4): full width, bấm dòng → trang chi tiết (`rowHref`), cột khai báo.
// Tự vẽ 4 trạng thái để màn không phải viết lại: ĐANG TẢI (khung xương, tiêu đề cột vẫn hiện — W6c), LỖI (có Thử lại),
// TRỐNG (icon + tiêu đề + 1 câu — W6a), KHÔNG THẤY (… khớp với "<từ khoá>" + Xoá tìm kiếm — W6b).
// Một ô một giá trị (§1.1): `render` trả đúng một giá trị; thông tin phụ → cột riêng.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Icon } from "../Icon";
import { useOffline } from "../states/OfflineBanner";

export type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  /** Căn phải (số tiền, số kg). `num` đã kèm căn phải + tabular-nums. */
  align?: "left" | "right";
  /** Chữ mono (mã chứng từ). */
  mono?: boolean;
  /** Số: tabular-nums + căn phải. */
  num?: boolean;
  /**
   * Cột giá vốn / lãi lỗ / tiền nhà cung cấp: icon khoá nhỏ ở tiêu đề (§1.7). DataTable tự BỎ cột này (cả tiêu đề
   * lẫn ô) khi `canViewCost` là false; BE vẫn là lớp chặn thật.
   */
  locked?: boolean;
  /** Độ rộng cột (CSS), vd "136px". Mặc định chia đều. */
  width?: string;
};

export type EmptyState = {
  icon?: string;
  title: string;
  /** Một câu: khi nào sẽ có dữ liệu. */
  hint?: string;
  action?: React.ReactNode;
};

type Props<T> = {
  columns: Column<T>[];
  /** null = chưa có dữ liệu lần đầu (cùng nghĩa với `loading`). */
  rows: T[] | null;
  rowKey: (row: T) => string | number;
  /** Đường dẫn trang chi tiết của dòng; có thì bấm dòng (và ô đầu) đi tới đó. */
  rowHref?: (row: T) => string | undefined;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  /** Từ khoá đang tìm: có từ khoá mà không có dòng → trạng thái "không thấy". */
  query?: string;
  onClearQuery?: () => void;
  /** "đơn hàng", "phiếu hoàn"… — dùng cho câu "Không tìm thấy <noun> khớp với …". */
  noun: string;
  empty: EmptyState;
  /** Người xem có quyền xem giá vốn (`view_costprice`) không. Cột `locked` chỉ hiện khi true (02b §4). */
  canViewCost: boolean;
  /** Mờ dữ liệu cũ. Bỏ trống = tự mờ khi trình duyệt mất mạng. */
  stale?: boolean;
  /** Nhãn đọc cho trình đọc màn hình. */
  caption: string;
  /** Số dòng khung xương. */
  skeletonRows?: number;
};

function colClass<T>(c: Column<T>): string {
  return [c.num || c.align === "right" ? "r" : "", c.num ? "num" : "", c.mono ? "mono" : ""].filter(Boolean).join(" ");
}

function SkeletonBody<T>({ columns, rows }: { columns: Column<T>[]; rows: number }) {
  const w = ["m", "l", "s", "m", "s", "l"];
  return (
    <>
      {Array.from({ length: rows }, (_, r) => (
        <tr key={r} className="lt-skel" aria-hidden="true">
          {columns.map((c, i) => (
            <td key={c.key}>
              <span className={`sk sk-${w[(r + i) % w.length]}`} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function DataTable<T>({
  columns: allColumns,
  rows,
  rowKey,
  rowHref,
  loading,
  error,
  onRetry,
  query,
  onClearQuery,
  noun,
  empty,
  canViewCost,
  stale: staleProp,
  caption,
  skeletonRows = 6,
}: Props<T>) {
  const router = useRouter();
  const offline = useOffline();
  const stale = staleProp ?? offline;
  // Chốt chặn: cột giá vốn không có quyền thì không vào DOM (kể cả khi màn quên lọc).
  const columns = allColumns.filter((c) => !c.locked || canViewCost);
  const isLoading = loading || (rows === null && !error);
  const hasRows = !!rows && rows.length > 0;
  const q = (query ?? "").trim();
  const colCount = columns.length;
  const widths = columns.map((c) => c.width ?? "auto");

  const onRowClick = (e: React.MouseEvent, href: string | undefined) => {
    if (!href) return;
    // Bấm vào nút/liên kết/ô nhập bên trong dòng thì để chúng tự xử lý.
    if ((e.target as HTMLElement).closest("a,button,input,select,textarea,label")) return;
    router.push(href);
  };

  let body: React.ReactNode = null;
  let stateRow: React.ReactNode = null;

  if (isLoading) {
    body = <SkeletonBody columns={columns} rows={skeletonRows} />;
  } else if (error) {
    stateRow = (
      <div className="state state-err" role="alert">
        <span className="state-ic">
          <Icon name="sync_problem" />
        </span>
        <p className="state-title">{error}</p>
        {onRetry && (
          <button type="button" className="btn" onClick={onRetry}>
            <Icon name="refresh" />
            Thử lại
          </button>
        )}
      </div>
    );
  } else if (!hasRows) {
    stateRow = q ? (
      <div className="state" role="status">
        <span className="state-ic">
          <Icon name="search_off" />
        </span>
        <b className="state-title">{`Không tìm thấy ${noun} khớp với “${q}”`}</b>
        {onClearQuery && (
          <button type="button" className="btn" onClick={onClearQuery}>
            Xoá tìm kiếm
          </button>
        )}
      </div>
    ) : (
      <div className="state" role="status">
        <span className="state-ic">
          <Icon name={empty.icon ?? "inbox"} />
        </span>
        <b className="state-title">{empty.title}</b>
        {empty.hint && <p>{empty.hint}</p>}
        {empty.action}
      </div>
    );
  } else if (rows) {
    body = rows.map((row) => {
      const href = rowHref?.(row);
      return (
        <tr
          key={rowKey(row)}
          className={href ? "lt-click" : undefined}
          onClick={href ? (e) => onRowClick(e, href) : undefined}
        >
          {columns.map((c, i) => {
            const cell = c.render(row);
            return (
              <td key={c.key} className={colClass(c) || undefined} data-label={c.header}>
                {i === 0 && href ? (
                  <Link href={href} className="lt-link">
                    {cell}
                  </Link>
                ) : (
                  cell
                )}
              </td>
            );
          })}
        </tr>
      );
    });
  }

  return (
    <div className={`lt-card${stale ? " is-stale" : ""}`} aria-busy={isLoading || undefined}>
      <div className="lt-scroll">
        <table className="lt">
          <caption className="sr-only">{caption}</caption>
          <colgroup>
            {widths.map((w, i) => (
              <col key={columns[i].key} style={w === "auto" ? undefined : { width: w }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} scope="col" className={colClass(c) || undefined}>
                  {c.header}
                  {c.locked && (
                    <>
                      <Icon name="lock" />
                      <span className="sr-only"> (cột giới hạn quyền xem)</span>
                    </>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{body}</tbody>
        </table>
      </div>
      {isLoading && (
        <div className="sr-only" role="status" aria-live="polite">
          Đang tải dữ liệu…
        </div>
      )}
      {stateRow && (
        <div className="lt-state" data-cols={colCount}>
          {stateRow}
        </div>
      )}
    </div>
  );
}
