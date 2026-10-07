"use client";

// Chỗ nhận `CodeFinder` cho ⌘K (Lô 17b H1). `shared/` không import module tính năng, nên tầng app (app/(console)/layout.tsx) đưa bộ tra mã
// vào đây; không có Provider thì ⌘K chỉ nhảy menu như trước.
import { createContext, useContext } from "react";
import type { CodeFinder } from "@/shared/lib/codeLookup";

const Ctx = createContext<CodeFinder | null>(null);

export function CodeFinderProvider({ finder, children }: { finder: CodeFinder; children: React.ReactNode }) {
  return <Ctx.Provider value={finder}>{children}</Ctx.Provider>;
}

export function useCodeFinder(): CodeFinder | null {
  return useContext(Ctx);
}
