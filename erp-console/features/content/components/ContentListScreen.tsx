"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/shared/ui/Icon";
import { Empty } from "@/shared/ui/StateBox";
import { fetchEntries, fetchEntryCounts } from "../api";
import type { ContentCounts, ContentEntryListItem, ContentKind, ContentStatus } from "../types";
import s from "../content.module.css";

const STATUS_TABS: Array<{ key: ContentStatus | "all"; label: string }> = [
  { key: "all", label: "Tất cả" },
  { key: "draft", label: "Nháp" },
  { key: "pending_review", label: "Chờ duyệt" },
  { key: "published", label: "Đã đăng" },
  { key: "unpublished", label: "Đã gỡ" },
];

const KIND_OPTIONS: Array<{ key: ContentKind | "all"; label: string }> = [
  { key: "all", label: "Tất cả loại" },
  { key: "post", label: "Bài viết" },
  { key: "page", label: "Trang" },
];

export function ContentListScreen() {
  const [statusFilter, setStatusFilter] = useState<ContentStatus | "all">("all");
  const [kindFilter, setKindFilter] = useState<ContentKind | "all">("all");
  const [entries, setEntries] = useState<ContentEntryListItem[]>([]);
  const [counts, setCounts] = useState<ContentCounts>({
    draft: 0,
    pending_review: 0,
    published: 0,
    unpublished: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function loadData() {
      setLoading(true);
      try {
        const [countsData, entriesData] = await Promise.all([
          fetchEntryCounts(kindFilter !== "all" ? { kind: kindFilter } : undefined),
          fetchEntries({
            status: statusFilter !== "all" ? statusFilter : undefined,
            kind: kindFilter !== "all" ? kindFilter : undefined,
          }),
        ]);
        if (active) {
          setCounts(countsData);
          setEntries(entriesData.results || []);
        }
      } catch (err) {
        console.error("Lỗi tải nội dung:", err);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadData();
    return () => {
      active = false;
    };
  }, [statusFilter, kindFilter]);

  const getStatusBadge = (key: ContentStatus | "all") => {
    if (key === "all") return null;
    return counts[key] ?? 0;
  };

  return (
    <div className={s.container}>
      <div className={s.header}>
        <div className={s.titleGroup}>
          <h1 className={s.title}>Nội dung & CMS</h1>
        </div>
        <div className={s.actions}>
          <Link href="/content/categories/" className="btn">
            <Icon name="category" />
            <span>Quản lý chuyên mục</span>
          </Link>
          <Link href="/content/edit/?new=post" className="btn btnPrimary">
            <span>+ Viết bài mới</span>
          </Link>
          <Link href="/content/edit/?new=page" className="btn">
            <span>+ Tạo trang</span>
          </Link>
        </div>
      </div>

      {/* Tabs lọc trạng thái (CMS-01-AC7) */}
      <div className={s.tabs} role="tablist">
        {STATUS_TABS.map((tab) => {
          const isActive = statusFilter === tab.key;
          const count = getStatusBadge(tab.key);
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`${s.tab} ${isActive ? s.tabActive : ""}`}
              onClick={() => setStatusFilter(tab.key)}
            >
              <span>{tab.label}</span>
              {count !== null && <span className={s.badge}>{count}</span>}
            </button>
          );
        })}
      </div>

      {/* Bộ lọc loại bài viết / trang */}
      <div className={s.filterBar}>
        <select
          className={s.input}
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value as ContentKind | "all")}
          aria-label="Lọc theo loại nội dung"
        >
          {KIND_OPTIONS.map((opt) => (
            <option key={opt.key} value={opt.key}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Danh sách bài viết */}
      {loading ? (
        <div className="muted" style={{ padding: "32px 0", textAlign: "center" }}>
          Đang tải dữ liệu...
        </div>
      ) : entries.length === 0 ? (
        <Empty icon="article" title="Chưa có bài viết nào">
          <span>Hãy bấm tạo bài mới hoặc thay đổi bộ lọc để xem bài viết.</span>
        </Empty>
      ) : (
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th>Tiêu đề</th>
                <th>Loại</th>
                <th>Trạng thái</th>
                <th>Cập nhật</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td>
                    <Link href={`/content/edit/?id=${entry.id}`} style={{ textDecoration: "none", color: "inherit" }}>
                      <b>{entry.title || "(Chưa có tiêu đề)"}</b>
                      <div className="muted">{entry.slug}</div>
                    </Link>
                  </td>
                  <td>{entry.kind === "post" ? "Bài viết" : "Trang"}</td>
                  <td>
                    <span className="tag">
                      {entry.status === "draft"
                        ? "Nháp"
                        : entry.status === "pending_review"
                        ? "Chờ duyệt"
                        : entry.status === "published"
                        ? "Đã đăng"
                        : entry.status === "unpublished"
                        ? "Đã gỡ"
                        : entry.status}
                    </span>
                    {entry.has_unpublished_changes && (
                      <span className={s.badgeWarning} style={{ marginLeft: 6 }}>
                        Có thay đổi chưa đăng
                      </span>
                    )}
                  </td>
                  <td className="muted">{entry.updated_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
