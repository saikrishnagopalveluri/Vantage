"use client";

import { useCallback, useEffect, useId, useState, useSyncExternalStore } from "react";
import { api } from "@/lib/api";
import { currentSubscription, pushSupported, subscribe, unsubscribe, updateCategories } from "@/lib/push";
import { useAsync } from "@/lib/hooks";
import { useToast } from "./toast";
import { Button } from "./ui";

const BOX = "mt-0.5 size-5 shrink-0 accent-[var(--accent)]";
const DEFAULT_CATEGORIES = ["streak", "news"]; // a light default; the reader tunes it from here after
const noSubscribe = () => () => {};

type Status = "loading" | "off" | "on";

export function NotificationsCard({ userId }: { userId: string }) {
  const toast = useToast();
  const titleId = useId();
  const categories = useAsync((signal) => api.pushCategories(signal), "push-categories");
  // Reading browser support/permission is synchronous, but touches window/Notification, which
  // don't exist during server rendering — the same pattern useInstall() uses for that reason.
  const supported = useSyncExternalStore(noSubscribe, pushSupported, () => false);
  const denied = useSyncExternalStore(noSubscribe, () => typeof Notification !== "undefined" && Notification.permission === "denied", () => false);
  const [status, setStatus] = useState<Status>("loading");
  const [selected, setSelected] = useState<string[]>(DEFAULT_CATEGORIES);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const sub = await currentSubscription();
    if (sub) {
      const rows = await api.pushSubscriptions(userId).catch(() => []);
      const mine = rows.find((r) => r.endpoint === sub.endpoint);
      if (mine) setSelected(mine.categories);
      setStatus("on");
    } else {
      setStatus("off");
    }
  }, [userId]);

  useEffect(() => {
    if (!supported || denied) return;
    let cancelled = false;
    currentSubscription().then(async (sub) => {
      if (cancelled) return;
      if (!sub) return setStatus("off");
      const rows = await api.pushSubscriptions(userId).catch(() => []);
      if (cancelled) return;
      const mine = rows.find((r) => r.endpoint === sub.endpoint);
      if (mine) setSelected(mine.categories);
      setStatus("on");
    });
    return () => {
      cancelled = true;
    };
  }, [supported, denied, userId]);

  async function enable() {
    setBusy(true);
    try {
      const ok = await subscribe(userId, selected);
      if (ok) {
        toast("Notifications on.");
        await refresh();
      } else if (Notification.permission !== "denied") {
        toast("Couldn't turn on notifications here.");
      }
      // A fresh "denied" is picked up on the next render without a status flag of its own —
      // useSyncExternalStore re-reads Notification.permission every render, and setBusy(false) below triggers one.
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    setBusy(true);
    try {
      await unsubscribe(userId);
      toast("Notifications off.");
      setStatus("off");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(id: string) {
    const next = selected.includes(id) ? selected.filter((c) => c !== id) : [...selected, id];
    setSelected(next);
    if (status === "on") await updateCategories(userId, next);
  }

  if (!supported) return null;

  return (
    <section aria-labelledby={titleId} className="raised rounded-2xl p-4 md:p-5">
      <h2 id={titleId} className="font-display text-xl">
        Notifications
      </h2>
      {denied && (
        <p className="mt-2 text-[15px] text-muted">
          Notifications are blocked for Vantage in your browser. Allow them from your browser&apos;s site settings, then reload this page.
        </p>
      )}
      {!denied && (
        <>
          <p className="mt-2 text-[15px] text-muted">Pick what&apos;s worth a ping. Nothing else reaches you.</p>
          <fieldset className="mt-4 space-y-2.5">
            <legend className="sr-only">Notification categories</legend>
            {Object.entries(categories.data ?? {}).map(([id, label]) => (
              <label key={id} className="flex min-h-11 cursor-pointer items-center gap-3 text-[15px]">
                <input type="checkbox" checked={selected.includes(id)} onChange={() => toggle(id)} className={BOX} />
                {label}
              </label>
            ))}
          </fieldset>
          <div className="mt-4">
            {status === "on" ? (
              <Button onClick={disable} disabled={busy}>
                Turn off notifications
              </Button>
            ) : (
              <Button variant="primary" onClick={enable} disabled={busy || selected.length === 0}>
                Turn on notifications
              </Button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
