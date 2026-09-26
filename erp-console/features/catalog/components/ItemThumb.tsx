"use client";

// Ảnh thu nhỏ trong danh sách Danh mục (A2). Chưa có ảnh HOẶC ảnh lỗi (URL hỏng, A2 mock có tình huống
// này để thử) -> khung mặc định: icon cá trung tính (Material Symbols, đã nạp sẵn cho console — không
// phải tệp ảnh riêng, không thêm request mạng nào).

import { useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import type { CatalogItemImage } from "../types";
import s from "../catalog.module.css";

export function ItemThumb({ image, size = 44 }: { image: CatalogItemImage | null; size?: number }) {
  const [broken, setBroken] = useState(false);
  const show = !!image && !broken;
  return (
    <span className={s.thumb} style={{ width: size, height: size }} aria-hidden="true">
      {show ? (
        // Trang trí (tên mặt hàng đã đọc được ở cột bên cạnh) -> alt rỗng, tránh đọc lặp cho screen reader.
        <img src={image!.urls.thumb} alt="" width={size} height={size} loading="lazy" onError={() => setBroken(true)} />
      ) : (
        <Icon name="set_meal" />
      )}
    </span>
  );
}
