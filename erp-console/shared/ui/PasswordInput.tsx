"use client";

// Ô mật khẩu dùng chung cho MỌI form (đăng nhập, tạo tài khoản, đặt lại, tự đổi, đặt mật khẩu mới) — S48-AC4:
// - nút mắt hiện/ẩn (vùng bấm 44×44). Chữ của nút nằm trong <span class="sr-only"> (không dùng aria-label) để
//   `getByLabel("Mật khẩu")` chỉ trúng ô nhập, còn `getByRole("button", {name: "Hiện mật khẩu"})` trúng nút.
// - `rules`: hiện gợi ý quy tắc ngay dưới ô, cập nhật khi gõ (trước khi gửi). Không chặn gửi — BE kiểm thật.
// - `error`: lỗi của riêng ô này (vd "Hai mật khẩu không khớp") — hiện dưới ô, gắn aria-invalid.
// - `shown` / `onShownChange`: điều khiển từ ngoài khi 2 ô (mới + nhập lại) hiện/ẩn cùng nhau.
// Không bao giờ lưu giá trị vào nháp/localStorage: component chỉ nhận value/onChange, không tự lưu.

import { useId, useState } from "react";
import { Icon } from "./Icon";
import { MSG } from "@/shared/lib/messages";
import { passwordChecks } from "@/shared/lib/passwordRules";

type Props = {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: "current-password" | "new-password";
  name?: string;
  disabled?: boolean;
  required?: boolean;
  /** Ô được focus khi hộp thoại mở (Sheet đọc data-autofocus). */
  autoFocus?: boolean;
  /** Câu gợi ý tĩnh dưới ô. */
  help?: string;
  /** Hiện danh sách quy tắc (ô mật khẩu MỚI). `username` để gợi ý "không giống tên đăng nhập". */
  rules?: boolean;
  username?: string;
  error?: string | null;
  shown?: boolean;
  onShownChange?: (shown: boolean) => void;
  /** Nút phụ cạnh ô (vd "Tạo ngẫu nhiên"). */
  extra?: React.ReactNode;
};

export function PasswordInput({
  id,
  label,
  value,
  onChange,
  autoComplete,
  name,
  disabled,
  required,
  autoFocus,
  help,
  rules,
  username,
  error,
  shown: shownProp,
  onShownChange,
  extra,
}: Props) {
  const [shownLocal, setShownLocal] = useState(false);
  const shown = shownProp ?? shownLocal;
  const setShown = (v: boolean) => (onShownChange ? onShownChange(v) : setShownLocal(v));
  const uid = useId();
  const helpId = `${uid}-help`;
  const rulesId = `${uid}-rules`;
  const errId = `${uid}-err`;
  const describedBy = [help ? helpId : "", rules ? rulesId : "", error ? errId : ""].filter(Boolean).join(" ") || undefined;

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="pw-row">
        <div className="pw-box">
          <input
            id={id}
            name={name}
            type={shown ? "text" : "password"}
            autoComplete={autoComplete}
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            className={shown ? "mono-input" : undefined}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            required={required}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            data-autofocus={autoFocus ? true : undefined}
          />
          <button
            type="button"
            className="iconbtn pw-eye"
            aria-pressed={shown}
            aria-controls={id}
            onClick={() => setShown(!shown)}
            disabled={disabled}
          >
            <Icon name={shown ? "visibility_off" : "visibility"} />
            <span className="sr-only">{shown ? MSG.pwHide : MSG.pwShow}</span>
          </button>
        </div>
        {extra}
      </div>
      {error && (
        <span className="field-err" id={errId} role="alert">
          <Icon name="error" />
          <span>{error}</span>
        </span>
      )}
      {help && (
        <span className="help" id={helpId}>
          {help}
        </span>
      )}
      {rules && (
        <div className="pw-rules" id={rulesId}>
          <span className="help">{MSG.pwRulesTitle}</span>
          <ul>
            {passwordChecks(value, username).map((c) => (
              <li key={c.key} className={c.ok === true ? "ok" : c.ok === null ? "na" : undefined}>
                <Icon name={c.ok === true ? "check_circle" : c.ok === null ? "info" : "radio_button_unchecked"} />
                {c.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
