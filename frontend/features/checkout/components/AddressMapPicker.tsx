"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import Button from "@/components/ui/Button";
import FullscreenSheet from "@/components/ui/FullscreenSheet";
import Icon from "@/components/ui/Icon";
import Spinner from "@/components/ui/Spinner";
import { cx } from "@/components/ui/cx";
import { loadGoogleMaps } from "../googleMaps";
import type { GoogleMapInstance, GooglePlacePrediction, LatLngLiteral } from "../googleMaps.d";
import s from "./AddressMapPicker.module.css";

/** Tâm bản đồ mở đầu: Phan Thiết (khu vực giao hàng, L1). Không phải vị trí của khách. */
const START_CENTER: LatLngLiteral = { lat: 10.9289, lng: 108.1021 };
const MIN_QUERY_CHARS = 2;
const SUGGEST_DEBOUNCE_MS = 250;

export const MAP_NOTICE_ID = "map-google-notice";

/** Câu thông báo Google (BR-BH-29, 05-phap-ly §1.2b): hiện ngay khi hộp thoại mở, trước khi script nạp xong. */
export const MAP_NOTICE_TEXT =
  "Bản đồ do Google cung cấp. Chữ bạn gõ và vị trí bạn ghim sẽ được gửi tới Google. Không muốn dùng, bạn đóng lại và gõ địa chỉ trực tiếp.";

type Suggestion = { id: string; main: string; secondary: string; prediction: GooglePlacePrediction };
type MapCtor = new (el: HTMLElement, options: Record<string, unknown>) => GoogleMapInstance;
type PlacesLib = {
  AutocompleteSessionToken: new () => unknown;
  AutocompleteSuggestion: {
    fetchAutocompleteSuggestions(request: Record<string, unknown>): Promise<{
      suggestions: { placePrediction: GooglePlacePrediction | null }[];
    }>;
  };
};
type Geocoder = { geocode(request: { location: LatLngLiteral }): Promise<{ results: { formatted_address: string }[] }> };

export interface AddressMapPickerProps {
  open: boolean;
  /** Đóng không đổi địa chỉ (X, Esc, "Nhập tay"). */
  onClose: () => void;
  /** Chỉ chuỗi địa chỉ, không toạ độ. */
  onConfirm: (address: string) => void;
  /** Script lỗi, bị chặn hoặc quá 10 giây: màn cha đóng hộp thoại này rồi mở C5. */
  onLoadFailed: () => void;
}

/**
 * Hộp thoại chọn vị trí giao hàng (C1b). Script Google chỉ nạp khi hộp thoại này mở. Toạ độ chỉ nằm trong biến cục bộ
 * (ghim, đảo địa chỉ) và mất khi đóng; không `localStorage`, không URL, không gửi lên máy chủ Cá Về. Không có
 * Geolocation và không có nút "Vị trí của tôi".
 */
export default function AddressMapPicker({ open, onClose, onConfirm, onLoadFailed }: AddressMapPickerProps) {
  const baseId = useId();
  const listId = `${baseId}-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [mapEl, setMapEl] = useState<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [listOpen, setListOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [address, setAddress] = useState("");
  const [geocoding, setGeocoding] = useState(false);

  const mapRef = useRef<GoogleMapInstance | null>(null);
  const tokenRef = useRef<unknown>(null);
  const mapCtorRef = useRef<MapCtor | null>(null);
  const placesRef = useRef<PlacesLib | null>(null);
  const geocoderRef = useRef<Geocoder | null>(null);
  const failedRef = useRef(onLoadFailed);
  failedRef.current = onLoadFailed;
  const movedByUserRef = useRef(false);

  // Mở: nạp script (lần đầu), rồi 3 thư viện. Lỗi bất kỳ -> báo màn cha. Đóng: bỏ hết trạng thái cục bộ (kể cả toạ độ).
  useEffect(() => {
    if (!open) return;
    let active = true;
    setStatus("loading");
    setQuery("");
    setSuggestions([]);
    setListOpen(false);
    setActiveIdx(-1);
    setAddress("");
    movedByUserRef.current = false;
    (async () => {
      try {
        const ns = await loadGoogleMaps();
        const [maps, places, geocoding] = await Promise.all([
          ns.maps.importLibrary("maps"),
          ns.maps.importLibrary("places"),
          ns.maps.importLibrary("geocoding"),
        ]);
        if (!active) return;
        mapCtorRef.current = maps.Map;
        placesRef.current = places;
        geocoderRef.current = new geocoding.Geocoder();
        tokenRef.current = new places.AutocompleteSessionToken();
        setStatus("ready");
      } catch {
        if (active) failedRef.current();
      }
    })();
    return () => {
      active = false;
      mapRef.current = null;
      mapCtorRef.current = null;
      placesRef.current = null;
      geocoderRef.current = null;
      tokenRef.current = null;
    };
  }, [open]);

  // Dựng bản đồ khi đã có thư viện và khung chứa.
  useEffect(() => {
    if (status !== "ready" || !mapEl || mapRef.current) return;
    const Ctor = mapCtorRef.current;
    if (!Ctor) return;
    const map = new Ctor(mapEl, {
      center: START_CENTER,
      zoom: 14,
      disableDefaultUI: true,
      zoomControl: true,
      gestureHandling: "greedy",
      clickableIcons: false,
    });
    mapRef.current = map;
    let timer: number | undefined;
    const listener = map.addListener("idle", () => {
      // Chỉ đảo địa chỉ sau khi khách kéo bản đồ hoặc chọn một gợi ý, không phải lần dựng đầu.
      if (!movedByUserRef.current) return;
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        const c = map.getCenter();
        if (!c || !geocoderRef.current) return;
        setGeocoding(true);
        geocoderRef.current
          .geocode({ location: { lat: c.lat(), lng: c.lng() } })
          .then((res) => {
            if (mapRef.current !== map) return;
            const best = res.results[0]?.formatted_address;
            if (best) setAddress(best);
          })
          .catch(() => {})
          .finally(() => setGeocoding(false));
      }, 350);
    });
    const dragListener = map.addListener("dragstart", () => {
      movedByUserRef.current = true;
    });
    return () => {
      window.clearTimeout(timer);
      listener.remove();
      dragListener.remove();
    };
  }, [status, mapEl]);

  // Gợi ý địa chỉ: gõ từ 2 ký tự, chờ 250 ms. Chỉ gọi khi thư viện đã sẵn sàng.
  useEffect(() => {
    const q = query.trim();
    if (status !== "ready" || q.length < MIN_QUERY_CHARS) {
      setSuggestions([]);
      return;
    }
    let active = true;
    const timer = window.setTimeout(async () => {
      const places = placesRef.current;
      if (!places) return;
      try {
        const res = await places.AutocompleteSuggestion.fetchAutocompleteSuggestions({
          input: q,
          includedRegionCodes: ["vn"],
          language: "vi",
          region: "vn",
          sessionToken: tokenRef.current,
        });
        if (!active) return;
        const next: Suggestion[] = [];
        res.suggestions.forEach((sg, i) => {
          const p = sg.placePrediction;
          if (!p) return;
          next.push({
            id: `${baseId}-opt-${i}`,
            main: p.mainText ? p.mainText.toString() : p.text.toString(),
            secondary: p.secondaryText ? p.secondaryText.toString() : "",
            prediction: p,
          });
        });
        setSuggestions(next.slice(0, 5));
        setActiveIdx(-1);
      } catch {
        if (active) setSuggestions([]);
      }
    }, SUGGEST_DEBOUNCE_MS);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [query, status, baseId]);

  const pick = useCallback(async (sg: Suggestion) => {
    setListOpen(false);
    setActiveIdx(-1);
    setQuery(sg.main);
    try {
      const place = sg.prediction.toPlace();
      await place.fetchFields({ fields: ["location", "formattedAddress"] });
      const addr = place.formattedAddress || [sg.main, sg.secondary].filter(Boolean).join(", ");
      setAddress(addr);
      if (place.location && mapRef.current) {
        movedByUserRef.current = false;
        mapRef.current.setCenter(place.location);
        mapRef.current.setZoom(17);
      }
    } catch {
      setAddress([sg.main, sg.secondary].filter(Boolean).join(", "));
    }
    // Phiên gợi ý kết thúc khi đã chọn; phiên mới cho lần tìm sau.
    const places = placesRef.current;
    if (places) tokenRef.current = new places.AutocompleteSessionToken();
  }, []);

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    const count = suggestions.length;
    if (e.key === "Escape" && listOpen && count > 0) {
      // Esc đóng danh sách trước, lần nữa mới đóng hộp thoại.
      e.preventDefault();
      setListOpen(false);
      setActiveIdx(-1);
      return;
    }
    if ((e.key === "ArrowDown" || e.key === "ArrowUp") && count > 0) {
      e.preventDefault();
      setListOpen(true);
      setActiveIdx((cur) => (e.key === "ArrowDown" ? (cur >= count - 1 ? 0 : cur + 1) : cur <= 0 ? count - 1 : cur - 1));
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (listOpen && activeIdx >= 0 && suggestions[activeIdx]) pick(suggestions[activeIdx]);
    }
  }

  const showList = listOpen && suggestions.length > 0;
  const activeId = showList && activeIdx >= 0 ? suggestions[activeIdx]?.id : undefined;

  return (
    <FullscreenSheet
      open={open}
      onClose={onClose}
      title="Chọn vị trí giao hàng"
      closeLabel="Đóng, quay lại nhập tay"
      initialFocusRef={inputRef}
      footer={
        <div className={s.footer}>
          <p className={cx(s.chosen, !address && s.chosenEmpty)} aria-live="polite">
            <Icon name="map-pin" size={18} />
            <span>{address || "Chọn một gợi ý hoặc kéo bản đồ để đặt ghim."}</span>
          </p>
          <div className={s.actions}>
            <Button
              size="lg"
              fullWidth
              disabled={!address || geocoding}
              onClick={() => onConfirm(address)}
            >
              Xác nhận vị trí này
            </Button>
            <span className={s.manual}>
              <Button variant="secondary" size="lg" fullWidth onClick={onClose}>
                Nhập tay
              </Button>
            </span>
          </div>
        </div>
      }
    >
      <div className={s.body}>
        <div className={s.searchWrap}>
          <div className={s.search}>
            <Icon name="search" size={20} />
            <input
              ref={inputRef}
              type="search"
              role="combobox"
              className={s.input}
              aria-label="Tìm địa chỉ"
              aria-describedby={MAP_NOTICE_ID}
              aria-expanded={showList}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={activeId}
              autoComplete="off"
              spellCheck={false}
              placeholder="Tìm địa chỉ"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setListOpen(true);
              }}
              onFocus={() => setListOpen(true)}
              onKeyDown={onKeyDown}
            />
            {query ? (
              <button
                type="button"
                className={s.clear}
                aria-label="Xoá chữ"
                onClick={() => {
                  setQuery("");
                  setSuggestions([]);
                  inputRef.current?.focus();
                }}
              >
                <Icon name="close" size={18} />
              </button>
            ) : null}
          </div>
          <p id={MAP_NOTICE_ID} className={s.notice}>
            {MAP_NOTICE_TEXT}
          </p>
          <ul id={listId} role="listbox" aria-label="Gợi ý địa chỉ" className={s.list} hidden={!showList}>
            {suggestions.map((sg, i) => (
              <li
                key={sg.id}
                id={sg.id}
                role="option"
                aria-selected={i === activeIdx}
                className={cx(s.option, i === activeIdx && s.optionActive)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(sg)}
              >
                <Icon name="map-pin" size={18} />
                <span className={s.optionText}>
                  <span className={s.optionMain}>{sg.main}</span>
                  {sg.secondary ? <span className={s.optionSub}>{sg.secondary}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className={s.mapArea}>
          <div ref={setMapEl} className={s.map} role="img" aria-label="Bản đồ, kéo để chỉnh ghim" />
          {status === "loading" ? (
            <div className={s.loading} aria-busy="true">
              <Spinner size={36} label="Đang tải bản đồ" />
            </div>
          ) : (
            <div className={s.pin} aria-hidden="true">
              <span className={s.pinLabel}>Giao tới đây</span>
              <Icon name="map-pin" size={36} />
            </div>
          )}
        </div>
      </div>
    </FullscreenSheet>
  );
}
