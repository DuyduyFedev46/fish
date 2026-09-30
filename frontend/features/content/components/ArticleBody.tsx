"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getCatalog } from "@/lib/api";
import type { CatalogItem } from "@/lib/types";
import ItemCard from "./ItemCard";
import type { InlineNode, PublicBlock, PublicBodyDoc, PublicImageUrls } from "../types";
import { isExternalLink, isInternalLink, isSafeHref } from "../safeHref";
import s from "./ArticleBody.module.css";

interface ArticleBodyProps {
  body: PublicBodyDoc;
  postSlug?: string;
}

/** Trạng thái catalog dùng chung cho mọi thẻ mặt hàng trong bài (SR-23 F7): nạp đúng 1 lần. */
type CatalogState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; byCode: Map<string, CatalogItem> };

// Bề rộng thật của 3 cỡ ảnh công khai (backend `CONTENT_IMAGE_WIDTHS`, không phóng to:
// ảnh gốc nhỏ hơn thì cỡ lớn = ảnh gốc, `block.width` là bề rộng cỡ lớn nhất).
const NOMINAL_WIDTHS: Array<[keyof PublicImageUrls, number]> = [
  ["sm", 480],
  ["md", 960],
  ["lg", 1600],
];
// Cột nội dung bài rộng tối đa 840px (bai-viet.module.css) -> ảnh không cần rộng hơn.
const IMAGE_SIZES = "(max-width: 840px) 100vw, 840px";

/** `srcset` 480w/960w/1600w (F8). Ảnh gốc hẹp hơn thì hạ bề rộng khai báo và bỏ cỡ trùng. */
function buildSrcSet(urls: PublicImageUrls, maxWidth: number): string | undefined {
  const cap = Number.isFinite(maxWidth) && maxWidth > 0 ? maxWidth : Infinity;
  const byWidth = new Map<number, string>();
  for (const [key, nominal] of NOMINAL_WIDTHS) {
    const url = urls[key];
    if (!url) continue;
    const w = Math.min(nominal, cap);
    if (!byWidth.has(w)) byWidth.set(w, url);
  }
  if (byWidth.size < 2) return undefined;
  return Array.from(byWidth.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([w, url]) => `${url} ${w}w`)
    .join(", ");
}

function renderInline(node: InlineNode, index: number): React.ReactNode {
  let content: React.ReactNode = node.text;

  if (node.marks) {
    if (node.marks.includes("bold")) {
      content = <strong className={s.bold}>{content}</strong>;
    }
    if (node.marks.includes("italic")) {
      content = <em className={s.italic}>{content}</em>;
    }
  }

  if (node.href && isSafeHref(node.href)) {
    const href = node.href.trim();
    if (isExternalLink(href)) {
      return (
        <a
          key={index}
          href={href}
          target="_blank"
          rel="nofollow noopener noreferrer"
          className={s.link}
        >
          {content}
        </a>
      );
    }
    if (isInternalLink(href)) {
      return (
        <Link key={index} href={href} className={s.link}>
          {content}
        </Link>
      );
    }
    // mailto:, tel: -> thẻ <a> thường, không mở tab mới.
    return (
      <a key={index} href={href} className={s.link}>
        {content}
      </a>
    );
  }

  return <React.Fragment key={index}>{content}</React.Fragment>;
}

function renderBlock(
  block: PublicBlock,
  index: number,
  postSlug: string | undefined,
  catalog: CatalogState
): React.ReactNode {
  switch (block.type) {
    case "heading": {
      if (block.level === 3) {
        return (
          <h3 key={index} className={s.heading3}>
            {block.text}
          </h3>
        );
      }
      return (
        <h2 key={index} className={s.heading2}>
          {block.text}
        </h2>
      );
    }

    case "paragraph": {
      return (
        <p key={index} className={s.paragraph}>
          {block.children.map((child, cIdx) => renderInline(child, cIdx))}
        </p>
      );
    }

    case "quote": {
      return (
        <blockquote key={index} className={s.quote}>
          <p>{block.children.map((child, cIdx) => renderInline(child, cIdx))}</p>
        </blockquote>
      );
    }

    case "list": {
      const ListTag = block.ordered ? "ol" : "ul";
      return (
        <ListTag key={index} className={s.list}>
          {block.items.map((item, itemIdx) => (
            <li key={itemIdx} className={s.listItem}>
              {item.map((child, cIdx) => renderInline(child, cIdx))}
            </li>
          ))}
        </ListTag>
      );
    }

    case "image": {
      const src = block.urls.lg || block.urls.md || block.urls.sm;
      return (
        <figure key={index} className={s.figure}>
          <div className={s.imageWrapper}>
            <img
              src={src}
              srcSet={buildSrcSet(block.urls, block.width)}
              sizes={IMAGE_SIZES}
              alt={block.alt}
              width={block.width}
              height={block.height}
              loading="lazy"
              className={s.img}
            />
          </div>
          {block.caption && <figcaption className={s.caption}>{block.caption}</figcaption>}
        </figure>
      );
    }

    case "item_card": {
      return (
        <ItemCard
          key={index}
          itemCode={block.item_code}
          postSlug={postSlug}
          loading={catalog.status === "loading"}
          item={catalog.status === "ready" ? catalog.byCode.get(block.item_code) ?? null : null}
        />
      );
    }

    default:
      return null;
  }
}

export default function ArticleBody({ body, postSlug }: ArticleBodyProps) {
  const blocks = body && Array.isArray(body.blocks) ? body.blocks : null;
  const hasItemCards = !!blocks && blocks.some((b) => b.type === "item_card");
  const [catalog, setCatalog] = useState<CatalogState>({ status: "loading" });

  // SR-23 F7: bài có N thẻ mặt hàng vẫn chỉ nạp catalog 1 lần (trước đây mỗi thẻ 1 request).
  // Bài không có thẻ nào thì không gọi API.
  useEffect(() => {
    if (!hasItemCards) return;
    let active = true;
    setCatalog({ status: "loading" });
    getCatalog()
      .then((items) => {
        if (!active) return;
        setCatalog({
          status: "ready",
          byCode: new Map((items || []).map((it) => [it.item_code, it])),
        });
      })
      .catch(() => {
        if (active) setCatalog({ status: "error" });
      });
    return () => {
      active = false;
    };
  }, [hasItemCards]);

  if (!blocks) {
    return null;
  }

  return (
    <article className={s.articleBody}>
      {blocks.map((block, idx) => renderBlock(block, idx, postSlug, catalog))}
    </article>
  );
}
