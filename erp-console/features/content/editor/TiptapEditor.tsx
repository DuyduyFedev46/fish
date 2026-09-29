"use client";

import React, { useEffect, useImperativeHandle, forwardRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import { CaveImageExtension } from "./CaveImageExtension";
import { bodyToTiptap, tiptapToBody, safeHref } from "./convert";
import type { BodyDoc } from "../types";
import s from "./TiptapEditor.module.css";

export interface TiptapEditorHandle {
  insertImage: (image: { id: number; alt?: string; caption?: string; url?: string }) => void;
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
          validate: (href) => safeHref(href),
        }),
        CaveImageExtension,
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
      if (safeHref(url)) {
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
        </div>

        <div className={s.editorArea}>
          <EditorContent editor={editor} />
        </div>
      </div>
    );
  }
);

TiptapEditor.displayName = "TiptapEditor";

export default TiptapEditor;
