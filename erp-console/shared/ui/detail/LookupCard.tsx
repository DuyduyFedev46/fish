"use client";

// Thẻ tra nhanh dạng popup (UI-RULES §5.4): bấm trường link (lô, mặt hàng, phiếu giao, đơn) → hộp thoại nhỏ đúng ngữ cảnh,
// có "Đóng" và "Mở trang …". Dữ liệu qua shared/lib/lookups.ts (chỉ vài trường, KHÔNG giá vốn, KHÔNG dữ liệu khách).
// Không có thẻ khách hàng. Đủ trạng thái: đang tải · lỗi (có Thử lại) · 403/404 (câu của API) · có dữ liệu.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { fetchLookup, type LookupCardData, type LookupKind } from "@/shared/lib/lookups";
import { Modal } from "../overlay/Modal";
import { SummaryBlock } from "../form/SummaryBlock";
import { Icon } from "../Icon";
import { Chip } from "../Chip";
import s from "./LookupCard.module.css";

type Props = { kind: LookupKind; id: number | string; onClose: () => void; title?: string };

export function LookupCard({ kind, id, onClose, title }: Props) {
  const [data, setData] = useState<LookupCardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      setForbidden(false);
      fetchLookup(kind, id, signal)
        .then((d) => setData(d))
        .catch((err: unknown) => {
          if (signal?.aborted) return;
          setForbidden(err instanceof ApiError && err.status === 403);
          setError(loadErrorText(err));
        })
        .finally(() => {
          if (!signal?.aborted) setLoading(false);
        });
    },
    [kind, id],
  );

  useEffect(() => {
    const ac = new AbortController();
    load(ac.signal);
    return () => ac.abort();
  }, [load]);

  return (
    <Modal
      title={data?.title ?? title ?? "Thông tin nhanh"}
      onClose={onClose}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} data-autofocus>
            Đóng
          </button>
          {data && (
            <Link href={data.href} prefetch={false} className="btn primary" onClick={onClose}>
              {data.hrefLabel}
            </Link>
          )}
        </>
      }
    >
      {loading && (
        <p className={s.state} role="status">
          <Icon name="progress_activity" className="spin" /> Đang tải…
        </p>
      )}
      {!loading && error && (
        <div className={s.state} role="alert">
          <Icon name={forbidden ? "lock" : "error"} />
          <span>{error}</span>
          {!forbidden && (
            <button type="button" className="btn" onClick={() => load()}>
              <Icon name="refresh" />
              Thử lại
            </button>
          )}
        </div>
      )}
      {!loading && data && (
        <>
          {data.status && (
            <div className={s.status}>
              <Chip entry={data.status} />
            </div>
          )}
          <SummaryBlock rows={data.rows} label={data.title} />
        </>
      )}
    </Modal>
  );
}
