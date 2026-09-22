"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ConsentFields } from "@/components/consent-fields";
import { DomainGrid } from "@/components/domain-grid";
import { EntityPicker, type PickItem } from "@/components/entity-picker";
import { Logo } from "@/components/icons";
import { Button, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { clearSession, createUserId, getUserId, isAccount, setUserId, useIsAccount } from "@/lib/session";
import type { ConsentBody } from "@/lib/types";

type Persona = "student" | "professional";
type StepId = "persona" | "current" | "fields" | "roles" | "companies" | "skills";

const STEPS: Record<Persona, StepId[]> = {
  student: ["persona", "fields", "roles", "companies", "skills"],
  professional: ["persona", "current", "fields", "roles", "companies", "skills"],
};

const PERSONAS: { id: Persona; title: string; body: string }[] = [
  { id: "student", title: "I'm a student", body: "I'm studying management (MBA, PGDM or similar) or preparing for my first job, and want to know what to learn and who is hiring." },
  { id: "professional", title: "I have a job", body: "I want to keep up with my company, my field and whatever I might move to next." },
];

function Heading({ title, hint }: { title: string; hint?: string }) {
  return (
    <>
      <h1 className="font-display text-[30px] leading-[1.1] md:text-4xl">{title}</h1>
      {hint && <p className="mt-2 max-w-lg text-[15px] leading-relaxed text-muted">{hint}</p>}
    </>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const [persona, setPersona] = useState<Persona | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [domainIds, setDomainIds] = useState<string[]>([]);
  const [roles, setRoles] = useState<PickItem[]>([]);
  const [companies, setCompanies] = useState<PickItem[]>([]);
  const [skills, setSkills] = useState<PickItem[]>([]);
  const [currentCompany, setCurrentCompany] = useState<PickItem[]>([]);
  const [currentRole, setCurrentRole] = useState<PickItem[]>([]);
  const [industryId, setIndustryId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consent, setConsent] = useState<ConsentBody | null>(null);
  const signedIn = useIsAccount();

  const steps = STEPS[persona ?? "student"];
  const step = steps[stepIndex];
  const last = stepIndex === steps.length - 1;
  const needsIndustry = currentCompany[0] !== undefined && !currentCompany[0].hint;
  const industries = useAsync((signal) => api.industries(signal), "industries");
  const toggleDomain = (id: string) =>
    setDomainIds((ids) => (ids.includes(id) ? ids.filter((i) => i !== id) : [...ids, id]));

  const canContinue =
    step === "persona"
      ? persona !== null && (signedIn || consent !== null)
      : step === "current"
        ? currentCompany.length === 1 && currentRole.length === 1 && (!needsIndustry || industryId !== "")
        : step === "fields"
          ? domainIds.length > 0
          : true;

  async function finish() {
    setBusy(true);
    setError(null);
    const account = isAccount() && getUserId() !== null;
    if (!account) setUserId(createUserId());
    try {
      await api.onboard({
        domain_ids: domainIds,
        target_role_ids: roles.map((r) => r.id),
        target_company_ids: companies.map((c) => c.id),
        capability_ids: skills.map((s) => s.id),
        consent: account ? null : consent,
        current:
          persona === "professional" && currentCompany[0] && currentRole[0]
            ? { company_id: currentCompany[0].id, role_id: currentRole[0].id, industry_id: needsIndustry ? industryId : null }
            : null,
      });
      router.replace("/feed");
    } catch (e) {
      if (!account) clearSession();
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setBusy(false);
    }
  }

  const next = () => (last ? finish() : setStepIndex((i) => i + 1));

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="pt-safe px-safe">
        <div className="mx-auto flex h-14 w-full max-w-xl items-center gap-2.5">
          <Link href="/" className="flex items-center gap-2.5" aria-label="Vantage home">
            <Logo size={28} />
            <span className="font-display text-xl">Vantage</span>
          </Link>
          {!persona && (
            <Link href="/login" className="ml-auto inline-flex min-h-11 items-center text-[15px] font-semibold text-accent">
              Log in
            </Link>
          )}
          {persona && (
            <span className="ml-auto font-mono text-xs text-muted" aria-live="polite">
              {stepIndex + 1} of {steps.length}
            </span>
          )}
        </div>
        {persona && (
          <div className="mx-auto h-1 w-full max-w-xl overflow-hidden rounded-full bg-sunken" role="progressbar" aria-valuemin={1} aria-valuemax={steps.length} aria-valuenow={stepIndex + 1}>
            <div className="h-full rounded-full bg-accent transition-[width] duration-500" style={{ width: `${((stepIndex + 1) / steps.length) * 100}%` }} />
          </div>
        )}
      </header>

      <main className="px-safe mx-auto w-full max-w-xl flex-1 py-6 md:py-10">
        <div key={step} className="rise">
          {step === "persona" && (
            <>
              <Heading title="Career news that fits you." hint="Vantage reads business and tech news, then tells you why each story matters for your job hunt or your job." />
              <p className="mt-5 text-[15px] font-semibold">Where are you right now?</p>
              <div className="mt-3 grid gap-3" role="radiogroup" aria-label="Where are you right now?">
                {PERSONAS.map((p) => (
                  <button
                    key={p.id}
                    role="radio"
                    aria-checked={persona === p.id}
                    onClick={() => setPersona(p.id)}
                    className={cx(
                      "rounded-2xl border p-4 text-left transition-[transform,border-color,background-color] duration-200 active:scale-[0.99]",
                      persona === p.id ? "border-accent bg-accent-soft" : "raised hover:border-muted",
                    )}
                  >
                    <span className="font-display text-xl">{p.title}</span>
                    <span className="mt-1 block text-[15px] text-muted">{p.body}</span>
                  </button>
                ))}
              </div>
              {!signedIn && (
                <div className="mt-6">
                  <ConsentFields onChange={setConsent} />
                </div>
              )}
            </>
          )}

          {step === "current" && (
            <>
              <Heading title="Where do you work?" hint="Your company, role and industry will lead your feed." />
              <div className="mt-6 space-y-6">
                <EntityPicker kind="companies" label="Company" single selected={currentCompany} onChange={setCurrentCompany} placeholder="Search companies" />
                <EntityPicker kind="roles" label="Your role" single selected={currentRole} onChange={setCurrentRole} placeholder="Search roles" />
                {needsIndustry && (
                  <div>
                    <label htmlFor="industry" className="mb-2 block text-[15px] font-semibold">
                      Industry
                    </label>
                    <select
                      id="industry"
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
              </div>
            </>
          )}

          {step === "fields" && (
            <>
              <Heading
                title={persona === "student" ? "Which fields interest you?" : "Which fields do you follow?"}
                hint="Pick up to four. This decides which stories you see and which roles we list next."
              />
              <div className="mt-6">
                <DomainGrid selected={domainIds} onToggle={toggleDomain} />
              </div>
              {domainIds.length === 0 && <p className="mt-4 text-sm text-muted">Pick at least one to continue.</p>}
            </>
          )}

          {step === "roles" && (
            <>
              <Heading
                title={persona === "student" ? "Which roles do you want?" : "Any roles you're aiming for?"}
                hint={persona === "student" ? "Add as many as you like. If you're not sure yet, skip this and add them later." : "Optional. It sharpens your skill gaps."}
              />
              <div className="mt-6">
                <EntityPicker kind="roles" label="Target roles" selected={roles} onChange={setRoles} placeholder="Search roles" domainIds={domainIds} suggested />
              </div>
            </>
          )}

          {step === "companies" && (
            <>
              <Heading
                title={persona === "student" ? "Which companies do you want to work for?" : "Any companies you're watching?"}
                hint="We'll rank their news higher and compare what each one asks for."
              />
              <div className="mt-6">
                <EntityPicker kind="companies" label="Companies" selected={companies} onChange={setCompanies} placeholder="Search companies" domainIds={domainIds} suggested />
              </div>
            </>
          )}

          {step === "skills" && (
            <>
              <Heading title="What can you already do?" hint="Add the skills and tools you're comfortable with. Anything the roles ask for that you skip shows up as a gap." />
              <div className="mt-6">
                <EntityPicker kind="capabilities" label="Skills and tools" selected={skills} onChange={setSkills} placeholder="Search skills and tools" domainIds={domainIds} suggested />
              </div>
            </>
          )}
        </div>

        {error && (
          <p role="alert" className="raised mt-5 rounded-xl p-3 text-[15px]">
            {error}
          </p>
        )}
      </main>

      <footer className="pb-safe sticky bottom-0 border-t border-line bg-paper">
        <div className="px-safe mx-auto flex w-full max-w-xl items-center gap-3 py-3">
          {stepIndex > 0 && (
            <Button variant="ghost" onClick={() => setStepIndex((i) => i - 1)} disabled={busy}>
              Back
            </Button>
          )}
          <Button variant="primary" className="ml-auto min-w-40 flex-1 sm:flex-none" onClick={next} disabled={!canContinue || busy}>
            {busy ? "Setting things up" : last ? "Show me my feed" : "Continue"}
          </Button>
        </div>
      </footer>
    </div>
  );
}
