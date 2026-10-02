"use client";

// In tem giao 100x150 mm. CHỈ giao diện: dữ liệu tem lấy từ GET /api/delivery/notes/{id}/label/ (BE đã che SĐT: T1).
// Màu: giấy tem luôn đen trên trắng nhờ color-scheme: light + màu hệ thống (label.module.css), không mã màu viết tay.
import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import QRCode from "qrcode";
import { dateOnly } from "@/shared/lib/format";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { fetchDeliveryLabel } from "@/features/deliveries/api";
import type { LabelData } from "@/features/deliveries/types";
import { Icon } from "@/shared/ui/Icon";
import s from "@/features/deliveries/label.module.css";

function LabelPrintContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { status, me } = useAuth();

  const noteParam = searchParams.get("note");
  const printNoParam = searchParams.get("print_no");

  const [labelData, setLabelData] = useState<LabelData | null>(null);
  const [qrSvg, setQrSvg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "anon") {
      // F14: giữ nguyên query (?note=…&print_no=…) để đăng nhập xong quay lại đúng tem đang in.
      const qs = searchParams.toString();
      router.replace(`/login/?next=${encodeURIComponent("/print/label/" + (qs ? "?" + qs : ""))}`);
      return;
    }

    if (status === "ready" && me) {
      if (!me.permissions.includes("delivery.print_label")) {
        setError("Bạn không có quyền in tem giao hàng. Nhờ Chủ cấp quyền hoặc nhờ người có quyền in giúp.");
        setLoading(false);
        return;
      }

      const noteId = noteParam ? parseInt(noteParam, 10) : NaN;
      if (isNaN(noteId)) {
        setError("Đường dẫn thiếu mã phiếu giao. Mở lại tem từ trang chi tiết phiếu giao.");
        setLoading(false);
        return;
      }

      const printNo = printNoParam ? parseInt(printNoParam, 10) : undefined;

      fetchDeliveryLabel(noteId, printNo)
        .then(async (data) => {
          setLabelData(data);
          try {
            const svg = await QRCode.toString(data.barcode_value, {
              type: "svg",
              margin: 1,
              width: 140,
              errorCorrectionLevel: "M",
            });
            setQrSvg(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`);
          } catch {
            setError("Chưa tạo được mã QR cho tem. Đóng cửa sổ rồi bấm In tem lại.");
          }
          setLoading(false);
        })
        .catch((err) => {
          const msg = err instanceof Error ? err.message : "Chưa tải được dữ liệu tem.";
          setError(msg);
          setLoading(false);
        });
    }
  }, [status, me, noteParam, printNoParam, router, searchParams]);

  useEffect(() => {
    if (labelData && qrSvg && !error) {
      const timer = setTimeout(() => {
        window.print();
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [labelData, qrSvg, error]);

  if (loading || status === "loading") {
    return (
      <div className={s.labelState} role="status" aria-live="polite">
        <p className="muted" style={{ textAlign: "center" }}>
          Đang nạp dữ liệu tem…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={s.labelState}>
        <div className="alert-box err" role="alert">
          <Icon name="error" />
          <span>
            <b>Không in được tem.</b> {error}
          </span>
        </div>
        <button type="button" className="btn" onClick={() => window.close()}>
          Đóng cửa sổ
        </button>
      </div>
    );
  }

  if (!labelData || !qrSvg) {
    return null;
  }

  const reprintTitle =
    labelData.reprint_reason === "ADDRESS_CHANGED" ? "IN LẠI – ĐỔI ĐỊA CHỈ" : `IN LẠI – LẦN ${labelData.print_no}`;

  return (
    <>
      <style>{`
        @page { size: 100mm 150mm; margin: 0; }
        @media print {
          body { margin: 0 !important; padding: 0 !important; color-scheme: light; background: Canvas !important; }
        }
      `}</style>

      <div className={s.labelBar}>
        <span>Khổ in chuẩn: 100 × 150 mm</span>
        <div className={s.labelBarBtns}>
          <button type="button" className="btn primary" onClick={() => window.print()}>
            In tem
          </button>
          <button type="button" className="btn" onClick={() => window.close()}>
            Đóng
          </button>
        </div>
      </div>

      <div className={s.labelSheet}>
        <div className={s.labelHead}>
          <div className={s.labelHeadRow}>
            <div>
              <div className={s.labelBrand}>CÁ VỀ</div>
              <div className={s.labelSub}>Vựa cá tươi sống B2C</div>
            </div>
            {labelData.is_reprint && <div className={s.labelReprint}>{reprintTitle}</div>}
          </div>
          <div className={s.labelRef}>
            <span>
              Mã đơn: <strong>{labelData.order_code}</strong>
            </span>
            <span>
              Lượt in: <strong>#{labelData.print_no}</strong>
            </span>
          </div>
        </div>

        <div className={s.labelQr}>
          {/* F14: QR là ảnh data-URI (không chèn HTML thô vào DOM). */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={qrSvg} alt={`Mã QR ${labelData.barcode_value}`} className={s.labelQrImg} />
          <div className={s.labelBarcode}>{labelData.barcode_value}</div>
          <div className={s.labelNote}>Mã phiếu: {labelData.note_code}</div>
        </div>

        <div className={s.labelRecipient}>
          <div className={s.labelKey}>Người nhận hàng</div>
          <div className={s.labelRecipientRow}>
            <div className={s.labelName}>{labelData.recipient_name}</div>
            {/* T1: chỉ hiện SĐT đã che bớt do BE trả (vd 09xx xxx 123), không bao giờ ghép lại số đầy đủ. */}
            <div className={s.labelPhone}>{labelData.recipient_phone_masked}</div>
          </div>
          <div className={s.labelAddress}>{labelData.address}</div>
        </div>

        <div className={s.labelGoods}>
          <div>
            <div className={s.labelGoodsKey}>Số kiện</div>
            <div className={s.labelGoodsVal}>{labelData.packages}</div>
          </div>
          <div>
            <div className={s.labelGoodsKey}>Tổng số kg</div>
            <div className={s.labelGoodsVal}>{labelData.total_kg} kg</div>
          </div>
          <div>
            <div className={s.labelGoodsKey}>HSD sớm nhất</div>
            <div className={s.labelGoodsValSm}>{dateOnly(labelData.earliest_expiry)}</div>
          </div>
        </div>

        <div className={s.labelPaid}>
          <div className={s.labelPaidText}>{labelData.paid_text}</div>
          <div className={s.labelPaidNote}>(Người giao hàng vui lòng không thu thêm tiền của khách)</div>
        </div>
      </div>
    </>
  );
}

export default function LabelPrintPage() {
  return (
    <Suspense
      fallback={
        <div className={s.labelState} role="status">
          <p className="muted" style={{ textAlign: "center" }}>
            Đang nạp trang in…
          </p>
        </div>
      }
    >
      <LabelPrintContent />
    </Suspense>
  );
}
