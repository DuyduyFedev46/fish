"use client";

import React, { useEffect, useImperativeHandle, useRef, forwardRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import { Icon } from "@/shared/ui/Icon";
import { CaveImageExtension } from "./CaveImageExtension";
import { ItemCardExtension } from "./ItemCardExtension";
import { ItemPickerModal, LinkModal } from "./EditorDialogs";
import { bodyToTiptap, tiptapToBody } from "./convert";
import { isSafeHref } from "./safeHref";
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

const TiptapEditor = forwardRef<TiptapEditorHandle, TiptapEditorProps>(({ value, onChange, disabled }, ref) => {
  const [dialog, setDialog] = useState<"item" | "link" | null>(null);
  const valueRef = useRef<BodyDoc>(value);
  valueRef.current = value;

  const editor = useEditor({
    editable: !disabled,
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
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
      const next = tiptapToBody(editor.getJSON());
      // Chỉ báo "đã sửa" khi nội dung thật sự khác bản đang giữ (nội dung máy chủ ở dạng chưa chuẩn hoá
      // hay bật/tắt chế độ chỉ đọc đều không được tính là người dùng đã gõ).
      if (JSON.stringify(next) === JSON.stringify(valueRef.current)) return;
      valueRef.current = next;
      onChange(next);
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
            attrs: { imageId: image.id, alt: image.alt || "", caption: image.caption || "", url: image.url || "" },
          })
          .run();
      },
      insertItemCard: (itemCode: string) => {
        if (!editor) return;
        editor.chain().focus().insertContent({ type: "itemCard", attrs: { itemCode } }).run();
      },
      focus: () => {
        if (editor) editor.chain().focus().run();
      },
    }),
    [editor],
  );

  // Đồng bộ khi value từ ngoài đổi (tải từ máy chủ, khôi phục phiên bản).
  useEffect(() => {
    if (!editor) return;
    const currentBody = tiptapToBody(editor.getJSON());
    if (JSON.stringify(currentBody) !== JSON.stringify(value)) {
      // emitUpdate = false: đồng bộ từ ngoài vào không phải việc người dùng gõ.
      editor.commands.setContent(bodyToTiptap(value), false);
    }
  }, [value, editor]);

  useEffect(() => {
    // emitUpdate = false: Tiptap mặc định phát "update" khi đổi chế độ sửa, làm bài vừa mở đã bị coi là đã sửa.
    if (editor) editor.setEditable(!disabled, false);
  }, [disabled, editor]);

  if (!editor) {
    return (
      <div className={s.container}>
        <div className={s.editorArea} role="status">
          Đang khởi tạo trình soạn thảo…
        </div>
      </div>
    );
  }

  const tool = (label: string, active: boolean, run: () => void, content: React.ReactNode) => (
    <button type="button" className={`${s.toolBtn} ${active ? s.active : ""}`} onClick={run} aria-label={label} aria-pressed={active} title={label} disabled={disabled}>
      {content}
    </button>
  );

  return (
    <div className={s.container}>
      <div className={s.toolbar} role="toolbar" aria-label="Định dạng bài viết">
        {tool("Tiêu đề mục", editor.isActive("heading", { level: 2 }), () => editor.chain().focus().toggleHeading({ level: 2 }).run(), "H2")}
        {tool("Tiêu đề phụ", editor.isActive("heading", { level: 3 }), () => editor.chain().focus().toggleHeading({ level: 3 }).run(), "H3")}
        {tool("Đậm", editor.isActive("bold"), () => editor.chain().focus().toggleBold().run(), <strong>B</strong>)}
        {tool("Nghiêng", editor.isActive("italic"), () => editor.chain().focus().toggleItalic().run(), <em>I</em>)}
        {tool("Danh sách chấm", editor.isActive("bulletList"), () => editor.chain().focus().toggleBulletList().run(), <span aria-hidden="true">•</span>)}
        {tool("Danh sách số", editor.isActive("orderedList"), () => editor.chain().focus().toggleOrderedList().run(), <span aria-hidden="true">1.</span>)}
        {tool("Trích dẫn", editor.isActive("blockquote"), () => editor.chain().focus().toggleBlockquote().run(), <span aria-hidden="true">&ldquo;</span>)}
        {tool("Chèn liên kết", editor.isActive("link"), () => setDialog("link"), <Icon name="link" />)}
        <button type="button" className={s.toolBtn} onClick={() => setDialog("item")} title="Chèn thẻ mặt hàng" disabled={disabled}>
          <Icon name="shopping_bag" />
          <span className={s.toolText}>Mặt hàng</span>
        </button>
      </div>

      <div className={s.editorArea}>
        <EditorContent editor={editor} />
      </div>

      {dialog === "item" && (
        <ItemPickerModal
          onClose={() => setDialog(null)}
          onPick={(code) => {
            editor.chain().focus().insertContent({ type: "itemCard", attrs: { itemCode: code } }).run();
            setDialog(null);
          }}
        />
      )}
      {dialog === "link" && (
        <LinkModal
          initial={(editor.getAttributes("link").href as string | undefined) ?? ""}
          onClose={() => setDialog(null)}
          onApply={(href) => {
            editor.chain().focus().extendMarkRange("link").setLink({ href }).run();
            setDialog(null);
          }}
          onRemove={() => {
            editor.chain().focus().extendMarkRange("link").unsetLink().run();
            setDialog(null);
          }}
        />
      )}
    </div>
  );
});

TiptapEditor.displayName = "TiptapEditor";

export default TiptapEditor;
