// Khung chờ đúng hình (UI3): lần tải đầu vẽ dáng của dải KPI / bảng thay cho icon quay giữa màn,
// để khi số liệu về không bị nhảy bố cục. Trình đọc màn hình nghe "Đang tải dữ liệu…" (role=status).
// Dùng qua prop `skeleton` của ResourceView.

type Bar = "s" | "m" | "l";
const WIDTH: Bar[] = ["m", "l", "s", "m", "s", "l", "m", "s"];

function Line({ w, className }: { w: Bar; className?: string }) {
  return <span className={`sk sk-${w}${className ? ` ${className}` : ""}`} />;
}

export function SkeletonKpis({ count = 4 }: { count?: number }) {
  return (
    <div className="kpi-band" aria-hidden="true">
      <div className="kpis sk-kpis">
        {Array.from({ length: count }, (_, i) => (
          <div className="tile" key={i}>
            <Line w="m" />
            <Line w="l" className="sk-val" />
            <Line w="s" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Dáng một khối bảng: đầu mục + `rows` dòng. Trên màn hẹp tự thành dáng danh sách (CSS). */
export function SkeletonTable({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="sect sk-table" aria-hidden="true">
      <div className="sect-h">
        <Line w="m" />
      </div>
      <div className="sk-rows">
        {Array.from({ length: rows }, (_, r) => (
          <div className="sk-row" key={r}>
            {Array.from({ length: cols }, (_, c) => (
              <Line key={c} w={WIDTH[(r + c) % WIDTH.length]} className={c === cols - 1 ? "sk-end" : undefined} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Bọc khung chờ: một thông báo cho trình đọc màn hình, phần hình bị ẩn khỏi cây truy cập. */
export function SkeletonScreen({ children, label = "Đang tải dữ liệu…" }: { children: React.ReactNode; label?: string }) {
  return (
    <div className="sk-screen" role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}
