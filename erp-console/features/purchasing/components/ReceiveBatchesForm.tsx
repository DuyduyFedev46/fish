"use client";

// F1a Nhập lô tại cảng (POST /api/purchasing/receipts/receive-batches/), trang /purchasing/new/.
// Giữ nguyên hành vi Lô 2/P8: nháp theo người dùng ở sessionStorage KHÔNG có giá mua (draftStorage.ts), idempotency key giữ qua F5 và
// đổi mới sau khi gửi thành công, dòng khối lượng 0 bị chặn trước khi gửi. Giá mua là ô tiền (type="money", số nguyên đồng).
// Không có dữ liệu cá nhân trong form; tên nhà cung cấp chỉ nằm trong ô chọn.
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { listItems } from "@/features/catalog/api";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { stripRuleCodes } from "@/features/inventory/lotView";
import { ApiError } from "@/shared/lib/http";
import { dateOnly, kg, todayInVietnam } from "@/shared/lib/format";
import { useResource } from "@/shared/lib/useResource";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { useToast } from "@/shared/ui/overlay/Toast";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { cancelPurchaseReceipt, fetchSuppliers, submitReceiveBatches } from "../api";
import { receiptAbility } from "../receiptView";
import { buildReceiveLines, firstErrorKey, validateReceiveForm } from "../receiveValidation";
import type { ReceiveBatchesLineInput, ReceiveBatchesResponse } from "../types";
import s from "../purchasing.module.css";
import { clearDraft, loadDraft, purgeLegacyDraft, resolveIdempotencyKey, saveDraft } from "./draftStorage";

function generateUUID(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const EMPTY_LINE: ReceiveBatchesLineInput = { item_code: "", qty: "", rate: "", shelf_life_days: null };

type Setup = { supplierId: number | ""; receivedDate: string; lines: ReceiveBatchesLineInput[]; idempotencyKey: string };

/** Khởi tạo từ nháp của CHÍNH người đang đăng nhập (không có giá mua); chưa có nháp thì form trống. */
function initialSetup(userId: number | null): Setup {
  const idempotencyKey = resolveIdempotencyKey(userId, generateUUID);
  purgeLegacyDraft(); // khoá cũ ở localStorage có giá mua, dùng chung mọi người
  const draft = userId !== null ? loadDraft(userId) : null;
  return {
    supplierId: draft?.supplierId ? draft.supplierId : "",
    receivedDate: draft?.receivedDate ? draft.receivedDate : todayInVietnam(),
    lines: draft && draft.lines.length > 0 ? draft.lines.map((l) => ({ ...l, rate: "" })) : [{ ...EMPTY_LINE }],
    idempotencyKey,
  };
}

export function ReceiveBatchesForm() {
  const { me } = useAuth();
  if (!me) return null;
  if (!receiptAbility(me).create) return <NoPermission homeHref="/purchasing/" />;
  return <FormLoader userId={me.id} />;
}

function FormLoader({ userId }: { userId: number }) {
  const lookups = useResource(
    "purchasing:receive-form-lookups",
    async () => {
      const [suppliers, items] = await Promise.all([fetchSuppliers(), listItems("all").then((r) => r.results)]);
      return { suppliers: suppliers.filter((x) => x.is_active), items: items.filter((i) => i.is_active) };
    },
    0,
  );
  if (lookups.error && !lookups.data) return <ErrorScreen onRetry={() => void lookups.reload()} homeHref="/purchasing/" />;
  if (!lookups.data) {
    return (
      <SkeletonScreen label="Đang tải nhà cung cấp và mặt hàng…">
        <SkeletonTable rows={3} cols={2} />
      </SkeletonScreen>
    );
  }
  return <FormBody userId={userId} suppliers={lookups.data.suppliers} items={lookups.data.items} />;
}

function FormBody({ userId, suppliers, items }: { userId: number; suppliers: { id: number; name: string }[]; items: { code: string; name: string }[] }) {
  const toast = useToast();
  const [setup] = useState(() => initialSetup(userId));
  const [supplierId, setSupplierId] = useState<number | "">(setup.supplierId || suppliers[0]?.id || "");
  const [receivedDate, setReceivedDate] = useState(setup.receivedDate);
  const [idempotencyKey, setIdempotencyKey] = useState(setup.idempotencyKey);
  const [lines, setLines] = useState<ReceiveBatchesLineInput[]>(setup.lines);
  const [touched, setTouched] = useState(false);
  const [result, setResult] = useState<ReceiveBatchesResponse | null>(null);

  // Tự lưu nháp (không gồm giá mua — xem draftStorage.ts); gửi xong thì xoá.
  useEffect(() => {
    if (result) clearDraft(userId);
    else saveDraft(userId, { supplierId, receivedDate, lines, idempotencyKey });
  }, [supplierId, receivedDate, lines, idempotencyKey, result, userId]);

  const supplierOptions = useMemo(() => [{ value: "", label: "Chọn nhà cung cấp" }, ...suppliers.map((x) => ({ value: String(x.id), label: x.name }))], [suppliers]);
  const itemOptions = useMemo(() => [{ value: "", label: "Chọn mặt hàng" }, ...items.map((i) => ({ value: i.code, label: `${i.code} — ${i.name}` }))], [items]);

  const sub = useSubmit(
    () =>
      submitReceiveBatches({
        supplier: Number(supplierId),
        received_date: receivedDate,
        idempotency_key: idempotencyKey,
        lines: buildReceiveLines(lines),
      }),
    {
      onSuccess: (res) => {
        setResult(res);
        clearDraft(userId);
        setIdempotencyKey(generateUUID()); // key cũ đã dùng; lần nhập sau phải key mới
      },
    },
  );

  const setLine = (idx: number, patch: Partial<ReceiveBatchesLineInput>) => setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));

  // Lỗi tính lại mỗi lần gõ; chỉ hiện sau lần bấm Ghi nhận đầu tiên, và hiện ngay dưới từng ô (UI-RULES §3).
  const errors = validateReceiveForm({ supplierId, lines });
  const shown = (key: string) => (touched ? errors[key] : undefined);

  const submit = () => {
    setTouched(true);
    const first = firstErrorKey(errors, lines.length);
    if (first) {
      // Đưa con trỏ tới ô lỗi đầu tiên (ô có thể chưa vẽ lỗi, nên chờ một khung hình).
      requestAnimationFrame(() => document.getElementsByName(first)[0]?.focus());
      return;
    }
    void sub.submit();
  };

  const saveNow = () => {
    saveDraft(userId, { supplierId, receivedDate, lines, idempotencyKey });
    toast.success("Đã lưu nháp trên máy này. Giá mua không được lưu.");
  };

  const reset = () => {
    setResult(null);
    setTouched(false);
    setLines([{ ...EMPTY_LINE }]);
    setIdempotencyKey(generateUUID());
  };

  if (result) return <SuccessView result={result} supplierName={suppliers.find((x) => x.id === Number(supplierId))?.name} onChange={setResult} onReset={reset} />;

  const alert = sub.error ? <FormAlert>{sub.error}</FormAlert> : undefined;

  return (
    <FormPage
      title="Nhập lô tại cảng"
      back={{ href: "/purchasing/", label: "Mua hàng" }}
      alert={alert}
      onSubmit={submit}
      primaryText="Ghi nhận phiếu nhập"
      submitting={sub.submitting}
      failed={sub.failed}
      secondary={{ label: "Lưu nháp", onClick: saveNow }}
    >
      <div className={s.twoCols}>
        <Field
          as="select"
          label="Nhà cung cấp"
          name="supplier"
          required
          value={supplierId === "" ? "" : String(supplierId)}
          onChange={(v) => setSupplierId(v ? Number(v) : "")}
          options={supplierOptions}
          error={shown("supplier") ?? sub.fieldErrors.supplier}
        />
        <Field label="Ngày nhập hàng" name="received_date" type="date" required value={receivedDate} onChange={setReceivedDate} error={sub.fieldErrors.received_date} />
      </div>
      <div className={s.lines} role="group" aria-label="Các mặt hàng nhập">
        {lines.map((line, idx) => (
          <div key={idx} className={s.lineCard}>
            <div className={s.lineHead}>
              <span>Mặt hàng {idx + 1}</span>
              {lines.length > 1 && (
                <button type="button" className={s.iconBtn} onClick={() => setLines((prev) => prev.filter((_, i) => i !== idx))} aria-label={`Xoá dòng ${idx + 1}`} disabled={sub.submitting}>
                  <Icon name="delete" />
                </button>
              )}
            </div>
            <div className={s.lineGrid}>
              <Field as="select" label="Mặt hàng" name={`item-${idx}`} required value={line.item_code} onChange={(v) => setLine(idx, { item_code: v })} options={itemOptions} error={shown(`item-${idx}`)} />
              <Field label="Khối lượng" name={`qty-${idx}`} type="number" required unit="kg" value={line.qty} onChange={(v) => setLine(idx, { qty: v })} error={shown(`qty-${idx}`)} />
              <Field label="Giá mua" name={`rate-${idx}`} type="money" unit="đ/kg" value={line.rate} onChange={(v) => setLine(idx, { rate: v })} error={shown(`rate-${idx}`)} />
              <Field
                label="Hạn dùng"
                name={`shelf-${idx}`}
                type="number"
                unit="ngày"
                value={line.shelf_life_days ? String(line.shelf_life_days) : ""}
                onChange={(v) => setLine(idx, { shelf_life_days: v && Number(v) > 0 ? Number(v) : null })}
              />
            </div>
          </div>
        ))}
      </div>
      <button type="button" className={`btn ${s.addLine}`} onClick={() => setLines((prev) => [...prev, { ...EMPTY_LINE }])} disabled={sub.submitting}>
        <Icon name="add" />
        <span>Thêm mặt hàng</span>
      </button>
    </FormPage>
  );
}

function SuccessView({ result, supplierName, onChange, onReset }: { result: ReceiveBatchesResponse; supplierName?: string; onChange: (r: ReceiveBatchesResponse) => void; onReset: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const code = `PR-${result.receipt.id}`;
  const cancelled = result.receipt.status === "CANCELLED";
  return (
    <div className={s.successBox} data-testid="receive-success">
      <h2 className={`${s.successTitle} ${cancelled ? s.cancelledTitle : ""}`}>
        <Icon name={cancelled ? "cancel" : "check_circle"} />
        <span>{cancelled ? `Phiếu nhập ${code} đã huỷ` : `Ghi nhận phiếu nhập thành công (Mã: ${code})`}</span>
      </h2>
      {supplierName && <p className="muted">Nhà cung cấp: {supplierName}</p>}
      <p className="muted">{cancelled ? "Các lô thuộc phiếu này đã chuyển sang Đã huỷ và hoàn kho về 0." : `Hệ thống đã sinh ${result.batches.length} lô mới ở trạng thái Nháp.`}</p>
      <ul className={s.batchList}>
        {result.batches.map((b) => (
          <li key={b.batch_id} className={s.batchItem}>
            <span className={`${s.batchCode} ${b.status === "CANCELLED" ? s.batchCodeCancelled : ""}`}>{b.batch_id}</span>
            <span className="num">{kg(b.qty_available)}</span>
            <span>{b.status === "CANCELLED" ? "Đã huỷ" : `Hạn dùng ${dateOnly(b.expiry_date)}`}</span>
          </li>
        ))}
      </ul>
      <div className={s.actions}>
        <button type="button" className="btn primary" onClick={onReset}>
          Nhập phiếu tiếp
        </button>
        <Link href={`/purchasing/detail/?id=${result.receipt.id}`} className="btn">
          Xem phiếu
        </Link>
        <Link href="/inventory/" className="btn">
          Xem tồn kho
        </Link>
        {!cancelled && (
          <button type="button" className="btn danger" onClick={() => setConfirming(true)}>
            Huỷ phiếu nhập này
          </button>
        )}
      </div>
      {confirming && (
        <CancelJustCreated
          code={code}
          id={result.receipt.id}
          onClose={() => setConfirming(false)}
          onDone={() => {
            setConfirming(false);
            onChange({ ...result, receipt: { ...result.receipt, status: "CANCELLED" }, batches: result.batches.map((b) => ({ ...b, status: "CANCELLED" })) });
          }}
        />
      )}
    </div>
  );
}

function CancelJustCreated({ id, code, onClose, onDone }: { id: number; code: string; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const sub = useSubmit(
    async () => {
      try {
        return await cancelPurchaseReceipt(id);
      } catch (err) {
        if (err instanceof ApiError) throw new ApiError(stripRuleCodes(err.message), err.status, err.code, err.details);
        throw err;
      }
    },
    {
      onSuccess: () => {
        toast.success(`Đã huỷ phiếu ${code}.`);
        onDone();
      },
    },
  );
  return (
    <Modal
      title="Huỷ phiếu nhập"
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn danger solid" onClick={() => void sub.submit()} disabled={sub.submitting} aria-busy={sub.submitting} data-autofocus>
            {sub.submitting ? "Đang huỷ…" : primaryLabel("Huỷ phiếu", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <FormAlert>{sub.error}</FormAlert>}
      <p>Huỷ phiếu {code}? Các lô Nháp của phiếu sẽ bị huỷ và hoàn kho về 0.</p>
    </Modal>
  );
}
