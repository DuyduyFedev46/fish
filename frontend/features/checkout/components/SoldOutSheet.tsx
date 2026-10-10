"use client";

import Button from "@/components/ui/Button";
import { BottomSheet } from "@/components/ui/Sheet";
import { formatQty } from "@/lib/quantity";
import { contactTarget } from "@/components/shopLinks";
import s from "./SoldOutSheet.module.css";

export type SoldOutLine = {
  itemCode: string;
  name: string;
  unit: "kg" | "combo";
  /** Số khách đặt (số của chính khách, không phải số tồn). */
  qty: number;
  /** Mức tối thiểu của món. */
  minQty: number;
  /** out: hết hẳn. short: còn nhưng không đủ số khách đặt. */
  level: "out" | "short";
  /** Đã bấm "Đổi thành …" cho dòng này. */
  changed: boolean;
};

export interface SoldOutSheetProps {
  open: boolean;
  lines: SoldOutLine[];
  hotline?: string;
  /** Đang gửi lại đơn. */
  busy?: boolean;
  onChangeToMin: (itemCode: string) => void;
  onUpdateAndRetry: () => void;
  onBackToCart: () => void;
}

/**
 * C3: "Một số món vừa hết hàng" (BR-BH-24). Điện thoại là bottom sheet, máy tính là hộp thoại. Không bao giờ hiện số kg còn,
 * không in chuỗi lỗi thô của máy chủ. Đóng bằng Esc hoặc lớp phủ = Quay lại giỏ hàng (không xoá gì).
 */
export default function SoldOutSheet({
  open,
  lines,
  hotline,
  busy = false,
  onChangeToMin,
  onUpdateAndRetry,
  onBackToCart,
}: SoldOutSheetProps) {
  return (
    <BottomSheet
      open={open}
      onClose={onBackToCart}
      title="Một số món vừa hết hàng"
      description="Có khách vừa đặt trước bạn."
      icon={{ name: "warning", tone: "warn" }}
      closeLabel="Đóng thông báo hết hàng"
      actions={
        <>
          <Button size="lg" fullWidth loading={busy} loadingText="Đang đặt…" onClick={onUpdateAndRetry}>
            Cập nhật giỏ và đặt lại
          </Button>
          <Button variant="secondary" size="lg" fullWidth disabled={busy} onClick={onBackToCart}>
            Quay lại giỏ hàng
          </Button>
        </>
      }
    >
      <ul className={s.list}>
        {lines.map((l) => {
          const atMin = l.qty <= l.minQty;
          const canReduce = l.level === "short" && !atMin;
          return (
            <li key={l.itemCode} className={s.item}>
              <div className={s.text}>
                <span className={s.name}>{l.name}</span>
                {l.level === "out" || (l.level === "short" && atMin) ? (
                  <span className={s.note}>{l.level === "out" ? "Đã hết" : "Không đủ hàng"} · sẽ bỏ khỏi đơn</span>
                ) : l.changed ? (
                  <span className={s.noteGood}>
                    Đã đổi thành {formatQty(l.minQty)} {l.unit}
                  </span>
                ) : (
                  <span className={s.note}>
                    Bạn đặt {formatQty(l.qty)} {l.unit} · không đủ hàng
                  </span>
                )}
              </div>
              {canReduce && !l.changed ? (
                <Button variant="outline" size="sm" disabled={busy} onClick={() => onChangeToMin(l.itemCode)}>
                  Đổi thành {formatQty(l.minQty)} {l.unit}
                </Button>
              ) : null}
              {l.level === "out" ? (
                <Button
                  variant="secondary"
                  size="sm"
                  href={contactTarget(hotline)}
                  aria-label={`Liên hệ Cá Về hỏi hàng ${l.name}`}
                >
                  Liên hệ chúng tôi
                </Button>
              ) : null}
            </li>
          );
        })}
      </ul>
    </BottomSheet>
  );
}
