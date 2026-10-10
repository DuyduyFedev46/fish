import type { ReactNode } from "react";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import { CATALOG_HREF } from "@/components/shopLinks";
import type { InlineNode, PublicBlock, PublicEntryDetail } from "../types";
import { BodyBlock, InlineText } from "./ArticleBody";
import s from "./HowToBuyView.module.css";

/**
 * Trang Cách mua (SHOP-5-04 AC3, màn P3-HowToBuy, DesktopPolicy#cach-mua). Đọc thân bài CMS `cach-mua-hang`:
 * - danh sách số mà mỗi mục mở đầu bằng chữ đậm -> thẻ bước có số (chữ đậm = tên bước, phần sau = mô tả);
 * - H3 + các đoạn sau nó -> hỏi đáp thu gọn `<details>` (02b §3.7.4).
 * Số 1 kg / 0,5 kg / 30 phút nằm sẵn trong CMS, do lệnh nạp lấy từ settings (`{min_qty_kg}`, `{qty_step_kg}`,
 * `{hold_minutes}`), FE không viết cứng.
 */

type Section = { heading: string | null; blocks: PublicBlock[] };

function splitSections(blocks: PublicBlock[]): Section[] {
  const sections: Section[] = [{ heading: null, blocks: [] }];
  for (const block of blocks) {
    if (block.type === "heading" && block.level === 2) sections.push({ heading: block.text, blocks: [] });
    else sections[sections.length - 1].blocks.push(block);
  }
  return sections.filter((x) => x.heading !== null || x.blocks.length > 0);
}

/** Mục danh sách dạng "**Tên bước.** Mô tả" -> {title, rest}; không mở đầu bằng chữ đậm thì null. */
function asStep(item: InlineNode[]): { title: string; rest: InlineNode[] } | null {
  const [first, ...rest] = item;
  if (!first || !first.marks?.includes("bold") || first.href) return null;
  const title = first.text.trim().replace(/[.:]\s*$/, "");
  if (!title) return null;
  const trimmed = rest.map((n, i) => (i === 0 ? { ...n, text: n.text.replace(/^\s+/, "") } : n));
  return { title, rest: trimmed.filter((n) => n.text.length > 0) };
}

function SectionBody({ blocks, sectionIndex }: { blocks: PublicBlock[]; sectionIndex: number }) {
  const out: ReactNode[] = [];
  let i = 0;
  let detailsCount = 0;
  while (i < blocks.length) {
    const block = blocks[i];
    if (block.type === "list" && block.ordered) {
      const steps = block.items.map(asStep);
      if (steps.every((x) => x !== null)) {
        out.push(
          <ol key={`steps-${i}`} className={s.steps}>
            {steps.map((step, k) => (
              <li key={k} className={s.step}>
                <span className={`${s.stepNo} num`} aria-hidden="true">
                  {k + 1}
                </span>
                <span className={s.stepText}>
                  <span className={s.stepTitle}>{step!.title}</span>
                  {step!.rest.length > 0 ? (
                    <span className={s.stepDesc}>
                      <InlineText nodes={step!.rest} />
                    </span>
                  ) : null}
                </span>
              </li>
            ))}
          </ol>
        );
        i += 1;
        continue;
      }
    }
    if (block.type === "heading" && block.level === 3) {
      const answer: PublicBlock[] = [];
      let j = i + 1;
      while (j < blocks.length && blocks[j].type !== "heading") {
        answer.push(blocks[j]);
        j += 1;
      }
      // Câu hỏi đầu tiên của trang mở sẵn (màn P3).
      const open = sectionIndex <= 1 && detailsCount === 0;
      detailsCount += 1;
      out.push(
        <details key={`faq-${i}`} className={s.faq} open={open}>
          <summary className={s.question}>
            <span>{block.text}</span>
            <span className={s.chevron}>
              <Icon name="chevron-down" size={18} />
            </span>
          </summary>
          <div className={s.answer}>
            {answer.map((b, k) => (
              <BodyBlock key={k} block={b} />
            ))}
          </div>
        </details>
      );
      i = j;
      continue;
    }
    out.push(<BodyBlock key={`b-${i}`} block={block} />);
    i += 1;
  }
  return <>{out}</>;
}

export default function HowToBuyView({ entry }: { entry: PublicEntryDetail }) {
  const sections = splitSections(entry.body?.blocks ?? []);
  return (
    <div className={s.wrap}>
      <header className={s.head}>
        <h1 className={s.title}>{entry.title}</h1>
        {entry.excerpt ? <p className={s.lead}>{entry.excerpt}</p> : null}
      </header>
      {sections.map((section, index) => (
        <section
          key={index}
          className={s.card}
          aria-labelledby={section.heading ? `how-to-buy-${index}` : undefined}
        >
          {section.heading ? (
            <h2 id={`how-to-buy-${index}`} className={s.cardTitle}>
              {section.heading}
            </h2>
          ) : null}
          <SectionBody blocks={section.blocks} sectionIndex={index} />
        </section>
      ))}
      <div className={s.cta}>
        <Button href={CATALOG_HREF} shape="pill" size="lg" fullWidth iconEnd={<Icon name="chevron-right" size={18} />}>
          Xem hàng đang có
        </Button>
      </div>
    </div>
  );
}
