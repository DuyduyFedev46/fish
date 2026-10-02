import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ItemForm } from "@/features/catalog/components/ItemForm";

// ED-30 (F1k, F1m): thêm mặt hàng /catalog/new/ và thêm combo /catalog/new/?type=BUNDLE. Cần catalog.add_item (ItemForm tự chặn người thiếu quyền).
export default function Page() {
  return (
    <ViewGuard view="catalog">
      <Suspense fallback={null}>
        <ItemForm />
      </Suspense>
    </ViewGuard>
  );
}
