"use client";

// SHOP-1-08: trang giới thiệu `/gioi-thieu/` đọc trang CMS `gioi-thieu` (02b §3.7.3, 06-marketing C2.3 cách (a)).
// Chữ nội dung lấy từ CMS (không viết cứng); chỉ chữ giao diện (nhãn, H1 khẩu hiệu K1, nút) nằm ở đây.
// Bố cục theo màn Landing / LandingMobile: hero → các mục theo H2 → mục cuối có nút mở bảng hàng.
// Khối `item_card` vẽ bằng ProductCard `row`, giá thật từ catalog (G1: không số kg tồn).

import { useCallback, useEffect, useState, type ReactNode } from "react";
import ShopFrame from "@/components/ShopFrame";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import TextLink from "@/components/ui/TextLink";
import ProductCard, { type ProductCardItem } from "@/components/catalog/ProductCard";
import Skeleton from "@/components/ui/Skeleton";
import { groupIconOf } from "@/features/catalog/groupIcon";
import { fetchPublicEntry } from "@/features/content/api";
import { isSafeHref } from "@/features/content/safeHref";
import type { InlineNode, PublicBlock, PublicEntryDetail } from "@/features/content/types";
import { getCatalog } from "@/lib/api";
import { ApiError, type CatalogItem } from "@/lib/types";
import s from "./AboutScreen.module.css";

const PAGE_SLUG = "gioi-thieu"; // naming: allow - slug trang CMS và URL công khai /gioi-thieu/ (decisions 2026-10-10)
const SHOP_HREF = "/shop/";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; entry: PublicEntryDetail }
  | { kind: "not-found" }
  | { kind: "gone" }
  | { kind: "error" };

type Section = { heading: string; blocks: PublicBlock[] };

/** Tách thân bài: các khối trước H2 đầu tiên là câu mở hero; mỗi H2 mở một mục. */
function splitSections(blocks: PublicBlock[]): { intro: PublicBlock[]; sections: Section[] } {
  const intro: PublicBlock[] = [];
  const sections: Section[] = [];
  for (const block of blocks) {
    if (block.type === "heading" && block.level === 2) {
      sections.push({ heading: block.text, blocks: [] });
    } else if (sections.length === 0) {
      intro.push(block);
    } else {
      sections[sections.length - 1].blocks.push(block);
    }
  }
  return { intro, sections };
}

function toCardItem(item: CatalogItem): ProductCardItem {
  return {
    itemCode: item.item_code,
    name: item.name,
    unit: item.unit,
    price: item.price,
    stockLevel: item.stock_level,
    shortNote: item.short_note || undefined,
    image: item.image,
    group: groupIconOf(item.group.slug, item.item_type),
    isCombo: item.item_type === "BUNDLE",
  };
}

function Inline({ nodes }: { nodes: InlineNode[] }) {
  return (
    <>
      {nodes.map((node, i) => {
        let content: ReactNode = node.text;
        if (node.marks?.includes("bold")) content = <strong>{content}</strong>;
        if (node.marks?.includes("italic")) content = <em>{content}</em>;
        if (node.href && isSafeHref(node.href)) {
          const external = /^https?:/i.test(node.href);
          return (
            <TextLink key={i} href={node.href} external={external}>
              {content}
            </TextLink>
          );
        }
        return <span key={i}>{content}</span>;
      })}
    </>
  );
}

function SectionBody({ blocks, catalog }: { blocks: PublicBlock[]; catalog: Map<string, CatalogItem> }) {
  const out: ReactNode[] = [];
  let i = 0;
  while (i < blocks.length) {
    const block = blocks[i];
    if (block.type === "item_card") {
      // Các thẻ hàng liền nhau gộp thành một danh sách; mã không còn trong catalog (ngưng bán, không giá) thì ẩn.
      const cards: CatalogItem[] = [];
      while (i < blocks.length && blocks[i].type === "item_card") {
        const found = catalog.get((blocks[i] as { item_code: string }).item_code);
        if (found) cards.push(found);
        i += 1;
      }
      if (cards.length > 0) {
        out.push(
          <ul key={`cards-${i}`} className={s.cards} aria-label="Món đang bán">
            {cards.map((item) => (
              <li key={item.item_code}>
                <ProductCard
                  variant="row"
                  item={toCardItem(item)}
                  href={`/shop/item/?code=${encodeURIComponent(item.item_code)}`}
                />
              </li>
            ))}
          </ul>
        );
      }
      continue;
    }
    if (block.type === "heading") {
      // H3 mở một thẻ: nhãn + các đoạn ngay sau nó (mục "Cấp đông theo lô" trên màn Landing).
      const body: PublicBlock[] = [];
      let j = i + 1;
      while (j < blocks.length && blocks[j].type !== "heading" && blocks[j].type !== "item_card") {
        body.push(blocks[j]);
        j += 1;
      }
      out.push(
        <article key={`h3-${i}`} className={s.card}>
          <h3 className={s.cardLabel}>{block.text}</h3>
          {body.map((b, k) => (
            <Block key={k} block={b} />
          ))}
        </article>
      );
      i = j;
      continue;
    }
    out.push(<Block key={`b-${i}`} block={block} />);
    i += 1;
  }
  return <>{out}</>;
}

function Block({ block }: { block: PublicBlock }) {
  switch (block.type) {
    case "paragraph":
      return (
        <p className={s.text}>
          <Inline nodes={block.children} />
        </p>
      );
    case "quote":
      return (
        <blockquote className={s.quote}>
          <Inline nodes={block.children} />
        </blockquote>
      );
    case "list":
      if (block.ordered) {
        return (
          <ol className={s.steps}>
            {block.items.map((nodes, k) => (
              <li key={k} className={s.step}>
                <span className={`${s.stepNum} num`} aria-hidden="true">
                  {String(k + 1).padStart(2, "0")}
                </span>
                <p className={s.text}>
                  <Inline nodes={nodes} />
                </p>
              </li>
            ))}
          </ol>
        );
      }
      return (
        <ul className={s.bullets}>
          {block.items.map((nodes, k) => (
            <li key={k}>
              <Inline nodes={nodes} />
            </li>
          ))}
        </ul>
      );
    default:
      // heading cấp 2 đã tách thành mục; ảnh chưa dùng trên trang này; item_card xử lý ở SectionBody.
      return null;
  }
}

export default function AboutScreen() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [catalog, setCatalog] = useState<Map<string, CatalogItem>>(new Map());
  const [attempt, setAttempt] = useState(0);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    let active = true;
    const entryPromise = fetchPublicEntry(PAGE_SLUG);
    // Catalog lỗi không chặn trang: chỉ ẩn thẻ hàng.
    const catalogPromise = getCatalog().catch(() => null);
    Promise.all([entryPromise, catalogPromise])
      .then(([entry, cat]) => {
        if (!active) return;
        setCatalog(new Map((cat?.items ?? []).map((item) => [item.item_code, item])));
        setState({ kind: "ready", entry });
      })
      .catch((err: unknown) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) setState({ kind: "not-found" });
        else if (err instanceof ApiError && err.status === 410) setState({ kind: "gone" });
        else setState({ kind: "error" });
      })
      .finally(() => {
        if (active) setRetrying(false);
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setRetrying(true);
    setAttempt((n) => n + 1);
  }, []);

  let content: ReactNode;
  if (state.kind === "loading") {
    content = (
      <div className={s.loading} aria-busy="true" aria-label="Đang tải trang giới thiệu">
        <Skeleton width="70%" height={32} />
        <Skeleton height={16} />
        <Skeleton width="60%" height={16} />
      </div>
    );
  } else if (state.kind === "not-found") {
    // 06-marketing C7: trang CMS trả 404.
    content = (
      <div className={s.state}>
        <EmptyState
          icon="fish"
          title="Không tìm thấy bài này"
          description="Bài có thể đã đổi hoặc chưa đăng."
          primaryAction={{ label: "Về trang chủ", href: "/" }}
        />
      </div>
    );
  } else if (state.kind === "gone") {
    content = (
      <div className={s.state}>
        <EmptyState
          icon="fish"
          title="Bài này không còn trên web"
          description="Cá Về đã gỡ bài này. Bạn xem các bài khác ở Góc bếp."
          primaryAction={{ label: "Xem Góc bếp", href: "/bai-viet/" }}
        />
      </div>
    );
  } else if (state.kind === "error") {
    content = (
      <div className={s.state}>
        <ErrorState
          title="Chưa tải được trang"
          description="Kiểm tra mạng rồi thử lại."
          onRetry={retry}
          retrying={retrying}
          showGhostGrid={false}
        />
      </div>
    );
  } else {
    const { intro, sections } = splitSections(state.entry.body.blocks);
    content = (
      <>
        <section className={s.hero} aria-labelledby="about-title">
          <div className={s.inner}>
            <span className={s.badge}>Hải sản cấp đông theo lô</span>
            <h1 id="about-title" className={s.heroTitle}>
              Từ cảng về bếp nhà bạn
            </h1>
            {intro.map((block, k) => (
              <div key={k} className={s.heroText}>
                <Block block={block} />
              </div>
            ))}
            <div className={s.heroActions}>
              <Button href={SHOP_HREF} variant="on-brand" size="lg">
                Xem hàng đang có
              </Button>
              {sections.length > 0 ? (
                <Button href="#cach-lam" variant="on-brand-outline" size="lg">
                  Cách chúng tôi làm
                </Button>
              ) : null}
            </div>
          </div>
        </section>
        {sections.map((section, k) => {
          const hasCards = section.blocks.some((b) => b.type === "item_card");
          const isLast = k === sections.length - 1;
          const className = [s.section, hasCards ? s.tinted : "", isLast ? s.cta : ""].filter(Boolean).join(" ");
          return (
            <section
              key={k}
              id={k === 0 ? "cach-lam" : undefined}
              className={className}
              aria-labelledby={`about-section-${k}`}
            >
              <div className={s.inner}>
                <h2 id={`about-section-${k}`} className={s.h2}>
                  {section.heading}
                </h2>
                <SectionBody blocks={section.blocks} catalog={catalog} />
                {hasCards || isLast ? (
                  <div className={s.sectionActions}>
                    <Button href={SHOP_HREF} variant="primary" size="lg">
                      {isLast ? "Mở bảng hàng" : "Xem hàng đang có"}
                    </Button>
                  </div>
                ) : null}
              </div>
            </section>
          );
        })}
      </>
    );
  }

  return (
    <ShopFrame header="sub" title="Giới thiệu" footer="full" bottomNav={false} backHref="/">
      {content}
    </ShopFrame>
  );
}
