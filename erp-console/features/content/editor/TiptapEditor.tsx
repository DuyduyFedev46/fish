"use client";

import React, { useEffect, useImperativeHandle, forwardRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import { CaveImageExtension } from "./CaveImageExtension";
import { ItemCardExtension } from "./ItemCardExtension";
import { bodyToTiptap, tiptapToBody } from "./convert";
import { isSafeHref } from "./safeHref";
import { fetchShopCatalog, type ShopCatalogItem } from "../api";
import type { BodyDoc } from "../types";
import s from "./TiptapEditor.module.css";

export interface TiptapEditorHandle {
  insertImage: (image: { id: number; alt?: string; caption?: string; url?: string }) => void;
  insertItemCard: (itemCode: string) => void;
  focus: () => void;
}

export interface TiptapEditorProps {
  value: BodyDoc;
  onChange: (doc: BodyDoc) => void;
  placeholder?: string;
  disabled?: boolean;
}

const TiptapEditor = forwardRef<TiptapEditorHandle, TiptapEditorProps>(
  ({ value, onChange, disabled }, ref) => {
    const [showItemModal, setShowItemModal] = useState(false);
    const [catalogItems, setCatalogItems] = useState<ShopCatalogItem[]>([]);
    const [loadingCatalog, setLoadingCatalog] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");

    const editor = useEditor({
      editable: !disabled,
      extensions: [
        StarterKit.configure({
          heading: {
            levels: [2, 3],
          },
          codeBlock: false,
          code: false,
          strike: false,
          horizontalRule: false,
          hardBreak: false,
        }),
        Link.configure({
          protocols: ["https", "http", "mailto", "tel"],
          autolink: false,
          openOnClick: false,
          validate: (href) => isSafeHref(href),
        }),
        CaveImageExtension,
        ItemCardExtension,
      ],
      content: bodyToTiptap(value),
      onUpdate: ({ editor }) => {
        const json = editor.getJSON();
        onChange(tiptapToBody(json));
      },
    });

    useImperativeHandle(
      ref,
      () => ({
        insertImage: (image) => {
          if (!editor) return;
          editor
            .chain()
            .focus()
            .insertContent({
              type: "caveImage",
              attrs: {
                imageId: image.id,
                alt: image.alt || "",
                caption: image.caption || "",
                url: image.url || "",
              },
            })
            .run();
        },
        insertItemCard: (itemCode: string) => {
          if (!editor) return;
          editor
            .chain()
            .focus()
            .insertContent({
              type: "itemCard",
              attrs: { itemCode },
            })
            .run();
        },
        focus: () => {
          if (editor) editor.chain().focus().run();
        },
      }),
      [editor]
    );

    // Đồng bộ khi value từ ngoài đổi mà editor chưa có (vd: load từ server)
    useEffect(() => {
      if (!editor) return;
      const currentJson = editor.getJSON();
      const currentBody = tiptapToBody(currentJson);
      if (JSON.stringify(currentBody) !== JSON.stringify(value)) {
        editor.commands.setContent(bodyToTiptap(value));
      }
    }, [value, editor]);

    // Đồng bộ editable
    useEffect(() => {
      if (editor) {
        editor.setEditable(!disabled);
      }
    }, [disabled, editor]);

    if (!editor) {
      return (
        <div className={s.container}>
          <div className={s.editorArea}>Đang khởi tạo trình soạn thảo...</div>
        </div>
      );
    }

    const setLink = () => {
      const prevUrl = editor.getAttributes("link").href;
      const url = window.prompt("Nhập địa chỉ liên kết (URL):", prevUrl);
      if (url === null) return;
      if (url === "") {
        editor.chain().focus().extendMarkRange("link").unsetLink().run();
        return;
      }
      if (isSafeHref(url)) {
        editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
      } else {
        alert("Đường dẫn không hợp lệ. Chỉ chấp nhận link https, http, mailto, tel hoặc đường dẫn nội bộ.");
      }
    };

    return (
      <div className={s.container}>
        <div className={s.toolbar}>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("heading", { level: 2 }) ? s.active : ""}`}
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            title="Tiêu đề mục (H2)"
            disabled={disabled}
          >
            H2
          </button>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("heading", { level: 3 }) ? s.active : ""}`}
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            title="Tiêu đề phụ (H3)"
            disabled={disabled}
          >
            H3
          </button>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("bold") ? s.active : ""}`}
            onClick={() => editor.chain().focus().toggleBold().run()}
            title="Đậm"
            disabled={disabled}
          >
            <strong>B</strong>
          </button>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("italic") ? s.active : ""}`}
            onClick={() => editor.chain().focus().toggleItalic().run()}
            title="Nghiêng"
            disabled={disabled}
          >
            <em>I</em>
          </button>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("bulletList") ? s.active : ""}`}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            title="Danh sách chấm"
            disabled={disabled}
          >
            • Danh sách
          </button>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("orderedList") ? s.active : ""}`}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            title="Danh sách số"
            disabled={disabled}
          >
            1. Số
          </button>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("blockquote") ? s.active : ""}`}
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            title="Trích dẫn"
            disabled={disabled}
          >
            “ Trích dẫn
          </button>
          <button
            type="button"
            className={`${s.toolBtn} ${editor.isActive("link") ? s.active : ""}`}
            onClick={setLink}
            title="Chèn liên kết"
            disabled={disabled}
          >
            🔗 Link
          </button>
          <button
            type="button"
            className={s.toolBtn}
            onClick={async () => {
              setShowItemModal(true);
              if (catalogItems.length === 0) {
                setLoadingCatalog(true);
                try {
                  const items = await fetchShopCatalog();
                  setCatalogItems(items || []);
                } catch {
                  // Fallback danh sách rỗng
                } finally {
                  setLoadingCatalog(false);
                }
              }
            }}
            title="Chèn thẻ mặt hàng Shop"
            disabled={disabled}
          >
            🛒 Mặt hàng
          </button>
        </div>

        <div className={s.editorArea}>
          <EditorContent editor={editor} />
        </div>

        {/* Modal chọn mặt hàng Shop (CMS-06-AC1) */}
        {showItemModal && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0,0,0,0.5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 9999,
            }}
          >
            <div
              style={{
                backgroundColor: "#fff",
                borderRadius: "8px",
                width: "480px",
                maxWidth: "90vw",
                maxHeight: "80vh",
                display: "flex",
                flexDirection: "column",
                boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)",
                overflow: "hidden",
              }}
            >
              <div style={{ padding: "16px", borderBottom: "1px solid #e2e8f0" }}>
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>Chèn thẻ mặt hàng Shop</h3>
                <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#64748b" }}>
                  Gõ từ khoá tìm kiếm theo tên hoặc mã mặt hàng (CMS-06-AC1)
                </p>
                <input
                  type="text"
                  placeholder="Gõ tên hoặc mã (vd: thu, CA-THU)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    marginTop: "12px",
                    border: "1px solid #cbd5e1",
                    borderRadius: "6px",
                    fontSize: "14px",
                  }}
                  autoFocus
                />
              </div>

              <div style={{ padding: "12px 16px", overflowY: "auto", flex: 1 }}>
                {loadingCatalog ? (
                  <p style={{ textAlign: "center", color: "#64748b", margin: "20px 0" }}>Đang tải danh mục Shop...</p>
                ) : (
                  (() => {
                    const q = searchQuery.trim().toLowerCase();
                    const filtered = catalogItems.filter(
                      (it) => it.name.toLowerCase().includes(q) || it.item_code.toLowerCase().includes(q)
                    );
                    if (filtered.length === 0) {
                      return (
                        <p style={{ textAlign: "center", color: "#94a3b8", margin: "20px 0" }}>
                          Không tìm thấy mặt hàng phù hợp.
                        </p>
                      );
                    }
                    return (
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {filtered.map((item) => (
                          <button
                            key={item.item_code}
                            type="button"
                            onClick={() => {
                              editor
                                ?.chain()
                                .focus()
                                .insertContent({
                                  type: "itemCard",
                                  attrs: { itemCode: item.item_code },
                                })
                                .run();
                              setShowItemModal(false);
                              setSearchQuery("");
                            }}
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              padding: "10px 12px",
                              backgroundColor: "#f8fafc",
                              border: "1px solid #e2e8f0",
                              borderRadius: "6px",
                              cursor: "pointer",
                              textAlign: "left",
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 600, fontSize: "14px", color: "#0f172a" }}>{item.name}</div>
                              <div style={{ fontSize: "12px", color: "#64748b" }}>Mã: {item.item_code}</div>
                            </div>
                            <span style={{ fontSize: "13px", color: "#0284c7", fontWeight: 500 }}>Chèn thẻ →</span>
                          </button>
                        ))}
                      </div>
                    );
                  })()
                )}
              </div>

              <div
                style={{
                  padding: "12px 16px",
                  borderTop: "1px solid #e2e8f0",
                  display: "flex",
                  justifyContent: "flex-end",
                  backgroundColor: "#f8fafc",
                }}
              >
                <button
                  type="button"
                  onClick={() => {
                    setShowItemModal(false);
                    setSearchQuery("");
                  }}
                  style={{
                    padding: "6px 14px",
                    border: "1px solid #cbd5e1",
                    borderRadius: "6px",
                    backgroundColor: "#fff",
                    cursor: "pointer",
                    fontSize: "14px",
                  }}
                >
                  Đóng
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }
);

TiptapEditor.displayName = "TiptapEditor";

export default TiptapEditor;
