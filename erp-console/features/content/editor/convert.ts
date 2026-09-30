import type { Block, BodyDoc, InlineNode } from "../types";
import { isSafeHref } from "./safeHref";

function inlinesFromTiptap(contentNodes: any[] = []): InlineNode[] {
  const result: InlineNode[] = [];
  for (const node of contentNodes) {
    if (!node || node.type !== "text" || !node.text) continue;
    const item: InlineNode = { text: String(node.text) };

    if (Array.isArray(node.marks)) {
      const validMarks: Array<"bold" | "italic"> = [];
      let href: string | undefined;

      for (const m of node.marks) {
        if (!m || typeof m.type !== "string") continue;
        if (m.type === "bold" && !validMarks.includes("bold")) {
          validMarks.push("bold");
        } else if (m.type === "italic" && !validMarks.includes("italic")) {
          validMarks.push("italic");
        } else if (m.type === "link" && m.attrs?.href) {
          const candidate = String(m.attrs.href).trim();
          if (isSafeHref(candidate)) {
            href = candidate;
          }
        }
      }

      if (validMarks.length > 0) item.marks = validMarks;
      if (href) item.href = href;
    }

    result.push(item);
  }
  return result;
}

function inlinesToTiptap(children: InlineNode[] = []): any[] {
  const result: any[] = [];
  for (const child of children) {
    if (!child || !child.text) continue;
    const marks: any[] = [];
    if (child.marks?.includes("bold")) marks.push({ type: "bold" });
    if (child.marks?.includes("italic")) marks.push({ type: "italic" });
    if (child.href && isSafeHref(child.href)) {
      marks.push({ type: "link", attrs: { href: child.href } });
    }

    result.push({
      type: "text",
      text: child.text,
      ...(marks.length > 0 ? { marks } : {}),
    });
  }
  return result;
}

/**
 * Chuyển đổi JSON từ Tiptap sang format BodyDoc của backend.
 * Bỏ qua mọi node / HTML lạ không nằm trong schema cho phép (CMS-03-AC5, AC6).
 */
export function tiptapToBody(tiptapJson: any): BodyDoc {
  if (!tiptapJson || tiptapJson.type !== "doc" || !Array.isArray(tiptapJson.content)) {
    return { type: "doc", blocks: [] };
  }

  const blocks: Block[] = [];

  for (const node of tiptapJson.content) {
    if (!node || typeof node.type !== "string") continue;

    if (node.type === "heading") {
      const level = node.attrs?.level === 3 ? 3 : 2;
      const text = (node.content || [])
        .map((c: any) => (c.type === "text" ? c.text || "" : ""))
        .join("");
      blocks.push({ type: "heading", level, text });
    } else if (node.type === "paragraph") {
      const children = inlinesFromTiptap(node.content);
      blocks.push({ type: "paragraph", children });
    } else if (node.type === "blockquote") {
      // Tiptap blockquote thường chứa paragraph
      const children: InlineNode[] = [];
      for (const p of node.content || []) {
        if (p.type === "paragraph") {
          children.push(...inlinesFromTiptap(p.content));
        } else if (p.type === "text") {
          children.push(...inlinesFromTiptap([p]));
        }
      }
      blocks.push({ type: "quote", children });
    } else if (node.type === "bulletList" || node.type === "orderedList") {
      const ordered = node.type === "orderedList";
      const items: InlineNode[][] = [];
      for (const li of node.content || []) {
        if (li.type === "listItem") {
          const liChildren: InlineNode[] = [];
          for (const p of li.content || []) {
            if (p.type === "paragraph") {
              liChildren.push(...inlinesFromTiptap(p.content));
            } else if (p.type === "text") {
              liChildren.push(...inlinesFromTiptap([p]));
            }
          }
          items.push(liChildren);
        }
      }
      blocks.push({ type: "list", ordered, items });
    } else if (node.type === "caveImage" || node.type === "image") {
      const imageId = Number(node.attrs?.imageId || node.attrs?.id);
      if (Number.isInteger(imageId) && imageId > 0) {
        blocks.push({
          type: "image",
          image_id: imageId,
          alt: node.attrs?.alt ? String(node.attrs.alt) : undefined,
          caption: node.attrs?.caption ? String(node.attrs.caption) : undefined,
        });
      }
    } else if (node.type === "itemCard") {
      const itemCode = node.attrs?.itemCode ? String(node.attrs.itemCode).trim() : "";
      if (itemCode) {
        blocks.push({ type: "item_card", item_code: itemCode });
      }
    }
    // Các node khác (table, raw HTML, script, iframe...) tự động bị bỏ qua
  }

  return { type: "doc", blocks };
}

/**
 * Chuyển đổi BodyDoc từ backend sang JSON cấu trúc Tiptap document.
 */
export function bodyToTiptap(bodyDoc: BodyDoc): any {
  if (!bodyDoc || bodyDoc.type !== "doc" || !Array.isArray(bodyDoc.blocks)) {
    return { type: "doc", content: [{ type: "paragraph", content: [] }] };
  }

  const content: any[] = [];

  for (const block of bodyDoc.blocks) {
    if (block.type === "heading") {
      content.push({
        type: "heading",
        attrs: { level: block.level === 3 ? 3 : 2 },
        content: block.text ? [{ type: "text", text: block.text }] : [],
      });
    } else if (block.type === "paragraph") {
      content.push({
        type: "paragraph",
        content: inlinesToTiptap(block.children),
      });
    } else if (block.type === "quote") {
      content.push({
        type: "blockquote",
        content: [
          {
            type: "paragraph",
            content: inlinesToTiptap(block.children),
          },
        ],
      });
    } else if (block.type === "list") {
      content.push({
        type: block.ordered ? "orderedList" : "bulletList",
        content: (block.items || []).map((item) => ({
          type: "listItem",
          content: [
            {
              type: "paragraph",
              content: inlinesToTiptap(item),
            },
          ],
        })),
      });
    } else if (block.type === "image") {
      content.push({
        type: "caveImage",
        attrs: {
          imageId: block.image_id,
          alt: block.alt || "",
          caption: block.caption || "",
        },
      });
    } else if (block.type === "item_card") {
      content.push({
        type: "itemCard",
        attrs: {
          itemCode: block.item_code,
        },
      });
    }
  }

  if (content.length === 0) {
    content.push({ type: "paragraph", content: [] });
  }

  return { type: "doc", content };
}
