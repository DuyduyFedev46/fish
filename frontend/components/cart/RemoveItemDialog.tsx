"use client";

import { useRef } from "react";
import type { SaleUnit } from "@/lib/types";
import { formatQty } from "@/lib/quantity";
import Button from "../ui/Button";
import Dialog from "../ui/Dialog";

export interface RemoveItemDialogProps {
  /** Món đang hỏi bỏ; null thì đóng. */
  item: { name: string; unit: SaleUnit; minQty: number } | null;
  onKeep: () => void;
  onRemove: () => void;
}

/** B2: "Bỏ … khỏi giỏ?". Bớt dưới mức tối thiểu hoặc bấm thùng rác đều qua hộp này (UI-RULES §1.2, §5.4). */
export default function RemoveItemDialog({ item, onKeep, onRemove }: RemoveItemDialogProps) {
  // Giữ món cuối cùng để chữ không đổi trong lúc hộp thoại chạy hiệu ứng đóng.
  const last = useRef(item);
  if (item) last.current = item;
  const shown = item ?? last.current;
  return (
    <Dialog
      open={item !== null}
      onClose={onKeep}
      title={shown ? `Bỏ ${shown.name} khỏi giỏ?` : "Bỏ món khỏi giỏ?"}
      description={
        shown
          ? `Mỗi món mua tối thiểu ${formatQty(shown.minQty)} ${shown.unit}. Bớt nữa sẽ bỏ món này khỏi giỏ.`
          : undefined
      }
      actions={
        <>
          <Button variant="secondary" fullWidth data-autofocus="" onClick={onKeep}>
            Giữ lại
          </Button>
          <Button variant="danger" fullWidth onClick={onRemove}>
            Bỏ khỏi giỏ
          </Button>
        </>
      }
    />
  );
}
