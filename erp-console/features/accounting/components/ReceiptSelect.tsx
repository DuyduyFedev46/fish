"use client";

// Ô chọn phiếu nhập cho form Hoá đơn mua (F1c) và form Chi phí phụ (F1d). Danh sách phiếu đã ghi nhận lấy từ BE theo trang
// (20 phiếu/trang): lọc theo nhà cung cấp ở BE và có nút "Tải thêm", nên phiếu thứ 21 trở đi vẫn chọn được (nợ Lô 10).
// Phiếu đang chọn luôn có trong danh sách dù nằm ngoài các trang đã tải hay bị bộ lọc nhà cung cấp loại ra.
// Không dùng usePagedList: đây là ô trong hộp thoại, không được tranh dải "mất mạng" của danh sách phía sau.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchReceipts } from "@/features/purchasing/api";
import type { ReceiptRow } from "@/features/purchasing/types";
import { loadErrorText } from "@/shared/lib/http";
import { Field } from "@/shared/ui/form/Field";
import { mergeReceiptPage, receiptOptions } from "../receiptOptions";
import s from "../accounting.module.css";

type Props = {
  label: string;
  name: string;
  value: string;
  /** `row` là phiếu vừa chọn (undefined khi chọn "không gắn"). */
  onChange: (value: string, row?: ReceiptRow) => void;
  /** Id nhà cung cấp để lọc ở BE; rỗng = mọi nhà cung cấp. */
  supplier: string;
  /** "0" = chỉ phiếu chưa có hoá đơn, rỗng = mọi phiếu. */
  hasInvoice: "0" | "";
  /** Chữ của lựa chọn rỗng, vd "Không gắn phiếu nhập" hoặc "Chọn phiếu nhập". */
  emptyLabel: string;
  required?: boolean;
  error?: string;
};

export function ReceiptSelect({ label, name, value, onChange, supplier, hasInvoice, emptyLabel, required, error }: Props) {
  const [rows, setRows] = useState<ReceiptRow[] | null>(null);
  const [count, setCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [moreLoading, setMoreLoading] = useState(false);
  const [picked, setPicked] = useState<ReceiptRow | null>(null);
  const seq = useRef(0);
  const page = useRef(1);

  const load = useCallback(() => {
    const id = ++seq.current;
    setRows(null);
    setFailure(null);
    fetchReceipts({ status: "SUBMITTED", supplier, date_from: "", date_to: "", has_invoice: hasInvoice }, 1)
      .then((r) => {
        if (id !== seq.current) return;
        page.current = 1;
        setRows(r.results);
        setCount(r.count);
        setHasMore(!!r.next);
      })
      .catch((e) => {
        if (id === seq.current) setFailure(e);
      });
  }, [supplier, hasInvoice]);

  useEffect(() => {
    load();
    return () => {
      seq.current += 1;
    };
  }, [load]);

  const loadMore = () => {
    const id = seq.current;
    const next = page.current + 1;
    setMoreLoading(true);
    setFailure(null);
    fetchReceipts({ status: "SUBMITTED", supplier, date_from: "", date_to: "", has_invoice: hasInvoice }, next)
      .then((r) => {
        if (id !== seq.current) return;
        page.current = next;
        setRows((prev) => mergeReceiptPage(prev, r.results));
        setCount(r.count);
        setHasMore(!!r.next);
      })
      .catch((e) => {
        if (id === seq.current) setFailure(e);
      })
      .finally(() => {
        if (id === seq.current) setMoreLoading(false);
      });
  };

  const options = useMemo(() => receiptOptions(rows, picked, value, emptyLabel), [rows, picked, value, emptyLabel]);

  const choose = (v: string) => {
    const row = (rows ?? []).find((r) => String(r.id) === v);
    setPicked(row ?? null);
    onChange(v, row);
  };

  return (
    <div className={s.picker} data-testid="receipt-select">
      <Field as="select" label={label} name={name} required={required} value={value} onChange={choose} options={options} error={error} />
      {rows === null && !failure ? (
        <p className={s.hint} role="status">
          Đang tải phiếu nhập…
        </p>
      ) : null}
      {failure ? (
        <p className={s.fieldNote} role="alert">
          {loadErrorText(failure)}{" "}
          <button type="button" className="btn" onClick={() => (rows ? loadMore() : load())}>
            Thử lại
          </button>
        </p>
      ) : null}
      {rows && !failure && rows.length === 0 ? <p className={s.hint}>Không có phiếu nhập nào phù hợp.</p> : null}
      {rows && rows.length > 0 ? (
        <div className={s.pickerFoot}>
          <span className={s.hint} data-testid="receipt-count">
            Đang hiện {rows.length} / {count} phiếu nhập
          </span>
          {hasMore ? (
            <button type="button" className="btn" onClick={loadMore} disabled={moreLoading} data-testid="receipt-more">
              {moreLoading ? "Đang tải…" : "Tải thêm phiếu nhập"}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
