"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { Logo } from "@/components/icons";
import { ProfileContext } from "@/components/profile-context";
import { ToastProvider } from "@/components/toast";
import { ErrorNotice, Skeleton } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { clearSession, isAccount, useUserId } from "@/lib/session";

function Splash() {
  return (
    <div className="grid min-h-dvh place-items-center" aria-busy>
      <Logo size={56} />
    </div>
  );
}

function ProfileGate({ userId, children }: { userId: string; children: ReactNode }) {
  const { data: profile, error, reload, setData } = useAsync((signal) => api.profile(userId, signal), `profile:${userId}`);

  const router = useRouter();
  // 404: no profile for this id yet. A new account goes on to onboarding; a guest id the server has
  // never seen is stale. 401: the session ended (cookie expired, or logged out elsewhere).
  const status = error instanceof ApiError ? error.status : 0;
  const needsOnboarding = status === 404 && isAccount();
  const stale = (status === 404 && !needsOnboarding) || status === 401;
  useEffect(() => {
    if (needsOnboarding) router.replace("/onboarding");
    else if (stale) clearSession();
  }, [needsOnboarding, stale, router]);

  if (profile) {
    return (
      <ProfileContext.Provider value={{ profile, reload, setProfile: setData }}>
        <ToastProvider>
          <AppShell profile={profile}>{children}</AppShell>
        </ToastProvider>
      </ProfileContext.Provider>
    );
  }
  if (error && !stale) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <ErrorNotice message={error.message} onRetry={reload} />
      </div>
    );
  }
  // The navigation is already useful, so show it straight away and fill the page when the profile arrives.
  return (
    <AppShell profile={null}>
      <div className="max-w-3xl space-y-4" aria-busy>
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-44 w-full" />
      </div>
    </AppShell>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const userId = useUserId();
  const router = useRouter();

  useEffect(() => {
    if (userId === null) router.replace("/login");
  }, [userId, router]);

  if (!userId) return <Splash />;
  return <ProfileGate userId={userId}>{children}</ProfileGate>;
}
