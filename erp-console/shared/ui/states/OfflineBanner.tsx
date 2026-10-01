"use client";

// Mất mạng (UI-RULES §7): banner "Mất kết nối. Đang thử lại…" + nút Thử lại; dữ liệu cũ mờ đi (class `is-stale`
// do màn đặt lên khối dữ liệu, hoặc `stale` của DataTable) và ghi "Dữ liệu lúc dd/mm/yyyy hh:mm" theo mốc `asOf`.
// Shell đã đặt MỘT dải chung cho mọi màn: màn không đặt thêm. Màn đăng ký `asOf` + `onRetry` bằng
// `useOfflineRegistration()` (ListPage và usePagedList đã tự làm); dải đọc từ đó (props, nếu có, thắng).
// Làm mờ dữ liệu cũ: DataTable tự làm khi offline; khối khác dùng `useOffline()`.
// Hiện khi trình duyệt báo offline HOẶC màn báo `failed` (tải lại thất bại do mạng).
import { Icon } from "../Icon";
import { dateTime } from "@/shared/lib/format";
import { useOnline } from "@/shared/lib/useOnline";
import { useOfflineSource } from "./offlineSource";

type Props = {
  /** Mốc dữ liệu đang hiển thị (ISO; `as_of` của BE hoặc giờ tải xong). */
  asOf?: string | null;
  onRetry?: () => void;
  /** Màn đã thử tải lại mà thất bại vì mạng. */
  failed?: boolean;
};

/** Màn dùng để biết có nên làm mờ dữ liệu cũ không. */
export function useOffline(failed = false): boolean {
  const online = useOnline();
  return !online || failed;
}

export function OfflineBanner({ asOf: asOfProp, onRetry: onRetryProp, failed }: Props) {
  const offline = useOffline(failed);
  const source = useOfflineSource();
  if (!offline) return null;
  const asOf = asOfProp ?? source?.asOf ?? null;
  const onRetry = onRetryProp ?? source?.onRetry;
  return (
    <div className="offline-banner" role="alert">
      <Icon name="wifi_off" />
      <span className="ob-text">
        Mất kết nối. Đang thử lại…
        {asOf ? <span className="ob-asof"> Dữ liệu lúc {dateTime(asOf)}</span> : null}
      </span>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          <Icon name="refresh" />
          Thử lại
        </button>
      )}
    </div>
  );
}
