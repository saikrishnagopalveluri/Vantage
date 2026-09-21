"use client";

import { useState } from "react";
import { DomainGrid } from "@/components/domain-grid";
import { EntityPicker, fromCapability, fromCompany, fromRole, type PickItem } from "@/components/entity-picker";
import { InstallCard } from "@/components/install-card";
import { PartnerBadge } from "@/components/partner-badge";
import { useProfile } from "@/components/profile-context";
import { Sheet } from "@/components/sheet";
import { useToast } from "@/components/toast";
import { Button, Card, Chip, LinkButton, PageHeader, Segmented } from "@/components/ui";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import Link from "next/link";
import { clearSession, isAccount, rememberDeletion } from "@/lib/session";
import { setTheme, useTheme, type Theme } from "@/lib/theme";
import { openQuiz } from "@/lib/triple-tap";
import type { Profile } from "@/lib/types";

function PlacementSheet({ profile, open, onClose }: { profile: Profile; open: boolean; onClose: () => void }) {
  const { reload } = useProfile();
  const toast = useToast();
  const placing = profile.profile_status === "targeting";
  const [company, setCompany] = useState<PickItem[]>([]);
  const [role, setRole] = useState<PickItem[]>([]);
  const [industryId, setIndustryId] = useState("");
  const [clearTargets, setClearTargets] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const industries = useAsync((signal) => api.industries(signal), "industries");

  const needsIndustry = company[0] !== undefined && !company[0].hint;
  const ready = company.length === 1 && role.length === 1 && (!needsIndustry || industryId !== "");

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.placement(profile.user_id, {
        company_id: company[0].id,
        role_id: role[0].id,
        industry_id: needsIndustry ? industryId : null,
        clear_targets: placing && clearTargets,
      });
      toast(
        result.event_type === "unchanged"
          ? "That's already your current job."
          : placing
            ? "Congratulations. Your feed now follows your new job."
            : "Job updated.",
      );
      reload();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title={placing ? "I got the job" : "I changed jobs"}>
      <div className="space-y-5">
        <EntityPicker kind="companies" label="Company" single selected={company} onChange={setCompany} placeholder="Search companies" />
        <EntityPicker kind="roles" label="Role" single selected={role} onChange={setRole} placeholder="Search roles" />
        {needsIndustry && (
          <div>
            <label htmlFor="placement-industry" className="mb-2 block text-[15px] font-semibold">
              Industry
            </label>
            <select
              id="placement-industry"
              value={industryId}
              onChange={(e) => setIndustryId(e.target.value)}
              className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 text-base"
            >
              <option value="">Choose an industry</option>
              {(industries.data ?? []).map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
          </div>
        )}
        {placing && (
          <label className="flex min-h-11 cursor-pointer items-center gap-3 text-[15px]">
            <input type="checkbox" checked={clearTargets} onChange={(e) => setClearTargets(e.target.checked)} className="size-5 accent-[var(--accent)]" />
            Clear my target roles and companies
          </label>
        )}
        {error && (
          <p role="alert" className="text-[15px] text-accent">
            {error}
          </p>
        )}
        <Button variant="primary" className="w-full" disabled={!ready || busy} onClick={submit}>
          {busy ? "Saving" : "Confirm"}
        </Button>
      </div>
    </Sheet>
  );
}

function TargetsEditor({ profile }: { profile: Profile }) {
  const { setProfile } = useProfile();
  const toast = useToast();
  const [domainIds, setDomainIds] = useState<string[]>(() => profile.domains.map((d) => d.id));
  const [roles, setRoles] = useState<PickItem[]>(() => profile.target_roles.map(fromRole));
  const [companies, setCompanies] = useState<PickItem[]>(() => profile.target_companies.map(fromCompany));
  const [skills, setSkills] = useState<PickItem[]>(() => profile.capabilities.map(fromCapability));
  const [busy, setBusy] = useState(false);

  const ids = (items: { id: string }[]) => items.map((i) => i.id).sort().join(",");
  const dirty =
    [...domainIds].sort().join(",") !== ids(profile.domains) ||
    ids(roles) !== ids(profile.target_roles) ||
    ids(companies) !== ids(profile.target_companies) ||
    ids(skills) !== ids(profile.capabilities);

  async function save() {
    setBusy(true);
    try {
      setProfile(
        await api.putTargets(profile.user_id, {
          domain_ids: domainIds,
          target_role_ids: roles.map((r) => r.id),
          target_company_ids: companies.map((c) => c.id),
          capability_ids: skills.map((s) => s.id),
        }),
      );
      toast("Saved. Your feed and skill gaps are updated.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't save.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="space-y-7">
      <div>
        <h2 className="font-display text-xl">Fields you follow</h2>
        <p className="mb-3 mt-1 text-sm text-muted">Up to four. These decide which stories reach you, even ones that don&apos;t name your role.</p>
        <DomainGrid stickyClass="top-12 md:top-0" selected={domainIds} onToggle={(id) => setDomainIds((cur) => (cur.includes(id) ? cur.filter((i) => i !== id) : [...cur, id]))} />
      </div>
      <EntityPicker kind="roles" label="Target roles" selected={roles} onChange={setRoles} placeholder="Search roles" domainIds={domainIds} suggested />
      <EntityPicker kind="companies" label="Target companies" selected={companies} onChange={setCompanies} placeholder="Search companies" domainIds={domainIds} suggested />
      <EntityPicker kind="capabilities" label="Skills and tools I have" selected={skills} onChange={setSkills} placeholder="Search skills and tools" domainIds={domainIds} suggested />
      <Button variant="primary" disabled={!dirty || busy} onClick={save}>
        {busy ? "Saving" : dirty ? "Save changes" : "Nothing to save"}
      </Button>
    </Card>
  );
}

function YourDataCard() {
  const { profile } = useProfile();
  const toast = useToast();
  const account = isAccount();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setBusy(true);
    try {
      const blob = await api.exportData();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "vantage-my-data.json";
      link.click();
      URL.revokeObjectURL(url);
      toast("Your data is downloading.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't prepare your data.");
    } finally {
      setBusy(false);
    }
  }

  async function erase() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteAccount(account ? password : undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't delete that. Try again.");
      setBusy(false);
      return;
    }
    rememberDeletion();
    clearSession();
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- a full load on purpose
    window.location.href = "/";
  }

  return (
    <Card>
      <h2 className="font-display text-xl">Your data</h2>
      <p className="mt-2 text-[15px] text-muted">
        It is yours. Download everything we hold about you, or delete it all. Read how we use it in the{" "}
        <Link href="/privacy" className="font-semibold text-accent underline underline-offset-4">
          Privacy Policy
        </Link>{" "}
        and the{" "}
        <Link href="/terms" className="font-semibold text-accent underline underline-offset-4">
          Terms of Use
        </Link>
        .
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={download} disabled={busy}>
          Download my data
        </Button>
        <Button
          onClick={() => {
            setPassword("");
            setError(null);
            setConfirming(true);
          }}
        >
          Delete my account and data
        </Button>
      </div>

      <Sheet open={confirming} onClose={() => setConfirming(false)} title="Delete everything?">
        <div className="space-y-4">
          <p className="text-[15px] leading-relaxed">
            This permanently deletes {account ? "your account, " : ""}your profile{profile.target_roles.length ? ` (including ${profile.target_roles.length} target role${profile.target_roles.length === 1 ? "" : "s"})` : ""}, your
            saved and hidden stories and any job descriptions. It can&apos;t be undone.
          </p>
          {account && (
            <div>
              <label htmlFor="confirm-password" className="mb-2 block text-[15px] font-semibold">
                Enter your password to confirm
              </label>
              <input
                id="confirm-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="min-h-11 w-full rounded-xl border border-line bg-surface px-3.5 text-base outline-none focus:border-accent"
              />
            </div>
          )}
          {error && (
            <p role="alert" className="text-[15px] text-accent">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" onClick={erase} disabled={busy || (account && password.length === 0)}>
              {busy ? "Deleting" : "Yes, delete everything"}
            </Button>
            <Button variant="ghost" onClick={() => setConfirming(false)} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      </Sheet>
    </Card>
  );
}

function AccountCard() {
  const toast = useToast();
  const account = isAccount();
  const me = useAsync((signal) => (account ? api.me(signal) : Promise.resolve(null)), `me:${account}`);
  const [confirmReset, setConfirmReset] = useState(false);
  const [busy, setBusy] = useState(false);

  async function logOut() {
    setBusy(true);
    try {
      await api.logout();
    } catch {
      // The cookie is only cleared by the server, so if it can't be reached say so instead of pretending.
      toast("Couldn't reach the server to log you out. Try again.");
      setBusy(false);
      return;
    }
    clearSession();
    // A full load, so the signed-out layout can't redirect to the login page first.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- a full load on purpose
    window.location.href = "/";
  }

  if (account) {
    return (
      <Card>
        <h2 className="font-display text-xl">Your account</h2>
        <p className="mt-2 text-[15px] text-muted">
          {me.data ? (
            <>
              Signed in as <strong className="text-ink">{me.data.email}</strong>. Log in with it on any device to get your profile back.
            </>
          ) : (
            "Signed in. Log in on any device to get your profile back."
          )}
        </p>
        <Button className="mt-4" onClick={logOut} disabled={busy}>
          {busy ? "Logging out" : "Log out"}
        </Button>
      </Card>
    );
  }

  return (
    <Card>
      <h2 className="font-display text-xl">This device</h2>
      <p className="mt-2 text-[15px] text-muted">
        You&apos;re using Vantage as a guest, so this device holds the only key to your profile. If you reset it, you start over. An account
        lets you keep a profile safe and use it anywhere. It starts fresh, so you would pick your fields again.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <LinkButton href="/login?mode=signup" variant="primary">
          Create an account
        </LinkButton>
        {confirmReset ? (
          <>
            <Button
              onClick={() => {
                clearSession();
                // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- a full load on purpose
                window.location.href = "/";
              }}
            >
              Yes, reset this device
            </Button>
            <Button variant="ghost" onClick={() => setConfirmReset(false)}>
              Cancel
            </Button>
          </>
        ) : (
          <Button onClick={() => setConfirmReset(true)}>Reset this device</Button>
        )}
      </div>
    </Card>
  );
}

export default function ProfilePage() {
  const { profile } = useProfile();
  const theme = useTheme();
  const [sheetOpen, setSheetOpen] = useState(false);
  const placed = profile.profile_status === "placed";

  // Remount the editor whenever the saved profile changes underneath it.
  const editorKey = [profile.domains, profile.target_roles, profile.target_companies, profile.capabilities]
    .map((list) => list.map((i) => i.id).join(","))
    .join("|");

  return (
    <div className="max-w-3xl space-y-5">
      <PageHeader eyebrow="Profile" title="Your profile" />

      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={placed ? "good" : "accent"}>{placed ? "Working" : "Job hunting"}</Chip>
          {placed && profile.current_industry && <Chip>{profile.current_industry.name}</Chip>}
        </div>
        <p className="mt-3 font-display text-2xl leading-snug">
          {placed
            ? `${profile.current_role?.title ?? "Working"} at ${profile.current_company?.name ?? "your company"}`
            : profile.target_roles.length
              ? `Aiming for ${profile.target_roles.map((r) => r.title).join(", ")}`
              : "Still exploring roles"}
        </p>
        <p className="mt-1 text-[15px] text-muted">
          {placed
            ? "Your feed leans toward your company, your role and your industry."
            : "Your feed leans toward your target companies, your roles and the skills you're missing."}
        </p>
        <Button variant={placed ? "secondary" : "primary"} className="mt-4" onClick={() => setSheetOpen(true)}>
          {placed ? "I changed jobs" : "I got the job"}
        </Button>
      </Card>

      <PlacementSheet key={profile.profile_status + (profile.current_company?.id ?? "")} profile={profile} open={sheetOpen} onClose={() => setSheetOpen(false)} />

      <TargetsEditor key={editorKey} profile={profile} />

      <Card>
        <h2 className="font-display text-xl">Appearance</h2>
        <p className="mb-3 mt-1 text-sm text-muted">System follows your device.</p>
        <Segmented<Theme>
          label="Theme"
          value={theme}
          onChange={setTheme}
          options={[
            { id: "system", label: "System" },
            { id: "light", label: "Light" },
            { id: "dark", label: "Dark" },
          ]}
        />
      </Card>

      <InstallCard />

      <Card>
        <h2 className="font-display text-xl">Pop quiz</h2>
        <p className="mt-2 text-[15px] text-muted">
          Questions from your own fields, roles and companies, plus a few management basics. Keep going until you get three wrong. It gets harder as you go, and you can post your score when you are done.
        </p>
        <Button variant="primary" className="mt-3" onClick={openQuiz}>
          Play the pop quiz
        </Button>
      </Card>

      <Card>
        <h2 className="font-display text-xl">About the data</h2>
        <p className="mt-2 text-[15px] text-muted">
          Job titles, tools and skills include information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and
          Training Administration, used under the CC BY 4.0 license. Company names come from SEC EDGAR, the NSE equity list and Wikidata.
          Skill lists describe typical US jobs, so treat them as a starting point.
        </p>
        <PartnerBadge className="mt-4 border-t border-line pt-4" />
      </Card>

      <YourDataCard />

      <AccountCard />
    </div>
  );
}
