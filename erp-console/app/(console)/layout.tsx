import { ConsoleGate } from "@/features/auth/components/ConsoleGate";
import { ConsoleCodeFinder } from "@/features/lookup/ConsoleCodeFinder";
import { ToastProvider } from "@/shared/ui/overlay/Toast";

// Mọi route trong (console)/ phải đăng nhập + có Group; ConsoleGate vẽ Shell 2 cột với menu theo quyền.
// Không còn cột phải: AI nằm TRONG trang (thanh AI ở danh sách, khối Trợ lý AI ở chi tiết) — layout không ghép gì của
// features/inventory hay features/ai nữa.
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ConsoleCodeFinder>
      <ConsoleGate>
        <ToastProvider>{children}</ToastProvider>
      </ConsoleGate>
    </ConsoleCodeFinder>
  );
}
