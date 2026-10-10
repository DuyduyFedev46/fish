import type { ProductCardItem } from "@/components/catalog/ProductCard";

// Dữ liệu GIẢ chỉ dùng ở trang xem thử component (/ui-preview/). Không tên khách, SĐT hay địa chỉ thật.
export const PREVIEW_ITEMS: ProductCardItem[] = [
  { itemCode: "PV-01", name: "Món mẫu còn hàng", unit: "kg", price: "278000", stockLevel: "in", shortNote: "Ghi chú ngắn mẫu", image: null, group: "squid", isCombo: false, minQty: 1, qtyStep: 0.5 },
  { itemCode: "PV-02", name: "Món mẫu sắp hết", unit: "kg", price: "378000", stockLevel: "low", shortNote: "", image: null, group: "shrimp", isCombo: false, minQty: 1, qtyStep: 0.5 },
  { itemCode: "PV-03", name: "Món mẫu đã hết", unit: "kg", price: "420000", stockLevel: "out", shortNote: "", image: null, group: "crab", isCombo: false, minQty: 1, qtyStep: 0.5 },
  { itemCode: "PV-04", name: "Combo mẫu", unit: "combo", price: "259000", stockLevel: "low", shortNote: "Hai món mẫu", image: null, group: "combo", isCombo: true, minQty: 1, qtyStep: 1 },
  {
    itemCode: "PV-05",
    name: "Món mẫu ảnh minh hoạ có tên khá dài để thử xuống dòng",
    unit: "kg",
    price: "330000",
    stockLevel: "in",
    shortNote: "",
    image: {
      alt: "Ảnh mẫu",
      is_illustration: true,
      urls: {
        thumb: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><rect width='160' height='160' fill='gray'/></svg>",
        card: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><rect width='160' height='160' fill='gray'/></svg>",
        detail: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><rect width='160' height='160' fill='gray'/></svg>",
      },
    },
    group: "fish",
    isCombo: false, minQty: 1, qtyStep: 0.5,
  },
];

export const PREVIEW_HOTLINE = "0900 000 000";
