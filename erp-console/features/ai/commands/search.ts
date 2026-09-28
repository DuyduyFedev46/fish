// Tìm kiếm ứng viên lệnh AI bằng BM25 tiếng Việt bỏ dấu (DW-02, DW-09, 02b §5.2).
// Tiêu chí: recall@5 >= 95%, không cần model, chỉ mục lưu trong RAM.

import type { AiCommandIndexItem } from "../types";

export function removeVietnameseDiacritics(str: string): string {
  if (!str) return "";
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

export function tokenize(text: string): string[] {
  const clean = removeVietnameseDiacritics(text);
  return clean
    .split(/[^a-z0-9]+/i)
    .filter((w) => w.length > 1);
}

export class BM25Index {
  private docs: AiCommandIndexItem[];
  private k1: number;
  private b: number;
  private docCount: number;
  private docTokens: string[][] = [];
  private docLengths: number[] = [];
  private avgDocLength = 0;
  private termDocFreq: Map<string, number> = new Map();

  constructor(docs: AiCommandIndexItem[], k1 = 1.2, b = 0.75) {
    this.docs = docs;
    this.k1 = k1;
    this.b = b;
    this.docCount = docs.length;
    this.init();
  }

  private init(): void {
    let totalLength = 0;
    this.docs.forEach((doc) => {
      const text = [
        doc.title || "",
        ...(doc.keywords || []),
        doc.id ? doc.id.replace(/\./g, " ") : "",
        doc.group || "",
      ].join(" ");

      const tokens = tokenize(text);
      this.docTokens.push(tokens);
      this.docLengths.push(tokens.length);
      totalLength += tokens.length;

      const uniqueTokens = new Set(tokens);
      uniqueTokens.forEach((t) => {
        this.termDocFreq.set(t, (this.termDocFreq.get(t) || 0) + 1);
      });
    });

    this.avgDocLength = this.docCount > 0 ? totalLength / this.docCount : 0;
  }

  search(
    query: string,
    options?: { screen?: string; limit?: number; minScore?: number; margin?: number }
  ): SearchResult {
    const queryTokens = tokenize(query);
    if (queryTokens.length === 0 || this.docCount === 0) {
      return { candidates: [], top1: null, skipTurnA: false, hasMatch: false };
    }

    const currentScreen = options?.screen;
    const limit = Math.min(Math.max(1, options?.limit ?? 3), 5); // tối đa 5 ứng viên theo DW-09-AC1
    const minScore = options?.minScore ?? 0.1;
    const margin = options?.margin ?? 0.2;

    const scored: Array<{ command: AiCommandIndexItem; score: number }> = [];

    this.docs.forEach((doc, idx) => {
      const tokens = this.docTokens[idx];
      const length = this.docLengths[idx];
      let score = 0;

      const termFreq = new Map<string, number>();
      tokens.forEach((t) => termFreq.set(t, (termFreq.get(t) || 0) + 1));

      queryTokens.forEach((term) => {
        const tf = termFreq.get(term) || 0;
        if (tf === 0) return;

        const df = this.termDocFreq.get(term) || 0;
        const idf = Math.log((this.docCount - df + 0.5) / (df + 0.5) + 1);

        const numerator = tf * (this.k1 + 1);
        const denominator = tf + this.k1 * (1 - this.b + this.b * (length / (this.avgDocLength || 1)));

        score += idf * (numerator / denominator);
      });

      // Ưu tiên màn hình hiện tại (DW-09 §5.2)
      if (currentScreen && doc.screens && doc.screens.includes(currentScreen)) {
        score *= 1.35;
      }

      if (score >= minScore) {
        scored.push({ command: doc, score });
      }
    });

    scored.sort((a, b) => b.score - a.score);

    const candidates = scored.slice(0, limit);
    if (candidates.length === 0) {
      return { candidates: [], top1: null, skipTurnA: false, hasMatch: false };
    }

    const top1 = candidates[0].command;
    let skipTurnA = false;

    if (candidates.length === 1) {
      skipTurnA = true;
    } else if (candidates.length >= 2) {
      const diff = candidates[0].score - candidates[1].score;
      if (diff >= margin) {
        skipTurnA = true;
      }
    }

    return {
      candidates,
      top1,
      skipTurnA,
      hasMatch: true,
    };
  }
}

export type SearchCandidate = {
  command: AiCommandIndexItem;
  score: number;
};

export type SearchResult = {
  candidates: SearchCandidate[];
  top1: AiCommandIndexItem | null;
  skipTurnA: boolean;
  hasMatch: boolean;
};

export function searchCommands(
  query: string,
  commands: AiCommandIndexItem[],
  options?: { screen?: string; limit?: number; minScore?: number; margin?: number }
): SearchResult {
  const index = new BM25Index(commands);
  return index.search(query, options);
}
