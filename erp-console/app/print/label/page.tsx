"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import QRCode from "qrcode";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { fetchDeliveryLabel } from "@/features/deliveries/api";
import type { LabelData } from "@/features/deliveries/types";

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
      router.replace("/login/?next=/print/label/");
      return;
    }

    if (status === "ready" && me) {
      if (!me.permissions.includes("delivery.print_label")) {
        setError("Bạn không có quyền in tem nhãn giao hàng (delivery.print_label).");
        setLoading(false);
        return;
      }

      const noteId = noteParam ? parseInt(noteParam, 10) : NaN;
      if (isNaN(noteId)) {
        setError("Thiếu mã phiếu giao hợp lệ trong đường dẫn (?note=...).");
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
            setQrSvg(svg);
          } catch {
            setError("Không thể tạo mã QR cho tem.");
          }
          setLoading(false);
        })
        .catch((err) => {
          const msg = err instanceof Error ? err.message : "Không thể tải dữ liệu tem.";
          setError(msg);
          setLoading(false);
        });
    }
  }, [status, me, noteParam, printNoParam, router]);

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
      <div style={{ padding: "32px", fontFamily: "var(--font-sans, sans-serif)", textAlign: "center" }}>
        Đang nạp dữ liệu tem...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: "32px",
          maxWidth: "500px",
          margin: "40px auto",
          fontFamily: "var(--font-sans, sans-serif)",
          border: "1px solid #f87171",
          borderRadius: "8px",
          backgroundColor: "#fef2f2",
          color: "#991b1b",
        }}
      >
        <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "8px" }}>Không thể in tem</h2>
        <p style={{ fontSize: "0.875rem", lineHeight: 1.5 }}>{error}</p>
        <button
          type="button"
          onClick={() => window.close()}
          style={{
            marginTop: "16px",
            padding: "8px 16px",
            backgroundColor: "#ffffff",
            border: "1px solid #d1d5db",
            borderRadius: "6px",
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          Đóng cửa sổ
        </button>
      </div>
    );
  }

  if (!labelData || !qrSvg) {
    return null;
  }

  const reprintTitle =
    labelData.reprint_reason === "ADDRESS_CHANGED"
      ? "IN LẠI – ĐỔI ĐỊA CHỈ"
      : `IN LẠI – LẦN ${labelData.print_no}`;

  return (
    <>
      <style>{`
        @page {
          size: 100mm 150mm;
          margin: 0;
        }
        @media print {
          .noPrint {
            display: none !important;
          }
          body {
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
          }
        }
      `}</style>

      {/* Toolbar for manual actions */}
      <div
        className="noPrint"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          maxWidth: "100mm",
          margin: "12px auto",
          padding: "8px 12px",
          background: "#f3f4f6",
          borderRadius: "6px",
          fontFamily: "var(--font-sans, sans-serif)",
          fontSize: "13px",
        }}
      >
        <span>Khổ in chuẩn: 100 × 150 mm</span>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            onClick={() => window.print()}
            style={{
              padding: "6px 12px",
              background: "#2563eb",
              color: "#ffffff",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            In tem
          </button>
          <button
            type="button"
            onClick={() => window.close()}
            style={{
              padding: "6px 12px",
              background: "#ffffff",
              color: "#374151",
              border: "1px solid #d1d5db",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Đóng
          </button>
        </div>
      </div>

      {/* Main Label: 100mm x 150mm */}
      <div
        style={{
          width: "100mm",
          height: "150mm",
          margin: "0 auto",
          boxSizing: "border-box",
          padding: "6mm 8mm",
          fontFamily: "var(--font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
          color: "#000000",
          backgroundColor: "#ffffff",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          border: "1px dashed #cccccc",
        }}
      >
        {/* Header */}
        <div style={{ borderBottom: "1.5px solid #000000", paddingBottom: "4mm" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ fontSize: "14pt", fontWeight: 800, letterSpacing: "0.5px" }}>CÁ VỀ</div>
              <div style={{ fontSize: "8pt", textTransform: "uppercase", color: "#333333" }}>
                Vựa cá tươi sống B2C
              </div>
            </div>
            {labelData.is_reprint && (
              <div
                style={{
                  border: "2px solid #000000",
                  padding: "2px 6px",
                  fontSize: "8.5pt",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                }}
              >
                {reprintTitle}
              </div>
            )}
          </div>
          <div style={{ marginTop: "2mm", display: "flex", justifyContent: "space-between", fontSize: "9pt" }}>
            <span>
              Mã đơn: <strong>{labelData.order_code}</strong>
            </span>
            <span>
              Lượt in: <strong>#{labelData.print_no}</strong>
            </span>
          </div>
        </div>

        {/* QR Code & Barcode Section */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "2mm 0",
            borderBottom: "1px solid #000000",
          }}
        >
          <div
            dangerouslySetInnerHTML={{ __html: qrSvg }}
            style={{ width: "35mm", height: "35mm", display: "flex", justifyContent: "center" }}
          />
          <div
            style={{
              fontFamily: "var(--font-mono, monospace)",
              fontSize: "11pt",
              fontWeight: 700,
              letterSpacing: "1px",
              marginTop: "1mm",
            }}
          >
            {labelData.barcode_value}
          </div>
          <div style={{ fontSize: "8pt", color: "#444444" }}>Mã phiếu: {labelData.note_code}</div>
        </div>

        {/* Recipient Section */}
        <div style={{ padding: "3mm 0", borderBottom: "1px solid #000000" }}>
          <div style={{ fontSize: "8pt", fontWeight: 700, textTransform: "uppercase", color: "#555555" }}>
            Người nhận hàng
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: "1mm" }}>
            <div style={{ fontSize: "13pt", fontWeight: 800 }}>{labelData.recipient_name}</div>
            <div style={{ fontSize: "12pt", fontWeight: 700, fontFamily: "var(--font-mono, monospace)" }}>
              {labelData.recipient_phone_masked}
            </div>
          </div>
          <div
            style={{
              fontSize: "9.5pt",
              lineHeight: 1.35,
              marginTop: "2mm",
              display: "-webkit-box",
              WebkitLineClamp: 4,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {labelData.address}
          </div>
        </div>

        {/* Goods / Packages Info */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: "2mm",
            padding: "2.5mm 0",
            borderBottom: "1px solid #000000",
            fontSize: "8.5pt",
          }}
        >
          <div>
            <div style={{ color: "#555555" }}>Số kiện</div>
            <div style={{ fontSize: "10pt", fontWeight: 700 }}>{labelData.packages}</div>
          </div>
          <div>
            <div style={{ color: "#555555" }}>Tổng kg</div>
            <div style={{ fontSize: "10pt", fontWeight: 700 }}>{labelData.total_kg} kg</div>
          </div>
          <div>
            <div style={{ color: "#555555" }}>HSD sớm nhất</div>
            <div style={{ fontSize: "9pt", fontWeight: 600 }}>{labelData.earliest_expiry}</div>
          </div>
        </div>

        {/* Payment Confirmation Banner */}
        <div
          style={{
            border: "2px solid #000000",
            padding: "3.5mm 2mm",
            textAlign: "center",
            marginTop: "1mm",
          }}
        >
          <div style={{ fontSize: "11pt", fontWeight: 900, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            {labelData.paid_text}
          </div>
          <div style={{ fontSize: "8pt", marginTop: "1mm", fontStyle: "italic" }}>
            (Người giao hàng vui lòng không thu thêm tiền của khách)
          </div>
        </div>
      </div>
    </>
  );
}

export default function LabelPrintPage() {
  return (
    <Suspense
      fallback={
        <div style={{ padding: "32px", textAlign: "center", fontFamily: "var(--font-sans, sans-serif)" }}>
          Đang nạp trang in...
        </div>
      }
    >
      <LabelPrintContent />
    </Suspense>
  );
}
