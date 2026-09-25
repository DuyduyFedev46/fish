"use client";

// Màn Nhân viên (S41, S42): danh sách (lọc đang làm / đã nghỉ / tất cả), tạo tài khoản, sửa hồ sơ, đổi nhóm,
// cho nghỉ / cho làm lại, đặt lại mật khẩu. Page bọc <ViewGuard view="staff"> (cần accounts.manage_staff → 403 do
// ViewGuard vẽ). UI4: danh sách hàng thoáng kiểu Linear (avatar chữ cái, tên, nhãn nhóm nhẹ, chấm trạng thái), chi
// tiết/tạo trong tấm bên, kết quả báo bằng thông báo nổi.

import { useId, useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { SideSheet } from "@/shared/ui/SideSheet";
import { Toast } from "@/shared/ui/Toast";
import { dateTime } from "@/shared/lib/format";
import { useDraft } from "@/shared/lib/useDraft";
import { useResource } from "@/shared/lib/useResource";
import { Icon } from "@/shared/ui/Icon";
import { ResourceView } from "@/shared/ui/ResourceView";
import { Toolbar } from "@/shared/ui/Toolbar";
import { filterStaff, listStaff } from "../api";
import type { StaffFilter, StaffMember } from "../types";
import { EMPTY_CREATE_DRAFT, StaffCreateForm, hasDraftContent, type CreateDraft } from "./StaffCreateForm";
import { StaffDetail } from "./StaffDetail";
import { Avatar, Credentials, GroupTags, StatusLine } from "./parts";
import { STAFF_MSG } from "../messages";
import s from "../staff.module.css";

const FILTERS: { key: StaffFilter; label: string; empty: string; emptyHint: string }[] = [
  {
    key: "active",
    label: "Đang làm",
    empty: "Chưa có nhân viên nào đang làm",
    emptyHint: "Bấm “Thêm nhân viên” để tạo tài khoản đầu tiên.",
  },
  { key: "inactive", label: "Đã nghỉ", empty: "Không có ai đã nghỉ", emptyHint: "Người được cho nghỉ sẽ hiện ở đây." },
  { key: "all", label: "Tất cả", empty: "Chưa có tài khoản nào", emptyHint: "Bấm “Thêm nhân viên” để tạo tài khoản đầu tiên." },
];

function Row({ m, onOpen }: { m: StaffMember; onOpen: () => void }) {
  const name = m.display_name || m.username;
  const metaId = useId();
  return (
    <li className={`${s.row}${m.is_active ? "" : ` ${s.off}`}`}>
      {/* Tên nút chỉ gồm tên + tên đăng nhập (không lẫn với nút lọc "Đang làm"); nhóm, trạng thái là mô tả. */}
      <button
        type="button"
        className={`${s.open} staff-open`}
        onClick={onOpen}
        aria-haspopup="dialog"
        aria-label={`${name}, ${m.username}`}
        aria-describedby={metaId}
      >
        <Avatar name={name} className={s.avatar} />
        <span className={s.name}>
          <b>{name}</b>
          <small>{m.username}</small>
        </span>
        <span className={s.meta} id={metaId}>
          <GroupTags groups={m.groups} />
          <span className={s.status}>
            <StatusLine active={m.is_active} />
            <span className={s.seen}>
              <span className="sr-only">Đăng nhập gần nhất: </span>
              {m.last_login ? <span className="num">{dateTime(m.last_login)}</span> : STAFF_MSG.neverLoggedIn}
            </span>
          </span>
        </span>
      </button>
      {m.phone ? (
        <a className={s.call} href={`tel:${m.phone}`} aria-label={`Gọi ${name}: ${m.phone}`}>
          <Icon name="call" />
          <span className={s.callNum}>{m.phone}</span>
        </a>
      ) : (
        <span className={s.noCall} aria-hidden="true">
          <span className={s.callNum}>—</span>
        </span>
      )}
    </li>
  );
}

/** Khung chờ đúng hình danh sách — dùng vạch `.sk` chung (shared/ui/Skeleton), đứng yên khi giảm chuyển động. */
function Skeleton() {
  return (
    <section className={`sect ${s.list}`} aria-busy="true" aria-label="Danh sách nhân viên">
      <span className="sr-only" role="status">
        Đang tải danh sách nhân viên…
      </span>
      <div className="sect-h" aria-hidden="true">
        <span className="sk sk-s" />
      </div>
      <div className={s.rowsWrap} aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className={s.skel}>
            <span className={`sk ${s.boneAv}`} />
            <span className={s.boneLines}>
              <span className={`sk ${i % 2 ? "sk-s" : "sk-m"}`} />
              <span className={`sk ${i % 3 ? "sk-s" : "sk-m"} ${s.boneSub}`} />
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function StaffScreen() {
  const { me } = useAuth();
  const [filter, setFilter] = useState<StaffFilter>("active");
  const [q, setQ] = useState("");
  // maxAge 0: đổi bộ lọc / mở lại màn luôn tải lại (danh sách đổi sau mỗi thao tác của Chủ).
  const res = useResource(me ? `staff:${me.id}:${filter}` : null, () => listStaff(filter), 0);
  const [openId, setOpenId] = useState<number | null>(null);
  const [snapshot, setSnapshot] = useState<StaffMember | null>(null);
  const [createBusy, setCreateBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [created, setCreated] = useState<{ username: string; password: string } | null>(null);
  const [draft, setDraft, clearDraft, restored] = useDraft<CreateDraft>(me?.id ?? null, "staff:create", EMPTY_CREATE_DRAFT);
  const discarding = useRef(false);

  const current = openId != null ? res.data?.find((m) => m.id === openId) || snapshot : null;
  const fconf = FILTERS.find((f) => f.key === filter)!;

  const open = (m: StaffMember) => {
    setToast(null);
    setSnapshot(m);
    setOpenId(m.id);
  };
  const closeDetail = () => {
    setOpenId(null);
    setSnapshot(null);
  };
  const changed = (message: string) => {
    setToast(message);
    void res.reload();
  };

  const createOpen = draft.open || created !== null;
  const openCreate = () => {
    setToast(null);
    setDraft({ ...draft, open: true });
  };
  // Gọi SAU chuyển động ra của tấm (SideSheet). "Bỏ nháp" đặt cờ trước rồi mới đóng.
  const closeCreate = () => {
    if (created) {
      setCreated(null);
    } else if (discarding.current) {
      discarding.current = false;
      clearDraft();
    } else {
      setDraft({ ...draft, open: false });
    }
  };

  return (
    <div className="screen">
      <p className="view-head">
        Mỗi người một tài khoản riêng. Chọn một hay nhiều nhóm; cho nghỉ thì người đó bị đăng xuất khỏi mọi máy ngay.
      </p>

      <div className={s.bar}>
        <div className="seg" role="group" aria-label="Lọc theo trạng thái">
          {FILTERS.map((f) => (
            <button key={f.key} type="button" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
              {f.label}
            </button>
          ))}
        </div>
        <button type="button" className="btn primary" onClick={openCreate} aria-haspopup="dialog">
          <Icon name="person_add" />
          Thêm nhân viên
        </button>
        <Toolbar
          query={q}
          onQuery={setQ}
          placeholder="Tìm tên, SĐT, nhóm…"
          onRefresh={() => void res.reload()}
          refreshing={res.loading}
        />
      </div>

      {!draft.open && hasDraftContent(draft) && (
        <div className="alert-box info" role="status">
          <Icon name="edit_note" />
          <span>
            Có tài khoản <b>{draft.username.trim() || "mới"}</b> đang tạo dở.{" "}
            <button type="button" className="inline-link" onClick={() => setDraft({ ...draft, open: true })}>
              Tiếp tục
            </button>
          </span>
        </div>
      )}

      {res.data === undefined && res.loading ? (
        <Skeleton />
      ) : (
        <ResourceView res={res}>
          {(rows) => {
            const shown = filterStaff(rows, q);
            const searching = !!q.trim();
            return (
              // aria-busy: đang tải lại danh sách (sau mỗi thao tác) — E2E chờ điều kiện này thay vì ngủ.
              <section className={`sect ${s.list}`} aria-labelledby="staff-h" aria-busy={res.loading}>
                <div className="sect-h">
                  <h2 id="staff-h">Nhân viên</h2>
                  <span className="sub num">
                    {searching ? `${shown.length} / ${rows.length} người khớp` : `${rows.length} người · ${fconf.label.toLowerCase()}`}
                  </span>
                </div>
                {shown.length ? (
                  <ul className={`${s.rows} ${s.rowsWrap} staff-list`}>
                    {shown.map((m) => (
                      <Row key={m.id} m={m} onOpen={() => open(m)} />
                    ))}
                  </ul>
                ) : (
                  <div className={`state ${s.rowsWrap}`}>
                    <span className="state-ic">
                      <Icon name={searching ? "search_off" : filter === "inactive" ? "person_off" : "group"} />
                    </span>
                    <h3 className="state-title">{searching ? "Không ai khớp tìm kiếm" : fconf.empty}</h3>
                    <p>{searching ? `Không có ai khớp “${q.trim()}”. Thử tên khác hoặc số điện thoại.` : fconf.emptyHint}</p>
                    {searching ? (
                      <button type="button" className="btn" onClick={() => setQ("")}>
                        <Icon name="close" />
                        Xoá tìm kiếm
                      </button>
                    ) : filter === "inactive" ? (
                      <button type="button" className="btn" onClick={() => setFilter("active")}>
                        Xem người đang làm
                      </button>
                    ) : null}
                  </div>
                )}
              </section>
            );
          }}
        </ResourceView>
      )}

      {current && (
        <StaffDetail key={current.id} member={current} isSelf={current.id === me?.id} onChanged={changed} onClose={closeDetail} />
      )}

      {createOpen && (
        <SideSheet title="Thêm nhân viên" onClose={closeCreate} busy={createBusy}>
          {(close) =>
            created ? (
              <div className={s.pane}>
                <div className={s.success} role="status">
                  <span className={s.successIcon} aria-hidden="true">
                    <Icon name="check" />
                  </span>
                  <h3>Đã tạo tài khoản {created.username}</h3>
                  <p>Đọc hoặc gửi tên đăng nhập và mật khẩu tạm cho nhân viên. Lần đầu đăng nhập, nhân viên phải đặt mật khẩu mới.</p>
                </div>
                <Credentials username={created.username} password={created.password} passwordLabel="Mật khẩu tạm" />
                <div className={`form-actions ${s.footer}`}>
                  <button type="button" className="btn primary" onClick={close} data-autofocus>
                    Xong
                  </button>
                </div>
              </div>
            ) : (
              <StaffCreateForm
                draft={draft}
                setDraft={setDraft}
                restored={restored}
                onBusy={setCreateBusy}
                onDiscard={() => {
                  discarding.current = true;
                  close();
                }}
                onCreated={(m, password) => {
                  setCreated({ username: m.username, password });
                  clearDraft(); // đã gửi xong → bỏ nháp
                  setToast(STAFF_MSG.created(m.username));
                  void res.reload();
                }}
              />
            )
          }
        </SideSheet>
      )}

      {toast && !current && !createOpen && <Toast key={toast} message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
