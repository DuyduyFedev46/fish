// Điều hướng trình duyệt sang trang cổng thanh toán SePay (BR-TT-01/13).
// FE không tự tính tiền hay chữ ký: mọi giá trị trong `session.fields` (kể cả chữ ký
// HMAC) đã được máy chủ lập sẵn (story P1, BE). Ở đây chỉ có việc chuyển tiếp.

import type { PaymentCheckoutSession } from "../../lib/types";

// BR-TT-13: chữ ký phụ thuộc THỨ TỰ field. Không được thêm/bớt/sắp lại/đổi tên field
// trong `session.fields` — chỉ render đúng nguyên mảng máy chủ trả thành input ẩn rồi submit.
export function redirectToGateway(session: PaymentCheckoutSession): void {
  if (typeof window === "undefined") return;

  const form = document.createElement("form");
  form.method = "POST";
  form.action = session.checkout_url;
  form.style.display = "none";

  for (const field of session.fields) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = field.name;
    input.value = field.value;
    form.appendChild(input);
  }

  document.body.appendChild(form);
  form.submit();
}

// CHỈ dùng ở chế độ mock (NEXT_PUBLIC_USE_MOCK=1): static export không có route nào nhận
// POST thật để đóng vai "cổng", nên đi bằng điều hướng GET thẳng tới trang giả lập của
// chính Shop (features/checkout/components/MockGatewayPanel.tsx). Không gọi hàm này khi
// USE_MOCK=false.
export function goToMockGateway(orderCode: string, amount: number): void {
  if (typeof window === "undefined") return;
  const origin = window.location.origin;
  const returnBase = `${origin}/shop/orders?code=${encodeURIComponent(orderCode)}`;
  const params = new URLSearchParams({
    mock_gateway: "1",
    order: orderCode,
    amount: String(amount),
    success_url: `${returnBase}&result=success`,
    cancel_url: `${returnBase}&result=cancel`,
    error_url: `${returnBase}&result=error`,
  });
  window.location.href = `${origin}/shop/checkout/?${params.toString()}`;
}
