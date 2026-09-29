import React from "react";
import Link from "next/link";
import type { InlineNode, PublicBlock, PublicBodyDoc } from "../types";
import { isExternalLink, isSafeHref } from "../safeHref";
import s from "./ArticleBody.module.css";

interface ArticleBodyProps {
  body: PublicBodyDoc;
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
    if (isExternalLink(node.href)) {
      return (
        <a
          key={index}
          href={node.href}
          target="_blank"
          rel="nofollow noopener noreferrer"
          className={s.link}
        >
          {content}
        </a>
      );
    }
    return (
      <Link key={index} href={node.href} className={s.link}>
        {content}
      </Link>
    );
  }

  return <React.Fragment key={index}>{content}</React.Fragment>;
}

function renderBlock(block: PublicBlock, index: number): React.ReactNode {
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
        <div key={index} className={s.itemCard}>
          <div className={s.itemCardInfo}>
            <span className={s.itemCardLabel}>Hải sản tươi vựa</span>
            <span className={s.itemCardCode}>Mặt hàng #{block.item_code}</span>
          </div>
          <Link href={`/shop#item-${block.item_code}`} className={s.itemCardBtn}>
            Xem trên Shop
          </Link>
        </div>
      );
    }

    default:
      return null;
  }
}

export default function ArticleBody({ body }: ArticleBodyProps) {
  if (!body || !Array.isArray(body.blocks)) {
    return null;
  }

  return (
    <article className={s.articleBody}>
      {body.blocks.map((block, idx) => renderBlock(block, idx))}
    </article>
  );
}
