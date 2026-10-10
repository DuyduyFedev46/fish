import type { Metadata } from "next";
import ShopFrame from "@/components/ShopFrame";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import s from "./not-found.module.css";

// SHOP-1-09 AC1 (D11; 06-marketing C7): chữ 404 là chữ giao diện, để trong code. Màn: X1-NotFound404, DesktopNotFound404.
// Khung theo màn X1-NotFound404 (QA lô 1 L1): điện thoại H2 (logo, tìm, giỏ) + BottomNav, nền xám nhạt; máy tính header full, footer F1.
// Lệch bảng 02b §1.4 (ghi 404 dùng `sub`, không BottomNav): làm theo màn theo yêu cầu điều phối, ghi ở 03-dev-notes-mkt.md.
export const metadata: Metadata = {
  title: { absolute: "Không tìm thấy trang — Cá Về" },
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return (
    <ShopFrame header="sticky" footer="full" bottomNav tone="muted">
      <section className={s.box} aria-labelledby="not-found-title">
        <span className={s.icon} aria-hidden="true">
          <Icon name="fish" size={38} strokeWidth={1.4} />
        </span>
        <span className={`${s.code} num`}>404</span>
        <h1 id="not-found-title" className={s.title}>
          Không tìm thấy trang này
        </h1>
        <p className={s.text}>Link có thể đã cũ hoặc gõ nhầm.</p>
        <div className={s.actions}>
          <Button href="/" variant="primary" size="lg" shape="pill">
            Về trang chủ
          </Button>
          <Button href="/shop/" variant="outline" size="lg" shape="pill">
            Xem hàng đang có
          </Button>
        </div>
      </section>
    </ShopFrame>
  );
}
