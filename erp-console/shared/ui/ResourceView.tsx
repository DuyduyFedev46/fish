"use client";

// Vẽ 3 trạng thái cho dữ liệu từ useResource: chưa có dữ liệu → đang tải / lỗi (nút Thử lại).
// Đã có dữ liệu mà tải lại lỗi → giữ nguyên số cũ + dải báo lỗi (không trắng trang, như bản cũ).
// Trạng thái RỖNG do từng màn tự vẽ (mỗi bảng có câu rỗng riêng).
// UI3: màn truyền `skeleton` → lần tải đầu vẽ khung chờ đúng hình thay cho icon quay; 403 hiện icon khoá.

import { Icon } from "./Icon";
import { ErrorBox, Loading } from "./StateBox";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import type { Resource } from "@/shared/lib/useResource";

export function ResourceView<T>({
  res,
  children,
  skeleton,
}: {
  res: Resource<T>;
  children: (data: T) => React.ReactNode;
  /** Khung chờ đúng hình (shared/ui/Skeleton). Không truyền → icon quay + chữ như cũ. */
  skeleton?: React.ReactNode;
}) {
  if (res.data === undefined) {
    if (res.error && !res.loading) {
      const forbidden = res.error instanceof ApiError && res.error.status === 403;
      return (
        <ErrorBox
          icon={forbidden ? "lock" : undefined}
          message={loadErrorText(res.error)}
          onRetry={() => void res.reload()}
        />
      );
    }
    return skeleton ? <>{skeleton}</> : <Loading label="Đang tải dữ liệu…" />;
  }
  return (
    <>
      {res.error != null && !res.loading && (
        <div className="alert-box err" role="alert">
          <Icon name="sync_problem" />
          <span>Không làm mới được, đang hiện số liệu lần tải trước. {loadErrorText(res.error)}</span>
        </div>
      )}
      {children(res.data)}
    </>
  );
}
