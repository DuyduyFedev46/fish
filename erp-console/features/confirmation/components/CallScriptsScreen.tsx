"use client";

// CS-18 — /confirmation/scripts/: kịch bản gọi soạn sẵn theo 4 tình huống. Chủ soạn, sửa, bật/tắt (add/change_callscript);
// Quản lý và CSKH chỉ đọc (chỉ thấy kịch bản đang bật, không có nút sửa). Không có xoá: tắt bằng công tắc. Không AI.
// Nút theo quyền thật của người dùng, BE vẫn là lớp chặn. Nội dung là chữ chung, không chứa dữ liệu khách (BR-GH-19).
import { useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import { useResource } from "@/shared/lib/useResource";
import { Icon } from "@/shared/ui/Icon";
import { ResourceView } from "@/shared/ui/ResourceView";
import { SkeletonTable } from "@/shared/ui/Skeleton";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { Section } from "@/shared/ui/detail/Section";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchCallScripts, updateCallScript } from "../api";
import { slotsOf } from "../callScripts";
import type { CallScript, CallScriptSituation } from "../types";
import { CallScriptModal } from "./CallScriptModal";
import s from "../confirmation.module.css";

const BACK = { href: "/confirmation/", label: "Gọi xác nhận" };

type Editing = { situation: CallScriptSituation; label: string; existing: CallScript | null } | null;

export function CallScriptsScreen() {
  const { me } = useAuth();
  const toast = useToast();
  const mayView = Boolean(me?.permissions.includes(PERM.viewCallScript));
  const mayAdd = Boolean(me?.permissions.includes(PERM.addCallScript));
  const mayChange = Boolean(me?.permissions.includes(PERM.changeCallScript));
  const res = useResource(me && mayView ? "call-scripts" : null, () => fetchCallScripts(), 0);
  const [editing, setEditing] = useState<Editing>(null);
  const [busy, setBusy] = useState<CallScriptSituation | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (me && !mayView) return <NoPermission homeHref="/confirmation/" />;
  if (res.error instanceof ApiError && res.error.status === 403) return <NoPermission homeHref="/confirmation/" />;

  const toggle = async (script: CallScript) => {
    if (busy) return;
    setBusy(script.situation);
    setActionError(null);
    try {
      await updateCallScript(script.situation, { is_active: !script.is_active });
      toast.success(script.is_active ? "Đã tắt kịch bản. Người gọi sẽ không thấy kịch bản này." : "Đã bật kịch bản.");
      await res.reload();
    } catch (err) {
      setActionError(err instanceof Error && err.message ? err.message : "Chưa đổi được. Kiểm tra mạng rồi bấm lại.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <DetailPage id="call-scripts" header={<DetailHeader back={BACK} title="Kịch bản gọi" />} banner={actionError ? <FormAlert>{actionError}</FormAlert> : undefined}>
      <ResourceView res={res} skeleton={<SkeletonTable rows={4} cols={2} />}>
        {(scripts) => {
          const slots = slotsOf(scripts);
          // Người chỉ đọc (Quản lý, CSKH) chỉ nhận kịch bản đang bật: chưa có cái nào thì nói rõ, không để màn trống.
          const readOnlyEmpty = !mayChange && scripts.length === 0;
          if (readOnlyEmpty) {
            return (
              <div className="page-state">
                <span className="state-ic">
                  <Icon name="chat" />
                </span>
                <h2 className="state-title">Chưa có kịch bản nào đang dùng</h2>
                <p>Khi Chủ soạn và bật kịch bản, nội dung sẽ hiện ở đây và trong chi tiết từng đơn cần gọi.</p>
              </div>
            );
          }
          return (
            <div className={s.scriptList}>
              {slots
                .filter((slot) => mayChange || slot.script)
                .map((slot) => {
                  const sc = slot.script;
                  return (
                    <Section
                      key={slot.situation}
                      title={slot.label}
                      aria-label={`Kịch bản: ${slot.label}`}
                      action={
                        <span className={s.scriptActions}>
                          {sc && <span className={`stat-chip ${sc.is_active ? "good" : "mute"}`}>{sc.is_active ? "Đang dùng" : "Đã tắt"}</span>}
                          {sc && mayChange && (
                            <>
                              <button type="button" className="btn" onClick={() => setEditing({ situation: slot.situation, label: slot.label, existing: sc })}>
                                <Icon name="edit" />
                                <span>Sửa</span>
                              </button>
                              <button type="button" className="btn" onClick={() => void toggle(sc)} disabled={busy !== null}>
                                {busy === slot.situation ? "Đang lưu…" : sc.is_active ? "Tắt" : "Bật"}
                              </button>
                            </>
                          )}
                          {!sc && mayAdd && (
                            <button type="button" className="btn primary" onClick={() => setEditing({ situation: slot.situation, label: slot.label, existing: null })}>
                              <Icon name="add" />
                              <span>Soạn kịch bản</span>
                            </button>
                          )}
                        </span>
                      }
                    >
                      {sc ? <p className={s.scriptText}>{sc.content}</p> : <p className="muted">Chưa soạn kịch bản cho tình huống này.</p>}
                    </Section>
                  );
                })}
            </div>
          );
        }}
      </ResourceView>

      {editing && (
        <CallScriptModal
          situation={editing.situation}
          label={editing.label}
          existing={editing.existing}
          onClose={() => setEditing(null)}
          onSaved={(_saved, created) => {
            setEditing(null);
            toast.success(created ? "Đã soạn kịch bản." : "Đã lưu kịch bản.");
            void res.reload();
          }}
        />
      )}
    </DetailPage>
  );
}
