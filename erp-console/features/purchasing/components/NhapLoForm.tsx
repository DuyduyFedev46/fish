"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "@/shared/ui/Icon";
import { listItems } from "@/features/catalog/api";
import type { CatalogItem } from "@/features/catalog/types";
import { fetchSuppliers, submitNhapLo } from "../api";
import type { NhapLoLineInput, NhapLoResponse, Supplier } from "../types";
import s from "../purchasing.module.css";

const DRAFT_STORAGE_KEY = "cave_draft_nhap_lo";

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
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function NhapLoForm() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loadingInitial, setLoadingInitial] = useState(true);

  const [supplierId, setSupplierId] = useState<number | "">("");
  const [receivedDate, setReceivedDate] = useState<string>(getTodayString());
  const [idempotencyKey, setIdempotencyKey] = useState<string>("");
  const [lines, setLines] = useState<NhapLoLineInput[]>([
    { item_code: "", qty: "", rate: "", shelf_life_days: null },
  ]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<NhapLoResponse | null>(null);

  // Khởi tạo key và nạp dữ liệu ban đầu
  useEffect(() => {
    let key = generateUUID();
    let initialSupplier: number | "" = "";
    let initialDate = getTodayString();
    let initialLines: NhapLoLineInput[] = [
      { item_code: "", qty: "", rate: "", shelf_life_days: null },
    ];

    if (typeof window !== "undefined" && window.localStorage) {
      const saved = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (saved) {
        try {
          const draft = JSON.parse(saved);
          if (draft.supplierId) initialSupplier = draft.supplierId;
          if (draft.receivedDate) initialDate = draft.receivedDate;
          if (Array.isArray(draft.lines) && draft.lines.length > 0) initialLines = draft.lines;
          if (draft.idempotencyKey) key = draft.idempotencyKey;
        } catch {
          // ignore corrupted draft
        }
      }
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
  }, []);

  // Tự động lưu nháp
  useEffect(() => {
    if (loadingInitial) return;
    if (typeof window !== "undefined" && window.localStorage) {
      if (successResult) {
        localStorage.removeItem(DRAFT_STORAGE_KEY);
      } else {
        localStorage.setItem(
          DRAFT_STORAGE_KEY,
          JSON.stringify({ supplierId, receivedDate, lines, idempotencyKey })
        );
      }
    }
  }, [supplierId, receivedDate, lines, idempotencyKey, loadingInitial, successResult]);

  const handleAddLine = () => {
    setLines((prev) => [
      ...prev,
      { item_code: items[0]?.code || "", qty: "", rate: "", shelf_life_days: null },
    ]);
  };

  const handleRemoveLine = (idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleLineChange = (idx: number, field: keyof NhapLoLineInput, val: unknown) => {
    setLines((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [field]: val };
      return copy;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

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

      const res = await submitNhapLo(payload);
      setSuccessResult(res);
      if (typeof window !== "undefined" && window.localStorage) {
        localStorage.removeItem(DRAFT_STORAGE_KEY);
      }
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
    setLines([{ item_code: items[0]?.code || "", qty: "", rate: "", shelf_life_days: null }]);
    setIdempotencyKey(generateUUID());
  };

  if (successResult) {
    return (
      <div className={s.successBox}>
        <h3 className={s.successTitle}>
          <Icon name="check_circle" />
          <span>Ghi nhận phiếu nhập thành công (Mã: PR-{successResult.receipt.id})</span>
        </h3>
        <p className={s.desc}>
          Hệ thống đã tự động ghi nhận phiếu nhập và sinh {successResult.batches.length} lô cá mới ở trạng thái Nháp (DRAFT):
        </p>

        <ul className={s.batchList}>
          {successResult.batches.map((b) => (
            <li key={b.batch_id} className={s.batchItem}>
              <span className={s.batchBadge}>{b.batch_id}</span> — {b.qty_available} kg — Hạn dùng: {b.expiry_date}
            </li>
          ))}
        </ul>

        <div className={s.actions} style={{ borderTop: "none", paddingTop: 0 }}>
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
