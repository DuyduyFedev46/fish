"use client";

// Đưa bộ tra mã vào ⌘K cho cả console. Là client component vì `codeFinder` chứa hàm, mà layout (server) không truyền hàm qua ranh giới được.
import { CodeFinderProvider } from "@/shared/ui/shell/CodeFinderContext";
import { codeFinder } from "./codeFinder";

export function ConsoleCodeFinder({ children }: { children: React.ReactNode }) {
  return <CodeFinderProvider finder={codeFinder}>{children}</CodeFinderProvider>;
}
