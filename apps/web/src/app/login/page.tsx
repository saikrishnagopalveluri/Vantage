"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { ConsentFields } from "@/components/consent-fields";
import { Logo } from "@/components/icons";
import { PartnerBadge } from "@/components/partner-badge";
import { Button, Segmented } from "@/components/ui";
import { api } from "@/lib/api";
import { setUserId } from "@/lib/session";
import type { ConsentBody } from "@/lib/types";

type Mode = "login" | "signup";

const COPY: Record<Mode, { title: string; hint: string; button: string; busy: string }> = {
  login: {
    title: "Welcome back",
    hint: "Log in to pick up your feed and skill gaps where you left them.",
    button: "Log in",
    busy: "Logging in",
  },
  signup: {
    title: "Make your account",
    hint: "An account keeps your profile safe and lets you use it on any device.",
    button: "Create account",
    busy: "Creating your account",
  },
};

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [mode, setMode] = useState<Mode>(params.get("mode") === "signup" ? "signup" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consent, setConsent] = useState<ConsentBody | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (mode === "signup" && !consent) return;
    setBusy(true);
    setError(null);
    try {
      const result = mode === "login" ? await api.login(email, password) : await api.signup(email, password, consent!);
      setUserId(result.user_id, true);
      router.replace(result.onboarded ? "/feed" : "/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  const copy = COPY[mode];

  return (
    <main className="px-safe mx-auto w-full max-w-md flex-1 py-8 md:py-14">
      <div key={mode} className="rise">
        <h1 className="font-display text-[32px] leading-[1.1] md:text-4xl">{copy.title}</h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted">{copy.hint}</p>
      </div>

      <div className="mt-6">
        <Segmented
          label="Log in or create an account"
          value={mode}
          onChange={(m) => {
            setMode(m);
            setError(null);
          }}
          options={[
            { id: "login", label: "Log in" },
            { id: "signup", label: "Create account" },
          ]}
        />
      </div>

      <form onSubmit={submit} className="raised mt-5 space-y-5 rounded-2xl p-5" noValidate>
        <div>
          <label htmlFor="email" className="mb-2 block text-[15px] font-semibold">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            autoCapitalize="none"
            spellCheck={false}
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="min-h-11 w-full rounded-xl border border-line bg-surface px-3.5 text-base outline-none focus:border-accent"
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-2 block text-[15px] font-semibold">
            Password
          </label>
          <div className="flex items-center rounded-xl border border-line bg-surface focus-within:border-accent">
            <input
              id="password"
              name="password"
              type={show ? "text" : "password"}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "signup" ? 8 : undefined}
              maxLength={128}
              aria-describedby={mode === "signup" ? "password-hint" : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="min-h-11 w-full rounded-xl bg-transparent px-3.5 text-base outline-none"
            />
            <button
              type="button"
              onClick={() => setShow((v) => !v)}
              aria-pressed={show}
              className="mr-1 min-h-11 shrink-0 rounded-lg px-3 text-sm font-semibold text-accent"
            >
              {show ? "Hide" : "Show"}
            </button>
          </div>
          {mode === "signup" && (
            <p id="password-hint" className="mt-2 text-sm text-muted">
              At least 8 characters. A few random words make a good one.
            </p>
          )}
        </div>

        {mode === "signup" && <ConsentFields onChange={setConsent} />}

        {error && (
          <p role="alert" className="rounded-xl bg-accent-soft p-3 text-[15px] text-accent">
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" className="w-full" disabled={busy || !email || !password || (mode === "signup" && !consent)}>
          {busy ? copy.busy : copy.button}
        </Button>
      </form>

      <div className="mt-6 space-y-2 text-center text-[15px] text-muted">
        <p>
          Not ready for an account?{" "}
          <Link href="/onboarding" className="font-semibold text-accent underline underline-offset-4">
            Try it as a guest
          </Link>
          .
        </p>
        <p className="text-sm">A guest profile lives only on this device. You can&apos;t move it to another one.</p>
        <p className="text-sm">
          <Link href="/terms" className="underline underline-offset-4">
            Terms
          </Link>
          {" · "}
          <Link href="/privacy" className="underline underline-offset-4">
            Privacy
          </Link>
        </p>
        <PartnerBadge size="sm" className="justify-center pt-2" />
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="pt-safe px-safe">
        <div className="mx-auto flex h-14 w-full max-w-md items-center">
          <Link href="/" className="flex items-center gap-2.5" aria-label="Vantage home">
            <Logo size={28} />
            <span className="font-display text-xl">Vantage</span>
          </Link>
        </div>
      </header>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
