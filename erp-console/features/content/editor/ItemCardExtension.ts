import { Node, mergeAttributes } from "@tiptap/core";

export const ItemCardExtension = Node.create({
  name: "itemCard",
  group: "block",
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      itemCode: {
        default: "",
        parseHTML: (element) => element.getAttribute("data-item-code") || "",
        renderHTML: (attributes) => ({
          "data-item-code": attributes.itemCode,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-type="item-card"]',
        getAttrs: (element: any) => ({
          itemCode: element.getAttribute("data-item-code") || "",
        }),
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "div",
      mergeAttributes({ "data-type": "item-card", class: "item-card-block" }, HTMLAttributes),
      ["span", { class: "item-card-badge" }, "🛒 Thẻ mặt hàng Shop: "],
      ["strong", { class: "item-card-code" }, HTMLAttributes["data-item-code"] || HTMLAttributes.itemCode || ""],
    ];
  },
});
