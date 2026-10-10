import type { Metadata } from "next";
import PreviewGallery from "@/features/ui-preview/PreviewGallery";

// Trang xem thử component. Chỉ được dựng khi build có NEXT_PUBLIC_UI_PREVIEW=1 (xem next.config.mjs); bản thường không có route này.
export const metadata: Metadata = {
  title: "Xem thử component",
  robots: { index: false, follow: false },
};

export default function UiPreviewPage() {
  return <PreviewGallery />;
}
