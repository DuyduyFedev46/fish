import { ConsoleGate } from "@/features/auth/components/ConsoleGate";
import { ActivityFeed } from "@/features/inventory/components/ActivityFeed";
import { AiAssistantGate } from "@/features/ai/components/AiAssistantGate";

// Mọi route trong (console)/ phải đăng nhập + có Group; ConsoleGate vẽ Shell với menu theo quyền.
// Tầng app ghép nội dung cột phải từ các module (features/auth không import module khác):
// tab "Hoạt động" = sổ kho của module inventory (S8).
// Tab "Trợ lý" = CÁNH CỔNG MỎNG của module AI (Phụ lục C.2 dòng 2): import tĩnh CHỈ AiAssistantGate
// (gọi /api/ai/status/ + cờ đồng ý; tắt/lỗi → null → RightRail hiện khung chờ); tấm nặng nạp động
// ssr:false bên trong gate khi `ai_enabled` VÀ đã đồng ý. KHÔNG import gì khác của features/ai ở đây.
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ConsoleGate activity={<ActivityFeed />} assistant={<AiAssistantGate />}>
      {children}
    </ConsoleGate>
  );
}
