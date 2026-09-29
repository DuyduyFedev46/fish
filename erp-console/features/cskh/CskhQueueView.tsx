"use client";

import React, { useState, useEffect, useCallback } from "react";
import { fetchCskhQueue, searchCskh } from "./api";
import type {
  CskhQueueItem,
  CskhSearchResultItem,
  QueueTabKey,
} from "./types";
import { QUEUE_TABS } from "./types";
import { CskhCallModal } from "./CskhCallModal";
import s from "./cskh.module.css";

export function CskhQueueView() {
  const [activeTab, setActiveTab] = useState<QueueTabKey>("DEFAULT");
  const [items, setItems] = useState<CskhQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<CskhSearchResultItem[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Modal state
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null);

  const loadQueue = useCallback(async (tabKey: QueueTabKey) => {
    setLoading(true);
    setError(null);
    try {
      const tab = QUEUE_TABS.find((t) => t.key === tabKey);
      const res = await fetchCskhQueue({ state: tab?.stateParam });
      setItems(res.results);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể tải hàng chờ CSKH.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue(activeTab);
  }, [activeTab, loadQueue]);

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }

    setSearching(true);
    setSearchError(null);
    try {
      const res = await searchCskh(q);
      setSearchResults(res.results);
      if (res.results.length === 0) {
        setSearchError("Không tìm thấy đơn hàng nào phù hợp.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi khi tìm kiếm.";
      setSearchError(msg);
      setSearchResults(null);
    } finally {
      setSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setSearchResults(null);
    setSearchError(null);
  };

  return (
    <div className={s.container}>
      {/* Header */}
      <div className={s.header}>
        <div className={s.titleArea}>
          <h1 className={s.title}>Gọi xác nhận đơn</h1>
          <p className={s.subtitle}>
            Hàng chờ CSKH gọi khách xác nhận trước khi kho bắt đầu soạn hàng.
          </p>
        </div>
        <div className={s.headerActions}>
          <button
            type="button"
            className={s.refreshBtn}
            onClick={() => loadQueue(activeTab)}
            disabled={loading}
          >
            <span>🔄</span>
            <span>{loading ? "Đang tải..." : "Tải lại"}</span>
          </button>
        </div>
      </div>

      {/* Search Bar (POST body) */}
      <div className={s.searchCard}>
        <form onSubmit={handleSearchSubmit} className={s.searchForm}>
          <input
            type="text"
            className={s.searchInput}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo số điện thoại (≥ 9 chữ số) hoặc mã đơn hàng..."
          />
          <button
            type="submit"
            className={s.searchSubmitBtn}
            disabled={searching || !searchQuery.trim()}
          >
            {searching ? "Đang tìm..." : "Tìm kiếm"}
          </button>
          {searchResults !== null && (
            <button
              type="button"
              className={s.btnSecondary}
              onClick={handleClearSearch}
            >
              Xoá tìm
            </button>
          )}
        </form>
        <div className={s.searchHint}>
          Tra cứu nhanh khi khách gọi ngược lại. Số điện thoại chỉ tìm khi nhập đủ từ 9 chữ số.
        </div>

        {searchError && (
          <div style={{ marginTop: "10px", color: "#dc2626", fontSize: "0.875rem" }}>
            {searchError}
          </div>
        )}

        {searchResults && searchResults.length > 0 && (
          <div className={s.searchResultsBox}>
            <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "#4b5563" }}>
              Kết quả tìm kiếm ({searchResults.length}):
            </div>
            {searchResults.map((item) => (
              <div key={item.note_id} className={s.searchResultRow}>
                <div>
                  <strong>{item.order_code}</strong> · <span>{item.status_label}</span>
                  {item.in_scope ? (
                    <span style={{ marginLeft: "8px", color: "#111827" }}>
                      — {item.customer_name} ({item.phone})
                    </span>
                  ) : (
                    <span style={{ marginLeft: "8px", color: "#6b7280" }}>
                      — SĐT: {item.phone_masked} (ngoài phạm vi gọi)
                    </span>
                  )}
                </div>
                {item.in_scope ? (
                  <button
                    type="button"
                    className={s.searchResultAction}
                    onClick={() => setSelectedNoteId(item.note_id)}
                  >
                    Mở xử lý →
                  </button>
                ) : (
                  <span style={{ fontSize: "0.75rem", color: "#9ca3af" }}>Chỉ xem</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className={s.tabsBar}>
        {QUEUE_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`${s.tabBtn} ${activeTab === tab.key ? s.tabActive : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error alert */}
      {error && (
        <div className={`${s.alertBox} ${s.alertError}`}>
          {error}
        </div>
      )}

      {/* CS-09: Guidance D5 banner for REFUND_CALL tab */}
      {activeTab === "REFUND_CALL" && (
        <div className={`${s.alertBox} ${s.alertWarn}`}>
          💡 <strong>Hướng dẫn CSKH:</strong> Không ghi số tài khoản khách vào hệ thống. Chủ sẽ lấy số tài khoản trực tiếp từ khách khi chuyển khoản.
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className={s.emptyState}>Đang tải danh sách hàng chờ...</div>
      ) : items.length === 0 ? (
        <div className={s.emptyState}>
          Hiện không có đơn nào trong danh sách này.
        </div>
      ) : (
        <>
          {/* Mobile Cards (visible on smaller screens) */}
          <div className={s.cardsContainer}>
            {items.map((item) => {
              const isClaimedByOther =
                item.claimed_by &&
                item.claimed_until &&
                new Date(item.claimed_until).getTime() > Date.now();

              return (
                <div
                  key={item.note_id}
                  className={s.queueCard}
                  onClick={() => setSelectedNoteId(item.note_id)}
                >
                  <div className={s.cardHeader}>
                    <div>
                      <div className={s.orderCode}>{item.order_code}</div>
                      <div className={s.paidTime}>
                        Trả tiền: {item.paid_at ? `${item.paid_at.slice(11, 16)} ngày ${item.paid_at.slice(8, 10)}/${item.paid_at.slice(5, 7)}` : "—"}
                      </div>
                    </div>
                    <div>
                      {item.confirm_state === "PENDING" && (
                        <span className={`${s.badge} ${s.badgePending}`}>Chờ gọi</span>
                      )}
                      {item.confirm_state === "CALLBACK" && (
                        <span className={`${s.badge} ${s.badgeCallback}`}>
                          Hẹn gọi lại {item.callback_at ? item.callback_at.slice(11, 16) : ""}
                        </span>
                      )}
                      {item.confirm_state === "ESCALATED" && (
                        <span className={`${s.badge} ${s.badgeEscalated}`}>
                          {item.escalation_label || "Cần quyết định"}
                        </span>
                      )}
                      {item.confirm_state === "REFUND_CALL" && (
                        <span className={`${s.badge} ${s.badgeRefundCall}`}>Báo hoàn tiền</span>
                      )}
                    </div>
                  </div>

                  {isClaimedByOther && (
                    <div style={{ marginBottom: "8px" }}>
                      <span className={`${s.badge} ${s.badgeClaimed}`}>
                        🔒 Đang xử lý: {item.claimed_by?.display_name} (tới {item.claimed_until?.slice(11, 16)})
                      </span>
                    </div>
                  )}

                  <div className={s.customerRow}>
                    <div className={s.customerName}>{item.customer_name}</div>
                    <a
                      href={`tel:${item.recipient_phone || item.phone}`}
                      className={s.phoneLink}
                      onClick={(e) => e.stopPropagation()}
                    >
                      📞 {item.recipient_phone || item.phone}
                    </a>
                  </div>

                  <div className={s.addressText}>{item.address}</div>

                  <div className={s.linesSummary}>
                    {item.lines_summary} · <strong>{item.total_kg} kg</strong>
                  </div>

                  {item.refund && (
                    <div style={{ marginBottom: "10px", padding: "8px 12px", background: "#fefce8", border: "1px solid #fef08a", borderRadius: "6px", fontSize: "0.8125rem", color: "#854d0e" }}>
                      <div>Số tiền hoàn: <strong style={{ color: "#dc2626" }}>{Number(item.refund.amount).toLocaleString("vi-VN")} đ</strong></div>
                      <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "2px" }}>
                        Trạng thái: <strong>{item.refund.status_label || (item.refund.status === "PENDING" ? "Chờ Chủ chuyển" : "Đã hoàn")}</strong>
                        {item.refund.deadline && <span> · Hạn: {item.refund.deadline}</span>}
                      </div>
                    </div>
                  )}

                  <div className={s.cardFooter}>
                    <span>Số lần gọi: <strong>{item.attempts}</strong>/3</span>
                    <span style={{ color: "#2563eb", fontWeight: 600 }}>Chi tiết gọi →</span>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Call Modal */}
      {selectedNoteId !== null && (
        <CskhCallModal
          noteId={selectedNoteId}
          initialItem={items.find((i) => i.note_id === selectedNoteId)}
          onClose={() => setSelectedNoteId(null)}
          onUpdated={() => loadQueue(activeTab)}
        />
      )}
    </div>
  );
}
