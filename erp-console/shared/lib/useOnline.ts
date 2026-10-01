"use client";

// Trình duyệt đang có mạng không (navigator.onLine + sự kiện online/offline). Lần vẽ đầu luôn là `true`
// (khớp HTML tĩnh), rồi đồng bộ ngay sau khi mount.
import { useEffect, useState } from "react";

export function useOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const sync = () => setOnline(window.navigator.onLine);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);
  return online;
}
