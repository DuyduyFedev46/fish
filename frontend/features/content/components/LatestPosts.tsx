"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchPublicEntries } from "../api";
import type { PublicEntryListItem } from "../types";
import s from "./LatestPosts.module.css";

function formatDate(isoStr?: string): string {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return isoStr;
  }
}

export default function LatestPosts() {
  const [posts, setPosts] = useState<PublicEntryListItem[]>([]);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let active = true;
    fetchPublicEntries({ page: 1 })
      .then((res) => {
        if (!active) return;
        const items = res.results || [];
        setPosts(items.slice(0, 3));
      })
      .catch(() => {
        if (!active) return;
        // CMS-14-AC4: API lỗi/tắt -> đánh dấu lỗi để ẩn khối
        setHasError(true);
      });

    return () => {
      active = false;
    };
  }, []);

  // CMS-14-AC4: Lỗi hoặc chưa có bài đăng -> ẩn hoàn toàn khối
  if (hasError || posts.length === 0) {
    return null;
  }

  return (
    <section className="section" style={{ backgroundColor: "#f8fafc" }}>
      <div className={s.container}>
        <div className={s.header}>
          <div>
            <h2 className="section-title" style={{ textAlign: "left", marginBottom: "4px" }}>
              Cẩm nang &amp; Mẹo hay từ vựa
            </h2>
            <p className="section-subtitle" style={{ textAlign: "left", margin: 0 }}>
              Kinh nghiệm chọn và chế biến hải sản tươi ngon đậm vị biển
            </p>
          </div>
          <Link href="/bai-viet" className={s.seeAllLink}>
            Xem tất cả bài viết →
          </Link>
        </div>

        <div className={s.grid}>
          {posts.map((post) => {
            const coverSrc = post.cover_image
              ? post.cover_image.urls.md || post.cover_image.urls.sm
              : null;
            return (
              <Link
                key={post.slug}
                href={`/bai-viet?slug=${encodeURIComponent(post.slug)}`}
                className={s.card}
              >
                {coverSrc && (
                  <div className={s.cardImgWrapper}>
                    <img
                      src={coverSrc}
                      alt={post.cover_image?.alt || post.title}
                      className={s.cardImg}
                      loading="lazy"
                    />
                  </div>
                )}
                <div className={s.cardBody}>
                  {post.category && (
                    <span className={s.cardCategory}>{post.category.name}</span>
                  )}
                  <h3 className={s.cardTitle}>{post.title}</h3>
                  <p className={s.cardExcerpt}>{post.excerpt}</p>
                  <span className={s.cardDate}>{formatDate(post.published_at)}</span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
