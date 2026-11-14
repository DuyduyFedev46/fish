"use client";

// Nút tải/nhập file Excel ở thanh công cụ tab Mặt hàng (FISH-66 S3, S4; 02a §2, M1).
//   [Tải file Excel]  [Nhập từ Excel]  […: Tải file mẫu]
// - Tải file Excel + menu "…": ai xem được tab Mặt hàng (catalog.view_item). Gửi đúng bộ lọc phía máy chủ đang chọn.
// - Nhập từ Excel: chỉ khi đủ 4 quyền nhập (ability.canImport), là link sang /catalog/import/ (làm ở lô 3).
// - Đang tạo file thì khoá nút + aria-busy; xong hoặc lỗi thì báo bằng toast (câu 02a §5: T1, T1b, T2, T3, E3, E4, E5).
// Không lưu gì vào URL hay storage; file chỉ đi qua blob tạm rồi được thu hồi.

import Link from "next/link";
import { useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { Icon } from "@/shared/ui/Icon";
import { MoreMenu, type MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { useToast } from "@/shared/ui/overlay/Toast";
import { exportItems, exportTemplate } from "../itemFilesApi";
import { INVALID_FILTER } from "../itemFilesTypes";
import { CATALOG_MSG as M } from "../messages";
import type { ItemListParams } from "../types";

// Icon dùng những tên đã có trong tập con font (public/fonts/ms): `download`/`upload_file` chưa có, thêm vào
// scripts/subset-material-symbols.py nếu muốn đổi.

/** Trang nhập file (lô 3) chưa có: giữ nút Nhập ẩn tới khi route `/catalog/import/` sẵn sàng. */
const IMPORT_PAGE_READY = false;

type Props = {
  /** Bộ lọc phía máy chủ đang chọn (nhóm, trạng thái, ảnh, loại). */
  params: ItemListParams;
  /** Ô tìm đang có chữ: toast báo thêm rằng file không theo ô tìm (T1b). */
  hasSearchText: boolean;
  /** Có đủ 4 quyền nhập (CatalogAbility.canImport). */
  canImport: boolean;
};

function failText(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return M.fileForbidden;
    if (err.code === INVALID_FILTER) return M.fileBadFilter;
  }
  return fallback;
}

export function ItemFileActions({ params, hasSearchText, canImport }: Props) {
  const toast = useToast();
  const [busy, setBusy] = useState<"list" | "template" | null>(null);
  const busyRef = useRef(false); // chặn bấm đúp trước khi React kịp vẽ lại

  async function run(kind: "list" | "template") {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(kind);
    try {
      if (kind === "list") {
        const saved = await exportItems(params);
        if (saved.rowCount === 0) toast.warn(M.fileDownloadedEmpty);
        else toast.success(M.fileDownloaded(saved.filename, saved.rowCount, hasSearchText));
      } else {
        const saved = await exportTemplate();
        toast.success(M.templateDownloaded(saved.filename));
      }
    } catch (err) {
      toast.error(failText(err, kind === "list" ? M.fileFailed : M.templateFailed));
    } finally {
      busyRef.current = false;
      setBusy(null);
    }
  }

  const more: MoreMenuItem[] = [
    {
      key: "template",
      label: busy === "template" ? M.fileBusy : M.fileTemplate,
      onSelect: () => void run("template"),
    },
  ];

  return (
    <>
      <button type="button" className="btn" onClick={() => void run("list")} disabled={busy !== null} aria-busy={busy === "list" || undefined} data-testid="item-export">
        <Icon name="description" />
        <span>{busy === "list" ? M.fileBusy : M.fileDownload}</span>
      </button>
      {canImport && IMPORT_PAGE_READY && (
        <Link href="/catalog/import/" className="btn" data-testid="item-import-link">
          <Icon name="swap_vert" />
          <span>{M.fileImport}</span>
        </Link>
      )}
      <MoreMenu items={more} label={M.fileMenuLabel} />
    </>
  );
}
