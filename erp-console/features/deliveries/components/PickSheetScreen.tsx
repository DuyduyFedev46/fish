"use client";

// CS-16 — phiếu soạn nội bộ 100x150 mm cho NV kho cầm vào kho lạnh. Dùng dữ liệu chi tiết phiếu giao (CS-03), không cần API mới.
// Trang TỰ chặn theo quyền (`print_label` hoặc `pack_deliverynote`) TRƯỚC khi gọi API: API chi tiết trả 200 cho NV giao với phiếu của
// chính họ, nên không thể trông vào 403 (CS-16-AC4). Dữ liệu khách (tên, SĐT, địa chỉ, người nhận hộ) và giá bị bỏ ngay trong `toPickSheet`,
// không vào state hay DOM (CS-16-AC2/AC3, BR-GH-17). URL chỉ mang ?note=<số>. Không ghi log, không localStorage.
import { useRouter, useSearchParams } from "next/navigation";
import React, { useEffect, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dateOnly, kg } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { Icon } from "@/shared/ui/Icon";
import { fetchDeliveryNoteDetail } from "../api";
import { idFromSearch } from "../deliveryUi";
import { canOpenPickSheet, pickSheetBlock, toPickSheet } from "../pickSheet";
import type { PickSheetData } from "../types";
import s from "../pickSheet.module.css";

type Failure = { title: string; text: string; kind: "error" | "warn" };

const NO_PERMISSION: Failure = {
  title: "Không có quyền",
  text: "Bạn không có quyền in phiếu soạn. Nhờ Chủ cấp quyền hoặc nhờ nhân viên kho in giúp.",
  kind: "error",
};

export function PickSheetScreen() {
  const search = useSearchParams();
  const router = useRouter();
  const { status, me } = useAuth();
  const noteId = idFromSearch(search.get("note"));

  const [sheet, setSheet] = useState<PickSheetData | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const permitted = Boolean(me && canOpenPickSheet(me.permissions));

  useEffect(() => {
    if (status === "anon") {
      const qs = search.toString();
      router.replace(`/login/?next=${encodeURIComponent("/print/pick-sheet/" + (qs ? "?" + qs : ""))}`);
      return;
    }
    if (status !== "ready" || !me) return;
    // Chặn theo quyền ở máy khách trước mọi request.
    if (!canOpenPickSheet(me.permissions)) {
      setFailure(NO_PERMISSION);
      return;
    }
    if (noteId === null) {
      setFailure({ title: "Không mở được phiếu soạn", text: "Đường dẫn thiếu mã phiếu giao. Mở lại phiếu soạn từ trang chi tiết phiếu giao.", kind: "error" });
      return;
    }
    let active = true;
    fetchDeliveryNoteDetail(noteId)
      .then((detail) => {
        if (!active) return;
        const data = toPickSheet(detail);
        const block = pickSheetBlock(data.status);
        if (block) setFailure({ title: "Chưa in được phiếu soạn", text: block.text, kind: block.kind });
        else setSheet(data);
      })
      .catch((err: unknown) => {
        if (!active) return;
        const code = err instanceof ApiError ? err.status : 0;
        if (code === 403) setFailure(NO_PERMISSION);
        else if (code === 404) setFailure({ title: "Không tìm thấy phiếu", text: "Phiếu giao này không có hoặc không thuộc phạm vi của bạn.", kind: "error" });
        else setFailure({ title: "Chưa tải được phiếu soạn", text: "Kiểm tra mạng rồi mở lại phiếu soạn.", kind: "error" });
      });
    return () => {
      active = false;
    };
  }, [status, me, noteId, router, search]);

  useEffect(() => {
    if (!sheet) return;
    const timer = setTimeout(() => window.print(), 400);
    return () => clearTimeout(timer);
  }, [sheet]);

  if (failure) {
    return (
      <div className={s.state}>
        <h1 className={s.stateTitle}>{failure.title}</h1>
        <div className={`alert-box ${failure.kind === "error" ? "err" : "warn"}`} role={failure.kind === "error" ? "alert" : "status"}>
          <Icon name={failure.kind === "error" ? "error" : "warning"} />
          <span>{failure.text}</span>
        </div>
        <button type="button" className="btn" onClick={() => window.close()}>
          Đóng cửa sổ
        </button>
      </div>
    );
  }

  if (!sheet || status === "loading" || !permitted) {
    return (
      <div className={s.state} role="status" aria-live="polite">
        <p className="muted">Đang nạp phiếu soạn…</p>
      </div>
    );
  }

  return (
    <>
      <style>{`
        @page { size: 100mm 150mm; margin: 0; }
        @media print {
          body { margin: 0 !important; padding: 0 !important; color-scheme: light; background: Canvas !important; }
        }
      `}</style>

      <div className={s.bar}>
        <span>Khổ in chuẩn: 100 × 150 mm</span>
        <div className={s.barBtns}>
          <button type="button" className="btn primary" onClick={() => window.print()}>
            In phiếu soạn
          </button>
          <button type="button" className="btn" onClick={() => window.close()}>
            Đóng
          </button>
        </div>
      </div>

      <article className={s.sheet} aria-label="Phiếu soạn nội bộ" data-testid="pick-sheet">
        <header className={s.head}>
          <div className={s.kind}>Phiếu soạn · nội bộ</div>
          <div className={s.code}>{sheet.note_code}</div>
        </header>
        <ul className={s.lines}>
          {sheet.lines.map((line, i) => (
            <li className={s.line} key={`${line.batch_id}-${i}`}>
              <div className={s.row}>
                <span className={s.name}>{line.item_name}</span>
                <span className={s.qty}>{kg(line.qty_kg)}</span>
              </div>
              <div className={`${s.row} ${s.meta}`}>
                <span>
                  Lô <span className={s.batch}>{line.batch_id}</span>
                </span>
                <span className={s.expiry}>HSD {dateOnly(line.expiry_date)}</span>
              </div>
            </li>
          ))}
        </ul>
        <div className={s.total}>
          <span>Tổng số kg</span>
          <span className={s.qty}>{kg(sheet.total_kg)}</span>
        </div>
        <p className={s.foot}>Chỉ dùng trong kho. Không đưa cho khách.</p>
      </article>
    </>
  );
}
