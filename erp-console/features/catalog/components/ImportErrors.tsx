"use client";

// M4 — Bảng lỗi theo dòng khi xem trước file Excel mặt hàng (FISH-66 S5-AC6/7/8/11/12, S4-AC2; 02a §3.3).

import { useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import { Section } from "@/shared/ui/detail/Section";
import type { ImportRowErrorsDetails } from "../itemFilesTypes";
import { ITEM_IMPORT_MSG as M } from "../messages";
import s from "../catalog.module.css";

const PAGE_SIZE = 200;

type Props = {
  details: ImportRowErrorsDetails;
  headingRef?: React.RefObject<HTMLHeadingElement>;
};

export function ImportErrors({ details, headingRef }: Props) {
  const [shown, setShown] = useState(PAGE_SIZE);
  const visibleErrors = details.errors.slice(0, shown);
  const remaining = details.errors.length - visibleErrors.length;

  return (
    <div className={s.importStack} data-testid="import-row-errors">
      <h2 ref={headingRef} tabIndex={-1} className="sr-only">
        {M.errRowSummary(details.error_count, details.error_row_count)}
      </h2>

      <div className="alert-box err" role="alert">
        <Icon name="error" />
        <div>
          <strong>{M.errRowSummary(details.error_count, details.error_row_count)}</strong>{" "}
          {M.errRowHint}
        </div>
      </div>

      <Section title={`${details.error_count} lỗi cần sửa`}>
        <div className={s.tableWrap}>
          <table className={s.importTable}>
            <caption className="sr-only">
              {M.errRowSummary(details.error_count, details.error_row_count)}
            </caption>
            <thead>
              <tr>
                <th scope="col" className={s.numCol}>{M.colRow}</th>
                <th scope="col">{M.colCode}</th>
                <th scope="col">{M.colColumn}</th>
                <th scope="col">{M.colHowToFix}</th>
              </tr>
            </thead>
            <tbody>
              {visibleErrors.map((err, idx) => (
                <tr key={`${err.row}-${err.column}-${idx}`}>
                  <td className={s.numCol}>{err.row}</td>
                  <td className="mono">{err.code || M.none}</td>
                  <td>{err.column}</td>
                  <td>{err.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {remaining > 0 && (
          <div className={s.sectionFoot}>
            <button
              type="button"
              className="btn"
              onClick={() => setShown((n) => n + PAGE_SIZE)}
            >
              {M.showMore(Math.min(PAGE_SIZE, remaining))}
            </button>
          </div>
        )}
      </Section>
    </div>
  );
}
