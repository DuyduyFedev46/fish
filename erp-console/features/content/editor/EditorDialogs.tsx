"use client";

// Hai hộp nhỏ của trình soạn thảo: chèn liên kết và chọn mặt hàng Shop (CMS-06-AC1).
// Dùng Modal chung, không dùng prompt/alert của trình duyệt. Mặt hàng lấy từ danh mục công khai của Shop (không có giá vốn).

import { useEffect, useId, useMemo, useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { fetchShopCatalog, type ShopCatalogItem } from "../api";
import { isSafeHref } from "./safeHref";
import s from "./TiptapEditor.module.css";

const LINK_INVALID = "Đường dẫn chưa đúng. Chỉ nhận liên kết https, http, mailto, tel hoặc đường dẫn nội bộ.";

export function LinkModal({ initial, onApply, onRemove, onClose }: { initial: string; onApply: (href: string) => void; onRemove: () => void; onClose: () => void }) {
  const formId = useId();
  const [href, setHref] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const submit = () => {
    const v = href.trim();
    if (!v) {
      onRemove();
      return;
    }
    if (!isSafeHref(v)) {
      setError(LINK_INVALID);
      return;
    }
    onApply(v);
  };
  return (
    <Modal
      title="Chèn liên kết"
      onClose={onClose}
      size="sm"
      footer={
        <>
          {initial && (
            <button type="button" className="btn danger" onClick={onRemove}>
              Bỏ liên kết
            </button>
          )}
          <button type="button" className="btn" onClick={onClose}>
            Huỷ
          </button>
          <button type="submit" form={formId} className="btn primary">
            Áp dụng
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.dialogForm}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Field
          label="Địa chỉ liên kết"
          value={href}
          error={error}
          autoFocus
          onChange={(v) => {
            setHref(v);
            setError(null);
          }}
        />
      </form>
    </Modal>
  );
}

export function ItemPickerModal({ onPick, onClose }: { onPick: (itemCode: string) => void; onClose: () => void }) {
  const [items, setItems] = useState<ShopCatalogItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [q, setQ] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setItems(null);
    setFailed(false);
    fetchShopCatalog()
      .then((r) => live && setItems(r || []))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [attempt]);

  const shown = useMemo(() => {
    const t = q.trim().toLowerCase();
    return (items ?? []).filter((it) => !t || it.name.toLowerCase().includes(t) || it.item_code.toLowerCase().includes(t));
  }, [items, q]);

  return (
    <Modal
      title="Chèn thẻ mặt hàng"
      onClose={onClose}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          Đóng
        </button>
      }
    >
      <div className={s.dialogForm}>
        <Field label="Tìm theo tên hoặc mã mặt hàng" value={q} onChange={setQ} autoFocus />
        {failed ? (
          <div className="alert-box err" role="alert">
            <Icon name="error" />
            <span>Chưa tải được danh sách mặt hàng.</span>
            <button type="button" className="btn" onClick={() => setAttempt((n) => n + 1)}>
              Thử lại
            </button>
          </div>
        ) : items === null ? (
          <p className={s.pickerNote} role="status">
            Đang tải mặt hàng…
          </p>
        ) : shown.length === 0 ? (
          <p className={s.pickerNote}>Không có mặt hàng nào khớp.</p>
        ) : (
          <ul className={s.pickerList}>
            {shown.map((it) => (
              <li key={it.item_code}>
                <button type="button" className={s.pickerItem} onClick={() => onPick(it.item_code)}>
                  <span>
                    <b>{it.name}</b>
                    <span className={s.pickerCode}>{it.item_code}</span>
                  </span>
                  <span className={s.pickerAct}>Chèn thẻ</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
