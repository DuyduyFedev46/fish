"use client";

// F1c Thêm hoá đơn mua (POST /api/purchasing/invoices/). Form ngắn nên là hộp thoại, mở từ trang chi tiết phiếu
// (gắn sẵn phiếu, nhà cung cấp theo phiếu) hoặc từ danh sách hoá đơn (chọn phiếu chưa có hoá đơn hay để trống). Chỉ Chủ có quyền thêm.
// Tiền: ô type="money", gửi đúng số nguyên đồng ("1650000"). Số gợi ý từ tiền mua của phiếu làm tròn .5 lên (không cắt cụt).
// "Đã trả tiền" bật thì hiện ô "Trả lúc" (giờ Việt Nam, mặc định bây giờ); tắt thì không gửi `paid_at`.
// Ô chọn phiếu tải theo trang, lọc nhà cung cấp ở BE, có "Tải thêm" (ReceiptSelect).
import { useMemo, useState } from "react";
import { fetchSuppliers } from "@/features/purchasing/api";
import { roundToDong } from "@/features/reports/decimal";
import { loadErrorText } from "@/shared/lib/http";
import { timeHM, todayInVietnam, vnInputToIso, vnd } from "@/shared/lib/format";
import { useResource } from "@/shared/lib/useResource";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createPurchaseInvoice } from "../api";
import { CURRENCY_UNIT, moneyBody, moneyMessage, suggestedAmount } from "../money";
import type { PurchaseInvoiceRow } from "../types";
import { ReceiptSelect } from "./ReceiptSelect";
import s from "../accounting.module.css";

export type InvoiceReceiptRef = {
  id: number;
  code: string;
  supplier: number;
  supplierName: string;
  /** Tiền mua của phiếu (chỉ Chủ có): gợi ý số tiền hoá đơn. Có thể lẻ ".50", nên làm tròn trước khi đưa vào ô. */
  purchaseAmount?: number | string | null;
};

type Props = {
  /** Gắn sẵn phiếu: bỏ ô chọn phiếu và nhà cung cấp. */
  receipt?: InvoiceReceiptRef;
  onClose: () => void;
  onDone: (row: PurchaseInvoiceRow) => void;
};

const NO_RECEIPT = "";

/** "2026-09-30T15:05": giờ Việt Nam hiện tại, dạng ô datetime-local. */
function nowForInput(): string {
  return `${todayInVietnam()}T${timeHM(new Date())}`;
}

export function PurchaseInvoiceForm({ receipt, onClose, onDone }: Props) {
  const [supplier, setSupplier] = useState(receipt ? String(receipt.supplier) : "");
  const [receiptId, setReceiptId] = useState(receipt ? String(receipt.id) : NO_RECEIPT);
  const [amount, setAmount] = useState(suggestedAmount(receipt?.purchaseAmount));
  const [date, setDate] = useState(todayInVietnam());
  const [paid, setPaid] = useState(false);
  const [paidAt, setPaidAt] = useState(nowForInput);
  const [touched, setTouched] = useState(false);
  // Nhà cung cấp của phiếu đang chọn (ô chọn phiếu) và số tiền hiện tại có phải số gợi ý từ phiếu không (người gõ thì không phải).
  const [receiptSupplier, setReceiptSupplier] = useState("");
  const [amountSuggested, setAmountSuggested] = useState(false);

  // Đổi nhà cung cấp khác với nhà cung cấp của phiếu đang chọn: bỏ phiếu (và số gợi ý của nó), tránh gắn phiếu của nhà cung cấp khác (TL12-FE-M1).
  const changeSupplier = (value: string) => {
    setSupplier(value);
    if (receiptId && receiptSupplier && receiptSupplier !== value) {
      setReceiptId(NO_RECEIPT);
      setReceiptSupplier("");
      if (amountSuggested) {
        setAmount("");
        setAmountSuggested(false);
      }
    }
  };
  const typeAmount = (value: string) => {
    setAmount(value);
    setAmountSuggested(false);
  };

  const suppliers = useResource(receipt ? null : "accounting:supplier-options", () => fetchSuppliers(), 60_000);
  const supplierOptions = useMemo(
    () => [{ value: "", label: "Chọn nhà cung cấp" }, ...(suppliers.data ?? []).filter((x) => x.is_active).map((x) => ({ value: String(x.id), label: x.name }))],
    [suppliers.data],
  );

  const local: Record<string, string> = {};
  if (!supplier) local.supplier = "Chọn nhà cung cấp.";
  const amountProblem = moneyMessage(amount, { noun: "Số tiền", positive: true });
  if (amountProblem) local.amount = amountProblem;
  if (!date) local.invoice_date = "Chọn ngày hoá đơn.";
  if (paid && !vnInputToIso(paidAt)) local.paid_at = "Chọn giờ trả tiền.";

  const sub = useSubmit(
    () =>
      createPurchaseInvoice({
        supplier: Number(supplier),
        receipt: receiptId ? Number(receiptId) : null,
        amount: moneyBody(amount),
        invoice_date: date,
        is_paid: paid,
        paid_at: paid ? vnInputToIso(paidAt) : null,
      }),
    { onSuccess: onDone },
  );

  const submit = () => {
    setTouched(true);
    if (Object.keys(local).length > 0) return;
    void sub.submit();
  };
  const err = (key: string) => (touched ? local[key] : undefined) ?? sub.fieldErrors[key];
  const loadFailed = !receipt && Boolean(suppliers.error) && !suppliers.data;

  return (
    <Modal
      title="Thêm hoá đơn mua"
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={submit} disabled={sub.submitting} aria-busy={sub.submitting} data-autofocus>
            {sub.submitting ? "Đang lưu…" : primaryLabel("Lưu hoá đơn", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && (
        <div data-testid="dialog-error">
          <FormAlert>{sub.error}</FormAlert>
        </div>
      )}
      {loadFailed && <FormAlert>{loadErrorText(suppliers.error)}</FormAlert>}
      {receipt ? (
        <SummaryBlock
          label="Phiếu nhập"
          rows={[
            { label: "Phiếu nhập", value: receipt.code, mono: true },
            { label: "Nhà cung cấp", value: receipt.supplierName },
            ...(receipt.purchaseAmount ? [{ label: "Tiền mua của phiếu", value: vnd(roundToDong(String(receipt.purchaseAmount))), num: true }] : []),
          ]}
        />
      ) : (
        <>
          <Field as="select" label="Nhà cung cấp" name="supplier" required value={supplier} onChange={changeSupplier} options={supplierOptions} error={err("supplier")} />
          <ReceiptSelect
            label="Phiếu nhập"
            name="receipt"
            value={receiptId}
            supplier={supplier}
            hasInvoice="0"
            emptyLabel="Không gắn phiếu nhập"
            error={err("receipt")}
            onChange={(value, row) => {
              setReceiptId(value);
              if (!row) {
                // Bỏ phiếu: số tiền đang là số gợi ý của phiếu đó thì bỏ theo.
                setReceiptSupplier("");
                if (amountSuggested) {
                  setAmount("");
                  setAmountSuggested(false);
                }
                return;
              }
              setSupplier(String(row.supplier));
              setReceiptSupplier(String(row.supplier));
              // Không đè số người dùng đã gõ; số gợi ý của phiếu trước thì cập nhật theo phiếu mới.
              if (row.purchase_amount !== undefined && (!amount || amountSuggested)) {
                const next = suggestedAmount(row.purchase_amount);
                setAmount(next);
                setAmountSuggested(next !== "");
              }
            }}
          />
        </>
      )}
      <Field label="Số tiền hoá đơn" name="amount" type="money" required unit={CURRENCY_UNIT} value={amount} onChange={typeAmount} error={err("amount")} />
      <Field label="Ngày hoá đơn" name="invoice_date" type="date" required value={date} onChange={setDate} error={err("invoice_date")} />
      <label className="check-row">
        <input type="checkbox" name="is_paid" checked={paid} onChange={(e) => setPaid(e.target.checked)} />
        <span>
          <b>Đã trả tiền</b>
        </span>
      </label>
      {paid && (
        <div className={s.paidAt} data-testid="paid-at">
          <Field label="Trả lúc" name="paid_at" type="datetime-local" required value={paidAt} onChange={setPaidAt} error={err("paid_at")} />
        </div>
      )}
    </Modal>
  );
}
