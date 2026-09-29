import { ApiError } from "@/lib/types";
import type {
  PublicCategory,
  PublicEntryDetail,
  PublicEntryListItem,
  PublicEntryListResponse,
} from "./types";

export const MOCK_CATEGORIES: PublicCategory[] = [
  {
    slug: "cong-thuc-nau",
    name: "Công thức nấu",
    description: "Các món ngon từ hải sản tươi",
  },
  {
    slug: "meo-nha-bep",
    name: "Mẹo nhà bếp",
    description: "Bảo quản, rã đông cá đúng cách",
  },
];

export const MOCK_ENTRY_MAP: Record<string, PublicEntryDetail> = {
  "cach-ra-dong-ca-thu": {
    kind: "post",
    slug: "cach-ra-dong-ca-thu",
    title: "Cách rã đông cá thu giữ trọn vị tươi như vừa cập cảng",
    seo_title: "Cách rã đông cá thu ngon chuẩn vị | Cá Về",
    description: "Bí quyết rã đông cá thu đúng cách không bị bở thịt, giữ nguyên chất dinh dưỡng.",
    excerpt: "Bí quyết rã đông cá thu tự nhiên bằng ngăn mát hoặc nước đá muối, giữ nguyên vị ngọt đậm đà của cá biển tươi.",
    category: { slug: "meo-nha-bep", name: "Mẹo nhà bếp" },
    cover_image: {
      alt: "Cá thu cắt khoanh tươi ngon",
      width: 1600,
      height: 1200,
      urls: {
        sm: "https://images.unsplash.com/photo-1534940502014-9988e0b62e49?w=600&auto=format&fit=crop&q=80",
        md: "https://images.unsplash.com/photo-1534940502014-9988e0b62e49?w=960&auto=format&fit=crop&q=80",
        lg: "https://images.unsplash.com/photo-1534940502014-9988e0b62e49?w=1600&auto=format&fit=crop&q=80",
      },
    },
    body: {
      type: "doc",
      blocks: [
        {
          type: "heading",
          level: 2,
          text: "1. Tại sao rã đông cá thu đúng cách lại quan trọng?",
        },
        {
          type: "paragraph",
          children: [
            {
              text: "Cá thu là loại cá thịt mềm, giàu dinh dưỡng và axit béo omega-3. Nếu rã đông vội vàng bằng lò vi sóng hoặc nước nóng, cấu trúc cơ thịt sẽ bị phá vỡ, làm cá mất nước và mất đi vị ngọt biển tự nhiên.",
            },
          ],
        },
        {
          type: "quote",
          children: [
            {
              text: "Quy tắc vàng của đầu bếp cảng: Luôn rã đông chậm trong ngăn mát tủ lạnh từ 6-8 tiếng trước khi chế biến.",
              marks: ["italic"],
            },
          ],
        },
        {
          type: "heading",
          level: 3,
          text: "Các bước rã đông bằng ngăn mát tủ lạnh:",
        },
        {
          type: "list",
          ordered: true,
          items: [
            [
              { text: "Lấy cá ra khỏi ngăn đá và giữ nguyên trong túi hút chân không." },
            ],
            [
              { text: "Đặt túi cá vào một chiếc đĩa sâu lòng để hứng nước ngưng tụ." },
            ],
            [
              { text: "Để ở ngăn mát tủ lạnh (nhiệt độ 2-4°C) trong 6 đến 8 tiếng." },
            ],
            [
              { text: "Lấy ra thấm khô bằng khăn giấy sạch trước khi tẩm ướp." },
            ],
          ],
        },
        {
          type: "image",
          alt: "Miếng cá thu tươi rã đông chuẩn vị",
          caption: "Cá thu sau khi rã đông chuẩn vị vẫn giữ được độ đàn hồi và màu sáng tự nhiên.",
          width: 1600,
          height: 1200,
          urls: {
            sm: "https://images.unsplash.com/photo-1534940502014-9988e0b62e49?w=600&auto=format&fit=crop&q=80",
            md: "https://images.unsplash.com/photo-1534940502014-9988e0b62e49?w=960&auto=format&fit=crop&q=80",
            lg: "https://images.unsplash.com/photo-1534940502014-9988e0b62e49?w=1600&auto=format&fit=crop&q=80",
          },
        },
        {
          type: "item_card",
          item_code: "CA-THU-01",
        },
        {
          type: "paragraph",
          children: [
            {
              text: "Xem thêm các công thức nấu ăn khác trên chuyên trang ",
            },
            {
              text: "Cá Về Blog",
              marks: ["bold"],
              href: "/bai-viet",
            },
            {
              text: " hoặc liên hệ qua kênh hỗ trợ của chúng tôi.",
            },
          ],
        },
      ],
    },
    published_at: "2026-09-28T08:00:00Z",
    updated_at: "2026-09-29T09:00:00Z",
    version: 1,
    effective_from: "2026-09-29T09:00:00Z",
    author: "Cá Về",
  },
};

export function mockGetPublicEntry(slug: string): PublicEntryDetail {
  if (slug === "bai-da-go") {
    throw new ApiError("Bài này không còn trên web.", 410);
  }

  const entry = MOCK_ENTRY_MAP[slug];
  if (!entry) {
    throw new ApiError("Không tìm thấy bài.", 404);
  }

  return entry;
}

export function mockGetPublicEntries(params?: {
  category?: string;
  page?: number;
}): PublicEntryListResponse {
  let list = Object.values(MOCK_ENTRY_MAP).map((e) => ({
    slug: e.slug,
    title: e.title,
    excerpt: e.excerpt,
    category: e.category,
    cover_image: e.cover_image,
    published_at: e.published_at,
  }));

  if (params?.category) {
    list = list.filter((e) => e.category?.slug === params.category);
  }

  return {
    results: list,
    total: list.length,
    page: params?.page || 1,
    total_pages: 1,
  };
}

export function mockGetPublicCategories(): PublicCategory[] {
  return MOCK_CATEGORIES;
}
