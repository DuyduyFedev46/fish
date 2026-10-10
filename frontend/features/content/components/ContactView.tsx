import Breadcrumb from "@/components/ui/Breadcrumb";
import Icon, { type IconName } from "@/components/ui/Icon";
import { telHref } from "@/components/shopLinks";
import { pickHotline, zaloUrlOf } from "@/lib/phone";
import type { SiteInfoResponse } from "@/features/site/types";
import type { PublicBlock, PublicEntryDetail } from "../types";
import { BodyBlock } from "./ArticleBody";
import s from "./ContactView.module.css";

/**
 * Trang Liên hệ (SHOP-5-04 AC2, màn P2-Contact · DesktopContact, UI-RULES §3.3).
 * KHÔNG có form. Chỉ hotline, Zalo, email, địa chỉ kinh doanh, giờ làm việc. Thẻ nào chưa có dữ liệu thì ẩn.
 * Số, email, địa chỉ lấy từ site-info (một nguồn, 06-marketing B5); câu mở đầu lấy từ thân bài CMS `lien-he`.
 * Giờ làm việc: `seller.working_hours` của site-info; trống thì lấy mục "Giờ làm việc" trong CMS (bản A của 06-marketing C2.2),
 * còn ô `[…]` chưa điền thì coi như chưa có, ẩn thẻ.
 */

type Card = {
  key: string;
  icon: IconName;
  label: string;
  value: string;
  href?: string;
  external?: boolean;
  action?: string;
};

const WORKING_HOURS_HEADING = "giờ làm việc";

function plainText(block: PublicBlock): string {
  if (block.type === "paragraph" || block.type === "quote") return block.children.map((c) => c.text).join("");
  if (block.type === "list") return block.items.map((it) => it.map((c) => c.text).join("")).join(", ");
  return "";
}

/** Có ô chờ điền kiểu "[giờ mở]" thì coi như chưa có dữ liệu. */
function filled(value: string | null | undefined): string | undefined {
  const v = (value ?? "").trim();
  if (!v || /\[[^\]]*\]/.test(v)) return undefined;
  return v;
}

function validEmail(value: string | null | undefined): string | undefined {
  const v = filled(value);
  return v && /^[^\s@<>()]+@[^\s@<>()]+\.[^\s@<>()]+$/.test(v) ? v : undefined;
}

/** Tách thân bài: đoạn mở (trước H2 đầu), mục "Giờ làm việc", các mục khác vẫn hiện dưới thẻ. */
function splitBody(blocks: PublicBlock[]) {
  const intro: PublicBlock[] = [];
  const rest: PublicBlock[] = [];
  let hours: string | undefined;
  let section: "intro" | "hours" | "rest" = "intro";
  for (const block of blocks) {
    if (block.type === "heading" && block.level === 2) {
      section = block.text.trim().toLowerCase() === WORKING_HOURS_HEADING ? "hours" : "rest";
      if (section === "rest") rest.push(block);
      continue;
    }
    if (section === "intro") intro.push(block);
    else if (section === "hours") hours = hours ?? filled(plainText(block));
    else rest.push(block);
  }
  return { intro, hours, rest };
}

export default function ContactView({
  entry,
  siteInfo,
}: {
  entry: PublicEntryDetail;
  siteInfo: SiteInfoResponse | null;
}) {
  const { intro, hours: cmsHours, rest } = splitBody(entry.body?.blocks ?? []);
  const seller = siteInfo?.seller;
  const hotline = pickHotline(seller?.phone, siteInfo?.confirmation_policy?.hotline);
  const zaloNumber = filled(seller?.zalo);
  const zaloUrl = zaloUrlOf(zaloNumber);
  const email = validEmail(seller?.email);
  const address = filled(seller?.address);
  const hours = filled(seller?.working_hours) ?? cmsHours;

  const cards: Card[] = [];
  if (hotline) cards.push({ key: "hotline", icon: "phone", label: "Hotline", value: hotline, href: telHref(hotline), action: "Gọi ngay" });
  if (zaloUrl && zaloNumber)
    cards.push({ key: "zalo", icon: "chat", label: "Zalo", value: zaloNumber, href: zaloUrl, external: true, action: "Nhắn Zalo" });
  if (email) cards.push({ key: "email", icon: "mail", label: "Email", value: email, href: `mailto:${email}`, action: "Gửi email" });
  if (address) cards.push({ key: "address", icon: "map-pin", label: "Địa chỉ kinh doanh", value: address });
  if (hours) cards.push({ key: "hours", icon: "clock", label: "Giờ làm việc", value: hours });

  return (
    <div className={s.container}>
      <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: entry.title }]} />
      <header className={s.head}>
        <h1 className={s.title}>{entry.title}</h1>
        {intro.map((b, i) => (
          <div key={i} className={s.lead}>
            <BodyBlock block={b} />
          </div>
        ))}
      </header>

      {cards.length > 0 ? (
        <ul className={s.cards}>
          {cards.map((c) => {
            const inner = (
              <>
                <span className={s.icon} aria-hidden="true">
                  <Icon name={c.icon} size={22} />
                </span>
                <span className={s.text}>
                  <span className={s.label}>{c.label}</span>
                  <span className={`${s.value} num`}>{c.value}</span>
                </span>
                {c.href ? (
                  <>
                    <span className={s.chevron} aria-hidden="true">
                      <Icon name={c.external ? "external" : "chevron-right"} size={18} />
                    </span>
                    {c.action ? (
                      <span className={c.key === "hotline" ? `${s.action} ${s.actionPrimary}` : s.action} aria-hidden="true">
                        {c.action}
                      </span>
                    ) : null}
                  </>
                ) : null}
              </>
            );
            return (
              <li key={c.key}>
                {c.href ? (
                  <a
                    href={c.href}
                    className={`${s.card} ${s.cardLink}`}
                    {...(c.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                  >
                    {inner}
                    {c.external ? <span className="visually-hidden"> (mở tab mới)</span> : null}
                  </a>
                ) : (
                  <div className={s.card}>{inner}</div>
                )}
              </li>
            );
          })}
        </ul>
      ) : null}

      {rest.length > 0 ? (
        <div className={s.more}>
          {rest.map((b, i) => (
            <BodyBlock key={i} block={b} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
