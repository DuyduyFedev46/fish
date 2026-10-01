import { ConsoleGate } from "@/features/auth/components/ConsoleGate";
import { NotFoundInApp } from "@/features/auth/components/AppStates";

// 404 nằm TRONG khung app (UI-RULES §7): có menu để đi tiếp. Người chưa đăng nhập được ConsoleGate chuyển về trang đăng nhập.
export default function NotFound() {
  return (
    <ConsoleGate>
      <NotFoundInApp />
    </ConsoleGate>
  );
}
