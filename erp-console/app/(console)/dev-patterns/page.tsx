"use client";

// Trang NỘI BỘ để thử các mẫu trang chi tiết / popup / khối AI (ED-04, ED-05, e2e/ed_batch2_patterns.py). Chỉ có ở bản mock.
// Bản build thật: `Demo` = null → hiện "Không tìm thấy trang này", mã demo không vào bundle (điều kiện viết nguyên văn để bị cắt).
import dynamic from "next/dynamic";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";

const Demo = process.env.NEXT_PUBLIC_USE_MOCK === "1" ? dynamic(() => import("./PatternDemo")) : null;

export default function Page() {
  return Demo ? <Demo /> : <NotFoundScreen />;
}
