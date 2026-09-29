"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ApiError } from "@/lib/types";
import { fetchPublicEntry } from "@/features/content/api";
import ArticleBody from "@/features/content/components/ArticleBody";
import type { PublicEntryDetail } from "@/features/content/types";
import s from "./trang.module.css";

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

function TrangContent() {
  const searchParams = useSearchParams();
  const slug = searchParams.get("slug");

  const [entry, setEntry] = useState<PublicEntryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadData = () => {
    if (!slug) {
      setLoading(false);
      setErrorStatus(404);
      setErrorMessage("Không tìm thấy trang.");
      return;
    }

    setLoading(true);
    setErrorStatus(null);
    setErrorMessage(null);

    fetchPublicEntry(slug)
      .then((data) => {
        setEntry(data);
        if (data.seo_title || data.title) {
          document.title = `${data.seo_title || data.title} | Cá Về`;
        }
        if (data.description) {
          const metaDesc = document.querySelector('meta[name="description"]');
          if (metaDesc) {
            metaDesc.setAttribute("content", data.description);
          }
        }
      })
      .catch((err: any) => {
        if (err instanceof ApiError) {
          setErrorStatus(err.status);
          setErrorMessage(err.message);
        } else {
          setErrorStatus(500);
          setErrorMessage("Chưa tải được trang.");
        }
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [slug]);

  if (loading) {
    return (
      <div className={s.container}>
        <div className={s.loadingBox}>Đang tải nội dung...</div>
      </div>
    );
  }

  // 1. Trường hợp 410 GONE (CMS-12-AC4)
  if (errorStatus === 410) {
    return (
      <div className={s.container}>
        <div className={s.errorBox}>
          <h2 className={s.errorTitle}>Trang này không còn trên web</h2>
          <p className={s.errorDesc}>
            {errorMessage || "Nội dung trang này đã được gỡ bỏ khỏi website."}
          </p>
          <div className={s.errorActions}>
            <Link href="/shop/" className={s.primaryBtn}>
              Về cửa hàng
            </Link>
            <Link href="/" className={s.secondaryBtn}>
              Về trang chủ
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 2. Trường hợp 404 NOT_FOUND (CMS-13-AC4)
  if (errorStatus === 404 || !entry) {
    return (
      <div className={s.container}>
        <div className={s.errorBox}>
          <h2 className={s.errorTitle}>Không tìm thấy trang</h2>
          <p className={s.errorDesc}>
            Trang bạn đang tìm kiếm không tồn tại hoặc đã được chuyển sang địa chỉ khác.
          </p>
          <div className={s.errorActions}>
            <Link href="/shop/" className={s.primaryBtn}>
              Về cửa hàng
            </Link>
            <Link href="/" className={s.secondaryBtn}>
              Về trang chủ
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 3. Trường hợp lỗi khác (mất mạng, server 500) (CMS-13-AC7)
  if (errorStatus) {
    return (
      <div className={s.container}>
        <div className={s.errorBox}>
          <h2 className={s.errorTitle}>Chưa tải được trang</h2>
          <p className={s.errorDesc}>
            {errorMessage || "Đã xảy ra lỗi trong quá trình nạp nội dung. Vui lòng thử lại."}
          </p>
          <div className={s.errorActions}>
            <button type="button" onClick={loadData} className={s.primaryBtn}>
              Thử lại
            </button>
            <Link href="/shop/" className={s.secondaryBtn}>
              Về cửa hàng
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const effectiveDateStr = formatDate(entry.effective_from || entry.published_at || entry.updated_at);

  return (
    <article className={s.container}>
      <nav className={s.breadcrumb} aria-label="Đường dẫn">
        <Link href="/">Trang chủ</Link>
        <span>/</span>
        <span aria-current="page">{entry.title}</span>
      </nav>

      <header className={s.header}>
        <h1 className={s.title}>{entry.title}</h1>
        {effectiveDateStr && (
          <div className={s.effectiveDate}>
            Có hiệu lực từ {effectiveDateStr}
          </div>
        )}
      </header>

      <div className={s.contentWrapper}>
        <ArticleBody body={entry.body} />
      </div>
    </article>
  );
}

export default function TrangPage() {
  return (
    <Suspense
      fallback={
        <div className={s.container}>
          <div className={s.loadingBox}>Đang tải trang...</div>
        </div>
      }
    >
      <TrangContent />
    </Suspense>
  );
}
