"use client";

// Thiết lập bài viết (ED-35 / F3l): phân loại, tóm tắt và tìm kiếm, ảnh bìa. Là một trang form (FormPage), thanh nút dính đáy.
// Bài nháp: "Lưu nháp" + "Gửi duyệt". Bài đã gửi duyệt/đã đăng: "Lưu thay đổi" + "Quay lại".
// Loại nội dung chỉ chọn được khi bài chưa lưu. Vai trò trang bắt buộc bị khoá khi trang đang đăng.

import { ENUMS } from "@/shared/lib/enums";
import { Field } from "@/shared/ui/form/Field";
import { FormPage } from "@/shared/ui/form/FormPage";
import { coverImageOf, type EntryForm } from "../contentModel";
import { CONTENT_MSG as M } from "../messages";
import type { ContentCategory, ContentImage, ContentKind, ContentPageRole } from "../types";
import s from "../content.module.css";

const PAGE_ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: M.fieldPageRoleNone },
  ...Object.entries(ENUMS.entryPageRole).map(([value, v]) => ({ value, label: v.label })),
];

type Props = {
  form: EntryForm;
  onChange: (patch: Partial<EntryForm>) => void;
  categories: ContentCategory[];
  categoriesFailed: boolean;
  images: ContentImage[];
  coverAlt: string;
  onCoverAlt: (v: string) => void;
  fieldErrors: Record<string, string>;
  alert: React.ReactNode;
  saved: boolean;
  pageRoleLocked: boolean;
  isDraft: boolean;
  readOnly: boolean;
  submitting: boolean;
  onSave: () => void;
  onBack: () => void;
  onSubmitReview: (() => void) | null;
};

export function EntrySettings(p: Props) {
  const { form, onChange, fieldErrors } = p;
  const cover = coverImageOf(p.images, form.coverImageId);
  const categoryOptions = [
    { value: "", label: M.fieldCategoryNone },
    ...p.categories.filter((c) => c.is_active || c.id === form.category).map((c) => ({ value: String(c.id), label: c.is_active ? c.name : `${c.name} (đã ngừng dùng)` })),
  ];
  const coverOptions = [
    { value: "", label: M.coverNone },
    ...p.images.map((img, i) => ({ value: String(img.id), label: img.alt ? `${M.coverImageOption(i + 1)}: ${img.alt}` : M.coverImageOption(i + 1) })),
  ];

  // Bài nháp: nút chính là "Gửi duyệt" (nếu có quyền), phụ là "Lưu nháp". Còn lại: "Lưu thay đổi" + "Quay lại".
  const draftWithSubmit = p.isDraft && p.onSubmitReview !== null;
  return (
    <FormPage
      title={M.settingsTitle}
      alert={p.alert}
      onSubmit={() => (draftWithSubmit ? p.onSubmitReview?.() : p.onSave())}
      primaryText={draftWithSubmit ? M.submitReview : M.settingsSave}
      submitting={p.submitting}
      primaryDisabled={p.readOnly}
      secondary={draftWithSubmit ? { label: M.saveDraft, onClick: p.onSave } : { label: M.settingsBackLabel, onClick: p.onBack }}
    >
      <section className={s.card} aria-label={M.sectionClass}>
        <h3 className={s.cardTitle}>{M.sectionClass}</h3>
        <Field
          as="select"
          label={M.fieldKind}
          value={form.kind}
          disabled={p.readOnly || p.saved}
          options={[
            { value: "post", label: M.kindPostOption },
            { value: "page", label: M.kindPageOption },
          ]}
          onChange={(v) => onChange({ kind: v as ContentKind })}
        />
        {form.kind === "post" ? (
          <Field
            as="select"
            label={M.fieldCategory}
            required
            value={form.category === null ? "" : String(form.category)}
            disabled={p.readOnly}
            error={fieldErrors.category ?? (p.categoriesFailed ? M.loadFailed : null)}
            options={categoryOptions}
            onChange={(v) => onChange({ category: v ? Number(v) : null })}
          />
        ) : (
          <>
            <Field
              as="select"
              label={M.fieldPageRole}
              value={form.pageRole ?? ""}
              disabled={p.readOnly || p.pageRoleLocked}
              error={fieldErrors.page_role ?? (p.pageRoleLocked ? M.pageRoleLocked : null)}
              options={PAGE_ROLE_OPTIONS}
              onChange={(v) => onChange({ pageRole: (v || null) as ContentPageRole })}
            />
            <label className="check-row">
              <input type="checkbox" checked={form.showInFooter} disabled={p.readOnly} onChange={(e) => onChange({ showInFooter: e.target.checked })} />
              <span>
                <b>{M.fieldFooter}</b>
              </span>
            </label>
            {form.showInFooter && (
              <Field
                label={M.fieldFooterOrder}
                type="number"
                value={String(form.footerOrder)}
                disabled={p.readOnly}
                error={fieldErrors.footer_order}
                onChange={(v) => onChange({ footerOrder: /^\d{1,4}$/.test(v) ? Number(v) : 0 })}
              />
            )}
          </>
        )}
      </section>

      <section className={s.card} aria-label={M.sectionSearch}>
        <h3 className={s.cardTitle}>{M.sectionSearch}</h3>
        <Field
          as="textarea"
          label={M.fieldExcerpt}
          value={form.excerpt}
          maxLength={300}
          counter
          rows={3}
          disabled={p.readOnly}
          error={fieldErrors.excerpt}
          onChange={(v) => onChange({ excerpt: v })}
        />
        <Field label={M.fieldSeoTitle} value={form.seoTitle} maxLength={70} disabled={p.readOnly} error={fieldErrors.seo_title} onChange={(v) => onChange({ seoTitle: v })} />
        <Field
          as="textarea"
          label={M.fieldSeoDescription}
          value={form.seoDescription}
          maxLength={160}
          counter
          rows={3}
          disabled={p.readOnly}
          error={fieldErrors.seo_description}
          onChange={(v) => onChange({ seoDescription: v })}
        />
      </section>

      <section className={s.card} aria-label={M.sectionCover}>
        <h3 className={s.cardTitle}>{M.sectionCover}</h3>
        {p.images.length === 0 ? (
          <p className="muted">{M.coverHintEmpty}</p>
        ) : (
          <>
            <Field
              as="select"
              label={M.fieldCover}
              value={form.coverImageId === null ? "" : String(form.coverImageId)}
              disabled={p.readOnly}
              error={fieldErrors.cover_image}
              options={coverOptions}
              onChange={(v) => onChange({ coverImageId: v ? Number(v) : null })}
            />
            {cover && (
              <>
                <div className={s.coverPreview}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={cover.urls.sm || cover.urls.md || cover.urls.lg} alt={p.coverAlt || cover.alt || "Ảnh bìa"} />
                </div>
                <Field
                  label={M.fieldCoverAlt}
                  required
                  value={p.coverAlt}
                  maxLength={200}
                  disabled={p.readOnly}
                  error={fieldErrors.cover_image_alt}
                  onChange={p.onCoverAlt}
                />
                <div>
                  <button type="button" className="btn" disabled={p.readOnly} onClick={() => onChange({ coverImageId: null })}>
                    {M.removeCover}
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </section>
    </FormPage>
  );
}
