"use client";

// F3m Thêm kho (chỉ Chủ): tên + loại ("Kho" hoặc "Nhóm kho"). Lỗi về tên của máy chủ (trống, quá dài, trùng) hiện nguyên câu
// dưới ô tên; lỗi khác (mạng, quyền) hiện ở đầu hộp. Giữ nguyên giá trị đã nhập khi lỗi (UI-RULES §6.6).
import { useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { addWarehouse } from "../api";

const NAME_MAX = 120;
const KIND_OPTIONS = [
  { value: "warehouse", label: "Kho" },
  { value: "group", label: "Nhóm kho" },
];

export function AddWarehouseModal({ onClose, onDone }: { onClose: () => void; onDone: (name: string) => void }) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState("warehouse");
  const [nameError, setNameError] = useState<string | null>(null);

  const sub = useSubmit(
    async () => {
      const trimmed = name.trim();
      if (!trimmed) {
        setNameError("Nhập tên kho.");
        return null;
      }
      setNameError(null);
      try {
        return await addWarehouse({ name: trimmed, is_group: kind === "group" });
      } catch (err) {
        if (err instanceof ApiError && err.code?.startsWith("WAREHOUSE_NAME")) {
          setNameError(err.message);
          return null; // lỗi đã hiện dưới ô tên; không đưa thêm alert đầu hộp
        }
        throw err;
      }
    },
    { onSuccess: (w) => w && onDone(w.name) },
  );

  return (
    <Modal
      title="Thêm kho"
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Huỷ
          </button>
          <button type="button" className="btn primary" onClick={() => void sub.submit()} disabled={sub.submitting} aria-busy={sub.submitting}>
            {sub.submitting ? "Đang lưu…" : primaryLabel("Thêm kho", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <FormAlert>{sub.error}</FormAlert>}
      <Field
        label="Tên kho"
        required
        value={name}
        onChange={(v) => {
          setName(v);
          setNameError(null);
        }}
        maxLength={NAME_MAX}
        error={nameError}
        autoFocus
      />
      <Field label="Loại" as="select" value={kind} onChange={setKind} options={KIND_OPTIONS} />
    </Modal>
  );
}
