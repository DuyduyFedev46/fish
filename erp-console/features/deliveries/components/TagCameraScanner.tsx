"use client";

// CS-17 — quét tem bằng camera, CHỈ khi trình duyệt có `BarcodeDetector` (không thêm thư viện quét mã). Không có thì màn
// không hiện nút camera; máy quét USB (gõ như bàn phím) và ô gõ tay luôn dùng được. Hình camera không được lưu hay gửi đi.
import { useEffect, useRef } from "react";
import s from "../deliveries.module.css";

type Detector = { detect: (source: HTMLVideoElement) => Promise<Array<{ rawValue: string }>> };
type DetectorCtor = new (opts?: { formats?: string[] }) => Detector;

function detectorCtor(): DetectorCtor | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { BarcodeDetector?: DetectorCtor }).BarcodeDetector ?? null;
}

/** Trình duyệt có đủ BarcodeDetector và getUserMedia để quét tem bằng camera. */
export function cameraScanSupported(): boolean {
  return Boolean(detectorCtor() && typeof navigator !== "undefined" && navigator.mediaDevices?.getUserMedia);
}

type Props = {
  onCode: (raw: string) => void;
  onFail: () => void;
};

export function TagCameraScanner({ onCode, onFail }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const codeRef = useRef(onCode);
  codeRef.current = onCode;
  const failRef = useRef(onFail);
  failRef.current = onFail;

  useEffect(() => {
    const Ctor = detectorCtor();
    if (!Ctor) {
      failRef.current();
      return;
    }
    let stream: MediaStream | null = null;
    let timer: ReturnType<typeof setInterval> | null = null;
    let alive = true;
    const detector = new Ctor({ formats: ["qr_code", "code_128"] });
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((s) => {
        if (!alive) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        const video = videoRef.current;
        if (!video) return;
        video.srcObject = s;
        void video.play().catch(() => undefined);
        let busy = false;
        timer = setInterval(() => {
          if (busy || video.readyState < 2) return;
          busy = true;
          detector
            .detect(video)
            .then((found) => {
              const hit = found.find((f) => f.rawValue);
              if (hit && alive) codeRef.current(hit.rawValue);
            })
            .catch(() => undefined)
            .finally(() => {
              busy = false;
            });
        }, 300);
      })
      .catch(() => {
        if (alive) failRef.current();
      });
    return () => {
      alive = false;
      if (timer) clearInterval(timer);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return <video ref={videoRef} className={s.cameraVideo} playsInline muted aria-label="Hình từ camera để quét mã trên tem" />;
}
