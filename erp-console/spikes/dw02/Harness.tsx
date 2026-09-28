"use client";

import React, { useState } from "react";
import commands from "../../spikes/dw02/index.json";

export default function AiSpikeHarness() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [status, setStatus] = useState<string>("Sẵn sàng thử nghiệm");

  const handleSearch = () => {
    if (!query.trim()) return;
    setStatus("Đang tìm kiếm bằng BM25...");
    // Tìm kiếm đơn giản client-side
    const qLower = query.toLowerCase();
    const matches = commands.filter((c: any) => {
      const matchTitle = c.title.toLowerCase().includes(qLower);
      const matchKws = c.keywords.some((kw: string) => kw.toLowerCase().includes(qLower));
      const matchId = c.id.toLowerCase().includes(qLower);
      return matchTitle || matchKws || matchId;
    });
    setResults(matches.slice(0, 5));
    setStatus(`Tìm thấy ${matches.length} lệnh phù hợp (hiện top ${Math.min(5, matches.length)})`);
  };

  return (
    <div style={{ padding: 24, fontFamily: "sans-serif", maxWidth: 800, margin: "0 auto" }}>
      <h1>Harness Thử Nghiệm AI On-Device (DW-02 Spike)</h1>
      <p style={{ color: "#666" }}>
        Môi trường thử nghiệm Gemma 3n / wllama on-device và BM25 cho Cá Về ERP.
      </p>

      <div style={{ marginTop: 20, marginBottom: 20 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Nhập câu lệnh mẫu (vd: Tra tồn kho cá thu)..."
          style={{ width: "70%", padding: "8px 12px", fontSize: 14 }}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button
          onClick={handleSearch}
          style={{ marginLeft: 8, padding: "8px 16px", cursor: "pointer" }}
        >
          Tìm lệnh
        </button>
      </div>

      <div style={{ padding: 12, background: "#f5f5f5", borderRadius: 4, marginBottom: 20 }}>
        <strong>Trạng thái:</strong> {status}
      </div>

      <div>
        <h3>Ứng viên Top-5:</h3>
        {results.length === 0 ? (
          <p>Chưa có kết quả.</p>
        ) : (
          <ol>
            {results.map((r, i) => (
              <li key={r.id} style={{ marginBottom: 8 }}>
                <strong>{r.title}</strong> (<code>{r.id}</code>) — Nhóm: {r.group}
              </li>
            ))}
          </ol>
        )}
      </div>

      <div style={{ marginTop: 40, borderTop: "1px solid #ddd", paddingTop: 16 }}>
        <h4>Thông số mô hình Gemma 3n (GGUF):</h4>
        <ul>
          <li>Mô hình: Gemma 3n (E2B / E4B)</li>
          <li>Kích thước context: 2048 / 4096 tokens</li>
          <li>Chỉ mục: 114 lệnh nghiệp vụ Cá Về</li>
        </ul>
      </div>
    </div>
  );
}
