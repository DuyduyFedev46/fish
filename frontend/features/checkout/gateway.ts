// Điều hướng trình duyệt sang trang cổng thanh toán SePay (BR-TT-01/13).
// FE không tự tính tiền hay chữ ký: mọi giá trị trong `session.fields` (kể cả chữ ký
// HMAC) đã được máy chủ lập sẵn (story P1, BE). Ở đây chỉ có việc chuyển tiếp.

import type { PaymentCheckoutSession } from "../../lib/types";

export function redirectToGateway(session: PaymentCheckoutSession): void {
  if (typeof window === "undefined") return;

  if (session.gateway_method === "GET") {
    const query = new URLSearchParams(session.fields).toString();
    window.location.href = query
      ? `${session.gateway_url}?${query}`
      : session.gateway_url;
    return;
  }

  // POST: dựng một form ẩn rồi submit — cách chuẩn để chuyển hướng kèm dữ liệu tới một
  // trang bên thứ ba mà không lộ chữ ký lên thanh địa chỉ.
  const form = document.createElement("form");
  form.method = "POST";
  form.action = session.gateway_url;
  form.style.display = "none";

  for (const [key, value] of Object.entries(session.fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = value;
    form.appendChild(input);
  }

  document.body.appendChild(form);
  form.submit();
}
