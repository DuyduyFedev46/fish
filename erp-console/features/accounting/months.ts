// Ô chọn tháng của bộ lọc hoá đơn / chi phí (R11, R12 nhận `month=YYYY-MM`). Hàm thuần.

/** n tháng gần nhất tính từ ngày `today` (YYYY-MM-DD, giờ Việt Nam), mới nhất trước. Giá trị "" = mọi tháng. */
export function recentMonthOptions(today: string, n = 12): { value: string; label: string }[] {
  const [y, m] = today.split("-").map(Number);
  const out = [{ value: "", label: "Mọi tháng" }];
  for (let i = 0; i < n; i += 1) {
    const idx = y * 12 + (m - 1) - i;
    const year = Math.floor(idx / 12);
    const month = (idx % 12) + 1;
    out.push({ value: `${year}-${String(month).padStart(2, "0")}`, label: `Tháng ${month}/${year}` });
  }
  return out;
}
