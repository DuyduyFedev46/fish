"use client";

// F1d Thêm chi phí phụ (POST /api/purchasing/costs/), trang /purchasing/costs/new/?receipt=<id>. CHỈ CHỦ (chi phí là giá vốn).
// Chủ nhập loại, tổng tiền, cách chia; hệ thống chia sẵn cho các lô của phiếu (theo số kg hoặc theo giá trị), Chủ sửa tay từng lô được.
// AC4: tổng các phần phải đúng bằng tổng chi phí. Lệch thì alert đỏ nói rõ còn thiếu/thừa bao nhiêu và nút "Lưu chi phí" bị khoá.
// Tiền gửi đúng số nguyên đồng (không làm tròn). Không có dữ liệu cá nhân nào trong form.
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { fetchReceipt, fetchSuppliers } from "@/features/purchasing/api";
import { receiptAbility } from "@/features/purchasing/receiptView";
import type { ReceiptDetail } from "@/features/purchasing/types";
import { ApiError } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { kg, todayInVietnam, vnd } from "@/shared/lib/format";
import { formatMoneyInput } from "@/shared/lib/moneyInput";
import { useResource } from "@/shared/lib/useResource";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit } from "@/shared/ui/form/useSubmit";
import { useToast } from "@/shared/ui/overlay/Toast";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { createPurchaseCost } from "../api";
import { checkAllocation, splitCost, type AllocationMethod } from "../costAllocation";
import { CURRENCY_UNIT, moneyBody, moneyMessage, parseMoney } from "../money";
import type { CostTargetBatch } from "../types";
import { ReceiptSelect } from "./ReceiptSelect";
import s from "../accounting.module.css";

const COST_TYPE_OPTIONS = Object.entries(ENUMS.purchaseCostType).map(([value, entry]) => ({ value, label: entry.label }));
const METHOD_OPTIONS = Object.entries(ENUMS.purchaseCostAllocation).map(([value, entry]) => ({ value, label: entry.label }));

/** Các lô của phiếu nhận được chi phí: dòng đã có lô (phiếu Nháp chưa có lô nào). */
export function targetsOf(receipt: ReceiptDetail): CostTargetBatch[] {
  return receipt.lines
    .filter((l) => l.batch !== null && l.batch_code && l.batch_status !== "CANCELLED")
    .map((l) => ({ batch: l.batch as number, batch_code: l.batch_code as string, item_name: l.item_name, qty: l.qty, rate: l.rate ?? "0" }));
}

export function PurchaseCostForm({ receiptId }: { receiptId: number | null }) {
  const { me } = useAuth();
  if (!me) return null;
  if (!receiptAbility(me).addCost) return <NoPermission homeHref="/purchasing/" />;
  return <PickOrForm initialId={receiptId} />;
}

function PickOrForm({ initialId }: { initialId: number | null }) {
  const [picked, setPicked] = useState<number | null>(initialId);
  if (picked === null) return <ReceiptPicker onPick={setPicked} />;
  return <LoadedReceipt key={picked} id={picked} onBackToPick={initialId === null ? () => setPicked(null) : undefined} />;
}

function ReceiptPicker({ onPick }: { onPick: (id: number) => void }) {
  // Nhà cung cấp lọc ở BE và "Tải thêm" trong ReceiptSelect, nên phiếu thứ 21 trở đi vẫn chọn được (nợ Lô 10).
  const suppliers = useResource("accounting:cost-supplier-filter", () => fetchSuppliers(), 60_000);
  const [supplier, setSupplier] = useState("");
  const [value, setValue] = useState("");
  const supplierOptions = [{ value: "", label: "Mọi nhà cung cấp" }, ...(suppliers.data ?? []).map((x) => ({ value: String(x.id), label: x.name }))];
  return (
    <FormPage
      title="Thêm chi phí phụ"
      back={{ href: "/purchasing/?tab=costs", label: "Chi phí phụ" }}
      onSubmit={() => value && onPick(Number(value))}
      primaryText="Tiếp tục"
      primaryDisabled={!value}
    >
      <Field as="select" label="Lọc theo nhà cung cấp" name="supplier_filter" value={supplier} onChange={setSupplier} options={supplierOptions} />
      <ReceiptSelect label="Phiếu nhập nhận chi phí" name="receipt" required value={value} supplier={supplier} hasInvoice="" emptyLabel="Chọn phiếu nhập" onChange={(v) => setValue(v)} />
    </FormPage>
  );
}

function LoadedReceipt({ id, onBackToPick }: { id: number; onBackToPick?: () => void }) {
  const res = useResource(`accounting:receipt-for-cost:${id}`, () => fetchReceipt(id), 0);
  if (res.error && !res.data) {
    if (res.error instanceof ApiError && res.error.status === 404) return <NotFoundScreen homeHref="/purchasing/" />;
    if (res.error instanceof ApiError && res.error.status === 403) return <NoPermission homeHref="/purchasing/" />;
    return <ErrorScreen onRetry={() => void res.reload()} homeHref="/purchasing/" />;
  }
  if (!res.data) {
    return (
      <SkeletonScreen label="Đang tải phiếu nhập…">
        <SkeletonTable rows={4} cols={2} />
      </SkeletonScreen>
    );
  }
  return <CostFormBody receipt={res.data} onBackToPick={onBackToPick} />;
}

function CostFormBody({ receipt, onBackToPick }: { receipt: ReceiptDetail; onBackToPick?: () => void }) {
  const router = useRouter();
  const toast = useToast();
  const targets = useMemo(() => targetsOf(receipt), [receipt]);
  const [costType, setCostType] = useState("ICE");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<AllocationMethod>("BY_QTY");
  const [date, setDate] = useState(todayInVietnam());
  const [note, setNote] = useState("");
  const [parts, setParts] = useState<string[]>(() => targets.map(() => ""));
  const [touched, setTouched] = useState(false);
  // Lưu xong thì khoá nút cho tới khi trang chuyển đi, tránh bấm lần hai tạo chi phí thứ hai (TL-L1).
  const [saved, setSaved] = useState(false);

  const total = parseMoney(amount);

  // Đổi tổng tiền hay cách chia thì chia lại tự động; sửa tay từng lô sau đó vẫn giữ nguyên cho tới lần đổi kế tiếp.
  useEffect(() => {
    if (total === null || total <= 0) {
      setParts(targets.map(() => ""));
      return;
    }
    setParts(splitCost(total, targets, method).map((n) => formatMoneyInput(String(n))));
  }, [total, method, targets]);

  const check = checkAllocation(
    total,
    parts.map((p) => parseMoney(p)),
  );
  // Ô lỗi (âm, quá lớn, có chữ) phải báo dưới ô và chặn gửi; không coi như 0 (QA Lô 10 B5).
  const totalProblem = moneyMessage(amount, { noun: "Tổng chi phí", positive: true });
  const partProblems = parts.map((p) => moneyMessage(p, { noun: "Số tiền", allowEmpty: true }));
  const hasProblem = Boolean(totalProblem) || partProblems.some(Boolean);
  const canSave = check.ok && !hasProblem && !saved;

  const sub = useSubmit(
    () =>
      createPurchaseCost({
        cost_type: costType,
        amount: moneyBody(amount),
        allocation_method: method,
        incurred_date: date,
        note: note.trim(),
        // Ô phần chia để trống = lô không nhận chi phí, bỏ khỏi danh sách; ô có chữ thì moneyBody ném lỗi chứ không thành 0.
        allocations: targets
          .map((t, i) => ({ batch: t.batch, amount: (parts[i] ?? "").trim() === "" ? "0" : moneyBody(parts[i]) }))
          .filter((a) => a.amount !== "0"),
      }),
    {
      onSuccess: () => {
        setSaved(true);
        toast.success("Đã lưu chi phí và chia vào giá vốn các lô.");
        router.push(`/purchasing/detail/?id=${receipt.id}`);
      },
    },
  );

  const submit = () => {
    setTouched(true);
    if (!canSave || !date) return;
    void sub.submit();
  };

  // Hiện lỗi tổng ngay khi đã gõ gì đó (nút Lưu khoá, người dùng phải thấy vì sao); ô trống thì chờ tới lần bấm.
  const amountError = (touched || amount.trim() !== "" ? totalProblem : null) ?? sub.fieldErrors.amount;
  // Lô bổ sung A #14: lỗi của BE gắn với ô Tổng chi phí (COST_AMOUNT_TOO_LARGE, INVALID_AMOUNT) chỉ hiện dưới ô, không lặp ở alert.
  // COST_LANDED_OVERFLOW gắn với phần chia vào lô (khoá `allocations`): hiện ở alert đầu form vì không có một ô riêng.
  const errorBelowField = Boolean(sub.fieldErrors.amount) && sub.error === sub.fieldErrors.amount;
  const alert = sub.error && !errorBelowField ? <FormAlert>{sub.error}</FormAlert> : check.message ? <FormAlert>{check.message}</FormAlert> : undefined;

  if (targets.length === 0) {
    return (
      <FormPage
        title="Thêm chi phí phụ"
        back={{ href: `/purchasing/detail/?id=${receipt.id}`, label: receipt.code }}
        onSubmit={() => router.push(`/purchasing/detail/?id=${receipt.id}`)}
        primaryText="Quay lại phiếu"
      >
        <FormAlert kind="warn">Phiếu {receipt.code} chưa có lô nào để chia chi phí. Ghi nhận phiếu trước.</FormAlert>
      </FormPage>
    );
  }

  return (
    <FormPage
      title="Thêm chi phí phụ"
      back={{ href: `/purchasing/detail/?id=${receipt.id}`, label: receipt.code }}
      alert={alert}
      onSubmit={submit}
      primaryText="Lưu chi phí"
      submitting={sub.submitting || saved}
      failed={sub.failed}
      primaryDisabled={!canSave}
      secondary={{ label: onBackToPick ? "Chọn phiếu khác" : "Quay lại", onClick: onBackToPick ?? (() => router.push(`/purchasing/detail/?id=${receipt.id}`)) }}
    >
      <SummaryBlock
        label="Phiếu nhập"
        rows={[
          { label: "Phiếu nhập", value: receipt.code, mono: true },
          { label: "Nhà cung cấp", value: receipt.supplier_name },
          { label: "Số lô nhận chi phí", value: String(targets.length), num: true },
        ]}
      />
      <div className={s.twoCols}>
        <Field as="select" label="Loại chi phí" name="cost_type" required value={costType} onChange={setCostType} options={COST_TYPE_OPTIONS} error={sub.fieldErrors.cost_type} />
        <Field label="Ngày phát sinh" name="incurred_date" type="date" required value={date} onChange={setDate} error={sub.fieldErrors.incurred_date} />
      </div>
      <div className={s.twoCols}>
        <Field label="Tổng chi phí" name="amount" type="money" required unit={CURRENCY_UNIT} value={amount} onChange={(v) => { setAmount(v); if (sub.failed) sub.reset(); }} error={amountError} />
        <Field as="select" label="Cách chia vào lô" name="allocation_method" value={method} onChange={(v) => setMethod(v as AllocationMethod)} options={METHOD_OPTIONS} />
      </div>
      <div className={s.allocTable} role="group" aria-label="Chia vào từng lô">
        {targets.map((t, i) => (
          <div key={t.batch} className={s.allocRow}>
            <Field
              label={`${t.batch_code} · ${t.item_name} · ${kg(t.qty)}`}
              name={`alloc-${i}`}
              type="money"
              unit={CURRENCY_UNIT}
              value={parts[i] ?? ""}
              onChange={(v) => setParts((prev) => prev.map((p, j) => (j === i ? v : p)))}
              error={partProblems[i] ?? undefined}
            />
          </div>
        ))}
        <div className={s.totalLine}>
          <span>Tổng đã chia</span>
          <strong className="num" data-testid="alloc-total">
            {vnd(check.allocated)}
          </strong>
        </div>
      </div>
      <Field as="textarea" label="Ghi chú" name="note" value={note} onChange={setNote} maxLength={200} rows={2} />
    </FormPage>
  );
}
