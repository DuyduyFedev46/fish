"use client";

// Hộp tìm địa chỉ giao hàng qua máy chủ Cá Về (SHOP-3-04, 02b §1.9b, phương án A, BR-BH-29).
// Không nạp thư viện bản đồ, không gọi thẳng dịch vụ bản đồ ngoài từ trình duyệt, không xin vị trí trình duyệt,
// không lưu chữ gõ hay địa chỉ vào storage/URL/console.

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { ApiError, getAddressPlace, searchAddress } from "@/lib/api";
import type {
  AddressPlaceResponse,
  AddressScheme,
  AddressSearchItem,
  AddressUnitSuggestion,
} from "@/lib/types";
import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import FullscreenSheet from "@/components/ui/FullscreenSheet";
import Icon from "@/components/ui/Icon";
import Spinner from "@/components/ui/Spinner";
import { cx } from "@/components/ui/cx";
import { recordAddressSearchFailure } from "../addressSearch";
import s from "./AddressSearchSheet.module.css";

const MIN_QUERY_CHARS = 2;
const QUERY_MAX_CHARS = 120;
const SUGGEST_DEBOUNCE_MS = 250;

export const MAP_NOTICE_ID = "address-search-notice";

/** Câu thông báo VietMap (BR-BH-29, 05-phap-ly §1.2c-A, legal-vn chốt): hiện ngay khi hộp tìm mở, trước request đầu tiên. */
export const MAP_NOTICE_TEXT =
  "Gợi ý địa chỉ do VietMap cung cấp. Chữ bạn gõ được máy chủ Cá Về chuyển tới VietMap để tìm địa chỉ, không kèm họ tên hay số điện thoại. Không muốn dùng, bạn đóng lại và gõ địa chỉ trực tiếp.";

export const RATE_LIMIT_MESSAGE = "Thao tác quá nhanh, thử lại sau vài giây.";

export interface AddressSearchConfirmResult {
  street: string;
  suggestion: AddressUnitSuggestion | null;
}

export interface AddressSearchSheetProps {
  open: boolean;
  scheme: AddressScheme;
  /** Đóng không đổi địa chỉ (X, Esc, "Nhập tay"). */
  onClose: () => void;
  /** Điền chuỗi số nhà + gợi ý phường (nếu khớp danh mục Cá Về). */
  onConfirm: (result: AddressSearchConfirmResult) => void;
  /** Máy chủ trả 503 hoặc mất mạng: màn cha đóng hộp này trước rồi mở hộp thoại C5. */
  onSearchFailed: () => void;
}

function isRateLimited(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 429 || err.code === "throttled");
}

function isUnavailableOrNetwork(err: unknown): boolean {
  if (!(err instanceof ApiError)) return true;
  return err.status === 503 || err.status >= 500 || err.code === "ADDRESS_SEARCH_UNAVAILABLE";
}

export default function AddressSearchSheet({
  open,
  scheme,
  onClose,
  onConfirm,
  onSearchFailed,
}: AddressSearchSheetProps) {
  const baseId = useId();
  const listId = `${baseId}-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AddressSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [pickedPlace, setPickedPlace] = useState<AddressPlaceResponse | null>(null);
  const [loadingPlace, setLoadingPlace] = useState(false);
  const [rateLimitError, setRateLimitError] = useState<string | null>(null);

  const failedRef = useRef(onSearchFailed);
  failedRef.current = onSearchFailed;
  const placeSeqRef = useRef(0);
  const prevSchemeRef = useRef<AddressScheme>(scheme);

  const resetAll = useCallback(() => {
    placeSeqRef.current += 1;
    setQuery("");
    setResults([]);
    setSearching(false);
    setHasSearched(false);
    setActiveIdx(-1);
    setSelectedRef(null);
    setPickedPlace(null);
    setLoadingPlace(false);
    setRateLimitError(null);
  }, []);

  // Mở/đóng hộp: xoá sạch trạng thái cục bộ. Request đầu tiên chỉ đi sau khi khách gõ đủ 2 ký tự (AC1, AC2).
  useEffect(() => {
    resetAll();
    prevSchemeRef.current = scheme;
  }, [open, resetAll, scheme]);

  // Đổi kiểu địa chỉ khi hộp đang mở: xoá kết quả cũ (02b §1.9b.4, AC3c).
  useEffect(() => {
    if (prevSchemeRef.current !== scheme) {
      prevSchemeRef.current = scheme;
      resetAll();
    }
  }, [scheme, resetAll]);

  // Tìm gợi ý: gộp khoảng trắng, từ 2 ký tự trở lên, chờ 250 ms.
  useEffect(() => {
    if (!open) return;
    const normalized = query.trim().replace(/\s+/g, " ");
    if (normalized.length < MIN_QUERY_CHARS) {
      setResults([]);
      setSearching(false);
      setHasSearched(false);
      setActiveIdx(-1);
      return;
    }
    let active = true;
    setSearching(true);
    const timer = window.setTimeout(async () => {
      try {
        const res = await searchAddress({
          scheme,
          text: normalized.slice(0, QUERY_MAX_CHARS),
        });
        if (!active) return;
        setResults(res.results);
        setHasSearched(true);
        setActiveIdx(-1);
        setRateLimitError(null);
      } catch (err) {
        if (!active) return;
        if (isRateLimited(err)) {
          setRateLimitError(RATE_LIMIT_MESSAGE);
          return;
        }
        if (isUnavailableOrNetwork(err)) {
          recordAddressSearchFailure();
          failedRef.current();
          return;
        }
        setResults([]);
        setHasSearched(true);
      } finally {
        if (active) setSearching(false);
      }
    }, SUGGEST_DEBOUNCE_MS);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [open, query, scheme]);

  // Cuộn dòng đang chọn bằng bàn phím vào vùng nhìn thấy.
  useEffect(() => {
    if (!open || activeIdx < 0) return;
    listRef.current?.querySelector<HTMLElement>('[data-active="true"]')?.scrollIntoView?.({ block: "nearest" });
  }, [activeIdx, open]);

  const pick = useCallback(
    async (item: AddressSearchItem, index: number) => {
      const seq = ++placeSeqRef.current;
      setActiveIdx(index);
      setSelectedRef(item.ref);
      setPickedPlace(null);
      setLoadingPlace(true);
      setRateLimitError(null);
      try {
        const place = await getAddressPlace({ scheme, ref: item.ref });
        if (placeSeqRef.current !== seq) return;
        setPickedPlace(place);
      } catch (err) {
        if (placeSeqRef.current !== seq) return;
        setSelectedRef(null);
        if (isRateLimited(err)) {
          setRateLimitError(RATE_LIMIT_MESSAGE);
          return;
        }
        if (isUnavailableOrNetwork(err)) {
          recordAddressSearchFailure();
          failedRef.current();
          return;
        }
      } finally {
        if (placeSeqRef.current === seq) setLoadingPlace(false);
      }
    },
    [scheme]
  );

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    // Luôn đóng hộp ngay ở lần bấm Escape đầu tiên và trả tiêu điểm về nút mở (SHOP-3-04 AC6, G5).
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      onClose();
      return;
    }
    const count = results.length;
    if ((e.key === "ArrowDown" || e.key === "ArrowUp") && count > 0) {
      e.preventDefault();
      setActiveIdx((cur) => (e.key === "ArrowDown" ? (cur >= count - 1 ? 0 : cur + 1) : cur <= 0 ? count - 1 : cur - 1));
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (count > 0) {
        const idx = activeIdx >= 0 ? activeIdx : 0;
        const target = results[idx];
        if (target) void pick(target, idx);
      }
    }
  }

  const normalizedLen = query.trim().replace(/\s+/g, " ").length;
  const showList = results.length > 0;
  const activeId = showList && activeIdx >= 0 ? `${baseId}-opt-${activeIdx}` : undefined;

  return (
    <FullscreenSheet
      open={open}
      onClose={onClose}
      title="Tìm địa chỉ giao hàng"
      closeLabel="Đóng, quay lại nhập tay"
      initialFocusRef={inputRef}
      footer={
        <div className={s.footer}>
          <div className={cx(s.chosen, !pickedPlace && !loadingPlace && s.chosenEmpty)} aria-live="polite">
            {loadingPlace ? (
              <>
                <Spinner size={18} />
                <span>Đang lấy chi tiết địa chỉ…</span>
              </>
            ) : pickedPlace ? (
              <>
                <Icon name="map-pin" size={18} />
                <div className={s.chosenText}>
                  <span className={s.chosenMain}>{pickedPlace.street}</span>
                  {pickedPlace.display && pickedPlace.display !== pickedPlace.street ? (
                    <span className={s.chosenSub}>{pickedPlace.display}</span>
                  ) : null}
                </div>
              </>
            ) : (
              <>
                <Icon name="map-pin" size={18} />
                <span>Gõ ít nhất 2 ký tự rồi chọn một địa chỉ gợi ý.</span>
              </>
            )}
          </div>
          <div className={s.actions}>
            <Button
              size="lg"
              fullWidth
              disabled={!pickedPlace || loadingPlace}
              onClick={() => {
                if (!pickedPlace) return;
                onConfirm({ street: pickedPlace.street, suggestion: pickedPlace.suggestion });
              }}
            >
              Dùng địa chỉ này
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
              type="text"
              inputMode="search"
              enterKeyHint="search"
              role="combobox"
              className={s.input}
              aria-label="Tìm địa chỉ"
              aria-describedby={MAP_NOTICE_ID}
              aria-expanded={showList}
              aria-controls={showList ? listId : undefined}
              aria-autocomplete="list"
              aria-activedescendant={activeId}
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
              maxLength={QUERY_MAX_CHARS}
              placeholder="Ví dụ: 12 Trần Hưng Đạo"
              value={query}
              onChange={(e) => {
                placeSeqRef.current += 1;
                setQuery(e.target.value);
                setSelectedRef(null);
                setPickedPlace(null);
                setLoadingPlace(false);
                setRateLimitError(null);
              }}
              onKeyDown={onKeyDown}
            />
            {query ? (
              <button
                type="button"
                className={s.clear}
                aria-label="Xoá chữ"
                onClick={() => {
                  placeSeqRef.current += 1;
                  setQuery("");
                  setResults([]);
                  setHasSearched(false);
                  setActiveIdx(-1);
                  setSelectedRef(null);
                  setPickedPlace(null);
                  setLoadingPlace(false);
                  setRateLimitError(null);
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
        </div>

        <div className={s.resultsArea}>
          {rateLimitError ? (
            <div className={s.bannerWrap}>
              <Banner tone="warn" live="assertive">
                {rateLimitError}
              </Banner>
            </div>
          ) : null}

          {searching ? (
            <div className={s.state} role="status" aria-busy="true">
              <Spinner size={18} />
              <span>Đang tìm địa chỉ…</span>
            </div>
          ) : showList ? (
            <ul id={listId} ref={listRef} role="listbox" aria-label="Gợi ý địa chỉ" className={s.list}>
              {results.map((item, i) => {
                const isSelected = selectedRef === item.ref;
                const isActive = i === activeIdx;
                return (
                  <li
                    key={item.ref}
                    id={`${baseId}-opt-${i}`}
                    role="option"
                    aria-selected={isSelected}
                    data-active={isActive || undefined}
                    className={cx(s.option, isActive && s.optionActive, isSelected && s.optionSelected)}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => void pick(item, i)}
                  >
                    <span className={s.optionIcon}>
                      <Icon name="map-pin" size={18} />
                    </span>
                    <span className={s.optionText}>
                      <span className={s.optionMain}>{item.title}</span>
                      {item.subtitle ? <span className={s.optionSub}>{item.subtitle}</span> : null}
                    </span>
                    {isSelected ? (
                      <span className={s.optionCheck}>
                        <Icon name="check" size={18} />
                      </span>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : hasSearched && normalizedLen >= MIN_QUERY_CHARS && !rateLimitError ? (
            <div className={s.state} role="status">
              <p className={s.stateTitle}>Không thấy địa chỉ phù hợp</p>
              <p className={s.stateSub}>Bạn thử gõ ngắn hơn (số nhà + tên đường), hoặc đóng hộp và gõ trực tiếp.</p>
            </div>
          ) : normalizedLen < MIN_QUERY_CHARS && !rateLimitError ? (
            <div className={s.state}>
              <p className={s.stateSub}>
                Đang tìm theo {scheme === "legacy" ? "địa chỉ cũ (trước sắp xếp)" : "địa chỉ mới (sau sắp xếp 01/07/2025)"}. Nhập từ 2 ký tự để xem gợi ý.
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </FullscreenSheet>
  );
}
