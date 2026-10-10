import Icon from "@/components/ui/Icon";
import s from "./PaymentMethod.module.css";

/**
 * Phương thức thanh toán duy nhất, chỉ đọc (COMPONENTS #25). Không hiện tên nhà cung cấp cổng thanh toán, không hiện số
 * tài khoản, không có radio (không có lựa chọn khác).
 */
export default function PaymentMethod() {
  return (
    <section className={s.box} aria-labelledby="payment-method-title">
      <h2 id="payment-method-title" className={s.title}>
        Phương thức thanh toán
      </h2>
      <div className={s.card}>
        <span className={s.iconBox} aria-hidden="true">
          <Icon name="qr" size={22} />
        </span>
        <span className={s.text}>
          <span className={s.name}>Chuyển khoản ngân hàng (quét mã QR)</span>
          <span className={s.desc}>Quét bằng app ngân hàng. Tiền về đủ là đơn tự xác nhận.</span>
        </span>
        <span className={s.tick} aria-hidden="true">
          <Icon name="check" size={20} strokeWidth={2.4} />
        </span>
      </div>
    </section>
  );
}
