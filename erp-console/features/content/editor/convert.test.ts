import { describe, expect, it } from "vitest";
import { bodyToTiptap, safeHref, tiptapToBody } from "./convert";
import type { BodyDoc } from "../types";

describe("safeHref", () => {
  it("chấp nhận link hợp lệ https, http, mailto, tel", () => {
    expect(safeHref("https://caveve.vn/shop")).toBe(true);
    expect(safeHref("http://example.com/item")).toBe(true);
    expect(safeHref("mailto:support@caveve.vn")).toBe(true);
    expect(safeHref("tel:0901234567")).toBe(true);
  });

  it("chấp nhận đường dẫn nội bộ hợp lệ", () => {
    expect(safeHref("/shop")).toBe(true);
    expect(safeHref("/bai-viet?slug=ca-thu")).toBe(true);
  });

  it("từ chối href nguy hiểm javascript, vbscript, data, relative protocol", () => {
    expect(safeHref("javascript:alert(1)")).toBe(false);
    expect(safeHref("JAVASCRIPT:alert(1)")).toBe(false);
    expect(safeHref(" vbscript:msgbox(1)")).toBe(false);
    expect(safeHref("data:text/html;base64,PHNjcmlwdD5...==")).toBe(false);
    expect(safeHref("//evil.example/phish")).toBe(false);
    expect(safeHref("/\\evil.example")).toBe(false);
    expect(safeHref("java\tscript:alert(1)")).toBe(false);
  });
});

describe("convert between tiptap and BodyDoc", () => {
  it("CMS-03-AC5: Chuyển đổi tiptap có các block không hợp lệ -> tự động loại bỏ", () => {
    const rawTiptap = {
      type: "doc",
      content: [
        {
          type: "heading",
          attrs: { level: 1 }, // Sẽ chuyển về level 2
          content: [{ type: "text", text: "Tiêu đề lớn" }],
        },
        {
          type: "html",
          content: [{ type: "text", text: "<script>alert(1)</script>" }],
        },
        {
          type: "iframe",
          attrs: { src: "https://evil.com" },
        },
        {
          type: "paragraph",
          content: [
            {
              type: "text",
              text: "<img src=x onerror=alert(1)>",
              marks: [{ type: "bold" }, { type: "unknownMark" }],
            },
            {
              type: "text",
              text: "link nguy hiểm",
              marks: [{ type: "link", attrs: { href: "javascript:alert(1)" } }],
            },
          ],
        },
      ],
    };

    const body = tiptapToBody(rawTiptap);

    // Không còn html hay iframe
    expect(body.blocks.some((b) => (b as any).type === "html")).toBe(false);
    expect(body.blocks.some((b) => (b as any).type === "iframe")).toBe(false);

    // Heading chuyển thành level 2
    expect(body.blocks[0]).toEqual({
      type: "heading",
      level: 2,
      text: "Tiêu đề lớn",
    });

    // Paragraph: giữ chữ <img ...>, giữ mark bold, bỏ unknownMark, bỏ href javascript
    expect(body.blocks[1]).toEqual({
      type: "paragraph",
      children: [
        {
          text: "<img src=x onerror=alert(1)>",
          marks: ["bold"],
        },
        {
          text: "link nguy hiểm",
          // href bị bỏ
        },
      ],
    });
  });

  it("chuyển đổi 2 chiều tương đương (round-trip)", () => {
    const original: BodyDoc = {
      type: "doc",
      blocks: [
        { type: "heading", level: 2, text: "Món cá ngon" },
        {
          type: "paragraph",
          children: [
            { text: "Cá Về ", marks: ["bold"] },
            { text: "rất tươi", marks: ["italic"] },
            { text: " và ", href: "https://caveve.vn" },
          ],
        },
        {
          type: "quote",
          children: [{ text: "Trích dẫn cảm nghĩ khách hàng" }],
        },
        {
          type: "list",
          ordered: true,
          items: [
            [{ text: "Bước 1" }],
            [{ text: "Bước 2", marks: ["bold"] }],
          ],
        },
        {
          type: "image",
          image_id: 123,
          alt: "Cá thu",
          caption: "Ảnh minh hoạ",
        },
        {
          type: "item_card",
          item_code: "CA-THU-1KG",
        },
      ],
    };

    const tiptapJson = bodyToTiptap(original);
    const convertedBack = tiptapToBody(tiptapJson);

    expect(convertedBack).toEqual(original);
  });
});
