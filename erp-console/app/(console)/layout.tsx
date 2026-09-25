import { ConsoleGate } from "@/features/auth/components/ConsoleGate";
import { ActivityFeed } from "@/features/inventory/components/ActivityFeed";

// Mọi route trong (console)/ phải đăng nhập + có Group; ConsoleGate vẽ Shell với menu theo quyền.
// Tầng app ghép nội dung cột phải từ các module (features/auth không import module khác):
// tab "Hoạt động" = sổ kho của module inventory (S8).
export default function Layout({ children }: { children: React.ReactNode }) {
  return <ConsoleGate activity={<ActivityFeed />}>{children}</ConsoleGate>;
}
