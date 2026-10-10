import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Skeleton from "@/components/ui/Skeleton";
import { CATALOG_HREF, KITCHEN_HREF } from "@/components/shopLinks";
import s from "./ContentState.module.css";

/**
 * Ba trạng thái lỗi và khung xương dùng chung cho trang CMS (`/pages/`) và Góc bếp (`/blog/`).
 * Chữ theo 06-marketing C7 (SHOP-5-04 AC4, SHOP-5-05 AC4). Không hiện câu lỗi của máy chủ.
 */
export type LoadFailure = "not-found" | "gone" | "error";

export function failureOf(status: number | undefined): LoadFailure {
  if (status === 404) return "not-found";
  if (status === 410) return "gone";
  return "error";
}

const COPY = {
  post: {
    "not-found": {
      title: "Không tìm thấy bài này",
      description: "Bài có thể đã đổi hoặc chưa đăng.",
    },
    gone: {
      title: "Bài này không còn trên web",
      description: "Cá Về đã gỡ bài này. Bạn xem các bài khác ở Góc bếp.",
    },
    error: { title: "Chưa tải được bài", description: "Kiểm tra mạng rồi thử lại." },
  },
  page: {
    "not-found": {
      title: "Không tìm thấy trang này",
      description: "Trang có thể đã đổi hoặc chưa đăng.",
    },
    gone: {
      title: "Trang này không còn trên web",
      description: "Cá Về đã gỡ trang này.",
    },
    error: { title: "Chưa tải được trang", description: "Kiểm tra mạng rồi thử lại." },
  },
} as const;

export function ContentFailure({
  kind,
  failure,
  onRetry,
  retrying,
}: {
  /** post: bài Góc bếp. page: trang chính sách, liên hệ, cách mua. */
  kind: "post" | "page";
  failure: LoadFailure;
  onRetry: () => void;
  retrying?: boolean;
}) {
  const copy = COPY[kind][failure];
  if (failure === "error") {
    return (
      <div className={s.wrap}>
        <ErrorState
          title={copy.title}
          description={copy.description}
          onRetry={onRetry}
          retrying={retrying}
          showGhostGrid={false}
        />
      </div>
    );
  }
  return (
    <div className={s.wrap}>
      <EmptyState icon={kind === "post" ? "fish" : "info"} title={copy.title} description={copy.description} headingLevel={1}>
        <div className={s.actions}>
          {kind === "post" && failure === "gone" ? (
            <Button href={KITCHEN_HREF} shape="pill">
              Xem Góc bếp
            </Button>
          ) : kind === "post" ? (
            <>
              <Button href={KITCHEN_HREF} shape="pill">
                Xem bài khác ở Góc bếp
              </Button>
              <Button href="/" variant="outline" shape="pill">
                Về trang chủ
              </Button>
            </>
          ) : (
            <>
              <Button href="/" shape="pill">
                Về trang chủ
              </Button>
              <Button href={CATALOG_HREF} variant="outline" shape="pill">
                Xem hàng đang có
              </Button>
            </>
          )}
        </div>
      </EmptyState>
    </div>
  );
}

/** Khung xương bài/trang: tiêu đề + vài dòng chữ; vùng chứa có `aria-busy` và chữ ẩn. */
export function ContentSkeleton({ label = "Đang tải nội dung" }: { label?: string }) {
  return (
    <div className={s.skeleton} aria-busy="true">
      <span className="visually-hidden" role="status">
        {label}
      </span>
      <Skeleton width="40%" height={12} />
      <Skeleton width="80%" height={24} />
      <Skeleton width="100%" height={14} />
      <Skeleton width="92%" height={14} />
      <Skeleton width="64%" height={14} />
      <Skeleton width="100%" height={14} />
      <Skeleton width="85%" height={14} />
    </div>
  );
}
