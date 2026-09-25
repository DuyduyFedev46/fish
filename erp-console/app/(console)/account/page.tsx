import { AccountScreen } from "@/features/auth/components/AccountScreen";

// S46/S47: Tài khoản của tôi — ai đã đăng nhập và có Group đều mở được (ConsoleGate đã chặn chưa đăng nhập / no-role).
export default function Page() {
  return <AccountScreen />;
}
