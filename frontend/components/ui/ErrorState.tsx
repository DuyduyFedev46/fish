import Button from "./Button";
import Icon from "./Icon";
import { ProductCardSkeleton } from "./Skeleton";
import s from "./ErrorState.module.css";

export interface ErrorStateProps {
  title: string;
  description: string;
  onRetry: () => void;
  /** true: đang gửi lại, nút có Spinner. */
  retrying?: boolean;
  /** Khung xương mờ đứng yên phía dưới, gợi chỗ hàng sẽ hiện. */
  showGhostGrid?: boolean;
}

/**
 * Lỗi tải dữ liệu cấp trang hoặc khối, có "Thử lại". Header, ô tìm và hàng lọc vẫn hiện (do trang lo).
 * Không hiện mã lỗi kỹ thuật hay chuỗi lỗi của máy chủ.
 */
export default function ErrorState({
  title,
  description,
  onRetry,
  retrying = false,
  showGhostGrid = true,
}: ErrorStateProps) {
  return (
    <div className={s.wrap}>
      <section className={s.error} role="alert">
        <span className={s.iconBox} aria-hidden="true">
          <Icon name="wifi-off" size={30} />
        </span>
        <h2 className={s.title}>{title}</h2>
        <p className={s.description}>{description}</p>
        <Button
          variant="primary"
          shape="pill"
          iconStart={<Icon name="refresh" size={18} />}
          loading={retrying}
          onClick={onRetry}
        >
          Thử lại
        </Button>
      </section>
      {showGhostGrid ? (
        <div className={s.ghost} aria-hidden="true">
          <ProductCardSkeleton count={4} animated={false} />
        </div>
      ) : null}
    </div>
  );
}
