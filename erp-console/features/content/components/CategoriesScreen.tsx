"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/shared/ui/Icon";
import { Empty } from "@/shared/ui/StateBox";
import { createCategory, fetchCategories, updateCategory } from "../api";
import type { ContentCategory, DeactivateCategoryBlockedError } from "../types";
import s from "../content.module.css";

export function CategoriesScreen() {
  const [categories, setCategories] = useState<ContentCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editCategory, setEditCategory] = useState<ContentCategory | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [order, setOrder] = useState<number>(0);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Error modal for BR-ND-02 (deactivate blocked)
  const [blockedError, setBlockedError] = useState<DeactivateCategoryBlockedError | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchCategories();
      setCategories(data);
    } catch (err) {
      console.error("Lỗi tải chuyên mục:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openCreate = () => {
    setName("");
    setDescription("");
    setOrder(categories.length > 0 ? Math.max(...categories.map((c) => c.order)) + 1 : 1);
    setFormError(null);
    setEditCategory(null);
    setShowCreateModal(true);
  };

  const openEdit = (cat: ContentCategory) => {
    setName(cat.name);
    setDescription(cat.description);
    setOrder(cat.order);
    setFormError(null);
    setEditCategory(cat);
    setShowCreateModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFormError("Vui lòng nhập tên chuyên mục");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      if (editCategory) {
        await updateCategory(editCategory.id, {
          name: name.trim(),
          description: description.trim(),
          order: Number(order),
        });
      } else {
        await createCategory({
          name: name.trim(),
          description: description.trim(),
          order: Number(order),
        });
      }
      setShowCreateModal(false);
      await loadData();
    } catch (err: any) {
      setFormError(err?.detail || err?.message || "Có lỗi xảy ra khi lưu");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (cat: ContentCategory) => {
    const nextActive = !cat.is_active;
    try {
      await updateCategory(cat.id, { is_active: nextActive });
      await loadData();
    } catch (err: any) {
      if (err?.code === "BR-ND-02") {
        setBlockedError({
          detail: err.detail || "Không thể ngừng dùng chuyên mục còn bài đăng.",
          code: err.code,
          entries: err.entries || [],
          total: err.total || 0,
        });
      } else {
        alert(err?.detail || "Không thể cập nhật trạng thái");
      }
    }
  };

  return (
    <div className={s.container}>
      <div className={s.header}>
        <div className={s.titleGroup}>
          <Link href="/content/" className="btn" aria-label="Quay lại danh sách bài">
            <Icon name="arrow_back" />
          </Link>
          <h1 className={s.title}>Quản lý chuyên mục</h1>
        </div>
        <div className={s.actions}>
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            <Icon name="add" />
            <span>Thêm chuyên mục</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="muted" style={{ padding: "32px 0", textAlign: "center" }}>
          Đang tải dữ liệu...
        </div>
      ) : categories.length === 0 ? (
        <Empty icon="category" title="Chưa có chuyên mục nào">
          <span>Hãy bấm &quot;Thêm chuyên mục&quot; để tạo chuyên mục đầu tiên.</span>
        </Empty>
      ) : (
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th style={{ width: 80 }}>Thứ tự</th>
                <th>Tên chuyên mục</th>
                <th>Đường dẫn (Slug)</th>
                <th>Bài đã đăng</th>
                <th>Trạng thái</th>
                <th style={{ textAlign: "right" }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((cat) => (
                <tr key={cat.id}>
                  <td>
                    <span className="code">{cat.order}</span>
                  </td>
                  <td>
                    <b>{cat.name}</b>
                    {cat.description && <div className="muted">{cat.description}</div>}
                  </td>
                  <td>
                    <code className="code">{cat.slug}</code>
                  </td>
                  <td>
                    <span>{cat.published_count} bài</span>
                  </td>
                  <td>
                    {cat.is_active ? (
                      <span className="status ok">
                        <span className="dot" aria-hidden="true" />
                        Đang hoạt động
                      </span>
                    ) : (
                      <span className="status mute">
                        <span className="dot" aria-hidden="true" />
                        Ngừng dùng
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div className={s.actions} style={{ justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        className="btn"
                        onClick={() => openEdit(cat)}
                        aria-label={`Sửa chuyên mục ${cat.name}`}
                      >
                        <Icon name="edit" />
                        <span>Sửa</span>
                      </button>
                      <button
                        type="button"
                        className="btn"
                        onClick={() => handleToggleActive(cat)}
                        aria-label={cat.is_active ? `Ngừng dùng ${cat.name}` : `Kích hoạt ${cat.name}`}
                      >
                        <Icon name={cat.is_active ? "block" : "check_circle"} />
                        <span>{cat.is_active ? "Ngừng dùng" : "Kích hoạt"}</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Thêm / Sửa chuyên mục */}
      {showCreateModal && (
        <div className={s.modalOverlay} role="dialog" aria-modal="true">
          <form className={s.modal} onSubmit={handleSubmit}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 600 }}>
                {editCategory ? "Sửa chuyên mục" : "Thêm chuyên mục mới"}
              </h2>
              <button
                type="button"
                className="btn"
                style={{ padding: 4 }}
                onClick={() => setShowCreateModal(false)}
                aria-label="Đóng"
              >
                <Icon name="close" />
              </button>
            </div>

            {formError && <div className={s.errorMsg}>{formError}</div>}

            <div className={s.formGroup}>
              <label htmlFor="cat-name">Tên chuyên mục *</label>
              <input
                id="cat-name"
                className={s.input}
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="VD: Công thức nấu"
                autoFocus
              />
            </div>

            {editCategory && (
              <div className={s.formGroup}>
                <label>Đường dẫn tĩnh (Slug - không đổi khi đổi tên)</label>
                <input className={s.input} type="text" value={editCategory.slug} disabled readOnly />
              </div>
            )}

            <div className={s.formGroup}>
              <label htmlFor="cat-desc">Mô tả ngắn</label>
              <textarea
                id="cat-desc"
                className={s.textarea}
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Mô tả về chuyên mục..."
              />
            </div>

            <div className={s.formGroup}>
              <label htmlFor="cat-order">Thứ tự hiển thị</label>
              <input
                id="cat-order"
                className={s.input}
                type="number"
                value={order}
                onChange={(e) => setOrder(Number(e.target.value))}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
              <button type="button" className="btn" onClick={() => setShowCreateModal(false)}>
                Huỷ
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? "Đang lưu..." : editCategory ? "Cập nhật" : "Tạo mới"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal báo lỗi ngừng dùng còn bài đã đăng (CMS-02-AC4) */}
      {blockedError && (
        <div className={s.modalOverlay} role="dialog" aria-modal="true">
          <div className={s.modal}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#dc2626" }}>
              <Icon name="warning" />
              <h2 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 600 }}>Không thể ngừng dùng</h2>
            </div>
            <p style={{ margin: 0, fontSize: "0.875rem" }}>
              Chuyên mục còn <b>{blockedError.total} bài</b> đang ở trạng thái <b>Đã đăng</b>. Bạn cần gỡ hoặc
              chuyển chuyên mục cho các bài viết này trước khi ngừng dùng:
            </p>
            <ul style={{ margin: "4px 0", paddingLeft: 20, fontSize: "0.875rem" }}>
              {blockedError.entries.map((entry) => (
                <li key={entry.id}>
                  <b>#{entry.id}</b>: {entry.title}
                </li>
              ))}
              {blockedError.total > blockedError.entries.length && (
                <li className="muted">... và còn {blockedError.total - blockedError.entries.length} bài khác</li>
              )}
            </ul>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
              <button type="button" className="btn btn-primary" onClick={() => setBlockedError(null)}>
                Đã hiểu
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
