"use client";

// Alert đầu hộp thoại của màn Gọi xác nhận. Nút gửi nằm ở chân hộp, còn alert ở đầu thân hộp: nếu người dùng đã cuộn xuống
// (điện thoại, form dài) thì lỗi 409 / lỗi gửi nằm ngoài khung nhìn và họ không thấy vì sao không lưu được.
// Nên khi alert hiện (hoặc đổi nội dung) thì cuộn nó vào tầm nhìn.
import { useEffect, useRef } from "react";
import { FormAlert } from "@/shared/ui/form/FormAlert";

export function ModalAlert({ kind, children }: { kind?: "error" | "warn"; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ block: "nearest" });
  }, [children]);
  return (
    <div ref={ref}>
      <FormAlert kind={kind}>{children}</FormAlert>
    </div>
  );
}
