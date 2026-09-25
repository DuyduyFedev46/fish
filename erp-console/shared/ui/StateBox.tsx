// 3 trạng thái chuẩn cho mọi màn dữ liệu (tải · lỗi có Thử lại · rỗng). S8+ dùng lại.
// UI5: lỗi/rỗng/403 cùng một kiểu — icon trong ô vuông 40px, tiêu đề 15/600, một câu, một hành động.
import { Icon } from "./Icon";
import { MSG } from "@/shared/lib/messages";

export function Loading({ label = "Đang tải…" }: { label?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <Icon name="progress_activity" className="spin" />
      {label}
    </div>
  );
}

export function ErrorBox({
  message = MSG.loadFailed,
  onRetry,
  icon = "error",
}: {
  message?: string;
  onRetry?: () => void;
  /** "lock" cho 403. */
  icon?: string;
}) {
  return (
    <div className="state state-err" role="alert">
      <span className="state-ic">
        <Icon name={icon} />
      </span>
      <p className="state-title">{message}</p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          <Icon name="refresh" />
          Thử lại
        </button>
      )}
    </div>
  );
}

export function Empty({
  icon = "inbox",
  title,
  children,
}: {
  icon?: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div className="big">
        <Icon name={icon} />
      </div>
      <h2>{title}</h2>
      {children && <p>{children}</p>}
    </div>
  );
}
