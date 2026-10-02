"use client";

// ED-28 F1f — Lập / sửa phiếu kiểm kê (trang riêng, khung FormPage). Dùng cho /stocktake/new/ và /stocktake/edit/?id=.
// Chọn kho chỉ để NẠP các lô còn tồn (kho chỉ là bộ lọc, phiếu tính theo LÔ). Nhập số đếm từng lô; lô đếm nhiều hơn sổ phải ghi lý do.
// "Lưu nháp" chỉ gửi các dòng đã nhập số; "Gửi duyệt" đòi mọi dòng đã nhập. Cả hai gọi cùng endpoint của BE (phiếu ở trạng thái Chờ duyệt).
// Tồn hệ thống hiện ở đây chỉ để xem trước chênh lệch: BE chụp lại tồn mỗi lần lưu (BR-KK-01).
// Không có số tiền (chỉ kg). Không có dữ liệu khách. Không ghi gì vào localStorage/URL/log (URL chỉ mang ?id=).
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { todayInVietnam } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { PERM, homePath } from "@/shared/lib/nav";
import { Icon } from "@/shared/ui/Icon";
import { SkeletonScreen } from "@/shared/ui/Skeleton";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit } from "@/shared/ui/form/useSubmit";
import { useToast } from "@/shared/ui/overlay/Toast";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { createStocktake, fetchStockBatches, fetchStocktake, fetchWarehouses, replaceStocktakeLines, updateStocktakeHeader } from "../api";
import {
  LIST_HREF,
  MAX_REASON,
  checkRows,
  cleanMessage,
  detailHref,
  diffTone,
  editHref,
  hasAction,
  idFromSearch,
  lineErrorOf,
  parseCount,
  previewDiff,
  qty,
  signedQty,
  summarize,
  toLineInputs,
  toMilli,
  type FormRow,
} from "../stocktakeUi";
import type { BatchOption, StocktakeDetail, WarehouseOption } from "../types";
import s from "../stocktake.module.css";

type Load = "loading" | "ready" | "error" | "notfound" | "forbidden";
type Attempt = null | "draft" | "send";

const BACK = { href: LIST_HREF, label: "Kiểm kê" };

function rowsOfDetail(d: StocktakeDetail): FormRow[] {
  return d.lines.map((l) => ({
    batch: l.batch,
    batchCode: l.batch_code,
    itemName: l.item_name,
    warehouseName: l.warehouse_name,
    systemMilli: toMilli(l.system_qty) ?? 0,
    counted: String(toMilli(l.counted_qty) === null ? "" : (toMilli(l.counted_qty) as number) / 1000).replace(".", ","),
    reason: l.reason,
  }));
}

function rowOfBatch(b: BatchOption): FormRow {
  return {
    batch: b.id,
    batchCode: b.batch_id,
    itemName: b.item_name,
    warehouseName: b.warehouse_name,
    systemMilli: toMilli(b.qty_available) ?? 0,
    counted: "",
    reason: "",
  };
}

/** Nạp lô của kho: giữ dòng đã có dữ liệu, bỏ dòng chưa chạm tới, thêm lô mới (không trùng lô). */
export function mergeLoaded(current: FormRow[], loaded: BatchOption[]): FormRow[] {
  const kept = current.filter((r) => r.counted.trim() !== "" || r.reason.trim() !== "");
  const have = new Set(kept.map((r) => r.batch));
  return [...kept, ...loaded.filter((b) => !have.has(b.id)).map(rowOfBatch)];
}

/** Câu lỗi của BE đã bỏ mã nghiệp vụ; xung đột phiên bản giữ nguyên để useSubmit bật ConflictBanner. */
function normalizeError(err: unknown): unknown {
  if (err instanceof ApiError && err.status !== 409) return new ApiError(cleanMessage(err.message), err.status, err.code, err.details);
  return err;
}

export function StocktakeForm({ mode }: { mode: "new" | "edit" }) {
  const params = useSearchParams();
  const id = mode === "edit" ? idFromSearch(params.get("id")) : null;
  const router = useRouter();
  const toast = useToast();
  const { me } = useAuth();

  const [load, setLoad] = useState<Load>(mode === "new" ? "ready" : "loading");
  const [detail, setDetail] = useState<StocktakeDetail | null>(null);
  const [countDate, setCountDate] = useState(() => todayInVietnam());
  const [note, setNote] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [rows, setRows] = useState<FormRow[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);
  const [batchLoad, setBatchLoad] = useState<"idle" | "loading" | "error">("idle");
  const [attempt, setAttempt] = useState<Attempt>(null);
  const [serverRow, setServerRow] = useState<{ row: number; message: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloading, setReloading] = useState(false);
  /** Mã phiếu sau lần Lưu nháp đầu tiên ở /new/: từ đó form chạy như trang sửa. */
  const [savedCode, setSavedCode] = useState<string | null>(null);

  const recId = useRef<number | null>(id);
  const updatedAt = useRef<string>("");
  const savedHeader = useRef<{ date: string; note: string } | null>(null);
  const seq = useRef(0);
  const batchSeq = useRef(0);

  // ---- tải phiếu khi sửa
  const applyDetail = useCallback((d: StocktakeDetail) => {
    setDetail(d);
    setCountDate(d.count_date);
    setNote(d.note);
    setRows(rowsOfDetail(d));
    recId.current = d.id;
    updatedAt.current = d.updated_at;
    savedHeader.current = { date: d.count_date, note: d.note };
  }, []);

  const loadDetail = useCallback(async () => {
    if (id === null) return;
    const mine = ++seq.current;
    setLoad("loading");
    try {
      const d = await fetchStocktake(id);
      if (mine !== seq.current) return;
      applyDetail(d);
      setLoad("ready");
    } catch (err) {
      if (mine !== seq.current) return;
      if (err instanceof ApiError && err.status === 404) setLoad("notfound");
      else if (err instanceof ApiError && err.status === 403) setLoad("forbidden");
      else setLoad("error");
    }
  }, [id, applyDetail]);

  useEffect(() => {
    if (mode === "edit") void loadDetail();
    return () => {
      seq.current += 1;
    };
  }, [mode, loadDetail]);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchWarehouses(ctrl.signal)
      .then(setWarehouses)
      .catch(() => setNotice("Chưa tải được danh sách kho. Tải lại trang để chọn kho."));
    return () => ctrl.abort();
  }, []);

  // ---- nạp lô theo kho
  const loadBatches = useCallback((warehouseId: string) => {
    const mine = ++batchSeq.current;
    if (!warehouseId) {
      setBatchLoad("idle");
      return;
    }
    setBatchLoad("loading");
    fetchStockBatches(Number(warehouseId))
      .then((list) => {
        if (mine !== batchSeq.current) return;
        setRows((cur) => mergeLoaded(cur, list));
        setBatchLoad("idle");
      })
      .catch(() => {
        if (mine !== batchSeq.current) return;
        setBatchLoad("error");
      });
  }, []);

  const onWarehouse = (value: string) => {
    setWarehouse(value);
    loadBatches(value);
  };

  const patchRow = (index: number, change: Partial<FormRow>) => {
    setServerRow((cur) => (cur && cur.row === index ? null : cur));
    setRows((cur) => cur.map((r, i) => (i === index ? { ...r, ...change } : r)));
  };
  const dropRow = (index: number) => {
    setServerRow(null);
    setRows((cur) => cur.filter((_, i) => i !== index));
  };

  // ---- kiểm tra
  const check = useMemo(() => checkRows(rows, attempt === "send"), [rows, attempt]);
  const sum = useMemo(() => summarize(rows), [rows]);
  const dateMissing = attempt !== null && !countDate;
  /** Lỗi hiện ra: lỗi gõ sai (số âm, chữ, trùng lô) hiện ngay; lỗi "thiếu" chỉ hiện sau khi bấm Lưu nháp/Gửi duyệt. */
  const visible = (i: number) => {
    const e = check.errors[i];
    if (!e) return {};
    if (attempt !== null) return e;
    const c = parseCount(rows[i].counted);
    return c.kind === "error" || e.counted ? { counted: e.counted } : {};
  };

  // ---- gửi
  /** Tồn trên phiếu là bản BE vừa chụp: cập nhật cho các dòng đã lưu, giữ nguyên dòng còn trống (kể cả lý do đã gõ). */
  const refreshSnapshots = (res: StocktakeDetail) => {
    const snap = new Map(res.lines.map((l) => [l.batch, toMilli(l.system_qty) ?? 0]));
    setRows((cur) => cur.map((r) => (snap.has(r.batch) ? { ...r, systemMilli: snap.get(r.batch) as number } : r)));
  };

  const persist = async (): Promise<StocktakeDetail> => {
    setServerRow(null);
    const lines = toLineInputs(rows);
    const sent = rows.map((r, i) => (parseCount(r.counted).kind === "ok" ? i : -1)).filter((i) => i >= 0);
    const header = { date: countDate, note: note.trim() };
    let saved: StocktakeDetail;
    try {
      if (recId.current === null) {
        const created = await createStocktake({ count_date: header.date, note: header.note, lines });
        // Gán ngay khi phản hồi về (trước khi useSubmit nhả nút): bấm lưu lần nữa sẽ sửa phiếu này, không tạo phiếu thứ hai.
        recId.current = created.id;
        updatedAt.current = created.updated_at;
        savedHeader.current = { date: created.count_date, note: created.note };
        return created;
      }
      // Dòng đi trước, kèm mốc phiên bản lúc mở form (hoặc lần lưu/tải lại gần nhất). 409 thì dừng hẳn, chưa ghi gì.
      saved = await replaceStocktakeLines(recId.current, updatedAt.current, lines);
    } catch (err) {
      const le = lineErrorOf(err);
      if (le && sent[le.index] !== undefined) setServerRow({ row: sent[le.index], message: le.message });
      throw normalizeError(err);
    }
    // Dòng đã lưu: ghi nhận phiên bản mới để lần lưu kế tiếp không tự va vào thay đổi của chính mình.
    updatedAt.current = saved.updated_at;
    const before = savedHeader.current;
    if (!before || (before.date === header.date && before.note === header.note)) return saved;
    try {
      const patched = await updateStocktakeHeader(recId.current, { count_date: header.date, note: header.note });
      updatedAt.current = patched.updated_at;
      savedHeader.current = { date: patched.count_date, note: patched.note };
      return patched;
    } catch (err) {
      refreshSnapshots(saved);
      throw new ApiError("Đã lưu số đếm nhưng chưa lưu được ngày hoặc ghi chú. Bấm lưu lại để thử lần nữa.", err instanceof ApiError ? err.status : 0);
    }
  };

  const afterSave = (res: StocktakeDetail, kind: "draft" | "send") => {
    if (kind === "send") {
      toast.success("Đã gửi duyệt. Phiếu chờ người khác duyệt.");
      router.push(detailHref(res.id));
      return;
    }
    recId.current = res.id;
    updatedAt.current = res.updated_at;
    savedHeader.current = { date: res.count_date, note: res.note };
    setDetail(res);
    refreshSnapshots(res);
    // Dòng chưa có số không lên BE (BE chỉ lưu dòng đã đếm) nhưng vẫn nằm trên màn, kể cả lý do đã gõ: nói rõ để người dùng biết.
    const pending = rows.filter((r) => parseCount(r.counted).kind !== "ok").length;
    toast.success(pending > 0 ? `Đã lưu nháp. ${pending} lô chưa có số nên chưa được lưu.` : "Đã lưu nháp.");
    if (mode === "new" && savedCode === null) {
      // Ở lại trang để giữ nguyên những gì đang gõ; chỉ đổi địa chỉ sang trang sửa (mở lại hoặc tải lại trang sẽ vào đúng phiếu này).
      window.history.replaceState(null, "", editHref(res.id));
      setSavedCode(res.code);
    }
  };

  const draft = useSubmit(persist, { onSuccess: (res) => afterSave(res, "draft") });
  const send = useSubmit(persist, { onSuccess: (res) => afterSave(res, "send") });
  const busy = draft.submitting || send.submitting;
  const conflict = draft.conflict || send.conflict;
  const error = send.error || draft.error;

  const start = (kind: "draft" | "send") => {
    if (busy) return;
    setAttempt(kind);
    setNotice(null);
    draft.reset();
    send.reset();
    const result = checkRows(rows, kind === "send");
    if (!countDate) return;
    if (rows.length === 0) {
      setNotice("Chọn kho để nạp các lô cần đếm.");
      return;
    }
    if (result.countedRows === 0) {
      setNotice("Nhập số đếm của ít nhất một lô.");
      return;
    }
    if (result.hasError) {
      setNotice("Có dòng chưa hợp lệ. Sửa các dòng báo đỏ rồi bấm lại.");
      return;
    }
    void (kind === "send" ? send : draft).submit();
  };

  /** Tải lại sau 409: nạp nguyên bản mới của máy chủ (dòng, ngày, ghi chú, mốc phiên bản) và bỏ bản đang gõ. */
  const reloadAfterConflict = async () => {
    if (recId.current === null) return;
    setReloading(true);
    try {
      const d = await fetchStocktake(recId.current);
      applyDetail(d);
      setWarehouse("");
      setServerRow(null);
      setAttempt(null);
      setNotice(null);
      draft.reset();
      send.reset();
    } catch {
      setNotice("Chưa tải lại được phiếu. Kiểm tra mạng rồi bấm Tải lại.");
    } finally {
      setReloading(false);
    }
  };

  // ---- màn phụ
  const homeHref = me ? homePath(me) : "/overview/";
  if (mode === "edit" && id === null) return <NotFoundScreen homeHref={homeHref} />;
  if (mode === "new" && me && !me.permissions.includes(PERM.addStockReconciliation)) return <NoPermission homeHref={homeHref} />;
  if (load === "loading")
    return (
      <SkeletonScreen label="Đang tải phiếu kiểm kê…">
        <div className={s.skelRow} />
        <div className={s.skelRow} />
        <div className={s.skelRow} />
      </SkeletonScreen>
    );
  if (load === "notfound") return <NotFoundScreen homeHref={homeHref} />;
  if (load === "forbidden") return <NoPermission homeHref={homeHref} />;
  if (load === "error") return <ErrorScreen homeHref={homeHref} onRetry={() => void loadDetail()} />;
  if (mode === "edit" && detail && (detail.status !== "DRAFT" || !hasAction(detail, "edit_lines"))) {
    return (
      <div className="page-state" data-stocktake-locked>
        <span className="state-ic">
          <Icon name="lock" />
        </span>
        <h2 className="state-title">Phiếu {detail.code} không sửa được</h2>
        <p>{detail.status === "APPROVED" ? "Phiếu đã duyệt, số liệu đã vào sổ kho." : "Bạn không có quyền sửa số đếm của phiếu này."}</p>
        <div className="page-state-actions">
          <Link href={detailHref(detail.id)} className="btn">
            Xem phiếu
          </Link>
        </div>
      </div>
    );
  }

  const editing = mode === "edit" || savedCode !== null;
  const title = editing ? `Sửa số đếm ${detail?.code ?? savedCode ?? ""}`.trim() : "Lập phiếu kiểm kê";

  return (
    <FormPage
      title={title}
      back={BACK}
      alert={
        <>
          {conflict && (
            <>
              <ConflictBanner noun="phiếu" updatedByName={conflict.updatedByName} updatedAt={conflict.updatedAt} onReload={() => void reloadAfterConflict()} reloading={reloading} />
              <p className={s.conflictHint} data-conflict-hint>
                Thay đổi chưa lưu của bạn sẽ bị bỏ khi tải lại.
              </p>
            </>
          )}
          {error && <FormAlert>{error}</FormAlert>}
          {!error && notice && <FormAlert>{notice}</FormAlert>}
        </>
      }
      onSubmit={() => start("send")}
      primaryText="Gửi duyệt"
      submitting={busy}
      failed={send.failed && !conflict}
      secondary={{ label: "Lưu nháp", onClick: () => start("draft") }}
    >
      <div className={s.head}>
        <Field label="Ngày kiểm kê" required type="date" value={countDate} onChange={setCountDate} name="count_date" error={dateMissing ? "Chọn ngày kiểm kê." : null} />
        <Field
          label="Kho cần đếm"
          as="select"
          value={warehouse}
          onChange={onWarehouse}
          name="warehouse"
          options={[{ value: "", label: "Chọn kho để nạp lô" }, ...warehouses.map((w) => ({ value: String(w.id), label: w.name }))]}
        />
        <Field label="Ghi chú" value={note} onChange={setNote} name="note" maxLength={500} />
      </div>

      <section className={s.section} aria-label="Các lô cần đếm">
        <div className={s.sectionHead}>
          <h3 className={s.sectionTitle}>Các lô cần đếm</h3>
          <span className={s.sectionCount} data-row-count>
            {check.countedRows} / {rows.length} lô đã nhập số
          </span>
        </div>
        {batchLoad === "loading" && (
          <p className={s.loadNote} role="status">
            <Icon name="progress_activity" className="spin" />
            <span>Đang nạp các lô còn tồn…</span>
          </p>
        )}
        {batchLoad === "error" && (
          <p className={s.loadErr} role="alert">
            <Icon name="sync_problem" />
            <span>Chưa nạp được các lô của kho này.</span>
            <button type="button" className="btn" onClick={() => loadBatches(warehouse)}>
              Thử lại
            </button>
          </p>
        )}
        {rows.length === 0 && batchLoad !== "loading" ? (
          <div className={s.empty} data-stocktake-empty>
            <p className={s.emptyTitle}>{warehouse ? "Kho này chưa có lô nào còn tồn" : "Chưa có lô nào để đếm"}</p>
            <p className={s.emptyHint}>{warehouse ? "Chọn kho khác để nạp thêm lô." : "Chọn kho ở trên để nạp các lô còn tồn."}</p>
          </div>
        ) : (
          <>
            <div className={s.rowHead} aria-hidden="true">
              <span>Lô</span>
              <span>Mặt hàng</span>
              <span className={s.r}>Tồn hệ thống (kg)</span>
              <span className={s.r}>Đếm được (kg)</span>
              <span className={s.r}>Chênh lệch (kg)</span>
              <span>Lý do</span>
              <span />
            </div>
            <ul className={s.rows} aria-label="Danh sách lô cần đếm">
              {rows.map((row, i) => {
                const err = visible(i);
                const srv = serverRow && serverRow.row === i ? serverRow.message : null;
                const d = previewDiff(row);
                const tone = diffTone(d);
                const needReason = d !== null && d > 0;
                return (
                  <li key={row.batch} className={s.row} data-line-row data-batch={row.batch} data-invalid={Boolean(err.counted || err.reason || srv) || undefined}>
                    <div className={s.rowTop}>
                      <div className={s.rowTitle}>
                        <span className={s.batchCode}>{row.batchCode}</span>
                        <span className={s.itemName}>{row.itemName}</span>
                      </div>
                      <button type="button" className={s.drop} onClick={() => dropRow(i)} aria-label={`Bỏ lô ${row.batchCode} khỏi phiếu`}>
                        <Icon name="close" />
                      </button>
                    </div>
                    <div className={s.cell}>
                      <span className={s.cellLabel}>Tồn hệ thống (kg)</span>
                      <span className={`${s.value} ${s.cellEnd}`} data-system>
                        {qty(row.systemMilli)}
                      </span>
                    </div>
                    <div className={`${s.cell} ${s.cellEnd}`}>
                      <label className={s.cellLabel} htmlFor={`counted-${row.batch}`}>
                        Đếm được (kg)
                      </label>
                      <div className={s.unitBox}>
                        <input
                          id={`counted-${row.batch}`}
                          className={`${s.control} ${s.num}`}
                          inputMode="decimal"
                          autoComplete="off"
                          value={row.counted}
                          onChange={(e) => patchRow(i, { counted: e.target.value })}
                          aria-label={`Đếm được của lô ${row.batchCode}`}
                          aria-invalid={Boolean(err.counted) || undefined}
                          aria-describedby={err.counted ? `counted-err-${row.batch}` : undefined}
                          data-counted
                        />
                        <span className={s.unit}>kg</span>
                      </div>
                      {err.counted && (
                        <p className={s.err} id={`counted-err-${row.batch}`} role="alert">
                          <Icon name="error" />
                          <span>{err.counted}</span>
                        </p>
                      )}
                    </div>
                    <div className={s.cell}>
                      <span className={s.cellLabel}>Chênh lệch (kg)</span>
                      <span className={`${s.value} ${tone === "crit" ? s.diffShort : tone === "warn" ? s.diffOver : ""} ${s.cellEnd}`} data-diff>
                        {d === null ? "—" : signedQty(d)}
                      </span>
                    </div>
                    <div className={`${s.cell} ${s.cellWide}`}>
                      <label className={s.cellLabel} htmlFor={`reason-${row.batch}`}>
                        {needReason ? "Lý do (bắt buộc khi đếm nhiều hơn sổ)" : "Lý do"}
                      </label>
                      <input
                        id={`reason-${row.batch}`}
                        className={s.control}
                        autoComplete="off"
                        maxLength={MAX_REASON}
                        value={row.reason}
                        onChange={(e) => patchRow(i, { reason: e.target.value })}
                        aria-label={`Lý do của lô ${row.batchCode}`}
                        aria-invalid={Boolean(err.reason) || undefined}
                        aria-describedby={err.reason ? `reason-err-${row.batch}` : undefined}
                        data-reason
                      />
                      {err.reason && (
                        <p className={s.err} id={`reason-err-${row.batch}`} role="alert">
                          <Icon name="error" />
                          <span>{err.reason}</span>
                        </p>
                      )}
                    </div>
                    {srv && (
                      <p className={`${s.err} ${s.cellWide}`} role="alert" data-line-error>
                        <Icon name="error" />
                        <span>{srv}</span>
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>

      <SummaryBlock
        label="Tóm tắt chênh lệch"
        rows={[
          { label: "Lô đã nhập số", value: `${check.countedRows} / ${rows.length}`, num: true },
          { label: "Lô hụt", value: sum.short > 0 ? `${sum.short} lô · −${qty(sum.shortMilli)} kg` : "0 lô", num: true },
          { label: "Lô dư", value: sum.over > 0 ? `${sum.over} lô · +${qty(sum.overMilli)} kg` : "0 lô", num: true },
          { label: "Chênh lệch ròng", value: `${signedQty(sum.netMilli)} kg`, num: true, strong: true },
        ]}
      />
    </FormPage>
  );
}
