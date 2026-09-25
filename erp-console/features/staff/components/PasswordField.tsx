"use client";

// Cặp ô mật khẩu TẠM do Chủ đặt cho nhân viên (tạo tài khoản S41, đặt lại mật khẩu S42) — S48:
// - ô chính + ô "Nhập lại" dùng ô chung shared/ui/PasswordInput (nút mắt hiện/ẩn ≥ 44px, gợi ý quy tắc trước khi gửi);
// - dòng công cụ dưới ô chính: "Tạo ngẫu nhiên" điền cả hai ô và HIỆN chữ để Chủ đọc cho nhân viên; "Sao chép" có
//   phản hồi "Đã chép" (UI4);
// - `mismatch` do form cha bật khi bấm gửi mà hai ô khác nhau (form cha KHÔNG gọi API trong trường hợp đó).
// Độ mạnh do BE kiểm (AUTH_PASSWORD_VALIDATORS) — FE hiện nguyên văn lỗi BE trả. Giá trị KHÔNG vào nháp.
import { useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import { PasswordInput } from "@/shared/ui/PasswordInput";
import { MSG } from "@/shared/lib/messages";
import { suggestPassword } from "../api";
import { CopyButton } from "./CopyButton";
import s from "../staff.module.css";

type Props = {
  id: string;
  /** Nhãn ô chính, vd "Mật khẩu tạm". Ô thứ hai: "Nhập lại " + nhãn viết thường. */
  label: string;
  value: string;
  onChange: (v: string) => void;
  again: string;
  onAgainChange: (v: string) => void;
  mismatch: boolean;
  /** UI5: ô còn trống khi bấm gửi (nút gửi không bị tắt) → báo tại ô đó. */
  missing?: "main" | "again" | null;
  /** Tên đăng nhập của người được đặt — cho gợi ý "không giống tên đăng nhập". */
  username?: string;
  disabled?: boolean;
  /** Focus vào ô chính khi tấm/chế độ mở. */
  autoFocus?: boolean;
};

export function PasswordField({
  id,
  label,
  value,
  onChange,
  again,
  onAgainChange,
  mismatch,
  missing = null,
  username,
  disabled,
  autoFocus,
}: Props) {
  const [shown, setShown] = useState(false);
  const lower = `${label.charAt(0).toLowerCase()}${label.slice(1)}`;
  return (
    <>
      <PasswordInput
        id={id}
        label={label}
        autoComplete="new-password"
        autoFocus={autoFocus}
        value={value}
        onChange={onChange}
        disabled={disabled}
        required
        rules
        username={username}
        shown={shown}
        onShownChange={setShown}
        help={MSG.tempPasswordHelp}
        error={missing === "main" ? MSG.needField(lower) : null}
        extra={
          <div className={s.pwTools}>
            <button
              type="button"
              className="btn"
              onClick={() => {
                const pw = suggestPassword();
                onChange(pw);
                onAgainChange(pw);
                setShown(true);
              }}
              disabled={disabled}
            >
              <Icon name="casino" />
              Tạo ngẫu nhiên
            </button>
            <CopyButton value={value} what={lower} disabled={disabled} />
          </div>
        }
      />
      <PasswordInput
        id={`${id}-again`}
        label={`Nhập lại ${lower}`}
        autoComplete="new-password"
        value={again}
        onChange={onAgainChange}
        disabled={disabled}
        required
        shown={shown}
        onShownChange={setShown}
        error={missing === "again" ? MSG.needFieldAgain(lower) : mismatch ? MSG.passwordMismatch : null}
      />
    </>
  );
}
