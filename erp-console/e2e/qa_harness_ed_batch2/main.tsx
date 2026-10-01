// Khung thử QA Lô 2 FE: chạy mẫu với apiFetch THẬT (NEXT_PUBLIC_USE_MOCK=0), Playwright chặn mạng bằng page.route.
// Chỉ dữ liệu giả. Chế độ chọn bằng ?m= : form · modal · field · header · ai
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "@/shared/ui/tokens.css";
import "@/shared/ui/globals.css";
import { apiFetch } from "@/shared/lib/http";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { useSubmit, primaryLabel, isConflictError, conflictOf, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";

const params = new URLSearchParams(location.search);
const MODE = params.get("m") || "form";
const sent: string[] = ((window as any).__sent = []);

async function save(qty: string) {
  sent.push(qty);
  await apiFetch("/api/qa/save/", { method: "POST", body: { quantity: qty } });
}

function FormDemo() {
  const [qty, setQty] = useState("12,5");
  const [done, setDone] = useState(0);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const sub = useSubmit(async () => {
    try { await save(qty); } catch (e) { if (isConflictError(e)) setConflict(conflictOf(e)); throw e; }
  }, { onSuccess: () => setDone((n) => n + 1) });
  const fe = sub.fieldErrors.quantity;
  return (
    <FormPage
      title="Nhập thử"
      back={{ href: "/x/", label: "Danh sách" }}
      alert={conflict ? <ConflictBanner noun="phiếu" updatedByName={conflict.updatedByName} updatedAt={conflict.updatedAt} onReload={() => setConflict(null)} /> : sub.error ? <FormAlert>{sub.error}</FormAlert> : undefined}
      onSubmit={() => void sub.submit()}
      primaryText="Lưu phiếu"
      submitting={sub.submitting}
      failed={sub.failed}
      secondary={{ label: "Huỷ", onClick: () => undefined }}
    >
      <Field label="Số lượng" required unit="kg" type="number" value={qty} onChange={setQty} name="qty" error={fe ?? (qty.trim() === "" ? "Nhập số kg lớn hơn 0." : null)} />
      <p data-done={done} role="status">{done ? "Đã lưu." : ""}</p>
    </FormPage>
  );
}

function ModalDemo() {
  const [open, setOpen] = useState(false);
  const [qty, setQty] = useState("12");
  const sub = useSubmit(async () => { await save(qty); }, { onSuccess: () => setOpen(false) });
  return (
    <DetailPage id="m" header={<DetailHeader back={{ href: "/x/", label: "Danh sách" }} title="PR-1" mono primary={<button id="open" className="btn primary" onClick={() => { sub.reset(); setOpen(true); }}>Sửa phiếu</button>} />}>
      <p>nền</p>
      {open && (
        <Modal title="Sửa số lượng" onClose={() => setOpen(false)} busy={sub.submitting}
          footer={<><button className="btn" disabled={sub.submitting} onClick={() => setOpen(false)}>Huỷ</button>
            <button className="btn primary" disabled={sub.submitting} onClick={() => void sub.submit()}>{sub.submitting ? "Đang gửi…" : primaryLabel("Lưu", sub.failed)}</button></>}>
          {sub.error && <FormAlert>{sub.error}</FormAlert>}
          <Field label="Số lượng" required unit="kg" type="number" value={qty} onChange={setQty} autoFocus />
        </Modal>
      )}
    </DetailPage>
  );
}

function FieldDemo() {
  return (
    <div style={{ maxWidth: 520, padding: 16 }} id="fields">
      <Field label="Số kg" required unit="kg" type="number" value="0" onChange={() => undefined} error="Nhập số kg lớn hơn 0." />
      <Field label="Giá" unit="đ" type="number" value="5000" onChange={() => undefined} />
      <Field label="Ghi chú" as="textarea" value="" onChange={() => undefined} />
      <Field label="Kho" as="select" required value="a" onChange={() => undefined} options={[{ value: "a", label: "Kho lạnh" }, { value: "b", label: "Kho khô" }]} />
    </div>
  );
}

function HeaderDemo() {
  const [chosen, setChosen] = useState("");
  const [qty, setQty] = useState("5");
  return (
    <DetailPage
      id="h"
      header={<DetailHeader back={{ href: "/orders/", label: "Đơn & tiền" }} title="SO261002-A1B2C3" mono status={<span className="stat-chip crit">Đã huỷ</span>}
        more={[{ key: "x", label: "Xoá nháp", danger: true, onSelect: () => setChosen("xoa") }, { key: "y", label: "Chốt lô", blockedReason: "Lô còn 18,5 kg.", onSelect: () => setChosen("chot") }]} />}
      timeline={<Timeline entries={[]} />}
    >
      <StatusPath steps={[{ key: "a", label: "Giữ chỗ" }, { key: "b", label: "Đã thanh toán" }, { key: "c", label: "Hoàn tất" }]} current="b" badEnd={{ label: "Đã huỷ", after: "a" }} next={null} done={["Giữ chỗ"]} />
      <InfoGrid title="Thông tin">
        <InfoField label="Số lượng" kind="editable" value={qty} display={`${qty} kg`} type="number" unit="kg" required onSave={async (n) => { await save(n); setQty(n); }} />
        <InfoField label="Giá vốn" kind="locked" value="Chỉ Chủ xem" reason="Giá vốn chỉ Chủ được xem" />
        <InfoField label="Ghi chú" value="" />
      </InfoGrid>
      <output id="chosen">{chosen}</output>
    </DetailPage>
  );
}

function HeaderEmpty() {
  return (
    <DetailPage id="he" header={<DetailHeader back={{ href: "/orders/", label: "Đơn & tiền" }} title="Nhóm quyền kho" />}>
      <p>Đối tượng không có vòng đời: không StatusPath, không '…', không nút chính.</p>
    </DetailPage>
  );
}

function App() {
  return (
    <div className="app"><aside className="rail-left" aria-hidden="true" /><div className="center"><main className="content" id="main">
      {MODE === "form" ? <FormDemo /> : MODE === "modal" ? <ModalDemo /> : MODE === "field" ? <FieldDemo /> : MODE === "header" ? <HeaderDemo /> : MODE === "header-empty" ? <HeaderEmpty /> : (
        <DetailPage id="ai" header={<DetailHeader back={{ href: "/x/", label: "Danh sách" }} title="PR-260928-01" mono />}
          aiSlot={<AiDocBlockGate targetModel="purchasing.purchasereceipt" targetId="PR-260928-01" onApplied={() => ((window as any).__applied = ((window as any).__applied || 0) + 1)} />}>
          <p>nền</p>
        </DetailPage>
      )}
    </main></div></div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
