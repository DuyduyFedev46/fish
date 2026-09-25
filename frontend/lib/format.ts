export function formatVnd(amount: number): string {
  return amount.toLocaleString("vi-VN") + "đ";
}

export function formatKg(qty: number): string {
  const rounded = Math.round(qty * 1000) / 1000;
  return `${rounded.toLocaleString("vi-VN")} kg`;
}
