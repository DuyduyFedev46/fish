"use client";

// Màn "AI của tôi" (ED-06 / W4b): /ai/settings/. Thẻ trạng thái + "Tắt trợ lý/Bật lại" (hộp xác nhận) · bảng chú giải mức ·
// mỗi nhóm một bảng Việc · Loại · Ghi chú · Mức tự chủ (nhóm nút radio; mức bị khoá vẫn hiện, kèm ổ khoá và lý do) ·
// ngưỡng tự làm (chỉ khi việc ở mức Tự ghi) · tích cam kết rồi "Lưu cài đặt".
// Logic mức/ngưỡng/thân PUT giữ nguyên ở ./levels.ts và ./payload.ts (BE thay thế toàn bộ cấu hình mỗi lần lưu).
// Không dữ liệu cá nhân nào ở đây; không ghi storage/URL/log.

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { ACCOUNT_HREF } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { Icon } from "@/shared/ui/Icon";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { useToast } from "@/shared/ui/overlay/Toast";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorBox } from "@/shared/ui/StateBox";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { commandLabel } from "../../commandLabels";
import { getMyConfig, killMyConfig, updateMyConfig } from "../api";
import { describeSaveError, displayLevel, limitFieldsOf, type LimitField } from "../levels";
import { MY_AI_MSG as M } from "../messages";
import { buildMyConfigPayload, readLimitInputs, type LimitInputs } from "../payload";
import { LEVEL_LEGEND, LIMIT_LABEL, LIMIT_UNIT, isDirty, levelChoices, limitErrors, lockNote } from "../view";
import type { MyConfig, MyConfigCommandItem } from "../../types";
import s from "../myConfig.module.css";

type Base = { overrides: Record<string, string>; limits: LimitInputs };

function baseOf(data: MyConfig): Base {
  const overrides: Record<string, string> = {};
  const limits: LimitInputs = {};
  for (const grp of data.groups) {
    for (const cmd of grp.commands) {
      if (cmd.source === "override") overrides[cmd.id] = cmd.level;
      if (cmd.limits) limits[cmd.id] = readLimitInputs(cmd.limits);
    }
  }
  return { overrides, limits };
}

function CommandRow({
  config,
  cmd,
  level,
  limits,
  errors,
  onLevel,
  onLimit,
  disabled,
}: {
  config: MyConfig;
  cmd: MyConfigCommandItem;
  level: string;
  limits: LimitInputs;
  errors: Record<string, string>;
  onLevel: (level: string) => void;
  onLimit: (field: LimitField, value: string) => void;
  disabled: boolean;
}) {
  const choices = levelChoices(config, cmd, level);
  const current = displayLevel(config, cmd, level);
  const note = lockNote(config, cmd);
  const fields = limitFieldsOf(cmd);
  return (
    <div className={s.item} data-command={cmd.id}>
      <div className={s.row}>
        <div className={s.name}>
          {commandLabel(cmd.id, cmd.title)}
          {cmd.red_zone && <span className={`tag ${s.kind}`}> {M.redZone}</span>}
        </div>
        <div className={s.kind}>
          <span className="tag">{cmd.kind === "read" ? M.kindRead : M.kindWrite}</span>
        </div>
        <div className={s.note}>
          {note ? (
            <>
              <Icon name="lock" />
              <span>{note}</span>
            </>
          ) : (
            <span className="muted">—</span>
          )}
        </div>
        <div className={s.levels} role="radiogroup" aria-label={M.levelGroupLabel(commandLabel(cmd.id, cmd.title))}>
          {choices.map((c) => (
            <label key={c.level} className={s.level}>
              <input
                type="radio"
                name={`level-${cmd.id}`}
                value={c.level}
                checked={c.selected}
                disabled={c.locked || disabled}
                onChange={() => onLevel(c.level)}
              />
              <span className={s.levelFace}>
                {c.locked && <Icon name="lock" />}
                {c.label}
              </span>
            </label>
          ))}
        </div>
      </div>
      {fields.length > 0 && current === "B" && (
        <div className={s.limits}>
          <p className={s.limitsTitle}>{M.limitsTitle}</p>
          <div className={s.limitsGrid}>
            {fields.map((f) => (
              <Field
                key={f}
                label={LIMIT_LABEL[f]}
                type="number"
                unit={LIMIT_UNIT[f]}
                value={limits[cmd.id]?.[f] ?? ""}
                onChange={(v) => onLimit(f, v)}
                error={errors[`${cmd.id}.${f}`]}
                disabled={disabled}
              />
            ))}
          </div>
          <p className={s.limitsHint}>{M.limitsHint}</p>
        </div>
      )}
    </div>
  );
}

export default function MyConfigScreen() {
  const toast = useToast();
  const [config, setConfig] = useState<MyConfig | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [limits, setLimits] = useState<LimitInputs>({});
  const [base, setBase] = useState<Base>({ overrides: {}, limits: {} });
  const [ack, setAck] = useState(false);
  const [ackMissing, setAckMissing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  // Lỗi do MÁY CHỦ trả về mới có nút "Thử lại"; lỗi ngưỡng tự kiểm thì nút vẫn là "Lưu cài đặt".
  const [serverFailed, setServerFailed] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [killTarget, setKillTarget] = useState<boolean | null>(null);

  const apply = useCallback((data: MyConfig) => {
    const b = baseOf(data);
    setConfig(data);
    setBase(b);
    setOverrides(b.overrides);
    setLimits(b.limits);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      apply(await getMyConfig());
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

  const errors = useMemo(() => (config ? limitErrors(config, overrides, limits) : {}), [config, overrides, limits]);
  const dirty = config ? isDirty(config, overrides, limits, base.overrides, base.limits) : false;

  if (loading && !config) {
    return (
      <SkeletonScreen label="Đang tải cài đặt AI…">
        <SkeletonTable rows={4} cols={4} />
      </SkeletonScreen>
    );
  }
  if (!config) {
    const forbidden = loadError instanceof ApiError && loadError.status === 403;
    return <ErrorBox icon={forbidden ? "lock" : undefined} message={loadError ? loadErrorText(loadError) : M.loadFailed} onRetry={() => void load()} />;
  }

  const setLevel = (id: string, level: string) => setOverrides((prev) => ({ ...prev, [id]: level }));
  const setLimit = (id: string, field: LimitField, value: string) =>
    setLimits((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), [field]: value } }));

  const discard = () => {
    setOverrides(base.overrides);
    setLimits(base.limits);
    setAck(false);
    setAckMissing(false);
    setShowErrors(false);
    setSaveError(null);
    setServerFailed(false);
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    setShowErrors(true);
    setAckMissing(!ack);
    if (Object.keys(errors).length > 0) {
      setSaveError(M.limitsInvalid);
      return;
    }
    if (!ack) {
      setSaveError(null);
      return;
    }
    setSaving(true);
    setSaveError(null);
    setServerFailed(false);
    const payload = buildMyConfigPayload(config, { overrides, limits });
    try {
      const updated = await updateMyConfig(payload);
      apply(updated);
      setAck(false);
      setShowErrors(false);
      setConflict(false);
      toast.success(M.saved(updated.version));
    } catch (err) {
      if (err instanceof ApiError && err.code === "AI_CONFIG_CONFLICT") setConflict(true);
      else {
        setSaveError(describeSaveError(err, config, payload));
        setServerFailed(true);
      }
    } finally {
      setSaving(false);
    }
  };

  const killed = config.killed;
  const busy = saving;
  // Chủ tắt AI cả vựa thì trạng thái chính phải nói đúng điều đó, không được ghi "đang bật" trong khi banner báo tắt.
  const globalOff = !config.ai_enabled;
  const headOff = globalOff || killed;
  const headText = globalOff ? M.statusGlobalOff : killed ? M.statusOff : M.statusOn;

  return (
    <div className={s.page}>
      <Link href={ACCOUNT_HREF} className={s.back}>
        <Icon name="arrow_back" />
        {M.back}
      </Link>

      {!config.ai_enabled && (
        <div className="alert-box info" role="status">
          <Icon name="info" />
          <span>{M.globalOff}</span>
        </div>
      )}
      {conflict && <ConflictBanner noun={M.noun} onReload={() => void load()} />}

      <section className={s.head} aria-label={M.subtitle}>
        <span className={`${s.headIcon} ${headOff ? s.headIconOff : ""}`}>
          <Icon name="auto_awesome" />
        </span>
        <div className={s.headBody}>
          <div className={s.headTitle}>
            <span>{headText}</span>
            <span className={`status ${headOff ? "mute" : "good"}`}>
              <span className="dot" />
              {headOff ? M.chipOff : M.chipOn}
            </span>
          </div>
          <div className={s.headMeta}>
            <span>{M.savedAt}</span>
            <span className="num">{dateTime(config.updated_at)}</span>
          </div>
        </div>
        <button type="button" className="btn" onClick={() => setKillTarget(!killed)} disabled={busy}>
          <Icon name="block" />
          {killed ? M.turnOn : M.turnOff}
        </button>
      </section>

      {killed && (
        <div className="alert-box warn" role="status">
          <Icon name="warning" />
          <span>{M.killedBanner}</span>
        </div>
      )}

      <section className={s.legend} aria-label={M.legendLabel}>
        <div className={`${s.legendRow} ${s.legendHead}`}>
          <div>{M.legendLevel}</div>
          <div>{M.legendMeaning}</div>
        </div>
        {LEVEL_LEGEND.map((l) => (
          <div key={l.name} className={s.legendRow}>
            <div className={s.legendName}>{l.name}</div>
            <div className={s.legendText}>{l.meaning}</div>
          </div>
        ))}
      </section>

      <form onSubmit={save} className={s.page} noValidate>
        {config.groups.map((grp) => (
          <section key={grp.group} className={s.group} aria-labelledby={`grp-${grp.group}`}>
            <div className={s.groupHead}>
              <h2 id={`grp-${grp.group}`}>{grp.label}</h2>
              <span className={s.groupCount}>{M.tasksCount(grp.commands.length)}</span>
            </div>
            {grp.commands.length === 0 ? (
              <p className={s.groupEmpty}>{M.groupEmpty}</p>
            ) : (
              <>
                <div className={s.cols} aria-hidden="true">
                  <div>{M.colTask}</div>
                  <div>{M.colKind}</div>
                  <div>{M.colNote}</div>
                  <div>{M.colLevel}</div>
                </div>
                {grp.commands.map((cmd) => (
                  <CommandRow
                    key={cmd.id}
                    config={config}
                    cmd={cmd}
                    level={overrides[cmd.id] || cmd.level}
                    limits={limits}
                    errors={showErrors ? errors : {}}
                    onLevel={(lv) => setLevel(cmd.id, lv)}
                    onLimit={(f, v) => setLimit(cmd.id, f, v)}
                    disabled={busy}
                  />
                ))}
              </>
            )}
          </section>
        ))}

        <section className={s.ack}>
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
              aria-describedby={ackMissing ? "ack-error" : undefined}
              disabled={busy}
            />
            <span>{M.ackLabel}</span>
          </label>
          {ackMissing && (
            <p className={s.ackError} id="ack-error" role="alert">
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
        </section>
      </form>

      {killTarget !== null && (
        <ConfirmModal
          title={killTarget ? M.offTitle : M.onTitle}
          confirmLabel={killTarget ? M.offConfirm : M.onConfirm}
          danger={killTarget}
          run={() => killMyConfig(killTarget)}
          onDone={() => {
            const next = killTarget;
            setKillTarget(null);
            toast.success(next ? M.offDone : M.onDone);
            void load();
          }}
          onClose={() => setKillTarget(null)}
          onReload={() => {
            setKillTarget(null);
            void load();
          }}
          noun={M.noun}
        >
          <p>{killTarget ? M.offBody : M.onBody}</p>
        </ConfirmModal>
      )}
    </div>
  );
}
