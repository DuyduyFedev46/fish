"use client";

// Mẫu form (UI-RULES §6): lần gửi đầu cố ý lỗi để thấy alert đỏ + nút "Thử lại" + giá trị còn nguyên; lần sau thành công.
import { useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { useSubmit } from "@/shared/ui/form/useSubmit";

export default function FormDemo() {
  const [qty, setQty] = useState("12,5");
  const [note, setNote] = useState("Cá thu loại 1");
  const [done, setDone] = useState(false);
  const attempts = useRef(0);
  const sub = useSubmit(
    async () => {
      attempts.current += 1;
      await new Promise((r) => setTimeout(r, 400));
      if (attempts.current === 1) throw new ApiError("Chưa lưu được vì mạng chập chờn. Dữ liệu của bạn vẫn còn đây.", 500);
    },
    { onSuccess: () => setDone(true) }
  );

  return (
    <FormPage
      title="Nhập thử một phiếu"
      back={{ href: "/dev-patterns/", label: "Mẫu trang chi tiết" }}
      alert={sub.error ? <FormAlert>{sub.error}</FormAlert> : undefined}
      onSubmit={() => void sub.submit()}
      primaryText="Lưu phiếu"
      submitting={sub.submitting}
      failed={sub.failed}
      secondary={{ label: "Huỷ", onClick: () => history.back() }}
    >
      <Field label="Số lượng" required unit="kg" type="number" value={qty} onChange={setQty} name="qty" />
      <Field label="Ghi chú" as="textarea" value={note} onChange={setNote} name="note" />
      <SummaryBlock
        label="Tóm tắt"
        rows={[
          { label: "Số dòng", value: "1", num: true },
          { label: "Tổng số lượng", value: `${qty} kg`, num: true, strong: true },
        ]}
      />
      {done && <p role="status" data-saved>Đã lưu phiếu.</p>}
    </FormPage>
  );
}
