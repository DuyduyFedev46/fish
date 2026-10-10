import s from "./Spinner.module.css";

// Vòng quay nhỏ báo đang xử lý. Luôn đi kèm chữ hiện cạnh; không có chữ thì có `label` ẩn (role="status").
export default function Spinner({ size = 18, label }: { size?: 16 | 18 | 36; label?: string }) {
  const ring = (
    <svg
      className={s.spinner}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="9" className={s.track} />
      <path d="M12 3a9 9 0 0 1 9 9" />
    </svg>
  );
  if (!label) return ring;
  return (
    <span role="status" className={s.wrap}>
      {ring}
      <span className="visually-hidden">{label}</span>
    </span>
  );
}
