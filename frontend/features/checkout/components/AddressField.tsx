"use client";

import Banner from "@/components/ui/Banner";
import Icon from "@/components/ui/Icon";
import TextField from "@/components/ui/TextField";
import s from "./AddressField.module.css";

export interface AddressFieldProps {
  id?: string;
  name?: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  error?: string;
  /** Vừa điền từ bản đồ (C1c): viền xanh và dòng báo; mất khi khách sửa tay. */
  filledFromMap?: boolean;
  /** Form đang gửi: ô chỉ đọc, nút Bản đồ tắt. */
  readOnly?: boolean;
  onOpenMap: () => void;
}

/** Id dòng "Cá Về giao trong khu vực Phan Thiết." để nối vào aria-describedby của ô. */
export const ADDRESS_AREA_NOTE_ID = "address-area-note";

/**
 * Một ô địa chỉ giao hàng (gõ tay được) cộng nút "Bản đồ" (COMPONENTS #8). Nút luôn hiện; có bấm được tới Google hay không
 * do màn cha quyết (thiếu key thì mở thẳng hộp thoại C5). Không tách địa chỉ thành nhiều ô, không lưu toạ độ.
 */
export default function AddressField({
  id = "f-addr",
  name = "delivery_address",
  value,
  onChange,
  onBlur,
  error,
  filledFromMap = false,
  readOnly = false,
  onOpenMap,
}: AddressFieldProps) {
  return (
    <div className={s.wrap}>
      {filledFromMap ? (
        <Banner tone="success" live="polite" icon="check">
          Đã điền địa chỉ từ bản đồ.
        </Banner>
      ) : null}
      <TextField
        id={id}
        name={name}
        label="Địa chỉ giao hàng"
        labelStyle="title"
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        multiline
        rows={2}
        required
        placeholder="Bấm để tìm trên bản đồ, hoặc gõ địa chỉ"
        autoComplete="street-address"
        hint="Thêm hẻm, tầng, toà nhà nếu có."
        error={error}
        readOnly={readOnly}
        tone={filledFromMap ? "good" : "default"}
        describedBy={ADDRESS_AREA_NOTE_ID}
        endSlot={
          <button
            type="button"
            className={s.mapButton}
            aria-label="Tìm và chọn địa chỉ trên bản đồ"
            disabled={readOnly}
            onClick={onOpenMap}
          >
            <Icon name="map-pin" size={20} />
            <span>Bản đồ</span>
          </button>
        }
      />
      <p id={ADDRESS_AREA_NOTE_ID} className={s.area}>
        Cá Về giao trong khu vực Phan Thiết.
      </p>
    </div>
  );
}
