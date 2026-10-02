import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ReceiveBatchesForm } from "@/features/purchasing/components/ReceiveBatchesForm";

// F1a Nhập lô tại cảng: /purchasing/new/. Form tự kiểm quyền thêm phiếu nhập (add_purchasereceipt).
export default function Page() {
  return (
    <ViewGuard view="purchasing">
      <ReceiveBatchesForm />
    </ViewGuard>
  );
}
