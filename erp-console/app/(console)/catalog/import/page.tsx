"use client";

import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ItemImportScreen } from "@/features/catalog/components/ItemImportScreen";

export default function CatalogImportPage() {
  return (
    <ViewGuard view="catalog">
      <ItemImportScreen />
    </ViewGuard>
  );
}
