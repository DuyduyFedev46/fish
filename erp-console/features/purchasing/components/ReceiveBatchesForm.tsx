"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/shared/ui/Icon";
import { listItems } from "@/features/catalog/api";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { dateOnly, todayInVietnam } from "@/shared/lib/format";
import type { CatalogItem } from "@/features/catalog/types";
import { cancelPurchaseReceipt, fetchSuppliers, submitReceiveBatches } from "../api";
import type { ReceiveBatchesLineInput, ReceiveBatchesResponse, Supplier } from "../types";
import s from "../purchasing.module.css";
import { clearDraft, loadDraft, purgeLegacyDraft, resolveIdempotencyKey, saveDraft } from "./draftStorage";

function generateUUID(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getTodayString(): string {
  return todayInVietnam();
}

export function ReceiveBatchesForm() {
  const { me } = useAuth();
  const userId = me?.id ?? null;
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loadingInitial, setLoadingInitial] = useState(true);

  const [supplierId, setSupplierId] = useState<number | "">("");
  const [receivedDate, setReceivedDate] = useState<string>(getTodayString());
  const [idempotencyKey, setIdempotencyKey] = useState<string>("");
  const [lines, setLines] = useState<ReceiveBatchesLineInput[]>([
    { item_code: "", qty: "", rate: "", shelf_life_days: null },
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<ReceiveBatchesResponse | null>(null);

  // Huỷ phiếu nhập (DW-18)
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelSuccessMsg, setCancelSuccessMsg] = useState<string | null>(null);

  // Khởi tạo key và nạp dữ liệu ban đầu. SR-07: nháp chỉ của người đang đăng nhập (sessionStorage) và KHÔNG có giá mua;
  // idempotency key: có trong nháp của CHÍNH người này thì dùng lại (F5 giữ key), không có thì sinh mới.
  useEffect(() => {
    const key = resolveIdempotencyKey(userId, generateUUID);
    let initialSupplier: number | "" = "";
    let initialDate = getTodayString();
    let initialLines: ReceiveBatchesLineInput[] = [
      { item_code: "", qty: "", rate: "", shelf_life_days: null },
    ];

    purgeLegacyDraft(); // khoá cũ ở localStorage có giá mua, dùng chung mọi người
    const draft = userId !== null ? loadDraft(userId) : null;
    if (draft) {
      if (draft.supplierId) initialSupplier = draft.supplierId;
      if (draft.receivedDate) initialDate = draft.receivedDate;
      if (draft.lines.length > 0) initialLines = draft.lines.map((l) => ({ ...l, rate: "" }));
    }

    setSupplierId(initialSupplier);
    setReceivedDate(initialDate);
    setLines(initialLines);
    setIdempotencyKey(key);

    Promise.all([
      fetchSuppliers().catch(() => []),
      listItems("all").then((r) => r.results).catch(() => []),
    ]).then(([sups, itms]) => {
      setSuppliers(sups.filter((s) => s.is_active));
      setItems(itms.filter((i) => i.is_active));
      if (!initialSupplier && sups.length > 0) {
        setSupplierId(sups[0].id);
      }
      setLoadingInitial(false);
    });
  }, [userId]);

  // Tự động lưu nháp (không gồm giá mua — xem draftStorage.ts)
  useEffect(() => {
    if (loadingInitial || userId === null) return;
    if (successResult) {
      clearDraft(userId);
    } else {
      saveDraft(userId, { supplierId, receivedDate, lines, idempotencyKey });
    }
  }, [supplierId, receivedDate, lines, idempotencyKey, loadingInitial, successResult, userId]);

  const handleAddLine = () => {
    setLines((prev) => [
      ...prev,
      { item_code: items[0]?.code || "", qty: "", rate: "", shelf_life_days: null },
    ]);
  };

  const handleRemoveLine = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleLineChange = (idx: number, field: keyof ReceiveBatchesLineInput, val: unknown) => {
    setLines((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [field]: val };
      return copy;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setCancelError(null);
    setCancelSuccessMsg(null);

    if (!supplierId) {
      setErrorMessage("Vui lòng chọn nhà cung cấp.");
      return;
    }

    if (lines.length === 0) {
      setErrorMessage("Phiếu nhập phải có ít nhất 1 mặt hàng.");
      return;
    }

    for (let i = 0; i < lines.length; i++) {
      const l = lines[i];
      if (!l.item_code) {
        setErrorMessage(`Dòng ${i + 1}: Chưa chọn mặt hàng.`);
        return;
      }
      const numQty = parseFloat(l.qty);
      if (isNaN(numQty) || numQty <= 0) {
        setErrorMessage(`Dòng ${i + 1}: Khối lượng phải lớn hơn 0 kg.`);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const payload = {
        supplier: Number(supplierId),
        received_date: receivedDate,
        idempotency_key: idempotencyKey,
        lines: lines.map((l) => ({
          item_code: l.item_code,
          qty: String(parseFloat(l.qty)),
          rate: l.rate ? String(parseFloat(l.rate)) : "0.00",
          shelf_life_days: l.shelf_life_days ? Number(l.shelf_life_days) : null,
        })),
      };

      const res = await submitReceiveBatches(payload);
      setSuccessResult(res);
      if (userId !== null) clearDraft(userId);
      setIdempotencyKey(generateUUID()); // gửi thành công → key cũ đã dùng, lần nhập sau phải key mới
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; code?: string; message?: string };
      setErrorMessage(
        errorObj.detail || errorObj.message || "Không thể lưu phiếu nhập. Vui lòng kiểm tra lại."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetNew = () => {
    setSuccessResult(null);
    setErrorMessage(null);
    setCancelError(null);
    setCancelSuccessMsg(null);
    setLines([{ item_code: items[0]?.code || "", qty: "", rate: "", shelf_life_days: null }]);
    setIdempotencyKey(generateUUID());
  };

  const handleCancelReceipt = async () => {
    if (!successResult) return;
    const receiptId = successResult.receipt.id;
    const confirmed = window.confirm(
      `Bạn có chắc chắn muốn huỷ phiếu nhập PR-${receiptId}? Các lô cá thuộc phiếu nhập này sẽ bị huỷ và hoàn kho về 0.`
    );
    if (!confirmed) return;

    setIsCancelling(true);
    setCancelError(null);
    try {
      await cancelPurchaseReceipt(receiptId);
      setSuccessResult((prev) =>
        prev
          ? {
              ...prev,
              receipt: { ...prev.receipt, status: "CANCELLED" },
              batches: prev.batches.map((b) => ({ ...b, status: "CANCELLED" })),
            }
          : null
      );
      setCancelSuccessMsg(
        `Phiếu nhập PR-${receiptId} đã được huỷ. Các lô liên quan đã chuyển trạng thái Đã huỷ (CANCELLED).`
      );
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; code?: string; message?: string };
      setCancelError(
        errorObj.detail || errorObj.message || "Không thể huỷ phiếu nhập. Vui lòng thử lại."
      );
    } finally {
      setIsCancelling(false);
    }
  };

  if (successResult) {
    const isCancelled = successResult.receipt.status === "CANCELLED";

    return (
      <div className={s.successBox}>
        <h3 className={s.successTitle}>
          <Icon name={isCancelled ? "cancel" : "check_circle"} />
          <span>
            {isCancelled
              ? `Phiếu nhập PR-${successResult.receipt.id} (ĐÃ HUỶ)`
              : `Ghi nhận phiếu nhập thành công (Mã: PR-${successResult.receipt.id})`}
          </span>
        </h3>

        {cancelSuccessMsg && (
          <div className={s.cancelledBox}>
            <Icon name="info" />
            <span>{cancelSuccessMsg}</span>
          </div>
        )}

        {cancelError && (
          <div className={s.errorBox} style={{ marginTop: "12px", marginBottom: "12px" }}>
            <strong>Lỗi huỷ phiếu: </strong>
            <span>{cancelError}</span>
          </div>
        )}

        <p className={s.desc}>
          {isCancelled
            ? `Các lô cá thuộc phiếu nhập này đã chuyển sang trạng thái Đã huỷ (CANCELLED) và hoàn kho về 0:`
            : `Hệ thống đã tự động ghi nhận phiếu nhập và sinh ${successResult.batches.length} lô cá mới ở trạng thái Nháp (DRAFT):`}
        </p>

        <ul className={s.batchList}>
          {successResult.batches.map((b) => (
            <li key={b.batch_id} className={s.batchItem}>
              <span className={b.status === "CANCELLED" ? s.batchBadgeCancelled : s.batchBadge}>
                {b.batch_id}
              </span>{" "}
              — {b.qty_available} kg —{" "}
              {b.status === "CANCELLED" ? "Trạng thái: Đã huỷ" : `Hạn dùng: ${dateOnly(b.expiry_date)}`}
            </li>
          ))}
        </ul>

        <div className={s.actions} style={{ borderTop: "none", paddingTop: 0 }}>
          {!isCancelled && (
            <button
              type="button"
              onClick={handleCancelReceipt}
              className={s.cancelBtn}
              disabled={isCancelling}
            >
              <Icon name="delete_forever" />
              <span>{isCancelling ? "Đang huỷ phiếu..." : "Huỷ phiếu nhập này"}</span>
            </button>
          )}
          <button type="button" onClick={handleResetNew} className={s.submitBtn}>
            Nhập phiếu tiếp
          </button>
          <Link href="/inventory/" className={s.addLineBtn} style={{ textDecoration: "none" }}>
            <Icon name="inventory_2" />
            <span>Xem tồn kho</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className={s.card}>
      {errorMessage && (
        <div className={s.errorBox}>
          <strong>Lỗi: </strong>
          <span>{errorMessage}</span>
        </div>
      )}

      <div className={s.gridTwo}>
        <div className={s.fieldGroup}>
          <label htmlFor="supplier-select" className={s.fieldLabel}>
            Nhà cung cấp / Đầu mối cảng *
          </label>
          <select
            id="supplier-select"
            value={supplierId}
            onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}
            className={s.select}
            disabled={isSubmitting}
            required
          >
            <option value="">-- Chọn nhà cung cấp --</option>
            {suppliers.map((sup) => (
              <option key={sup.id} value={sup.id}>
                {sup.name}
              </option>
            ))}
          </select>
        </div>

        <div className={s.fieldGroup}>
          <label htmlFor="received-date" className={s.fieldLabel}>
            Ngày nhập hàng *
          </label>
          <input
            id="received-date"
            type="date"
            value={receivedDate}
            onChange={(e) => setReceivedDate(e.target.value)}
            className={s.input}
            disabled={isSubmitting}
            required
          />
        </div>
      </div>

      <div className={s.tableContainer}>
        <table className={s.linesTable}>
          <thead>
            <tr>
              <th style={{ width: "35%" }}>Mặt hàng *</th>
              <th style={{ width: "20%" }}>Số lượng (kg) *</th>
              <th style={{ width: "25%" }}>Đơn giá mua (đ/kg)</th>
              <th style={{ width: "15%" }}>Hạn dùng (ngày)</th>
              <th style={{ width: "5%" }}></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, idx) => (
              <tr key={idx}>
                <td>
                  <select
                    value={line.item_code}
                    onChange={(e) => handleLineChange(idx, "item_code", e.target.value)}
                    className={s.select}
                    style={{ width: "100%" }}
                    disabled={isSubmitting}
                    required
                  >
                    <option value="">-- Chọn mặt hàng --</option>
                    {items.map((it) => (
                      <option key={it.code} value={it.code}>
                        {it.code} — {it.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    step="0.001"
                    min="0.001"
                    placeholder="0.000"
                    value={line.qty}
                    onChange={(e) => handleLineChange(idx, "qty", e.target.value)}
                    className={s.input}
                    style={{ width: "100%" }}
                    disabled={isSubmitting}
                    required
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="1000"
                    min="0"
                    placeholder="80000"
                    value={line.rate}
                    onChange={(e) => handleLineChange(idx, "rate", e.target.value)}
                    className={s.input}
                    style={{ width: "100%" }}
                    disabled={isSubmitting}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min="1"
                    placeholder="Mặc định"
                    value={line.shelf_life_days ?? ""}
                    onChange={(e) =>
                      handleLineChange(
                        idx,
                        "shelf_life_days",
                        e.target.value ? Number(e.target.value) : null
                      )
                    }
                    className={s.input}
                    style={{ width: "100%" }}
                    disabled={isSubmitting}
                  />
                </td>
                <td style={{ textAlign: "center" }}>
                  {lines.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveLine(idx)}
                      className={s.removeBtn}
                      title="Xoá dòng"
                      disabled={isSubmitting}
                    >
                      <Icon name="delete" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={handleAddLine}
        className={s.addLineBtn}
        disabled={isSubmitting}
      >
        <Icon name="add" />
        <span>Thêm mặt hàng</span>
      </button>

      <div className={s.actions}>
        <button
          type="submit"
          className={s.submitBtn}
          disabled={isSubmitting || lines.length === 0}
        >
          {isSubmitting ? "Đang ghi nhận..." : "Ghi nhận phiếu nhập (Nhập lô)"}
        </button>
      </div>
    </form>
  );
}
