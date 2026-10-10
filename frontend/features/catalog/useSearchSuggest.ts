"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getCatalog } from "@/lib/api";
import { foldVietnamese } from "@/lib/text";
import type { CatalogItem } from "@/lib/types";
import type { SuggestItem } from "@/components/search/SearchSuggest";
import { groupIconOf } from "./groupIcon";
import { rankItems } from "./catalogView";
import { addRecent, parseRecent } from "./recentSearches";

const RECENT_KEY = "shop_recent_searches_v1";

/**
 * Dữ liệu cho SearchBox: lọc tại chỗ trên catalog đã tải (có cache, không gọi API mỗi lần gõ) và
 * "Tìm gần đây" trong localStorage (chỉ từ khoá).
 */
export function useSearchSuggest() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [query, setQuery] = useState("");
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    getCatalog()
      .then((c) => active && setItems(c.items))
      .catch(() => {}); // lỗi: panel chỉ còn "Xem tất cả" và "Tìm gần đây"
    try {
      setRecent(parseRecent(window.localStorage.getItem(RECENT_KEY)));
    } catch {
      /* không có localStorage */
    }
    return () => {
      active = false;
    };
  }, []);

  const suggestions: SuggestItem[] = useMemo(() => {
    const q = foldVietnamese(query.trim());
    if (q.length < 2) return [];
    return rankItems(items.filter((i) => foldVietnamese(i.name).includes(q)))
      .slice(0, 5)
      .map((i) => ({
        itemCode: i.item_code,
        name: i.name,
        price: i.price,
        unit: i.unit,
        group: groupIconOf(i.group.slug, i.item_type),
        image: i.image,
      }));
  }, [items, query]);

  const remember = useCallback((q: string) => {
    setRecent((prev) => {
      const next = addRecent(prev, q);
      if (next === prev) return prev;
      try {
        window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      } catch {
        /* bỏ qua */
      }
      return next;
    });
  }, []);

  const clearRecent = useCallback(() => {
    setRecent([]);
    try {
      window.localStorage.removeItem(RECENT_KEY);
    } catch {
      /* bỏ qua */
    }
  }, []);

  return {
    suggestions,
    recentQueries: recent,
    onQueryChange: setQuery,
    onRemember: remember,
    onClearRecent: clearRecent,
  };
}
