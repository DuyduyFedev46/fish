"use client";

// Nút sao chép có phản hồi (UI4): bấm → chữ đổi "Đã chép" + dấu tích trong 1,6 giây, trình đọc màn hình được báo qua
// vùng aria-live. Máy không cho dùng clipboard (http thường, trình duyệt cũ) → thử cách cũ, vẫn không được thì báo
// "Không chép được" để người dùng tự bôi đen chép tay (giá trị luôn hiện sẵn trên màn).
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import s from "../staff.module.css";

type Props = {
  value: string;
  /** Phần tên đọc cho trình đọc màn hình, vd "mật khẩu tạm" → "Sao chép mật khẩu tạm". */
  what: string;
  /** Chữ hiện trên nút. */
  label?: string;
  disabled?: boolean;
};

async function writeClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    /* thử cách cũ bên dưới */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.className = "sr-only";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

export function CopyButton({ value, what, label = "Sao chép", disabled }: Props) {
  const [state, setState] = useState<"idle" | "done" | "fail">("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const onClick = async () => {
    const ok = await writeClipboard(value);
    setState(ok ? "done" : "fail");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setState("idle"), 1600);
  };

  return (
    <>
      <button
        type="button"
        className={`btn${state === "done" ? ` ${s.copied}` : ""}`}
        onClick={() => void onClick()}
        disabled={disabled || !value}
      >
        <Icon name={state === "done" ? "check" : state === "fail" ? "error" : "content_copy"} />
        {state === "done" ? "Đã chép" : state === "fail" ? "Không chép được" : label}
        <span className="sr-only"> {what}</span>
      </button>
      <span className="sr-only" role="status">
        {state === "done" ? `Đã chép ${what}.` : state === "fail" ? `Không chép được ${what}, hãy bôi đen để chép tay.` : ""}
      </span>
    </>
  );
}
