"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { JD, JDGap, JDSkill } from "@/lib/types";
import { EntityPicker, type PickItem } from "./entity-picker";
import { CheckIcon, PlusIcon, TrashIcon } from "./icons";
import { useProfile } from "./profile-context";
import { Sheet } from "./sheet";
import { useToast } from "./toast";
import { Button, Card, Chip, EmptyState, ErrorNotice, Skeleton, cx } from "./ui";

const MAX_FILE_BYTES = 200_000;

function AddSheet({ open, onClose, onAdded }: { open: boolean; onClose: () => void; onAdded: () => void }) {
  const { profile } = useProfile();
  const toast = useToast();
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState<PickItem[]>([]);
  const [role, setRole] = useState<PickItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);

  async function readFile(f: File | undefined) {
    if (!f) return;
    if (f.size > MAX_FILE_BYTES) {
      setError("That file is too big. Paste the text of the job description instead.");
      return;
    }
    setError(null);
    setText(await f.text());
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.addJd(profile.user_id, {
        text,
        title: title.trim() || null,
        company_id: company[0]?.id ?? null,
        role_id: role[0]?.id ?? null,
      });
      toast("Added. Its skills are now part of your gaps.");
      setText("");
      setTitle("");
      setCompany([]);
      setRole([]);
      onAdded();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title="Add a job description">
      <div className="space-y-5">
        <div>
          <label htmlFor="jd-text" className="mb-2 block text-[15px] font-semibold">
            Paste the job description
          </label>
          <textarea
            id="jd-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={9}
            maxLength={30000}
            placeholder="Paste the whole posting, or just the requirements."
            className="w-full resize-y rounded-xl border border-line bg-surface p-3.5 text-base leading-relaxed outline-none placeholder:text-muted focus:border-accent"
          />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm text-muted">
            <span>{text.length.toLocaleString()} of 30,000 characters</span>
            <button type="button" onClick={() => file.current?.click()} className="min-h-11 font-semibold text-accent underline underline-offset-4">
              Or open a .txt file
            </button>
            <input ref={file} type="file" accept=".txt,text/plain" aria-label="Open a .txt file" className="sr-only" tabIndex={-1} onChange={(e) => readFile(e.target.files?.[0])} />
          </div>
        </div>

        <div>
          <label htmlFor="jd-title" className="mb-2 block text-[15px] font-semibold">
            Name it <span className="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="jd-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={140}
            placeholder="Brand Manager at HUL"
            className="min-h-11 w-full rounded-xl border border-line bg-surface px-3.5 text-base outline-none placeholder:text-muted focus:border-accent"
          />
        </div>

        <EntityPicker kind="companies" label="Company (optional)" single selected={company} onChange={setCompany} placeholder="Search companies" />
        <EntityPicker kind="roles" label="Role (optional)" single selected={role} onChange={setRole} placeholder="Search roles" />

        {error && (
          <p role="alert" className="text-[15px] text-accent">
            {error}
          </p>
        )}
        <Button variant="primary" className="w-full" disabled={busy || text.trim().length < 40} onClick={submit}>
          {busy ? "Reading it" : "Add job description"}
        </Button>
      </div>
    </Sheet>
  );
}

function SkillChips({ skills, all }: { skills: JDSkill[]; all: boolean }) {
  const shown = all ? skills : skills.slice(0, 8);
  return (
    <ul className="flex flex-wrap gap-1.5">
      {shown.map((s) => (
        <li key={s.capability_id}>
          <span
            className={cx(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold",
              s.user_has_it ? "bg-good-soft text-good" : "border border-line",
            )}
          >
            {s.user_has_it && <CheckIcon width={12} height={12} />}
            {s.name}
          </span>
        </li>
      ))}
      {!all && skills.length > shown.length && <li className="self-center text-xs text-muted">+{skills.length - shown.length} more</li>}
    </ul>
  );
}

function JDCard({ jd, onRemove }: { jd: JD; onRemove: (jd: JD) => void }) {
  const [all, setAll] = useState(false);
  const missing = jd.skills.filter((s) => !s.user_has_it).length;
  const context = [jd.company?.name ?? jd.company_name, jd.role?.title].filter(Boolean).join(" · ");
  return (
    <Card className="rise">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-xl leading-snug">{jd.title ?? "Untitled job"}</h3>
          {context && <p className="mt-0.5 text-sm text-muted">{context}</p>}
        </div>
        <Chip tone={jd.coverage >= 70 ? "good" : "accent"}>{jd.coverage}% covered</Chip>
      </div>
      <p className="mt-3 text-sm text-muted">
        Asks for {jd.skills.length} skills and tools. {missing === 0 ? "You have all of them." : `You're missing ${missing}.`}
      </p>
      <div className="mt-3">
        <SkillChips skills={jd.skills} all={all} />
      </div>
      <div className="mt-3 flex items-center justify-between">
        {jd.skills.length > 8 ? (
          <button type="button" onClick={() => setAll((v) => !v)} aria-expanded={all} className="min-h-11 text-sm font-semibold text-accent">
            {all ? "Show fewer" : "Show all"}
          </button>
        ) : (
          <span />
        )}
        <Button variant="ghost" className="min-h-11 px-2 text-sm" onClick={() => onRemove(jd)} aria-label={`Remove ${jd.title ?? "this job description"}`}>
          <TrashIcon width={16} height={16} />
          Remove
        </Button>
      </div>
    </Card>
  );
}

function GapRow({ gap, onOwn, pending }: { gap: JDGap; onOwn: (gap: JDGap) => void; pending: boolean }) {
  return (
    <li className="py-3.5">
      <div className="flex items-center justify-between gap-3">
        <p className="flex flex-wrap items-center gap-2 font-semibold">
          {gap.name}
          <Chip>{gap.kind}</Chip>
        </p>
        <p className="shrink-0 font-mono text-sm" aria-label={`Asked for in ${gap.jd_count} of ${gap.jd_total} job descriptions`}>
          {gap.jd_count}/{gap.jd_total}
        </p>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-sunken" aria-hidden>
        <div className={cx("h-full rounded-full transition-[width] duration-700", gap.user_has_it ? "bg-good" : "bg-accent")} style={{ width: `${Math.round((gap.jd_count / gap.jd_total) * 100)}%` }} />
      </div>
      <div className="mt-2 flex items-center justify-between gap-3">
        {gap.user_has_it ? (
          <span className="flex items-center gap-1 text-sm font-semibold text-good">
            <CheckIcon width={16} height={16} /> You have this
          </span>
        ) : (
          <span className="text-sm font-semibold text-accent">Missing</span>
        )}
        <Button variant="ghost" className="min-h-9 px-2 text-sm" disabled={pending} onClick={() => onOwn(gap)}>
          {gap.user_has_it ? "Actually, I don't" : "I have this"}
        </Button>
      </div>
    </li>
  );
}

export function JDPanel() {
  const { profile, setProfile } = useProfile();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const owned = profile.capabilities.map((c) => c.id).join(",");
  const jds = useAsync((signal) => api.jds(profile.user_id, signal), `jds:${profile.user_id}:${owned}`);
  const gaps = useAsync((signal) => api.jdGaps(profile.user_id, signal), `jdgaps:${profile.user_id}:${owned}`);

  const refresh = () => {
    jds.reload();
    gaps.reload();
  };

  async function remove(jd: JD) {
    try {
      await api.deleteJd(profile.user_id, jd.id);
      toast("Removed.");
      refresh();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't remove that.");
    }
  }

  async function own(gap: JDGap) {
    setPending(gap.capability_id);
    const ids = profile.capabilities.map((c) => c.id);
    try {
      setProfile(
        await api.putTargets(profile.user_id, {
          domain_ids: profile.domains.map((d) => d.id),
          target_role_ids: profile.target_roles.map((r) => r.id),
          target_company_ids: profile.target_companies.map((c) => c.id),
          capability_ids: gap.user_has_it ? ids.filter((id) => id !== gap.capability_id) : [...ids, gap.capability_id],
        }),
      );
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't update that.");
    } finally {
      setPending(null);
    }
  }

  if (jds.error && !jds.data) return <ErrorNotice message={jds.error.message} onRetry={refresh} />;
  if (!jds.data) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-md text-[15px] text-muted">
          Paste the postings you care about. We read the skills and tools each one names, then show what you&apos;re missing across all of them.
        </p>
        <Button variant="primary" onClick={() => setAdding(true)}>
          <PlusIcon width={18} height={18} /> Add a job description
        </Button>
      </div>

      {jds.data.length === 0 ? (
        <EmptyState title="No job descriptions yet">
          Add two or three for the jobs you want. The skills that show up in most of them are the ones worth learning first.
        </EmptyState>
      ) : (
        <>
          {gaps.data && gaps.data.skills.length > 0 && (
            <Card>
              <h2 className="font-display text-xl">Across your {gaps.data.jd_count === 1 ? "job description" : `${gaps.data.jd_count} job descriptions`}</h2>
              <p className="mt-1 text-[15px]">
                You cover {gaps.data.coverage}% of what they ask for. Skills you lack come first, most requested on top.
              </p>
              <ul className="mt-2 divide-y divide-line">
                {gaps.data.skills.map((g) => (
                  <GapRow key={g.capability_id} gap={g} pending={pending === g.capability_id} onOwn={own} />
                ))}
              </ul>
            </Card>
          )}
          <ul className="space-y-4">
            {jds.data.map((jd) => (
              <li key={jd.id}>
                <JDCard jd={jd} onRemove={remove} />
              </li>
            ))}
          </ul>
        </>
      )}

      <AddSheet open={adding} onClose={() => setAdding(false)} onAdded={refresh} />
    </div>
  );
}
