"use client";

// SHOP-5-05 AC2–AC4: bài Góc bếp (màn G2-KitchenArticle · DesktopKitchenArticle).
// Điện thoại: bài → "Món dùng trong bài" → "Bài liên quan". Máy tính: bài bên trái, cột phải dính gồm hai khối đó.

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Breadcrumb from "@/components/ui/Breadcrumb";
import { KITCHEN_HREF } from "@/components/shopLinks";
import { formatDate } from "@/lib/format";
import { ApiError } from "@/lib/types";
import { fetchPublicEntries, fetchPublicEntry } from "../api";
import { GONE_TITLE, LOAD_ERROR_TITLE, NOT_FOUND_TITLE, setPageDescription, setPageMeta, withBrand } from "../pageMeta";
import { categoryHref, postHref } from "../slugs";
import type { PublicEntryDetail, PublicEntryListItem } from "../types";
import ArticleBody from "./ArticleBody";
import ArticleItems, { itemCodesOf } from "./ArticleItems";
import { ContentFailure, ContentSkeleton, failureOf, type LoadFailure } from "./ContentState";
import s from "./KitchenArticleView.module.css";

const RELATED_MAX = 3;

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; entry: PublicEntryDetail }
  | { kind: "failed"; failure: LoadFailure };

export default function KitchenArticleView({ slug }: { slug: string }) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [retrying, setRetrying] = useState(false);
  const [related, setRelated] = useState<PublicEntryListItem[]>([]);

  const load = useCallback(async () => {
    try {
      const entry = await fetchPublicEntry(slug);
      setState({ kind: "ready", entry });
      // Không lặp "| Cá Về" khi seo_title đã có thương hiệu (02b §12, QA lô 1).
      setPageMeta({ title: withBrand(entry.seo_title || entry.title || ""), noindex: false });
      setPageDescription(entry.description || entry.excerpt);
    } catch (err) {
      const failure = failureOf(err instanceof ApiError ? err.status : undefined);
      setState({ kind: "failed", failure });
      setPageMeta({
        title: failure === "not-found" ? NOT_FOUND_TITLE : failure === "gone" ? GONE_TITLE : LOAD_ERROR_TITLE,
        noindex: true,
      });
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const entry = state.kind === "ready" ? state.entry : null;
  const categorySlug = entry?.category?.slug ?? "";

  // Bài liên quan: cùng chuyên mục, bỏ bài đang xem (06-marketing B7 G7). Lỗi thì ẩn khối.
  useEffect(() => {
    if (!entry) return;
    let active = true;
    fetchPublicEntries({ category: categorySlug || undefined })
      .then((res) => {
        if (!active) return;
        setRelated((res.results || []).filter((p) => p.slug !== entry.slug).slice(0, RELATED_MAX));
      })
      .catch(() => active && setRelated([]));
    return () => {
      active = false;
    };
  }, [entry, categorySlug]);

  const codes = useMemo(() => (entry ? itemCodesOf(entry.body?.blocks ?? []) : []), [entry]);

  async function retry() {
    setRetrying(true);
    await load();
    setRetrying(false);
  }

  if (state.kind === "loading") {
    return (
      <div className={s.page}>
        <div className={s.container}>
          <ContentSkeleton label="Đang tải bài" />
        </div>
      </div>
    );
  }
  if (state.kind === "failed") {
    return (
      <div className={s.page}>
        <div className={s.container}>
          <ContentFailure kind="post" failure={state.failure} onRetry={retry} retrying={retrying} />
        </div>
      </div>
    );
  }

  const post = state.entry;
  const cover = post.cover_image;
  const coverSrc = cover ? cover.urls.lg || cover.urls.md || cover.urls.sm : null;
  const crumbs = [
    { label: "Trang chủ", href: "/" },
    { label: "Góc bếp", href: KITCHEN_HREF },
    ...(post.category ? [{ label: post.category.name, href: categoryHref(post.category.slug) }] : []),
    { label: post.title },
  ];

  return (
    <div className={s.page}>
      <div className={s.container}>
        <div className={s.crumbs}>
          <Breadcrumb items={crumbs} />
        </div>
        <div className={s.columns}>
          <article className={s.article} aria-labelledby="post-title">
            {cover && coverSrc ? (
              <img
                src={coverSrc}
                srcSet={[
                  cover.urls.sm && `${cover.urls.sm} 480w`,
                  cover.urls.md && `${cover.urls.md} 960w`,
                  cover.urls.lg && `${cover.urls.lg} 1600w`,
                ]
                  .filter(Boolean)
                  .join(", ")}
                sizes="(max-width: 720px) 100vw, 720px"
                alt={cover.alt || ""}
                width={cover.width}
                height={cover.height}
                className={s.cover}
              />
            ) : null}
            <header className={s.head}>
              {post.category ? (
                <Link href={categoryHref(post.category.slug)} className={s.tag}>
                  {post.category.name}
                </Link>
              ) : null}
              <h1 id="post-title" className={s.title}>
                {post.title}
              </h1>
              <span className={`${s.meta} num`}>
                {post.author || "Cá Về"}
                {post.published_at ? ` · ${formatDate(post.published_at)}` : ""}
              </span>
            </header>
            <div className={s.body}>
              <ArticleBody body={post.body} variant="article" />
            </div>
          </article>

          <aside className={s.side} aria-label="Mua và đọc thêm">
            <ArticleItems codes={codes} postSlug={post.slug} />
            {related.length > 0 ? (
              <nav className={s.related} aria-labelledby="related-title">
                <h2 id="related-title" className={s.relatedTitle}>
                  Bài liên quan
                </h2>
                <ul className={s.relatedList}>
                  {related.map((p) => {
                    const src = p.cover_image ? p.cover_image.urls.sm || p.cover_image.urls.md : null;
                    return (
                      <li key={p.slug} className={s.relatedRow}>
                        <Link href={postHref(p.slug)} className={s.relatedLink}>
                          <span className={s.relatedThumb} aria-hidden="true">
                            {src ? <img src={src} alt="" loading="lazy" className={s.relatedImg} /> : null}
                          </span>
                          <span>{p.title}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            ) : null}
          </aside>
        </div>
      </div>
    </div>
  );
}
