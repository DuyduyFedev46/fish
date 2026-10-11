import Icon from "@/components/ui/Icon";
import s from "./PaymentChoice.module.css";

/**
 * Chọn phương thức thanh toán ngay ở form đặt hàng (SHOP-FIX-01). Hiện chỉ một lựa chọn, chọn sẵn; không ghi tên
 * nhà cung cấp cổng. Radio thật trong fieldset để đọc màn hình và phím hoạt động.
 */
export default function PaymentChoice({ disabled }: { disabled?: boolean }) {
  return (
    <fieldset className={s.box} disabled={disabled}>
      <legend className={s.legend}>Phương thức thanh toán</legend>
      <label className={s.card} htmlFor="f-pay-qr">
        <input className={s.radio} type="radio" id="f-pay-qr" name="payment_method" value="bank_qr" checked readOnly />
        <span className={s.iconBox} aria-hidden="true">
          <Icon name="qr" size={22} />
        </span>
        <span className={s.text}>
          <span className={s.name}>Chuyển khoản ngân hàng (quét mã QR)</span>
          <span className={s.desc}>Bấm Đặt hàng để sang trang quét mã. Tiền về đủ là đơn tự xác nhận.</span>
        </span>
      </label>
    </fieldset>
  );
}
