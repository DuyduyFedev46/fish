import { describe, it, expect } from "vitest";
import { getSchema } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import { CaveImageExtension } from "./CaveImageExtension";
import { ItemCardExtension } from "./ItemCardExtension";
import { bodyToTiptap, tiptapToBody } from "./convert";
import { isSafeHref } from "./safeHref";
import type { BodyDoc } from "../types";

// TD-08: kiểm lược đồ Tiptap 3 thật (cùng cấu hình với TiptapEditor): nội dung bài cũ (body.blocks) nạp vào
// lược đồ rồi xuất ra phải y nguyên, không mất định dạng, không thêm đoạn rỗng cuối bài.
const extensions = [
  StarterKit.configure({
    heading: { levels: [2, 3] },
    codeBlock: false,
    code: false,
    strike: false,
    horizontalRule: false,
    hardBreak: false,
    link: false,
    underline: false,
    trailingNode: false,
  }),
  Link.configure({
    protocols: ["https", "http", "mailto", "tel"],
    autolink: false,
    openOnClick: false,
    validate: (href: string) => isSafeHref(href),
  }),
  CaveImageExtension,
  ItemCardExtension,
];
const schema = getSchema(extensions);

const sample: BodyDoc = {
  type: "doc",
  blocks: [
    { type: "heading", level: 2, text: "Cá thu tươi" },
    { type: "heading", level: 3, text: "Cách chọn" },
    {
      type: "paragraph",
      children: [
        { text: "Chữ thường, " },
        { text: "đậm", marks: ["bold"] },
        { text: " nghiêng", marks: ["italic"] },
        { text: " cả hai", marks: ["bold", "italic"] },
        { text: " liên kết", href: "https://example.com/a?b=1" },
        { text: " đậm có link", marks: ["bold"], href: "mailto:cuahang@example.com" },
      ],
    },
    { type: "quote", children: [{ text: "Cá về sáng nay", marks: ["italic"] }] },
    { type: "list", ordered: false, items: [[{ text: "Một" }], [{ text: "Hai", marks: ["bold"] }]] },
    { type: "list", ordered: true, items: [[{ text: "Bước 1" }], [{ text: "Bước 2", href: "tel:0900000000" }]] },
    { type: "image", image_id: 7, alt: "Cá thu", caption: "Ảnh minh hoạ" },
    { type: "item_card", item_code: "CA-THU-1KG" },
  ],
};

describe("TD-08 round-trip body.blocks ⇄ lược đồ Tiptap 3", () => {
  it("nội dung đủ loại khối giữ nguyên qua lược đồ thật", () => {
    const pmDoc = schema.nodeFromJSON(bodyToTiptap(sample));
    pmDoc.check();
    expect(tiptapToBody(pmDoc.toJSON())).toEqual(sample);
  });

  it("lược đồ không có gạch chân, gạch ngang, mã, ngắt dòng cứng", () => {
    for (const name of ["underline", "strike", "code"]) expect(schema.marks[name]).toBeUndefined();
    expect(schema.nodes.hardBreak).toBeUndefined();
    expect(schema.marks.link).toBeDefined();
  });

  it("liên kết javascript: bị chặn khi xuất", () => {
    const json = {
      type: "doc",
      content: [
        { type: "paragraph", content: [{ type: "text", text: "xấu", marks: [{ type: "link", attrs: { href: "javascript:alert(1)" } }] }] },
      ],
    };
    const body = tiptapToBody(schema.nodeFromJSON(json).toJSON());
    expect(JSON.stringify(body)).not.toContain("javascript");
  });
});
