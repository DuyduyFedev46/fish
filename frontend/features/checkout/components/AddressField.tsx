"use client";

// Khối địa chỉ giao hàng có cấu trúc (STA-02, BR-BH-29): kiểu địa chỉ → tỉnh → [quận/huyện, chỉ kiểu cũ] → phường/xã → số nhà
// (ô chữ có nút "Bản đồ"). Màn cha giữ state; đổi cấp cha xoá cấp con ở `formRules` (selectScheme/selectProvince/selectDistrict).

import Banner from "@/components/ui/Banner";
import Icon from "@/components/ui/Icon";
import TextField from "@/components/ui/TextField";
import type { AddressSelection, AddressScheme, FormErrors } from "../formRules";
import { STREET_MAX } from "../formRules";
import AdministrativeUnitPicker from "./AdministrativeUnitPicker";
import s from "./AddressField.module.css";

export interface AddressFieldProps {
  selection: AddressSelection;
  onScheme: (scheme: AddressScheme) => void;
  onProvince: (code: string) => void;
  onDistrict: (code: string) => void;
  onWard: (code: string) => void;
  street: string;
  onStreet: (value: string) => void;
  onStreetBlur?: () => void;
  errors: FormErrors;
  /** Vừa điền số nhà từ bản đồ (C1c): viền xanh và dòng báo; mất khi khách sửa tay. */
  filledFromMap?: boolean;
  /** Form đang gửi: các ô chỉ đọc, nút Bản đồ tắt. */
  readOnly?: boolean;
  onOpenMap: () => void;
}

/** Id dòng "Cá Về giao trong khu vực Phan Thiết." để nối vào aria-describedby của ô số nhà. */
export const ADDRESS_AREA_NOTE_ID = "address-area-note";

const SCHEME_OPTIONS: { value: AddressScheme; label: string }[] = [
  { value: "current", label: "Địa chỉ mới (sau sắp xếp 01/07/2025)" },
  { value: "legacy", label: "Địa chỉ cũ (trước sắp xếp)" },
];

export default function AddressField({
  selection,
  onScheme,
  onProvince,
  onDistrict,
  onWard,
  street,
  onStreet,
  onStreetBlur,
  errors,
  filledFromMap = false,
  readOnly = false,
  onOpenMap,
}: AddressFieldProps) {
  const legacy = selection.scheme === "legacy";
  const wardParent = legacy ? selection.districtCode : selection.provinceCode;

  return (
    <div className={s.wrap}>
      <h2 className={s.title}>Địa chỉ giao hàng</h2>
      <fieldset id="f-addr-scheme" className={s.scheme} disabled={readOnly}>
        <legend className={s.legend}>Kiểu địa chỉ</legend>
        {SCHEME_OPTIONS.map((o) => (
          <label key={o.value} className={s.schemeOption}>
            <input
              type="radio"
              name="address-scheme"
              value={o.value}
              checked={selection.scheme === o.value}
              onChange={() => onScheme(o.value)}
              className={s.schemeInput}
            />
            <span className={s.schemeLabel}>{o.label}</span>
          </label>
        ))}
        <p className={s.note}>
          {legacy ? "Địa chỉ cũ gồm tỉnh, quận/huyện, phường/xã." : "Địa chỉ mới gồm tỉnh, phường/xã (không còn quận/huyện)."}
        </p>
      </fieldset>
      <AdministrativeUnitPicker
        id="f-addr-province"
        label="Tỉnh/thành phố"
        scheme={selection.scheme}
        level="province"
        value={selection.provinceCode}
        onChange={onProvince}
        placeholder="Chọn tỉnh/thành phố"
        searchLabel="Tìm tỉnh/thành phố (gõ không dấu cũng được)"
        error={errors.province}
        readOnly={readOnly}
      />
      {legacy ? (
        <AdministrativeUnitPicker
          id="f-addr-district"
          label="Quận/huyện"
          scheme="legacy"
          level="district"
          parentCode={selection.provinceCode}
          value={selection.districtCode}
          onChange={onDistrict}
          placeholder="Chọn quận/huyện"
          disabledHint="Chọn tỉnh/thành phố trước"
          searchLabel="Tìm quận/huyện (gõ không dấu cũng được)"
          error={errors.district}
          readOnly={readOnly}
        />
      ) : null}
      <AdministrativeUnitPicker
        id="f-addr-ward"
        label="Phường/xã"
        scheme={selection.scheme}
        level="ward"
        parentCode={wardParent}
        value={selection.wardCode}
        onChange={onWard}
        placeholder="Chọn phường/xã"
        disabledHint={legacy ? "Chọn quận/huyện trước" : "Chọn tỉnh/thành phố trước"}
        searchLabel="Tìm phường/xã (gõ không dấu cũng được)"
        error={errors.ward}
        readOnly={readOnly}
      />
      {filledFromMap ? (
        <Banner tone="success" live="polite" icon="check">
          Đã điền số nhà từ bản đồ. Bạn vẫn cần chọn tỉnh, phường/xã ở trên.
        </Banner>
      ) : null}
      <TextField
        id="f-addr"
        name="street_address"
        label="Số nhà, tên đường, hẻm, tầng"
        value={street}
        onChange={(v) => onStreet(v.slice(0, STREET_MAX))}
        onBlur={onStreetBlur}
        multiline
        rows={2}
        required
        placeholder="Ví dụ: 12 Đường Giả, hẻm 3"
        autoComplete="address-line1"
        hint="Thêm hẻm, tầng, toà nhà nếu có."
        error={errors.street}
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
