"use client";

// "Tìm khách gọi lại": tra đơn theo số điện thoại (đủ từ 9 chữ số) hoặc mã đơn. Từ khoá gửi bằng POST (không để số điện thoại lên URL),
// không lưu vào máy hay log. Kết quả trong phạm vi: tên + số đủ + nút mở. Ngoài phạm vi: chỉ số đã che do BE trả, không mở được.
import Link from "next/link";
import { useRef, useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { Modal } from "@/shared/ui/overlay/Modal";
import { PersonalText } from "@/shared/ui/PersonalText";
import { searchCustomers } from "../api";
import { detailHref } from "../confirmationUi";
import type { CustomerSearchResultItem } from "../types";
import s from "../confirmation.module.css";

export const SEARCH_MESSAGES = {
  empty: "Nhập số điện thoại hoặc mã đơn.",
  shortPhone: "Nhập đủ số điện thoại (ít nhất 9 chữ số) hoặc mã đơn.",
  none: "Không có đơn nào khớp.",
};

/** Kiểm từ khoá trước khi gửi (BE vẫn là lớp chặn thật). null = hợp lệ. */
export function searchQueryError(q: string): string | null {
  const t = q.trim();
  if (!t) return SEARCH_MESSAGES.empty;
  const digits = t.replace(/[\s.\-]/g, "").replace(/^\+84/, "0");
  if (/^\d+$/.test(digits) && digits.length < 9) return SEARCH_MESSAGES.shortPhone;
  return null;
}

export function SearchCustomerModal({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [state, setState] = useState<{ kind: "idle" } | { kind: "loading" } | { kind: "error"; message: string } | { kind: "done"; rows: CustomerSearchResultItem[] }>({ kind: "idle" });
  const seq = useRef(0);

  const run = async () => {
    const bad = searchQueryError(q);
    setFieldError(bad);
    if (bad) return;
    const mine = ++seq.current;
    setState({ kind: "loading" });
    try {
      const res = await searchCustomers(q.trim());
      if (mine === seq.current) setState({ kind: "done", rows: res.results });
    } catch (err) {
      if (mine === seq.current) setState({ kind: "error", message: err instanceof Error && err.message ? err.message : "Chưa tìm được. Kiểm tra mạng rồi bấm Tìm lại." });
    }
  };

  return (
    <Modal
      title="Tìm khách gọi lại"
      onClose={onClose}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          Đóng
        </button>
      }
    >
      <form
        className={s.searchForm}
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
      >
        <Field label="Số điện thoại hoặc mã đơn" value={q} onChange={(v) => { setQ(v); setFieldError(null); }} error={fieldError} autoFocus />
        <button type="submit" className="btn primary" disabled={state.kind === "loading"}>
          {state.kind === "loading" ? "Đang tìm…" : "Tìm"}
        </button>
      </form>

      {state.kind === "error" && <FormAlert>{state.message}</FormAlert>}
      {state.kind === "done" && state.rows.length === 0 && (
        <p className="muted" role="status">
          {SEARCH_MESSAGES.none}
        </p>
      )}
      {state.kind === "done" && state.rows.length > 0 && (
        <ul className={s.results} aria-label="Kết quả tìm kiếm">
          {state.rows.map((r) => (
            <li key={r.note_id} className={s.result}>
              <div className={s.resultMain}>
                <span className={s.resultCode}>{r.order_code}</span>
                <span className={s.resultMeta}>{r.status_label}</span>
                {r.in_scope ? (
                  <>
                    <span className={s.resultMeta}>
                      <PersonalText value={r.customer_name ?? null} whenEmpty="—" />
                    </span>
                    <span className={s.resultMeta}>
                      <PersonalText value={r.phone ?? null} whenEmpty="—" />
                    </span>
                  </>
                ) : (
                  <span className={s.maskedPhone}>{r.phone_masked}</span>
                )}
              </div>
              {r.in_scope ? (
                <Link href={detailHref(r.note_id)} className="btn" onClick={onClose}>
                  <span>Mở đơn</span>
                  <Icon name="arrow_forward" />
                </Link>
              ) : (
                <span className="muted">Ngoài phạm vi gọi, chỉ xem</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
