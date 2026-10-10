"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ApiError } from "@/lib/types";
import { formatDate } from "@/lib/format";
import {
  fetchPublicCategories,
  fetchPublicEntries,
  fetchPublicEntry,
} from "@/features/content/api";
import ShopFrame from "@/components/ShopFrame";
import ArticleBody from "@/features/content/components/ArticleBody";
import type {
  PublicCategory,
  PublicEntryDetail,
  PublicEntryListItem,
} from "@/features/content/types";
import { GONE_TITLE, LOAD_ERROR_TITLE, NOT_FOUND_TITLE, setPageMeta, withBrand } from "@/features/content/pageMeta";
import s from "./blog.module.css";

const PAGE_SIZE = 12;


function BaiVietContent() {
  const searchParams = useSearchParams();
  const slug = searchParams.get("slug");
  const categoryParam = searchParams.get("category");
  const pageParam = parseInt(searchParams.get("trang") || searchParams.get("page") || "1", 10);
  const currentPage = isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;

  const [entry, setEntry] = useState<PublicEntryDetail | null>(null);
  const [list, setList] = useState<PublicEntryListItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [categories, setCategories] = useState<PublicCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Tải danh mục chuyên mục cho thanh lọc
  useEffect(() => {
    if (!slug) {
      fetchPublicCategories()
        .then((cats) => setCategories(cats || []))
        .catch(() => setCategories([]));
    }
  }, [slug]);

  const loadData = () => {
    setLoading(true);
    setErrorStatus(null);
    setErrorMessage(null);

    if (slug) {
      fetchPublicEntry(slug)
        .then((data) => {
          setEntry(data);
          // Không lặp "| Cá Về" khi seo_title đã có thương hiệu (QA lô 1, ghi nợ lô 5b).
          setPageMeta({ title: withBrand(data.seo_title || data.title || ""), noindex: false });
        })
        .catch((err: any) => {
          if (err instanceof ApiError) {
            setErrorStatus(err.status);
            setErrorMessage(err.message);
          } else {
            setErrorStatus(500);
            setErrorMessage("Chưa tải được bài.");
          }
          // QA lô 2 L3: bài không có / đã gỡ -> tiêu đề đúng + một thẻ robots noindex.
          const status = err instanceof ApiError ? err.status : 500;
          if (status === 404) setPageMeta({ title: NOT_FOUND_TITLE, noindex: true });
          else if (status === 410) setPageMeta({ title: GONE_TITLE, noindex: true });
          else setPageMeta({ title: LOAD_ERROR_TITLE, noindex: true });
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      fetchPublicEntries({
        category: categoryParam || undefined,
        page: currentPage,
      })
        .then((res) => {
          setList(res.results || []);
          setTotalCount(res.count ?? res.total ?? 0);
          setPageMeta({ title: "Bài viết & Cẩm nang cá biển | Cá Về", noindex: false });
        })
        .catch((err: any) => {
          if (err instanceof ApiError && err.status === 404) {
            // CMS-14-AC6: page quá giới hạn trả 404
            setList([]);
            setTotalCount(0);
          } else {
            setErrorStatus(500);
            setErrorMessage(err?.message || "Chưa tải được danh sách bài.");
          }
        })
        .finally(() => {
          setLoading(false);
        });
    }
  };

  useEffect(() => {
    loadData();
  }, [slug, categoryParam, currentPage]);

  if (loading) {
    return (
      <div className={s.container}>
        <div className={s.loadingBox}>Đang tải nội dung...</div>
      </div>
    );
  }

  // 1. Trường hợp 410 GONE (CMS-13-AC4)
  if (errorStatus === 410) {
    return (
      <div className={s.container}>
        <div className={s.errorBox}>
          <h2 className={s.errorTitle}>Bài này không còn trên web</h2>
          <p className={s.errorDesc}>
            {errorMessage || "Nội dung bài viết đã được gỡ hoặc chuyển sang chuyên mục khác."}
          </p>
          <Link href="/shop" className={s.actionBtn}>
            Về cửa hàng Cá Về
          </Link>
        </div>
      </div>
    );
  }

  // 2. Trường hợp 404 NOT_FOUND (CMS-13-AC4)
  if (errorStatus === 404) {
    return (
      <div className={s.container}>
        <div className={s.errorBox}>
          <h2 className={s.errorTitle}>Không tìm thấy bài viết</h2>
          <p className={s.errorDesc}>
            Đường dẫn bài viết không tồn tại hoặc đã bị thay đổi.
          </p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
            <Link href="/blog" className={s.actionBtn} style={{ backgroundColor: "var(--ink-3)" }}>
              Xem bài viết khác
            </Link>
            <Link href="/shop" className={s.actionBtn}>
              Về cửa hàng
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 3. Trường hợp lỗi khác (500 hoặc mất mạng) (CMS-13-AC4)
  if (errorStatus && errorStatus >= 400) {
    return (
      <div className={s.container}>
        <div className={s.errorBox}>
          <h2 className={s.errorTitle}>Chưa tải được bài</h2>
          <p className={s.errorDesc}>
            Đã có lỗi xảy ra trong quá trình nạp dữ liệu. Vui lòng kiểm tra lại kết nối mạng.
          </p>
          <button type="button" onClick={loadData} className={s.actionBtn}>
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  // 4. Hiển thị chi tiết bài viết (CMS-13, CMS-06)
  if (slug && entry) {
    const cover = entry.cover_image;
    const coverSrc = cover ? (cover.urls.lg || cover.urls.md || cover.urls.sm) : null;
    const isUpdated = entry.updated_at && entry.published_at && entry.updated_at !== entry.published_at;

    return (
      <div className={s.container}>
        {/* Breadcrumb */}
        <nav className={s.breadcrumb} aria-label="Đường dẫn">
          <Link href="/">Trang chủ</Link>
          <span>/</span>
          <Link href="/blog">Bài viết</Link>
          {entry.category && (
            <>
              <span>/</span>
              <Link href={`/blog?category=${encodeURIComponent(entry.category.slug)}`}>
                {entry.category.name}
              </Link>
            </>
          )}
        </nav>

        {/* Header */}
        <header className={s.header}>
          {entry.category && (
            <Link
              href={`/blog?category=${encodeURIComponent(entry.category.slug)}`}
              className={s.categoryTag}
            >
              {entry.category.name}
            </Link>
          )}
          <h1 className={s.title}>{entry.title}</h1>
          <div className={s.metaBar}>
            <span className={s.author}>Tác giả: {entry.author || "Cá Về"}</span>
            <span>•</span>
            <span>Đăng ngày: {formatDate(entry.published_at)}</span>
            {isUpdated && (
              <>
                <span>•</span>
                <span>Cập nhật: {formatDate(entry.updated_at)}</span>
              </>
            )}
          </div>
        </header>

        {/* Ảnh bìa */}
        {cover && coverSrc && (
          <div className={s.coverWrapper}>
            <img
              src={coverSrc}
              alt={cover.alt || entry.title}
              width={cover.width}
              height={cover.height}
              className={s.coverImg}
            />
          </div>
        )}

        {/* Nội dung bài viết sạch, render qua ArticleBody an toàn kèm ItemCard */}
        <ArticleBody body={entry.body} postSlug={entry.slug} />
      </div>
    );
  }

  // 5. Hiển thị danh sách bài viết khi không có slug (CMS-14)
  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;
  const hasNextPage = currentPage < totalPages;
  const hasPrevPage = currentPage > 1;

  return (
    <div className={s.container}>
      <header className={s.header}>
        <h1 className={s.title}>Cẩm nang &amp; Kinh nghiệm từ cảng cá</h1>
        <p style={{ color: "var(--ink-3)", margin: 0 }}>
          Chia sẻ kinh nghiệm chọn hải sản tươi, bí quyết bảo quản và các công thức nấu ăn đậm đà vị biển.
        </p>
      </header>

      {/* Tabs lọc chuyên mục (CMS-14-AC2) */}
      <nav className={s.categoryTabs} aria-label="Chuyên mục bài viết">
        <Link
          href="/blog"
          className={`${s.tabItem} ${!categoryParam ? s.tabActive : ""}`}
        >
          Tất cả
        </Link>
        {categories.map((cat) => {
          const isActive = categoryParam === cat.slug;
          return (
            <Link
              key={cat.slug}
              href={`/blog?category=${encodeURIComponent(cat.slug)}`}
              className={`${s.tabItem} ${isActive ? s.tabActive : ""}`}
            >
              {cat.name}
            </Link>
          );
        })}
      </nav>

      {/* CMS-14-AC2: Chuyên mục không có bài -> hiện "Chưa có bài" */}
      {list.length === 0 ? (
        <div style={{ textAlign: "center", padding: "48px 16px", color: "var(--ink-3)" }}>
          Chưa có bài
        </div>
      ) : (
        <>
          <div className={s.listGrid}>
            {list.map((item) => {
              const coverSrc = item.cover_image
                ? (item.cover_image.urls.md || item.cover_image.urls.sm)
                : null;
              return (
                <Link
                  key={item.slug}
                  href={`/blog?slug=${encodeURIComponent(item.slug)}`}
                  className={s.card}
                >
                  {coverSrc && (
                    <div className={s.cardImgWrapper}>
                      <img
                        src={coverSrc}
                        alt={item.cover_image?.alt || item.title}
                        className={s.cardImg}
                        loading="lazy"
                      />
                    </div>
                  )}
                  <div className={s.cardBody}>
                    {item.category && (
                      <span
                        style={{
                          fontSize: "12px",
                          color: "var(--accent-text)",
                          fontWeight: 600,
                          marginBottom: "4px",
                        }}
                      >
                        {item.category.name}
                      </span>
                    )}
                    <h3 className={s.cardTitle}>{item.title}</h3>
                    <p className={s.cardExcerpt}>{item.excerpt}</p>
                    <span className={s.cardDate}>{formatDate(item.published_at)}</span>
                  </div>
                </Link>
              );
            })}
          </div>

          {/* Phân trang (CMS-14-AC1) */}
          {totalPages > 1 && (
            <div className={s.pagination}>
              <Link
                href={{
                  pathname: "/blog",
                  query: {
                    ...(categoryParam ? { category: categoryParam } : {}),
                    trang: currentPage - 1,
                  },
                }}
                className={`${s.pageBtn} ${!hasPrevPage ? s.pageDisabled : ""}`}
                aria-disabled={!hasPrevPage}
              >
                ← Trang trước
              </Link>

              <span className={s.pageInfo}>
                Trang {currentPage} / {totalPages}
              </span>

              <Link
                href={{
                  pathname: "/blog",
                  query: {
                    ...(categoryParam ? { category: categoryParam } : {}),
                    trang: currentPage + 1,
                  },
                }}
                className={`${s.pageBtn} ${!hasNextPage ? s.pageDisabled : ""}`}
                aria-disabled={!hasNextPage}
              >
                Trang sau →
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Khung mới (lô 1) bọc ngoài; giao diện bên trong do lô 5 viết lại. Danh sách = H2 + thanh đáy, bài chi tiết = H3.
function BaiVietFrame() {
  const slug = useSearchParams().get("slug");
  return (
    <ShopFrame
      header={slug ? "sub" : "sticky"}
      title={slug ? "Góc bếp" : undefined}
      footer="full"
      bottomNav={!slug}
      backHref="/blog/"
    >
      <BaiVietContent />
    </ShopFrame>
  );
}

export default function BaiVietPage() {
  return (
    <Suspense
      fallback={
        <ShopFrame header="sticky" footer="full" bottomNav>
          <div className={s.container}>
            <div className={s.loadingBox}>Đang tải nội dung...</div>
          </div>
        </ShopFrame>
      }
    >
      <BaiVietFrame />
    </Suspense>
  );
}
