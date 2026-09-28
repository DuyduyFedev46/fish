/**
 * Spike DW-02: Đo recall@3, recall@5 và margin của BM25 bỏ dấu tiếng Việt trên chỉ mục lệnh thật.
 * Chạy: node erp-console/spikes/dw02/recall.mjs
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 1. Hàm bỏ dấu tiếng Việt và chuẩn hoá token
function removeVietnameseDiacritics(str) {
  if (!str) return "";
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

function tokenize(text) {
  const clean = removeVietnameseDiacritics(text);
  return clean
    .split(/[^a-z0-9]+/i)
    .filter((w) => w.length > 1);
}

// 2. Lớp BM25 đơn giản tối ưu cho tra cứu lệnh
class BM25Index {
  constructor(docs, k1 = 1.2, b = 0.75) {
    this.docs = docs;
    this.k1 = k1;
    this.b = b;
    this.docCount = docs.length;
    this.docTokens = [];
    this.docLengths = [];
    this.avgDocLength = 0;
    this.termDocFreq = new Map();

    this.init();
  }

  init() {
    let totalLength = 0;
    this.docs.forEach((doc, idx) => {
      // Kết hợp id, title, group và keywords thành text văn bản
      const text = [
        doc.title || "",
        ...(doc.keywords || []),
        doc.id ? doc.id.replace(/\./g, " ") : "",
        doc.group || ""
      ].join(" ");

      const tokens = tokenize(text);
      this.docTokens.push(tokens);
      this.docLengths.push(tokens.length);
      totalLength += tokens.length;

      const uniqueTokens = new Set(tokens);
      for (const token of uniqueTokens) {
        this.termDocFreq.set(token, (this.termDocFreq.get(token) || 0) + 1);
      }
    });

    this.avgDocLength = this.docCount > 0 ? totalLength / this.docCount : 0;
  }

  search(query, topK = 5) {
    const qTokens = tokenize(query);
    if (qTokens.length === 0) return [];

    const scores = new Array(this.docCount).fill(0);

    for (const qTerm of qTokens) {
      const df = this.termDocFreq.get(qTerm) || 0;
      if (df === 0) continue;

      // IDF
      const idf = Math.log(1 + (this.docCount - df + 0.5) / (df + 0.5));

      for (let i = 0; i < this.docCount; i++) {
        const tokens = this.docTokens[i];
        let tf = 0;
        for (const t of tokens) {
          if (t === qTerm) tf++;
        }
        if (tf === 0) continue;

        const docLen = this.docLengths[i];
        const denom = tf + this.k1 * (1 - this.b + this.b * (docLen / this.avgDocLength));
        const termScore = idf * ((tf * (this.k1 + 1)) / denom);
        scores[i] += termScore;
      }
    }

    const scoredDocs = [];
    for (let i = 0; i < this.docCount; i++) {
      if (scores[i] > 0) {
        scoredDocs.push({
          doc: this.docs[i],
          score: scores[i]
        });
      }
    }

    scoredDocs.sort((a, b) => b.score - a.score);
    return scoredDocs.slice(0, topK);
  }
}

// 3. Nạp dữ liệu và chạy đánh giá
const indexPath = path.join(__dirname, "index.json");
const queriesPath = path.join(
  __dirname,
  "../../../doc/features/2026-09-28-ai-digital-worker/research/cau-mau-50.json"
);

if (!fs.existsSync(indexPath)) {
  console.error("Thiếu file index.json tại:", indexPath);
  process.exit(1);
}
if (!fs.existsSync(queriesPath)) {
  console.error("Thiếu file cau-mau-50.json tại:", queriesPath);
  process.exit(1);
}

const commands = JSON.parse(fs.readFileSync(indexPath, "utf8"));
const queries = JSON.parse(fs.readFileSync(queriesPath, "utf8"));

const bm25 = new BM25Index(commands);

let hitAt1 = 0;
let hitAt3 = 0;
let hitAt5 = 0;
let totalMargin = 0;
let marginCount = 0;

const misses = [];

queries.forEach((q) => {
  const results = bm25.search(q.query, 5);
  const ids = results.map((r) => r.doc.id);

  if (ids.length > 0 && ids[0] === q.expected_id) {
    hitAt1++;
  }
  if (ids.slice(0, 3).includes(q.expected_id)) {
    hitAt3++;
  }
  if (ids.slice(0, 5).includes(q.expected_id)) {
    hitAt5++;
  } else {
    misses.push({
      query: q.query,
      expected: q.expected_id,
      got: ids
    });
  }

  if (results.length >= 2) {
    const s1 = results[0].score;
    const s2 = results[1].score;
    if (s1 > 0) {
      const margin = (s1 - s2) / s1;
      totalMargin += margin;
      marginCount++;
    }
  }
});

const recallAt1 = (hitAt1 / queries.length) * 100;
const recallAt3 = (hitAt3 / queries.length) * 100;
const recallAt5 = (hitAt5 / queries.length) * 100;
const avgMargin = marginCount > 0 ? (totalMargin / marginCount) : 0;

console.log("=== KẾT QUẢ ĐO RECALL BM25 SPIKE DW-02 ===");
console.log(`Tổng số câu thử nghiệm: ${queries.length}`);
console.log(`Tổng số lệnh trong chỉ mục: ${commands.length}`);
console.log(`Recall@1: ${recallAt1.toFixed(1)}% (${hitAt1}/${queries.length})`);
console.log(`Recall@3: ${recallAt3.toFixed(1)}% (${hitAt3}/${queries.length})`);
console.log(`Recall@5: ${recallAt5.toFixed(1)}% (${hitAt5}/${queries.length})`);
console.log(`Margin trung bình top-1 / top-2: ${avgMargin.toFixed(3)}`);

if (misses.length > 0) {
  console.log("\nCác câu chưa lọt top-5:");
  misses.forEach((m) => {
    console.log(`- "${m.query}" -> expected ${m.expected}, got: [${m.got.join(", ")}]`);
  });
} else {
  console.log("\n100% câu thử nghiệm lọt vào Top-5!");
}

// Trả về mã thoát dựa trên tiêu chí DW-02-AC3: recall@5 >= 95%
if (recallAt5 >= 95.0) {
  console.log("\n>> TIÊU CHÍ ĐẠT: Recall@5 >= 95% (DW-02-AC3 PASS)");
  process.exit(0);
} else {
  console.error("\n>> TIÊU CHÍ KHÔNG ĐẠT: Recall@5 < 95%");
  process.exit(1);
}
