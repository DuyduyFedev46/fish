"use client";

// Màn "Chính sách AI" của Chủ (ED-42 / W4c): /ai/policy/. Cột chính: chế độ cả vựa (ba thẻ) · việc nhạy cảm (công tắc + thời gian chờ)
// · trần lệnh Nhập lô. Cột phụ: "Tắt toàn bộ AI ngay" (hiệu lực tức thì, qua hộp xác nhận) · AI của từng nhân viên (xem cài đặt chỉ đọc,
// tắt/bật) · tích cam kết rồi "Lưu chính sách". Không dùng confirm()/alert() của trình duyệt; lỗi BE hiện nguyên văn `detail`.
// Tên nhân viên ở đây là tên NỘI BỘ, không phải khách; không ghi vào storage/URL/log.

import { useCallback, useEffect, useMemo, useState } from "react";
import { dateTime } from "@/shared/lib/format";
import { groupLabel } from "@/shared/lib/groups";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ENUMS } from "@/shared/lib/enums";
import { stripRuleCodes } from "@/shared/lib/ruleCodes";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { Icon } from "@/shared/ui/Icon";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { Modal } from "@/shared/ui/overlay/Modal";
import { useToast } from "@/shared/ui/overlay/Toast";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorBox, Loading } from "@/shared/ui/StateBox";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { getAiPolicy, getUserAiConfig, killUserAi, updateAiPolicy } from "../api";
import { buildCapsForSave } from "../caps";
import { commandLabel } from "../../commandLabels";
import { POLICY_MSG as M } from "../messages";
import type { AiPolicy, AiPolicyUserSummary, MyConfig } from "../../types";
import { capErrors, capsToSave, countChips, formOf, isPolicyDirty, MODE_CARDS, policySubtitle, redZoneDescription, userInitial, type CapForm, type PolicyForm } from "../view";
import s from "../policy.module.css";

const RED_ZONE_ICON: Record<string, string> = {
  "inventory.close_batch": "lock",
  "sales.confirm_refund": "currency_exchange",
  "sales.confirm_payment_manual": "payments",
};

function UserConfigModal({ user, onClose }: { user: AiPolicyUserSummary; onClose: () => void }) {
  const [config, setConfig] = useState<MyConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setConfig(null);
    setError(null);
    getUserAiConfig(user.user_id, ctl.signal)
      .then(setConfig)
      .catch((err) => {
        if (!ctl.signal.aborted) setError(loadErrorText(err));
      });
    return () => ctl.abort();
  }, [user.user_id, attempt]);

  return (
    <Modal
      title={M.viewTitle(user.display_name)}
      onClose={onClose}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          {M.viewClose}
        </button>
      }
    >
      {error ? (
        <ErrorBox message={error || M.viewLoadFailed} onRetry={() => setAttempt((n) => n + 1)} />
      ) : !config ? (
        <Loading />
      ) : (
        <>
          <p className={s.viewMeta}>
            {M.viewReadOnly} {M.viewVersion(config.version)} · {dateTime(config.updated_at)}
          </p>
          {config.groups.every((g) => g.commands.length === 0) && <p className={s.empty}>{M.viewNoTasks}</p>}
          {config.groups
            .filter((g) => g.commands.length > 0)
            .map((g) => (
              <section key={g.group} className={s.viewGroup}>
                <h3>{g.label}</h3>
                {g.commands.map((c) => (
                  <div key={c.id} className={s.viewRow}>
                    <span>{commandLabel(c.id, c.title)}</span>
                    <span className="tag">{ENUMS.aiLevel[c.level]?.label ?? c.level}</span>
                  </div>
                ))}
              </section>
            ))}
        </>
      )}
    </Modal>
  );
}

export default function AiPolicyScreen() {
  const toast = useToast();
  const [policy, setPolicy] = useState<AiPolicy | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [base, setBase] = useState<PolicyForm | null>(null);
  const [form, setForm] = useState<PolicyForm | null>(null);
  const [ack, setAck] = useState(false);
  const [ackMissing, setAckMissing] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  // Chỉ lỗi do MÁY CHỦ trả về mới có nút "Thử lại"; lỗi trần tự kiểm thì nút vẫn là "Lưu chính sách".
  const [serverFailed, setServerFailed] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [killAll, setKillAll] = useState(false);
  const [viewing, setViewing] = useState<AiPolicyUserSummary | null>(null);
  const [toggling, setToggling] = useState<AiPolicyUserSummary | null>(null);

  const apply = useCallback((data: AiPolicy) => {
    const f = formOf(data);
    setPolicy(data);
    setBase(f);
    setForm(f);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      apply(await getAiPolicy());
      setConflict(false);
      setSaveError(null);
    } catch (err) {
      setLoadError(err);
    } finally {
      setLoading(false);
    }
  }, [apply]);

  useEffect(() => {
    void load();
  }, [load]);

  const errors = useMemo(() => (form ? capErrors(form.caps) : {}), [form]);
  const dirty = base && form ? isPolicyDirty(base, form) : false;

  if (loading && !policy) {
    return (
      <SkeletonScreen label="Đang tải chính sách AI…">
        <SkeletonTable rows={4} cols={4} />
      </SkeletonScreen>
    );
  }
  if (!policy || !form || !base) {
    const forbidden = loadError instanceof ApiError && loadError.status === 403;
    return <ErrorBox icon={forbidden ? "lock" : undefined} message={loadError ? loadErrorText(loadError) : M.loadFailed} onRetry={() => void load()} />;
  }

  const setCap = (field: keyof CapForm, value: string) => setForm({ ...form, caps: { ...form.caps, [field]: value } });

  const discard = () => {
    setForm(base);
    setAck(false);
    setAckMissing(false);
    setShowErrors(false);
    setSaveError(null);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    setShowErrors(true);
    setAckMissing(!ack);
    if (Object.keys(errors).length > 0) {
      setSaveError(M.capsInvalid);
      return;
    }
    if (!ack) {
      setSaveError(null);
      return;
    }
    setSaving(true);
    setSaveError(null);
    setServerFailed(false);
    try {
      const updated = await updateAiPolicy({
        base_version: policy.version,
        global_mode: form.mode,
        red_zone: form.redZone,
        // Ghi bằng id MỚI của lệnh Nhập lô, bỏ khoá cũ nếu BE còn trả (xem ../caps.ts).
        caps: buildCapsForSave(policy.caps, capsToSave(form.caps)),
        acknowledge_responsibility: true,
      });
      apply(updated);
      setAck(false);
      setShowErrors(false);
      setConflict(false);
      toast.success(M.saved(updated.version));
    } catch (err) {
      if (err instanceof ApiError && err.code === "AI_POLICY_CONFLICT") setConflict(true);
      else {
        setSaveError(err instanceof Error ? err.message : M.loadFailed);
        setServerFailed(true);
      }
    } finally {
      setSaving(false);
    }
  };

  const busy = saving;
  const capBlock = showErrors ? errors : {};

  return (
    <div className={s.page}>
      <div className={s.sub}>
        <span>{policySubtitle(policy)}</span>
      </div>

      {policy.global_mode === "off" && (
        <div className="alert-box warn" role="status">
          <Icon name="warning" />
          <span>{M.offBanner}</span>
        </div>
      )}
      {conflict && <ConflictBanner noun={M.noun} onReload={() => void load()} />}

      <form onSubmit={save} noValidate className={s.cols}>
        <div className={s.main}>
          <section className={s.card} aria-labelledby="pol-mode">
            <div className={s.cardHead}>
              <h2 id="pol-mode">{M.modeTitle}</h2>
            </div>
            <div className={s.modes} role="radiogroup" aria-labelledby="pol-mode">
              {MODE_CARDS.map((m) => (
                <label key={m.value} className={s.mode}>
                  <input type="radio" name="global-mode" value={m.value} checked={form.mode === m.value} disabled={busy} onChange={() => setForm({ ...form, mode: m.value })} />
                  <span className={s.modeTop}>
                    <span className={s.dotRadio} aria-hidden="true" />
                    {m.title}
                  </span>
                  <span className={s.modeText}>{m.text}</span>
                  {base.mode === m.value && <span className={`tag ${s.modeUse}`}>{M.inUse}</span>}
                </label>
              ))}
            </div>
          </section>

          <section className={`${s.card} ${s.rzCard}`} aria-labelledby="pol-red">
            <div className={s.cardHead}>
              <h2 id="pol-red">{M.sensitiveTitle}</h2>
              <span className={s.cardHint}>{M.sensitiveHint}</span>
            </div>
            <div className={s.rzHead} aria-hidden="true">
              <span>{M.colTask}</span>
              <span>{M.colDesc}</span>
              <span>{M.colState}</span>
              <span>{M.colDelay}</span>
              <span>{M.colAllow}</span>
            </div>
            {policy.red_zone.map((rz) => {
              const open = form.redZone[rz.perm] ?? rz.open;
              return (
                <div key={rz.perm} className={s.rz} data-perm={rz.perm}>
                  <span className={s.rzName}>
                    <Icon name={RED_ZONE_ICON[rz.perm] ?? "policy"} />
                    {rz.label}
                  </span>
                  <span className={s.rzDesc}>{redZoneDescription(rz)}</span>
                  <span className={s.rzState}>
                    <span className={`stat-chip ${open ? "good" : ""}`}>{open ? M.open : M.closed}</span>
                  </span>
                  <span className={s.rzDelay}>
                    {rz.delay_minutes > 0 ? (
                      <>
                        <Icon name="schedule" />
                        {M.delay(rz.delay_minutes)}
                      </>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </span>
                  <span className={s.rzSwitch}>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={open}
                      aria-label={M.switchLabel(rz.label)}
                      className={s.switch}
                      disabled={busy}
                      onClick={() => setForm({ ...form, redZone: { ...form.redZone, [rz.perm]: !open } })}
                    >
                      <span className={s.track} aria-hidden="true">
                        <span className={s.thumb} />
                      </span>
                    </button>
                  </span>
                  <details className={s.rzDetail}>
                    <summary>{M.detail}</summary>
                    <dl>
                      <dt>{M.canDo}</dt>
                      <dd>{stripRuleCodes(rz.can_do)}</dd>
                      <dt>{M.cannotDo}</dt>
                      <dd>{stripRuleCodes(rz.cannot_do)}</dd>
                      <dt>{M.legal}</dt>
                      <dd>{stripRuleCodes(rz.legal_note)}</dd>
                    </dl>
                  </details>
                </div>
              );
            })}
          </section>

          <section className={s.card} aria-labelledby="pol-caps">
            <div className={s.cardHead}>
              <h2 id="pol-caps">{M.capsTitle}</h2>
            </div>
            <div className={s.cardBody}>
              <div className={s.capsGrid}>
                <Field label={M.capKg} type="number" unit={M.capUnitKg} value={form.caps.kg} onChange={(v) => setCap("kg", v)} error={capBlock.kg} disabled={busy} />
                <Field label={M.capVnd} type="number" unit={M.capUnitVnd} value={form.caps.vnd} onChange={(v) => setCap("vnd", v)} error={capBlock.vnd} disabled={busy} />
                <Field label={M.capDaily} type="number" unit={M.capUnitDaily} value={form.caps.daily} onChange={(v) => setCap("daily", v)} error={capBlock.daily} disabled={busy} />
              </div>
              <p className={s.capsHint}>{M.capsHint}</p>
            </div>
          </section>
        </div>

        <div className={s.side}>
          <section className={`${s.card} ${s.danger}`} aria-labelledby="pol-kill">
            <div className={s.cardBody}>
              <div className={s.dangerHead}>
                <Icon name="warning" />
                <h2 id="pol-kill">{M.killAllTitle}</h2>
              </div>
              <div className={s.dangerMeta}>
                <span>{M.killAllEffect}</span>
                <span>{M.killAllNow}</span>
              </div>
              <button type="button" className="btn danger" onClick={() => setKillAll(true)} disabled={busy || policy.global_mode === "off"}>
                <Icon name="block" />
                {M.killAllButton}
              </button>
            </div>
          </section>

          <section className={s.card} aria-labelledby="pol-staff">
            <div className={s.cardHead}>
              <h2 id="pol-staff">{M.staffTitle}</h2>
              <span className={s.cardHint}>{M.staffCount(policy.users.length)}</span>
            </div>
            {policy.users.length === 0 && <p className={s.empty}>{M.staffEmpty}</p>}
            {policy.users.map((u) => (
              <div key={u.user_id} className={s.staffRow} data-user={u.user_id}>
                <div className={s.staffTop}>
                  <span className="avatar" aria-hidden="true">
                    {userInitial(u.display_name)}
                  </span>
                  <div>
                    <div className={s.staffName}>{u.display_name}</div>
                    <div className={s.staffRole}>{u.groups.length > 0 ? u.groups.map(groupLabel).join(", ") : "—"}</div>
                  </div>
                  <span className={`status ${u.killed ? "mute" : "good"} ${s.staffStatus}`}>
                    <span className="dot" />
                    {u.killed ? M.staffOff : M.staffOn}
                  </span>
                </div>
                <div className={s.counts}>
                  {countChips(u).map((c) => (
                    <span key={c.key} className="tag" title={c.title}>
                      {c.text}
                    </span>
                  ))}
                </div>
                <div className={s.staffActions}>
                  <button type="button" className="btn" onClick={() => setViewing(u)}>
                    {M.viewConfig}
                  </button>
                  <button type="button" className="btn" onClick={() => setToggling(u)} disabled={busy}>
                    {u.killed ? M.turnOn : M.turnOff}
                  </button>
                </div>
              </div>
            ))}
          </section>

          <section className={s.card}>
            <div className={s.ack}>
              {saveError && <FormAlert>{saveError}</FormAlert>}
              <label className={s.ackLabel}>
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(e) => {
                    setAck(e.target.checked);
                    if (e.target.checked) setAckMissing(false);
                  }}
                  aria-invalid={ackMissing || undefined}
                  aria-describedby={ackMissing ? "pol-ack-error" : undefined}
                  disabled={busy}
                />
                <span>{M.ackLabel}</span>
              </label>
              {ackMissing && (
                <p className={s.ackError} id="pol-ack-error" role="alert">
                  {M.ackMissing}
                </p>
              )}
              <div className={s.actions}>
                <button type="button" className="btn" onClick={discard} disabled={busy || (!dirty && !ack)}>
                  {M.discard}
                </button>
                <button type="submit" className="btn primary" disabled={busy} aria-busy={busy || undefined}>
                  {busy ? (
                    <>
                      <Icon name="progress_activity" className="spin" />
                      <span>{M.saving}</span>
                    </>
                  ) : serverFailed && saveError && ack ? (
                    M.retrySave
                  ) : (
                    M.save
                  )}
                </button>
              </div>
            </div>
          </section>
        </div>
      </form>

      {killAll && (
        <ConfirmModal
          title={M.killAllConfirmTitle}
          confirmLabel={M.killAllButton}
          danger
          run={() => updateAiPolicy({ base_version: policy.version, global_mode: "off", acknowledge_responsibility: true })}
          onDone={(updated) => {
            setKillAll(false);
            apply(updated);
            setAck(false);
            toast.success(M.killAllDone);
          }}
          onClose={() => setKillAll(false)}
          onReload={() => {
            setKillAll(false);
            void load();
          }}
          noun={M.noun}
        >
          <p>{M.killAllConfirmBody}</p>
          {dirty && <p className="muted">{M.killAllDirty}</p>}
        </ConfirmModal>
      )}

      {toggling && (
        <ConfirmModal
          title={toggling.killed ? M.turnOnTitle(toggling.display_name) : M.turnOffTitle(toggling.display_name)}
          confirmLabel={toggling.killed ? M.turnOn : M.turnOff}
          danger={!toggling.killed}
          run={() => killUserAi(toggling.user_id, !toggling.killed)}
          onDone={() => {
            const who = toggling;
            setToggling(null);
            toast.success(who.killed ? M.turnOnDone(who.display_name) : M.turnOffDone(who.display_name));
            // Chỉ đổi dòng của người này; không đụng phần Chủ đang sửa dở.
            setPolicy((p) => (p ? { ...p, users: p.users.map((x) => (x.user_id === who.user_id ? { ...x, killed: !who.killed } : x)) } : p));
          }}
          onClose={() => setToggling(null)}
          onReload={() => {
            setToggling(null);
            void load();
          }}
          noun={M.noun}
        >
          <p>{toggling.killed ? M.turnOnBody : M.turnOffBody}</p>
        </ConfirmModal>
      )}

      {viewing && <UserConfigModal user={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}
