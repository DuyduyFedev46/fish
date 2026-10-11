"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { getCatalog } from "@/lib/api";
import { pickHotline } from "@/lib/phone";
import { formatDate, formatPriceVnd } from "@/lib/format";
import type { CatalogItem, CatalogResponse } from "@/lib/types";
import { getSiteInfo } from "@/features/site/api";
import { fetchPublicEntries } from "@/features/content/api";
import type { PublicEntryListItem } from "@/features/content/types";
import { itemHref, toCardItem } from "@/features/catalog/cardItem";
import { groupIconOf } from "@/features/catalog/groupIcon";
import ShopFrame from "@/components/ShopFrame";
import CategoryTile from "@/components/catalog/CategoryTile";
import ProductCard from "@/components/catalog/ProductCard";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import Icon from "@/components/ui/Icon";
import Skeleton, { ProductCardSkeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { groupHref } from "@/components/shopLinks";
import { isSafeHref } from "@/features/content/safeHref";
import { DESKTOP_COMMITMENTS, MOBILE_COMMITMENTS, parseBanner, parseCommitments } from "../homeBlocks";
import type { BannerSlide, Commitment } from "../homeBlocks";
import { loadHomeBanner, loadHomeCommitments } from "../homeContent";
import s from "./HomeScreen.module.css";

const RAIL_LIMIT = 8;
const COMBO_LIMIT = 3;
const POST_LIMIT = 3;

// Khẩu hiệu thương hiệu (06-marketing K1, chữ giao diện ở code) và ô phụ thanh toán (06-marketing H6, ĐÃ ĐỐI CHIẾU:
// BR-TT-04 tiền thiếu thì không tự xác nhận). Chữ banner và cam kết lấy từ CMS (SHOP-5-03).
const BRAND_SLOGAN = "Từ cảng về bếp nhà bạn";
const PAYMENT_TILE = {
  eyebrow: "Chuyển khoản quét mã QR",
  title: "Tiền về đủ là đơn tự xác nhận",
  note: "Quét bằng app ngân hàng của bạn",
};

/** Món hết xếp cuối, còn lại giữ thứ tự catalog. */
function outLast(items: CatalogItem[]): CatalogItem[] {
  return [...items.filter((i) => i.stock_level !== "out"), ...items.filter((i) => i.stock_level === "out")];
}

/** Trang chủ Shop `/` (A1): banner, nhóm hàng, hàng đang có, combo, Góc bếp, cam kết. */
export default function HomeScreen() {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [retrying, setRetrying] = useState(false);
  const [hotline, setHotline] = useState<string | undefined>(undefined);
  const [posts, setPosts] = useState<PublicEntryListItem[]>([]);
  // undefined: đang tải; []: CMS chưa có, đã gỡ hoặc lỗi -> ẩn khối (5-03 AC2).
  const [slides, setSlides] = useState<BannerSlide[] | undefined>(undefined);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const load = useCallback((fresh: boolean) => {
    return getCatalog({ fresh })
      .then((c) => {
        setCatalog(c);
        setState("ready");
        return true;
      })
      .catch(() => {
        setState("error");
        return false;
      });
  }, []);

  useEffect(() => {
    let active = true;
    load(false);
    getSiteInfo()
      .then((info) => {
        if (!active) return;
        setHotline(pickHotline(info.seller?.phone, info.confirmation_policy?.hotline));
      })
      .catch(() => {});
    fetchPublicEntries({ page: 1 })
      .then((res) => active && setPosts((res.results || []).slice(0, POST_LIMIT)))
      .catch(() => active && setPosts([]));
    loadHomeBanner()
      .then((entry) => active && setSlides(entry ? parseBanner(entry.body) : []))
      .catch(() => active && setSlides([]));
    loadHomeCommitments()
      .then((entry) => active && setCommitments(entry ? parseCommitments(entry.body) : []))
      .catch(() => active && setCommitments([]));
    return () => {
      active = false;
    };
  }, [load]);

  async function retry() {
    setRetrying(true);
    const ok = await load(true);
    setRetrying(false);
    if (ok) headingRef.current?.focus();
  }

  const view = useMemo(() => {
    const items = catalog?.items ?? [];
    const simple = items.filter((i) => i.item_type === "SIMPLE" && i.stock_level !== "out").slice(0, RAIL_LIMIT);
    const combos = outLast(items.filter((i) => i.item_type === "BUNDLE")).slice(0, COMBO_LIMIT);
    const featuredCombo = combos.find((c) => c.stock_level !== "out") ?? combos[0];
    return { items, simple, combos, featuredCombo };
  }, [catalog]);

  const busy = state === "loading";

  return (
    <ShopFrame header="home" footer="full" bottomNav tone="muted">
      <div className={cx("container", s.page)}>
        <section className={s.hero} aria-label="Khuyến mãi">
          <HomeBanner slides={slides} headingRef={headingRef} />
          <div className={s.sideTiles}>
            {view.featuredCombo ? (
              <Link href={itemHref(view.featuredCombo.item_code)} className={cx(s.tile, s.tileCombo)}>
                <span className={s.tileText}>
                  <span className={s.tileEyebrow}>Combo nấu nhanh</span>
                  <span className={s.tileTitle}>{view.featuredCombo.name}</span>
                  <span className={cx(s.tilePrice, "num")}>
                    {formatPriceVnd(view.featuredCombo.price)} <span className={s.tileUnit}>/ combo</span>
                  </span>
                </span>
                <Icon name="combo" size={52} strokeWidth={1.2} />
              </Link>
            ) : null}
            <Link href="/shop/" className={cx(s.tile, s.tilePay)}>
              <span className={s.tileText}>
                <span className={s.tileEyebrowGood}>{PAYMENT_TILE.eyebrow}</span>
                <span className={s.tileTitle}>{PAYMENT_TILE.title}</span>
                <span className={s.tileNote}>{PAYMENT_TILE.note}</span>
              </span>
              <Icon name="qr" size={48} strokeWidth={1.3} />
            </Link>
          </div>
        </section>

        <div aria-busy={busy} className={s.data}>
          {busy ? <span className="visually-hidden" role="status">Đang tải hàng</span> : null}

          {state === "error" ? (
            <div className={s.errorBox}>
              <ErrorState
                hotline={hotline}
                title="Chưa tải được hàng"
                description="Kiểm tra kết nối mạng rồi thử lại"
                onRetry={retry}
                retrying={retrying}
              />
            </div>
          ) : (
            <>
              <section className={s.categories} aria-label="Danh mục">
                {busy ? (
                  <div className={s.catGrid} aria-hidden="true">
                    {Array.from({ length: 5 }, (_, i) => (
                      <div key={i} className={s.catSkeleton}>
                        <Skeleton width={48} height={48} radius="lg" />
                        <Skeleton width={36} height={12} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <nav aria-label="Danh mục" className={s.catGrid}>
                    {(catalog?.groups ?? []).map((g) => (
                      <CategoryTile
                        key={g.slug}
                        label={g.name}
                        href={groupHref(g.slug)}
                        icon={groupIconOf(g.slug)}
                        itemCount={g.item_count}
                      />
                    ))}
                    <span className={s.onlyDesktopFlex}>
                      <CategoryTile label="Tất cả" href="/shop/" icon="combo" itemCount={view.items.length} />
                    </span>
                  </nav>
                )}
              </section>

              <HomeCommitments items={commitments} />

              <section className={s.block} aria-labelledby="home-in-stock">
                <div className={s.blockHead}>
                  <h2 id="home-in-stock" className={s.blockTitle}>Đang có hàng</h2>
                  <Link href="/shop/" className={s.more}>Xem tất cả</Link>
                </div>
                {busy ? (
                  <div className={s.rail} aria-hidden="true">
                    <ProductCardSkeleton count={4} />
                  </div>
                ) : view.simple.length > 0 ? (
                  <div className={s.rail}>
                    {view.simple.map((it) => (
                      <ProductCard
                        key={it.item_code}
                        item={toCardItem(it)}
                        variant="rail"
                        href={itemHref(it.item_code)}
                        hotline={hotline}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon="fish"
                    title="Hiện chưa có hàng"
                    description="Liên hệ chúng tôi để hỏi hàng"
                    contactHref={hotline ? `tel:${hotline.replace(/[^\d+]/g, "")}` : undefined}
                    contactLabel="Liên hệ chúng tôi"
                  />
                )}
              </section>

              {!busy && view.combos.length > 0 ? (
                <div className={s.split}>
                  <section className={cx(s.panel, s.comboPanel)} aria-labelledby="home-combo">
                    <div className={s.blockHead}>
                      <h2 id="home-combo" className={s.blockTitle}>Combo nấu nhanh</h2>
                      <Link href="/shop/?type=combo" className={s.more}>Xem tất cả</Link>
                    </div>
                    <ul className={s.comboList}>
                      {view.combos.map((c) => (
                        <li key={c.item_code}>
                          <ProductCard item={toCardItem(c)} variant="row" href={itemHref(c.item_code)} />
                        </li>
                      ))}
                    </ul>
                  </section>
                  <KitchenCorner posts={posts} />
                </div>
              ) : (
                <KitchenCorner posts={posts} standalone />
              )}
            </>
          )}
        </div>
      </div>
    </ShopFrame>
  );
}

/**
 * Banner trang chủ từ CMS `home-banner` (SHOP-5-03). Đang tải: giữ khung (không nhảy bố cục). CMS không có slide:
 * ẩn banner, vẫn giữ một h1 ẩn cho trình đọc màn hình. Nhiều slide: chấm chọn slide, không tự chạy.
 */
function HomeBanner({
  slides,
  headingRef,
}: {
  slides: BannerSlide[] | undefined;
  headingRef: RefObject<HTMLHeadingElement>;
}) {
  const [index, setIndex] = useState(0);
  if (slides === undefined) {
    return <div className={s.banner} aria-hidden="true" />;
  }
  if (slides.length === 0) {
    return (
      <h1 ref={headingRef} tabIndex={-1} className="visually-hidden">
        Cá Về: hải sản cấp đông theo lô
      </h1>
    );
  }
  const current = slides[Math.min(index, slides.length - 1)];
  const button = current.button && isSafeHref(current.button.href) ? current.button : null;
  return (
    <div className={s.banner}>
      {current.image ? <img className={s.bannerImage} src={current.image.src} alt={current.image.alt} /> : null}
      <div className={s.bannerText}>
        <span className={s.eyebrow}>{BRAND_SLOGAN}</span>
        <h1 ref={headingRef} tabIndex={-1} className={s.bannerTitle}>
          {current.title}
        </h1>
        {current.subtitle ? <p className={s.bannerSub}>{current.subtitle}</p> : null}
        {button ? (
          <span className={s.bannerBtn}>
            <Button href={button.href} variant="on-brand" size="md">
              {button.label}
            </Button>
          </span>
        ) : null}
      </div>
      {current.image ? null : (
        <span className={s.bannerArt} aria-hidden="true">
          <Icon name="fish" size={300} strokeWidth={0.7} />
        </span>
      )}
      {slides.length > 1 ? (
        <div className={s.dots}>
          {slides.map((slide, i) => (
            <button
              key={`${i}-${slide.title}`}
              type="button"
              className={s.dot}
              aria-label={`Xem banner ${i + 1}: ${slide.title}`}
              aria-current={i === index ? "true" : undefined}
              onClick={() => setIndex(i)}
            >
              <span className={s.dotMark} />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** Dải cam kết từ CMS `home-commitments`: điện thoại 3 ô (tiêu đề), máy tính 2 ô (tiêu đề + mô tả). Rỗng: ẩn. */
function HomeCommitments({ items }: { items: Commitment[] }) {
  const shown = items.slice(0, Math.max(MOBILE_COMMITMENTS, DESKTOP_COMMITMENTS));
  if (shown.length === 0) return null;
  return (
    <section className={s.commitments} aria-label="Cam kết của Cá Về">
      {shown.map((c, i) => (
        <div key={`${i}-${c.title}`} className={cx(s.commit, i >= DESKTOP_COMMITMENTS && s.onlyMobileBlock)}>
          <span className={s.commitIcon}>
            <Icon name={c.icon} size={20} strokeWidth={1.6} />
          </span>
          <span className={s.commitText}>
            <span className={s.commitTitle}>{c.title}</span>
            {c.detail ? <span className={s.commitDetail}>{c.detail}</span> : null}
          </span>
        </div>
      ))}
    </section>
  );
}

/** Khối Góc bếp: bài mới nhất. Không có bài hoặc lỗi thì ẩn hẳn. */
function KitchenCorner({ posts, standalone = false }: { posts: PublicEntryListItem[]; standalone?: boolean }) {
  if (posts.length === 0) return null;
  return (
    <section className={cx(s.kitchen, standalone && s.kitchenAlone)} aria-labelledby="home-kitchen">
      <div className={s.blockHead}>
        <h2 id="home-kitchen" className={s.blockTitle}>Góc bếp</h2>
        <Link href="/blog/" className={s.more}>Xem bài viết</Link>
      </div>
      <ul className={s.posts}>
        {posts.map((p) => {
          const cover = p.cover_image ? p.cover_image.urls.md || p.cover_image.urls.sm : null;
          return (
            <li key={p.slug}>
              <Link href={`/blog/?slug=${encodeURIComponent(p.slug)}`} className={s.post}>
                <span className={s.postCover}>
                  <PostCover src={cover} />
                </span>
                <span className={s.postBody}>
                  {p.category ? <span className={s.postTag}>{p.category.name}</span> : null}
                  <span className={s.postTitle}>{p.title}</span>
                  <span className={cx(s.postDate, "num")}>{formatDate(p.published_at)}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** Ảnh bìa bài viết; không có ảnh hoặc ảnh lỗi thì hiện icon. */
function PostCover({ src }: { src: string | null }) {
  const [broken, setBroken] = useState(false);
  if (!src || broken) return <Icon name="fish" size={32} strokeWidth={1.4} />;
  return <img src={src} alt="" loading="lazy" onError={() => setBroken(true)} />;
}
