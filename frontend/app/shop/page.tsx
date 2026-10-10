import { Suspense } from "react";
import CatalogScreen from "@/features/catalog/components/CatalogScreen";

export default function ShopCatalogPage() {
  return (
    <Suspense fallback={null}>
      <CatalogScreen />
    </Suspense>
  );
}
