"use client";

// Xem MỘT phiên bản đã đăng của bài, chỉ đọc (SR-19, GL-05-AC1, CMS-11).
// Mở từ link bằng chứng đồng ý ở chi tiết đơn: `/content/edit/?id=<bài>&version=<N>`.
// Hiện đúng nội dung phiên bản N mà khách đã đồng ý — không phải bản nháp hay bản mới hơn — nên KHÔNG có nút
// sửa/khôi phục. Giờ hiển thị theo Asia/Ho_Chi_Minh để đối chiếu với thời điểm khách đồng ý.

import React, { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { dateTimeFull } from "@/shared/lib/format";
import { ErrorBox, Loading } from "@/shared/ui/StateBox";
import { Icon } from "@/shared/ui/Icon";
import { SideSheet } from "@/shared/ui/SideSheet";
import { getEntryVersion } from "../api";
import { isSafeHref } from "../editor/safeHref";
import type { Block, ContentEntryVersionDetail, InlineNode } from "../types";
import s from "./policy-version.module.css";

type Props = {
  entryId: number;
  versionNo: number;
  /** Đóng panel, quay về màn soạn bài. */
  onClose: () => void;
};


function Inline({ nodes }: { nodes: InlineNode[] }) {
  return (
    <>
      {nodes.map((n, i) => {
        let el: React.ReactNode = n.text;
        if (n.marks?.includes("bold")) el = <strong>{el}</strong>;
        if (n.marks?.includes("italic")) el = <em>{el}</em>;
        if (n.href && isSafeHref(n.href)) {
          el = (
            <a href={n.href} target="_blank" rel="noopener noreferrer">
              {el}
            </a>
          );
        }
        return <React.Fragment key={i}>{el}</React.Fragment>;
      })}
    </>
  );
}

function BlockView({ block }: { block: Block }) {
  switch (block.type) {
    case "heading":
      return block.level === 2 ? <h3 className={s.h2}>{block.text}</h3> : <h4 className={s.h3}>{block.text}</h4>;
    case "paragraph":
      return (
        <p className={s.p}>
          <Inline nodes={block.children} />
        </p>
      );
    case "quote":
      return (
        <blockquote className={s.quote}>
          <Inline nodes={block.children} />
        </blockquote>
      );
    case "list": {
      const Tag = block.ordered ? "ol" : "ul";
      return (
        <Tag className={s.list}>
          {block.items.map((item, i) => (
            <li key={i}>
              <Inline nodes={item} />
            </li>
          ))}
        </Tag>
      );
    }
    case "image":
      return (
        <p className={s.placeholder}>
          [Ảnh #{block.image_id}
          {block.caption ? `: ${block.caption}` : block.alt ? `: ${block.alt}` : ""}]
        </p>
      );
    case "item_card":
      return <p className={s.placeholder}>[Thẻ sản phẩm {block.item_code}]</p>;
    default:
      return null;
  }
}

export default function PolicyVersionSheet({ entryId, versionNo, onClose }: Props) {
  const [detail, setDetail] = useState<ContentEntryVersionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setNotFound(false);
    setError(null);
    getEntryVersion(entryId, versionNo, ac.signal)
      .then((d) => {
        if (!ac.signal.aborted) setDetail(d);
      })
      .catch((err: unknown) => {
        if (ac.signal.aborted) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else if (err instanceof ApiError && err.status === 403) {
          setError("Bạn không có quyền xem nội dung chính sách này.");
        } else {
          setError(err instanceof Error ? err.message : "Không tải được phiên bản chính sách.");
        }
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [entryId, versionNo, reload]);

  const retry = useCallback(() => setReload((n) => n + 1), []);

  return (
    <SideSheet title={notFound ? `Phiên bản ${versionNo}` : `Phiên bản ${versionNo} (khách đã đồng ý)`} onClose={onClose}>
      {(close) => (
        <div className={s.wrap} data-policy-version-sheet>
          {loading ? (
            <Loading label={`Đang tải phiên bản ${versionNo}…`} />
          ) : notFound ? (
            <div className="state state-err" role="alert">
              <span className="state-ic">
                <Icon name="search_off" />
              </span>
              <p className="state-title">Không tìm thấy phiên bản {versionNo}</p>
              <p className={s.hint}>Phiên bản này không có trong lịch sử của bài. Hãy quay về bài để xem các phiên bản đã đăng.</p>
              <button type="button" className="btn primary" onClick={close}>
                Về bài
              </button>
            </div>
          ) : error ? (
            <ErrorBox message={error} onRetry={retry} />
          ) : detail ? (
            <>
              <p className={s.readonly}>
                <Icon name="lock" />
                <span>Chỉ đọc. Đây là nội dung đúng như khách đã thấy khi bấm đồng ý.</span>
              </p>
              <dl className={s.meta}>
                <div>
                  <dt>Đăng lúc</dt>
                  <dd className="num">{dateTimeFull(detail.published_at)} (giờ Việt Nam)</dd>
                </div>
                {detail.published_by_name && (
                  <div>
                    <dt>Người đăng</dt>
                    <dd>{detail.published_by_name}</dd>
                  </div>
                )}
              </dl>
              <h2 className={s.title}>{detail.title}</h2>
              <div className={s.body}>
                {detail.body.blocks.length === 0 ? (
                  <p className={s.hint}>Phiên bản này chưa có nội dung.</p>
                ) : (
                  detail.body.blocks.map((b, i) => <BlockView key={i} block={b} />)
                )}
              </div>
              <div className={s.actions}>
                <button type="button" className="btn" onClick={close}>
                  Về bài
                </button>
              </div>
            </>
          ) : null}
        </div>
      )}
    </SideSheet>
  );
}
