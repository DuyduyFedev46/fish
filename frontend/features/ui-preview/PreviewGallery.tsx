"use client";

// Trang xem thử mọi component nền của lô 1 (SHOP-1-02). Chỉ được dựng khi build có NEXT_PUBLIC_UI_PREVIEW=1.
import { useRef, useState } from "react";
import type { ReactNode } from "react";
import CategoryTile from "@/components/catalog/CategoryTile";
import ImageFrame from "@/components/catalog/ImageFrame";
import PriceTag from "@/components/catalog/PriceTag";
import ProductCard from "@/components/catalog/ProductCard";
import StockBadge from "@/components/catalog/StockBadge";
import Banner from "@/components/ui/Banner";
import Button, { type ButtonVariant } from "@/components/ui/Button";
import Chip from "@/components/ui/Chip";
import Dialog from "@/components/ui/Dialog";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import FullscreenSheet from "@/components/ui/FullscreenSheet";
import Icon from "@/components/ui/Icon";
import IconButton from "@/components/ui/IconButton";
import Popover from "@/components/ui/Popover";
import { BottomSheet } from "@/components/ui/Sheet";
import Skeleton, { ChipRowSkeleton, ProductCardSkeleton } from "@/components/ui/Skeleton";
import Spinner from "@/components/ui/Spinner";
import TextLink from "@/components/ui/TextLink";
import { useToast } from "@/components/ui/Toast";
import { PREVIEW_HOTLINE, PREVIEW_ITEMS } from "./previewFixtures";
import s from "./PreviewGallery.module.css";

const VARIANTS: ButtonVariant[] = [
  "primary",
  "outline",
  "secondary",
  "ghost",
  "danger",
  "danger-text",
  "on-brand",
  "on-brand-outline",
];

function Section({ title, children, dark = false }: { title: string; children: ReactNode; dark?: boolean }) {
  return (
    <section className={s.section}>
      <h2 className={s.h2}>{title}</h2>
      <div className={dark ? s.dark : s.row}>{children}</div>
    </section>
  );
}

export default function PreviewGallery() {
  const toast = useToast();
  const [dialog, setDialog] = useState<null | "confirm" | "alert">(null);
  const [sheet, setSheet] = useState(false);
  const [full, setFull] = useState(false);
  const [popover, setPopover] = useState(false);
  const [loading, setLoading] = useState(false);
  const anchorRef = useRef<HTMLButtonElement>(null);

  return (
    <div className={s.page}>
      <h1 className={s.h1}>Xem thử component Shop</h1>

      <Section title="Button">
        {VARIANTS.map((v) => (
          <Button key={v} variant={v}>
            {v}
          </Button>
        ))}
        <Button size="lg">lg pill</Button>
        <Button size="sm">sm</Button>
        <Button iconStart={<Icon name="phone" size={18} />} variant="secondary">
          Liên hệ chúng tôi
        </Button>
        <Button
          loading={loading}
          loadingText="Đang đặt…"
          onClick={() => {
            setLoading(true);
            window.setTimeout(() => setLoading(false), 1500);
          }}
        >
          Đặt hàng
        </Button>
        <Button disabled>Đang tắt</Button>
      </Section>

      <Section title="IconButton + CartBadge" dark>
        <IconButton label="Giỏ hàng, 3 món" icon="cart" variant="on-brand" badgeCount={3} />
        <IconButton label="Gọi hotline" icon="phone" variant="on-brand" />
        <span className={s.light}>
          <IconButton label="Giỏ hàng, 12 món" icon="cart" badgeCount={12} />
          <IconButton label="Giỏ hàng" icon="cart" badgeCount={0} />
          <IconButton label="Đóng" icon="close" variant="close" />
          <IconButton label="Bỏ món khỏi giỏ" icon="trash" variant="danger-ghost" />
        </span>
      </Section>

      <Section title="Chip + TextLink">
        <Chip label="Tất cả" selected href="/ui-preview/" />
        <Chip label="Cá" href="/ui-preview/" />
        <Chip label="Mực" onClick={() => {}} />
        <Chip label="Gợi ý" variant="link" href="/ui-preview/" />
        <Chip label="Tìm gần đây" variant="link" icon="clock" href="/ui-preview/" />
        <TextLink href="/ui-preview/">liên kết trong câu</TextLink>
        <TextLink href="/ui-preview/" variant="standalone" iconEnd="chevron-right">
          Xem tất cả
        </TextLink>
        <TextLink href="https://example.com" external variant="standalone">
          Liên kết ngoài
        </TextLink>
      </Section>

      <Section title="PriceTag">
        <PriceTag amount="278000" unit="kg" size="card" />
        <PriceTag amount="450000" unit="combo" size="rail" />
        <PriceTag amount="278000" unit="kg" size="detail" />
        <PriceTag amount="278000" unit="kg" size="meta" />
        <PriceTag amount="417000" size="total" />
        <PriceTag amount="125000" size="line" />
        <PriceTag amount="300000" previousAmount="330000" unit="kg" size="rail" />
        <PriceTag amount="420000" unit="kg" size="card" tone="muted" />
      </Section>

      <Section title="StockBadge">
        <StockBadge level="low" />
        <StockBadge level="out" />
        <StockBadge level="low" size="md" />
        <StockBadge level="in" placement="inline" />
        <StockBadge level="low" placement="inline" />
        <StockBadge level="out" placement="inline" />
      </Section>

      <Section title="ImageFrame">
        <div className={s.frame}>
          <ImageFrame alt="" group="shrimp" ratio="3/2" />
        </div>
        <div className={s.frame}>
          <ImageFrame alt="Tôm mẫu" group="shrimp" ratio="1/1" topLeft={<StockBadge level="low" />} />
        </div>
        <div className={s.frame}>
          <ImageFrame alt="" group="crab" ratio="4/3" dimmed topRight={<StockBadge level="out" />} />
        </div>
        <div className={s.frame}>
          <ImageFrame
            alt="Ảnh minh hoạ"
            group="fish"
            ratio="1/1"
            image={PREVIEW_ITEMS[4].image}
            counter={{ current: 1, total: 3 }}
          />
        </div>
        <ImageFrame alt="" group="combo" squareSize={72} />
      </Section>

      <Section title="CategoryTile">
        <div className={s.tiles}>
          <CategoryTile label="Cá" href="/ui-preview/" icon="fish" itemCount={5} />
          <CategoryTile label="Tôm" href="/ui-preview/" icon="shrimp" itemCount={1} />
          <CategoryTile label="Mực" href="/ui-preview/" icon="squid" itemCount={4} />
          <CategoryTile label="Cua ghẹ" href="/ui-preview/" icon="crab" itemCount={2} />
          <CategoryTile label="Combo" href="/ui-preview/" icon="combo" itemCount={3} />
        </div>
      </Section>

      <Section title="ProductCard rail và row">
        <div className={s.cards}>
          {PREVIEW_ITEMS.map((it) => (
            <ProductCard key={it.itemCode} item={it} variant="rail" href="/ui-preview/" hotline={PREVIEW_HOTLINE} />
          ))}
        </div>
        <div className={s.rows}>
          {PREVIEW_ITEMS.slice(0, 4).map((it) => (
            <ProductCard key={it.itemCode} item={it} variant="row" href="/ui-preview/" />
          ))}
        </div>
      </Section>

      <Section title="Banner">
        <div className={s.stack}>
          <Banner tone="info" title="Thông tin">Một câu thông tin.</Banner>
          <Banner tone="success">Một câu thành công.</Banner>
          <Banner tone="warn" title="Cảnh báo">Một câu cảnh báo.</Banner>
          <Banner tone="crit" live="assertive">Một câu lỗi cách sửa.</Banner>
          <Banner tone="info" layout="strip">Dải một dòng</Banner>
        </div>
      </Section>

      <Section title="EmptyState, ErrorState, Skeleton, Spinner">
        <div className={s.stack}>
          <EmptyState
            icon="search"
            title="Không tìm thấy"
            description="Thử từ khoá khác hoặc xem các nhóm hàng bên dưới"
            suggestions={[
              { label: "Cá", href: "/ui-preview/" },
              { label: "Tôm", href: "/ui-preview/" },
            ]}
            contactHref="tel:0900000000"
          />
          <EmptyState
            icon="cart"
            framed={false}
            title="Giỏ hàng đang trống"
            primaryAction={{ label: "Xem hàng đang có", href: "/ui-preview/" }}
          />
          <ErrorState title="Chưa tải được hàng" description="Kiểm tra kết nối mạng rồi thử lại" onRetry={() => {}} />
          <ChipRowSkeleton />
          <div className={s.cards} aria-busy="true">
            <ProductCardSkeleton count={2} />
          </div>
          <Skeleton width={120} height={16} />
          <span className={s.row}>
            <Spinner size={16} label="Đang tải" />
            <Spinner size={36} label="Đang chờ" />
          </span>
        </div>
      </Section>

      <Section title="Dialog, BottomSheet, FullscreenSheet, Popover, Toast">
        <Button variant="secondary" onClick={() => setDialog("confirm")}>
          Mở Dialog xác nhận
        </Button>
        <Button variant="secondary" onClick={() => setDialog("alert")}>
          Mở Dialog cảnh báo
        </Button>
        <Button variant="secondary" onClick={() => setSheet(true)}>
          Mở BottomSheet
        </Button>
        <Button variant="secondary" onClick={() => setFull(true)}>
          Mở FullscreenSheet
        </Button>
        <span className={s.anchor}>
          <button
            ref={anchorRef}
            type="button"
            className={s.plain}
            aria-expanded={popover}
            onClick={() => setPopover((v) => !v)}
          >
            Mở Popover
          </button>
          <Popover open={popover} onOpenChange={setPopover} anchorRef={anchorRef} width={260}>
            <TextLink href="/ui-preview/" variant="nav">Cá thu</TextLink>
            <TextLink href="/ui-preview/" variant="nav">Cá ngừ</TextLink>
          </Popover>
        </span>
        <Button
          variant="outline"
          onClick={() =>
            toast.show({ message: "Đã thêm 1 kg Món mẫu vào giỏ", action: { label: "Xem giỏ", href: "/ui-preview/" } })
          }
        >
          Hiện Toast
        </Button>
      </Section>

      <Dialog
        open={dialog === "confirm"}
        onClose={() => setDialog(null)}
        title="Bỏ Món mẫu khỏi giỏ?"
        description="Mỗi món mua tối thiểu 1 kg. Bớt nữa sẽ bỏ món này khỏi giỏ."
        closeLabel="Đóng, giữ lại Món mẫu"
        actions={
          <>
            <Button variant="secondary" data-autofocus onClick={() => setDialog(null)}>
              Giữ lại
            </Button>
            <Button variant="danger" onClick={() => setDialog(null)}>
              Bỏ khỏi giỏ
            </Button>
          </>
        }
      />
      <Dialog
        open={dialog === "alert"}
        onClose={() => setDialog(null)}
        kind="alert"
        icon={{ name: "wifi-off", tone: "neutral" }}
        title="Chưa gửi được đơn"
        description="Đơn chưa được tạo. Kiểm tra mạng rồi thử lại."
        actions={
          <>
            <Button size="lg" data-autofocus onClick={() => setDialog(null)}>
              Thử lại
            </Button>
            <Button variant="ghost" onClick={() => setDialog(null)}>
              Để sau
            </Button>
          </>
        }
      />
      <BottomSheet
        open={sheet}
        onClose={() => setSheet(false)}
        icon={{ name: "warning", tone: "warn" }}
        title="Một số món vừa hết hàng"
        description="Có khách vừa đặt trước bạn."
        closeLabel="Đóng thông báo hết hàng"
        actions={
          <>
            <Button size="lg" onClick={() => setSheet(false)}>
              Cập nhật giỏ và đặt lại
            </Button>
            <Button variant="secondary" onClick={() => setSheet(false)}>
              Quay lại giỏ hàng
            </Button>
          </>
        }
      >
        <ProductCard item={PREVIEW_ITEMS[2]} variant="row" href="/ui-preview/" />
      </BottomSheet>
      <FullscreenSheet
        open={full}
        onClose={() => setFull(false)}
        title="Chọn vị trí giao hàng"
        closeLabel="Đóng, quay lại nhập tay"
        footer={<Button fullWidth size="lg" onClick={() => setFull(false)}>Xác nhận vị trí này</Button>}
      >
        <p className={s.pad}>Nội dung tấm gần toàn màn.</p>
      </FullscreenSheet>
    </div>
  );
}
