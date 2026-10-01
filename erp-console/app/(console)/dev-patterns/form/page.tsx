"use client";

// Trang NỘI BỘ thử mẫu form (FormPage, FormAlert, SummaryBlock). Chỉ có ở bản mock; bản build thật hiện "Không tìm thấy".
import dynamic from "next/dynamic";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";

const Demo = process.env.NEXT_PUBLIC_USE_MOCK === "1" ? dynamic(() => import("./FormDemo")) : null;

export default function Page() {
  return Demo ? <Demo /> : <NotFoundScreen />;
}
