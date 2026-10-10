import React from "react";
import Link from "next/link";
import type { InlineNode, PublicBlock, PublicBodyDoc, PublicImageUrls } from "../types";
import { isExternalLink, isInternalLink, isSafeHref } from "../safeHref";
import { headingAnchors } from "../headings";
import s from "./ArticleBody.module.css";

/**
 * Thân bài CMS (khối JSON đã kiểm ở máy chủ) cho trang chính sách và bài Góc bếp (SHOP-5-04, SHOP-5-05).
 * - Tiêu đề cấp 2 có `id` (cùng hàm với mục lục, `headings.ts`).
 * - Khối `item_card` KHÔNG vẽ ở đây: màn bài viết gom lại thành khối "Món dùng trong bài" (màn G2).
 * - Chữ luôn render dạng text (React tự thoát ký tự), link đi qua `safeHref` (SR-24 F9).
 */
interface ArticleBodyProps {
  body: PublicBodyDoc;
  /** policy: chữ 14–15 px như P1-Policy. article: chữ đọc 16–17 px như G2-KitchenArticle. */
  variant?: "policy" | "article";
}

// Bề rộng thật của 3 cỡ ảnh công khai (backend `CONTENT_IMAGE_WIDTHS`, không phóng to:
// ảnh gốc nhỏ hơn thì cỡ lớn = ảnh gốc, `block.width` là bề rộng cỡ lớn nhất).
const NOMINAL_WIDTHS: Array<[keyof PublicImageUrls, number]> = [
  ["sm", 480],
  ["md", 960],
  ["lg", 1600],
];
// Cột bài rộng tối đa 720px (màn DesktopKitchenArticle) -> ảnh không cần rộng hơn.
const IMAGE_SIZES = "(max-width: 720px) 100vw, 720px";

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

export function InlineText({ nodes }: { nodes: InlineNode[] }) {
  return <>{nodes.map((node, i) => renderInline(node, i))}</>;
}

function renderInline(node: InlineNode, index: number): React.ReactNode {
  let content: React.ReactNode = node.text;
  if (node.marks?.includes("bold")) content = <strong className={s.bold}>{content}</strong>;
  if (node.marks?.includes("italic")) content = <em>{content}</em>;

  if (node.href && isSafeHref(node.href)) {
    const href = node.href.trim();
    if (isExternalLink(href)) {
      return (
        <a key={index} href={href} target="_blank" rel="nofollow noopener noreferrer" className={s.link}>
          {content}
          <span className="visually-hidden"> (mở tab mới)</span>
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

export function BodyBlock({ block, id }: { block: PublicBlock; id?: string }) {
  switch (block.type) {
    case "heading":
      return block.level === 3 ? (
        <h3 className={s.heading3}>{block.text}</h3>
      ) : (
        <h2 id={id} className={s.heading2}>
          {block.text}
        </h2>
      );
    case "paragraph":
      return (
        <p className={s.paragraph}>
          <InlineText nodes={block.children} />
        </p>
      );
    case "quote":
      return (
        <blockquote className={s.quote}>
          <p>
            <InlineText nodes={block.children} />
          </p>
        </blockquote>
      );
    case "list": {
      const ListTag = block.ordered ? "ol" : "ul";
      return (
        <ListTag className={s.list}>
          {block.items.map((item, i) => (
            <li key={i}>
              <InlineText nodes={item} />
            </li>
          ))}
        </ListTag>
      );
    }
    case "image": {
      const src = block.urls.lg || block.urls.md || block.urls.sm;
      return (
        <figure className={s.figure}>
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
          {block.caption ? <figcaption className={s.caption}>{block.caption}</figcaption> : null}
        </figure>
      );
    }
    default:
      // item_card: màn bài viết tự gom; khối lạ: bỏ qua, không vỡ trang.
      return null;
  }
}

export default function ArticleBody({ body, variant = "article" }: ArticleBodyProps) {
  const blocks = body && Array.isArray(body.blocks) ? body.blocks : null;
  if (!blocks) return null;
  const { idByIndex } = headingAnchors(blocks);
  return (
    <div className={variant === "policy" ? `${s.body} ${s.policy}` : `${s.body} ${s.article}`}>
      {blocks.map((block, i) => (
        <BodyBlock key={i} block={block} id={idByIndex.get(i)} />
      ))}
    </div>
  );
}
