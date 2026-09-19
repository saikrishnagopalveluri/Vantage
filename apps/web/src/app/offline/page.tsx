import type { Metadata } from "next";
import { Logo } from "@/components/icons";

export const metadata: Metadata = { title: "Offline" };

export default function OfflinePage() {
  return (
    <main className="grid min-h-dvh place-items-center px-6 text-center">
      <div className="max-w-sm">
        <Logo size={56} />
        <h1 className="mt-6 font-display text-3xl">You&apos;re offline</h1>
        <p className="mt-3 text-[15px] text-muted">
          Vantage couldn&apos;t reach the network, and this page isn&apos;t saved on your device yet. Reconnect and
          it will pick up where you left off.
        </p>
      </div>
    </main>
  );
}
