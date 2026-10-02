"use client";

// F1c Thêm hoá đơn mua (POST /api/purchasing/invoices/). Form ngắn (5 trường) nên là hộp thoại, mở từ trang chi tiết phiếu
// (gắn sẵn phiếu, nhà cung cấp theo phiếu) hoặc từ tab "Hoá đơn mua" (chọn phiếu chưa có hoá đơn hay để trống). Chỉ Chủ có quyền thêm.
// Tiền: ô type="money", gửi đúng số nguyên đồng ("1650000"); không làm tròn, không số lẻ.
import { useMemo, useState } from "react";
import { fetchReceipts, fetchSuppliers } from "@/features/purchasing/api";
import type { ReceiptRow } from "@/features/purchasing/types";
import { loadErrorText } from "@/shared/lib/http";
import { todayInVietnam, vnd } from "@/shared/lib/format";
import { formatMoneyInput } from "@/shared/lib/moneyInput";
import { useResource } from "@/shared/lib/useResource";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createPurchaseInvoice } from "../api";
import { CURRENCY_UNIT, moneyBody, moneyMessage } from "../money";
import type { PurchaseInvoiceRow } from "../types";
import s from "../accounting.module.css";

export type InvoiceReceiptRef = {
  id: number;
  code: string;
  supplier: number;
  supplierName: string;
  /** Tiền mua của phiếu (chỉ Chủ có): gợi ý số tiền hoá đơn. */
  purchaseAmount?: number | null;
};

type Props = {
  /** Gắn sẵn phiếu: bỏ ô chọn phiếu và nhà cung cấp. */
  receipt?: InvoiceReceiptRef;
  onClose: () => void;
  onDone: (row: PurchaseInvoiceRow) => void;
};

const NO_RECEIPT = "";

export function PurchaseInvoiceForm({ receipt, onClose, onDone }: Props) {
  const [supplier, setSupplier] = useState(receipt ? String(receipt.supplier) : "");
  const [receiptId, setReceiptId] = useState(receipt ? String(receipt.id) : NO_RECEIPT);
  const [amount, setAmount] = useState(receipt?.purchaseAmount ? formatMoneyInput(String(Math.round(receipt.purchaseAmount))) : "");
  const [date, setDate] = useState(todayInVietnam());
  const [paid, setPaid] = useState("0");
  const [touched, setTouched] = useState(false);

  const suppliers = useResource(receipt ? null : "accounting:supplier-options", () => fetchSuppliers(), 60_000);
  const receipts = useResource(
    receipt ? null : "accounting:receipts-without-invoice",
    () => fetchReceipts({ status: "SUBMITTED", supplier: "", date_from: "", date_to: "", has_invoice: "0" }, 1),
    0,
  );

  const supplierOptions = useMemo(
    () => [{ value: "", label: "Chọn nhà cung cấp" }, ...(suppliers.data ?? []).filter((x) => x.is_active).map((x) => ({ value: String(x.id), label: x.name }))],
    [suppliers.data],
  );
  const receiptOptions = useMemo(
    () => [
      { value: NO_RECEIPT, label: "Không gắn phiếu nhập" },
      ...(receipts.data?.results ?? []).map((r) => ({ value: String(r.id), label: `${r.code} · ${r.supplier_name}` })),
    ],
    [receipts.data],
  );

  const pickReceipt = (value: string) => {
    setReceiptId(value);
    const row: ReceiptRow | undefined = receipts.data?.results.find((r) => String(r.id) === value);
    if (!row) return;
    setSupplier(String(row.supplier));
    if (row.purchase_amount !== undefined && !amount) setAmount(formatMoneyInput(String(Math.round(Number(row.purchase_amount)))));
  };

  const local: Record<string, string> = {};
  if (!supplier) local.supplier = "Chọn nhà cung cấp.";
  const amountProblem = moneyMessage(amount, { noun: "Số tiền", positive: true });
  if (amountProblem) local.amount = amountProblem;
  if (!date) local.invoice_date = "Chọn ngày hoá đơn.";

  const sub = useSubmit(
    () =>
      createPurchaseInvoice({
        supplier: Number(supplier),
        receipt: receiptId ? Number(receiptId) : null,
        amount: moneyBody(amount),
        invoice_date: date,
        is_paid: paid === "1",
        paid_at: paid === "1" ? new Date().toISOString() : null,
      }),
    { onSuccess: onDone },
  );

  const submit = () => {
    setTouched(true);
    if (Object.keys(local).length > 0) return;
    void sub.submit();
  };
  const err = (key: string) => (touched ? local[key] : undefined) ?? sub.fieldErrors[key];
  const loadFailed = !receipt && Boolean(suppliers.error || receipts.error) && !suppliers.data;

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
      {loadFailed && <FormAlert>{loadErrorText(suppliers.error ?? receipts.error)}</FormAlert>}
      {receipt ? (
        <SummaryBlock
          label="Phiếu nhập"
          rows={[
            { label: "Phiếu nhập", value: receipt.code, mono: true },
            { label: "Nhà cung cấp", value: receipt.supplierName },
            ...(receipt.purchaseAmount ? [{ label: "Tiền mua của phiếu", value: vnd(receipt.purchaseAmount), num: true }] : []),
          ]}
        />
      ) : (
        <>
          <Field as="select" label="Phiếu nhập" name="receipt" value={receiptId} onChange={pickReceipt} options={receiptOptions} error={err("receipt")} />
          <Field as="select" label="Nhà cung cấp" name="supplier" required value={supplier} onChange={setSupplier} options={supplierOptions} error={err("supplier")} />
        </>
      )}
      <Field label="Số tiền hoá đơn" name="amount" type="money" required unit={CURRENCY_UNIT} value={amount} onChange={setAmount} error={err("amount")} />
      <div className={s.twoCols}>
        <Field label="Ngày hoá đơn" name="invoice_date" type="date" required value={date} onChange={setDate} error={err("invoice_date")} />
        <Field
          as="select"
          label="Tình trạng"
          name="is_paid"
          value={paid}
          onChange={setPaid}
          options={[
            { value: "0", label: "Chưa trả tiền" },
            { value: "1", label: "Đã trả tiền" },
          ]}
        />
      </div>
    </Modal>
  );
}
