import { Suspense } from "react";
import ItemDetailScreen from "@/features/catalog/components/ItemDetailScreen";

export default function ItemDetailPage() {
  return (
    <Suspense fallback={null}>
      <ItemDetailScreen />
    </Suspense>
  );
}
