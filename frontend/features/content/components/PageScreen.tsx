"use client";

// SHOP-5-04: trang CMS `/pages/?slug=` theo màn P1-Policy · DesktopPolicy (chính sách), P2-Contact · DesktopContact
// (slug `lien-he`), P3-HowToBuy (slug `cach-mua-hang`). Nội dung chữ ở CMS; ở đây chỉ chữ giao diện.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import ShopFrame from "@/components/ShopFrame";
import Breadcrumb from "@/components/ui/Breadcrumb";
import { ApiError } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { getFooterLinks, getSiteInfo } from "@/features/site/api";
import type { SiteInfoResponse } from "@/features/site/types";
import PolicyNav from "@/features/site/components/PolicyNav";
import { fetchPublicEntry } from "../api";
import { headingAnchors } from "../headings";
import { GONE_TITLE, LOAD_ERROR_TITLE, NOT_FOUND_TITLE, setPageDescription, setPageMeta, withBrand } from "../pageMeta";
import { CONTACT_SLUG, HOW_TO_BUY_SLUG, policyHref } from "../slugs";
import type { PublicEntryDetail } from "../types";
import ArticleBody from "./ArticleBody";
import ContactView from "./ContactView";
import { ContentFailure, ContentSkeleton, failureOf, type LoadFailure } from "./ContentState";
import HowToBuyView from "./HowToBuyView";
import s from "./PageScreen.module.css";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; entry: PublicEntryDetail }
  | { kind: "failed"; failure: LoadFailure };

type PolicyLink = { slug: string; label: string; href: string };

const HOW_TO_BUY_LINK = { label: "Cách mua hàng", href: policyHref(HOW_TO_BUY_SLUG), slug: HOW_TO_BUY_SLUG };

function headerTitle(slug: string): string {
  if (slug === CONTACT_SLUG) return "Liên hệ";
  if (slug === HOW_TO_BUY_SLUG) return "Cách mua hàng";
  return "Chính sách";
}

export default function PageScreen() {
  const slug = useSearchParams().get("slug") ?? "";
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [retrying, setRetrying] = useState(false);
  const [policies, setPolicies] = useState<PolicyLink[] | null>(null);
  const [siteInfo, setSiteInfo] = useState<SiteInfoResponse | null>(null);

  const load = useCallback(async (): Promise<void> => {
    if (!slug) {
      setState({ kind: "failed", failure: "not-found" });
      setPageMeta({ title: NOT_FOUND_TITLE, noindex: true });
      return;
    }
    try {
      const entry = await fetchPublicEntry(slug);
      setState({ kind: "ready", entry });
      // seo_title trong CMS đã có "Cá Về" thì không thêm hậu tố lần nữa (QA lô 1 L2).
      setPageMeta({ title: withBrand(entry.seo_title || entry.title || ""), noindex: false });
      setPageDescription(entry.description || entry.excerpt);
    } catch (err) {
      const failure = failureOf(err instanceof ApiError ? err.status : undefined);
      setState({ kind: "failed", failure });
      setPageMeta({
        title: failure === "not-found" ? NOT_FOUND_TITLE : failure === "gone" ? GONE_TITLE : LOAD_ERROR_TITLE,
        noindex: true,
      });
    }
  }, [slug]);

  useEffect(() => {
    setState({ kind: "loading" });
    load();
  }, [load]);

  // Danh sách chính sách lấy từ CMS (footer-links); lỗi thì ẩn khối, trang vẫn đọc được.
  useEffect(() => {
    let active = true;
    getFooterLinks()
      .then((links) => {
        if (!active) return;
        setPolicies((links || []).map((l) => ({ slug: l.slug, label: l.title, href: policyHref(l.slug) })));
      })
      .catch(() => active && setPolicies([]));
    return () => {
      active = false;
    };
  }, []);

  // Thẻ liên hệ đọc site-info (một nguồn cho hotline, Zalo, email, địa chỉ, giờ làm). Có cache 5 phút sẵn.
  useEffect(() => {
    if (slug !== CONTACT_SLUG) return;
    let active = true;
    getSiteInfo()
      .then((info) => active && setSiteInfo(info))
      .catch(() => active && setSiteInfo(null));
    return () => {
      active = false;
    };
  }, [slug]);

  async function retry() {
    setRetrying(true);
    await load();
    setRetrying(false);
  }

  return (
    <ShopFrame header="sub" title={headerTitle(slug)} footer="full" bottomNav={false} backHref="/">
      <div className={s.page}>
        {state.kind === "loading" ? (
          <div className={s.container}>
            <ContentSkeleton />
          </div>
        ) : state.kind === "failed" ? (
          <div className={s.container}>
            <ContentFailure kind="page" failure={state.failure} onRetry={retry} retrying={retrying} />
          </div>
        ) : slug === CONTACT_SLUG ? (
          <ContactView entry={state.entry} siteInfo={siteInfo} />
        ) : (
          <PolicyLayout entry={state.entry} slug={slug} policies={policies} />
        )}
      </div>
    </ShopFrame>
  );
}

function PolicyLayout({
  entry,
  slug,
  policies,
}: {
  entry: PublicEntryDetail;
  slug: string;
  policies: PolicyLink[] | null;
}) {
  const isHowToBuy = slug === HOW_TO_BUY_SLUG;
  const toc = useMemo(() => headingAnchors(entry.body?.blocks ?? []).toc, [entry]);
  const effectiveRaw = entry.effective_from || entry.published_at || entry.updated_at;
  const updated = effectiveRaw ? formatDate(effectiveRaw) : "";
  const crumbs = isHowToBuy
    ? [{ label: "Trang chủ", href: "/" }, { label: entry.title }]
    : [{ label: "Trang chủ", href: "/" }, { label: "Chính sách" }, { label: entry.title }];

  return (
    <div className={s.container}>
      <Breadcrumb items={crumbs} />
      <div className={s.columns}>
        <aside className={s.aside}>
          <PolicyNav
            variant="aside"
            policies={policies ?? []}
            loading={policies === null}
            currentSlug={slug}
            extraLinks={[HOW_TO_BUY_LINK]}
          />
        </aside>

        <div className={s.main}>
          {isHowToBuy ? (
            <HowToBuyView entry={entry} />
          ) : (
            <article className={s.article} aria-labelledby="page-title">
              <header className={s.head}>
                <h1 id="page-title" className={s.title}>
                  {entry.title}
                </h1>
                {updated ? <span className={`${s.updated} num`}>Cập nhật lần cuối {updated}</span> : null}
              </header>
              <PolicyNav variant="toc" policies={[]} currentSlug={slug} toc={toc} />
              <ArticleBody body={entry.body} variant="policy" />
            </article>
          )}
        </div>
      </div>

      <div className={s.listBelow}>
        <PolicyNav variant="list" policies={policies ?? []} loading={policies === null} currentSlug={slug} />
      </div>
    </div>
  );
}
