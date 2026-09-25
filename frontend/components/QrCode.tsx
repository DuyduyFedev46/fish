"use client";

import { useEffect, useState } from "react";

export default function QrCode({ value, size = 240 }: { value: string; size?: number }) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    import("qrcode")
      .then((QRCode) =>
        QRCode.toDataURL(value, { width: size, margin: 1 })
      )
      .then((url) => {
        if (!cancelled) setDataUrl(url);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [value, size]);

  if (error) {
    return <p className="qr-error">Không tạo được mã QR. Vui lòng dùng nội dung chuyển khoản bên dưới.</p>;
  }

  if (!dataUrl) {
    return <div className="qr-loading" style={{ width: size, height: size }} aria-label="Đang tạo mã QR" />;
  }

  // eslint-disable-next-line @next/next/no-img-element
  return <img src={dataUrl} width={size} height={size} alt="Mã VietQR để thanh toán" className="qr-image" />;
}
