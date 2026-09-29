import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { CategoriesScreen } from "@/features/content/components/CategoriesScreen";

export default function CategoriesPage() {
  return (
    <ViewGuard view="content-categories">
      <CategoriesScreen />
    </ViewGuard>
  );
}
