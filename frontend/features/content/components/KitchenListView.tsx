"use client";

// SHOP-5-05 AC1, AC4: danh sách Góc bếp (màn G1-KitchenList · DesktopKitchenList).
// Chip chuyên mục là link (`?category=`, nút Back hoạt động), chip đang chọn có `aria-current="page"`.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Breadcrumb from "@/components/ui/Breadcrumb";
import Chip from "@/components/ui/Chip";
import EmptyState from "@/components/ui/EmptyState";
import Icon from "@/components/ui/Icon";
import Skeleton, { ChipRowSkeleton } from "@/components/ui/Skeleton";
import Button from "@/components/ui/Button";
import { CATALOG_HREF, KITCHEN_HREF } from "@/components/shopLinks";
import { ApiError } from "@/lib/types";
import { fetchPublicCategories, fetchPublicEntries } from "../api";
import { setPageDescription, setPageMeta } from "../pageMeta";
import { categoryHref, postHref } from "../slugs";
import type { PublicCategory, PublicEntryListItem } from "../types";
import { ContentFailure } from "./ContentState";
import s from "./KitchenListView.module.css";

const PAGE_SIZE = 12;
// Chữ giao diện (06-marketing B7 G1, ĐÃ ĐỐI CHIẾU): CMS không có chỗ cho đoạn giới thiệu danh sách.
const LEAD = "Mẹo rã đông và cách nấu hải sản cấp đông.";
const LIST_TITLE = "Góc bếp | Cá Về";
const LIST_DESCRIPTION = "Góc bếp Cá Về: mẹo rã đông và cách nấu hải sản cấp đông tại nhà.";

type ListState =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "ready"; posts: PublicEntryListItem[]; total: number };

function pageHref(category: string, page: number): string {
  const q = new URLSearchParams();
  if (category) q.set("category", category);
  if (page > 1) q.set("page", String(page));
  const qs = q.toString();
  return qs ? `${KITCHEN_HREF}?${qs}` : KITCHEN_HREF;
}

export default function KitchenListView({ category, page }: { category: string; page: number }) {
  const [categories, setCategories] = useState<PublicCategory[] | null>(null);
  const [state, setState] = useState<ListState>({ kind: "loading" });
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    let active = true;
    fetchPublicCategories()
      .then((cats) => active && setCategories(cats || []))
      .catch(() => active && setCategories([]));
    return () => {
      active = false;
    };
  }, []);

  const load = useCallback(async () => {
    try {
      const res = await fetchPublicEntries({ category: category || undefined, page });
      const posts = res.results || [];
      setState({ kind: "ready", posts, total: res.count ?? res.total ?? posts.length });
    } catch (err) {
      // Trang vượt quá số trang trả 404: coi như rỗng (CMS-14 AC6).
      if (err instanceof ApiError && err.status === 404) setState({ kind: "ready", posts: [], total: 0 });
      else setState({ kind: "error" });
    }
  }, [category, page]);

  useEffect(() => {
    setState({ kind: "loading" });
    load();
  }, [load]);

  useEffect(() => {
    // Tiêu đề không lặp "| Cá Về" (02b §12, QA lô 1).
    setPageMeta({ title: LIST_TITLE, noindex: false });
    setPageDescription(LIST_DESCRIPTION);
  }, []);

  async function retry() {
    setRetrying(true);
    await load();
    setRetrying(false);
  }

  const currentCategory = categories?.find((c) => c.slug === category);
  const totalPages = state.kind === "ready" ? Math.max(1, Math.ceil(state.total / PAGE_SIZE)) : 1;

  return (
    <div className={s.page}>
      <div className={s.container}>
        <Breadcrumb
          items={
            currentCategory
              ? [{ label: "Trang chủ", href: "/" }, { label: "Góc bếp", href: KITCHEN_HREF }, { label: currentCategory.name }]
              : [{ label: "Trang chủ", href: "/" }, { label: "Góc bếp" }]
          }
        />
        <div className={s.headRow}>
          <div className={s.head}>
            <h1 className={s.title}>Góc bếp</h1>
            <p className={s.lead}>{LEAD}</p>
          </div>
          {categories === null ? (
            <ChipRowSkeleton count={4} />
          ) : categories.length > 0 ? (
            <nav aria-label="Chuyên mục" className={s.chips}>
              <ul className={s.chipList}>
                <li>
                  <Chip label="Tất cả" href={KITCHEN_HREF} selected={!category} />
                </li>
                {categories.map((c) => (
                  <li key={c.slug}>
                    <Chip label={c.name} href={categoryHref(c.slug)} selected={c.slug === category} />
                  </li>
                ))}
              </ul>
            </nav>
          ) : null}
        </div>

        {state.kind === "loading" ? (
          <ul className={s.grid} aria-busy="true">
            <li className="visually-hidden" role="status">
              Đang tải bài
            </li>
            {Array.from({ length: 4 }, (_, i) => (
              <li key={i} className={s.cell} aria-hidden="true">
                <div className={s.card}>
                  <span className={s.media}>
                    <Skeleton width="100%" height="100%" radius="md" />
                  </span>
                  <span className={s.body}>
                    <Skeleton width="30%" height={12} />
                    <Skeleton width="90%" height={16} />
                    <Skeleton width="70%" height={12} />
                  </span>
                </div>
              </li>
            ))}
          </ul>
        ) : state.kind === "error" ? (
          <ContentFailure kind="post" failure="error" onRetry={retry} retrying={retrying} />
        ) : state.posts.length === 0 ? (
          <div className={s.empty}>
            {category ? (
              <EmptyState icon="fish" title="Chưa có bài ở mục này." primaryAction={{ label: "Xem tất cả bài", href: KITCHEN_HREF }} />
            ) : (
              <EmptyState icon="fish" title="Góc bếp chưa có bài." primaryAction={{ label: "Xem hàng đang có", href: CATALOG_HREF }} />
            )}
          </div>
        ) : (
          <>
            <ul className={s.grid} aria-label={currentCategory ? `Bài viết mục ${currentCategory.name}` : "Bài viết"}>
              {state.posts.map((post) => (
                <li key={post.slug} className={s.cell}>
                  <PostCard post={post} />
                </li>
              ))}
            </ul>
            {totalPages > 1 ? (
              <nav className={s.pager} aria-label="Trang">
                {page > 1 ? (
                  <Button href={pageHref(category, page - 1)} variant="outline" shape="pill" iconStart={<Icon name="chevron-left" size={18} />}>
                    Trang trước
                  </Button>
                ) : (
                  <span />
                )}
                <span className={`${s.pageInfo} num`}>
                  Trang {page} / {totalPages}
                </span>
                {page < totalPages ? (
                  <Button href={pageHref(category, page + 1)} variant="outline" shape="pill" iconEnd={<Icon name="chevron-right" size={18} />}>
                    Trang sau
                  </Button>
                ) : (
                  <span />
                )}
              </nav>
            ) : null}
          </>
        )}
        <div className="visually-hidden" role="status" aria-live="polite">
          {state.kind === "ready" ? `${state.posts.length} bài` : ""}
        </div>
      </div>
    </div>
  );
}

function PostCard({ post }: { post: PublicEntryListItem }) {
  const cover = post.cover_image;
  const src = cover ? cover.urls.md || cover.urls.sm || cover.urls.lg : null;
  return (
    <article className={s.card}>
      <span className={s.media}>
        {src ? (
          <img src={src} alt="" loading="lazy" className={s.img} width={cover?.width} height={cover?.height} />
        ) : (
          <span className={s.placeholder} aria-hidden="true">
            <Icon name="fish" size={28} />
          </span>
        )}
      </span>
      <span className={s.body}>
        {post.category ? <span className={s.tag}>{post.category.name}</span> : null}
        <h2 className={s.cardTitle}>
          <Link href={postHref(post.slug)} className={s.cardLink}>
            {post.title}
          </Link>
        </h2>
        {post.excerpt ? <p className={s.excerpt}>{post.excerpt}</p> : null}
      </span>
    </article>
  );
}
