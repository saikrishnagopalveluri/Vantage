"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { ConsentBody } from "@/lib/types";

const BOX = "mt-0.5 size-5 shrink-0 accent-[var(--accent)]";

/** The two things a person confirms before we keep any data about them. Reports a consent only when both are ticked. */
export function ConsentFields({ onChange }: { onChange: (consent: ConsentBody | null) => void }) {
  const legal = useAsync((signal) => api.legal(signal), "legal");
  const [adult, setAdult] = useState(false);
  const [agreed, setAgreed] = useState(false);

  useEffect(() => {
    const info = legal.data;
    onChange(info && adult && agreed ? { terms_version: info.terms_version, privacy_version: info.privacy_version, over_18: true } : null);
  }, [legal.data, adult, agreed, onChange]);

  return (
    <fieldset className="space-y-3">
      <legend className="mb-1 text-[15px] font-semibold">Before we start</legend>
      <label className="flex min-h-11 cursor-pointer items-start gap-3 text-[15px] leading-snug">
        <input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} className={BOX} />I am 18 or older.
      </label>
      <label className="flex min-h-11 cursor-pointer items-start gap-3 text-[15px] leading-snug">
        <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className={BOX} />
        <span>
          I agree to the{" "}
          <Link href="/terms" target="_blank" className="font-semibold text-accent underline underline-offset-4">
            Terms of Use
          </Link>{" "}
          and have read the{" "}
          <Link href="/privacy" target="_blank" className="font-semibold text-accent underline underline-offset-4">
            Privacy Policy
          </Link>
          .
        </span>
      </label>
      <p className="text-sm text-muted">
        We keep your choices and, for an account, your email, only to run the app for you. You can download or delete all of it at any time.
      </p>
      {legal.error && !legal.data && (
        <p role="alert" className="text-sm text-accent">
          Couldn&apos;t load the current terms. Reload the page.
        </p>
      )}
    </fieldset>
  );
}
