import { Node, mergeAttributes } from "@tiptap/core";

export const CaveImageExtension = Node.create({
  name: "caveImage",
  group: "block",
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      imageId: { default: null },
      alt: { default: "" },
      caption: { default: "" },
      url: { default: "" },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-type="cave-image"]',
        getAttrs: (element: any) => ({
          imageId: Number(element.getAttribute("data-image-id")),
          alt: element.getAttribute("data-alt") || "",
          caption: element.getAttribute("data-caption") || "",
          url: element.getAttribute("data-url") || "",
        }),
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "div",
      mergeAttributes({ "data-type": "cave-image", class: "cave-image-block" }, HTMLAttributes),
      [
        "div",
        { class: "cave-image-box" },
        HTMLAttributes.url
          ? ["img", { src: HTMLAttributes.url, alt: HTMLAttributes.alt || "", class: "cave-image-preview" }]
          : ["span", { class: "cave-image-tag" }, `📷 [Ảnh #${HTMLAttributes.imageId || ""}: ${HTMLAttributes.alt || "Không có alt"}]`],
      ],
      HTMLAttributes.caption ? ["p", { class: "cave-image-caption" }, HTMLAttributes.caption] : ["span"],
    ];
  },
});
