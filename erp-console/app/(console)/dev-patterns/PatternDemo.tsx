"use client";

// Mẫu trang chi tiết + popup + khối AI (chỉ mock). Dữ liệu bịa, không có dữ liệu cá nhân.
import Link from "next/link";
import { useRef, useState } from "react";
import { ApiError, apiFetch } from "@/shared/lib/http";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { GuidancePanel } from "@/features/guidance/components/GuidancePanel";
import { toTimelineEntries } from "@/features/guidance/detailAdapters";
import type { GuidanceTimelineEntry } from "@/features/guidance/types";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { LookupCard } from "@/shared/ui/detail/LookupCard";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { useSubmit, primaryLabel, isConflictError, conflictOf, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";

const STEPS = [
  { key: "DRAFT", label: "Nháp" },
  { key: "SUBMITTED", label: "Đã nhập kho" },
  { key: "INVOICED", label: "Đã có hoá đơn" },
];

// Dữ liệu dòng thời gian kiểu guidance, cố ý có `why.br`-style mã trong dữ liệu khác để chứng minh khối không vẽ mã BR.
const GUIDANCE_TIMELINE: GuidanceTimelineEntry[] = [
  { at: "2026-09-28T01:10:00Z", kind: "create", label: "Tạo phiếu nhập", doc: "", actor: { kind: "user", display: "Lộc" } },
  { at: "2026-09-28T03:20:00Z", kind: "submit", label: "Xác nhận nhập kho", doc: "", actor: { kind: "ai", display: "AI của Lộc", level: "C" } },
];

export default function PatternDemo() {
  const [modal, setModal] = useState(false);
  const [lookup, setLookup] = useState(false);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [reloaded, setReloaded] = useState(0);
  const [qty, setQty] = useState("12");
  const [note, setNote] = useState("");
  const [appliedCount, setAppliedCount] = useState(0);
  const attempts = useRef(0);

  const modalSub = useSubmit(
    async () => {
      attempts.current += 1;
      await new Promise((r) => setTimeout(r, 700));
      if (attempts.current === 1) throw new ApiError("Chưa lưu được vì mạng chập chờn.", 500);
    },
    { onSuccess: () => setModal(false) }
  );

  async function saveQty(next: string) {
    // Đi qua apiFetch (mock) để chứng minh thân 409 của BE tới được ConflictBanner (tên + giờ người sửa).
    await apiFetch("/api/dev-patterns/qty/", {
      method: "PATCH",
      body: { quantity: next },
      mock: () =>
        next.trim() === "409"
          ? { status: 409, body: { detail: "Phiếu vừa được người khác cập nhật, tải lại để xem.", code: "STALE_STATE", updated_at: "2026-09-28T03:30:00Z", updated_by_name: "Lộc" } }
          : next.trim() === "410"
            ? { status: 409, body: { detail: "Phiếu đang có người nhận xử lý, chờ họ xong.", code: "CLAIMED" } } // 409 KHÔNG phải xung đột sửa
            : { status: 200, body: {} },
    });
    setQty(next);
  }

  return (
    <DetailPage
      id="pattern-demo"
      header={
        <DetailHeader
          back={{ href: "/overview/", label: "Tổng quan" }}
          title="PR-260928-01"
          mono
          status={<span className="stat-chip good">Đã nhập kho</span>}
          primary={
            <button type="button" className="btn primary" onClick={() => { modalSub.reset(); setModal(true); }}>
              Sửa phiếu
            </button>
          }
          more={[
            { key: "print", label: "In phiếu", onSelect: () => undefined },
            { key: "cancel", label: "Huỷ phiếu", blockedReason: "Phiếu đã có hoá đơn", danger: true },
          ]}
        />
      }
      banner={
        conflict ? (
          <ConflictBanner
            noun="phiếu"
            updatedByName={conflict.updatedByName}
            updatedAt={conflict.updatedAt}
            onReload={() => {
              setConflict(null);
              setReloaded((n) => n + 1);
            }}
          />
        ) : null
      }
      aiSlot={<AiDocBlockGate targetModel="purchasing.purchasereceipt" targetId="PR-260928-01" onApplied={() => setAppliedCount((n) => n + 1)} />}
      timeline={<Timeline entries={toTimelineEntries(GUIDANCE_TIMELINE)} />}
    >
      <StatusPath steps={STEPS} current="SUBMITTED" next="Ghi hoá đơn nhà cung cấp" done={["Tạo phiếu", "Nhập kho"]} />
      <InfoGrid title="Thông tin">
        <InfoField label="Nhà cung cấp" value="Vựa Hải Sản Cảng Cá" />
        <InfoField
          label="Số lượng"
          kind="editable"
          value={qty}
          display={`${qty} kg`}
          type="number"
          unit="kg"
          required
          onSave={async (next) => {
            try {
              await saveQty(next);
            } catch (err) {
              if (isConflictError(err)) setConflict(conflictOf(err));
              throw err;
            }
          }}
        />
        <InfoField label="Giá vốn" kind="locked" value="Chỉ Chủ xem" reason="Giá vốn chỉ Chủ được xem" />
        <InfoField label="Lô" kind="link" value="CA01-260928-AB12C" onOpen={() => setLookup(true)} mono />
      </InfoGrid>
      <p data-reload-count={reloaded} data-applied-count={appliedCount} className="muted">
        Đã tải lại {reloaded} lần · đề xuất AI đã áp dụng {appliedCount} lần.
      </p>
      <Link href="/dev-patterns/form/" className="btn">
        Mở mẫu form
      </Link>
      <GuidancePanel docType="order" docId={102} />

      {modal && (
        <Modal
          title="Sửa số lượng"
          onClose={() => setModal(false)}
          busy={modalSub.submitting}
          footer={
            <>
              <button type="button" className="btn" onClick={() => setModal(false)} disabled={modalSub.submitting}>
                Huỷ
              </button>
              <button type="button" className="btn primary" onClick={() => void modalSub.submit()} disabled={modalSub.submitting}>
                {modalSub.submitting ? "Đang gửi…" : primaryLabel("Lưu", modalSub.failed)}
              </button>
            </>
          }
        >
          {modalSub.error && <FormAlert>{modalSub.error}</FormAlert>}
          <Field label="Số lượng" required unit="kg" type="number" value={qty} onChange={setQty} autoFocus />
          <Field label="Ghi chú" as="textarea" value={note} onChange={setNote} />
        </Modal>
      )}
      {lookup && <LookupCard kind="batch" id={1} onClose={() => setLookup(false)} />}
    </DetailPage>
  );
}
