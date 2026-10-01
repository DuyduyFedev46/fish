// Khung màn danh sách (UI-RULES §4): [tiêu đề + nút tạo mới góc phải] · tab · thanh lọc · thanh AI · bảng · chân.
// Chỉ là bố cục: dữ liệu, bộ lọc và bảng do màn truyền vào (FilterBar, AiBar, DataTable). Tên màn đã có ở topbar,
// nên `title` chỉ dùng khi màn cần tiêu đề phụ (vd tên tab); không bắt buộc.
// Mất mạng: truyền `asOf` + `onRetry` để dải mất mạng chung ghi "Dữ liệu lúc …" và có nút Thử lại
// (màn dùng `usePagedList` thì hook đã tự đăng ký, không cần truyền lại).
import { useOfflineRegistration } from "../states/offlineSource";

type Props = {
  title?: string;
  /** Nút tạo mới / hành động chính, góc phải hàng tiêu đề. */
  actions?: React.ReactNode;
  /** <Tabs …/> (dưới topbar, trên thanh lọc). */
  tabs?: React.ReactNode;
  /** Banner đầu danh sách (ConflictBanner…; dải mất mạng đã có sẵn trong khung). */
  banner?: React.ReactNode;
  /** <FilterBar …/>. */
  filters?: React.ReactNode;
  /** <AiBar …/>. */
  aiBar?: React.ReactNode;
  /** <DataTable …/>. */
  children: React.ReactNode;
  /** Chân bảng: nút "Tải thêm", số trang… */
  footer?: React.ReactNode;
  /** Mốc dữ liệu đang hiển thị (ISO). */
  asOf?: string | null;
  /** Hàm tải lại, cho nút Thử lại của dải mất mạng. */
  onRetry?: () => void;
  /** id cho vùng nội dung (nối aria-controls của tab). */
  id?: string;
};

export function ListPage({ title, actions, tabs, banner, filters, aiBar, children, footer, id, asOf, onRetry }: Props) {
  useOfflineRegistration(asOf || onRetry ? { asOf, onRetry } : null);
  return (
    <div className="lp" id={id}>
      {(title || actions) && (
        <div className="lp-head">
          {title ? <h2>{title}</h2> : <span />}
          {actions && <div className="lp-actions">{actions}</div>}
        </div>
      )}
      {tabs}
      {banner}
      {filters}
      {aiBar}
      {children}
      {footer && <div className="lp-foot">{footer}</div>}
    </div>
  );
}
