import type { ReactNode } from "react";

// Bộ icon SVG nét của Shop (Q-UX-2). Mọi icon đi qua đây; thêm icon mới = thêm vào union + map.
export type IconName =
  | "search"
  | "cart"
  | "phone"
  | "receipt"
  | "home"
  | "grid"
  | "chevron-left"
  | "chevron-right"
  | "chevron-down"
  | "close"
  | "plus"
  | "minus"
  | "trash"
  | "check"
  | "info"
  | "warning"
  | "error"
  | "map-pin"
  | "map"
  | "copy"
  | "clock"
  | "chat"
  | "mail"
  | "fish"
  | "shrimp"
  | "squid"
  | "crab"
  | "combo"
  | "filter"
  | "sort"
  | "refresh"
  | "external"
  | "truck"
  | "package"
  | "qr"
  | "lock"
  | "snowflake"
  | "wifi-off"
  | "ban"
  | "hourglass";

const PATHS: Record<IconName, ReactNode> = {
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M20 20l-4.2-4.2" />
    </>
  ),
  cart: (
    <>
      <path d="M3 4h2l2.4 10.2a1.5 1.5 0 0 0 1.5 1.1h8.6a1.5 1.5 0 0 0 1.5-1.1L21 8H6.2" />
      <circle cx="9.5" cy="19.5" r="1.3" />
      <circle cx="17" cy="19.5" r="1.3" />
    </>
  ),
  phone: <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2" />,
  receipt: <path d="M8 3h8l3 3v15H5V3h3zM9 10h6M9 14h6M9 18h3" />,
  home: <path d="M4 11l8-6 8 6v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z" />,
  grid: <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
  "chevron-left": <path d="M15 6l-6 6 6 6" />,
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  "chevron-down": <path d="M6 9l6 6 6-6" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  trash: <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" />,
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  warning: <path d="M12 3l10 18H2zM12 10v5M12 18h.01" />,
  error: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v6M12 16.5h.01" />
    </>
  ),
  "map-pin": (
    <>
      <path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" />
      <circle cx="12" cy="9.5" r="2.5" />
    </>
  ),
  map: <path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14" />,
  copy: <path d="M9 9h10v11H9zM5 15V4h10" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  chat: <path d="M4 5h16v11H9l-5 4z" />,
  mail: <path d="M3 6h18v12H3zM3 7l9 7 9-7" />,
  fish: <path d="M5 12c2.6-3.6 6-5.5 9.5-5.5 2.7 0 4.7 1.9 6.5 5.5-1.8 3.6-3.8 5.5-6.5 5.5C11 17.5 7.6 15.6 5 12zM5 12L2 8.5M5 12l-3 3.5" />,
  shrimp: <path d="M18 5c-5 0-9 3.5-9 8 0 3 2 5 5 5h3M9 13H5M18 5c2 0 3 1.2 3 3s-1.6 3-3.5 3M12 18l-2 3M16 18l1 3" />,
  squid: <path d="M12 3c-3 0-5 3-5 7v3h10v-3c0-4-2-7-5-7zM8 13l-1 7M10.5 13l-.5 8M13.5 13l.5 8M16 13l1 7" />,
  crab: <path d="M6 13a6 4 0 1 0 12 0a6 4 0 1 0-12 0M5 10L3 6l3 1M19 10l2-4-3 1M7 16l-2 3M17 16l2 3" />,
  combo: <path d="M4 8l8-4 8 4v8l-8 4-8-4zM4 8l8 4 8-4M12 12v8" />,
  filter: <path d="M4 5h16l-6 8v6l-4-2v-4z" />,
  sort: <path d="M7 4v16M7 20l-3-3M7 20l3-3M17 20V4M17 4l-3 3M17 4l3 3" />,
  refresh: <path d="M20 11a8 8 0 1 0-2 6M20 4v7h-7" />,
  external: <path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6" />,
  truck: <path d="M3 7h11v9H3zM14 10h4l3 3v3h-7M7 19a1.5 1.5 0 1 0 0-.1M17 19a1.5 1.5 0 1 0 0-.1" />,
  package: <path d="M4 8l8-4 8 4v8l-8 4-8-4zM4 8l8 4 8-4M12 12v8" />,
  qr: <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2v2h-2zM18 18h2v2h-2zM18 14h2M14 18v2" />,
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </>
  ),
  snowflake: <path d="M12 2v20M4.5 6.5l15 11M19.5 6.5l-15 11" />,
  "wifi-off": <path d="M3 3l18 18M8.5 16.4a5 5 0 0 1 7 0M5 12.9a10 10 0 0 1 3.2-2M10 6.2A15 15 0 0 1 22 9.5M2 9.5a15 15 0 0 1 4-2.4M12 20h.01" />,
  ban: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M5.6 5.6l12.8 12.8" />
    </>
  ),
  hourglass: <path d="M6 3h12M6 21h12M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9" />,
};

export default function Icon({
  name,
  size = 20,
  strokeWidth = 1.75,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
