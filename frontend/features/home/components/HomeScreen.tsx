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
import { groupRepresentativeImage } from "@/features/catalog/catalogView";
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
import { DESKTOP_COMMITMENTS, MOBILE_COMMITMENTS, fallbackStripText, parseBanner, parseCommitments } from "../homeBlocks";
import type { BannerSlide, Commitment } from "../homeBlocks";
import { loadHomeBanner, loadHomeCommitments } from "../homeContent";
import s from "./HomeScreen.module.css";

const RAIL_LIMIT = 8;
const COMBO_LIMIT = 3;
const POST_LIMIT = 3;

// Khẩu hiệu thương hiệu (06-marketing K1, chữ giao diện ở code) và ô phụ thanh toán (06-marketing H6, ĐÃ ĐỐI CHIẾU:
// BR-TT-04 tiền thiếu thì không tự xác nhận). Chữ banner và cam kết lấy từ CMS (SHOP-5-03).
const BRAND_SLOGAN = "Từ cảng về bếp nhà bạn";
const DEFAULT_BANNER_TITLE = "Cá Về: hải sản cấp đông theo lô";
const DEFAULT_BANNER_BUTTON = { label: "Xem hàng đang có", href: "/shop/" } as const;
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
  const [minQtyKg, setMinQtyKg] = useState<string | undefined>(undefined);
  const [posts, setPosts] = useState<PublicEntryListItem[]>([]);
  // undefined: đang tải; []: CMS chưa có, đã gỡ hoặc lỗi -> hiện banner mặc định (GUI-10).
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
        setMinQtyKg(info.policies?.min_qty_kg);
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
  const effectiveMinQtyKg = minQtyKg ?? catalog?.items.find((i) => i.unit === "kg")?.min_qty ?? "0.5";

  return (
    <ShopFrame header="home" footer="full" bottomNav tone="muted">
      <div className={cx("container", s.page)}>
        <section className={s.hero} aria-label="Khuyến mãi">
          <HomeBanner slides={slides} headingRef={headingRef} minQtyKg={effectiveMinQtyKg} />
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
                        image={groupRepresentativeImage(view.items, g.slug)}
                        itemCount={g.item_count}
                      />
                    ))}
                    <span className={s.onlyDesktopFlex}>
                      <CategoryTile
                        label="Tất cả"
                        href="/shop/"
                        icon="combo"
                        image={groupRepresentativeImage(view.items, "all")}
                        itemCount={view.items.length}
                      />
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
 * Banner trang chủ từ CMS `home-banner` (SHOP-5-03, GUI-10).
 * - Đang tải (`slides === undefined`): giữ khung cùng nền minh hoạ để không nhảy bố cục.
 * - CMS 404 hoặc rỗng (`slides.length === 0`): hiện banner mặc định với câu chữ có sẵn trong code và nền minh hoạ nội bộ.
 * - Slide không có ảnh hoặc ảnh lỗi (`onError`): hiện nền minh hoạ biển/cảng/hải sản bằng CSS + SVG nội bộ.
 * - Slide có ảnh hợp lệ: hiện ảnh kèm lớp phủ tối đảm bảo tương phản chữ trắng.
 */
function HomeBanner({
  slides,
  headingRef,
  minQtyKg,
}: {
  slides: BannerSlide[] | undefined;
  headingRef: RefObject<HTMLHeadingElement>;
  minQtyKg?: string;
}) {
  const [index, setIndex] = useState(0);
  const [imageBroken, setImageBroken] = useState(false);

  const fallbackSlide: BannerSlide = {
    title: DEFAULT_BANNER_TITLE,
    subtitle: fallbackStripText(minQtyKg ?? "0.5"),
    button: DEFAULT_BANNER_BUTTON,
    image: null,
  };
  const current =
    slides && slides.length > 0
      ? slides[Math.min(index, slides.length - 1)]
      : fallbackSlide;
  const imageSrc = current.image?.src ?? null;

  useEffect(() => {
    setImageBroken(false);
  }, [imageSrc]);

  if (slides === undefined) {
    return (
      <div className={s.banner} aria-hidden="true">
        <HomeBannerIllustration />
      </div>
    );
  }

  const button = current.button && isSafeHref(current.button.href) ? current.button : null;
  const showImage = Boolean(current.image && !imageBroken);

  return (
    <div className={s.banner}>
      {showImage && current.image ? (
        <>
          <img
            className={s.bannerImage}
            src={current.image.src}
            alt={current.image.alt}
            onError={() => setImageBroken(true)}
          />
          <span className={s.bannerScrim} aria-hidden="true" />
        </>
      ) : (
        <HomeBannerIllustration />
      )}
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

/** Nền minh hoạ biển, cảng cá và hải sản cấp đông bằng CSS/SVG nội bộ khi slide không có ảnh (GUI-10). */
function HomeBannerIllustration() {
  return (
    <div className={s.bannerScene} aria-hidden="true">
      <span className={s.bannerGlow} />
      <svg
        className={s.bannerArtSvg}
        viewBox="0 0 680 320"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMaxYMid slice"
      >
        <g transform="translate(566 66)">
          <circle r="54" stroke="currentColor" strokeOpacity="0.12" strokeWidth="1.2" strokeDasharray="4 5" />
          <circle r="38" stroke="currentColor" strokeOpacity="0.16" strokeWidth="1" />
          <path d="M0 -46V-30M0 30V46M-46 0H-30M30 0H46" stroke="currentColor" strokeOpacity="0.2" strokeWidth="1.2" strokeLinecap="round" />
          <path
            d="M0 -14V14M-12 -7L12 7M-12 7L12 -7"
            stroke="currentColor"
            strokeOpacity="0.34"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          <circle r="3" fill="currentColor" fillOpacity="0.38" />
        </g>

        <g transform="translate(330 42)">
          <path d="M98 32L18 8L18 54Z" fill="currentColor" fillOpacity="0.06" />
          <path d="M98 32L190 6L190 56Z" fill="currentColor" fillOpacity="0.07" />
          <path d="M93 74L95 36H101L103 74Z" fill="currentColor" fillOpacity="0.22" />
          <rect x="94" y="29" width="8" height="7" rx="1.5" fill="currentColor" fillOpacity="0.34" />
          <path d="M92 29L98 23L104 29Z" fill="currentColor" fillOpacity="0.28" />
          <path d="M72 74H128" stroke="currentColor" strokeOpacity="0.22" strokeWidth="2" strokeLinecap="round" />

          <g transform="translate(136 44)">
            <path d="M8 28H68L58 42H16L8 28Z" fill="currentColor" fillOpacity="0.24" />
            <path d="M22 16H46V28H22V16Z" fill="currentColor" fillOpacity="0.2" />
            <path d="M36 4V28M36 6L54 18" stroke="currentColor" strokeOpacity="0.28" strokeWidth="1.6" strokeLinecap="round" />
            <circle cx="30" cy="22" r="2" fill="currentColor" fillOpacity="0.42" />
            <circle cx="38" cy="22" r="2" fill="currentColor" fillOpacity="0.42" />
          </g>
        </g>

        <path
          d="M140 168C215 142 285 186 365 162C445 138 515 178 595 154C630 144 658 148 680 156V320H140V168Z"
          fill="currentColor"
          fillOpacity="0.06"
        />
        <path
          d="M160 168C225 144 292 184 368 160C444 136 516 176 594 152C628 142 656 146 680 154"
          stroke="currentColor"
          strokeOpacity="0.18"
          strokeWidth="1.5"
          strokeLinecap="round"
        />

        <path
          d="M80 214C164 186 248 232 338 206C428 180 510 224 598 198C632 188 658 192 680 200V320H80V214Z"
          fill="currentColor"
          fillOpacity="0.09"
        />
        <path
          d="M110 212C186 186 262 228 346 204C430 180 512 222 596 196C630 186 658 190 680 198"
          stroke="currentColor"
          strokeOpacity="0.24"
          strokeWidth="1.8"
          strokeLinecap="round"
        />

        <path
          d="M0 262C96 238 192 278 294 252C396 226 494 270 596 244C630 236 658 240 680 248V320H0V262Z"
          fill="currentColor"
          fillOpacity="0.12"
        />
        <path
          d="M24 260C114 238 204 276 300 250C396 224 494 268 594 242C628 234 656 238 680 246"
          stroke="currentColor"
          strokeOpacity="0.28"
          strokeWidth="2"
          strokeLinecap="round"
        />

        <g transform="translate(362 126) rotate(-8)">
          <path d="M82 30L116 10L128 28Z" fill="currentColor" fillOpacity="0.22" />
          <path d="M138 30L158 18L164 32Z" fill="currentColor" fillOpacity="0.18" />
          <path d="M96 76L122 92L130 74Z" fill="currentColor" fillOpacity="0.2" />
          <path
            d="M14 54C42 22 98 16 156 30C182 36 204 46 220 54C204 62 182 72 156 78C98 92 42 86 14 54Z"
            fill="currentColor"
            fillOpacity="0.18"
            stroke="currentColor"
            strokeOpacity="0.46"
            strokeWidth="2.2"
          />
          <path
            d="M216 54L256 22L244 54L256 86L216 54Z"
            fill="currentColor"
            fillOpacity="0.24"
            stroke="currentColor"
            strokeOpacity="0.44"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <path d="M58 34C66 46 66 62 58 74" stroke="currentColor" strokeOpacity="0.42" strokeWidth="2" strokeLinecap="round" />
          <circle cx="42" cy="49" r="3.5" fill="currentColor" fillOpacity="0.58" />
          <path
            d="M36 54H198"
            stroke="currentColor"
            strokeOpacity="0.24"
            strokeWidth="1.4"
            strokeDasharray="6 6"
          />
          <path
            d="M84 32C88 42 86 48 82 52M106 30C110 40 108 48 104 52M128 31C132 40 130 48 126 52M150 34C153 42 151 48 148 52"
            stroke="currentColor"
            strokeOpacity="0.28"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </g>

        <g transform="translate(284 96) rotate(-12)">
          <path
            d="M0 16C12 4 34 4 52 16C34 28 12 28 0 16ZM50 16L64 6L60 16L64 26L50 16Z"
            fill="currentColor"
            fillOpacity="0.18"
            stroke="currentColor"
            strokeOpacity="0.34"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
          <circle cx="12" cy="14" r="1.8" fill="currentColor" fillOpacity="0.45" />
        </g>

        <g transform="translate(476 228) rotate(-4)">
          <path
            d="M0 14C10 3 28 3 44 14C28 25 10 25 0 14ZM42 14L54 5L50 14L54 23L42 14Z"
            fill="currentColor"
            fillOpacity="0.16"
            stroke="currentColor"
            strokeOpacity="0.32"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
          <circle cx="10" cy="12" r="1.6" fill="currentColor" fillOpacity="0.42" />
        </g>

        <g transform="translate(334 222) rotate(14)">
          <path
            d="M0 18L22 4L56 12L66 18L56 24L22 32L0 18Z"
            fill="currentColor"
            fillOpacity="0.15"
            stroke="currentColor"
            strokeOpacity="0.3"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
          <path
            d="M66 14C76 10 84 11 90 14M66 18C78 17 86 18 92 20M66 22C76 24 84 25 89 28"
            stroke="currentColor"
            strokeOpacity="0.28"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </g>

        <circle cx="348" cy="154" r="4" stroke="currentColor" strokeOpacity="0.28" strokeWidth="1.4" />
        <circle cx="332" cy="166" r="2.5" stroke="currentColor" strokeOpacity="0.24" />
        <circle cx="446" cy="108" r="3" stroke="currentColor" strokeOpacity="0.24" strokeWidth="1.2" />
        <circle cx="628" cy="188" r="4.5" stroke="currentColor" strokeOpacity="0.26" strokeWidth="1.4" />
        <circle cx="612" cy="204" r="2.5" fill="currentColor" fillOpacity="0.22" />
      </svg>
      <span className={s.bannerTextScrim} />
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
