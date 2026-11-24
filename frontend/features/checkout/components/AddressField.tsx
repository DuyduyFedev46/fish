"use client";

// Khối địa chỉ giao hàng có cấu trúc (STA-02, SHOP-3-04, 02b §1.9b.4, BR-BH-29):
// kiểu địa chỉ → tỉnh → [quận/huyện, chỉ kiểu cũ] → phường/xã → số nhà (ô chữ có nút "Tìm địa chỉ" khi cờ bật).
// Màn cha giữ state; đổi cấp cha xoá cấp con ở `formRules` (selectScheme/selectProvince/selectDistrict/selectWard).

import type { AddressUnitSuggestion } from "@/lib/types";
import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
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
  /** Vừa điền số nhà từ hộp tìm VietMap (C1c): viền xanh và banner gợi ý phường; mất khi khách sửa tay. */
  filledFromMap?: boolean;
  /** Gợi ý phường từ máy chủ (khớp đúng 1 dòng danh mục Cá Về); `null` khi không khớp. */
  wardSuggestion?: AddressUnitSuggestion | null;
  /** Khách bấm "Dùng phường này" trên banner gợi ý. */
  onApplyWardSuggestion?: () => void;
  /** `site-info.address_search_enabled === true`: hiện nút "Tìm địa chỉ"; tắt/vắng/lỗi thì ẩn nút (Q-5). */
  addressSearchEnabled?: boolean;
  /** Form đang gửi: các ô chỉ đọc, nút Tìm địa chỉ tắt. */
  readOnly?: boolean;
  onOpenMap: () => void;
}

/** Id dòng "Cá Về giao trong khu vực Phan Thiết." để nối vào aria-describedby của ô số nhà. */
export const ADDRESS_AREA_NOTE_ID = "address-area-note";

const SCHEME_OPTIONS: { value: AddressScheme; label: string }[] = [
  { value: "current", label: "Địa chỉ mới (sau sắp xếp 01/07/2025)" },
  { value: "legacy", label: "Địa chỉ cũ (trước sắp xếp)" },
];

function suggestionMatches(selection: AddressSelection, suggestion: AddressUnitSuggestion): boolean {
  if (selection.scheme !== suggestion.scheme) return false;
  if (selection.provinceCode !== suggestion.province_code) return false;
  if (suggestion.scheme === "legacy" && selection.districtCode !== (suggestion.district_code ?? "")) return false;
  return selection.wardCode === suggestion.ward_code;
}

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
  wardSuggestion = null,
  onApplyWardSuggestion,
  addressSearchEnabled = false,
  readOnly = false,
  onOpenMap,
}: AddressFieldProps) {
  const legacy = selection.scheme === "legacy";
  const wardParent = legacy ? selection.districtCode : selection.provinceCode;
  const matchedAlready = wardSuggestion ? suggestionMatches(selection, wardSuggestion) : false;

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
          {wardSuggestion ? (
            matchedAlready ? (
              "Đã điền số nhà từ VietMap. Phường đã khớp."
            ) : (
              <div className={s.suggestionBanner}>
                <span>
                  Đã điền số nhà từ VietMap. Phường gợi ý: <strong>{wardSuggestion.ward_name}</strong>.
                </span>
                {onApplyWardSuggestion ? (
                  <Button variant="secondary" size="md" disabled={readOnly} onClick={onApplyWardSuggestion}>
                    Dùng phường này
                  </Button>
                ) : null}
              </div>
            )
          ) : (
            "Đã điền số nhà từ VietMap. Bạn chọn tỉnh và phường/xã ở trên nhé."
          )}
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
          addressSearchEnabled ? (
            <button
              type="button"
              className={s.mapButton}
              aria-label="Tìm địa chỉ giao hàng"
              disabled={readOnly}
              onClick={onOpenMap}
            >
              <Icon name="map-pin" size={20} />
              <span>Tìm địa chỉ</span>
            </button>
          ) : undefined
        }
      />
      <p id={ADDRESS_AREA_NOTE_ID} className={s.area}>
        Cá Về giao trong khu vực Phan Thiết.
      </p>
    </div>
  );
}
