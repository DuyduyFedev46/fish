"use client";

// CS-17 — /deliveries/lookup/: quét hoặc gõ mã trên tem để mở đúng phiếu soạn.
// Máy quét USB gõ như bàn phím rồi nhấn Enter vào ô mã; có camera (BarcodeDetector) thì thêm nút quét; ô gõ tay luôn có.
// Mã được kiểm regex GH-… Ở MÁY KHÁCH trước khi gọi API, để số điện thoại gõ nhầm không lên URL và không vào access log (QA L1).
// Tem cũ (BR-GH-16) → cảnh báo vàng; đơn đã huỷ (BR-GH-07) → cảnh báo đỏ; còn hiệu lực → mở phiếu luôn. Mã tem không chứa dữ liệu cá nhân,
// vẫn không lưu vào localStorage, URL hay console.
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { ApiError } from "@/shared/lib/http";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { Section } from "@/shared/ui/detail/Section";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { lookupDeliveryTag } from "../api";
import { TAG_MESSAGES, checkTagCode, tagWarning } from "../tagCode";
import type { TagLookup } from "../types";
import { TagCameraScanner, cameraScanSupported } from "./TagCameraScanner";
import s from "../deliveries.module.css";

const BACK = { href: "/deliveries/", label: "Giao hàng" };
const detailPath = (noteId: number) => `/deliveries/detail/?id=${noteId}`;

export function TagLookupScreen() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const inFlight = useRef(false);
  const [raw, setRaw] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<TagLookup | null>(null);
  const [cameraOk, setCameraOk] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [cameraFailed, setCameraFailed] = useState(false);

  useEffect(() => setCameraOk(cameraScanSupported()), []);

  // Sẵn sàng cho lần quét kế tiếp: ô mã được chọn hết để mã mới ghi đè.
  const refocus = () =>
    requestAnimationFrame(() => {
      const input = formRef.current?.querySelector("input");
      input?.focus();
      input?.select();
    });

  const lookup = async (value: string) => {
    if (inFlight.current) return;
    setResult(null);
    setApiError(null);
    const check = checkTagCode(value);
    if (!check.ok) {
      setFieldError(check.message);
      refocus();
      return;
    }
    setFieldError(null);
    inFlight.current = true;
    setBusy(true);
    try {
      const res = await lookupDeliveryTag(check.code);
      if (!tagWarning(res)) {
        router.push(detailPath(res.note_id));
        return;
      }
      setResult(res);
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      setApiError(
        status === 404 ? TAG_MESSAGES.notFound : status === 400 ? TAG_MESSAGES.invalid : status === 403 ? TAG_MESSAGES.forbidden : TAG_MESSAGES.failed,
      );
      refocus();
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  const warning = result ? tagWarning(result) : null;

  return (
    <DetailPage
      id="delivery-lookup"
      header={<DetailHeader back={BACK} title="Quét mã tem" />}
    >
      <Section title="Mã trên tem">
        <form
          ref={formRef}
          className={s.lookupForm}
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            void lookup(raw);
          }}
          aria-busy={busy || undefined}
        >
          {apiError && <FormAlert>{apiError}</FormAlert>}
          <div className={s.lookupRow}>
            <Field label="Mã tem" required value={raw} onChange={(v) => { setRaw(v); setFieldError(null); }} error={fieldError} disabled={busy} autoFocus name="tag-code" placeholder="GH-HD-0001-AB12C.1" maxLength={60} />
            <button type="submit" className="btn primary" disabled={busy}>
              {busy ? <Icon name="progress_activity" className="spin" /> : <Icon name="search" />}
              <span>{busy ? "Đang tra…" : "Tra mã"}</span>
            </button>
            {cameraOk && (
              <button type="button" className="btn" onClick={() => { setCameraFailed(false); setCameraOn((on) => !on); }} aria-pressed={cameraOn}>
                <Icon name="photo_camera" />
                <span>{cameraOn ? "Tắt camera" : "Quét bằng camera"}</span>
              </button>
            )}
          </div>
        </form>

        {cameraOn && !cameraFailed && (
          <div className={s.camera}>
            <TagCameraScanner
              onCode={(code) => {
                setCameraOn(false);
                setRaw(code);
                void lookup(code);
              }}
              onFail={() => {
                setCameraOn(false);
                setCameraFailed(true);
              }}
            />
          </div>
        )}
        {cameraFailed && (
          <div className={s.camera}>
            <FormAlert kind="warn">{TAG_MESSAGES.camera}</FormAlert>
          </div>
        )}

        {result && warning && (
          <div className={s.lookupResult} data-testid="lookup-result">
            <FormAlert kind={warning.kind}>{warning.text}</FormAlert>
            <SummaryBlock
              label="Kết quả tra mã tem"
              rows={[
                { label: "Tem lần", value: result.print_no, num: true },
                { label: "Tem còn hiệu lực", value: result.valid_print_no ? `Lần ${result.valid_print_no}` : "Không còn" },
                { label: "Trạng thái phiếu", value: <Chip table={ENUMS.deliveryStatus} value={result.status} /> },
              ]}
            />
            <div className={s.lookupActions}>
              <button type="button" className="btn primary" onClick={() => router.push(detailPath(result.note_id))}>
                Mở phiếu
              </button>
            </div>
          </div>
        )}
      </Section>
    </DetailPage>
  );
}
