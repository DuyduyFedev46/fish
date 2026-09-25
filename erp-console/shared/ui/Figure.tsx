// Số kèm đơn vị (UI3): "546.000 ₫" → số màu chữ chính + đơn vị "₫"/"kg" màu ink-3 (DESIGN.md: đơn vị cùng cỡ, màu phụ).
// Nhận CHUỖI đã định dạng từ shared/lib/format.ts (vnd, kg) — textContent giữ nguyên "546.000 ₫" (e2e so chữ).
// Không có đơn vị (vd "—") thì in nguyên chuỗi.

export function Figure({ text }: { text: string }) {
  const m = /^(.*\S) (₫|kg)$/.exec(text);
  if (!m) return <span className="fig">{text}</span>;
  return (
    <span className="fig">
      {m[1]} <span className="unit">{m[2]}</span>
    </span>
  );
}
